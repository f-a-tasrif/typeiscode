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
    """Immovable, always-solid boundary."""
    GLYPH = "####"

    def is_blocking(self) -> bool:
        return True


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
    A bridge/wall segment whose solidity is entirely governed by the
    live property dictionary: Platform.isSolid.
    This is the canonical example from the design doc.
    """
    GLYPH_SOLID = "PLAT"
    GLYPH_GHOST = "plat"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        # Platform is solid (blocks movement) when Platform.isSolid is True.
        # When Platform.isSolid is False, it is non-solid / passable.
        return bool(PropertyRegistry.get("Platform", "isSolid", True))

    def glyph(self) -> str:
        return self.GLYPH_SOLID if self.is_blocking() else self.GLYPH_GHOST


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
