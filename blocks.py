
from __future__ import annotations
from game_object import GameObject
from registry import PropertyRegistry

CLASS = "CLASS"
PROP = "PROP"
OP = "OP"
VALUE = "VALUE"
NOT = "NOT"


_GLYPHS = {
    ("CLASS", "Platform"): "Path.",
    ("CLASS", "Wall"): "Wall.",
    ("CLASS", "Door"): "Door.",
    ("CLASS", "Trap"): "Trap.",
    ("CLASS", "Room"): "Room.",
    ("CLASS", "Stone"): "Stone",
    ("CLASS", "Seal"): "Seal.",
    ("CLASS", "Seal2"): "Seal2",
    ("CLASS", "Seal3"): "Seal3",
    ("CLASS", "Seal4"): "Seal4",
    ("CLASS", "Seal5"): "Seal5",
    ("CLASS", "Seal6"): "Seal6",
    ("CLASS", "Lever"): "Lever",
    ("CLASS", "Lever2"): "Lev2",
    ("CLASS", "Lever3"): "Lev3",
    ("CLASS", "Lever4"): "Lev4",
    ("CLASS", "Beacon"): "Beacon",
    ("CLASS", "Latch"): "Latch",
    ("CLASS", "Laser"): "Laser",
    ("CLASS", "Gate"): "Gate.",
    ("CLASS", "Access"): "Access",
    ("CLASS", "Turn"): "turn",
    ("CLASS", "Entry"): "entry",
    ("CLASS", "Flag"): "Flag.",
    ("PROP", "fire"): "fire",
    ("PROP", "water"): "water",
    ("PROP", "isSolid"): "solid",
    ("PROP", "isOpen"): "open",
    ("PROP", "isLethal"): "lethal",
    ("PROP", "solid"): "solid",
    ("PROP", "active"): "active",
    ("PROP", "lit"): "lit",
    ("PROP", "moved"): "moved",
    ("PROP", "beams"): "beams",
    ("PROP", "at"): "at",
    ("PROP", "point"): "point",
    ("OP", "="): " = ",
    ("VALUE", True): "True",
    ("VALUE", False): "False",
    ("NOT", "NOT"): "not",
}


class CodeBlock(GameObject):

    def __init__(self, x: int, y: int, kind: str, value):
        super().__init__(x, y, movable=True)
        self.kind = kind
        self.value = value

    def is_blocking(self) -> bool:




        return False

    def glyph(self) -> str:
        return _GLYPHS.get((self.kind, self.value), "????")

    def __repr__(self):
        return f"CodeBlock({self.kind}={self.value} @ {self.x},{self.y})"






MERGE_TOKENS: set[tuple[str, object]] = {
    ("CLASS", "Platform"), ("CLASS", "Stone"), ("PROP", "isOpen")
}
MERGE_CLASSES: set[tuple[str, object]] = {("CLASS", "Platform"), ("CLASS", "Stone")}
MERGE_PROP: tuple[str, object] = ("PROP", "isOpen")


def is_merge_pair(a, b) -> bool:
    if not (isinstance(a, CodeBlock) and isinstance(b, CodeBlock)):
        return False

    if abs(a.x - b.x) + abs(a.y - b.y) != 1:
        return False


    pair = {(a.kind, a.value), (b.kind, b.value)}
    return MERGE_PROP in pair and bool(pair & MERGE_CLASSES)


class CircuitLine:

    def __init__(self, name: str, slot_positions: list[tuple[int, int]]):
        assert len(slot_positions) == 4, "A circuit line always has 4 slots"
        self.name = name
        self.slot_positions = slot_positions
        self.last_result = None



        self.bound_target: tuple[object, object] | None = None

    def slot_kind(self, index: int) -> str:
        return (CLASS, PROP, OP, VALUE)[index]

    def read_blocks(self, blocks_by_pos: dict) -> list[CodeBlock | None]:
        return [blocks_by_pos.get(pos) for pos in self.slot_positions]

    def learn_target(self, blocks_by_pos: dict) -> None:
        expected_kinds = (CLASS, PROP, OP, VALUE)
        slots = [blocks_by_pos.get(pos) for pos in self.slot_positions]
        if not any(b is None for b in slots):
            if all(b.kind == k for b, k in zip(slots, expected_kinds)) and slots[2].value == "=":
                self.bound_target = (slots[0].value, slots[1].value)

    def try_compile(self, blocks_by_pos: dict, owned_targets: set | None = None) -> bool:


        self.learn_target(blocks_by_pos)

        if owned_targets is None:
            owned: set = {self.bound_target} if self.bound_target else set()
        else:
            owned = set(owned_targets)
            if self.bound_target:
                owned.add(self.bound_target)





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
