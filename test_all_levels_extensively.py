from levels_data import build_level1, build_level2, build_level3
from registry import PropertyRegistry

def test_level1():
    lvl = build_level1()
    print("--- LEVEL 1 TEST ---")
    assert PropertyRegistry.get("Platform", "isSolid") is True
    # Obstacle platform at (9, 5) is solid
    plat = lvl.object_at(9, 5)
    assert plat.is_blocking() is True

    # Move spare False block at (9, 2) into slot (7, 2)
    # Clear (7,2) by pushing True at (7,2) to (8,2)
    # Player moves to (6,1) -> (7,1) -> (7,2) pushes True to (8,2)
    # Then player pushes False at (9,2) left to (7,2)
    lvl.player.x, lvl.player.y = 8, 2
    lvl.move_player("d") # pushes False at (9,2) to (10,2) or (7,2)
    
    # Or simulate puzzle solve by placing statement directly:
    bpos = lvl.blocks_by_pos()
    false_block = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is False][0]
    true_block = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is True][0]
    false_block.x, false_block.y = 7, 2
    true_block.x, true_block.y = 10, 2
    lvl.recompile_circuits()

    assert PropertyRegistry.get("Platform", "isSolid") is False
    assert plat.is_blocking() is False
    print("Level 1 passed!")

def test_level2():
    lvl = build_level2()
    print("--- LEVEL 2 TEST ---")
    assert PropertyRegistry.get("Door", "isOpen") is False
    door = lvl.object_at(9, 5)
    assert door.is_blocking() is True

    # Swap spare True block into slot (7, 2)
    true_block = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is True][0]
    false_block = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is False][0]
    true_block.x, true_block.y = 7, 2
    false_block.x, false_block.y = 10, 2
    lvl.recompile_circuits()

    assert PropertyRegistry.get("Door", "isOpen") is True
    assert door.is_blocking() is False
    print("Level 2 passed!")

def test_level3():
    lvl = build_level3()
    print("--- LEVEL 3 TEST ---")
    trap = lvl.object_at(8, 5)
    plat = lvl.object_at(20, 5)
    assert PropertyRegistry.get("Trap", "isLethal") is True
    assert PropertyRegistry.get("Platform", "isSolid") is True
    assert trap.is_lethal() is True
    assert plat.is_blocking() is True

    # Solve Workshop A: Trap.isLethal = False
    trap_false = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is False and b.x < 12][0]
    trap_true = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is True and b.x < 12][0]
    trap_false.x, trap_false.y = 7, 2
    trap_true.x, trap_true.y = 10, 2
    lvl.recompile_circuits()

    assert PropertyRegistry.get("Trap", "isLethal") is False
    assert trap.is_lethal() is False

    # Solve Workshop B: Platform.isSolid = False
    plat_false = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is False and b.x > 12][0]
    plat_true = [b for b in lvl.dynamic_objects if getattr(b, 'value', None) is True and b.x > 12][0]
    plat_false.x, plat_false.y = 19, 2
    plat_true.x, plat_true.y = 22, 2
    lvl.recompile_circuits()

    assert PropertyRegistry.get("Platform", "isSolid") is False
    assert plat.is_blocking() is False
    print("Level 3 passed!")

if __name__ == "__main__":
    test_level1()
    test_level2()
    test_level3()
    print("\nALL LEVELS TESTED AND PASSED 100%!")
