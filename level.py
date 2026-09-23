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
from game_object import GameObject, Wall, Floor, Goal, Player, Platform, Door, Trap, HiddenBoom, BorderMine
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

    # -- lookups --------------------------------------------------------
    def object_at(self, x, y) -> GameObject | None:
        for obj in self.dynamic_objects:
            if obj.x == x and obj.y == y:
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

    # -- core game loop ---------------------------------------------------
    def recompile_circuits(self):
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

        # If the logic just collapsed the path the character is standing on
        # back into a void, it falls in on the spot.
        if self.player is not None and not self.won and not self.dead:
            standing = self.object_at(self.player.x, self.player.y)
            if isinstance(standing, Platform) and standing.is_void():
                self.dead = True
                self.player_invisible = True

    def move_player(self, direction: str) -> str:
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
                target = self.object_at(bx, by)
                if target is not None:
                    # Shoving the Path./open pair straight into each other
                    # fuses them on the spot.
                    if is_merge_pair(occ, target):
                        return self._fuse_pair(occ, target)
                    return "Can't push -- something is already there."
                occ.x, occ.y = bx, by
                self.player.x, self.player.y = nx, ny
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
                self.moves += 1
                if occ.is_lethal():
                    self.dead = True
                    if isinstance(occ, Platform) and occ.is_void():
                        self.player_invisible = True
                        return ("You fell into the void!  The character "
                                "vanishes into the dark.  Game over.")
                    if isinstance(occ, (HiddenBoom, BorderMine)):
                        return "BOOM! The hidden explosive burst and blew you to pieces!"
                    return "You stepped on a live trap! Game over."
        else:
            self.player.x, self.player.y = nx, ny
            self.moves += 1

        if isinstance(tile, Goal) and (self.player.x, self.player.y) == (nx, ny):
            self.won = True
            return "You reached the goal! Level complete."

        return ""

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
                else:
                    occ = self.object_at(x, y)
                    if occ is not None:
                        glyph = occ.glyph()
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
        self.recompile_circuits()
