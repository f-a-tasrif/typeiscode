from levels_data import build_level1, build_level2, build_level3
from blocks import CodeBlock

with open('layout_debug.txt', 'w', encoding='utf-8') as f:
    for lvl in [build_level1(), build_level2(), build_level3()]:
        f.write(f'LEVEL {lvl.name}\n')
        for y in range(lvl.height):
            row = ''
            for x in range(lvl.width):
                if lvl.player and (lvl.player.x, lvl.player.y) == (x, y):
                    row += 'P'
                else:
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
                    else:
                        tile = lvl.tile_at(x, y)
                        if tile.__class__.__name__ == 'Wall':
                            row += '#'
                        elif tile.__class__.__name__ == 'Goal':
                            row += 'G'
                        else:
                            row += '.'
            f.write(row + '\n')
        f.write('CIRCUITS\n')
        for c in lvl.circuits:
            f.write(f'{c.name} {c.slot_positions} {c.last_result}\n')
        f.write(f'BLOCKS {[(o.x,o.y,o.kind,o.value) for o in lvl.dynamic_objects if isinstance(o, CodeBlock)]}\n')
        f.write('\n')
