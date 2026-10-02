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
    draw_ash,
    draw_skeleton,
    draw_code_block,
    draw_stone,
    draw_laser,
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
TARGET_FPS     = 120  # game loop target refresh rate
CAM_FRAME_MS   = 8    # animation tick (~120fps: 1000/120 = 8.3ms)
RESIZE_DEBOUNCE_MS = 60  # coalesce drag-resize events into one redraw
CAM_LERP       = 0.35 # per-tick easing toward the player (higher = snappier)
CAM_EPS        = 0.03 # stop animating below this distance (cells)
CAM_ZOOM_LERP  = 0.35 # per-tick easing for smooth zoom
CAM_ZOOM_EPS   = 0.01
CAM_ZOOM_MIN   = 0.2
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

    "",

"",
]


HELP_PANEL_TEXT = (
    "WASD / arrows move, R restart, C center camera,\n"
    "+/- zoom, 0/F fit map, Q quit.\n\n"
    "Push code blocks onto the circuit line so\n"
    "the statement compiles.  CLASS PROP = VALUE\n\n"
    "Big maps use a follow-camera: the view\n"
    "stays zoomed on your room and scrolls\n"
    "as you move."
)


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
        # _cam_cx/_cam_cy/_zoom_cur are what is drawn; _zoom is the target.
        # A Tk `after` loop eases the drawn values toward the target so
        # movement glides instead of snapping.
        self._zoom = 1.0
        self._zoom_cur = 1.0
        self._cam_cx: float | None = None
        self._cam_cy: float | None = None
        self._cam_anim: str | None = None
        self._panel_cache: tuple | None = None
        # perf state: resize debounce, geometry cache, frame timing
        self._resize_pending: str | None = None
        self._last_win_size: tuple[int, int] | None = None
        self._last_render_ms: float = 0.0
        # incremental board cache: when the camera/cell geometry is
        # unchanged (typical in full-map view), only repaint cells whose
        # visual signature changed instead of clearing the whole canvas.
        self._board_geom = None
        self._cell_sigs: dict[tuple[int, int], tuple] = {}

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
        # Static help text is set once here, never per-frame: the old code
        # rewrote this Text widget on every move (panel key includes moves),
        # and each Tk Text delete+insert costs input latency.
        self.help_view.set_text(HELP_PANEL_TEXT)
        self._last_hint: str | None = None

    # ── level lifecycle ─────────────────────────────────────────────
    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self, from_start: bool = False):
        if from_start or self.game_completed:
            self.level_index = 0
            self.game_completed = False
        self._cancel_camera_anim()
        self.level = self.current_builder()()
        self.level.reset()
        self._snap_camera_to_player()

    def next_level(self) -> bool:
        if self.level_index + 1 >= len(ALL_LEVELS):
            self.game_completed = True
            return False
        self._cancel_camera_anim()
        self.level_index += 1
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self._snap_camera_to_player()
        return True

    # ── responsive resize ───────────────────────────────────────────
    def _on_resize(self, w: int, h: int):
        # Dragging the edge fires dozens of <Configure> events/sec; each
        # full redraw costs ~one frame, so the queue felt "late". Debounce
        # into a single redraw after the burst settles.
        try:
            if self._resize_pending is not None:
                self.window.root.after_cancel(self._resize_pending)
        except Exception:
            pass
        try:
            self._resize_pending = self.window.root.after(
                RESIZE_DEBOUNCE_MS, self._do_resize)
        except Exception:
            self._resize_pending = None

    def _do_resize(self):
        self._resize_pending = None
        self.render_frame(self._last_message)

    # ── follow-camera ─────────────────────────────────────────────
    def _snap_camera_to_player(self):
        """Center the camera on the player (called on level load)."""
        self._cancel_camera_anim()
        p = getattr(self.level, "player", None)
        if p is not None:
            self._cam_cx = p.x + 0.5
            self._cam_cy = p.y + 0.5
        else:
            self._cam_cx = self.level.width / 2
            self._cam_cy = self.level.height / 2
        self._zoom_cur = self._zoom

    def _camera_target(self) -> tuple[float, float]:
        """Where the camera wants to be (player center, or map center)."""
        p = getattr(self.level, "player", None)
        if p is not None:
            return p.x + 0.5, p.y + 0.5
        return self.level.width / 2, self.level.height / 2

    def _camera_needs_anim(self) -> bool:
        """True while the drawn camera/zoom still lags behind the target."""
        if self._cam_cx is None or self._cam_cy is None:
            return True
        tx, ty = self._camera_target()
        if abs(tx - self._cam_cx) > CAM_EPS:
            return True
        if abs(ty - self._cam_cy) > CAM_EPS:
            return True
        if abs(self._zoom - self._zoom_cur) > CAM_ZOOM_EPS:
            return True
        return False

    def _cancel_camera_anim(self):
        anim, self._cam_anim = self._cam_anim, None
        if anim is not None:
            try:
                self.window.root.after_cancel(anim)
            except Exception:
                pass

    def _nudge_camera_toward_target(self, alpha: float = 0.6):
        """Pre-step drawn camera toward the player before a full render.

        Movement keys call this so the character reads instantly while
        the remaining distance still glides in cheap board-only ticks.
        """
        try:
            tx, ty = self._camera_target()
        except Exception:
            return
        if self._cam_cx is None or self._cam_cy is None:
            self._cam_cx, self._cam_cy = tx, ty
        else:
            self._cam_cx += (tx - self._cam_cx) * alpha
            self._cam_cy += (ty - self._cam_cy) * alpha
        try:
            self._zoom_cur += (self._zoom - self._zoom_cur) * alpha
        except Exception:
            pass

    def _request_camera_anim(self):
        if self._cam_anim is not None:
            return
        if not self._camera_needs_anim():
            return
        try:
            self._cam_anim = self.window.root.after(CAM_FRAME_MS, self._camera_tick)
        except Exception:
            self._cam_anim = None

    def _camera_tick(self):
        """Ease drawn camera/zoom toward the target, then redraw board only.

        Ticks redraw just the canvas (no panel/text/backdrop work) so
        key handling stays responsive while the view glides.
        """
        self._cam_anim = None
        try:
            tx, ty = self._camera_target()
            if self._cam_cx is None or self._cam_cy is None:
                self._cam_cx, self._cam_cy = tx, ty
                self._zoom_cur = self._zoom
            else:
                self._cam_cx += (tx - self._cam_cx) * CAM_LERP
                self._cam_cy += (ty - self._cam_cy) * CAM_LERP
                self._zoom_cur += (self._zoom - self._zoom_cur) * CAM_ZOOM_LERP
                if not self._camera_needs_anim():
                    # Close enough: snap exactly to avoid endless drift.
                    self._cam_cx, self._cam_cy = tx, ty
                    self._zoom_cur = self._zoom
            self.render_frame(self._last_message, board_only=True)
        except Exception:
            # Never let a background tick kill the game (e.g. window
            # destroyed mid-animation).
            self._cam_anim = None

    def _compute_camera(self, cols: int, rows: int,
                        cw: int, ch: int, avail_w: int, avail_h: int):
        """Return (cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy).

        Small boards fit entirely (no scrolling). Big boards keep a
        large cell size and scroll a viewport that follows the player,
        so rooms stay close to the screen.  The drawn camera
        (_cam_cx/_cam_cy/_zoom_cur) is eased toward the player by the
        animation loop; this method only reads it, never steps it.
        """
        import math

        zoom_cur = getattr(self, "_zoom_cur", getattr(self, "_zoom", 1.0))
        fit = min(avail_w // max(1, cols), avail_h // max(1, rows))
        fit = max(1, fit)
        want = min(avail_w // CAM_VIEW_COLS, avail_h // CAM_VIEW_ROWS)
        want = max(CAM_MIN_CELL, want)
        want = min(want, CAM_MAX_CELL)
        want = max(1, int(round(want * zoom_cur)))

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
            return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy

        # Zoomed mode: keep cells big, scroll to the player.
        cell = want
        view_cols = max(1, avail_w // cell)
        view_rows = max(1, avail_h // cell)
        view_cols = min(view_cols, cols)
        view_rows = min(view_rows, rows)

        tx, ty = self._camera_target()
        if self._cam_cx is None or self._cam_cy is None:
            self._cam_cx, self._cam_cy = tx, ty

        max_x0 = max(0.0, float(cols - view_cols))
        max_y0 = max(0.0, float(rows - view_rows))
        cam_x0 = min(max(self._cam_cx - view_cols / 2, 0.0), max_x0)
        cam_y0 = min(max(self._cam_cy - view_rows / 2, 0.0), max_y0)

        board_w = view_cols * cell
        board_h = view_rows * cell
        ox = (cw - board_w) // 2
        oy = (ch - board_h) // 2
        return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy

    def _zoom_for_full_map(self, avail_w: int, avail_h: int) -> float:
        """Zoom target that fits the whole current level on screen.

        Mirrors _compute_camera's fit-vs-want math: returns fit / want_base
        clamped to [CAM_ZOOM_MIN, CAM_ZOOM_MAX], so "fit map" always lands
        exactly where the renderer switches to whole-board mode.
        """
        cols = max(1, self.level.width)
        rows = max(1, self.level.height)
        fit = min(avail_w // cols, avail_h // rows)
        fit = max(1, fit)
        want_base = min(avail_w // CAM_VIEW_COLS, avail_h // CAM_VIEW_ROWS)
        want_base = max(CAM_MIN_CELL, want_base)
        want_base = min(want_base, CAM_MAX_CELL)
        if want_base <= 0:
            return CAM_ZOOM_MIN
        needed = fit / float(want_base)
        return max(CAM_ZOOM_MIN, min(float(CAM_ZOOM_MAX), needed))

    def fit_map_to_screen(self) -> float:
        """Zoom out (or in) just enough to show the full map. Returns zoom."""
        try:
            cw, ch = self.canvas.get_size()
        except Exception:
            cw, ch = 0, 0
        if cw < 10 or ch < 10:
            # Canvas not laid out yet: fall back to the minimum zoom so a
            # very early keypress still zooms out instead of doing nothing.
            self._zoom = CAM_ZOOM_MIN
        else:
            avail_w = cw - 2 * BOARD_PADDING
            avail_h = ch - 2 * BOARD_PADDING
            self._zoom = self._zoom_for_full_map(avail_w, avail_h)
        self._nudge_camera_toward_target(0.6)
        return self._zoom

    def _cell_sig(self, gx: int, gy: int) -> tuple:
        """Visual signature of one board cell for incremental repaints.

        Covers everything the painter reads for the cell: the static
        tile, terrain class + its live registry-derived state, the block
        on top, player presence + death variant, and the global flags
        (relocated flag, forged gate, portal visibility). Two frames with
        equal signatures paint identically, so the cell can be skipped.
        """
        tile = self.level.tile_at(gx, gy)
        parts: list = [tile.__class__.__name__]
        terr = self.level.terrain_at(gx, gy)
        if terr is None:
            parts.append(None)
        else:
            try:
                _b = terr.is_blocking()
            except Exception:
                _b = None
            try:
                _l = terr.is_lethal()
            except Exception:
                _l = None
            _void_fn = getattr(terr, "is_void", None)
            try:
                _v = _void_fn() if callable(_void_fn) else None
            except Exception:
                _v = None
            # Portal visibility only affects Warp cells: scoping it here
            # keeps a P-toggles-warps keypress to those cells alone.
            _w = bool(getattr(self, "_show_warps", True)) \
                if terr.__class__.__name__ == "Warp" else None
            parts.append((terr.__class__.__name__, _b, _l, _v, _w))
        blk = self.level.block_at(gx, gy)
        parts.append((blk.kind, blk.value) if blk is not None else None)
        p = getattr(self.level, "player", None)
        if p is not None and p.x == gx and p.y == gy:
            parts.append(("P", self.level.dead, self.level.player_invisible))
        else:
            parts.append(None)
        parts.append((
            bool(PropertyRegistry.get("Flag", "moved", False)),
            getattr(self.level, "flag2", None),
            bool(PropertyRegistry.get("Gate", "at", False)),
            getattr(self.level, "gate2", None),
        ))
        return tuple(parts)

    # ── rendering ───────────────────────────────────────────────────
    def render_frame(self, message: str = "", board_only: bool = False):
        import time as _time
        _t0 = _time.perf_counter()
        # Full renders own the message slot; camera ticks pass the
        # stored message back and must not clear it, and they skip all
        # panel work so input stays responsive while gliding.
        if not board_only:
            self._last_message = message or ""
        else:
            message = self._last_message
        if not board_only:
            # update_idletasks() forces a full layout pass and was the top
            # input-latency cost (every keypress paid it). The canvas size
            # only changes when the window does, so skip the flush when the
            # toplevel size is unchanged since the last frame.
            # Ticks skip this entirely: it forces layout and costs latency.
            try:
                _ww = self.window.root.winfo_width()
                _wh = self.window.root.winfo_height()
            except Exception:
                _ww, _wh = 0, 0
            if (_ww, _wh) != self._last_win_size:
                try:
                    self.window.root.update_idletasks()
                except Exception:
                    pass
                try:
                    _ww = self.window.root.winfo_width()
                    _wh = self.window.root.winfo_height()
                except Exception:
                    pass
                self._last_win_size = (_ww, _wh)
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
        # Single art path at every zoom: tiles must look identical whether
        # zoomed on a room or viewing the full map, so no LOD switching.
        # Speed in full-map view comes from the incremental repaint below,
        # not from cheaper art.
        fast = False
        board_w = view_cols * cell
        board_h = view_rows * cell
        # visible cell range (clipped to the board)
        import math as _math
        x0i = max(0, int(_math.floor(cam_x0)))
        y0i = max(0, int(_math.floor(cam_y0)))
        x1i = min(cols, int(_math.ceil(cam_x0 + view_cols)))
        y1i = min(rows, int(_math.ceil(cam_y0 + view_rows)))

        # Incremental repaint: if the camera/cell geometry is unchanged
        # since the last frame (the common case in full-map view), skip
        # the clear + chrome and overpaint only cells whose visual
        # signature changed. Every cell paint starts with a full-cell
        # opaque rect, so overpainting is artifact-free. Camera ticks
        # always take the full path (their geometry is mid-glide).
        geom_key = (cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy,
                    cw, ch, self.level_index, id(self.level))
        full = board_only or (geom_key != self._board_geom)
        changed: set[tuple[int, int]] | None = None
        if not full:
            changed = set()
            fresh: dict[tuple[int, int], tuple] = {}
            for _gy in range(y0i, y1i):
                for _gx in range(x0i, x1i):
                    _sig = self._cell_sig(_gx, _gy)
                    fresh[(_gx, _gy)] = _sig
                    if _sig != self._cell_sigs.get((_gx, _gy)):
                        changed.add((_gx, _gy))
            self._cell_sigs = fresh
        else:
            self._cell_sigs = {}
            self._board_geom = geom_key

        def _px(gx: int) -> int:
            return int(round(ox + (gx - cam_x0) * cell))

        def _py(gy: int) -> int:
            return int(round(oy + (gy - cam_y0) * cell))

        if full:
            self.canvas.clear()
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
        gate_on = bool(PropertyRegistry.get("Gate", "at", False))
        gate2 = getattr(self.level, "gate2", None)
        if is_global:
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
                    if not full and (gx, gy) not in changed:
                        continue
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__

                    # 1. background tile (decoy Goals read as floor relocated)
                    if tile_cls == "Wall":
                        draw_wall(raw, px, py, cell, fast=fast)
                    elif tile_cls == "Goal":
                        if flag_moved:
                            draw_floor(raw, px, py, cell, fast=fast)
                        else:
                            draw_goal(raw, px, py, cell, fast=fast)
                    else:
                        draw_floor(raw, px, py, cell, fast=fast)
                        if flag_moved and flag2 is not None and (gx, gy) == flag2:
                            draw_goal(raw, px, py, cell, fast=fast)
                        elif gate_on and gate2 is not None and (gx, gy) == gate2:
                            draw_goal(raw, px, py, cell, fast=fast)

                    # 2. terrain layer
                    terr = self.level.terrain_at(gx, gy)
                    tcls = terr.__class__.__name__ if terr is not None else ""
                    if tcls == "Door":
                        if terr.is_blocking():
                            draw_door_closed(raw, px, py, cell, fast=fast)
                        else:
                            draw_door_open(raw, px, py, cell, fast=fast)
                    elif tcls == "Trap":
                        if terr.is_lethal():
                            draw_trap_lethal(raw, px, py, cell, fast=fast)
                        else:
                            draw_trap_safe(raw, px, py, cell, fast=fast)
                    elif tcls == "Platform":
                        if terr.is_void():
                            draw_void(raw, px, py, cell, fast=fast)
                        else:
                            draw_floor(raw, px, py, cell, fast=fast)
                    elif tcls == "Stone":
                        if terr.is_blocking():
                            draw_stone(raw, px, py, cell, fast=fast)
                        else:
                            draw_floor(raw, px, py, cell, fast=fast)
                    elif tcls == "SealWall":
                        if terr.is_blocking():
                            draw_seal_wall(raw, px, py, cell, fast=fast)
                        else:
                            draw_floor(raw, px, py, cell, fast=fast)
                    elif tcls in ("Seal2Wall", "Seal3Wall"):
                        if terr.is_blocking():
                            draw_seal_wall(raw, px, py, cell, fast=fast)
                        else:
                            draw_floor(raw, px, py, cell, fast=fast)
                    elif tcls == "LatchDoor":
                        if terr.is_blocking():
                            draw_door_closed(raw, px, py, cell, fast=fast)
                        else:
                            draw_door_open(raw, px, py, cell, fast=fast)
                    elif tcls == "LaserDoor":
                        if terr.is_blocking():
                            draw_laser(raw, px, py, cell, active=True, fast=fast)
                        else:
                            draw_laser(raw, px, py, cell, active=False, fast=fast)
                    elif tcls == "Warp":
                        # Portals are visible by default (P toggles reveal/hide).
                        if getattr(self, "_show_warps", True):
                            draw_warp(raw, px, py, cell, fast=fast)
                        # else: drawn as plain floor (background tile already drawn in step 1)
                    elif tcls in ("HiddenBoom", "HardMine"):
                        # Land mines stay visible in global levels (level 9):
                        # pixel-bomb marker on the floor.
                        draw_mine(raw, px, py, cell, fast=fast)

                    # 3. block layer on top
                    blk = self.level.block_at(gx, gy)
                    if blk is not None:
                        draw_code_block(raw, px, py, cell,
                                        blk.glyph().strip(), blk.kind, fast=fast)

                    # 4. player layer
                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)
                    if is_player:
                        if self.level.dead:
                            under = self.level.terrain_at(gx, gy)
                            if self.level.player_invisible:
                                # drowned in the void: character is gone
                                draw_void(raw, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ == "LaserDoor"
                                    and under.is_lethal()):
                                # vaporised by live beams: ash pile
                                draw_ash(raw, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ in (
                                        "HiddenBoom", "BorderMine", "HardMine")):
                                # blown apart by a mine: ash pile
                                draw_ash(raw, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ == "Trap"
                                    and under.is_lethal()):
                                # killed by a live trap: skeleton
                                draw_skeleton(raw, px, py, cell, fast=fast)
                            elif under is not None and under.is_lethal():
                                draw_boom_explosion(raw, px, py, cell, fast=fast)
                            else:
                                draw_player(raw, px, py, cell, fast=fast)
                        else:
                            draw_player(raw, px, py, cell, fast=fast)
        else:
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
                    if not full and (gx, gy) not in changed:
                        continue
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__

                    # 1. background tile — walls always look the same, passable or not
                    if tile_cls == "Wall":
                        draw_wall(raw, px, py, cell, fast=fast)
                    elif tile_cls == "Goal":
                        draw_goal(raw, px, py, cell, fast=fast)
                    else:
                        draw_floor(raw, px, py, cell, fast=fast)

                    # 2. dynamic object on top
                    occ = self.level.object_at(gx, gy)
                    cls = occ.__class__.__name__ if occ is not None else ""
                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)

                    if is_player and self.level.dead and cls in ("HiddenBoom", "BorderMine", "HardMine"):
                        draw_ash(raw, px, py, cell, fast=fast)
                    elif (is_player and self.level.dead and cls == "LaserDoor"
                            and occ is not None and occ.is_lethal()):
                        draw_ash(raw, px, py, cell, fast=fast)
                    elif (is_player and self.level.dead and cls == "Trap"
                            and occ is not None and occ.is_lethal()):
                        draw_skeleton(raw, px, py, cell, fast=fast)
                    elif is_player and self.level.dead and self.level.player_invisible:
                        # Fell into the void: the character is gone — only the
                        # empty pit is drawn.
                        draw_void(raw, px, py, cell, fast=fast)
                    elif is_player:
                        draw_player(raw, px, py, cell, fast=fast)
                    elif occ is not None:
                        if cls == "Platform":
                            if occ.is_void():
                                draw_void(raw, px, py, cell, fast=fast)
                            else:
                                # Path.solid = True — void trap removed, plain floor
                                draw_floor(raw, px, py, cell, fast=fast)
                        elif cls == "Door":
                            if occ.is_blocking():
                                draw_door_closed(raw, px, py, cell, fast=fast)
                            else:
                                draw_door_open(raw, px, py, cell, fast=fast)
                        elif cls == "Trap":
                            if occ.is_lethal():
                                draw_trap_lethal(raw, px, py, cell, fast=fast)
                            else:
                                draw_trap_safe(raw, px, py, cell, fast=fast)
                        elif cls == "Stone":
                            if occ.is_blocking():
                                draw_stone(raw, px, py, cell, fast=fast)
                            else:
                                draw_floor(raw, px, py, cell, fast=fast)
                        elif cls == "SealWall":
                            if occ.is_blocking():
                                draw_seal_wall(raw, px, py, cell, fast=fast)
                            else:
                                draw_floor(raw, px, py, cell, fast=fast)
                        elif cls == "Warp":
                            # Portals are visible by default (P toggles reveal/hide).
                            if getattr(self, "_show_warps", True):
                                draw_warp(raw, px, py, cell, fast=fast)
                            # else: drawn as plain floor (background tile already drawn in step 1)
                        elif cls == "CodeBlock":
                            label = occ.glyph().strip()
                            kind = occ.kind
                            draw_code_block(raw, px, py, cell, label, kind, fast=fast)

        if full and not board_only:
            # Full repaints own every visible cell: snapshot signatures so
            # the next same-geometry frame can repaint incrementally.
            # (Camera ticks skip this — their geometry is mid-glide and the
            # next tick is a full repaint anyway.)
            fresh: dict[tuple[int, int], tuple] = {}
            for _gy in range(y0i, y1i):
                for _gx in range(x0i, x1i):
                    fresh[(_gx, _gy)] = self._cell_sig(_gx, _gy)
            self._cell_sigs = fresh

        # ── info panel ──
        # Camera ticks redraw only the canvas and return early: panel
        # Text/label/backdrop work is what made keys feel late.
        if board_only:
            self._request_camera_anim()
            return
        press = getattr(self.level, "fusion_press_count", 0)
        hint = LEVEL_HINTS[self.level_index] if 0 <= self.level_index < len(LEVEL_HINTS) else ""
        panel_key = (self.level_index, self.level.moves, self._last_message,
                     press, self.game_completed, hint)
        panel_dirty = (panel_key != self._panel_cache)
        if panel_dirty:
            self._panel_cache = panel_key
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
            if press > 0:
                self.message_label.configure(
                    text=f"⚙ Stone. + open: {press}/3 presses to fuse",
                    fg=ACCENT)
                if not self.message_label.winfo_ismapped():
                    self.message_label.pack(fill="x", padx=12, pady=5, anchor="nw")
            # Static help text is written once in _build_info_panel and
            # never touched here (a Tk Text rewrite per move costs latency).
            # Hints panel shows only when the current level carries hint
            # text (currently level 8); otherwise the section stays hidden.
            # Rewrite only when the hint actually changes: Text
            # delete+insert per move costs input latency.
            if not self.game_completed and hint:
                if not self.hints_label.winfo_ismapped():
                    self.hints_label.pack(fill="x", padx=12, pady=5, anchor="nw")
                if not self.hints_view._text.winfo_ismapped():
                    self.hints_view._text.pack(fill="x", padx=12, pady=4, anchor="nw")
                if self._last_hint != hint:
                    self.hints_view.set_text(hint)
                    self._last_hint = hint
            else:
                self.hints_label.pack_forget()
                self.hints_view._text.pack_forget()
                self._last_hint = None

        self._paint_panel_backdrop()
        # Keep gliding toward the player/zoom target after this frame.
        self._request_camera_anim()
        try:
            import time as _time2
            self._last_render_ms = (_time2.perf_counter() - _t0) * 1000.0
        except Exception:
            pass

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
            self._cancel_camera_anim()
            self.window.root.destroy()
            return
        if key == "h":
            self.render_frame("Arrows/WASD move. R=restart. +/-=zoom. 0/F=fit map. C=center. Q=quit.")
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
            self._nudge_camera_toward_target(0.6)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- rooms closer.")
            return
        if key in ("minus", "kp_subtract"):
            self._zoom = max(CAM_ZOOM_MIN, self._zoom - 0.15)
            self._nudge_camera_toward_target(0.6)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- see more rooms.")
            return
        if key in ("0", "f", "fit"):
            zoom = self.fit_map_to_screen()
            self.render_frame(f"Zoom {zoom:.2f}x -- full map in view.")
            return
        if key == "c":
            # Let the easing loop glide back to the player (smooth);
            # restart/next-level still snap instantly.
            self.render_frame("Camera gliding to player.")
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
            self._nudge_camera_toward_target(1.0)
            self.render_frame(msg + "  Press R to restart.")
            return
        # Snap the camera exactly onto the player: at 120Hz there is no
        # glide after a move, so one keypress costs exactly one redraw and
        # no background tick storm competes with the next keypress.
        self._nudge_camera_toward_target(1.0)
        self.render_frame(msg)

    # ── entry point ─────────────────────────────────────────────────
    def run(self):
        self.window.run()
