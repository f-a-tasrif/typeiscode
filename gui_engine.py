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
from registry import PropertyRegistry
from tile_renderer import (
    draw_wall, draw_floor, draw_goal, draw_player,
    draw_void,
    draw_door_closed, draw_door_open,
    draw_trap_lethal, draw_trap_safe,
    draw_boom_explosion,
    draw_code_block,
    draw_stone,
    draw_seal_wall, draw_warp, draw_mine,
    get_canvas_photo, get_panel_photo, get_panel_slice,
)

# ── colour tokens (info-panel only) ─────────────────────────────────
BACKGROUND     = "#0f1323"
PANEL_BG       = "#111528"
PANEL_SECTION  = "#1d2447"
TEXT_COLOR      = "#eef1ff"
TEXT_BODY       = "#d9defa"
TEXT_DIM        = "#a8b0d0"
ACCENT         = "#8aa2ff"
SUCCESS_COLOR   = "#4adc6e"
DANGER_COLOR    = "#e05565"

# Board chrome
BOARD_BG       = "#0e1225"
BOARD_BORDER   = "#3a4a80"
BOARD_PADDING  = 8

# ── follow-camera (rooms come closer) ─────────────────────────────
# Instead of shrinking the whole map to fit, keep cells large and show
# a viewport that follows the player. Small levels still fit entirely;
# big levels (e.g. 44-50 cols) render zoomed-in around the player.
CAM_VIEW_COLS  = 20   # target visible columns when zoomed
CAM_VIEW_ROWS  = 13   # target visible rows when zoomed
CAM_MAX_CELL   = 56   # cap for zoomed cell size (px)
CAM_MIN_CELL   = 8    # floor so tiny windows never divide by zero
CAM_SMOOTH     = 1.0  # 1.0 = snap to player; <1.0 = eased follow
CAM_ZOOM_MIN   = 0.6
CAM_ZOOM_MAX   = 2.0

