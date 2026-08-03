from collections import deque
import copy

from levels_data import build_level1, build_level2, build_level3
from level import DIRS
from blocks import CodeBlock

LEVEL_BUILDERS = [build_level1, build_level2, build_level3]


def state_key(level):
    objs = tuple(sorted(
        (
            (o.__class__.__name__, o.x, o.y, getattr(o, 'kind', None), getattr(o, 'value', None))
            for o in level.dynamic_objects
        ),
        key=lambda x: (x[0], x[1], x[2], str(x[3]), str(x[4]))
    ))
    return (level.player.x, level.player.y, objs)


def successors(orig_level):
    for d in DIRS:
        level = copy.deepcopy(orig_level)
        msg = level.move_player(d)
        if level.won or level.dead:
            yield d, level
        elif msg == "":
            yield d, level


for builder in LEVEL_BUILDERS:
    level = builder()
    print("LEVEL:", level.name)
    print("Start player:", level.player.x, level.player.y)
    print("Goal:", [(x, y) for (x, y), tile in level.tiles.items() if tile.__class__.__name__ == 'Goal'])

    visited = set()
    q = deque([(level, 0)])
    found = False
    while q:
        state, dist = q.popleft()
        key = state_key(state)
        if key in visited:
            continue
        visited.add(key)
        if state.won:
            print(f"-> SOLVED {state.name} in {dist} moves! Visited: {len(visited)} states.")
            found = True
            break
        if state.dead or dist > 80:
            continue
        for d, next_state in successors(state):
            q.append((next_state, dist + 1))
    assert found, f"Level {level.name} should be solvable!"
    print("---")
