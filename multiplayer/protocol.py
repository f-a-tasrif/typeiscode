from __future__ import annotations

import json
import uuid

GAME_MAGIC = "type-is-code"
DISCOVERY_PORT = 28766
DEFAULT_LOBBY_PORT = 28765
MAX_PLAYERS = 4
BEACON_INTERVAL_S = 1.0



GAMEMODES: list[dict[str, str]] = [
    {"id": "co-op-puzzle", "label": "Win together"},
    {"id": "race", "label": "I'm faster than you"},
    {"id": "versus", "label": "Duel"},
]

GAMEMODE_IDS = [g["id"] for g in GAMEMODES]


def valid_gamemode(mode: str) -> bool:
    return mode in GAMEMODE_IDS


def gamemode_label(mode: str) -> str:
    for g in GAMEMODES:
        if g["id"] == mode:
            return g["label"]
    return mode


def new_lobby_id() -> str:
    return uuid.uuid4().hex[:8]


def encode_msg(obj: dict) -> bytes:
    return (json.dumps(obj) + "\n").encode("utf-8")


def decode_line(line: bytes | str) -> dict:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    return json.loads(line)


def make_beacon(lobby_id: str, host_name: str, gamemode: str,
                tcp_port: int, player_count: int) -> dict:
    return {
        "magic": GAME_MAGIC,
        "type": "beacon",
        "lobby_id": lobby_id,
        "host_name": host_name,
        "gamemode": gamemode,
        "tcp_port": tcp_port,
        "players": player_count,
    }


def is_beacon(obj: dict) -> bool:
    return (isinstance(obj, dict) and obj.get("magic") == GAME_MAGIC
            and obj.get("type") in ("beacon", "probe-reply")
            and "lobby_id" in obj and "tcp_port" in obj)
