"""tests/test_maps.py -- replay HTML solutions on data-driven global levels.

Parametrized by level number (5 + index into MAPS).  Each MAPS entry holds
name, rows, start=(row, col), tokens=[(row, col, text)] and
solution=[(moves_string, note)].  Moves translate U->w, D->s, L->a, R->d.

Every step must increment level.moves (a step that doesn't is a rejected
move), the player must never die, and level.won must be True at the end.
On failure the first bad move index, the board and the registry are
printed -- the solution itself is never edited.

Requires maps_data.py (ported from type-is-code-maps.html, Stage 1).  If
it is absent the run is skipped with a clear message.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from maps_data import MAPS
except ImportError:
    MAPS = None

from levels_data import _build_from_map  # noqa: E402

DIRS = {"U": "w", "D": "s", "L": "a", "R": "d"}

# (level_no, after_phase_index, class, prop, expected): registry spot-checks
# run mid-replay. Phase indices are 0-based.
PHASE_CHECKS = {
    5: [(0, "Platform", "isSolid", True), (5, "Trap", "isLethal", False)],
    6: [(0, "Platform", "isSolid", True)],
    8: [(3, "Platform", "isSolid", True)],
}


# Levels whose HTML solutions cannot complete go here as
# {level_no: reason}. Currently empty: every replay passes.
# (Level numbers follow ALL_LEVELS; MAPS[0] has no level.)
EXPECTED_FAIL = {}


def replay(entry, checks=(), builder=None):
    """Replay one MAPS entry.

    Builds via the ALL_LEVELS builder when given (so builder tweaks
    like value flips apply), else raw from the entry data. Stops at
    the first win: our engine ends the level the moment the player
    steps on the goal, so moves past that point are engine no-ops,
    not solution steps.  Returns (level, rejected, died_at, won,
    check_failures).
    """
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
    # MAPS[0] has no level (old level 5 was deleted); levels 5-8 use MAPS[1:].
    # Levels are built via their ALL_LEVELS builders so builder tweaks apply.
    # Explicit builder mapping (independent of ALL_LEVELS order).
    from levels_data import build_level5, build_level6, build_level7, build_level8
    builders = [build_level5, build_level6, build_level7, build_level8]
    entries = [(5 + i, builder, entry)
               for i, (builder, entry) in enumerate(zip(builders, MAPS[1:]))]
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