# ── per-level hints (HINTS panel) ───────────────────────────────────
# One entry per level in ALL_LEVELS, index-aligned with level_index.
# Only level 8 carries hint text; all other entries are blank and the
# HINTS section stays hidden on those levels.
LEVEL_HINTS = [
"",

"",

"",

"",

"",

"",

"",

"1. There lies hidden bombs,\n"
        "where the player must succumb,\n"
        "discovers a path without turning into crumbs.\n"
    "2. Two meaningful blocks can be fused into one.\n",

"",

    "",
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
        self._show_warps = True
        self._label_photos: dict[str, object] = {}
        self._panel_bg_key = None
        # follow-camera state: smoothed center in cell coords + zoom factor
        self._zoom = 1.0
        self._cam_cx: float | None = None
        self._cam_cy: float | None = None

        # window + layout
        self.window = Window("Type Is Code", 1280, 680, bg=BACKGROUND,
                             min_width=980, min_height=560)
        self.canvas = self.window.create_canvas(bg=BOARD_BG)
        self._build_info_panel()

        # input bindings
        self.window.on_key_down(self.on_key)
        self.window.on_resize(self._on_resize)
        self.window.focus()

        # initial render (deferred so geometry is settled)
        self.window.root.after(50, lambda: self.render_frame(self._last_message))

    def _build_info_panel(self):
        self.info_frame = self.window.create_frame(width=430)
        self.status_label = self.info_frame.add_label(
            "", font=("Consolas", 16, "bold"), fg=TEXT_COLOR, bg=PANEL_BG,
            wraplength=405)
        self.moves_label = self.info_frame.add_label(
            "", font=("Consolas", 13), fg=TEXT_DIM, bg=PANEL_BG)
        self.message_label = self.info_frame.add_label(
            "", font=("Consolas", 12, "italic"), fg=TEXT_BODY, bg=PANEL_BG,
            wraplength=405)
        self.controls_label = self.info_frame.add_label(
            "🎮 Controls", font=("Consolas", 14, "bold"),
            fg=ACCENT, bg=PANEL_BG)
        self.help_view = self.info_frame.add_text_view(
            width=44, height=7, font=("Consolas", 12),
            fg=TEXT_BODY, bg=PANEL_SECTION)
        self.hints_label = self.info_frame.add_label(
            "💡 HINTS", font=("Consolas", 14, "bold"),
            fg=ACCENT, bg=PANEL_BG)
        self.hints_view = self.info_frame.add_text_view(
            width=44, height=8, font=("Consolas", 12),
            fg=TEXT_BODY, bg=PANEL_SECTION)

    # ── level lifecycle ─────────────────────────────────────────────
    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self, from_start: bool = False):
        if from_start or self.game_completed:
            self.level_index = 0
            self.game_completed = False
        self.level = self.current_builder()()
        self.level.reset()
        self._snap_camera_to_player()

    def next_level(self) -> bool:
        if self.level_index + 1 >= len(ALL_LEVELS):
            self.game_completed = True
            return False
        self.level_index += 1
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self._snap_camera_to_player()
        return True

    # ── responsive resize ───────────────────────────────────────────
    def _on_resize(self, w: int, h: int):
        self.render_frame(self._last_message)

    # ── follow-camera ─────────────────────────────────────────────
    def _snap_camera_to_player(self):
        """Center the camera on the player (called on level load)."""
        p = getattr(self.level, "player", None)
        if p is not None:
            self._cam_cx = p.x + 0.5
            self._cam_cy = p.y + 0.5
        else:
            self._cam_cx = self.level.width / 2
            self._cam_cy = self.level.height / 2

    def _compute_camera(self, cols: int, rows: int,
                        cw: int, ch: int, avail_w: int, avail_h: int):
        """Return (cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy).

        Small boards fit entirely (no scrolling). Big boards keep a
        large cell size and scroll a viewport that follows the player,
        so rooms stay close to the screen.
        """
        import math

        fit = min(avail_w // max(1, cols), avail_h // max(1, rows))
        fit = max(1, fit)
        want = min(avail_w // CAM_VIEW_COLS, avail_h // CAM_VIEW_ROWS)
        want = max(CAM_MIN_CELL, want)
        want = min(want, CAM_MAX_CELL)
        want = max(1, int(round(want * self._zoom)))

        if want <= fit:
            # Whole board fits at a comfortable size -- no scrolling.
            cell = fit
            view_cols, view_rows = cols, rows
            cam_x0 = 0.0
            cam_y0 = 0.0
            board_w = cell * cols
            board_h = cell * rows
            ox = (cw - board_w) // 2
            oy = (ch - board_h) // 2
            self._snap_camera_to_player()
            return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy

        # Zoomed mode: keep cells big, scroll to the player.
        cell = want
        view_cols = max(1, avail_w // cell)
        view_rows = max(1, avail_h // cell)
        view_cols = min(view_cols, cols)
        view_rows = min(view_rows, rows)

        p = getattr(self.level, "player", None)
        tx = (p.x + 0.5) if p is not None else cols / 2
        ty = (p.y + 0.5) if p is not None else rows / 2
        if self._cam_cx is None or self._cam_cy is None:
            self._cam_cx, self._cam_cy = tx, ty
        else:
            k = CAM_SMOOTH
            self._cam_cx += (tx - self._cam_cx) * k
            self._cam_cy += (ty - self._cam_cy) * k

        max_x0 = max(0.0, float(cols - view_cols))
        max_y0 = max(0.0, float(rows - view_rows))
        cam_x0 = min(max(self._cam_cx - view_cols / 2, 0.0), max_x0)
        cam_y0 = min(max(self._cam_cy - view_rows / 2, 0.0), max_y0)

        board_w = view_cols * cell
        board_h = view_rows * cell
        ox = (cw - board_w) // 2
        oy = (ch - board_h) // 2
        return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy

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
        win_w, win_h = self.window.root.winfo_width(), self.window.root.winfo_height()

        avail_w = cw - 2 * BOARD_PADDING
        avail_h = ch - 2 * BOARD_PADDING
        cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy = \
            self._compute_camera(cols, rows, cw, ch, avail_w, avail_h)
        board_w = view_cols * cell
        board_h = view_rows * cell
        # visible cell range (clipped to the board)
        import math as _math
        x0i = max(0, int(_math.floor(cam_x0)))
        y0i = max(0, int(_math.floor(cam_y0)))
        x1i = min(cols, int(_math.ceil(cam_x0 + view_cols)))
        y1i = min(rows, int(_math.ceil(cam_y0 + view_rows)))

        def _px(gx: int) -> int:
            return int(round(ox + (gx - cam_x0) * cell))

        def _py(gy: int) -> int:
            return int(round(oy + (gy - cam_y0) * cell))

        # night-crystal backdrop behind the board: left crop of the ONE
        # window-sized image, so it continues seamlessly into the panel
        try:
            bg_photo = get_canvas_photo(win_w, win_h, cw, ch)
        except Exception:
            bg_photo = None
        if bg_photo is not None:
            self._bg_photo = bg_photo  # keep a ref so Tk does not blank it
            raw.create_image(0, 0, image=bg_photo, anchor="nw")

        # board drop shadow for lifted-map 3D look
        raw.create_rectangle(ox - 3 + 6, oy - 3 + 8,
                             ox + board_w + 3 + 6, oy + board_h + 3 + 8,
                             fill="#05070f", outline="")

        # teal glow rim around the board, like the reference mockup
        for pad, color in ((10, "#0e3a40"), (7, "#155e63"), (4, "#2aa5a0")):
            raw.create_rectangle(ox - pad, oy - pad,
                                 ox + board_w + pad, oy + board_h + pad,
                                 fill="", outline=color, width=2)

        # board background + border
        raw.create_rectangle(ox - 3, oy - 3,
                             ox + board_w + 3, oy + board_h + 3,
                             fill="", outline=BOARD_BORDER, width=2)

        # ── draw every cell ──
        # Global levels layer each cell: floor/goal tile -> terrain ->
        # block on top -> player.  The block chip is inset, so the terrain
        # rim (open door, vanished table) stays visible underneath.
        is_global = getattr(self.level, "rule_mode", "circuit") == "global"
        # Relocated-flag state (map10): the visible Goals are decoys and
        # the finish art belongs on the hidden chamber cell instead.
        flag_moved = bool(PropertyRegistry.get("Flag", "moved", False))
        flag2 = getattr(self.level, "flag2", None)
        if is_global:
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__

                    # 1. background tile (decoy Goals read as floor relocated)
                    if tile_cls == "Wall":
                        draw_wall(raw, px, py, cell)
                    elif tile_cls == "Goal":
                        if flag_moved:
                            draw_floor(raw, px, py, cell)
                        else:
                            draw_goal(raw, px, py, cell)
                    else:
                        draw_floor(raw, px, py, cell)
                        if flag_moved and flag2 is not None and (gx, gy) == flag2:
                            draw_goal(raw, px, py, cell)

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
                    elif tcls == "Stone":
                        if terr.is_blocking():
                            draw_stone(raw, px, py, cell)
                        else:
                            draw_floor(raw, px, py, cell)
                    elif tcls == "SealWall":
                        if terr.is_blocking():
                            draw_seal_wall(raw, px, py, cell)
                        else:
                            draw_floor(raw, px, py, cell)
                    elif tcls == "Warp":
                        # Portals are visible by default (P toggles reveal/hide).
                        if getattr(self, "_show_warps", True):
                            draw_warp(raw, px, py, cell)
                        # else: drawn as plain floor (background tile already drawn in step 1)
                    elif tcls in ("HiddenBoom", "HardMine"):
                        # Land mines stay visible in global levels (level 9):
                        # pixel-bomb marker on the floor.
                        draw_mine(raw, px, py, cell)

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
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
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
                        elif cls == "Stone":
                            if occ.is_blocking():
                                draw_stone(raw, px, py, cell)
                            else:
                                draw_floor(raw, px, py, cell)
                        elif cls == "SealWall":
                            if occ.is_blocking():
                                draw_seal_wall(raw, px, py, cell)
                            else:
                                draw_floor(raw, px, py, cell)
                        elif cls == "Warp":
                            # Portals are visible by default (P toggles reveal/hide).
                            if getattr(self, "_show_warps", True):
                                draw_warp(raw, px, py, cell)
                            # else: drawn as plain floor (background tile already drawn in step 1)
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
        # Game feedback message — previously stored but never shown.
        if self._last_message:
            msg_fg = DANGER_COLOR if self.level.dead else TEXT_BODY
            self.message_label.configure(text=f"▶ {self._last_message}", fg=msg_fg)
            if not self.message_label.winfo_ismapped():
                self.message_label.pack(fill="x", padx=12, pady=5, anchor="nw")
        else:
            self.message_label.pack_forget()
        press = getattr(self.level, "fusion_press_count", 0)
        if press > 0:
            self.message_label.configure(
                text=f"⚙ Stone. + open: {press}/3 presses to fuse",
                fg=ACCENT)
            if not self.message_label.winfo_ismapped():
                self.message_label.pack(fill="x", padx=12, pady=5, anchor="nw")
        help_text = (
            "W / ↑  = up        A / ← = left\n"
            "S / ↓  = down      D / → = right\n"
            "R = restart level   C = center camera\n"
            "+ / - = zoom in / out\n"
            "Q = quit\n\n"
            "Push code blocks onto the circuit line so\n"
            "the statement compiles.  CLASS PROP = VALUE\n\n"
            "Big maps use a follow-camera: the view\n"
            "stays zoomed on your room and scrolls\n"
            "as you move."
        )
        self.help_view.set_text(help_text)
        # Hints panel shows only when the current level carries hint
        # text (currently level 8); otherwise the section stays hidden.
        hint = LEVEL_HINTS[self.level_index] if 0 <= self.level_index < len(LEVEL_HINTS) else ""
        if not self.game_completed and hint:
            if not self.hints_label.winfo_ismapped():
                self.hints_label.pack(fill="x", padx=12, pady=5, anchor="nw")
            if not self.hints_view._text.winfo_ismapped():
                self.hints_view._text.pack(fill="x", padx=12, pady=4, anchor="nw")
            self.hints_view.set_text(hint)
        else:
            self.hints_label.pack_forget()
            self.hints_view._text.pack_forget()

        self._paint_panel_backdrop()

    def _paint_panel_backdrop(self):
        """Dress the whole side panel in the night art (darkened for text).

        Frame gaps show the full-panel slice; each header/status label
        gets its own aligned slice behind its text.  Repaints only when
        the window/panel size changes — never from widget geometry, so
        moves never visibly shift the panel.  Skipped (leaving the flat
        colours) when geometry is unset or the art is unavailable.
        """
        try:
            frame = self.info_frame._frame
            root = self.window.root
            win_w, win_h = root.winfo_width(), root.winfo_height()
            panel_w, panel_h = frame.winfo_width(), frame.winfo_height()
            if win_w < 50 or win_h < 50 or panel_w < 50 or panel_h < 50:
                return
            key = (win_w, win_h, panel_w, panel_h)
            if key == self._panel_bg_key:
                return
            root.update_idletasks()
            win_w, win_h = root.winfo_width(), root.winfo_height()
            panel_w, panel_h = frame.winfo_width(), frame.winfo_height()
            if win_w < 50 or win_h < 50 or panel_w < 50 or panel_h < 50:
                return
            key = (win_w, win_h, panel_w, panel_h)
            if key == self._panel_bg_key:
                return
            self._panel_bg_key = key
            bg = get_panel_photo(win_w, win_h, panel_w)
            if bg is None:
                return
            self.info_frame.set_background(bg)
            for name, lab in (("status", self.status_label),
                              ("moves", self.moves_label),
                              ("message", self.message_label),
                              ("controls", self.controls_label),
                              ("hints", self.hints_label)):
                if not lab.winfo_ismapped():
                    continue
                lx, ly, lw, lh = (lab.winfo_x(), lab.winfo_y(),
                                  lab.winfo_width(), lab.winfo_height())
                photo = get_panel_slice(lx, ly, lw, lh, win_w, win_h, panel_w)
                if photo is None:
                    continue
                self._label_photos[name] = photo
                lab.configure(image=photo, compound="center")
        except Exception:
            return

    # ── input ───────────────────────────────────────────────────────
    def on_key(self, key: str):
        # map arrow keys to wasd
        arrow_map = {"up": "w", "down": "s", "left": "a", "right": "d"}
        key = arrow_map.get(key, key)

        if key == "q":
            self.window.root.destroy()
            return
        if key == "h":
            self.render_frame("Arrows/WASD move. R=restart. +/-=zoom. C=center. Q=quit.")
            return
        if key == "r":
            from_start = self.game_completed
            self.restart_level(from_start=from_start)
            msg = "Game restarted from Level 1." if from_start else "Level restarted."
            self.render_frame(msg)
            return
        if key == "p":
            self._show_warps = not getattr(self, "_show_warps", False)
            self.render_frame("Portals " + ("revealed." if self._show_warps else "hidden."))
            return
        if key in ("plus", "equal", "kp_add"):
            self._zoom = min(CAM_ZOOM_MAX, self._zoom + 0.15)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- rooms closer.")
            return
        if key in ("minus", "kp_subtract"):
            self._zoom = max(CAM_ZOOM_MIN, self._zoom - 0.15)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- see more rooms.")
            return
        if key == "c":
            self._snap_camera_to_player()
            self.render_frame("Camera centered on player.")
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
