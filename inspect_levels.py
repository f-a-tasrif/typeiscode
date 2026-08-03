import sys
sys.path.insert(0, '.')
from levels_data import build_level1
from blocks import CodeBlock

lvl = build_level1()
vals = [o for o in lvl.dynamic_objects if isinstance(o, CodeBlock) and o.kind == 'VALUE']
print([(o.x, o.y, o.value) for o in vals])
print('unique_positions', len({(o.x, o.y) for o in vals}))
