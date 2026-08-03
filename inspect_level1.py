import os
import levels_data
from level import DIRS

os.chdir(r'e:\Projects\typeiscode')
lvl = levels_data.build_level1()
print('Level:', lvl.name)
print('Player:', lvl.player.x, lvl.player.y)
print('Goal:', [(x,y) for (x,y),t in lvl.tiles.items() if t.__class__.__name__=='Goal'])
print('Blocks:', [(o.x,o.y,o.kind,o.value) for o in lvl.dynamic_objects if o.__class__.__name__=='CodeBlock'])
print('Row2:', ''.join('C' if lvl.object_at(x,2) else '.' if lvl.tile_at(x,2).__class__.__name__!='Wall' else '#' for x in range(lvl.width)))
print('Row3:', ''.join('C' if lvl.object_at(x,3) else '.' if lvl.tile_at(x,3).__class__.__name__!='Wall' else '#' for x in range(lvl.width)))
print('Can enter workshop at 2,2?', lvl.object_at(2,2) is None and lvl.tile_at(2,2).__class__.__name__!='Wall')
print('Tile 2,3:', type(lvl.tile_at(2,3)).__name__)
print('Tile 2,4:', type(lvl.tile_at(2,4)).__name__)
print('Object 3,2:', lvl.object_at(3,2))
print('Object 2,2:', lvl.object_at(2,2))
print('Object 4,2:', lvl.object_at(4,2))
print('Object 11,2:', lvl.object_at(11,2))
print('Object 12,2:', lvl.object_at(12,2))

# try simple path to workshop
possible = []
for d in DIRS:
    msg = lvl.move_player(d)
    possible.append((d, msg, lvl.player.x, lvl.player.y))
print('First moves:', possible)
