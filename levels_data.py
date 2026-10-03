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
from game_object import Platform, Door, Trap, HiddenBoom, BorderMine, Floor, SealWall, Seal2Wall, Seal3Wall, Seal4Wall, Seal5Wall, Seal6Wall, LeverPedestal, LatchDoor, LaserDoor, Stone, HardMine
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
    "Stone": {"solid": True},
    "Seal": {"active": True},
    "Flag": {"moved": False},
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
    "Stone": {"solid": True},
    "Seal": {"active": True},
    "Seal2": {"active": True},
    "Seal3": {"active": True},
    "Seal4": {"active": True},
    "Seal5": {"active": True},
    "Seal6": {"active": True},
    "Lever": {"active": False},
    "Lever2": {"active": False},
    "Lever3": {"active": False},
    "Lever4": {"active": False},
    "Beacon": {"lit": False},
    "Latch": {"isOpen": False},
    "Laser": {"beams": True},
    "Gate": {"at": False},
    "Flag": {"moved": False},
}

# -- data-driven global levels (levels 5+) ------------------------------
# Token text -> (kind, value) for CodeBlocks placed by _build_from_map.
MAP_TOKENS: dict[str, tuple[str, object]] = {
    "Path.": (CLASS, "Platform"),
    "Door.": (CLASS, "Door"),
    "Trap.": (CLASS, "Trap"),
    "Stone.": (CLASS, "Stone"),
    "Seal.": (CLASS, "Seal"),
    "Seal2.": (CLASS, "Seal2"),
    "Seal3.": (CLASS, "Seal3"),
    "Seal4.": (CLASS, "Seal4"),
    "Seal5.": (CLASS, "Seal5"),
    "Seal6.": (CLASS, "Seal6"),
    "Lever.": (CLASS, "Lever"),
    "Lever2.": (CLASS, "Lever2"),
    "Lever3.": (CLASS, "Lever3"),
    "Lever4.": (CLASS, "Lever4"),
    "Beacon.": (CLASS, "Beacon"),
    "lit": (PROP, "lit"),
    "Latch.": (CLASS, "Latch"),
    "Laser.": (CLASS, "Laser"),
    "Gate.": (CLASS, "Gate"),
    "Wall.": (CLASS, "Wall"),
    "Flag.": (CLASS, "Flag"),
    "@Door": (CLASS, "Access"),
    "@Trap": (CLASS, "Turn"),
    "Entry": (CLASS, "Entry"),
    "OR": (PROP, "point"),
    "at": (PROP, "at"),
    "beams": (PROP, "beams"),
    "solid": (PROP, "isSolid"),
    "open": (PROP, "isOpen"),
    "lethal": (PROP, "isLethal"),
    "active": (PROP, "active"),
    "moved": (PROP, "moved"),
    "=": (OP, "="),
    "True": (VALUE, True),
    "False": (VALUE, False),
    "NOT": (NOT, "NOT"),
}


def _build_from_map(name: str, rows: list[str], start: tuple[int, int],
                    tokens: list[tuple[int, int, str]], warp: list | None = None,
                    stone_mode: bool = False, rec: list | None = None,
                    f2: list | tuple | None = None,
                    border_mines: bool = False, swap_sz: bool = False,
                    beacon2: list | tuple | None = None) -> Level:
    
    W, H = len(rows[0]), len(rows)
    lvl = Level(name, W, H, RULES_REGISTRY)
    lvl.rule_mode = "global"
    lvl.fusion_enabled = False
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                lvl.add_wall(x, y)
            elif ch == "T":
                if stone_mode:
                    lvl.add_object(Stone(x, y))
                else:
                    # Level 1's own path trap: safe floor while
                    # Path.solid = True, lethal void while False.
                    lvl.add_object(Platform(x, y))
            elif ch == "D":
                lvl.add_object(Door(x, y))
            elif ch == "E":
                lvl.add_object(LatchDoor(x, y))
            elif ch == "L":
                lvl.add_object(LaserDoor(x, y))
            elif ch == "X":
                lvl.add_object(Trap(x, y))
            elif ch == "F":
                lvl.set_goal(x, y)
            elif ch == "M":
                lvl.add_object(HiddenBoom(x, y))
            elif ch == "H":
                lvl.add_object(HardMine(x, y))
            elif ch == "B":
                lvl.add_wall(x, y)
                lvl.add_object(BorderMine(x, y))
            elif ch == "S":
                lvl.add_object(Seal2Wall(x, y) if swap_sz else SealWall(x, y))
            elif ch == "Z":
                lvl.add_object(SealWall(x, y) if swap_sz else Seal2Wall(x, y))
            elif ch == "Y":
                lvl.add_object(Seal3Wall(x, y))
            elif ch == "P":
                lvl.add_object(Seal4Wall(x, y))
            elif ch == "Q":
                lvl.add_object(Seal5Wall(x, y))
            elif ch == "W":
                lvl.add_object(Seal6Wall(x, y))
            elif ch == "V":
                lvl.add_object(LeverPedestal(x, y, "Lever"))
                lvl.levers.append((x, y, "Lever"))
            elif ch == "U":
                lvl.add_object(LeverPedestal(x, y, "Lever2"))
                lvl.levers.append((x, y, "Lever2"))
            elif ch == "N":
                lvl.add_object(LeverPedestal(x, y, "Lever3"))
                lvl.levers.append((x, y, "Lever3"))
            elif ch == "K":
                lvl.add_object(LeverPedestal(x, y, "Lever4"))
                lvl.levers.append((x, y, "Lever4"))
            # "." = nothing
    sr, sc = start
    lvl.set_player(sc, sr)
    for tr, tc, text in tokens:
        kind, value = MAP_TOKENS[text]
        lvl.add_object(CodeBlock(tc, tr, kind, value))
    for w in (warp or []):
        # w = [row1, col1, row2, col2]
        lvl.add_warp_pair(w[1], w[0], w[3], w[2])
        # note: maps_data uses [row, col] order; Level uses (x=col, y=row)
    if rec:
        for a, b, c in rec:
            ka, va = MAP_TOKENS[a]
            kb, vb = MAP_TOKENS[b]
            kc, vc = MAP_TOKENS[c]
            lvl.recipes.append(((ka, va), (kb, vb), (kc, vc)))
    if f2 is not None:
        lvl.gate2 = (f2[1], f2[0])
    if beacon2 is not None:
        lvl.beacon2 = (beacon2[1], beacon2[0])
    if border_mines:
        lvl.add_wall_border()
    lvl.recompile_circuits()
    return lvl


