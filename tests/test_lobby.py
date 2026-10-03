"""tests/test_lobby.py -- lobby host/join/start roundtrip on localhost."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiplayer.lobby import LobbyHost, LobbyClient  # noqa: E402
from multiplayer.protocol import GAMEMODES  # noqa: E402


def test_host_join_start_leave():
    host = LobbyHost("Host", GAMEMODES[0]["id"], port=0)
    port = host.start()
    try:
        guest = LobbyClient("Guest")
        resp = guest.connect("127.0.0.1", port)
        assert resp["type"] == "welcome", resp
        time.sleep(0.5)
        assert "Guest" in host.players, host.players
        host.start_game()
        time.sleep(0.5)
        assert guest.started, "guest must see host start"
        assert "coming soon" in guest.start_note, guest.start_note
        guest.leave()
        time.sleep(0.5)
        assert "Guest" not in host.players, host.players
    finally:
        host.stop()


def test_bad_gamemode_rejected():
    try:
        LobbyHost("Host", "no-such-mode", port=0)
    except ValueError:
        return
    raise AssertionError("unknown gamemode must raise ValueError")


if __name__ == "__main__":
    tests = [test_host_join_start_leave, test_bad_gamemode_rejected]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
