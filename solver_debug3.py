from collections import deque
import copy
import json
from levels_data import build_level1, build_level2, build_level3
from level import DIRS

builders = [build_level1, build_level2, build_level3]


def state_key(level):
    objs = tuple(sorted(
        (
            (o.__class__.__name__, o.x, o.y, getattr(o, 'kind', None), getattr(o, 'value', None))
            for o in level.dynamic_objects
        ),
        key=lambda x: (x[0], x[1], x[2], x[3], x[4])
    ))
    return (level.player.x, level.player.y, objs)


def solve(level):
    q = deque([(level, 0)])
    visited = set()
    while q:
        state, dist = q.popleft()
        key = state_key(state)
        if key in visited:
            continue
        visited.add(key)
        if state.won:
            return True, dist, len(visited)
        if state.dead:
            continue
        if dist > 150:
            continue
        for d in DIRS:
            next_state = copy.deepcopy(state)
            next_state.move_player(d)
            q.append((next_state, dist + 1))
    return False, None, len(visited)

results = []
for build in builders:
    lvl = build()
    solvable, dist, count = solve(lvl)
    results.append({'level': lvl.name, 'solvable': solvable, 'moves': dist, 'visited': count})

with open('e:/Projects/typeiscode/solver_debug3_output.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