def _flip_value_block(lvl: Level, entry: dict, text: str) -> None:
    
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


def build_level4() -> Level:
    
    e = MAPS[3]
    return _build_from_map("4",
                           e["rows"], e["start"], e["tokens"])


def build_level6() -> Level:
    
    e = MAPS[2]
    lvl = _build_from_map("6",
                          e["rows"], e["start"], e["tokens"])
    # The first room's spare True is a False here (a decoy next to the
    # Path slot; the solution still feeds the rule with NOT).
    _flip_value_block(lvl, e, "True")
    return lvl


def build_level7() -> Level:
    
    e = MAPS[4]
    lvl = _build_from_map("7",
                          e["rows"], e["start"], e["tokens"])
    _flip_value_block(lvl, e, "False")
    return lvl


def build_level8() -> Level:
    
    W, H = 28, 12
    lvl = Level("13 - If one path closes, another opens. ", W, H, DEFAULT_REGISTRY)
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



def build_level9() -> Level:
    e = MAPS[5]
    lvl = _build_from_map("8 - Vault cathedral", e["rows"], e["start"], e["tokens"],
                          stone_mode=True)
    for w in e.get("warp", []):
        lvl.add_warp_pair(w[1], w[0], w[3], w[2])
    return lvl


def build_level10() -> Level:
    e = MAPS[6]
    lvl = _build_from_map("9 - The Relocating Flag", e["rows"], e["start"], e["tokens"],
                          stone_mode=True)
    for w in e.get("warp", []):
        lvl.add_warp_pair(w[1], w[0], w[3], w[2])
    # Wall.solid = False is solvable here, so the outer border gets live
    # mines exactly like the vault B walls (see map10's mineW rule).
    lvl.add_wall_border()
    f2 = e.get("f2")
    if f2 is not None:
        # maps_data uses [row, col]; Level uses (x=col, y=row).
        lvl.flag2 = (f2[1], f2[0])
    return lvl


def build_level11() -> Level:
    e = MAPS[7]
    return _build_from_map("10 - The Forge Citadel", e["rows"], e["start"],
                           e["tokens"], warp=e.get("warp"),
                           stone_mode=True, rec=e.get("rec"),
                           f2=e.get("f2"), border_mines=True)


def build_level12() -> Level:
    e = MAPS[8]
    return _build_from_map("11 - Nested Vaults & Timing Window", e["rows"],
                           e["start"], e["tokens"], warp=e.get("warp"),
                           stone_mode=True, border_mines=True, swap_sz=True)


def build_level13() -> Level:
    e = MAPS[9]
    return _build_from_map("12 - The Cascade Vaults Undercroft", e["rows"],
                           e["start"], e["tokens"], warp=e.get("warp"),
                           stone_mode=True, border_mines=True,
                           beacon2=e.get("f2"))


ALL_LEVELS = [build_level1, build_level4,
              build_level6, build_level7, build_level9,
              build_level10, build_level11, build_level12, build_level13,
              build_level8]
