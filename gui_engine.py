"""
gui_engine.py
-------------
Graphical game engine for "Type Is Code".

Renders every entity as procedural Canvas shapes (via tile_renderer)
instead of text glyphs.  The window is fully resizable — cell size is
recomputed dynamically so that the board always fills the available
canvas area.  Arrow keys are supported alongside W/A/S/D.
"""

from __future__ import annotations
from graficial import Window
from levels_data import ALL_LEVELS
from tile_renderer import (
    draw_wall, draw_floor, draw_goal, draw_player,
    draw_void,
    draw_door_closed, draw_door_open,
    draw_trap_lethal, draw_trap_safe,
    draw_boom_explosion,
    draw_code_block,
)

# ── colour tokens (info-panel only) ─────────────────────────────────
BACKGROUND     = "#0f1323"
PANEL_BG       = "#111528"
PANEL_SECTION  = "#181e3a"
TEXT_COLOR      = "#e0e4ff"
TEXT_DIM        = "#8890b0"
ACCENT         = "#5f7fff"
SUCCESS_COLOR   = "#4adc6e"
DANGER_COLOR    = "#e05565"

# Board chrome
BOARD_BG       = "#0e1225"
BOARD_BORDER   = "#3a4a80"
BOARD_PADDING  = 8

# ── per-level hints (HINTS panel) ───────────────────────────────────
# One entry per level in ALL_LEVELS, index-aligned with level_index.
# Lines stay under ~44 characters so they fit the panel's text view.
LEVEL_HINTS = [
    "The gap ahead is a void, not ground.\n"
    "It obeys the circuit: Platform.isSolid\n"
    "is false.  Push the spare `true` block\n"
    "into the empty slot to seal it.",

    "The Door stays shut while Door.isOpen\n"
    "is false.  Push the spare `true` block\n"
    "into the statement's last slot and the\n"
    "door swings open.",

    "Two problems, two workshops — each\n"
    "room must be cleared before the\n"
    "obstacle it controls.  Disarm the trap\n"
    "(isLethal = false), then seal the void\n"
    "(isSolid = true) using each room's\n"
    "spare block.",

    "Both statements need fixing: seal the\n"
    "void (isSolid = true) and open the Door\n"
    "(isOpen = true).  The corridor goal is\n"
    "mined — fuse a new GOAL by pushing the\n"
    "Path. and open tokens together.  One\n"
    "contact is enough.",

    "Only two `false` blocks exist.  Swap\n"
    "blue's false for the hub `true` to seal\n"
    "the void, then feed that freed false\n"
    "into the Wall statement: passable walls\n"
    "open the sealed annex.  Its false arms\n"
    "the Trap — walk the corridor to the flag.",

    "True down seals both tables (Path).\n"
    "True up opens the Door.  Drop into\n"
    "the vault, push NOT up-right into\n"
    "the Trap slot, True beside it: NOT\n"
    "True is False.  Cross the trap.",

    "Push NOT up into the Path rule: NOT\n"
    "True is False, the gap table goes.\n"
    "Push the second NOT up into the Door\n"
    "rule, False beside it: NOT False is\n"
    "True.  Through the door.",

    "Push False out of the Door rule (it\n"
    "reverts to False), carry it to the\n"
    "Trap rule, slide True into the Door\n"
    "slot.  Back down and cross the trap.",

    "True opens Room 1's door.  True goes\n"
    "through it, down into the Path rule.\n"
    "True crosses the dead table to room\n"
    "3.  NOT up, True beside it: trap off.\n"
    "Cross to the flag.",
]


