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
from game_object import GameObject, Wall, Floor, Goal, Player, Platform, Door, Trap
from blocks import CodeBlock, CircuitLine
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
        self.moves = 0

    # -- level construction helpers -----------------------------------
    def add_wall_border(self):
        for x in range(self.width):
            self.tiles[(x, 0)] = Wall(x, 0)
            self.tiles[(x, self.height - 1)] = Wall(x, self.height - 1)
        for y in range(self.height):
            self.tiles[(0, y)] = Wall(0, y)
            self.tiles[(self.width - 1, y)] = Wall(self.width - 1, y)

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
        bpos = self.blocks_by_pos()
        for c in self.circuits:
            c.try_compile(bpos)

    def move_player(self, direction: str) -> str:
        """Attempt to move the player. Returns a short status message."""
        if direction not in DIRS or self.won or self.dead:
            return ""
        dx, dy = DIRS[direction]
        nx, ny = self.player.x + dx, self.player.y + dy

        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return "You can't leave the grid."

        tile = self.tile_at(nx, ny)
        if isinstance(tile, Wall):
            return "A wall blocks the way."

        occ = self.object_at(nx, ny)
        if occ is not None:
            if isinstance(occ, CodeBlock):
                # try to push it; if the destination is occupied by another
                # movable block, allow the push only when the block can slide
                # into the next cell as a swap.
                bx, by = nx + dx, ny + dy
                if not (0 <= bx < self.width and 0 <= by < self.height):
                    return "Can't push that off the grid."
                beyond_tile = self.tile_at(bx, by)
                if isinstance(beyond_tile, Wall):
                    return "Can't push -- wall behind the block."
                target = self.object_at(bx, by)
                if target is not None:
                    if isinstance(target, CodeBlock):
                        if not (0 <= bx + dx < self.width and 0 <= by + dy < self.height):
                            return "Can't push -- blocked by the edge."
                        if isinstance(self.tile_at(bx + dx, by + dy), Wall):
                            return "Can't push -- wall behind the block."
                        if self.object_at(bx + dx, by + dy) is not None:
                            return "Can't push -- something is already there."
                        target.x, target.y = bx + dx, by + dy
                    else:
                        return "Can't push -- something is already there."
                occ.x, occ.y = bx, by
                self.player.x, self.player.y = nx, ny
                self.moves += 1
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
                    return "You stepped on a live trap! Game over."
        else:
            self.player.x, self.player.y = nx, ny
            self.moves += 1

        if isinstance(tile, Goal) and (self.player.x, self.player.y) == (nx, ny):
            self.won = True
            return "You reached the goal! Level complete."

        return ""

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
                if self.player and self.player.x == x and self.player.y == y:
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
        self.recompile_circuits()
