"""tests/test_race.py -- scoring/standings + LAN race message roundtrip."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiplayer.race import (  # noqa: E402
    RACE_DURATION_S, RacerStats, compute_standings, fmt_time, score_for,
)
from multiplayer.lobby import LobbyHost, LobbyClient  # noqa: E402


def test_duration_is_10_minutes():
    assert RACE_DURATION_S == 600


def test_rank_levels_then_restarts_then_steps():
    racers = [
        RacerStats("slow", levels=5, moves=100, restarts=0),
        RacerStats("fast", levels=5, moves=300, restarts=0),
        RacerStats("clean", levels=5, moves=300, restarts=1),
        RacerStats("champ", levels=6, moves=900, restarts=9),
    ]
    order = [s.name for s in compute_standings(racers)]
    assert order == ["champ", "slow", "fast", "clean"], order


def test_score_mirrors_rank_order():
    a = RacerStats("a", levels=3, moves=120, restarts=1)
    b = RacerStats("b", levels=3, moves=200, restarts=1)
    assert a.score > b.score
    assert score_for(1, 0, 0) > score_for(0, 999, 999)


def test_fmt_time():
    assert fmt_time(600) == "10:00"
    assert fmt_time(61) == "01:01"
    assert fmt_time(-5) == "00:00"


def _drain(client, timeout=3.0):
    """Collect (kind, payload) for `timeout` seconds."""
    out = []
    end = time.time() + timeout
    while time.time() < end:
        try:
            out.append(client.events.get(timeout=max(0.0, end - time.time())))
        except Exception:
            break
    return out


def test_race_message_flow():
    host = LobbyHost("Host", "race", port=0)
    port = host.start()
    try:
        g1 = LobbyClient(" speedy ")
        g1.connect("127.0.0.1", port)
        g2 = LobbyClient("slowpoke")
        g2.connect("127.0.0.1", port)
        time.sleep(0.3)

        host.start_race(duration_s=60)
        time.sleep(0.5)
        kinds1 = [k for k, _ in _drain(g1, timeout=1.0)]
        assert "race_start" in kinds1, kinds1

        g1.send_progress(levels=2, moves=50, restarts=0)
        g2.send_progress(levels=2, moves=80, restarts=1)
        time.sleep(0.8)
        boards = [p for k, p in _drain(g1, timeout=1.0) if k == "race_board"]
        assert boards, "guest must receive leaderboard"
        names = [r["name"] for r in boards[-1]["standings"]]
        assert names[0] == " speedy ".strip(), names  # fewer steps wins tie
        assert set(names) >= {"Host", "speedy", "slowpoke"}

        late = LobbyClient("late")
        try:
            late.connect("127.0.0.1", port)
        except ConnectionError as e:
            assert "race in progress" in str(e), e
        else:
            raise AssertionError("late join during race must be rejected")
        finally:
            try:
                late.leave()
            except Exception:
                pass

        msg = host.end_race()
        assert msg["type"] == "race_end"
        order = [s["name"] for s in msg["standings"]]
        assert order[0] == "speedy", order
        time.sleep(0.5)
        kinds2 = [k for k, _ in _drain(g2, timeout=1.0)]
        assert "race_end" in kinds2, kinds2
        g1.leave()
        g2.leave()
    finally:
        host.stop()


if __name__ == "__main__":
    tests = [test_duration_is_10_minutes,
             test_rank_levels_then_restarts_then_steps,
             test_score_mirrors_rank_order, test_fmt_time,
             test_race_message_flow]
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
