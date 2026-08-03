from collections import deque
import copy

from levels_data import build_level1, build_level2
from level import DIRS

def state_key(level):
    objs = tuple(sorted(
        (
            (o.__class__.__name__, o.x, o.y, getattr(o, 'kind', None), getattr(o, 'value', None))
            for o in level.dynamic_objects
        ),
        key=lambda x: (x[0], x[1], x[2], str(x[3]), str(x[4]))
    ))
    return (level.player.x, level.player.y, objs)

for builder in [build_level1, build_level2]:
    level = builder()
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
            print(f"Level '{state.name}' solved in {dist} moves! Visited: {len(visited)} states.")
            found = True
            break
        if state.dead or dist > 50:
            continue
        for d in DIRS:
            nxt = copy.deepcopy(state)
            msg = nxt.move_player(d)
            if nxt.won or msg == "":
                q.append((nxt, dist + 1))
    print(f"{level.name} solved status: {found}")
