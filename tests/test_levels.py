import unittest
from blocks import CodeBlock
from levels_data import build_level1, build_level2, build_level3, ALL_LEVELS
from registry import PropertyRegistry
from game_object import Platform, Door, Trap
from gui_engine import GUIEngine
from engine import GameEngine


class TestLevels(unittest.TestCase):
    def test_level1_value_blocks_are_separate(self):
        lvl = build_level1()
        value_blocks = [
            obj for obj in lvl.dynamic_objects if isinstance(obj, CodeBlock) and obj.kind == "VALUE"
        ]

        positions = {(obj.x, obj.y) for obj in value_blocks}
        self.assertEqual(len(positions), len(value_blocks))
        self.assertEqual({obj.value for obj in value_blocks}, {False, True})

    def test_adjacent_blocks_do_not_chain_push(self):
        lvl = build_level1()
        blocks = [obj for obj in lvl.dynamic_objects if isinstance(obj, CodeBlock)]
        first, second = blocks[:2]
        first.x, first.y = 3, 2
        second.x, second.y = 4, 2
        lvl.set_player(2, 2)

        message = lvl.move_player("d")

        self.assertEqual(message, "Can't push -- something is already there.")
        self.assertEqual((first.x, first.y), (3, 2))
        self.assertEqual((second.x, second.y), (4, 2))
        self.assertEqual((lvl.player.x, lvl.player.y), (2, 2))

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

    def test_statement_can_compile_away_from_highlight_and_reverts_when_broken(self):
        lvl = build_level2()
        door = [o for o in lvl.dynamic_objects if isinstance(o, Door)][0]
        blocks = [obj for obj in lvl.dynamic_objects if isinstance(obj, CodeBlock)]

        # Assemble Door.isOpen = true away from the highlighted slots.
        class_block = next(obj for obj in blocks if obj.kind == "CLASS")
        prop_block = next(obj for obj in blocks if obj.kind == "PROP")
        op_block = next(obj for obj in blocks if obj.kind == "OP")
        true_block = next(obj for obj in blocks if obj.kind == "VALUE" and obj.value is True)
        for block, x in zip((class_block, prop_block, op_block, true_block), range(9, 13)):
            block.x, block.y = x, 3
        lvl.recompile_circuits()
        self.assertFalse(door.is_blocking())

        # Breaking the live statement closes the door; restoring it reopens it.
        true_block.x, true_block.y = 13, 3
        lvl.recompile_circuits()
        self.assertTrue(door.is_blocking())
        true_block.x, true_block.y = 12, 3
        lvl.recompile_circuits()
        self.assertFalse(door.is_blocking())

    def test_trap_is_lethal_live_update(self):
        lvl = build_level3()
        trap = [o for o in lvl.dynamic_objects if isinstance(o, Trap)][0]

        self.assertTrue(PropertyRegistry.get("Trap", "isLethal"))
        self.assertTrue(trap.is_lethal())

        PropertyRegistry.set("Trap", "isLethal", False)
        self.assertFalse(trap.is_lethal())

    def test_level_index_bounds_and_completion(self):
        engine = GameEngine()
        self.assertEqual(engine.level_index, 0)
        self.assertTrue(engine.next_level())
        self.assertEqual(engine.level_index, 1)
        self.assertTrue(engine.next_level())
        self.assertEqual(engine.level_index, 2)
        # Completing final level should return False and NOT increment level_index further
        self.assertFalse(engine.next_level())
        self.assertEqual(engine.level_index, 2)
        self.assertLess(engine.level_index, len(ALL_LEVELS))

        # Repeated calls to next_level should stay capped
        self.assertFalse(engine.next_level())
        self.assertEqual(engine.level_index, 2)


if __name__ == "__main__":
    unittest.main()
