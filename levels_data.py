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
from game_object import Platform, Door, Trap, HiddenBoom, BorderMine
from blocks import CodeBlock, CircuitLine, CLASS, PROP, OP, VALUE

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


def build_level1() -> Level:
    """
    Tutorial level. The path to the goal is broken: the circuit reads
    Path.solid = false, so the Path cell in the corridor is an open void
    and stepping into it makes the character vanish.
    Swap in the spare `true` block to seal the void into solid, walkable
    ground and cross to the goal.
    """
    W, H = 16, 7
    lvl = Level("1 - First Compile", W, H, DEFAULT_REGISTRY)
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
    lvl = Level("2 - Open Sesame", W, H, DEFAULT_REGISTRY)
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
    lvl = Level("3 - Two Statements", W, H, DEFAULT_REGISTRY)
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
    lvl = Level("4 - Spacious Statements", W, H, DEFAULT_REGISTRY)
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
    # it either.  Leaves the doorway at doorB open.
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


ALL_LEVELS = [build_level1, build_level2, build_level3, build_level4]
