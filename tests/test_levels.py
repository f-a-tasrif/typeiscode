import unittest
from blocks import CodeBlock
from levels_data import build_level1, build_level2, build_level3
from registry import PropertyRegistry
from game_object import Platform, Door, Trap


class TestLevels(unittest.TestCase):
    def test_level1_value_blocks_are_separate(self):
        lvl = build_level1()
        value_blocks = [
            obj for obj in lvl.dynamic_objects if isinstance(obj, CodeBlock) and obj.kind == "VALUE"
        ]

        positions = {(obj.x, obj.y) for obj in value_blocks}
        self.assertEqual(len(positions), len(value_blocks))
        self.assertEqual({obj.value for obj in value_blocks}, {False, True})

    def test_platform_solidity_live_update(self):
        lvl = build_level1()
        platform = [o for o in lvl.dynamic_objects if isinstance(o, Platform)][0]
        
        # Initially Platform isSolid is True -> blocking
        self.assertTrue(PropertyRegistry.get("Platform", "isSolid"))
        self.assertTrue(platform.is_blocking())

        # When Platform.isSolid becomes False -> non-solid / passable
        PropertyRegistry.set("Platform", "isSolid", False)
        self.assertFalse(platform.is_blocking())

    def test_door_is_open_live_update(self):
        lvl = build_level2()
        door = [o for o in lvl.dynamic_objects if isinstance(o, Door)][0]

        self.assertFalse(PropertyRegistry.get("Door", "isOpen"))
        self.assertTrue(door.is_blocking())

        PropertyRegistry.set("Door", "isOpen", True)
        self.assertFalse(door.is_blocking())

    def test_trap_is_lethal_live_update(self):
        lvl = build_level3()
        trap = [o for o in lvl.dynamic_objects if isinstance(o, Trap)][0]

        self.assertTrue(PropertyRegistry.get("Trap", "isLethal"))
        self.assertTrue(trap.is_lethal())

        PropertyRegistry.set("Trap", "isLethal", False)
        self.assertFalse(trap.is_lethal())


if __name__ == "__main__":
    unittest.main()
