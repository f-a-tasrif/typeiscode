"""
blocks.py
---------
The pushable syntax tokens (CodeBlock) and the CircuitLine "compiler"
that reads whatever tokens currently sit in its slots and, if they form
a valid statement, writes the result into PropertyRegistry.

A statement has exactly four slots, read left to right:

    [CLASS]  .  [PROPERTY]  =  [VALUE]
     slot0        slot1    (slot1 also implicitly carries '.')
                              slot2 = operator '='
                              slot3 = value

To keep pushing/sokoban mechanics simple we use 4 slot positions:
    slot 0 -> CLASS token      (e.g. Platform, Door, Trap)
    slot 1 -> PROPERTY token   (e.g. isSolid, isOpen, isLethal)
    slot 2 -> OPERATOR token   (e.g. =)
    slot 3 -> VALUE token      (e.g. true, false)
"""

from __future__ import annotations
from game_object import GameObject
from registry import PropertyRegistry

CLASS = "CLASS"
PROP = "PROP"
OP = "OP"
VALUE = "VALUE"

# how each (kind, value) pair is rendered as a 4-char glyph
_GLYPHS = {
    ("CLASS", "Platform"): "Plat.",
    ("CLASS", "Door"): "DOOR",
    ("CLASS", "Trap"): "TRAP",
    ("PROP", "isSolid"): "sold",
    ("PROP", "isOpen"): "open",
    ("PROP", "isLethal"): "lethal",
    ("OP", "="): " == ",
    ("VALUE", True): "true",
    ("VALUE", False): "false",
}


class CodeBlock(GameObject):
    """A pushable syntax token: a class name, property, operator, or value."""

    def __init__(self, x: int, y: int, kind: str, value):
        super().__init__(x, y, movable=True)
        self.kind = kind
        self.value = value

    def is_blocking(self) -> bool:
        # Code blocks don't block by themselves; being pushable, the engine
        # handles collision explicitly. They *do* occupy their cell though,
        # so nothing else can walk through -- engine checks for this via
        # object presence, not is_blocking().
        return False

    def glyph(self) -> str:
        return _GLYPHS.get((self.kind, self.value), "????")

    def __repr__(self):
        return f"CodeBlock({self.kind}={self.value} @ {self.x},{self.y})"


class CircuitLine:
    """
    A compiler strip made of 4 fixed grid coordinates. Every tick, the
    engine asks each CircuitLine to re-evaluate itself by looking at
    whatever CodeBlocks currently occupy its slot coordinates.
    """

    def __init__(self, name: str, slot_positions: list[tuple[int, int]]):
        assert len(slot_positions) == 4, "A circuit line always has 4 slots"
        self.name = name
        self.slot_positions = slot_positions
        self.last_result = None  # human readable string of last compile
        # The highlighted slots identify which property this circuit controls,
        # but do not constrain where the player can assemble the statement.
        # It is learned from the line's initial, well-formed statement.
        self.bound_target: tuple[object, object] | None = None

    def slot_kind(self, index: int) -> str:
        return (CLASS, PROP, OP, VALUE)[index]

    def read_blocks(self, blocks_by_pos: dict) -> list[CodeBlock | None]:
        return [blocks_by_pos.get(pos) for pos in self.slot_positions]

    def try_compile(self, blocks_by_pos: dict) -> bool:
        """
        Attempt to compile the statement currently sitting on this line.
        Returns True if the registry was actually changed.
        """
        expected_kinds = (CLASS, PROP, OP, VALUE)

        # Learn this circuit's target from its original highlighted statement.
        # After that, the same statement can be assembled anywhere on the board.
        slots = [blocks_by_pos.get(pos) for pos in self.slot_positions]
        if not any(b is None for b in slots):
            if all(b.kind == k for b, k in zip(slots, expected_kinds)) and slots[2].value == "=":
                self.bound_target = (slots[0].value, slots[1].value)

        # Scan every row: highlighted cells are visual guidance only, not a
        # requirement for compiling.  Statements remain left-to-right.
        rows = sorted({y for _, y in blocks_by_pos})
        for y in rows:
            row_x_coords = sorted(x for (x, by) in blocks_by_pos if by == y)
            for x in row_x_coords:
                b0 = blocks_by_pos.get((x, y))
                b1 = blocks_by_pos.get((x + 1, y))
                b2 = blocks_by_pos.get((x + 2, y))
                b3 = blocks_by_pos.get((x + 3, y))
                if (
                    b0 and b0.kind == CLASS and
                    b1 and b1.kind == PROP and
                    b2 and b2.kind == OP and b2.value == "=" and
                    b3 and b3.kind == VALUE
                ):
                    if self.bound_target and (b0.value, b1.value) != self.bound_target:
                        continue
                    changed = PropertyRegistry.set(b0.value, b1.value, b3.value)
                    self.last_result = f"{b0.value}.{b1.value} = {b3.value}"
                    return changed

        # Check for syntax error vs incomplete
        for y in rows:
            row_blocks = [b for (x, by), b in blocks_by_pos.items() if by == y]
            if len(row_blocks) >= 4:
                self.last_result = "SYNTAX ERROR"
                return False

        self.last_result = None
        return False

    def render_text(self) -> str:
        if self.last_result == "SYNTAX ERROR":
            return f"[{self.name}]  >> SYNTAX ERROR"
        if self.last_result is None:
            return f"[{self.name}]  >> (incomplete)"
        return f"[{self.name}]  >> {self.last_result}  [COMPILED OK]"
