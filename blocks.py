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
    ("CLASS", "Platform"): "Path.",
    ("CLASS", "Wall"): "Wall.",
    ("CLASS", "Door"): "Door.",
    ("CLASS", "Trap"): "Trap.",
    ("PROP", "isSolid"): "solid",
    ("PROP", "isOpen"): "open",
    ("PROP", "isLethal"): "lethal",
    ("PROP", "solid"): "solid",
    ("OP", "="): " = ",
    ("VALUE", True): "True",
    ("VALUE", False): "False",
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


# The `Path.` class token and the `open` property token are the two halves
# of a "goal seed": press one into the other -- horizontally or vertically,
# in either order -- MERGE_PRESS_TIMES times in a row and they fuse into a
# brand-new Goal tile (see Level._press_merge).
MERGE_PRESS_TIMES = 3
MERGE_TOKENS: set[tuple[str, object]] = {("CLASS", "Platform"), ("PROP", "isOpen")}


def is_merge_pair(a, b) -> bool:
    """True when `a` and `b` are the Path./open pair, orthogonally adjacent."""
    if not (isinstance(a, CodeBlock) and isinstance(b, CodeBlock)):
        return False
    # Only horizontal or vertical neighbours can press into each other.
    if abs(a.x - b.x) + abs(a.y - b.y) != 1:
        return False
    # Set equality makes the check order-agnostic: Path.-then-open and
    # open-then-Path both count.
    return {(a.kind, a.value), (b.kind, b.value)} == MERGE_TOKENS


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

    def learn_target(self, blocks_by_pos: dict) -> None:
        """Learn this circuit's owned target from its initial slot contents."""
        expected_kinds = (CLASS, PROP, OP, VALUE)
        slots = [blocks_by_pos.get(pos) for pos in self.slot_positions]
        if not any(b is None for b in slots):
            if all(b.kind == k for b, k in zip(slots, expected_kinds)) and slots[2].value == "=":
                self.bound_target = (slots[0].value, slots[1].value)

    def try_compile(self, blocks_by_pos: dict, owned_targets: set | None = None) -> bool:
        """
        Attempt to compile the statement currently sitting on this line.
        Returns True if the registry was actually changed.

        Each circuit owns one (CLASS, PROP) target (learned from its slots).
        It compiles its own target first; if none is present it falls back
        to any *unowned* target (e.g. Wall.solid, which has no dedicated
        circuit). Targets owned by another circuit are skipped so two
        circuits never steal each other's statements.
        """
        # Learn this circuit's target from its original highlighted statement.
        # After that, the same statement can be assembled anywhere on the board.
        self.learn_target(blocks_by_pos)

        if owned_targets is None:
            owned: set = {self.bound_target} if self.bound_target else set()
        else:
            owned = set(owned_targets)
            if self.bound_target:
                owned.add(self.bound_target)

        # Scan every row (hly / horizontal) and every column (vly / vertical):
        # highlighted cells are visual guidance only, not a requirement for
        # compiling.  Horizontal statements read left-to-right, vertical
        # statements read top-to-bottom.
        def _matches(b0, b1, b2, b3) -> bool:
            return (
                b0 and b0.kind == CLASS and
                b1 and b1.kind == PROP and
                b2 and b2.kind == OP and b2.value == "=" and
                b3 and b3.kind == VALUE
            )

        def _target_of(b0, b1, b2, b3):
            if not _matches(b0, b1, b2, b3):
                return None
            return (b0.value, b1.value)

        def _apply(b0, b1, b2, b3) -> bool:
            prop = PropertyRegistry.canonical(b0.value, b1.value)
            changed = PropertyRegistry.set(b0.value, prop, b3.value)
            self.last_result = f"{b0.value}.{prop} = {b3.value}"
            return changed

        def _scan(own_only: bool):
            rows_l = sorted({yy for _, yy in blocks_by_pos})
            for yy in rows_l:
                row_x = sorted(xx for (xx, by) in blocks_by_pos if by == yy)
                for xx in row_x:
                    quad = (
                        blocks_by_pos.get((xx, yy)),
                        blocks_by_pos.get((xx + 1, yy)),
                        blocks_by_pos.get((xx + 2, yy)),
                        blocks_by_pos.get((xx + 3, yy)),
                    )
                    target = _target_of(*quad)
                    if target is None:
                        continue
                    is_own = bool(self.bound_target and target == self.bound_target)
                    is_other = target in owned and not is_own
                    if own_only and not is_own:
                        continue
                    if not own_only and (is_own or is_other):
                        continue
                    return _apply(*quad)
            cols_l = sorted({xx for xx, _ in blocks_by_pos})
            for xx in cols_l:
                col_y = sorted(yy for (bx, yy) in blocks_by_pos if bx == xx)
                for yy in col_y:
                    quad = (
                        blocks_by_pos.get((xx, yy)),
                        blocks_by_pos.get((xx, yy + 1)),
                        blocks_by_pos.get((xx, yy + 2)),
                        blocks_by_pos.get((xx, yy + 3)),
                    )
                    target = _target_of(*quad)
                    if target is None:
                        continue
                    is_own = bool(self.bound_target and target == self.bound_target)
                    is_other = target in owned and not is_own
                    if own_only and not is_own:
                        continue
                    if not own_only and (is_own or is_other):
                        continue
                    return _apply(*quad)
            return None

        matched = _scan(own_only=True)
        if matched is not None:
            return matched
        matched = _scan(own_only=False)
        if matched is not None:
            return matched

        # Check for syntax error vs incomplete
        rows = sorted({y for _, y in blocks_by_pos})
        cols = sorted({x for x, _ in blocks_by_pos})
        for y in rows:
            row_blocks = [b for (x, by), b in blocks_by_pos.items() if by == y]
            if len(row_blocks) >= 4:
                self.last_result = "SYNTAX ERROR"
                return False
        for x in cols:
            col_blocks = [b for (bx, y), b in blocks_by_pos.items() if bx == x]
            if len(col_blocks) >= 4:
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
