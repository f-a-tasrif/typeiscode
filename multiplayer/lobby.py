"""lobby.py — LAN lobby host + client (same-network TCP + UDP beacons).

Host:
    LobbyHost(host_name, gamemode).start() -> TCP accept loop + UDP beacon.
    Players join over TCP with {"type": "hello", "name": ...}.
    Host keeps a player list and broadcasts {"type": "lobby_state", ...}.
    host.start_game() broadcasts {"type": "start"} — gameplay itself is a
    placeholder until gamemode level logic lands, so the lobby stays open.

Client:
    LobbyClient.discover(timeout) -> [LobbyInfo] via UDP beacons.
    LobbyClient(name).connect(ip, port) -> hello/welcome handshake,
    then background listener fills .events / .players / .started.
"""
from __future__ import annotations

import queue
import socket
import threading
import time
from dataclasses import dataclass, field

from .protocol import (
    BEACON_INTERVAL_S,
    DEFAULT_LOBBY_PORT,
    DISCOVERY_PORT,
    GAME_MAGIC,
    MAX_PLAYERS,
    encode_msg,
    is_beacon,
    make_beacon,
    new_lobby_id,
    valid_gamemode,
)


@dataclass
class LobbyInfo:
    lobby_id: str
    host_name: str
    gamemode: str
    address: str
    port: int
    players: int = 0


def _recv_line(f) -> dict | None:
    import json
    line = f.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except Exception:
        return None


