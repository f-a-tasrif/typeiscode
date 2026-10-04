
from __future__ import annotations
from game_object import GameObject, Wall, Floor, Goal, Player, Platform, Door, Trap, HiddenBoom, BorderMine, Warp, SealWall, Seal2Wall, Seal3Wall, Seal4Wall, Seal5Wall, Seal6Wall, LeverPedestal, LeverWall, LatchDoor, LaserDoor, HardMine
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


        self.tiles: dict[tuple[int, int], GameObject] = {}
        for x in range(width):
            for y in range(height):
                self.tiles[(x, y)] = Floor(x, y)

        self.player: Player | None = None
        self.dynamic_objects: list[GameObject] = []
        self.circuits: list[CircuitLine] = []

        self.won = False
        self.dead = False


        self.player_invisible = False
        self.moves = 0
        self.rule_mode = "circuit"
        self.fusion_enabled = True
        self.active_rules: list[str] = []
        self.fusion_press_count = 0


        self.flag2: tuple[int, int] | None = None


        self.gate2: tuple[int, int] | None = None


        self.beacon2: tuple[int, int] | None = None




        self.levers: list[tuple[int, int, str]] = []
        self.lever_fired: dict[str, bool] = {}
        self.lever_moved: dict[str, tuple] = {}



        self.recipes: list = []





        self._block_map: dict[tuple[int, int], CodeBlock] = {}
        self._terrain_map: dict[tuple[int, int], GameObject] = {}
        self._warp_map: dict[tuple[int, int], GameObject] = {}
        self._bpos_cache: dict | None = None
        self._index_dirty = True


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
        self._index_dirty = True

    def add_wall(self, x, y):
        self.tiles[(x, y)] = Wall(x, y)

    def set_goal(self, x, y):
        self.tiles[(x, y)] = Goal(x, y)

    def set_player(self, x, y):
        self.player = Player(x, y)

    def add_object(self, obj: GameObject):
        self.dynamic_objects.append(obj)
        self._index_dirty = True

    def _rebuild_index(self):
        block_map: dict = {}
        terrain_map: dict = {}
        warp_map: dict = {}
        for obj in self.dynamic_objects:
            pos = (obj.x, obj.y)
            if isinstance(obj, CodeBlock):
                if pos not in block_map:
                    block_map[pos] = obj
            else:
                if pos not in terrain_map:
                    terrain_map[pos] = obj
                if isinstance(obj, Warp):
                    warp_map[pos] = obj
        self._block_map = block_map
        self._terrain_map = terrain_map
        self._warp_map = warp_map
        self._bpos_cache = dict(block_map)
        self._index_dirty = False

    def _ensure_index(self):



        if self._index_dirty or self._bpos_cache is None:
            self._rebuild_index()

    def add_circuit(self, circuit: CircuitLine):
        self.circuits.append(circuit)

    def add_warp_pair(self, x1, y1, x2, y2):
        w1 = Warp(x1, y1, x2, y2)
        w2 = Warp(x2, y2, x1, y1)
        self.dynamic_objects.append(w1)
        self.dynamic_objects.append(w2)
        self._index_dirty = True


    def block_at(self, x, y) -> CodeBlock | None:
        self._ensure_index()
        return self._block_map.get((x, y))

    def terrain_at(self, x, y) -> GameObject | None:
        self._ensure_index()
        return self._terrain_map.get((x, y))

    def object_at(self, x, y) -> GameObject | None:



        b = self.block_at(x, y)
        if b is not None:
            return b
        return self.terrain_at(x, y)

    def warp_at(self, x, y) -> "Warp | None":
        self._ensure_index()
        return self._warp_map.get((x, y))

    def blocks_by_pos(self) -> dict:
        self._ensure_index()
        return self._bpos_cache

    def tile_at(self, x, y) -> GameObject:
        return self.tiles.get((x, y), Wall(x, y))

    def _apply_seal_walls(self):
        pass


    def recompile_circuits(self):


        self._rebuild_index()
        if getattr(self, "rule_mode", "circuit") == "global":
            self._compile_global_rules()
            self._apply_seal_walls()


            if self.player is not None and not self.won and not self.dead:
                under = self.terrain_at(self.player.x, self.player.y)
                if under is not None and under.is_lethal():
                    self.dead = True
                    if isinstance(under, Platform) and under.is_void():
                        self.player_invisible = True
            return




        PropertyRegistry.reset(self.initial_registry)
        bpos = self.blocks_by_pos()
        for c in self.circuits:
            c.learn_target(bpos)
        owned = {c.bound_target for c in self.circuits if c.bound_target}
        for c in self.circuits:
            c.try_compile(bpos, owned_targets=owned)
        self._apply_seal_walls()



        if self.player is not None and not self.won and not self.dead:
            standing = self.object_at(self.player.x, self.player.y)
            if isinstance(standing, Platform) and standing.is_void():
                self.dead = True
                self.player_invisible = True

    def _move_player_circuit(self, direction: str) -> str:
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


                    if is_merge_pair(occ, target):
                        return self._fuse_pair(occ, target)
                    return "Can't push -- something is already there."
                occ.x, occ.y = bx, by
                self._index_dirty = True
                self.player.x, self.player.y = nx, ny
                warp = self.warp_at(self.player.x, self.player.y)
                if warp is not None:
                    dest_x, dest_y = warp.pair_x, warp.pair_y

                    if self.block_at(dest_x, dest_y) is None:
                        self.player.x, self.player.y = dest_x, dest_y
                self.moves += 1


                partner = self._merge_partner(occ)
                if partner is not None:
                    return self._fuse_pair(occ, partner)
                self.recompile_circuits()
            else:



                if isinstance(occ, LaserDoor) and occ.is_blocking():
                    self.player.x, self.player.y = nx, ny
                    self.moves += 1
                    self.dead = True
                    return ("Zapped! The laser vaporised you into ash! "
                            "Game over.")
                if occ.is_blocking():
                    return f"{occ.__class__.__name__} is solid -- you can't pass."

                self.player.x, self.player.y = nx, ny
                warp = self.warp_at(self.player.x, self.player.y)
                if warp is not None:
                    dest_x, dest_y = warp.pair_x, warp.pair_y

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
                        return "BOOM! The mine blew you to ash! Game over."
                    return "The trap stripped you to a skeleton! Game over."
        else:
            self.player.x, self.player.y = nx, ny
            warp = self.warp_at(self.player.x, self.player.y)
            if warp is not None:
                dest_x, dest_y = warp.pair_x, warp.pair_y

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
        if getattr(self, "rule_mode", "circuit") == "global":
            return self._move_player_global(direction)
        return self._move_player_circuit(direction)

    def _compile_global_rules(self) -> None:
        from blocks import CLASS, PROP, OP, VALUE, NOT




        self.initial_registry.setdefault("Stone", {"solid": True})
        self.initial_registry.setdefault("Seal", {"active": True})
        self.initial_registry.setdefault("Latch", {"isOpen": False})
        self.initial_registry.setdefault("Laser", {"beams": True})
        self.initial_registry.setdefault("Seal2", {"active": True})
        self.initial_registry.setdefault("Seal3", {"active": True})
        self.initial_registry.setdefault("Seal4", {"active": True})
        self.initial_registry.setdefault("Seal5", {"active": True})
        self.initial_registry.setdefault("Seal6", {"active": True})
        self.initial_registry.setdefault("Lever", {"active": False})
        self.initial_registry.setdefault("Lever2", {"active": False})
        self.initial_registry.setdefault("Lever3", {"active": False})
        self.initial_registry.setdefault("Lever4", {"active": False})
        self.initial_registry.setdefault("Beacon", {"lit": False})
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


        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return "You can't leave the grid."


        tile = self.tile_at(nx, ny)
        if isinstance(tile, Wall) and tile.is_blocking():
            return "A wall blocks the way."

        seal = self.terrain_at(nx, ny)
        if isinstance(seal, SealWall) and seal.is_blocking():
            return "A sealed wall blocks the way."



        terr = self.terrain_at(nx, ny)
        if isinstance(terr, LaserDoor) and terr.is_blocking():
            self.player.x, self.player.y = nx, ny
            self.moves += 1
            self.dead = True
            return ("Zapped! The laser vaporised you into ash! Game over.")
        if terr is not None and terr.is_blocking():
            return f"{terr.__class__.__name__} is solid -- you can't pass."


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
                    self._index_dirty = True
                    self.player.x, self.player.y = nx, ny
                    self.moves += 1
                    self.recompile_circuits()
                    gate_msg = self._check_gate_win()
                    if gate_msg is not None:
                        return f"Crafted {crafted[1]}!  " + gate_msg
                    return f"Crafted {crafted[1]}!"
                return "Can't push -- something is already there."
            blk.x, blk.y = bx, by
            self._index_dirty = True


        self.player.x, self.player.y = nx, ny
        warp = self.warp_at(self.player.x, self.player.y)
        if warp is not None:
            dest_x, dest_y = warp.pair_x, warp.pair_y

            if self.block_at(dest_x, dest_y) is None:
                self.player.x, self.player.y = dest_x, dest_y
        self.moves += 1
        self.recompile_circuits()
        lever_msg = self._fire_levers()


        under = self.terrain_at(self.player.x, self.player.y)
        if under is not None and under.is_lethal():
            self.dead = True
            if isinstance(under, Platform) and under.is_void():
                self.player_invisible = True
                return ("You fell into the void!  The character "
                        "vanishes into the dark.  Game over.")
            if isinstance(under, (HiddenBoom, BorderMine, HardMine)):
                return "BOOM! The mine blew you to ash! Game over."
            return "The trap stripped you to a skeleton! Game over."

        flag_msg = self._check_flag_win()
        if flag_msg is not None:
            return flag_msg
        gate_msg = self._check_gate_win()
        if gate_msg is not None:
            return gate_msg
        beacon_msg = self._check_beacon_win()
        if beacon_msg is not None:
            return (lever_msg + " " + beacon_msg).strip() if lever_msg else beacon_msg
        goal_msg = self._check_goal_win(self.tile_at(self.player.x, self.player.y))
        if goal_msg is not None:
            return (lever_msg + " " + goal_msg).strip() if lever_msg else goal_msg

        return lever_msg

    def _check_flag_win(self) -> str | None:
        if not bool(PropertyRegistry.get("Flag", "moved", False)):
            return None
        if self.flag2 is not None and (self.player.x, self.player.y) == self.flag2:
            self.won = True
            return "You reached the relocated flag! Level complete."
        return None

    def _check_gate_win(self) -> str | None:
        if not bool(PropertyRegistry.get("Gate", "at", False)):
            return None
        if self.gate2 is not None and (self.player.x, self.player.y) == self.gate2:
            self.won = True
            return "You reached the forged flag! Level complete."
        return None

    def _check_beacon_win(self) -> str | None:
        if not bool(PropertyRegistry.get("Beacon", "lit", False)):
            return None
        if self.beacon2 is not None and (self.player.x, self.player.y) == self.beacon2:
            self.won = True
            return "You reached the beacon flag! Level complete."
        return None

    def _dest_free(self, dx: int, dy: int) -> bool:
        if not (0 <= dx < self.width and 0 <= dy < self.height):
            return False
        dest_tile = self.tile_at(dx, dy)
        if isinstance(dest_tile, Wall) and dest_tile.is_blocking():
            return False
        dest_terr = self.terrain_at(dx, dy)
        if isinstance(dest_terr, SealWall) and dest_terr.is_blocking():
            return False
        if dest_terr is not None and dest_terr.is_blocking():
            return False
        if self.warp_at(dx, dy) is not None:
            return False
        if isinstance(self.terrain_at(dx, dy), (HiddenBoom, BorderMine, HardMine)):
            return False
        if self.block_at(dx, dy) is not None:
            return False
        return True

    def _fire_levers(self) -> str:
        if not getattr(self, "levers", None):
            return ""
        msgs = []
        for lx, ly, lname in list(self.levers):
            active = bool(PropertyRegistry.get(lname, "active", False))
            fired = bool(self.lever_fired.get(lname))
            ox, oy = lx, ly + 1
            dx, dy = lx, ly + 2
            if active and not fired:
                blk = self.block_at(ox, oy)
                if blk is not None and not self._dest_free(dx, dy):
                    continue
                moved = None
                if blk is not None:
                    blk.x, blk.y = dx, dy
                    moved = blk
                    self._index_dirty = True
                if self.terrain_at(ox, oy) is None:
                    self.dynamic_objects.append(LeverWall(ox, oy))
                    self._index_dirty = True
                self.lever_fired[lname] = True
                self.lever_moved[lname] = (moved, (ox, oy), (dx, dy))
                msgs.append(f"{lname} pulled down")
            elif not active and fired:
                self.dynamic_objects = [
                    o for o in self.dynamic_objects
                    if not (isinstance(o, LeverWall) and (o.x, o.y) == (ox, oy))
                ]
                self._index_dirty = True
                rec = self.lever_moved.pop(lname, None)
                if rec is not None:
                    blk, origin, dest = rec
                    if blk is not None and (blk.x, blk.y) == dest:
                        if self.block_at(*origin) is None:
                            blk.x, blk.y = origin
                            self._index_dirty = True
                self.lever_fired[lname] = False
                msgs.append(f"{lname} released")
        if msgs:
            self._ensure_index()
            self.recompile_circuits()
            fired = [m for m in msgs if "pulled" in m]
            if fired:
                return f"Lever(s) fired: {', '.join(fired)} shoved its token down."
            return "Lever(s) released: wall removed, token restored."
        return ""

    def _check_goal_win(self, tile: GameObject) -> str | None:
        if bool(PropertyRegistry.get("Flag", "moved", False)):
            return None
        if isinstance(tile, Goal):
            self.won = True
            return "You reached the goal! Level complete."
        return None

    def _merge_partner(self, block: CodeBlock) -> CodeBlock | None:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            other = self.object_at(block.x + dx, block.y + dy)
            if is_merge_pair(block, other):
                return other
        return None

    def _fuse_pair(self, pushed: CodeBlock, other: CodeBlock) -> str:

        is_stone_pair = {(pushed.kind, pushed.value), (other.kind, other.value)} == {
            ("CLASS", "Stone"), ("PROP", "isOpen")}
        if is_stone_pair:

            if bool(PropertyRegistry.get("Seal", "active", True)):
                return ("Stone. + open resist fusion while Seal.active = True. "
                        "Open the seal vault first.")
            self.fusion_press_count += 1
            if self.fusion_press_count < 3:
                return (f"Stone. + open: press {self.fusion_press_count}/3 "
                        f"to fuse into a new GOAL.")
            self.fusion_press_count = 0

        else:
            self.fusion_press_count = 0


        names = f"{pushed.glyph().strip()} + {other.glyph().strip()}"
        gx, gy = pushed.x, pushed.y
        self.dynamic_objects = [
            o for o in self.dynamic_objects
            if o is not pushed and o is not other
        ]
        self._index_dirty = True
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


    def render(self) -> str:
        bpos = self.blocks_by_pos()
        flag_moved = bool(PropertyRegistry.get("Flag", "moved", False))
        flag2 = getattr(self, "flag2", None)
        gate_on = bool(PropertyRegistry.get("Gate", "at", False))
        gate2 = getattr(self, "gate2", None)
        beacon_on = bool(PropertyRegistry.get("Beacon", "lit", False))
        beacon2 = getattr(self, "beacon2", None)
        lines = []
        header = "     " + "".join(f"{x:^5}" for x in range(self.width))
        lines.append(header)
        for y in range(self.height):
            row_cells = []
            for x in range(self.width):

                on_player = (self.player is not None and self.player.x == x
                             and self.player.y == y
                             and not (self.dead and self.player_invisible))
                if on_player:
                    if self.dead:
                        under = self.terrain_at(x, y)
                        if type(under) is Trap:

                            glyph = "SKEL"
                        elif isinstance(under, (LaserDoor, HiddenBoom,
                                                BorderMine, HardMine)):
                            glyph = "ASH "
                        else:
                            glyph = self.player.glyph()
                    else:
                        glyph = self.player.glyph()
                elif (flag_moved and flag2 is not None and (x, y) == flag2
                        and self.block_at(x, y) is None):

                    glyph = Goal(x, y).glyph()
                elif (gate_on and gate2 is not None and (x, y) == gate2
                        and self.block_at(x, y) is None):
                    glyph = Goal(x, y).glyph()
                elif (beacon_on and beacon2 is not None and (x, y) == beacon2
                        and self.block_at(x, y) is None):
                    glyph = Goal(x, y).glyph()
                else:



                    blk = self.block_at(x, y)
                    if blk is not None:
                        glyph = blk.glyph()
                    else:
                        terr = self.terrain_at(x, y)
                        if terr is not None:
                            glyph = terr.glyph()
                        elif flag_moved and isinstance(self.tile_at(x, y), Goal):

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
        self.lever_fired = {}
        self.lever_moved = {}
        self.dynamic_objects = [
            o for o in self.dynamic_objects if not isinstance(o, LeverWall)
        ]
        self._index_dirty = True
        self.recompile_circuits()
