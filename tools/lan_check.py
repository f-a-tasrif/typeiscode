"""tools/lan_check.py -- diagnose same-network lobby discovery + join.

Run on the HOST machine:
    python tools/lan_check.py host
Run on the GUEST machine (same Wi-Fi):
    python tools/lan_check.py find
The guest should list the host's lobby. If it doesn't, discovery
broadcasts are blocked -- type the host IP manually in the game
(see the HOST IP line on the host's lobby screen).

Guest direct-connect test (no discovery involved):
    python tools/lan_check.py join <host-ip> [port]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiplayer.lobby import (  # noqa: E402
    LobbyClient, LobbyHost, broadcast_targets, lan_ips,
)
from multiplayer.protocol import DEFAULT_LOBBY_PORT  # noqa: E402


def cmd_host():
    print("Local IPs:", lan_ips())
    print("Broadcast targets:", broadcast_targets())
    host = LobbyHost("lan-check", "race", port=0)
    port = host.start()
    print(f"Hosting 'lan-check' lobby on TCP port {port}.")
    print("On the guest, run:  python tools/lan_check.py find")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1.0)
            try:
                while True:
                    kind, payload = host.events.get_nowait()
                    print(f"event: {kind} {payload}")
            except Exception:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        host.stop()


def cmd_find():
    print("Listening for beacons (~4s)...")
    found = LobbyClient.discover(timeout=4.0)
    if not found:
        print("No lobbies found. Checklist:")
        print("  - same Wi-Fi on both machines (guest/isolation modes block this)")
        print("  - host lobby open (run 'python tools/lan_check.py host' there)")
        print("  - host firewall allowing Python (UDP 28766 in, TCP out)")
        print("  - else join directly: python tools/lan_check.py join <host-ip>")
        return
    for info in found:
        print(f"  {info.host_name} [{info.gamemode}] {info.players}p "
              f"at {info.address}:{info.port} (lobby {info.lobby_id})")


def cmd_join(ip, port):
    print(f"Connecting to {ip}:{port} ...")
    client = LobbyClient("lan-check-guest")
    try:
        resp = client.connect(ip, port)
    except Exception as e:
        print(f"JOIN FAILED: {e}")
        return
    print(f"JOINED: lobby {resp.get('lobby_id')} as {resp.get('you')}")
    client.leave()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "find"
    if mode == "host":
        cmd_host()
    elif mode == "find":
        cmd_find()
    elif mode == "join" and len(sys.argv) > 2:
        cmd_join(sys.argv[2],
                 int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_LOBBY_PORT)
    else:
        print(__doc__)
