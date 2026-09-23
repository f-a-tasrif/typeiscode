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
        self.help_view.set_text(
            "W / ↑  = up        A / ← = left\n"
            "S / ↓  = down      D / → = right\n"
            "R = restart level\n"
            "Q = quit\n\n"
            "Push code blocks onto the circuit line so\n"
            "the statement compiles.  CLASS PROP = VALUE\n"
            "Put Path. next to open = they fuse into a new GOAL"
        )

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
