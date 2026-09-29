"""
levels_data.py
--------------
Concrete puzzle layouts. Each build_levelN() function returns a fresh
Level instance (levels are rebuilt from scratch on restart / on
progression so the PropertyRegistry and block positions always start
clean).

Layout pattern used by every level ("workshop + corridor"):
  * Row `corridor_y` is the main walkway from the player's start to the
    goal. Exactly one obstacle (Platform / Door / Trap) sits in it,
    whose live property decides whether it blocks / harms the player.
  * A 3-tile deep "workshop" room (rows y=1,2,3) is reachable through a
    doorway placed BEFORE the obstacle's column, so there is never a way
    to bypass the obstacle by wandering through the workshop.
  * Inside the workshop sits a CircuitLine (4 contiguous slots: CLASS,
    PROPERTY, OPERATOR, VALUE) pre-loaded with a statement, plus a spare
    correction block with ample clearance (at least 1 empty grid space
    on surrounding sides) to be pushed Sokoban-style into the slot.
"""

from level import Level
from game_object import Platform, Door, Trap, HiddenBoom, BorderMine, Floor
from blocks import CodeBlock, CircuitLine, CLASS, PROP, OP, VALUE, NOT
from maps_data import MAPS

DEFAULT_REGISTRY = {
    "Wall": {"solid": True},
    # Path.solid = False by default: every Path./Platform cell starts out
    # as an open void (the trap).  Only a compiled Path.solid = True turns
    # it back into walkable ground — and breaking the statement makes the
    # void reappear.
    "Platform": {"isSolid": False},
    "Door": {"isOpen": False},
    "Trap": {"isLethal": True},
}

RULES_REGISTRY = {
    "Wall": {"solid": True},
    # Like level 1: the path starts as an open void (pit) and only a
    # compiled Path.solid = True seals it -- except the HTML solutions
    # for these maps open the tables instead of sealing them, so the
    # T cells stay deadly once opened (see tests/test_maps.py).
    "Platform": {"isSolid": False},
    "Door": {"isOpen": False},
    "Trap": {"isLethal": True},
}

# -- data-driven global levels (levels 5+) ------------------------------
# Token text -> (kind, value) for CodeBlocks placed by _build_from_map.
MAP_TOKENS: dict[str, tuple[str, object]] = {
    "Path.": (CLASS, "Platform"),
    "Door.": (CLASS, "Door"),
    "Trap.": (CLASS, "Trap"),
    "solid": (PROP, "isSolid"),
    "open": (PROP, "isOpen"),
    "lethal": (PROP, "isLethal"),
    "=": (OP, "="),
    "True": (VALUE, True),
    "False": (VALUE, False),
    "NOT": (NOT, "NOT"),
}


def _build_from_map(name: str, rows: list[str], start: tuple[int, int],
                    tokens: list[tuple[int, int, str]]) -> Level:
    """Build a global-rules level from HTML map data.

    `rows` are ASCII map rows, `start` is (row, col), `tokens` are
    (row, col, text).  The game uses (x, y) = (col, row).  No wall
    border is added (nothing in these levels can make walls passable,
    so no BorderMines are needed) and no CircuitLine objects are used:
    rules compile from statements found anywhere on the board.
    """
    W, H = len(rows[0]), len(rows)
    lvl = Level(name, W, H, RULES_REGISTRY)
    lvl.rule_mode = "global"
    lvl.fusion_enabled = False
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                lvl.add_wall(x, y)
            elif ch == "T":
                # Level 1's own path trap: safe floor while
                # Path.solid = True, lethal void while False.
                lvl.add_object(Platform(x, y))
            elif ch == "D":
                lvl.add_object(Door(x, y))
            elif ch == "X":
                lvl.add_object(Trap(x, y))
            elif ch == "F":
                lvl.set_goal(x, y)
            # "." = nothing
    sr, sc = start
    lvl.set_player(sc, sr)
    for tr, tc, text in tokens:
        kind, value = MAP_TOKENS[text]
        lvl.add_object(CodeBlock(tc, tr, kind, value))
    lvl.recompile_circuits()
    return lvl


