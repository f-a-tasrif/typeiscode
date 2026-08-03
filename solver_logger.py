from collections import deque
import copy
import json

from levels_data import build_level1, build_level2, build_level3
from level import DIRS

LEVEL_BUILDERS = [build_level1, build_level2, build_level3]


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
    visited = set()
    q = deque([(level, 0)])
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
        if dist > 200:
            continue
        for d in DIRS:
            state2 = copy.deepcopy(state)
            state2.move_player(d)
            q.append((state2, dist + 1))
    return False, None, len(visited)


results = []
for build in LEVEL_BUILDERS:
    level = build()
    solvable, dist, visited = solve(level)
    results.append({
        'level': level.name,
        'solvable': solvable,
        'distance': dist,
        'visited': visited,
        'player': (level.player.x, level.player.y),
        'goal': [(x, y) for (x, y), tile in level.tiles.items() if tile.__class__.__name__ == 'Goal'],
        'blocks': [(o.x, o.y, getattr(o, 'kind', None), getattr(o, 'value', None)) for o in level.dynamic_objects],
        'circuits': [(c.name, c.slot_positions, c.last_result) for c in level.circuits],
    })

with open('solver_report.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