class LobbyHost:
    def __init__(self, host_name: str, gamemode: str,
                 port: int = DEFAULT_LOBBY_PORT,
                 max_players: int = MAX_PLAYERS):
        if not host_name.strip():
            raise ValueError("host_name must not be empty")
        if not valid_gamemode(gamemode):
            raise ValueError(f"unknown gamemode {gamemode!r}")
        self.host_name = host_name.strip()
        self.gamemode = gamemode
        self.port = port
        self.max_players = max_players
        self.lobby_id = new_lobby_id()
        self.players: list[str] = [self.host_name]
        self.started = False
        self.events: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._clients: list = []  # (socket, file, name)
        self._running = False
        self._server: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self.bound_port: int = port

    # -- lifecycle ---------------------------------------------------
    def start(self) -> int:
        """Bind TCP + launch accept/beacon threads. Returns bound port."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(8)
        srv.settimeout(0.5)
        self._server = srv
        self.bound_port = srv.getsockname()[1]
        self._running = True
        t_accept = threading.Thread(target=self._accept_loop, daemon=True)
        t_beacon = threading.Thread(target=self._beacon_loop, daemon=True)
        t_accept.start()
        t_beacon.start()
        self._threads = [t_accept, t_beacon]
        return self.bound_port

    def stop(self):
        self._running = False
        try:
            if self._server is not None:
                self._server.close()
        except Exception:
            pass
        with self._lock:
            clients = list(self._clients)
            self._clients = []
        for sock, _f, _n in clients:
            try:
                sock.close()
            except Exception:
                pass

    # -- host actions ------------------------------------------------
    def start_game(self, note: str = "") -> dict:
        """Broadcast START. Placeholder: lobby stays open for later logic."""
        msg = {"type": "start", "lobby_id": self.lobby_id,
               "gamemode": self.gamemode,
               "note": note or f"Gamemode '{self.gamemode}' gameplay coming soon."}
        self.started = True
        self._broadcast(msg)
        self.events.put(("started", msg))
        return msg

    def _broadcast(self, obj: dict):
        raw = encode_msg(obj)
        with self._lock:
            clients = list(self._clients)
        for sock, _f, _n in clients:
            try:
                sock.sendall(raw)
            except Exception:
                pass

    def _broadcast_state(self):
        with self._lock:
            players = list(self.players)
        self._broadcast({"type": "lobby_state", "lobby_id": self.lobby_id,
                         "gamemode": self.gamemode, "players": players,
                         "host": self.host_name})

    # -- internals ---------------------------------------------------
    def _accept_loop(self):
        while self._running:
            try:
                conn, _addr = self._server.accept()
            except socket.timeout:
                continue
            except Exception:
                return
            t = threading.Thread(target=self._handle_client,
                                 args=(conn,), daemon=True)
            t.start()

    def _handle_client(self, conn: socket.socket):
        try:
            conn.settimeout(10.0)
            f = conn.makefile("r", encoding="utf-8")
            hello = _recv_line(f)
            if not hello or hello.get("type") != "hello":
                conn.sendall(encode_msg({"type": "error",
                                         "message": "expected hello"}))
                conn.close()
                return
            name = str(hello.get("name", "")).strip()[:24] or "Player"
            with self._lock:
                if len(self.players) >= self.max_players:
                    conn.sendall(encode_msg({"type": "error",
                                             "message": "lobby full"}))
                    conn.close()
                    return
                base, i = name, 2
                while base in self.players:
                    base = f"{name}-{i}"
                    i += 1
                name = base
                self.players.append(name)
                self._clients.append((conn, f, name))
            conn.sendall(encode_msg({"type": "welcome",
                                     "lobby_id": self.lobby_id,
                                     "gamemode": self.gamemode,
                                     "players": list(self.players),
                                     "you": name,
                                     "host": self.host_name}))
            self.events.put(("join", name))
            self._broadcast({"type": "player_joined", "name": name,
                             "players": list(self.players)})
            conn.settimeout(60.0)
            while self._running:
                msg = _recv_line(f)
                if msg is None:
                    break
                if msg.get("type") == "leave":
                    break
                # Unknown chat/ping messages are ignored for now.
            with self._lock:
                if name in self.players:
                    self.players.remove(name)
                self._clients = [(s, ff, n) for s, ff, n in self._clients
                                 if n != name]
            self.events.put(("leave", name))
            self._broadcast({"type": "player_left", "name": name,
                             "players": list(self.players)})
            try:
                conn.close()
            except Exception:
                pass
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def _beacon_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        # Also answer active probes on the discovery port.
        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen.bind(("0.0.0.0", DISCOVERY_PORT))
            listen.settimeout(0.2)
        except Exception:
            listen = None  # another host owns the port; broadcast still works
        while self._running:
            try:
                with self._lock:
                    n = len(self.players)
                beacon = make_beacon(self.lobby_id, self.host_name,
                                     self.gamemode, self.bound_port, n)
                import json as _json
                raw = _json.dumps(beacon).encode("utf-8")
                for target in ("255.255.255.255", "127.0.0.1"):
                    try:
                        sock.sendto(raw, (target, DISCOVERY_PORT))
                    except Exception:
                        pass
                if listen is not None:
                    try:
                        data, addr = listen.recvfrom(2048)
                        import json as _j2
                        obj = _j2.loads(data.decode("utf-8", "ignore"))
                        if isinstance(obj, dict) and obj.get("type") == "probe":
                            try:
                                sock.sendto(raw, addr)
                            except Exception:
                                pass
                    except socket.timeout:
                        pass
                    except Exception:
                        pass
                else:
                    time.sleep(BEACON_INTERVAL_S)
                    continue
                # pace broadcasts without blocking probe replies too long
                time.sleep(BEACON_INTERVAL_S)
            except Exception:
                time.sleep(BEACON_INTERVAL_S)
        try:
            sock.close()
        except Exception:
            pass
        if listen is not None:
            try:
                listen.close()
            except Exception:
                pass


class LobbyClient:
    def __init__(self, player_name: str):
        if not player_name.strip():
            raise ValueError("player_name must not be empty")
        self.player_name = player_name.strip()
        self.players: list[str] = []
        self.gamemode = ""
        self.lobby_id = ""
        self.host_name = ""
        self.started = False
        self.start_note = ""
        self.you = ""
        self.events: queue.Queue = queue.Queue()
        self._sock: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    @staticmethod
    def discover(timeout: float = 2.0) -> list[LobbyInfo]:
        """Listen for host beacons on the LAN (+ send a probe)."""
        found: dict[str, LobbyInfo] = {}
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except Exception:
                pass
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            sock.settimeout(0.3)
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            return []
        import json as _json
        probe = _json.dumps({"magic": GAME_MAGIC, "type": "probe"}).encode()
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                sock.sendto(probe, (target, DISCOVERY_PORT))
            except Exception:
                pass
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
                obj = _json.loads(data.decode("utf-8", "ignore"))
            except socket.timeout:
                continue
            except Exception:
                continue
            if not is_beacon(obj):
                continue
            lid = str(obj["lobby_id"])
            found[lid] = LobbyInfo(
                lobby_id=lid,
                host_name=str(obj.get("host_name", "host")),
                gamemode=str(obj.get("gamemode", "?")),
                address=addr[0],
                port=int(obj.get("tcp_port", DEFAULT_LOBBY_PORT)),
                players=int(obj.get("players", 0)),
            )
        try:
            sock.close()
        except Exception:
            pass
        return list(found.values())

    def connect(self, address: str, port: int,
                timeout: float = 5.0) -> dict:
        sock = socket.create_connection((address, port), timeout=timeout)
        sock.settimeout(10.0)
        sock.sendall(encode_msg({"type": "hello", "name": self.player_name}))
        f = sock.makefile("r", encoding="utf-8")
        resp = _recv_line(f)
        if resp is None:
            sock.close()
            raise ConnectionError("no response from host")
        if resp.get("type") == "error":
            sock.close()
            raise ConnectionError(str(resp.get("message", "join rejected")))
        if resp.get("type") != "welcome":
            sock.close()
            raise ConnectionError("unexpected reply from host")
        self._sock = sock
        self.lobby_id = str(resp.get("lobby_id", ""))
        self.gamemode = str(resp.get("gamemode", ""))
        self.players = list(resp.get("players", []))
        self.you = str(resp.get("you", self.player_name))
        self.host_name = str(resp.get("host", ""))
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop,
                                        args=(f,), daemon=True)
        self._thread.start()
        return resp

    def leave(self):
        self._running = False
        try:
            if self._sock is not None:
                self._sock.sendall(encode_msg({"type": "leave"}))
        except Exception:
            pass
        try:
            if self._sock is not None:
                self._sock.close()
        except Exception:
            pass
        self._sock = None

    def _listen_loop(self, f):
        while self._running:
            try:
                msg = _recv_line(f)
            except Exception:
                break
            if msg is None:
                break
            mtype = msg.get("type")
            if mtype in ("lobby_state", "player_joined", "player_left"):
                self.players = list(msg.get("players", self.players))
            elif mtype == "start":
                self.started = True
                self.start_note = str(msg.get("note", ""))
                self.gamemode = str(msg.get("gamemode", self.gamemode))
            self.events.put((mtype, msg))
        self._running = False
        self.events.put(("disconnected", {}))