def _flip_value_block(lvl: Level, entry: dict, text: str) -> None:
    """Toggle a VALUE token block (False<->True) in a built level.

    `maps_data.py` stays a faithful port of the HTML; deliberate
    deviations live here. Recompiles afterwards.
    """
    for tr, tc, t in entry["tokens"]:
        if t == text:
            blk = lvl.block_at(tc, tr)
            assert blk is not None and blk.kind == VALUE, (tr, tc, t)
            assert isinstance(blk.value, bool), (tr, tc, t)
            blk.value = not blk.value
            lvl.recompile_circuits()
            return
    raise AssertionError(f"token {text!r} not found")


def build_level1() -> Level:
    """
    Tutorial level. The path to the goal is broken: the circuit reads
    Path.solid = false, so the Path cell in the corridor is an open void
    and stepping into it makes the character vanish.
    Swap in the spare `true` block to seal the void into solid, walkable
    ground and cross to the goal.
    """
    W, H = 16, 7
    lvl = Level("1", W, H, DEFAULT_REGISTRY)
    lvl.add_wall_border()
    lvl.set_player(1, 5)
    lvl.set_goal(14, 5)

    # seal row 4 except a doorway at x=2 (before the obstacle at x=9)
    for x in range(1, W - 1):
        if x != 2:
            lvl.add_wall(x, 4)

    lvl.add_object(Platform(9, 5))

    slots = [(4, 2), (5, 2), (6, 2), (7, 2)]
    lvl.add_circuit(CircuitLine("Bridge Statement", slots))
    lvl.add_object(CodeBlock(4, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(5, 2, PROP, "isSolid"))
    lvl.add_object(CodeBlock(6, 2, OP, "="))
    lvl.add_object(CodeBlock(7, 2, VALUE, False))  # current state: the path is a void

    lvl.add_object(CodeBlock(9, 2, VALUE, True))  # spare correction block: Path.solid = True seals the void

    lvl.recompile_circuits()
    return lvl


def build_level2() -> Level:
    """
    Introduces Door. A closed Door blocks the corridor; the workshop
    circuit reads Door.isOpen = false. Swap in the spare `true` block
    to open it.
    """
    W, H = 16, 7
    lvl = Level("2", W, H, DEFAULT_REGISTRY)
    lvl.add_wall_border()
    lvl.set_player(1, 5)
    lvl.set_goal(14, 5)

    for x in range(1, W - 1):
        if x != 2:
            lvl.add_wall(x, 4)

    lvl.add_object(Door(9, 5))

    slots = [(4, 2), (5, 2), (6, 2), (7, 2)]
    lvl.add_circuit(CircuitLine("Door Statement", slots))
    lvl.add_object(CodeBlock(4, 2, CLASS, "Door"))
    lvl.add_object(CodeBlock(5, 2, PROP, "isOpen"))
    lvl.add_object(CodeBlock(6, 2, OP, "="))
    lvl.add_object(CodeBlock(7, 2, VALUE, False))  # wrong -- needs to be True

    lvl.add_object(CodeBlock(9, 2, VALUE, True))  # spare correction block, kept separate

    lvl.recompile_circuits()
    return lvl


def build_level3() -> Level:
    """
    Two obstacles in sequence: a live Trap that must be disarmed
    (Trap.isLethal = false) and, further along, a void in the path that
    must be sealed into walkable ground (Path.solid = true). Two
    independent workshops, one per obstacle, each reachable strictly
    before its own obstacle's column.
    """
    W, H = 28, 7
    lvl = Level("3", W, H, DEFAULT_REGISTRY)
    lvl.add_wall_border()
    lvl.set_player(1, 5)
    lvl.set_goal(26, 5)

    doorA, doorB = 2, 14
    obstacleA, obstacleB = 8, 20

    # row 4: only two doorways, each strictly before its own obstacle
    for x in range(1, W - 1):
        if x not in (doorA, doorB):
            lvl.add_wall(x, 4)

    # dividing wall between workshop rooms
    for y in range(1, 4):
        lvl.add_wall(12, y)

    lvl.add_object(Trap(obstacleA, 5))
    lvl.add_object(Platform(obstacleB, 5))

    # Trap circuit in workshop A
    slotsA = [(4, 2), (5, 2), (6, 2), (7, 2)]
    circA = CircuitLine("Trap Statement", slotsA)
    lvl.add_circuit(circA)
    lvl.add_object(CodeBlock(4, 2, CLASS, "Trap"))
    lvl.add_object(CodeBlock(5, 2, PROP, "isLethal"))
    lvl.add_object(CodeBlock(6, 2, OP, "="))
    lvl.add_object(CodeBlock(7, 2, VALUE, True))    # wrong -- needs False
    lvl.add_object(CodeBlock(9, 2, VALUE, False))   # spare correction block

    # Bridge circuit in workshop B
    slotsB = [(16, 2), (17, 2), (18, 2), (19, 2)]
    circB = CircuitLine("Bridge Statement", slotsB)
    lvl.add_circuit(circB)
    lvl.add_object(CodeBlock(16, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(17, 2, PROP, "isSolid"))
    lvl.add_object(CodeBlock(18, 2, OP, "="))
    lvl.add_object(CodeBlock(19, 2, VALUE, False))  # the path ahead is a void -- needs True
    lvl.add_object(CodeBlock(21, 2, VALUE, True))   # spare correction block

    lvl.recompile_circuits()
    return lvl


def build_level4() -> Level:
    """
    Swap the values (global rules).  Intended solution: push False down
    out of the Door rule (registry reverts to Door.open = False),
    carry it left and up into the Trap rule (Trap.lethal = False),
    push True left into the empty Door slot (Door.open = True), drop
    back to the corridor and cross the harmless trap through the open
    door to the flag.  Teaches rule reversion and that a stray token
    after the value is ignored.
        """
    e = MAPS[3]
    return _build_from_map("7",
                            e["rows"], e["start"], e["tokens"])


def build_level5() -> Level:
    """
    Three rooms with a NOT vault and a trap (global rules).  Intended
    solution: True down into the Path rule (Path.solid = True -- safe
    floor), True up into the Door rule (door opens), cross the middle
    room and drop through a table gap into the vault, push NOT up and
    right into the Trap rule slot, push True up beside it (Trap.lethal
    = NOT True = False), cross the harmless trap to the flag.
    Introduces the NOT token.  (The HTML map has a False feeding the
    Path rule; here it is a True so the tables seal instead of opening
    into voids.)
    """
    e = MAPS[1]
    lvl = _build_from_map("5",
                          e["rows"], e["start"], e["tokens"])
    _flip_value_block(lvl, e, "False")
    return lvl


def build_level6() -> Level:
    """
    Serpentine vault (global rules).  Intended solution: push the first
    NOT up into the Path rule (Path.solid = NOT True = False -- the gap
    table becomes a void), walk in, push the second NOT up through the
    wall opening into the Door rule, then push False up beside it
    (Door.open = NOT False = True) and walk through the door to the
    flag.  Both Path and Door rules use NOT.
    """
    e = MAPS[2]
    lvl = _build_from_map("6",
                          e["rows"], e["start"], e["tokens"])
    # The first room's spare True is a False here (a decoy next to the
    # Path slot; the solution still feeds the rule with NOT).
    _flip_value_block(lvl, e, "True")
    return lvl


def build_level7() -> Level:
    """
    Four chambers, three gates (global rules, 25x9).  Longest chain:
    True up into the Door rule (opens), True right through the door
    and down into the Path rule (Path.solid = True -- safe floor),
    True down and right through the sealed table cell into room 3,
    NOT up into the Trap slot, True up beside it (Trap.lethal = NOT
    True = False), cross the harmless trap to the flag.  (The HTML
    map feeds the Path rule with a False; here it is a True.)
    """
    e = MAPS[4]
    lvl = _build_from_map("8",
                          e["rows"], e["start"], e["tokens"])
    _flip_value_block(lvl, e, "False")
    return lvl


def build_level8() -> Level:
    """
    Same design as level 3 (two obstacles in sequence, each with its own
    workshop) but with a much taller upper floor: the workshop room grows
    from 3 rows of play space to 8, so every block can be pushed, spun
    around, and re-arranged freely before being slotted in.  Both
    statements still need fixing: Door.isOpen = true and
    Path.solid = true (sealing the void back into walkable ground).  The rooms' contents are exchanged
    relative to level 3: workshop A (first room) now holds the
    Platform/Bridge statement guarding the obstacle at x=8, while
    workshop B (second room) holds the Door statement guarding the
    obstacle at x=20 -- so each circuit still sits in the room reached
    strictly before its own obstacle.

    The bottom wall of the second workshop is mined exactly like the
    outer border (BorderMine inside every wall cell), so even
    Wall.solid = False cannot walk through it.  That seals off the
    original corridor GOAL -- its only safe approach is wall cell
    (26, 9) -- so the level is finished by fusing a new GOAL from the
    Path. and open tokens: they fuse the moment they are put together
    (one contact, no pressing); the original flag disappears the moment
    the new one blooms (only one flag exists at a time).
    """
    W, H = 28, 12
    lvl = Level("8 - If one path closes, another opens. ", W, H, DEFAULT_REGISTRY)
    lvl.add_wall_border()
    lvl.set_player(1, 10)
    lvl.set_goal(26, 10)

    doorA, doorB = 2, 14
    obstacleA, obstacleB = 8, 20

    # row 9 (seal): only two doorways, each strictly before its own obstacle
    for x in range(1, W - 1):
        if x not in (doorA, doorB):
            lvl.add_wall(x, 9)

    # The bottom wall of the second workshop gets BorderMine booms inside
    # its cells, same as the outer wall: with Wall.solid = False the player
    # still dies trying to walk through it, and blocks can't be pushed into
    # it either. Leaves the doorway at doorB open.
    for x in range(13, W - 1):
        if x != doorB:
            lvl.add_object(BorderMine(x, 9))

    # dividing wall between workshop rooms, now spanning the taller room
    for y in range(1, 9):
        lvl.add_wall(12, y)

    # The first obstacle (first room's trap) is now the Platform; the
    # second one (second room's trap) is now the Door.
    lvl.add_object(Platform(obstacleA, 10))
    # The floor directly after the first obstacle conceals an armed explosive.
    lvl.add_object(HiddenBoom(obstacleA + 1, 10))
    # A hidden explosive seals the direct corridor approach to the goal.
    lvl.add_object(HiddenBoom(25, 10))
    lvl.add_object(Door(obstacleB, 10))

    # Bridge circuit in workshop A (slots near mid-room for generous clearance)
    slotsA = [(4, 5), (5, 5), (6, 5), (7, 5)]
    circA = CircuitLine("Bridge Statement", slotsA)
    lvl.add_circuit(circA)
    lvl.add_object(CodeBlock(4, 5, CLASS, "Platform"))
    lvl.add_object(CodeBlock(5, 5, PROP, "isSolid"))
    lvl.add_object(CodeBlock(6, 5, OP, "="))
    lvl.add_object(CodeBlock(7, 5, VALUE, False))  # the path ahead is a void -- needs True
    lvl.add_object(CodeBlock(9, 5, VALUE, True))   # spare correction block
    lvl.add_object(CodeBlock(10, 7, CLASS, "Wall"))  # spare Wall token, kept in the first room

    # Door circuit in workshop B
    slotsB = [(16, 5), (17, 5), (18, 5), (19, 5)]
    circB = CircuitLine("Door Statement", slotsB)
    lvl.add_circuit(circB)
    lvl.add_object(CodeBlock(16, 5, CLASS, "Door"))
    lvl.add_object(CodeBlock(17, 5, PROP, "isOpen"))
    lvl.add_object(CodeBlock(18, 5, OP, "="))
    lvl.add_object(CodeBlock(19, 5, VALUE, False))  # wrong -- needs True
    lvl.add_object(CodeBlock(21, 5, VALUE, True))   # spare correction block

    lvl.recompile_circuits()
    return lvl


ALL_LEVELS = [build_level1, build_level2, build_level3, build_level4,
              build_level5, build_level6, build_level7, build_level8]
