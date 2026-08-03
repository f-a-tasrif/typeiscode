from collections import deque
from levels_data import build_level1, build_level2, build_level3
from level import DIRS

builders = [build_level1, build_level2, build_level3]

with open('solver_debug2.txt', 'w', encoding='utf-8') as out:
    for build in builders:
        lvl = build()
        out.write(f'LEVEL {lvl.name}\n')
        out.write(f'player={lvl.player.x},{lvl.player.y}\n')
        out.write(f'goal={[(x,y) for (x,y),tile in lvl.tiles.items() if tile.__class__.__name__=="Goal"]}\n')
        out.write(f'circuits={[(c.name, c.slot_positions, c.last_result) for c in lvl.circuits]}\n')
        out.write(f'blocks={[(o.x,o.y,o.kind,o.value) for o in lvl.dynamic_objects if o.__class__.__name__=="CodeBlock"]}\n')
        out.write('grid:\n')
        for y in range(lvl.height):
            row = ''
            for x in range(lvl.width):
                occ = lvl.object_at(x, y)
                if lvl.player and (lvl.player.x, lvl.player.y) == (x, y):
                    row += 'P'
                elif occ is not None:
                    t = occ.__class__.__name__
                    row += {'Platform':'B','Door':'D','Trap':'T','CodeBlock':'C'}.get(t,'?')
                else:
                    tile = lvl.tile_at(x, y)
                    row += {'Wall':'#','Goal':'G'}.get(tile.__class__.__name__, '.')
            out.write(row + '\n')
        out.write('\n')
    out.write('DONE\n')
