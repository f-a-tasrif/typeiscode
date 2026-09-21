import unittest
from blocks import CodeBlock
from levels_data import build_level1, build_level2, build_level3, build_level4, ALL_LEVELS
from registry import PropertyRegistry
from game_object import Platform, Door, Trap, HiddenBoom
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

    def test_wall_solid_live_update(self):
        lvl = build_level1()
        wall = lvl.tile_at(1, 4)  # interior seal wall (border is mined, see below)

        self.assertTrue(PropertyRegistry.get("Wall", "solid"))
        self.assertTrue(wall.is_blocking())
        self.assertEqual(lvl.move_player("w"), "A wall blocks the way.")

        PropertyRegistry.set("Wall", "solid", False)
        self.assertFalse(wall.is_blocking())
        self.assertEqual(lvl.move_player("w"), "")
        self.assertEqual((lvl.player.x, lvl.player.y), (1, 4))

        PropertyRegistry.set("Wall", "solid", True)
        self.assertTrue(wall.is_blocking())

    def test_outer_border_is_mined(self):
        from game_object import BorderMine
        lvl = build_level1()
        mines = [o for o in lvl.dynamic_objects if isinstance(o, BorderMine)]
        # every outer-border cell is covered
        expected = (
            {(x, 0) for x in range(lvl.width)}
            | {(x, lvl.height - 1) for x in range(lvl.width)}
            | {(0, y) for y in range(lvl.height)}
            | {(lvl.width - 1, y) for y in range(lvl.height)}
        )
        self.assertEqual({(m.x, m.y) for m in mines}, expected)
        # mines stay lethal even when traps are disarmed
        PropertyRegistry.set("Trap", "isLethal", False)
        self.assertTrue(mines[0].is_lethal())
        # surfing the outer wall with Wall.solid=False goes BOOM
        PropertyRegistry.set("Wall", "solid", False)
        lvl.set_player(1, 5)
        self.assertIn("BOOM", lvl.move_player("a"))
        self.assertTrue(lvl.dead)

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

    def test_level4_spacious_workshop_layout(self):
        lvl = build_level4()
        door = [o for o in lvl.dynamic_objects if isinstance(o, Door)][0]
        hidden_booms = [o for o in lvl.dynamic_objects if isinstance(o, HiddenBoom)]
        hidden_boom = hidden_booms[0]
        plat = [o for o in lvl.dynamic_objects if isinstance(o, Platform)][0]

        # Two-statement structure: door + platform puzzles.
        self.assertEqual(len(lvl.circuits), 2)
        self.assertFalse(PropertyRegistry.get("Door", "isOpen"))
        self.assertTrue(PropertyRegistry.get("Platform", "isSolid"))
        self.assertTrue(door.is_blocking())
        self.assertEqual((hidden_boom.x, hidden_boom.y), (door.x + 1, door.y))
        self.assertTrue(hidden_boom.is_lethal())
        self.assertEqual(hidden_boom.glyph(), "    ")
        self.assertEqual(
            {(boom.x, boom.y) for boom in hidden_booms},
            {(9, 10), (13, 2), (13, 4), (13, 6), (13, 8), (25, 10)},
        )
        self.assertTrue(plat.is_blocking())
        wall_blocks = [
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "CLASS" and o.value == "Wall"
        ]
        self.assertEqual({(block.x, block.y) for block in wall_blocks}, {(10, 7)})
        solid_blocks = [
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "PROP" and o.value == "solid"
        ]
        self.assertEqual({(block.x, block.y) for block in solid_blocks}, {(10, 4)})

        # But the upper floor is much taller, giving every block room to
        # be pushed around and arranged freely.
        self.assertGreater(lvl.height, 7)

        # Spare correction blocks sit clear of anything on all sides.
        slots = {pos for c in lvl.circuits for pos in c.slot_positions}
        spares = [
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "VALUE"
            and (o.x, o.y) not in slots
        ]
        self.assertEqual(len(spares), 2)
        for spare in spares:
            self.assertNotIn((spare.x, spare.y), slots)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                self.assertIsNone(lvl.object_at(spare.x + dx, spare.y + dy))

        # Solving the door statement opens the door.
        door_true = next(
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "VALUE" and o.value is True
            and (o.x, o.y) == (9, 5)
        )
        door_false = next(
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "VALUE" and o.value is False
            and (o.x, o.y) == (7, 5)
        )
        door_true.x, door_true.y = 7, 5
        door_false.x, door_false.y = 10, 5
        lvl.recompile_circuits()
        self.assertFalse(door.is_blocking())

        # Crossing the opened door exposes the hidden explosive.
        lvl.set_player(door.x - 1, door.y)
        self.assertEqual(lvl.move_player("d"), "")
        self.assertIn("BOOM", lvl.move_player("d"))
        self.assertTrue(lvl.dead)

        plat_false = next(
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "VALUE" and o.value is False
            and (o.x, o.y) == (21, 5)
        )
        plat_true = next(
            o for o in lvl.dynamic_objects
            if isinstance(o, CodeBlock) and o.kind == "VALUE" and o.value is True
            and (o.x, o.y) == (19, 5)
        )
        plat_false.x, plat_false.y = 19, 5
        plat_true.x, plat_true.y = 22, 5
        lvl.recompile_circuits()
        self.assertFalse(plat.is_blocking())

    def test_level_index_bounds_and_completion(self):
        engine = GameEngine()
        self.assertEqual(engine.level_index, 0)
        self.assertTrue(engine.next_level())
        self.assertEqual(engine.level_index, 1)
        self.assertTrue(engine.next_level())
        self.assertEqual(engine.level_index, 2)
        self.assertTrue(engine.next_level())
        self.assertEqual(engine.level_index, 3)
        # Completing final level should return False and NOT increment level_index further
        self.assertFalse(engine.next_level())
        self.assertEqual(engine.level_index, 3)
        self.assertLess(engine.level_index, len(ALL_LEVELS))

        # Repeated calls to next_level should stay capped
        self.assertFalse(engine.next_level())
        self.assertEqual(engine.level_index, 3)


if __name__ == "__main__":
    unittest.main()
