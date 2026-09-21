from levels_data import build_level1, build_level2, build_level3, build_level4
from blocks import CodeBlock

for lvl in [build_level1(), build_level2(), build_level3(), build_level4()]:
    print('LEVEL', lvl.name)
    for y in range(lvl.height):
        row = ''
        for x in range(lvl.width):
            if lvl.player and (lvl.player.x, lvl.player.y) == (x, y):
                row += 'P'
                continue
            occ = lvl.object_at(x, y)
            if occ is not None:
                cls = occ.__class__.__name__
                if cls == 'CodeBlock':
                    row += 'C'
                elif cls == 'Platform':
                    row += 'B'
                elif cls == 'Door':
                    row += 'D'
                elif cls == 'Trap':
                    row += 'T'
                else:
                    row += '?'
                continue
            tile = lvl.tile_at(x, y)
            if tile.__class__.__name__ == 'Wall':
                row += '#'
            elif tile.__class__.__name__ == 'Goal':
                row += 'G'
            else:
                row += '.'
        print(row)
    print('CIRCUITS')
    for c in lvl.circuits:
        print(c.name, c.slot_positions, c.last_result)
    print('BLOCKS', [(o.x,o.y,o.kind,o.value) for o in lvl.dynamic_objects if isinstance(o, CodeBlock)])
    print()
