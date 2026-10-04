
from __future__ import annotations
from registry import PropertyRegistry


class GameObject:


    GLYPH = "????"

    def __init__(self, x: int, y: int, movable: bool = False):
        self.x = x
        self.y = y
        self.movable = movable


    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return False

    def is_win(self) -> bool:
        return False

    def on_tick(self, world) -> None:
        return None

    def glyph(self) -> str:
        return self.GLYPH

    def pos(self):
        return (self.x, self.y)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.x},{self.y})"


class Wall(GameObject):
    GLYPH = "####"

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Wall", "solid", True))


class Floor(GameObject):
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
    GLYPH_VOID = "VOID"
    GLYPH_SAFE = "    "

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_void(self) -> bool:
        return not bool(PropertyRegistry.get("Platform", "isSolid", True))

    def is_blocking(self) -> bool:

        return False

    def is_lethal(self) -> bool:

        return self.is_void()

    def glyph(self) -> str:
        return self.GLYPH_VOID if self.is_void() else self.GLYPH_SAFE


class Door(GameObject):
    GLYPH_CLOSED = "DOOR"
    GLYPH_OPEN = "open"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        return not bool(PropertyRegistry.get("Door", "isOpen", False))

    def glyph(self) -> str:
        return self.GLYPH_OPEN if not self.is_blocking() else self.GLYPH_CLOSED


class Trap(GameObject):
    GLYPH_ON = "TRAP"
    GLYPH_OFF = "trap"

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_lethal(self) -> bool:
        return bool(PropertyRegistry.get("Trap", "isLethal", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_lethal() else self.GLYPH_OFF


class Stone(GameObject):
    GLYPH_ON = "STON"
    GLYPH_OFF = "    "

    def __init__(self, x, y):
        super().__init__(x, y, movable=False)

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Stone", "solid", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_blocking() else self.GLYPH_OFF


class SealWall(GameObject):
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

    def glyph(self) -> str:

        return "    "


class HardMine(GameObject):

    GLYPH = "MINE"

    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return True

    def glyph(self) -> str:
        return self.GLYPH


class LatchDoor(GameObject):
    GLYPH_CLOSED = "LTCH"
    GLYPH_OPEN = "open"

    def is_blocking(self) -> bool:
        return not bool(PropertyRegistry.get("Latch", "isOpen", False))

    def glyph(self) -> str:
        return self.GLYPH_OPEN if not self.is_blocking() else self.GLYPH_CLOSED


class LaserDoor(GameObject):

    GLYPH_ON = "LASR"
    GLYPH_OFF = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Laser", "beams", True))

    def is_lethal(self) -> bool:
        return bool(PropertyRegistry.get("Laser", "beams", True))

    def glyph(self) -> str:
        return self.GLYPH_ON if self.is_blocking() else self.GLYPH_OFF


class Seal2Wall(SealWall):
    GLYPH_SEALED = "SL2"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal2", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal3Wall(SealWall):
    GLYPH_SEALED = "SL3"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal3", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal4Wall(SealWall):
    GLYPH_SEALED = "SL4"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal4", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal5Wall(SealWall):
    GLYPH_SEALED = "SL5"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal5", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class Seal6Wall(SealWall):
    GLYPH_SEALED = "SL6"
    GLYPH_OPEN = "    "

    def is_blocking(self) -> bool:
        return bool(PropertyRegistry.get("Seal6", "active", True))

    def glyph(self) -> str:
        return self.GLYPH_SEALED if self.is_blocking() else self.GLYPH_OPEN


class LeverPedestal(GameObject):

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

    GLYPH = "WALL"

    def is_blocking(self) -> bool:
        return True


class BorderMine(GameObject):

    GLYPH = "####"

    def is_blocking(self) -> bool:
        return False

    def is_lethal(self) -> bool:
        return True

    def glyph(self) -> str:
        return "####"