class GUIEngine:
    # ── construction ────────────────────────────────────────────────
    def __init__(self, start_index: int = 0):
        if not 0 <= start_index < len(ALL_LEVELS):
            raise ValueError(f"Invalid start_index {start_index}. Choose 0-{len(ALL_LEVELS) - 1}.")
        self.level_index = start_index
        self.game_completed = False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self._last_message = ""

        # window + layout
        self.window = Window("Type Is Code", 1200, 640, bg=BACKGROUND,
                             min_width=900, min_height=480)
        self.canvas = self.window.create_canvas(bg=BOARD_BG)
        self._build_info_panel()

        # input bindings
        self.window.on_key_down(self.on_key)
        self.window.on_resize(self._on_resize)
        self.window.focus()

        # initial render (deferred so geometry is settled)
        self.window.root.after(50, lambda: self.render_frame(self._last_message))

    def _build_info_panel(self):
        self.info_frame = self.window.create_frame(width=380)
        self.status_label = self.info_frame.add_label(
            "", font=("Consolas", 14, "bold"), fg=TEXT_COLOR, bg=PANEL_BG)
        self.moves_label = self.info_frame.add_label(
            "", font=("Consolas", 11), fg=TEXT_DIM, bg=PANEL_BG)
        self.info_frame.add_label(
            "🎮 Controls", font=("Consolas", 12, "bold"),
            fg=ACCENT, bg=PANEL_BG)
        self.help_view = self.info_frame.add_text_view(
            width=44, height=6, fg=TEXT_DIM, bg=PANEL_SECTION)
        self.hints_label = self.info_frame.add_label(
            "💡 HINTS", font=("Consolas", 12, "bold"),
            fg=ACCENT, bg=PANEL_BG)
        self.hints_view = self.info_frame.add_text_view(
            width=44, height=5, fg=TEXT_DIM, bg=PANEL_SECTION)

    # ── level lifecycle ─────────────────────────────────────────────
    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self, from_start: bool = False):
        if from_start or self.game_completed:
            self.level_index = 0
            self.game_completed = False
        self.level = self.current_builder()()
        self.level.reset()

    def next_level(self) -> bool:
        if self.level_index + 1 >= len(ALL_LEVELS):
            self.game_completed = True
            return False
        self.level_index += 1
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        return True

    # ── responsive resize ───────────────────────────────────────────
    def _on_resize(self, w: int, h: int):
        self.render_frame(self._last_message)

    # ── rendering ───────────────────────────────────────────────────
    def render_frame(self, message: str = ""):
        self._last_message = message or ""
        # settle pending geometry so the canvas reports its current size
        # (otherwise the board is drawn for the previous window size)
        self.window.root.update_idletasks()
        self.canvas.clear()
        raw = self.canvas.raw  # direct tk.Canvas for tile_renderer

        cols = self.level.width
        rows = self.level.height

        # compute cell size from available canvas area
        cw, ch = self.canvas.get_size()
        if cw < 10 or ch < 10:
            return  # canvas not ready yet

        avail_w = cw - 2 * BOARD_PADDING
        avail_h = ch - 2 * BOARD_PADDING
        cell = min(avail_w // cols, avail_h // rows)
        cell = max(20, cell)  # never smaller than 20px

        board_w = cell * cols
        board_h = cell * rows
        ox = (cw - board_w) // 2   # center board horizontally
        oy = (ch - board_h) // 2   # center board vertically

        # board background + border
        raw.create_rectangle(ox - 3, oy - 3,
                             ox + board_w + 3, oy + board_h + 3,
                             fill="", outline=BOARD_BORDER, width=2)

        # ── draw every cell ──
        # Global levels layer each cell: floor/goal tile -> terrain ->
        # block on top -> player.  The block chip is inset, so the terrain
        # rim (open door, vanished table) stays visible underneath.
        is_global = getattr(self.level, "rule_mode", "circuit") == "global"
        if is_global:
            for gy in range(rows):
                for gx in range(cols):
                    px = ox + gx * cell
                    py = oy + gy * cell
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__

                    # 1. background tile
                    if tile_cls == "Wall":
                        draw_wall(raw, px, py, cell)
                    elif tile_cls == "Goal":
                        draw_goal(raw, px, py, cell)
                    else:
                        draw_floor(raw, px, py, cell)

                    # 2. terrain layer
                    terr = self.level.terrain_at(gx, gy)
                    tcls = terr.__class__.__name__ if terr is not None else ""
                    if tcls == "Door":
                        if terr.is_blocking():
                            draw_door_closed(raw, px, py, cell)
                        else:
                            draw_door_open(raw, px, py, cell)
                    elif tcls == "Trap":
                        if terr.is_lethal():
                            draw_trap_lethal(raw, px, py, cell)
                        else:
                            draw_trap_safe(raw, px, py, cell)
                    elif tcls == "Platform":
                        if terr.is_void():
                            draw_void(raw, px, py, cell)
                        else:
                            draw_floor(raw, px, py, cell)

                    # 3. block layer on top
                    blk = self.level.block_at(gx, gy)
                    if blk is not None:
                        draw_code_block(raw, px, py, cell,
                                        blk.glyph().strip(), blk.kind)

                    # 4. player layer
                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)
                    if is_player:
                        if self.level.dead:
                            under = self.level.terrain_at(gx, gy)
                            if self.level.player_invisible:
                                # drowned in the void: character is gone
                                draw_void(raw, px, py, cell)
                            elif under is not None and under.is_lethal():
                                draw_boom_explosion(raw, px, py, cell)
                            else:
                                draw_player(raw, px, py, cell)
                        else:
                            draw_player(raw, px, py, cell)
        else:
            for gy in range(rows):
                for gx in range(cols):
                    px = ox + gx * cell
                    py = oy + gy * cell
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__

                    # 1. background tile — walls always look the same, passable or not
                    if tile_cls == "Wall":
                        draw_wall(raw, px, py, cell)
                    elif tile_cls == "Goal":
                        draw_goal(raw, px, py, cell)
                    else:
                        draw_floor(raw, px, py, cell)

                    # 2. dynamic object on top
                    occ = self.level.object_at(gx, gy)
                    cls = occ.__class__.__name__ if occ is not None else ""
                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)

                    if is_player and self.level.dead and cls in ("HiddenBoom", "BorderMine"):
                        draw_boom_explosion(raw, px, py, cell)
                    elif is_player and self.level.dead and self.level.player_invisible:
                        # Fell into the void: the character is gone — only the
                        # empty pit is drawn.
                        draw_void(raw, px, py, cell)
                    elif is_player:
                        draw_player(raw, px, py, cell)
                    elif occ is not None:
                        if cls == "Platform":
                            if occ.is_void():
                                draw_void(raw, px, py, cell)
                            else:
                                # Path.solid = True — void trap removed, plain floor
                                draw_floor(raw, px, py, cell)
                        elif cls == "Door":
                            if occ.is_blocking():
                                draw_door_closed(raw, px, py, cell)
                            else:
                                draw_door_open(raw, px, py, cell)
                        elif cls == "Trap":
                            if occ.is_lethal():
                                draw_trap_lethal(raw, px, py, cell)
                            else:
                                draw_trap_safe(raw, px, py, cell)
                        elif cls == "CodeBlock":
                            label = occ.glyph().strip()
                            kind = occ.kind
                            draw_code_block(raw, px, py, cell, label, kind)

        # ── info panel ──
        lvl_num = min(self.level_index + 1, len(ALL_LEVELS))
        if self.game_completed:
            self.status_label.configure(
                text=f"✅  ALL {len(ALL_LEVELS)} LEVELS COMPLETE!",
                fg=SUCCESS_COLOR)
        else:
            self.status_label.configure(
                text=f"Level {lvl_num}/{len(ALL_LEVELS)}:  {self.level.name}",
                fg=TEXT_COLOR)

        self.moves_label.configure(text=f"Moves: {self.level.moves}")
        help_text = (
            "W / ↑  = up        A / ← = left\n"
            "S / ↓  = down      D / → = right\n"
            "R = restart level\n"
            "Q = quit\n\n"
            "Push code blocks onto the circuit line so\n"
            "the statement compiles.  CLASS PROP = VALUE\n"
            "Put Path. next to open = they fuse into a new GOAL"
        )
        if getattr(self.level, "rule_mode", "circuit") == "global":
            help_text += ("\nRules read left to right in one row. "
                          "NOT flips the value after it.")
        self.help_view.set_text(help_text)
        # Hints panel exists only on level 4 (index 3); it is hidden
        # on every other level.
        if self.level_index == 3 and not self.game_completed:
            self.hints_label.pack(fill="x", padx=8, pady=3, anchor="nw")
            self.hints_view._text.pack(fill="x", padx=8, pady=2, anchor="nw")
            self.hints_view.set_text(LEVEL_HINTS[self.level_index])
        else:
            self.hints_label.pack_forget()
            self.hints_view._text.pack_forget()

    # ── input ───────────────────────────────────────────────────────
    def on_key(self, key: str):
        # map arrow keys to wasd
        arrow_map = {"up": "w", "down": "s", "left": "a", "right": "d"}
        key = arrow_map.get(key, key)

        if key == "q":
            self.window.root.destroy()
            return
        if key == "h":
            self.render_frame("Arrow keys or W/A/S/D to move.  R = restart.  Q = quit.")
            return
        if key == "r":
            from_start = self.game_completed
            self.restart_level(from_start=from_start)
            msg = "Game restarted from Level 1." if from_start else "Level restarted."
            self.render_frame(msg)
            return
        if key not in ("w", "a", "s", "d"):
            return

        # block movement after game completion
        if self.game_completed:
            self.render_frame(
                "All levels complete!  Press R to restart from Level 1, or Q to quit.")
            return

        msg = self.level.move_player(key)
        if self.level.won:
            if not self.next_level():
                self.render_frame(
                    "🎉 Congratulations!  You compiled your way through every level!  "
                    "Press R to play again or Q to quit.")
                return
            self.render_frame("Level solved!  New level loaded.")
            return
        if self.level.dead:
            self.render_frame(msg + "  Press R to restart.")
            return
        self.render_frame(msg)

    # ── entry point ─────────────────────────────────────────────────
    def run(self):
        self.window.run()
