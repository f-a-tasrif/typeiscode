"""
level.py
--------
Level owns the grid of static tiles (Wall/Floor/Goal), the dynamic
objects (Player, Platform, Door, Trap, CodeBlock) and the CircuitLines.
It exposes a Sokoban-style move() method: the player steps in a
direction; if a movable CodeBlock is in the way it gets pushed (if the
cell beyond it is free); if a Platform/Door/Trap is in the way its
*live* is_blocking()/is_lethal() decides what happens.
"""

from __future__ import annotations
from game_object import GameObject, Wall, Floor, Goal, Player, Platform, Door, Trap, HiddenBoom, BorderMine, Warp, SealWall, Seal2Wall, Seal3Wall, LatchDoor, LaserDoor, HardMine
from blocks import CodeBlock, CircuitLine, is_merge_pair
from registry import PropertyRegistry

DIRS = {
    "w": (0, -1),
    "s": (0, 1),
    "a": (-1, 0),
    "d": (1, 0),
}


class Level:
    def __init__(self, name: str, width: int, height: int, initial_registry: dict):
        self.name = name
        self.width = width
        self.height = height
        self.initial_registry = initial_registry

        PropertyRegistry.reset(initial_registry)

        # static background tile at every cell, default Floor
        self.tiles: dict[tuple[int, int], GameObject] = {}
        for x in range(width):
            for y in range(height):
                self.tiles[(x, y)] = Floor(x, y)

        self.player: Player | None = None
        self.dynamic_objects: list[GameObject] = []  # Platform/Door/Trap/CodeBlock
        self.circuits: list[CircuitLine] = []

        self.won = False
        self.dead = False
        # True when the character has fallen into a Path void: it is gone
        # from the board (invisible) for the rest of the run.
        self.player_invisible = False
        self.moves = 0
        self.rule_mode = "circuit"
        self.fusion_enabled = True
        self.active_rules: list[str] = []
        self.fusion_press_count = 0   # tracks Stone./open presses toward fusion
        # Relocated-flag target (x, y) for Flag.moved levels (map10):
        # while Flag.moved is True the win cell is here, not the Goal tiles.
        self.flag2: tuple[int, int] | None = None
        # Forge-crafted finish (map14): while Gate.at is True the win cell
        # is here; the level starts with no Goal tiles at all.
        self.gate2: tuple[int, int] | None = None
        # Crafting recipes: [((kind,val),(kind,val),(kind,val)), ...]
        # Pushing the first two together (either order, orthogonal contact
        # via a push) consumes both and spawns the third at the target cell.
        self.recipes: list = []

    # -- level construction helpers -----------------------------------
    def add_wall_border(self):
        seen = set()
        for x in range(self.width):
            for y in (0, self.height - 1):
                self.tiles[(x, y)] = Wall(x, y)
                if (x, y) not in seen:
                    seen.add((x, y))
                    self.dynamic_objects.append(BorderMine(x, y))
        for y in range(self.height):
            for x in (0, self.width - 1):
                self.tiles[(x, y)] = Wall(x, y)
                if (x, y) not in seen:
                    seen.add((x, y))
                    self.dynamic_objects.append(BorderMine(x, y))

    def add_wall(self, x, y):
        self.tiles[(x, y)] = Wall(x, y)

    def set_goal(self, x, y):
        self.tiles[(x, y)] = Goal(x, y)

    def set_player(self, x, y):
        self.player = Player(x, y)

    def add_object(self, obj: GameObject):
        self.dynamic_objects.append(obj)

    def add_circuit(self, circuit: CircuitLine):
        self.circuits.append(circuit)

    def add_warp_pair(self, x1, y1, x2, y2):
        """Place two Warp objects that point to each other."""
        w1 = Warp(x1, y1, x2, y2)
        w2 = Warp(x2, y2, x1, y1)
        self.dynamic_objects.append(w1)
        self.dynamic_objects.append(w2)

    # -- lookups --------------------------------------------------------
    def block_at(self, x, y) -> CodeBlock | None:
        for obj in self.dynamic_objects:
            if isinstance(obj, CodeBlock) and obj.x == x and obj.y == y:
                return obj
        return None

    def terrain_at(self, x, y) -> GameObject | None:
        for obj in self.dynamic_objects:
            if not isinstance(obj, CodeBlock) and obj.x == x and obj.y == y:
                return obj
        return None

    def object_at(self, x, y) -> GameObject | None:
        # Block-first ordering so stacked cells resolve to the pushable token.
        # Known edge case: a block resting on a cell that later becomes
        # blocking stays there. Do not add special handling.
        b = self.block_at(x, y)
        if b is not None:
            return b
        return self.terrain_at(x, y)

    def warp_at(self, x, y) -> "Warp | None":
        for obj in self.dynamic_objects:
            if isinstance(obj, Warp) and obj.x == x and obj.y == y:
                return obj
        return None

    def blocks_by_pos(self) -> dict:
        return {
            (o.x, o.y): o
            for o in self.dynamic_objects
            if isinstance(o, CodeBlock)
        }

    def tile_at(self, x, y) -> GameObject:
        return self.tiles.get((x, y), Wall(x, y))

    def _apply_seal_walls(self):
        """SealWall.is_blocking() reads the registry live, so no explicit
        update is needed here. This method exists as a hook for future use
        and to make the architecture explicit."""
        pass

    # -- core game loop ---------------------------------------------------
    def recompile_circuits(self):
        if getattr(self, "rule_mode", "circuit") == "global":
            self._compile_global_rules()
            self._apply_seal_walls()
            # Like the circuit-mode void check below: if the new rules turned
            # the cell under the player lethal, the run ends on the spot.
            if self.player is not None and not self.won and not self.dead:
                under = self.terrain_at(self.player.x, self.player.y)
                if under is not None and under.is_lethal():
                    self.dead = True
                    if isinstance(under, Platform) and under.is_void():
                        self.player_invisible = True
            return
        # Compilation is a projection of the *current* board, not a one-way
        # mutation.  Start from the level defaults every time so breaking a
        # statement immediately restores its wall/path behaviour and a later
        # valid statement can compile again.
        PropertyRegistry.reset(self.initial_registry)
        bpos = self.blocks_by_pos()
        for c in self.circuits:
            c.learn_target(bpos)
        owned = {c.bound_target for c in self.circuits if c.bound_target}
        for c in self.circuits:
            c.try_compile(bpos, owned_targets=owned)
        self._apply_seal_walls()

        # If the logic just collapsed the path the character is standing on
        # back into a void, it falls in on the spot.
        if self.player is not None and not self.won and not self.dead:
            standing = self.object_at(self.player.x, self.player.y)
            if isinstance(standing, Platform) and standing.is_void():
                self.dead = True
                self.player_invisible = True

    def _move_player_circuit(self, direction: str) -> str:
        """Attempt to move the player. Returns a short status message."""
        if direction not in DIRS or self.won or self.dead:
            return ""
        dx, dy = DIRS[direction]
        nx, ny = self.player.x + dx, self.player.y + dy

        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return "You can't leave the grid."

        tile = self.tile_at(nx, ny)
        if isinstance(tile, Wall) and tile.is_blocking():
            return "A wall blocks the way."

        seal = self.terrain_at(nx, ny)
        if isinstance(seal, SealWall) and seal.is_blocking():
            return "A sealed wall blocks the way."

        occ = self.object_at(nx, ny)
        if occ is not None:
            if isinstance(occ, CodeBlock):
                # A push only moves the block directly in front of the player.
                # Blocks cannot be chain-pushed: an occupied destination stops
                # the move, keeping adjacent blocks independent.
                bx, by = nx + dx, ny + dy
                if not (0 <= bx < self.width and 0 <= by < self.height):
                    return "Can't push that off the grid."
                beyond_tile = self.tile_at(bx, by)
                if isinstance(beyond_tile, Wall) and beyond_tile.is_blocking():
                    return "Can't push -- wall behind the block."
                if self.warp_at(bx, by) is not None:
                    return "Can't push a block onto a portal."
                beyond_seal = self.terrain_at(bx, by)
                if isinstance(beyond_seal, SealWall) and beyond_seal.is_blocking():
                    return "Can't push -- sealed wall behind the block."
                target = self.object_at(bx, by)
                if target is not None:
                    # Shoving the Path./open pair straight into each other
                    # fuses them on the spot.
                    if is_merge_pair(occ, target):
                        return self._fuse_pair(occ, target)
                    return "Can't push -- something is already there."
                occ.x, occ.y = bx, by
                self.player.x, self.player.y = nx, ny
                warp = self.warp_at(self.player.x, self.player.y)
                if warp is not None:
                    dest_x, dest_y = warp.pair_x, warp.pair_y
                    # only teleport if destination cell has no block on it
                    if self.block_at(dest_x, dest_y) is None:
                        self.player.x, self.player.y = dest_x, dest_y
                self.moves += 1
                # Path. and open fuse the moment they end up side by side —
                # no repeated pressing required.
                partner = self._merge_partner(occ)
                if partner is not None:
                    return self._fuse_pair(occ, partner)
                self.recompile_circuits()
            else:
                # Platform / Door / Trap -- consult live behaviour
                if occ.is_blocking():
                    return f"{occ.__class__.__name__} is solid -- you can't pass."
                # not blocking: step onto/through it
                self.player.x, self.player.y = nx, ny
                warp = self.warp_at(self.player.x, self.player.y)
                if warp is not None:
                    dest_x, dest_y = warp.pair_x, warp.pair_y
                    # only teleport if destination cell has no block on it
                    if self.block_at(dest_x, dest_y) is None:
                        self.player.x, self.player.y = dest_x, dest_y
                self.moves += 1
                if occ.is_lethal():
                    self.dead = True
                    if isinstance(occ, Platform) and occ.is_void():
                        self.player_invisible = True
                        return ("You fell into the void!  The character "
                                "vanishes into the dark.  Game over.")
                    if isinstance(occ, (HiddenBoom, BorderMine, HardMine)):
                        return "BOOM! The hidden explosive burst and blew you to pieces!"
                    return "You stepped on a live trap! Game over."
        else:
            self.player.x, self.player.y = nx, ny
            warp = self.warp_at(self.player.x, self.player.y)
            if warp is not None:
                dest_x, dest_y = warp.pair_x, warp.pair_y
                # only teleport if destination cell has no block on it
                if self.block_at(dest_x, dest_y) is None:
                    self.player.x, self.player.y = dest_x, dest_y
            self.moves += 1

        flag_msg = self._check_flag_win()
        if flag_msg is not None:
            return flag_msg
        if (self.player.x, self.player.y) == (nx, ny):
            goal_msg = self._check_goal_win(tile)
            if goal_msg is not None:
                return goal_msg

        return ""

    def move_player(self, direction: str) -> str:
        """Dispatch to the circuit or global mover based on rule_mode."""
        if getattr(self, "rule_mode", "circuit") == "global":
            return self._move_player_global(direction)
        return self._move_player_circuit(direction)

    def _compile_global_rules(self) -> None:
        from blocks import CLASS, PROP, OP, VALUE, NOT

        # Stone/Seal compile automatically via the generic scanner as long
        # as they appear in initial_registry (see RULES_REGISTRY). Ensure
        # defaults for levels built before the extension.
        self.initial_registry.setdefault("Stone", {"solid": True})
        self.initial_registry.setdefault("Seal", {"active": True})
        self.initial_registry.setdefault("Latch", {"isOpen": False})
        self.initial_registry.setdefault("Laser", {"beams": True})
        self.initial_registry.setdefault("Seal2", {"active": True})
        self.initial_registry.setdefault("Seal3", {"active": True})
        self.initial_registry.setdefault("Gate", {"at": False})
        PropertyRegistry.reset(self.initial_registry)
        self.active_rules = []
        bpos = self.blocks_by_pos()
        ordered = sorted(bpos.items(), key=lambda kv: (kv[0][1], kv[0][0]))
        for (x, y), b0 in ordered:
            if b0.kind != CLASS:
                continue
            b1 = bpos.get((x + 1, y))
            b2 = bpos.get((x + 2, y))
            if b1 is None or b1.kind != PROP:
                continue
            if b2 is None or b2.kind != OP or b2.value != "=":
                continue
            b3 = bpos.get((x + 3, y))
            if b3 is None:
                continue
            if b3.kind == NOT:
                b4 = bpos.get((x + 4, y))
                if b4 is None or b4.kind != VALUE:
                    continue
                raw = b4.value
                val = (not raw) if isinstance(raw, bool) else (not b4.value)
                negated = True
            elif b3.kind == VALUE:
                raw = b3.value
                val = b3.value
                negated = False
            else:
                continue
            cls_name = b0.value
            canon = PropertyRegistry.canonical(cls_name, b1.value)
            bucket = self.initial_registry.get(cls_name)
            if bucket is None or canon not in bucket:
                continue
            PropertyRegistry.set(cls_name, canon, val)
            if negated:
                self.active_rules.append(f"{cls_name}.{canon} = NOT {raw} -> {val}")
            else:
                self.active_rules.append(f"{cls_name}.{canon} = {raw}")

    def _craft_result(self, a, b):
        """Return (kind, value) if blocks a,b match a recipe, else None."""
        for (k1, v1), (k2, v2), (kr, vr) in self.recipes:
            if ((a.kind, a.value) == (k1, v1) and (b.kind, b.value) == (k2, v2)) or \
               ((a.kind, a.value) == (k2, v2) and (b.kind, b.value) == (k1, v1)):
                return (kr, vr)
        return None

    def _move_player_global(self, direction: str) -> str:
        if direction not in DIRS or self.won or self.dead:
            return ""
        dx, dy = DIRS[direction]
        nx, ny = self.player.x + dx, self.player.y + dy

        # 1. Out of bounds -> reject.
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return "You can't leave the grid."

        # 2. Wall tile at target that is blocking -> reject.
        tile = self.tile_at(nx, ny)
        if isinstance(tile, Wall) and tile.is_blocking():
            return "A wall blocks the way."

        seal = self.terrain_at(nx, ny)
        if isinstance(seal, SealWall) and seal.is_blocking():
            return "A sealed wall blocks the way."

        # 3. terrain at target that is blocking -> reject.
        terr = self.terrain_at(nx, ny)
        if terr is not None and terr.is_blocking():
            return f"{terr.__class__.__name__} is solid -- you can't pass."

        # 4. Push a block if one sits at the target.
        blk = self.block_at(nx, ny)
        if blk is not None:
            bx, by = nx + dx, ny + dy
            if not (0 <= bx < self.width and 0 <= by < self.height):
                return "Can't push that off the grid."
            beyond_tile = self.tile_at(bx, by)
            if isinstance(beyond_tile, Wall) and beyond_tile.is_blocking():
                return "Can't push -- wall behind the block."
            beyond_terr = self.terrain_at(bx, by)
            if isinstance(beyond_terr, SealWall) and beyond_terr.is_blocking():
                return "Can't push -- sealed wall behind the block."
            if beyond_terr is not None and beyond_terr.is_blocking():
                return f"Can't push -- {beyond_terr.__class__.__name__} is solid."
            if self.warp_at(bx, by) is not None:
                return "Can't push a block onto a portal."
            if isinstance(self.terrain_at(bx, by), (HiddenBoom, BorderMine, HardMine)):
                return "Can't push a block onto a mine."
            if self.block_at(bx, by) is not None:
                other = self.block_at(bx, by)
                crafted = self._craft_result(blk, other)
                if crafted is not None:
                    from blocks import CodeBlock as _CB
                    self.dynamic_objects = [
                        o for o in self.dynamic_objects
                        if o is not blk and o is not other
                    ]
                    self.dynamic_objects.append(_CB(bx, by, crafted[0], crafted[1]))
                    self.player.x, self.player.y = nx, ny
                    self.moves += 1
                    self.recompile_circuits()
                    gate_msg = self._check_gate_win()
                    if gate_msg is not None:
                        return f"Crafted {crafted[1]}!  " + gate_msg
                    return f"Crafted {crafted[1]}!"
                return "Can't push -- something is already there."
            blk.x, blk.y = bx, by

        # 5. Move the player, then recompile with the new board.
        self.player.x, self.player.y = nx, ny
        warp = self.warp_at(self.player.x, self.player.y)
        if warp is not None:
            dest_x, dest_y = warp.pair_x, warp.pair_y
            # only teleport if destination cell has no block on it
            if self.block_at(dest_x, dest_y) is None:
                self.player.x, self.player.y = dest_x, dest_y
        self.moves += 1
        self.recompile_circuits()

        # 6. AFTER recompile: lethality then relocated-flag / goal.
        under = self.terrain_at(self.player.x, self.player.y)
        if under is not None and under.is_lethal():
            self.dead = True
            if isinstance(under, Platform) and under.is_void():
                self.player_invisible = True
                return ("You fell into the void!  The character "
                        "vanishes into the dark.  Game over.")
            if isinstance(under, (HiddenBoom, BorderMine, HardMine)):
                return "BOOM! The hidden explosive burst and blew you to pieces!"
            return "You stepped on a live trap! Game over."

        flag_msg = self._check_flag_win()
        if flag_msg is not None:
            return flag_msg
        gate_msg = self._check_gate_win()
        if gate_msg is not None:
            return gate_msg
        goal_msg = self._check_goal_win(self.tile_at(self.player.x, self.player.y))
        if goal_msg is not None:
            return goal_msg

        return ""

    def _check_flag_win(self) -> str | None:
        """Relocated-flag win (map10): while Flag.moved is True the finish
        is the hidden chamber cell, and the visible Goal tiles are decoys."""
        if not bool(PropertyRegistry.get("Flag", "moved", False)):
            return None
        if self.flag2 is not None and (self.player.x, self.player.y) == self.flag2:
            self.won = True
            return "You reached the relocated flag! Level complete."
        return None

    def _check_gate_win(self) -> str | None:
        """Forge finish (map14): while Gate.at is True the win cell is
        gate2, generated inside an isolated chamber (no Goal tiles)."""
        if not bool(PropertyRegistry.get("Gate", "at", False)):
            return None
        if self.gate2 is not None and (self.player.x, self.player.y) == self.gate2:
            self.won = True
            return "You reached the forged flag! Level complete."
        return None

    def _check_goal_win(self, tile: GameObject) -> str | None:
        """Normal Goal-tile win, suppressed while the flag is relocated."""
        if bool(PropertyRegistry.get("Flag", "moved", False)):
            return None
        if isinstance(tile, Goal):
            self.won = True
            return "You reached the goal! Level complete."
        return None

    def _merge_partner(self, block: CodeBlock) -> CodeBlock | None:
        """The Path./open token sitting orthogonally next to `block`, if any."""
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            other = self.object_at(block.x + dx, block.y + dy)
            if is_merge_pair(block, other):
                return other
        return None

    def _fuse_pair(self, pushed: CodeBlock, other: CodeBlock) -> str:
        """
        The Path. and open tokens are consumed the moment they are put
        together -- one contact is enough, no repeated pressing.  Both
        blocks vanish, any pre-existing goal (there is only ever one
        flag) is removed, and a brand-new Goal tile blooms on the cell
        the pushed token occupies.
        """
        # Stone./open requires 3 presses; Platform./open fuses on 1 contact
        is_stone_pair = {(pushed.kind, pushed.value), (other.kind, other.value)} == {
            ("CLASS", "Stone"), ("PROP", "isOpen")}
        if is_stone_pair:
            # Like map8.html: the pair resists fusion while the seal holds.
            if bool(PropertyRegistry.get("Seal", "active", True)):
                return ("Stone. + open resist fusion while Seal.active = True. "
                        "Open the seal vault first.")
            self.fusion_press_count += 1
            if self.fusion_press_count < 3:
                return (f"Stone. + open: press {self.fusion_press_count}/3 "
                        f"to fuse into a new GOAL.")
            self.fusion_press_count = 0
            # fall through to the actual fusion below
        else:
            self.fusion_press_count = 0  # reset if a different pair is touched

        # --- existing fusion logic (unchanged) ---
        names = f"{pushed.glyph().strip()} + {other.glyph().strip()}"
        gx, gy = pushed.x, pushed.y
        self.dynamic_objects = [
            o for o in self.dynamic_objects
            if o is not pushed and o is not other
        ]
        replaced = False
        for (tx, ty), tile in list(self.tiles.items()):
            if isinstance(tile, Goal) and (tx, ty) != (gx, gy):
                self.tiles[(tx, ty)] = Floor(tx, ty)
                replaced = True
        self.tiles[(gx, gy)] = Goal(gx, gy)
        self.recompile_circuits()
        msg = f"{names} fuse together!"
        if replaced:
            msg += "  The original GOAL vanishes."
        msg += f"  A new GOAL appears at ({gx}, {gy}) -- step onto it to win."
        return msg

    def is_over(self) -> bool:
        return self.won or self.dead

    # -- rendering --------------------------------------------------------
    def render(self) -> str:
        bpos = self.blocks_by_pos()
        flag_moved = bool(PropertyRegistry.get("Flag", "moved", False))
        flag2 = getattr(self, "flag2", None)
        gate_on = bool(PropertyRegistry.get("Gate", "at", False))
        gate2 = getattr(self, "gate2", None)
        lines = []
        header = "     " + "".join(f"{x:^5}" for x in range(self.width))
        lines.append(header)
        for y in range(self.height):
            row_cells = []
            for x in range(self.width):
                # An invisible character (fallen into a void) is not drawn.
                on_player = (self.player is not None and self.player.x == x
                             and self.player.y == y
                             and not (self.dead and self.player_invisible))
                if on_player:
                    glyph = self.player.glyph()
                elif (flag_moved and flag2 is not None and (x, y) == flag2
                        and self.block_at(x, y) is None):
                    # Relocated finish flag in its hidden chamber.
                    glyph = Goal(x, y).glyph()
                elif (gate_on and gate2 is not None and (x, y) == gate2
                        and self.block_at(x, y) is None):
                    glyph = Goal(x, y).glyph()
                else:
                    # Block first, then terrain, then the static tile, so a
                    # block stacked on terrain (e.g. on an open door or a
                    # vanished table cell) still reads as the block.
                    blk = self.block_at(x, y)
                    if blk is not None:
                        glyph = blk.glyph()
                    else:
                        terr = self.terrain_at(x, y)
                        if terr is not None:
                            glyph = terr.glyph()
                        elif flag_moved and isinstance(self.tile_at(x, y), Goal):
                            # Decoy flag while relocated: reads as plain floor.
                            glyph = Floor(x, y).glyph()
                        else:
                            glyph = self.tile_at(x, y).glyph()
                row_cells.append(f"{glyph:^5}")
            lines.append(f"{y:>3}  " + "".join(row_cells))
        return "\n".join(lines)

    def render_circuits(self) -> str:
        return "\n".join(c.render_text() for c in self.circuits)

    def render_registry(self) -> str:
        snap = PropertyRegistry.snapshot()
        parts = []
        for cls, props in snap.items():
            for p, v in props.items():
                parts.append(f"{cls}.{p}={v}")
        return "  |  ".join(parts)

    def reset(self):
        PropertyRegistry.reset(self.initial_registry)
        self.player_invisible = False
        self.fusion_press_count = 0
        self.recompile_circuits()
