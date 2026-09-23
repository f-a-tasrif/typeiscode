"""
game_object.py
--------------
Core OOP hierarchy for "Type Is Code".

Every entity in the world (the player, platforms, doors, code blocks...)
derives from the abstract base class GameObject. Subclasses override
is_blocking() / is_lethal() / on_tick() to express *polymorphic* behavior
that is re-evaluated every single game tick by reading a live, mutable
property dictionary (see registry.py). This is the technical backbone
that mirrors the puzzle-design concept: rewriting a class's properties
on the circuit line instantly changes how every instance of that class
behaves, because behavior is never hard-coded -- it is looked up.
"""

from __future__ import annotations
from registry import PropertyRegistry


class GameObject:
    """Abstract base class for every entity that can exist on the grid."""

    #: 4-character glyph used by the renderer. Subclasses override this.
    GLYPH = "????"

    def __init__(self, x: int, y: int, movable: bool = False):
        self.x = x
        self.y = y
        self.movable = movable  # can the player push this object?

    # -- polymorphic behavior, re-checked every tick -----------------
    def is_blocking(self) -> bool:
        """Whether this object physically stops the player from entering."""
        return False

    def is_lethal(self) -> bool:
        """Whether stepping on this object ends the game."""
        return False

    def is_win(self) -> bool:
        """Whether stepping on this object wins the level."""
        return False

    def on_tick(self, world) -> None:
        """Hook called once per tick; base does nothing."""
        return None

    def glyph(self) -> str:
        return self.GLYPH

    def pos(self):
        return (self.x, self.y)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.x},{self.y})"


class Wall(GameObject):
    """A boundary tile whose solidity is controlled by Wall.solid."""
    GLYPH = "####"

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Wall", "solid", True))


class Floor(GameObject):
    """Purely cosmetic empty tile."""
    GLYPH = "    "


class Goal(GameObject):
    GLYPH = "GOAL"

    def is_win(self) -> bool:
        return True


class Player(GameObject):
    GLYPH = "@@@@"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)


class Platform(GameObject):
    """
    The walkable path cell (shown as `Path.` on the circuit line) whose
    state is governed by the live property dictionary: Path.solid.

      * Path.solid = True  -> the void trap is REMOVED: the cell is plain
        walkable floor, the character crosses it safely.
      * Path.solid = False -> the path is a VOID.  It never blocks (there
        is simply no floor) -- stepping onto it drops the character into
        the void, which ends the run with the character invisible.

    Recompiling the statement flips between the two states, so changing
    the logic back makes the trap reappear.
    """
    GLYPH_VOID = "VOID"
    GLYPH_SAFE = "    "  # reads as plain floor in the terminal renderer

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_void(self) -> bool:
        """True while Path.solid = False: the cell is an open void."""
        return not bool(PropertyRegistry.get("Platform", "isSolid", True))

    def is_blocking(self) -> bool:
        # Never blocks: solid=True is walkable floor, solid=False is a hole.
        return False

    def is_lethal(self) -> bool:
        # Falling into the void ends the run.
        return self.is_void()

    def glyph(self) -> str:
        return self.GLYPH_VOID if self.is_void() else self.GLYPH_SAFE


class Door(GameObject):
    """A door that blocks unless Door.isOpen is True."""
    GLYPH_CLOSED = "DOOR"
    GLYPH_OPEN = "open"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        return not bool(PropertyRegistry.get("Door", "isOpen", False))

    def glyph(self) -> str:
        return self.GLYPH_OPEN if not self.is_blocking() else self.GLYPH_CLOSED


class Trap(GameObject):
    """A trap that is lethal unless Trap.isLethal is set to False."""
    GLYPH_ON = "TRAP"
    GLYPH_OFF = "trap"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_lethal(self) -> bool:
        return bool(PropertyRegistry.get("Trap", "isLethal", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_lethal() else self.GLYPH_OFF


class HiddenBoom(Trap):
    """An armed trap that is invisible until the player steps on it."""

    def glyph(self) -> str:
        # The renderer treats an all-space glyph as an empty floor tile.
        return "    "


class BorderMine(GameObject):
    """Invisible perimeter explosive: always lethal, never blocking.

    Planted on every outer-border wall cell so that Wall.solid = False
    (passable interior walls) cannot be abused to surf around the outer
    wall and skip the puzzle. Independent of Trap.isLethal on purpose.
    """

    GLYPH = "####"  # terminal keeps showing a wall

    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return True

    def glyph(self) -> str:
        return "####"
