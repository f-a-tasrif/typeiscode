
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from maps_data import MAPS
except ImportError:
    MAPS = None

from levels_data import _build_from_map

DIRS = {"U": "w", "D": "s", "L": "a", "R": "d"}



PHASE_CHECKS = {
    3: [(0, "Platform", "isSolid", True)],
    10: [(3, "Platform", "isSolid", True)],
}





EXPECTED_FAIL = {}


def replay(entry, checks=(), builder=None):
    from registry import PropertyRegistry
    if builder is not None:
        lvl = builder()
    else:
        lvl = _build_from_map(entry["name"], entry["rows"],
                               entry["start"], entry["tokens"])
    checks = sorted(checks)
    rejected = []
    died_at = None
    check_failures = []
    step = 0
    for phase_i, (moves, _note) in enumerate(entry["solution"]):
        for ch in moves:
            if ch not in DIRS:
                continue
            m0 = lvl.moves
            lvl.move_player(DIRS[ch])
            if lvl.moves == m0 and not lvl.won:
                rejected.append((phase_i, step, ch))
            step += 1
            if lvl.dead and died_at is None:
                died_at = (phase_i, step, ch)
                return lvl, rejected, died_at, False, check_failures
            if lvl.won:
                break
        for (cphase, cls, prop, want) in checks:
            if cphase == phase_i:
                got = PropertyRegistry.get(cls, prop)
                if got is not want and got != want:
                    check_failures.append((phase_i, cls, prop, want, got))
        if lvl.won:
            break
    return lvl, rejected, died_at, lvl.won, check_failures


def test_map(level_no, entry, builder=None):
    lvl, rejected, died_at, won, check_failures = replay(
        entry, PHASE_CHECKS.get(level_no, ()), builder)
    if rejected or died_at is not None or not won or check_failures:
        print(f"--- FAIL level {level_no}: {entry['name']} ---")
        if rejected:
            pi, si, ch = rejected[0]
            print(f"first rejected move: phase {pi} step {si} ({ch})")
        if died_at is not None:
            pi, si, ch = died_at
            print(f"died at: phase {pi} step {si} ({ch})")
        for pi, cls, prop, want, got in check_failures:
            print(f"phase {pi}: {cls}.{prop}={got!r}, want {want!r}")
        print(f"won={won}")
        print(lvl.render())
        print("REGISTRY: " + lvl.render_registry())
        print("RULES: " + str(getattr(lvl, "active_rules", [])))
    assert not rejected, f"level {level_no}: rejected moves {rejected[:3]}"
    assert died_at is None, f"level {level_no}: died at {died_at}"
    assert won, f"level {level_no}: solution ended without winning"
    assert not check_failures, f"level {level_no}: {check_failures}"


if __name__ == "__main__":
    if MAPS is None:
        print("SKIP: maps_data.py not present -- "
              "port it from type-is-code-maps.html (Stage 1) first.")
        sys.exit(0)
    only = [int(a) for a in sys.argv[1:] if a.isdigit()]
    failed = 0
    xfailed = 0
    ran = 0





    from levels_data import build_level6, build_level7, build_level8
    entries = [(3, build_level6, MAPS[2]),
               (4, build_level7, MAPS[3]),
               (10, build_level8, MAPS[4])]
    for level_no, builder, entry in entries:
        if only and level_no not in only:
            continue
        ran += 1
        try:
            test_map(level_no, entry, builder)
            print(f"PASS level {level_no}: {entry['name']}")
        except AssertionError as e:
            if level_no in EXPECTED_FAIL:
                xfailed += 1
                print(f"XFAIL level {level_no} (expected: {EXPECTED_FAIL[level_no]}): {e}")
            else:
                failed += 1
                print(f"FAIL level {level_no}: {e}")
    print(f"{ran - failed - xfailed}/{ran} map replays passed, {xfailed} expected failures")
    sys.exit(1 if failed else 0)
