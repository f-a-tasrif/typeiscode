from collections import deque
import copy
import levels_data
from level import DIRS


def state_key(level):
    objs = tuple(sorted(
        ((o.__class__.__name__, o.x, o.y, getattr(o, 'kind', None), getattr(o, 'value', None))
         for o in level.dynamic_objects),
        key=lambda x: (x[0], x[1], x[2], x[3], x[4])
    ))
    return (level.player.x, level.player.y, objs)


def successors(orig_level):
    for d in DIRS:
        level = copy.deepcopy(orig_level)
        msg = level.move_player(d)
        if msg == '' or level.won or level.dead:
            yield d, level


for build_func in [levels_data.build_level1, levels_data.build_level2, levels_data.build_level3]:
    lvl = build_func()
    print('LEVEL', lvl.name)
    print('Start player', lvl.player.x, lvl.player.y)
    print('Goal', [(x, y) for (x, y), tile in lvl.tiles.items() if tile.__class__.__name__ == 'Goal'])
    print('Blocks', [(o.x, o.y, o.kind, o.value) for o in lvl.dynamic_objects if o.__class__.__name__ == 'CodeBlock'])
    print('Circuits', [(c.name, c.slot_positions, c.last_result) for c in lvl.circuits])

    visited = set()
    q = deque([(lvl, 0)])
    found = False
    while q:
        state, dist = q.popleft()
        key = state_key(state)
        if key in visited:
            continue
        visited.add(key)
        if state.won:
            print('FOUND in', dist)
            found = True
            break
        if state.dead:
            continue
        if dist > 200:
            continue
        for d, next_state in successors(state):
            q.append((next_state, dist + 1))
    print('Solvable', found, 'visited', len(visited))
    print('---')
