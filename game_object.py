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


class Stone(GameObject):
    """A stone block that is blocking while Stone.solid = True.
    While False the stone vanishes (plain floor) and reappears
    as soon as the logic flips back, like SealWall."""
    GLYPH_ON = "STON"
    GLYPH_OFF = "    "

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Stone", "solid", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_blocking() else self.GLYPH_OFF


class SealWall(GameObject):
    """A wall cell that is blocking while Seal.active = True, open while False.
    Acts like a Wall when sealed, like a Floor when unsealed."""
    GLYPH_SEALED = "SEAL"
    GLYPH_OPEN = "    "

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal", "active", True))

    def is_lethal(self) -> bool:
        return False

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Warp(GameObject):
    """An invisible portal tile. Teleports the player to its paired Warp.
    Blocks cannot be pushed onto a Warp (enforced in level.py).
    The glyph is blank so it renders as floor."""
    GLYPH = "    "

    def __init__(self, x, y, pair_x: int, pair_y: int):
        super().__init__(x, y, movable=False)
        self.pair_x = pair_x
        self.pair_y = pair_y

    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return False


class HiddenBoom(Trap):
    """An armed trap that is invisible until the player steps on it."""

    def glyph(self) -> str:
        # The renderer treats an all-space glyph as an empty floor tile.
        return "    "


class HardMine(GameObject):
    """An always-lethal mine that never disarms (map8 `H` stays armed).

    Unlike HiddenBoom (lethal only while Trap.isLethal), this kills
    regardless of the trap rule. Blocks can never be pushed onto it.
    Renders with the same bomb art as a mine.
    """

    GLYPH = "MINE"

    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return True

    def glyph(self) -> str:
        return self.GLYPH


class LatchDoor(GameObject):
    """Pink latch door: blocks while Latch.isOpen is False (like Door)."""
    GLYPH_CLOSED = "LTCH"
    GLYPH_OPEN = "open"

    def is_blocking(self) -> bool:
        return not bool(PropertyRegistry.get("Latch", "isOpen", False))

    def glyph(self) -> str:
        return self.GLYPH_OPEN if not self.is_blocking() else self.GLYPH_CLOSED


class LaserDoor(GameObject):
    """Laser beams: blocks while Laser.beams is True (like Stone).

    Touching live beams vaporises the character (ash death) instead of
    merely blocking: is_lethal() is True while the beams are on, and the
    level movers kill the player on entry (see level.py)."""

    GLYPH_ON = "LASR"
    GLYPH_OFF = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Laser", "beams", True))

    def is_lethal(self) -> bool:
        return bool(PropertyRegistry.get("Laser", "beams", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_blocking() else self.GLYPH_OFF


class Seal2Wall(SealWall):
    """Teal seal ring: blocks while Seal2.active is True."""
    GLYPH_SEALED = "SL2"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal2", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal3Wall(SealWall):
    """Amber seal ring: blocks while Seal3.active is True."""
    GLYPH_SEALED = "SL3"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal3", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal4Wall(SealWall):
    """Green seal ring (Map17 Gallery): blocks while Seal4.active is True."""
    GLYPH_SEALED = "SL4"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal4", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal5Wall(SealWall):
    """Pink seal ring (Map17 Vault): blocks while Seal5.active is True."""
    GLYPH_SEALED = "SL5"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal5", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal6Wall(SealWall):
    """Sky seal ring (Map17 Vault/Forge chute): blocks while Seal6.active."""
    GLYPH_SEALED = "SL6"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal6", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class LeverPedestal(GameObject):
    """Lever base tile (Map17 V/U/N/K): always solid, like the HTML's LEV.

    Reversible: while ``<LeverN>.active`` is True the lever fires once and
    shoves the token directly below it one cell down, leaving a single
    LeverWall behind at the vacated cell (see Level._fire_levers). When
    active flips back to False the wall is removed, the shoved token is
    pulled back to its origin, and the handle flips back up.
    """

    GLYPH_UP = "LEVU"
    GLYPH_DOWN = "LEVD"

    def __init__(self, x, y, lever_name: str = "Lever"):
        super().__init__(x, y, movable=False)
        self.lever_name = lever_name

    def is_blocking(self) -> bool:
        return True

    def is_active(self) -> bool:
        return bool(PropertyRegistry.get(self.lever_name, "active", False))

    def glyph(self) -> str:
        return self.GLYPH_DOWN if self.is_active() else self.GLYPH_UP


class LeverWall(GameObject):
    """Single wall left behind at a fired lever's vacated origin cell.

    Always solid (independent of Wall.solid) so the sealed hole reads as
    a real wall. Removed again when the lever deactivates.
    """

    GLYPH = "WALL"

    def is_blocking(self) -> bool:
        return True


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