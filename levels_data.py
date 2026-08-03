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
  * Inside the workshop sits a CircuitLine (4 slots: CLASS, PROPERTY,
    OPERATOR, VALUE) pre-loaded with a statement, plus a spare
    correction block with ample clearance (at least 1 empty grid space
    on surrounding sides) to be pushed Sokoban-style into the slot.
"""

from level import Level
from game_object import Platform, Door, Trap
from blocks import CodeBlock, CircuitLine, CLASS, PROP, OP, VALUE

DEFAULT_REGISTRY = {
    "Platform": {"isSolid": True},
    "Door": {"isOpen": False},
    "Trap": {"isLethal": True},
}


def build_level1() -> Level:
    """
    Tutorial level. A solid Platform blocks the route to the goal.
    The workshop circuit reads Platform.isSolid = true.
    Swap in the spare `false` block to make the platform non-solid/passable.
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

    slots = [(4, 2), (6, 2), (8, 2), (11, 2)]
    lvl.add_circuit(CircuitLine("Bridge Statement", slots))
    lvl.add_object(CodeBlock(4, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(6, 2, PROP, "isSolid"))
    lvl.add_object(CodeBlock(8, 2, OP, "="))
    lvl.add_object(CodeBlock(11, 2, VALUE, True))  # current state: solid/blocking

    lvl.add_object(CodeBlock(9, 2, VALUE, False))  # spare correction block to make it false (passable)

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

    slots = [(4, 2), (6, 2), (8, 2), (11, 2)]
    lvl.add_circuit(CircuitLine("Door Statement", slots))
    lvl.add_object(CodeBlock(4, 2, CLASS, "Door"))
    lvl.add_object(CodeBlock(6, 2, PROP, "isOpen"))
    lvl.add_object(CodeBlock(8, 2, OP, "="))
    lvl.add_object(CodeBlock(11, 2, VALUE, False))  # wrong -- needs to be True

    lvl.add_object(CodeBlock(2, 2, VALUE, True))  # spare correction block, kept separate

    lvl.recompile_circuits()
    return lvl


def build_level3() -> Level:
    """
    Two obstacles in sequence: a live Trap that must be disarmed
    (Trap.isLethal = false) and, further along, a solid Platform that
    must be made passable (Platform.isSolid = false). Two independent
    workshops, one per obstacle, each reachable strictly before its
    own obstacle's column.
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
    slotsA = [(4, 2), (6, 2), (8, 2), (11, 2)]
    circA = CircuitLine("Trap Statement", slotsA)
    lvl.add_circuit(circA)
    lvl.add_object(CodeBlock(4, 2, CLASS, "Trap"))
    lvl.add_object(CodeBlock(6, 2, PROP, "isLethal"))
    lvl.add_object(CodeBlock(8, 2, OP, "="))
    lvl.add_object(CodeBlock(11, 2, VALUE, True))    # wrong -- needs False
    lvl.add_object(CodeBlock(2, 2, VALUE, False))   # spare correction block

    # Bridge circuit in workshop B
    slotsB = [(16, 2), (18, 2), (20, 2), (23, 2)]
    circB = CircuitLine("Bridge Statement", slotsB)
    lvl.add_circuit(circB)
    lvl.add_object(CodeBlock(16, 2, CLASS, "Platform"))
    lvl.add_object(CodeBlock(18, 2, PROP, "isSolid"))
    lvl.add_object(CodeBlock(20, 2, OP, "="))
    lvl.add_object(CodeBlock(23, 2, VALUE, True))   # wrong -- needs False
    lvl.add_object(CodeBlock(14, 2, VALUE, False))  # spare correction block

    lvl.recompile_circuits()
    return lvl


ALL_LEVELS = [build_level1, build_level2, build_level3]
