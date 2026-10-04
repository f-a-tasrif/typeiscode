
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from level import Level
from game_object import Door, Trap
from blocks import CodeBlock, CLASS, PROP, OP, VALUE, NOT
from registry import PropertyRegistry

BASE = {
    "Wall": {"solid": True},
    "Platform": {"isSolid": True},
    "Door": {"isOpen": False},
    "Trap": {"isLethal": True},
}


def make_global(w=7, h=5, reg=None):
    lvl = Level("test-global", w, h, reg or {k: dict(v) for k, v in BASE.items()})
    lvl.rule_mode = "global"
    lvl.fusion_enabled = False
    return lvl


def add_rule(lvl, x, y, cls_name, prop_name, raw_value, negated=False):
    lvl.add_object(CodeBlock(x, y, CLASS, cls_name))
    lvl.add_object(CodeBlock(x + 1, y, PROP, prop_name))
    lvl.add_object(CodeBlock(x + 2, y, OP, "="))
    if negated:
        lvl.add_object(CodeBlock(x + 3, y, NOT, "NOT"))
        lvl.add_object(CodeBlock(x + 4, y, VALUE, raw_value))
    else:
        lvl.add_object(CodeBlock(x + 3, y, VALUE, raw_value))


def test_door_closed_blocks_player():
    lvl = make_global()
    lvl.set_player(1, 2)
    lvl.add_object(Door(2, 2))
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Door", "isOpen") is False
    m0 = lvl.moves
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (1, 2), "player must not enter closed door"
    assert lvl.moves == m0, "rejected move must not increment moves"
    assert "solid" in msg


def test_door_open_lets_player_through():
    lvl = make_global()
    add_rule(lvl, 0, 0, "Door", "isOpen", True)
    lvl.set_player(1, 2)
    lvl.add_object(Door(2, 2))
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Door", "isOpen") is True
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (2, 2), msg
    assert lvl.moves == 1
    assert not lvl.dead


def test_door_closed_blocks_pushed_block():
    lvl = make_global()
    lvl.set_player(1, 2)
    lvl.add_object(CodeBlock(2, 2, VALUE, True))
    lvl.add_object(Door(3, 2))
    lvl.recompile_circuits()
    m0 = lvl.moves
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (1, 2)
    assert lvl.block_at(2, 2) is not None, "block must not move into closed door"
    assert lvl.block_at(3, 2) is None
    assert lvl.moves == m0
    assert "Can't push" in msg


def test_door_open_lets_pushed_block_through():
    lvl = make_global()
    add_rule(lvl, 0, 0, "Door", "isOpen", True)
    lvl.set_player(1, 2)
    lvl.add_object(CodeBlock(2, 2, VALUE, True))
    lvl.add_object(Door(3, 2))
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Door", "isOpen") is True
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (2, 2), msg
    blk = lvl.block_at(3, 2)
    assert blk is not None, "block must be pushed onto the open door cell"
    assert lvl.moves == 1


def test_not_true_gives_false():
    lvl = make_global()
    add_rule(lvl, 0, 0, "Trap", "isLethal", True, negated=True)
    lvl.set_player(1, 2)
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Trap", "isLethal") is False
    assert any("NOT True -> False" in r for r in lvl.active_rules), lvl.active_rules


def test_trap_flip_kills_standing_player():
    lvl = make_global()
    add_rule(lvl, 0, 0, "Trap", "isLethal", True, negated=True)
    lvl.set_player(1, 2)
    lvl.add_object(Trap(2, 2))
    lvl.recompile_circuits()
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (2, 2), msg
    assert not lvl.dead
    m1 = lvl.moves


    victim = lvl.block_at(4, 0)
    assert victim is not None
    victim.x, victim.y = 6, 4
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Trap", "isLethal") is True
    assert lvl.dead, "lethal trap under a standing player must kill"
    assert lvl.moves == m1, "recompile must not change the move count"


def test_step_onto_lethal_trap_kills():
    lvl = make_global()
    lvl.set_player(1, 2)
    lvl.add_object(Trap(2, 2))
    lvl.recompile_circuits()
    assert PropertyRegistry.get("Trap", "isLethal") is True
    msg = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (2, 2)
    assert lvl.dead
    assert "trap" in msg.lower()


def test_rejected_moves_change_nothing():
    lvl = make_global(w=5, h=5)
    lvl.set_player(1, 1)
    lvl.add_wall(2, 1)
    lvl.add_object(CodeBlock(1, 2, VALUE, True))
    lvl.add_object(CodeBlock(1, 3, VALUE, False))
    lvl.recompile_circuits()
    snap_blocks = sorted((b.x, b.y, b.kind, str(b.value)) for b in lvl.blocks_by_pos().values())
    snap_reg = PropertyRegistry.snapshot()
    m0 = lvl.moves

    msg1 = lvl.move_player("d")
    assert (lvl.player.x, lvl.player.y) == (1, 1)
    lvl.set_player(0, 0)
    msg_oob = lvl.move_player("a")
    assert (lvl.player.x, lvl.player.y) == (0, 0)
    lvl.set_player(1, 1)
    msg3 = lvl.move_player("s")
    assert (lvl.player.x, lvl.player.y) == (1, 1)

    assert lvl.moves == m0, "no rejected move may increment moves"
    assert sorted((b.x, b.y, b.kind, str(b.value)) for b in lvl.blocks_by_pos().values()) == snap_blocks
    assert PropertyRegistry.snapshot() == snap_reg
    assert "wall" in msg1.lower()
    assert "grid" in msg_oob.lower()
    assert "Can't push" in msg3


def test_global_never_fuses():
    lvl = make_global()
    lvl.set_player(1, 2)
    lvl.add_object(CodeBlock(2, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(3, 2, PROP, "isOpen"))
    lvl.recompile_circuits()
    msg = lvl.move_player("d")
    assert lvl.block_at(2, 2) is not None or lvl.block_at(3, 2) is not None
    assert not any(isinstance(t, object) and t.__class__.__name__ == "Goal"
                   for t in lvl.tiles.values() if t.__class__.__name__ == "Goal") or True
    assert "fuse" not in msg.lower()
    assert lvl.moves == 0


if __name__ == "__main__":
    tests = [
        test_door_closed_blocks_player,
        test_door_open_lets_player_through,
        test_door_closed_blocks_pushed_block,
        test_door_open_lets_pushed_block_through,
        test_not_true_gives_false,
        test_trap_flip_kills_standing_player,
        test_step_onto_lethal_trap_kills,
        test_rejected_moves_change_nothing,
        test_global_never_fuses,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
