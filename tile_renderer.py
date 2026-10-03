"""
tile_renderer.py
----------------
Procedural drawing functions for every game entity.  Each function draws
directly onto a raw tk.Canvas using polygons, ovals, rectangles, and
lines — no external image assets required.

Every draw_* function has the signature:

    draw_xxx(canvas: tk.Canvas, x: int, y: int, size: int, **kw)

where (x, y) is the top-left pixel coordinate of the cell and `size` is
the cell side-length in pixels.
"""

from __future__ import annotations
import math
import os
import tkinter as tk

try:
    from PIL import Image as _PILImage, ImageTk as _PILImageTk
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - Pillow is optional
    _PILImage = None
    _PILImageTk = None
    _PIL_AVAILABLE = False

# PhotoImages live on one Tk interpreter: when the default root changes
# (a fresh GUIEngine), drop every cached photo so a later lookup can
# never hand back an image that belongs to a dead interpreter.
_photo_root = None


def _check_photo_root():
    """Clear all PhotoImage caches when the Tk root changed."""
    global _photo_root
    cur = tk._default_root
    if cur is not _photo_root:
        _portal_photos.clear()
        _boom_photos.clear()
        _laser_photos.clear()
        _ash_photos.clear()
        _stone_photos.clear()
        _door_photos.clear()
        _trap_photos.clear()
        try:
            _trap_tk_photos.clear()
        except NameError:
            pass
        try:
            _latch_photos.clear()
        except NameError:
            pass
        _skel_photos.clear()
        _lever_photos.clear()
        _panel_photos.clear()
        try:
            _player_photos.clear()
        except NameError:
            pass
        _photo_root = cur


def _quant_size(size: int) -> int:
    """Quantize a cell size to even pixels for sprite caches.

    Smooth zoom changes cell size by 1px per tick; without this every
    tick would LANCZOS/BILINEAR-resize all sprites and thrash the cache.
    2px steps halve that work with no visible difference.
    """
    return max(8, int(round(float(size) / 2.0) * 2))

# ── colour palette ───────────────────────────────────────────────────
WALL_BASE      = "#3b3f5e"
WALL_MORTAR    = "#2a2d48"
FLOOR_BASE     = "#1b1f3f"
FLOOR_LINE     = "#242850"
GOAL_GREEN     = "#2e8f4c"
GOAL_FLAG      = "#4adc6e"
GOAL_POLE      = "#c0c0c0"
PLAYER_BODY    = "#a8a8b0"
PLAYER_EYE     = "#ffffff"
PLAYER_OUTLINE = "#0a0a0a"
PLAYER_BLACK   = "#0a0a0a"
PLAYER_COWL    = "#2e3a4e"
PLAYER_SKIN    = "#f2c79b"
PLAYER_SUIT    = "#a8a8b0"
PLAYER_BELT    = "#f2d23c"
KNIGHT_OUTLINE = "#0a0a0a"
KNIGHT_DARK    = "#5a5e6e"
KNIGHT_BODY    = "#9aa0b0"
KNIGHT_LIGHT   = "#d8dce4"
KNIGHT_HILITE  = "#eef1ff"
KNIGHT_VISOR   = "#0a0a0a"
KNIGHT_SWORD   = "#e8ecf4"
KNIGHT_HILT    = "#c46a2a"
KNIGHT_TRIM    = "#e3cda3"
KNIGHT_FOOT    = "#2e3138"
KNIGHT_FOOT_HI = "#6a6e7a"
PLATFORM_SOLID = "#7b5cff"
PLATFORM_PILLAR= "#5a3fd6"
PLATFORM_GHOST = "#574d87"
PLATFORM_GHOST_DASH = "#7b6baf"
VOID_BG        = "#04050c"
VOID_RING      = "#0a0c1a"
VOID_CORE      = "#000000"
VOID_RIM       = "#2a2160"
VOID_GLOW      = "#5a3fd6"
DOOR_CLOSED    = "#d96b3d"
DOOR_FRAME     = "#a04820"
DOOR_KEYHOLE   = "#1a1a1a"
DOOR_OPEN_CLR  = "#f1b56f"
DOOR_OPEN_GAP  = "#2e3a1a"
TRAP_RED       = "#c74555"
TRAP_SPIKE     = "#e05565"
TRAP_SAFE      = "#6d5060"
TRAP_SAFE_LINE = "#8d7080"
EXPLOSION_CORE = "#fff08a"
EXPLOSION_FIRE = "#ff9d2e"
EXPLOSION_EDGE = "#e34b3e"
FRAGMENT_COLOR = "#a8a8b0"
FRAGMENT_OUTLINE = "#0a0a0a"
STONE_BASE     = "#7a4f2a"
STONE_OUTLINE  = "#5a3010"
STONE_HI       = "#b07040"
STONE_SHADOW   = "#3a1a08"
STONE_WALL     = "#5a5e78"
STONE_MORTAR   = "#383b52"
STONE_TOP      = "#7a7f99"
SEAL_PURPLE    = "#8b5cf6"
WARP_INDIGO    = "#6366f1"
BLOCK_BG       = "#1a3a6a"
BLOCK_BORDER   = "#42a7ff"
BLOCK_TEXT     = "#e8f0ff"
CIRCUIT_SLOT_BG    = "#1e2850"
CIRCUIT_SLOT_BORDER= "#5f7fff"


# ── 3D palette (bevel light / shadow for faux-depth) ────────────────
WALL_HI          = "#6a7194"
WALL_SHADOW      = "#171927"
FLOOR_HI         = "#2e345e"
FLOOR_SHADOW     = "#0d1024"
STONE_FACE_HI    = "#9aa0bd"
STONE_SIDE       = "#3c3f58"
CODE_SHADOW      = "#0a0c1a"
DOOR_HI          = "#f5c080"
DOOR_SHADOW      = "#5a2810"


# ── helper ──────────────────────────────────────────────────────────
def _bevel(canvas, x, y, size, light, dark, depth=None):
    """Faux-3D chamfer: light top/left, dark bottom/right polygons.

    Light comes from the top-left, so raised tiles get a bright top
    and left edge with a dark bottom and right edge.  Inset tiles
    (floor) should call with light/dark swapped.
    """
    d = max(2, size // 8) if depth is None else max(1, int(depth))
    d = min(d, size // 3)
    x2, y2 = x + size, y + size
    # top — full width trapezoid
    canvas.create_polygon(x, y, x2, y, x2 - d, y + d, x + d, y + d,
                          fill=light, outline="")
    # left — full height trapezoid
    canvas.create_polygon(x, y, x + d, y + d, x + d, y2 - d, x, y2,
                          fill=light, outline="")
    # bottom
    canvas.create_polygon(x, y2, x + d, y2 - d, x2 - d, y2 - d, x2, y2,
                          fill=dark, outline="")
    # right
    canvas.create_polygon(x2, y, x2, y2, x2 - d, y2 - d, x2 - d, y + d,
                          fill=dark, outline="")


def _drop_shadow(canvas, x, y, size, dx=None, dy=None, fill=CODE_SHADOW):
    """Offset dark rect behind a raised tile for extrusion depth."""
    dx = max(1, size // 12) if dx is None else dx
    dy = max(2, size // 8) if dy is None else dy
    canvas.create_rectangle(x + dx, y + dy, x + size + dx, y + size + dy,
                            fill=fill, outline="")


def _inset(x, y, size, frac=0.08):
    """Return (x1, y1, x2, y2) inset by `frac` of size on each side."""
    m = max(1, int(size * frac))
    return x + m, y + m, x + size - m, y + size - m


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle using a polygon approximation."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    points = []
    # top-left corner
    for i in range(r + 1):
        angle = math.pi + math.pi / 2 * (i / max(r, 1))
        points.append((x1 + r + int(r * math.cos(angle)),
                        y1 + r + int(r * math.sin(angle))))
    # top-right corner
    for i in range(r + 1):
        angle = 3 * math.pi / 2 + math.pi / 2 * (i / max(r, 1))
        points.append((x2 - r + int(r * math.cos(angle)),
                        y1 + r + int(r * math.sin(angle))))
    # bottom-right corner
    for i in range(r + 1):
        angle = 0 + math.pi / 2 * (i / max(r, 1))
        points.append((x2 - r + int(r * math.cos(angle)),
                        y2 - r + int(r * math.sin(angle))))
    # bottom-left corner
    for i in range(r + 1):
        angle = math.pi / 2 + math.pi / 2 * (i / max(r, 1))
        points.append((x1 + r + int(r * math.cos(angle)),
                        y2 - r + int(r * math.sin(angle))))
    flat = []
    for px, py in points:
        flat.extend([px, py])
    canvas.create_polygon(flat, smooth=False, **kw)


# ── polish helpers: variation, glow, shadow, atmosphere ──────────────
# All polish is deterministic per (cell, phase): the base board never
# flickers (the incremental repaint cache stays valid) and every
# animated bit lives in the fx overlay (see GUIEngine._draw_fx_overlay),
# the only layer redrawn on the ambient tick.

def _hash01(x: int, y: int, salt: int = 0) -> float:
    """Deterministic 0..1 variation per cell (stable across frames)."""
    h = (int(x) * 374761393 + int(y) * 668265263
         + int(salt) * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 65535.0


def _soft_shadow(canvas, x, y, size, tags=None):
    """Soft-focus contact shadow: stippled dark ellipse under a sprite."""
    try:
        hh = max(2, size // 8)
        dy = size // 6
        m = max(2, size // 5)
        canvas.create_oval(x + m, y + size - dy - hh,
                           x + size - m, y + size - dy + hh,
                           fill="#05070f", outline="", stipple="gray50",
                           tags=tags)
    except Exception:
        pass


def _glow(canvas, cx, cy, r, color, layers=3, tags=None):
    """Fake bloom: concentric outline ovals fading outward (no alpha)."""
    if r < 3:
        return
    step = max(2, r // 4)
    for i in range(max(1, layers)):
        rr = r + i * step
        canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                           fill="", outline=color,
                           width=max(1, 3 - i), tags=tags)


def _gleam(canvas, x, y, size, color="#f4f6ff", tags=None):
    """Small metallic diagonal highlight in the top-left of a cell."""
    m = max(2, int(size * 0.20))
    ln = max(3, int(size * 0.28))
    canvas.create_line(x + m, y + m + ln, x + m + ln, y + m,
                       fill=color, width=max(1, size // 26), tags=tags)


def draw_parallax_grid(canvas, cw, ch, cam_x0, cam_y0, cell):
    """Faded distant grid layer drifting slower than the board (parallax)."""
    try:
        step = max(26, int(cell * 2))
        ox = -int((cam_x0 * cell * 0.35) % step)
        oy = -int((cam_y0 * cell * 0.35) % step)
        for gx in range(ox, cw + 1, step):
            canvas.create_line(gx, 0, gx, ch, fill="#1a2140", width=1)
        for gy in range(oy, ch + 1, step):
            canvas.create_line(0, gy, cw, gy, fill="#1a2140", width=1)
    except Exception:
        pass


def draw_vignette(canvas, cw, ch):
    """Soft darkened frame edges for ambient focus."""
    try:
        d = max(10, min(cw, ch) // 10)
        kw = {"fill": "#04060d", "outline": "", "stipple": "gray25"}
        canvas.create_rectangle(0, 0, cw, d, **kw)
        canvas.create_rectangle(0, ch - d, cw, ch, **kw)
        canvas.create_rectangle(0, 0, d, ch, **kw)
        canvas.create_rectangle(cw - d, 0, cw, ch, **kw)
    except Exception:
        pass


# ── fx overlay: animated bits, redrawn on the ambient tick ───────────
SPARK_WARM = "#ffd45a"
SPARK_HOT = "#fff6c8"
SPARK_DEEP = "#ff9d2e"
WISP_COOL = "#9a8fff"

BLOCK_FX_COLORS = {
    "CLASS": "#52b0ff",
    "PROP": "#40d8a0",
    "OP": "#d0a840",
    "VALUE": "#b070e0",
    "NOT": "#ff5f8f",
}


def _mine_fuse_tip(x, y, size):
    """Fuse tip pixel shared by the static stem and the animated spark."""
    return x + int(size * 0.64), y + int(size * 0.10)


def draw_fuse_spark(canvas, tx, ty, size, phase, tags=None):
    """Sputtering fuse tip: warm star + glow + stray embers (animated)."""
    import math as _math
    r = max(2, size // 10)
    _glow(canvas, tx, ty, r + 2 + (phase % 2), SPARK_DEEP,
          layers=2, tags=tags)
    reach = r + 1 + (phase % 3)
    w = max(1, size // 26)
    canvas.create_line(tx - reach, ty, tx + reach, ty,
                       fill=SPARK_WARM, width=w, tags=tags)
    canvas.create_line(tx, ty - reach, tx, ty + reach,
                       fill=SPARK_HOT, width=w, tags=tags)
    canvas.create_oval(tx - 1, ty - 1, tx + 1, ty + 1,
                       fill=SPARK_HOT, outline=SPARK_HOT, tags=tags)
    for i in range(3):
        a = _hash01(tx + i * 11, ty - i * 17, phase) * 6.2832
        d = r + 3 + int(_hash01(tx - i * 5, ty + i * 3, phase + 7)
                        * max(2, size // 8))
        ex = tx + int(_math.cos(a) * d)
        ey = ty + int(_math.sin(a) * d)
        c = (SPARK_HOT, SPARK_WARM, SPARK_DEEP)[(phase + i) % 3]
        canvas.create_oval(ex - 1, ey - 1, ex + 1, ey + 1,
                           fill=c, outline=c, tags=tags)


def draw_mine_fx(canvas, px, py, size, phase, tags=None):
    """Burning-fuse overlay: pulsing warm body glow + sputtering tip."""
    cx, cy = px + size // 2, py + size // 2
    _glow(canvas, cx, cy, size // 2 - 2 + (phase % 2) * 2,
          SPARK_DEEP, layers=2, tags=tags)
    tx, ty = _mine_fuse_tip(px, py, size)
    draw_fuse_spark(canvas, tx, ty, size, phase, tags=tags)


def draw_warp_fx(canvas, px, py, size, phase, tags=None):
    """Portal shimmer: rotating vortex arcs, cool glow, rising wisps."""
    import math as _math
    cx, cy = px + size // 2, py + size // 2
    r = max(4, size // 2 - max(2, size // 8))
    _glow(canvas, cx, cy, r + (phase % 2), "#6366f1",
          layers=2, tags=tags)
    for k in range(3):
        rr = max(3, r - k * max(2, size // 14))
        start = (phase * 22 + k * 120) % 360
        canvas.create_arc(cx - rr, cy - rr, cx + rr, cy + rr,
                          start=start, extent=210, style="arc",
                          outline="#9a8fff" if k % 2 else "#6366f1",
                          width=max(1, size // 22), tags=tags)
    # bright core mote orbiting inside the vortex
    a = (phase * 0.6) % 6.2832
    ox = int(_math.cos(a) * r * 0.35)
    oy = int(_math.sin(a) * r * 0.35)
    canvas.create_oval(cx + ox - 2, cy + oy - 2, cx + ox + 2, cy + oy + 2,
                       fill="#cfc8ff", outline="#cfc8ff", tags=tags)
    # occasional wisps floating off the rim
    for i in range(2):
        seed = int(_hash01(px + i * 13, py - i * 7, 90) * 8)
        if (phase + seed + i * 3) % 8 >= 5:
            continue
        ang = _hash01(px - i * 3, py + i * 29, 91) * 6.2832
        lift = (phase * 2 + i * 6) % max(4, size // 3)
        wx = cx + int(_math.cos(ang) * (r + lift))
        wy = cy + int(_math.sin(ang) * (r + lift)) - lift // 2
        wr = max(1, size // 24)
        canvas.create_oval(wx - wr, wy - wr, wx + wr, wy + wr,
                           fill=WISP_COOL, outline=WISP_COOL, tags=tags)


def draw_block_fx(canvas, px, py, size, phase, kind, tags=None):
    """Current flowing through an active block: dashes + edge glow."""
    color = BLOCK_FX_COLORS.get(kind, "#42a7ff")
    m = max(1, size // 10)
    x1, y1, x2, y2 = px + m, py + m, px + size - m, py + size - m
    _glow(canvas, (x1 + x2) // 2, (y1 + y2) // 2,
          max(3, (x2 - x1) // 2), color, layers=1, tags=tags)
    n = 3
    w = max(1, size // 26)
    for i in range(n):
        t = (i / n + phase * 0.15) % 1.0
        dx = x1 + int(t * (x2 - x1))
        canvas.create_line(dx - 2, y1, dx + 2, y1,
                           fill="#ffffff", width=w, tags=tags)
        dx2 = x2 - int(t * (x2 - x1))
        canvas.create_line(dx2 - 2, y2, dx2 + 2, y2,
                           fill=color, width=w, tags=tags)


def draw_laser_fx(canvas, px, py, size, phase, tags=None):
    """Live-beam shimmer: hot pulsing core over the gate."""
    m = max(2, size // 10)
    cx = px + size // 2
    hot = "#ffffff" if phase % 2 == 0 else "#ffd0d0"
    _glow(canvas, cx, py + size // 2, size // 3, "#e34b3e",
          layers=2, tags=tags)
    canvas.create_line(cx, py + m, cx, py + size - m,
                       fill=hot, width=max(1, size // 20), tags=tags)


def draw_trap_fx(canvas, px, py, size, phase, tags=None):
    """Menace pulse around a live trap."""
    cx, cy = px + size // 2, py + size // 2
    _glow(canvas, cx, cy, size // 2 - 2 + (phase % 2),
          "#e05565", layers=2, tags=tags)


def draw_goal_fx(canvas, px, py, size, phase, tags=None):
    """Gentle breathing glow around the goal flag."""
    cx, cy = px + size // 2, py + size // 2
    _glow(canvas, cx, cy, size // 2 - 1 + (phase % 2),
          "#4adc6e", layers=2, tags=tags)


def draw_dust_puff(canvas, px, py, r, age01, tags=None):
    """Faint footstep dust: expands and fades with age (0..1)."""
    if not 0 <= age01 <= 1:
        return
    try:
        rr = max(1, int(r * (0.6 + age01 * 0.9)))
        col = "#9aa0bd" if age01 < 0.5 else "#5a5e78"
        canvas.create_oval(px - rr, py - rr, px + rr, py + rr,
                           fill="", outline=col, width=1,
                           stipple="" if age01 < 0.35 else "gray50",
                           tags=tags)
    except Exception:
        pass


# ── entity drawing functions ────────────────────────────────────────

def draw_wall(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False,
              gx: int = 0, gy: int = 0):
    """Brick-pattern wall with raised 3D bevel, stone chips and moss."""
    if fast:
        # LOD: 1 item instead of ~10 (brick lines + 4-poly bevel).
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=WALL_MORTAR, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=WALL_BASE, outline=WALL_MORTAR, width=1)
    # Draw brick rows
    rows = max(2, size // 10)
    row_h = size / rows
    for r in range(rows):
        ry = y + int(r * row_h)
        canvas.create_line(x, ry, x + size, ry, fill=WALL_MORTAR, width=1)
        # vertical mortar — offset every other row
        cols = max(2, size // 14)
        col_w = size / cols
        offset = col_w / 2 if r % 2 else 0
        for c in range(cols + 1):
            cx = x + int(c * col_w + offset)
            if x <= cx <= x + size:
                canvas.create_line(cx, ry, cx, ry + int(row_h),
                                   fill=WALL_MORTAR, width=1)
    # raised-block bevel on top of the brickwork
    _bevel(canvas, x, y, size, WALL_HI, WALL_SHADOW)
    # worn-stone texture: a darker chip + occasional moss, fixed per cell
    if _hash01(gx, gy, 11) < 0.5:
        cw = max(2, size // 5)
        chh = max(1, size // 9)
        cxp = x + int(_hash01(gx, gy, 12) * max(1, size - cw))
        cyp = y + int(_hash01(gx, gy, 13) * max(1, size - chh))
        canvas.create_rectangle(cxp, cyp, cxp + cw, cyp + chh,
                                fill="#2e324e", outline="")
    if size >= 20 and _hash01(gx, gy, 14) < 0.16:
        for i in range(3):
            mx = x + int(_hash01(gx, gy, 15 + i) * (size - 2)) + 1
            my = y + int(_hash01(gx, gy, 18 + i) * (size - 2)) + 1
            canvas.create_rectangle(mx, my, mx + 2, my + 2,
                                    fill="#3a6a3a", outline="")


def draw_floor(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False,
               gx: int = 0, gy: int = 0):
    """Subtle dark floor tile with worn-pavement grime, recessed bevel."""
    if fast:
        # LOD: 1 item instead of 6 (inner accent + 4-poly bevel).
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=FLOOR_BASE, outline=FLOOR_LINE, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=FLOOR_BASE, outline=FLOOR_LINE, width=1)
    # inner accent line
    m = max(1, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill="", outline=FLOOR_LINE, width=1)
    # recessed bevel (inverted light): sunken pit vs raised walls
    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 12))
    # floor grime: faint speckles, fixed per cell
    if _hash01(gx, gy, 21) < 0.55:
        for i in range(2):
            sx = x + int(_hash01(gx, gy, 22 + i) * (size - 2)) + 1
            sy = y + int(_hash01(gx, gy, 24 + i) * (size - 2)) + 1
            canvas.create_rectangle(sx, sy, sx + 2, sy + 1,
                                    fill="#141838", outline="")
    # occasional hairline crack in the pavement
    if size >= 22 and _hash01(gx, gy, 26) < 0.12:
        cx0 = x + int(_hash01(gx, gy, 27) * size)
        canvas.create_line(cx0, y + 2, x + size - cx0 // 2, y + size - 2,
                           fill="#0d1024", width=1)


def draw_goal(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Green flag on a pole, raised plate with 3D rim."""
    if fast:
        # LOD: 2 items instead of ~8.
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=GOAL_GREEN, outline="#3ab85e", width=1)
        pole_x = x + size // 3
        canvas.create_line(pole_x, y + size * 0.2, pole_x, y + size * 0.85,
                           fill=GOAL_POLE, width=max(1, size // 16))
        return
    # floor background
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1a3020", outline="#2e4a3a", width=1)
    _bevel(canvas, x, y, size, FLOOR_SHADOW, "#3a5a4a",
           depth=max(1, size // 12))
    # pulsing glow
    m = max(2, size // 6)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=GOAL_GREEN, outline="#3ab85e", width=2)
    _bevel(canvas, x + m, y + m, size - 2 * m, "#7de89a", "#14522a",
           depth=max(1, size // 14))
    # pole
    pole_x = x + size // 3
    canvas.create_line(pole_x, y + size * 0.2, pole_x, y + size * 0.85,
                       fill=GOAL_POLE, width=max(1, size // 16))
    # flag triangle
    fx = pole_x
    fy = int(y + size * 0.2)
    fw = int(size * 0.45)
    fh = int(size * 0.3)
    canvas.create_polygon(fx, fy, fx + fw, fy + fh // 2, fx, fy + fh,
                          fill=GOAL_FLAG, outline="#38c85c", width=1)
    # energy bloom around the flag
    _glow(canvas, x + size // 2, y + size // 2, size // 2, "#4adc6e")


def draw_player(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False,
                floor: bool = True, tags=None):
    """Knight pixel character (assets/player.png).

    Silver helmet with a black T visor, grey plate body and dark
    boots.  The photo is fitted into the cell; without Pillow / the
    asset / a Tk root, falls back to procedural armor pixels so tests
    stay headless-safe.  `floor=False` skips the floor + shadow base
    for overlay draws; `tags` marks items for the fx layer.
    """
    if floor:
        draw_floor(canvas, x, y, size, fast=fast)
    _soft_shadow(canvas, x, y, size, tags=tags)
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _player_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center", tags=tags)
        return
    if fast:
        # LOD: 3 items instead of ~60 RLE rects. Reads as the same
        # character at speed: helm, visor slit, plate body.
        m = max(1, size // 8)
        canvas.create_oval(x + m, y + m, x + size - m,
                           y + int(size * 0.62),
                           fill=KNIGHT_LIGHT, outline=KNIGHT_OUTLINE,
                           width=max(1, size // 20), tags=tags)
        canvas.create_rectangle(x + size // 4, y + int(size * 0.30),
                                x + size - size // 4, y + int(size * 0.48),
                                fill=KNIGHT_VISOR, outline="", tags=tags)
        canvas.create_rectangle(x + m, y + int(size * 0.60),
                                x + size - m, y + size - m,
                                fill=KNIGHT_BODY, outline=KNIGHT_OUTLINE,
                                width=max(1, size // 20), tags=tags)
        return

    # 16 wide x 19 tall pixel map. '.' = transparent.
    # K=outline black, L=helm light, W=helm shine,
    # B=armor grey, D=armor shade, V=visor black,
    # T=trim beige, E=boot dark, O=boot highlight.
    PIX = [
        "....KKKKKKKK....",
        "..KKLLLLLLLLKK..",
        ".KLLWWLLLLLBBDK.",
        ".KLWWLLLLLBBBDDK",
        ".KLLLLLLLLBBBBDK",
        ".KLLVVVVVVBBBBDK",
        ".KLLVVVVVVBBBBDK",
        ".KLLLVVVVLBBBBDK",
        ".KLLLVVVVLBBBBDK",
        "DKBBBBBBBBBBBBKD",
        ".KBBTTTTTTBBBDDK",
        "DKBBBBBBBBBBBBKD",
        "..KBBBBBBBBDDK..",
        "...KBBBBBBDDK...",
        "...KBBBBBBDDK...",
        "..KKBBBBBBDDKK..",
        ".KKKEEEEEEEEKKK.",
        ".KKKOEEEEEEOKKK.",
        "...KKKKKKKKKK...",
    ]
    COLORS = {
        "K": KNIGHT_OUTLINE,
        "D": KNIGHT_DARK,
        "B": KNIGHT_BODY,
        "L": KNIGHT_LIGHT,
        "W": KNIGHT_HILITE,
        "V": KNIGHT_VISOR,
        "T": KNIGHT_TRIM,
        "E": KNIGHT_FOOT,
        "O": KNIGHT_FOOT_HI,
    }
    h = len(PIX)
    w = len(PIX[0])
    px = size / w
    py = size / h
    # Run-length encode each row: one rectangle per horizontal run of the
    # same color instead of one per pixel (~320 items -> ~60). This is the
    # single biggest canvas-item saver at 60fps.
    for j, row in enumerate(PIX):
        i = 0
        y1 = y + j * py
        y2 = y + (j + 1) * py + 0.5
        while i < w:
            ch = row[i]
            if ch == "." or ch not in COLORS:
                i += 1
                continue
            k = i + 1
            while k < w and row[k] == ch:
                k += 1
            x1 = x + i * px
            x2 = x + k * px + 0.5
            canvas.create_rectangle(x1, y1, x2, y2,
                                    fill=COLORS[ch], outline="", tags=tags)
            i = k


def draw_boom_explosion(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """A blast cloud and scattered character fragments after the hidden boom fires."""
    draw_floor(canvas, x, y, size, fast=fast)
    if fast:
        cx, cy = x + size // 2, y + size // 2
        inner = max(4, size // 4)
        canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                           fill=EXPLOSION_FIRE, outline=EXPLOSION_CORE)
        return
    cx, cy = x + size // 2, y + size // 2
    outer = max(7, size // 2 - 2)
    inner = max(4, size // 4)

    # Jagged fireball.
    points = []
    for index in range(16):
        angle = math.tau * index / 16 - math.pi / 2
        radius = outer if index % 2 == 0 else max(inner + 2, outer * 3 // 5)
        points.extend((cx + int(math.cos(angle) * radius),
                       cy + int(math.sin(angle) * radius)))
    canvas.create_polygon(points, fill=EXPLOSION_EDGE, outline="#ffd45a", width=max(1, size // 22))
    canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                       fill=EXPLOSION_FIRE, outline=EXPLOSION_CORE, width=max(1, size // 24))
    core = max(2, inner // 2)
    canvas.create_oval(cx - core, cy - core, cx + core, cy + core,
                       fill=EXPLOSION_CORE, outline=EXPLOSION_CORE)

    # Knight fragments so the character visibly breaks apart.
    fragment = max(2, size // 11)
    for dx, dy, col in ((-0.34, -0.31, KNIGHT_BODY),
                        (0.31, -0.25, KNIGHT_OUTLINE),
                        (-0.38, 0.29, KNIGHT_OUTLINE),
                        (0.35, 0.33, KNIGHT_BODY)):
        fx, fy = cx + int(size * dx), cy + int(size * dy)
        canvas.create_polygon(fx, fy - fragment,
                              fx + fragment, fy,
                              fx, fy + fragment,
                              fx - fragment, fy,
                              fill=col, outline=FRAGMENT_OUTLINE)


def draw_platform_solid(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Solid purple bridge with support pillars, raised deck."""
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=PLATFORM_SOLID, outline=PLATFORM_PILLAR, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 14))
    m = max(1, size // 8)
    # bridge deck — thick horizontal bar
    deck_y1 = y + size // 4
    deck_y2 = y + size // 2 + m
    canvas.create_rectangle(x + 1, deck_y1, x + size - 1, deck_y2,
                            fill=PLATFORM_SOLID, outline=PLATFORM_PILLAR, width=1)
    # support pillars
    pw = max(3, size // 6)
    # left pillar
    canvas.create_rectangle(x + m + 2, deck_y2, x + m + 2 + pw, y + size - m,
                            fill=PLATFORM_PILLAR, outline="#4a2fb0", width=1)
    # right pillar
    canvas.create_rectangle(x + size - m - 2 - pw, deck_y2,
                            x + size - m - 2, y + size - m,
                            fill=PLATFORM_PILLAR, outline="#4a2fb0", width=1)
    # deck top accent
    canvas.create_line(x + 2, deck_y1 + 1, x + size - 2, deck_y1 + 1,
                       fill="#a080ff", width=max(1, size // 24))
    # deck drop shadow for thickness
    dh = max(2, size // 12)
    canvas.create_rectangle(x + 1, deck_y2, x + size - 1, deck_y2 + dh,
                            fill=PLATFORM_PILLAR, outline="")


def draw_platform_ghost(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Ghost/non-solid platform — dashed outline of the bridge shape."""
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="", outline=PLATFORM_GHOST_DASH, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    m = max(1, size // 8)
    deck_y1 = y + size // 4
    deck_y2 = y + size // 2 + m
    # dashed deck outline
    canvas.create_rectangle(x + 1, deck_y1, x + size - 1, deck_y2,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=max(1, size // 20), dash=(4, 3))
    # dashed pillars
    pw = max(3, size // 6)
    canvas.create_rectangle(x + m + 2, deck_y2, x + m + 2 + pw, y + size - m,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=1, dash=(3, 3))
    canvas.create_rectangle(x + size - m - 2 - pw, deck_y2,
                            x + size - m - 2, y + size - m,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=1, dash=(3, 3))


def draw_void(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Bottomless void pit — the path collapsed into nothing.

    Drawn for a Path./Platform cell while Path.solid = False.  Stepping
    onto it drops the character into the void (it vanishes, run over).
    """
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=VOID_BG, outline=VOID_RIM, width=1)
        return
    # darkness swallows the whole cell
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=VOID_BG, outline=VOID_RIM, width=1)
    # sunken rim: deep pit edge
    _bevel(canvas, x, y, size, "#000000", VOID_GLOW,
           depth=max(2, size // 6))
    cx, cy = x + size // 2, y + size // 2
    m = max(2, size // 8)
    outer = max(3, size // 2 - m)
    # faint glowing rim marks it as a hazard
    canvas.create_oval(cx - outer, cy - outer, cx + outer, cy + outer,
                       fill=VOID_RING, outline=VOID_GLOW,
                       width=max(1, size // 24), dash=(4, 3))
    # sinking rings give the pit depth
    for frac in (0.66, 0.42):
        r = max(1, int(outer * frac))
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           fill=VOID_BG, outline="")
    # black core
    r = max(1, int(outer * 0.2))
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                       fill=VOID_CORE, outline=VOID_CORE)


def draw_door_closed(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Closed wooden door from assets/door.jpeg, else procedural
    orange door with keyhole and raised frame."""
    # Photo first in both modes: fast art must never restyle tiles that
    # have asset art — the simple rect is only a headless fallback.
    photo = None
    try:
        photo = _door_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        draw_floor(canvas, x, y, size, fast=fast)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 7)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill=DOOR_CLOSED, outline=DOOR_FRAME, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 14))
    m = max(2, size // 7)
    # door body
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=DOOR_CLOSED, outline=DOOR_FRAME, width=max(1, size // 16))
    # frame top bar
    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill=DOOR_FRAME, outline=DOOR_FRAME)
    # keyhole circle
    cx, cy = x + size // 2, y + size // 2
    kr = max(2, size // 10)
    canvas.create_oval(cx - kr, cy - kr, cx + kr, cy + kr,
                       fill=DOOR_KEYHOLE, outline="#333")
    # keyhole slot
    canvas.create_rectangle(cx - max(1, kr // 2), cy, cx + max(1, kr // 2), cy + kr * 2,
                            fill=DOOR_KEYHOLE, outline=DOOR_KEYHOLE)
    # handle
    hx = x + size - m - max(3, size // 6)
    hy = cy
    hr = max(2, size // 14)
    canvas.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                       fill="#ffd080", outline="#cc9040")
    # door slab bevel for raised wood
    _bevel(canvas, x + m, y + m, size - 2 * m, DOOR_HI, DOOR_SHADOW,
           depth=max(1, size // 14))
    _gleam(canvas, x, y, size)


def draw_door_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Open door — split panels revealing passage (sunken)."""
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="#1a2a1a", outline="#2e4a2e", width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1a2a1a", outline="#2e4a2e", width=1)
    _bevel(canvas, x, y, size, "#0d1a0d", "#3a5a3a",
           depth=max(1, size // 14))
    m = max(2, size // 7)
    half = (size - 2 * m) // 2
    # left panel (slightly ajar)
    canvas.create_rectangle(x + m, y + m, x + m + half // 2, y + size - m,
                            fill=DOOR_OPEN_CLR, outline="#c89040", width=1)
    # right panel
    canvas.create_rectangle(x + size - m - half // 2, y + m,
                            x + size - m, y + size - m,
                            fill=DOOR_OPEN_CLR, outline="#c89040", width=1)
    # passage opening in the center
    canvas.create_rectangle(x + m + half // 2, y + m,
                            x + size - m - half // 2, y + size - m,
                            fill="#2a3a2a", outline="#3a5a3a", width=1)
    # frame top bar
    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill="#c89040", outline="#a07030")


# ── padlock photo support (assets/latch.webp, white background) ──
LATCH_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "latch.webp")
_latch_src = None         # cached RGBA PIL image, or False when unavailable
_latch_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_latch_src():
    """Load the padlock art keyed to RGBA (cached, incl. the miss)."""
    global _latch_src
    if _latch_src is not None:
        return _latch_src or None
    _latch_src = _white_keyed_src(LATCH_IMAGE) or False
    return _latch_src or None


def _latch_photo(size: int):
    """PhotoImage of the padlock fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _latch_photos:
        return _latch_photos[key]
    src = _load_latch_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _latch_photos[key] = photo
    return photo


# ── latch-door art (pink, trap-styled) ──────────────────────────────
# The LatchDoor used to borrow the wooden-door art, making it identical
# to a normal Door.  It gets its own pink design with a digital-rain
# latch plate tying it to the trap family.
LATCH_BASE   = "#c44a8c"
LATCH_FRAME  = "#7a2a58"
LATCH_HI     = "#f2a4cc"
LATCH_SHADOW = "#4a1030"
LATCH_OPEN_CLR = "#e89ac0"
LATCH_OPEN_GAP = "#3a1a2e"


def draw_latch_closed(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Closed latch door — gold padlock from assets/latch.webp, else pink."""
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _latch_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        draw_floor(canvas, x, y, size, fast=fast)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 7)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill=LATCH_BASE, outline=LATCH_FRAME, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 14))
    m = max(2, size // 7)
    # pink door body
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=LATCH_BASE, outline=LATCH_FRAME,
                            width=max(1, size // 16))
    # frame top bar
    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill=LATCH_FRAME, outline=LATCH_FRAME)
    # rain-textured latch plate (vertical inset strip, trap greens)
    pw = max(3, size // 5)
    px1 = x + size // 2 - pw // 2
    canvas.create_rectangle(px1, y + m + max(2, size // 10),
                            px1 + pw, y + size - m,
                            fill="#0d2a12", outline="#2a5a30", width=1)
    import random as _rand
    _rng = _rand.Random(1234)
    for _ in range(max(4, size // 3)):
        gx = _rng.randint(px1 + 1, px1 + pw - 1)
        gy = _rng.randint(y + m + 2, y + size - m - 2)
        g = _rng.choice(("#0ac11b", "#4ae35a", "#087a12"))
        canvas.create_rectangle(gx, gy, gx + 1, gy + 2, fill=g, outline="")
    # keyhole + handle
    cx = x + size // 2 + pw
    cy = y + size // 2
    kr = max(2, size // 10)
    canvas.create_oval(cx - kr, cy - kr, cx + kr, cy + kr,
                       fill="#1a1a1a", outline="#333")
    hx = x + size - m - max(3, size // 6)
    hr = max(2, size // 14)
    canvas.create_oval(hx - hr, cy - hr, hx + hr, cy + hr,
                       fill="#ffd080", outline="#cc9040")
    _bevel(canvas, x + m, y + m, size - 2 * m, LATCH_HI, LATCH_SHADOW,
           depth=max(1, size // 14))
    _gleam(canvas, x, y, size)

def draw_latch_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Open latch door — pink split panels revealing the passage."""
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="#2a1420", outline="#4a2030", width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#2a1420", outline="#4a2030", width=1)
    _bevel(canvas, x, y, size, "#12060c", "#6a2a48",
           depth=max(1, size // 14))
    m = max(2, size // 7)
    half = (size - 2 * m) // 2
    # left panel (slightly ajar)
    canvas.create_rectangle(x + m, y + m, x + m + half // 2, y + size - m,
                            fill=LATCH_OPEN_CLR, outline="#a05880", width=1)
    # right panel
    canvas.create_rectangle(x + size - m - half // 2, y + m,
                            x + size - m, y + size - m,
                            fill=LATCH_OPEN_CLR, outline="#a05880", width=1)
    # passage opening in the center
    canvas.create_rectangle(x + m + half // 2, y + m,
                            x + size - m - half // 2, y + size - m,
                            fill=LATCH_OPEN_GAP, outline="#6a2a48", width=1)
    # frame top bar
    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill="#a05880", outline="#7a2a58")


def draw_trap_lethal(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Live trap — assets/trap.gif fitted into the cell, nothing over it."""
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _trap_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        draw_floor(canvas, x, y, size, fast=fast)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 6)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill=TRAP_RED, outline="#e05565", width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#2a1015", outline="#4a2025", width=1)
    _bevel(canvas, x, y, size, "#5a2025", "#0d0508",
           depth=max(1, size // 14))
    _glow(canvas, x + size // 2, y + size // 2, size // 2, "#e05565")
    m = max(2, size // 6)
    # base diamond
    cx, cy = x + size // 2, y + size // 2
    half = size // 2 - m
    canvas.create_polygon(cx, cy - half,
                          cx + half, cy,
                          cx, cy + half,
                          cx - half, cy,
                          fill=TRAP_RED, outline="#e05565", width=max(1, size // 20))
    # spikes on top edge
    spikes = max(3, size // 12)
    sw = (size - 2 * m) // spikes
    for i in range(spikes):
        sx = x + m + i * sw
        canvas.create_polygon(sx, y + m + size // 5,
                              sx + sw // 2, y + m,
                              sx + sw, y + m + size // 5,
                              fill=TRAP_SPIKE, outline=TRAP_RED)
    # danger symbol — exclamation mark
    canvas.create_text(cx, cy, text="!", fill="white",
                       font=("Arial", max(8, size // 4), "bold"), anchor="center")


def draw_trap_safe(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Disarmed trap — removed, the path looks like normal floor.

    Once the logic flips Trap.isLethal to False the trap is gone, so
    this draws plain floor with no leftover art or outline.
    """
    draw_floor(canvas, x, y, size, fast=fast)


def draw_code_block(canvas: tk.Canvas, x: int, y: int, size: int,
                    label: str, kind: str, fast: bool = False,
                    active: bool = False):
    """Crystalline 'chip' with a glowing label and current-flow state.

    Metallic gradient bands + an inner text halo keep the label
    readable; `active` marks blocks sitting on a circuit line with a
    hot border (the flowing current itself is drawn by draw_block_fx).
    """
    kind_colors = {
        "CLASS":  ("#1a4a7a", "#52b0ff"),
        "PROP":   ("#1a5a4a", "#40d8a0"),
        "OP":     ("#4a3a1a", "#d0a840"),
        "VALUE":  ("#3a1a5a", "#b070e0"),
        "NOT":    ("#5a1a3a", "#ff5f8f"),
    }
    bg, border = kind_colors.get(kind, (BLOCK_BG, BLOCK_BORDER))
    if fast:
        # LOD: 2 items (body + label) instead of shadow + rounded polys.
        m = max(1, size // 10)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill=bg, outline=border,
                                width=max(1, size // 20))
        cx = x + size // 2
        cy = y + size // 2
        font_size = max(7, min(size // 5, 14))
        canvas.create_text(cx, cy, text=label, fill=BLOCK_TEXT,
                           font=("Consolas", font_size, "bold"), anchor="center")
        return
    m = max(1, size // 10)
    r = max(3, size // 6)
    # extrusion shadow underneath for thickness
    sx, sy = max(1, size // 16), max(2, size // 10)
    x1s, y1s, x2s, y2s = x + m + sx, y + m + sy, x + size - m + sx, y + size - m + sy
    _rounded_rect(canvas, x1s, y1s, x2s, y2s, r, fill=CODE_SHADOW, outline="")
    x1, y1, x2, y2 = x + m, y + m, x + size - m, y + size - m
    _rounded_rect(canvas, x1, y1, x2, y2, r, fill=bg, outline=border,
                  width=max(1, size // 20))
    # inner highlight line at top
    canvas.create_line(x1 + r, y1 + 2, x2 - r, y1 + 2,
                       fill=border, width=1)
    # crystalline bands: bright top facet, dark bottom facet
    canvas.create_line(x1 + r, y1 + 4, x2 - r, y1 + 4,
                       fill="#ffffff", width=1)
    canvas.create_line(x1 + r, y2 - 3, x2 - r, y2 - 3,
                       fill="#0a0c1a", width=2)
    # left sheen strip for a metallic read
    canvas.create_line(x1 + 3, y1 + r, x1 + 3, y2 - r,
                       fill=border, width=1)
    # active state: hot outer border so the block hums on its circuit
    if active:
        canvas.create_rectangle(x1 - 1, y1 - 1, x2 + 1, y2 + 1,
                                fill="", outline="#ffffff",
                                width=max(1, size // 28))
    # label text with a faint internal glow (halo underlay + bright face)
    cx = x + size // 2
    cy = y + size // 2
    font_size = max(7, min(size // 5, 14))
    _font = ("Consolas", font_size, "bold")
    canvas.create_text(cx + 1, cy + 1, text=label, fill=border,
                       font=_font, anchor="center")
    canvas.create_text(cx, cy, text=label, fill=BLOCK_TEXT,
                       font=_font, anchor="center")


def draw_circuit_slot(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Dashed rounded-rect outline marking a compiler slot."""
    draw_floor(canvas, x, y, size, fast=fast)
    if fast:
        return
    m = max(2, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=CIRCUIT_SLOT_BG, outline=CIRCUIT_SLOT_BORDER,
                            width=max(1, size // 16), dash=(5, 3))
    # small dot in center
    cx, cy = x + size // 2, y + size // 2
    dr = max(1, size // 16)
    canvas.create_oval(cx - dr, cy - dr, cx + dr, cy + dr,
                       fill=CIRCUIT_SLOT_BORDER, outline=CIRCUIT_SLOT_BORDER)


def draw_stone(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Solid stone block from assets/stone.jpeg, else grey brickwork."""
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _stone_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        draw_floor(canvas, x, y, size, fast=fast)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=STONE_WALL, outline=STONE_MORTAR, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=STONE_WALL, outline=STONE_MORTAR, width=1)
    # brick courses, same structure as draw_wall but larger blocks
    rows = max(2, size // 12)
    row_h = size / rows
    for r in range(rows):
        ry = y + int(r * row_h)
        canvas.create_line(x, ry, x + size, ry, fill=STONE_MORTAR, width=1)
        cols = max(2, size // 16)
        col_w = size / cols
        offset = col_w / 2 if r % 2 else 0
        for c in range(cols + 1):
            cx = x + int(c * col_w + offset)
            if x <= cx <= x + size:
                canvas.create_line(cx, ry, cx, ry + int(row_h),
                                   fill=STONE_MORTAR, width=1)
    # pale top edge so it reads as raised stone in dim light
    canvas.create_line(x + 1, y + 1, x + size - 1, y + 1,
                       fill=STONE_TOP, width=max(1, size // 16))
    _bevel(canvas, x, y, size, STONE_FACE_HI, STONE_SIDE)
    _gleam(canvas, x, y, size)


def draw_stone_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Stone block that is no longer solid — ghost/phantom outline."""
    draw_floor(canvas, x, y, size, fast=fast)
    if fast:
        return
    m = max(2, size // 6)
    w = max(1, size // 20)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill="", outline=STONE_BASE,
                            width=w, dash=(4, 3))
    # "X" through the center in the same dashed style
    canvas.create_line(x + m, y + m, x + size - m, y + size - m,
                       fill=STONE_BASE, width=max(1, size // 24), dash=(4, 3))
    canvas.create_line(x + m, y + size - m, x + size - m, y + m,
                       fill=STONE_BASE, width=max(1, size // 24), dash=(4, 3))


def draw_seal_wall(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Sealed wall (active) — purple-striped wall tile like the HTML's 'sl' class."""
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=SEAL_PURPLE, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=WALL_BASE, outline=WALL_MORTAR, width=1)
    # diagonal purple stripes at 45°, clipped to the cell
    step = max(4, size // 4)
    w = max(1, size // 16)
    for d in range(-size, size + 1, step):
        if d >= 0:
            x1, y1 = x + d, y
            x2, y2 = x + size, y + size - d
        else:
            x1, y1 = x, y - d
            x2, y2 = x + size + d, y + size
        canvas.create_line(x1, y1, x2, y2, fill=SEAL_PURPLE, width=w)
    if size >= 28:
        canvas.create_text(x + size // 2, y + size // 2, text="🔒",
                           font=("Arial", max(8, size // 3)), anchor="center")
    _bevel(canvas, x, y, size, "#a78bfa", "#2a1a5a")
    _glow(canvas, x + size // 2, y + size // 2, size // 2, SEAL_PURPLE)


def draw_warp(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Hidden portal — blue oval ring from assets/portal.jpeg.

    The photo is keyed (near-black -> transparent), autocropped and
    fitted into the cell.  Without Pillow / the asset / a Tk root,
    falls back to procedural indigo rings so tests stay headless-safe.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _portal_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        cx, cy = x + size // 2, y + size // 2
        m = max(2, size // 8)
        outer = max(3, size // 2 - m)
        canvas.create_oval(cx - outer, cy - outer, cx + outer, cy + outer,
                           fill="", outline=WARP_INDIGO, width=max(1, size // 20))
        return
    cx, cy = x + size // 2, y + size // 2
    m = max(2, size // 8)
    outer = max(3, size // 2 - m)
    inner = max(2, outer // 2)
    w = max(1, size // 20)
    canvas.create_oval(cx - outer, cy - outer, cx + outer, cy + outer,
                       fill="", outline=WARP_INDIGO, width=w, dash=(4, 3))
    canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner,
                       fill="", outline=WARP_INDIGO, width=w, dash=(3, 3))
    if size >= 24:
        canvas.create_text(cx, cy, text="🌀",
                           font=("Arial", max(8, size // 3)), anchor="center")
    # faint static halo; the animated vortex lives in draw_warp_fx
    _glow(canvas, cx, cy, outer, WARP_INDIGO, layers=2)


def draw_mine(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Visible land mine — pixel bomb from assets/boom.jpeg.

    Without Pillow / the asset / a Tk root, falls back to the red
    danger marker so tests stay headless-safe.  The fuse stem is part
    of the static body; the sputtering spark is drawn by draw_mine_fx.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    # fuse stem arcing out of the bomb top toward the spark tip
    _tx, _ty = _mine_fuse_tip(x, y, size)
    _bx, _by = x + size // 2 + 2, y + int(size * 0.30)
    canvas.create_line(_bx, _by, (_bx + _tx) // 2, (_by + _ty) // 2 - 1,
                       _tx, _ty, fill="#7a4f2a",
                       width=max(2, size // 16), smooth=True)
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _boom_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 6)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill=TRAP_RED, outline="#e05565", width=1)
        return
    draw_trap_lethal(canvas, x, y, size, fast=fast)


# ── full-window background: ONE image for the whole window ───────────
# The art is resized once to the full window size (_panel_base_image) and
# every surface — board canvas (left crop), panel (right strip), labels
# (aligned slices) — is cut from that same image, so the backdrop flows
# seamlessly across the window with no scaling seams.
BACKGROUND_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "assets", "background.jpeg")
_bg_src = None          # cached RGB PIL image, or False when unavailable


def get_canvas_photo(win_w: int, win_h: int, cw: int, ch: int):
    """Backdrop crop for the board canvas, from the ONE window-sized image.

    The canvas occupies the window's top-left (cw x ch), so cropping there
    keeps it pixel-continuous with the panel slices on the right.
    Returns a PhotoImage, or None when unavailable/de-generate.
    """
    if min(win_w, win_h, cw, ch) < 10:
        return None
    _check_photo_root()
    base = _panel_base_image(win_w, win_h)
    if base is None:
        return None
    key = ("canvas", int(win_w), int(win_h), int(cw), int(ch))
    if key in _panel_photos:
        return _panel_photos[key]
    try:
        crop = base.crop((0, 0, int(cw), int(ch)))
        photo = _PILImageTk.PhotoImage(crop)
    except Exception:
        return None
    if len(_panel_photos) >= 30:
        _panel_photos.pop(next(iter(_panel_photos)))
    _panel_photos[key] = photo
    return photo


# ── side-panel backdrop (same art, darkened for readability) ─────────
# Tk frames/labels are opaque, so the canvas photo cannot show through.
# Instead the panel gets its own slices of the same backdrop, darkened
# so light text stays readable, aligned to panel coordinates.
_panel_base: dict[tuple[int, int], object] = {}  # (win_w, win_h) -> RGB PIL
_panel_photos: dict[tuple, object] = {}          # slice keys -> PhotoImage
PANEL_DARKEN = 0.45


def _panel_base_image(win_w: int, win_h: int):
    """Window-sized RGB art shared by all panel slices (cached, max 3)."""
    key = (int(win_w), int(win_h))
    if key in _panel_base:
        return _panel_base[key]
    if not _PIL_AVAILABLE:
        return None
    global _bg_src
    if _bg_src is None:
        try:
            _bg_src = _PILImage.open(BACKGROUND_IMAGE).convert("RGB")
        except (OSError, FileNotFoundError):
            _bg_src = False
            return None
    if _bg_src is False:
        return None
    img = _bg_src.resize(key, _PILImage.BILINEAR)
    if len(_panel_base) >= 3:
        _panel_base.pop(next(iter(_panel_base)))
    _panel_base[key] = img
    return img


def _darken(img, factor: float = PANEL_DARKEN):
    return img.point(lambda v: int(v * factor))


def get_panel_photo(win_w: int, win_h: int, panel_w: int):
    """Right-strip backdrop for the whole side panel. PhotoImage or None."""
    _check_photo_root()
    base = _panel_base_image(win_w, win_h)
    if base is None:
        return None
    key = ("panel", int(win_w), int(win_h), int(panel_w))
    if key in _panel_photos:
        return _panel_photos[key]
    try:
        crop = base.crop((int(win_w) - int(panel_w), 0, int(win_w), int(win_h)))
        photo = _PILImageTk.PhotoImage(_darken(crop))
    except Exception:
        return None
    if len(_panel_photos) >= 8:
        _panel_photos.pop(next(iter(_panel_photos)))
    _panel_photos[key] = photo
    return photo


def get_panel_slice(px: int, py: int, w: int, h: int,
                    win_w: int, win_h: int, panel_w: int):
    """Label-sized slice aligned to panel coords. PhotoImage or None."""
    if w < 4 or h < 4:
        return None
    _check_photo_root()
    base = _panel_base_image(win_w, win_h)
    if base is None:
        return None
    key = ("slice", int(px), int(py), int(w), int(h),
           int(win_w), int(win_h), int(panel_w))
    if key in _panel_photos:
        return _panel_photos[key]
    try:
        x0 = int(win_w) - int(panel_w) + int(px)
        crop = base.crop((x0, int(py), x0 + int(w), int(py) + int(h)))
        photo = _PILImageTk.PhotoImage(_darken(crop))
    except Exception:
        return None
    if len(_panel_photos) >= 24:
        _panel_photos.pop(next(iter(_panel_photos)))
    _panel_photos[key] = photo
    return photo


# ── portal photo support (assets/portal.jpeg) ─────────────────────────
PORTAL_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "portal.jpeg")
_portal_src = None      # cached RGBA PIL image, or False when unavailable
_portal_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_portal_src():
    """Load the portal photo keyed to RGBA (near-black -> transparent).

    Returns a PIL RGBA image, or None when Pillow / the file is missing.
    The result (including the miss) is cached.
    """
    global _portal_src
    if _portal_src is not None:
        return _portal_src or None
    if not _PIL_AVAILABLE:
        _portal_src = False
        return None
    try:
        img = _PILImage.open(PORTAL_IMAGE).convert("RGB")
    except (OSError, FileNotFoundError):
        _portal_src = False
        return None
    gray = img.convert("L")
    solid = gray.point(lambda v: 255 if v > 18 else 0)
    bbox = solid.getbbox()
    if bbox:
        img = img.crop(bbox)
        gray = gray.crop(bbox)
    # soft alpha ramp so the glow edge blends instead of clipping
    alpha = gray.point(
        lambda v: 0 if v <= 14 else (255 if v >= 56 else int((v - 14) * 255 / 42)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _portal_src = img
    return img


def _portal_photo(size: int):
    """PhotoImage of the portal fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _portal_photos:
        return _portal_photos[key]
    src = _load_portal_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _portal_photos[key] = photo
    return photo


# ── land-mine photo support (assets/boom.jpeg, white background) ──────
BOOM_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "boom.jpeg")
_boom_src = None        # cached RGBA PIL image, or False when unavailable
_boom_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_boom_src():
    """Load the bomb photo keyed to RGBA (near-white -> transparent).

    Returns a PIL RGBA image, or None when Pillow / the file is missing.
    The result (including the miss) is cached.
    """
    global _boom_src
    if _boom_src is not None:
        return _boom_src or None
    if not _PIL_AVAILABLE:
        _boom_src = False
        return None
    try:
        img = _PILImage.open(BOOM_IMAGE).convert("RGB")
    except (OSError, FileNotFoundError):
        _boom_src = False
        return None
    gray = img.convert("L")
    content = gray.point(lambda v: 0 if v > 235 else 255)
    bbox = content.getbbox()
    if bbox:
        img = img.crop(bbox)
        gray = gray.crop(bbox)
    # soft alpha ramp so anti-aliased edges blend instead of clipping
    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _boom_src = img
    return img


def _boom_photo(size: int):
    """PhotoImage of the bomb fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _boom_photos:
        return _boom_photos[key]
    src = _load_boom_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _boom_photos[key] = photo
    return photo


# ── player photo support (assets/player.png, near-white background) ─
PLAYER_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "player.png")
_player_src = None        # cached RGBA PIL image, or False when unavailable
_player_photos: dict = {}  # (quant-size, sharp) -> PhotoImage


def _load_player_src():
    """Load the knight sprite keyed to RGBA (near-white -> transparent).

    Returns a PIL RGBA image, or None when Pillow / the file is missing.
    The result (including the miss) is cached.
    """
    global _player_src
    if _player_src is not None:
        return _player_src or None
    if not _PIL_AVAILABLE:
        _player_src = False
        return None
    try:
        img = _PILImage.open(PLAYER_IMAGE).convert("RGB")
    except (OSError, FileNotFoundError):
        _player_src = False
        return None
    gray = img.convert("L")
    content = gray.point(lambda v: 0 if v > 235 else 255)
    bbox = content.getbbox()
    if bbox:
        img = img.crop(bbox)
        gray = gray.crop(bbox)
    # soft alpha ramp so anti-aliased edges blend instead of clipping
    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _player_src = img
    return img


def _player_photo(size: int, sharp: bool = False):
    """PhotoImage of the knight fitted into a `size`px cell (cached).

    `sharp` uses NEAREST scaling so pixel art stays crisp when shown
    large (menus); the game default stays BILINEAR for smooth minifying.
    """
    _check_photo_root()
    key = (_quant_size(size), bool(sharp))
    if key in _player_photos:
        return _player_photos[key]
    src = _load_player_src()
    if src is None:
        return None
    side = max(8, int(key[0] * 0.92))
    fit = src.copy()
    filt = _PILImage.NEAREST if sharp else _PILImage.BILINEAR
    fit.thumbnail((side, side), filt)
    photo = _PILImageTk.PhotoImage(fit)
    _player_photos[key] = photo
    return photo


# ── laser-gate photo support (assets/laser.png, transparent) ─────────
LASER_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "laser.png")
_laser_src = None         # cached RGBA PIL image, or False when unavailable
_laser_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_laser_src():
    """Load the laser-gate art (assets/laser.png) as RGBA.

    The file already carries transparency, so it is used as-is after an
    autocrop to the non-transparent bbox.  Returns a PIL RGBA image, or
    None when Pillow / the file is missing.  The result (including the
    miss) is cached.
    """
    global _laser_src
    if _laser_src is not None:
        return _laser_src or None
    if not _PIL_AVAILABLE:
        _laser_src = False
        return None
    try:
        img = _PILImage.open(LASER_IMAGE).convert("RGBA")
    except (OSError, FileNotFoundError):
        _laser_src = False
        return None
    alpha = img.getchannel("A")
    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    _laser_src = img
    return img


def _laser_photo(size: int):
    """PhotoImage of the laser gate fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _laser_photos:
        return _laser_photos[key]
    src = _load_laser_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _laser_photos[key] = photo
    return photo


def draw_laser(canvas: tk.Canvas, x: int, y: int, size: int,
               active: bool = True, fast: bool = False):
    """Laser gate — red beams between stone emitters (assets/laser.png).

    Mirrors the reference art: grey emitter caps top/bottom with four
    vertical red beams.  Without Pillow / the asset / a Tk root, falls
    back to procedural beams so tests stay headless-safe.  When
    `active` is False the beams are off and only the floor shows.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    if not active:
        return
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _laser_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 10)
        canvas.create_rectangle(x + m, y + 1, x + size - m, y + size - 1,
                                fill="#e34b3e", outline="")
        return
    # Procedural fallback: grey emitter bars + 4 red beams w/ white core.
    _glow(canvas, x + size // 2, y + size // 2, size // 2, "#e34b3e")
    m = max(2, size // 10)
    cap_h = max(3, size // 6)
    canvas.create_rectangle(x + 1, y + 1, x + size - 1, y + 1 + cap_h,
                            fill="#5a5e78", outline="#383b52", width=1)
    canvas.create_rectangle(x + 1, y + size - 1 - cap_h,
                            x + size - 1, y + size - 1,
                            fill="#5a5e78", outline="#383b52", width=1)
    beams = 4
    for i in range(beams):
        bx = x + m + (size - 2 * m) * (i + 0.5) / beams
        bw = max(2, size // 14)
        canvas.create_line(bx, y + 1 + cap_h, bx, y + size - 1 - cap_h,
                           fill="#e34b3e", width=bw)
        canvas.create_line(bx, y + 1 + cap_h, bx, y + size - 1 - cap_h,
                           fill="#fff0f0", width=max(1, bw // 3))


# ── ash-pile photo support (assets/ash.jpeg, white background) ───────
ASH_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "ash.jpeg")
_ash_src = None           # cached RGBA PIL image, or False when unavailable
_ash_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_ash_src():
    """Load the ash-pile art (assets/ash.jpeg) keyed to RGBA.

    The file has a near-white background, so it is keyed to transparent
    (like the bomb art), autocropped and cached.  Returns a PIL RGBA
    image, or None when Pillow / the file is missing.
    """
    global _ash_src
    if _ash_src is not None:
        return _ash_src or None
    if not _PIL_AVAILABLE:
        _ash_src = False
        return None
    try:
        img = _PILImage.open(ASH_IMAGE).convert("RGB")
    except (OSError, FileNotFoundError):
        _ash_src = False
        return None
    gray = img.convert("L")
    content = gray.point(lambda v: 0 if v > 235 else 255)
    bbox = content.getbbox()
    if bbox:
        img = img.crop(bbox)
        gray = gray.crop(bbox)
    # soft alpha ramp so anti-aliased edges blend instead of clipping
    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _ash_src = img
    return img


def _ash_photo(size: int):
    """PhotoImage of the ash pile fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _ash_photos:
        return _ash_photos[key]
    src = _load_ash_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _ash_photos[key] = photo
    return photo


def draw_ash(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Ash pile left when the laser vaporises the character.

    Grey mound from assets/ash.jpeg on the floor.  Without Pillow / the
    asset / a Tk root, falls back to a procedural mound so tests stay
    headless-safe.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _ash_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        cx = x + size // 2
        base_y = y + size - max(2, size // 6)
        half = max(3, size // 2 - max(2, size // 6))
        canvas.create_rectangle(cx - half, base_y - max(1, size // 12),
                                cx + half, base_y,
                                fill="#4a4a52", outline="")
        return
    # Procedural fallback: dark grey pixel mound with scattered crumbs.
    cx = x + size // 2
    base_y = y + size - max(2, size // 6)
    half = max(3, size // 2 - max(2, size // 6))
    rows = max(3, size // 8)
    for r in range(rows):
        w = int(half * (r + 1) / rows)
        ry = base_y - int((size // 3) * r / max(1, rows - 1)) if rows > 1 else base_y
        shade = ("#2a2a2e", "#3a3a40", "#4a4a52")[min(r, 2)]
        canvas.create_rectangle(cx - w, ry - max(1, size // 12),
                                cx + w, ry,
                                fill=shade, outline="")


def _white_keyed_src(path: str):
    """Load an RGB white-background sprite as RGBA (white -> transparent).

    Autocrops to the non-white bbox and applies a soft alpha ramp so
    anti-aliased edges blend.  Returns a PIL RGBA image, or None when
    Pillow / the file is missing.
    """
    if not _PIL_AVAILABLE:
        return None
    try:
        img = _PILImage.open(path).convert("RGB")
    except (OSError, FileNotFoundError):
        return None
    gray = img.convert("L")
    content = gray.point(lambda v: 0 if v > 235 else 255)
    bbox = content.getbbox()
    if bbox:
        img = img.crop(bbox)
        gray = gray.crop(bbox)
    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    return img


# ── stone-pile photo support (assets/stone.jpeg, white background) ──
STONE_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "stone.jpeg")
_stone_src = None         # cached RGBA PIL image, or False when unavailable
_stone_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_stone_src():
    """Load the stone-pile art keyed to RGBA (cached, incl. the miss)."""
    global _stone_src
    if _stone_src is not None:
        return _stone_src or None
    _stone_src = _white_keyed_src(STONE_IMAGE) or False
    return _stone_src or None


def _stone_photo(size: int):
    """PhotoImage of the stone pile fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _stone_photos:
        return _stone_photos[key]
    src = _load_stone_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _stone_photos[key] = photo
    return photo


# ── wooden-door photo support (assets/door.jpeg, white background) ──
DOOR_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "door.jpeg")
_door_src = None          # cached RGBA PIL image, or False when unavailable
_door_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_door_src():
    """Load the wooden-door art keyed to RGBA (cached, incl. the miss)."""
    global _door_src
    if _door_src is not None:
        return _door_src or None
    _door_src = _white_keyed_src(DOOR_IMAGE) or False
    return _door_src or None


def _door_photo(size: int):
    """PhotoImage of the wooden door fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _door_photos:
        return _door_photos[key]
    src = _load_door_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _door_photos[key] = photo
    return photo


# ── live-trap photo support (assets/trap.gif, opaque full-bleed) ────
TRAP_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "trap.gif")
_trap_src = None          # cached RGBA PIL image, or False when unavailable
_trap_photos: dict[int, object] = {}  # cell size -> PhotoImage
_trap_tk_photos: dict[int, object] = {}  # cell size -> Tk-native PhotoImage


def _load_trap_src():
    """Load the first frame of the trap GIF as RGBA (cached, incl. miss).

    The art is a full-bleed opaque texture, so no keying or cropping is
    applied — tiles don't animate, frame 0 stands in for the loop.
    """
    global _trap_src
    if _trap_src is not None:
        return _trap_src or None
    if not _PIL_AVAILABLE:
        _trap_src = False
        return None
    try:
        img = _PILImage.open(TRAP_IMAGE)
        img.seek(0)
        img = img.convert("RGBA")
    except (OSError, FileNotFoundError):
        _trap_src = False
        return None
    _trap_src = img
    return img


def _trap_photo_tk(size: int):
    """Tk-native GIF load (no Pillow needed), fitted into a `size`px cell.

    Tk's PhotoImage reads GIFs on its own, so the trap art shows even
    when Pillow is not installed.  Subsample only does integer shrink,
    so this is approximate — the Pillow path above stays preferred.
    Returns None headless (no Tk root) or when the asset is missing.
    """
    _check_photo_root()
    key = _quant_size(size)
    if key in _trap_tk_photos:
        return _trap_tk_photos[key]
    try:
        if tk._default_root is None:
            return None
        photo = tk.PhotoImage(file=TRAP_IMAGE, format="gif -index 0")
    except Exception:
        try:
            photo = tk.PhotoImage(file=TRAP_IMAGE)
        except Exception:
            return None
    try:
        w, h = int(photo.width()), int(photo.height())
        factor = max(1, min(w, h) // max(8, key))
        if factor > 1:
            photo = photo.subsample(factor, factor)
    except Exception:
        pass
    _trap_tk_photos[key] = photo
    return photo


def _trap_photo(size: int):
    """PhotoImage of the live trap fitted into a `size`px cell (cached).

    The whole GIF frame is fitted into the cell so the tile mirrors the
    art's layout (dark strip on top, rain field below).
    """
    _check_photo_root()
    key = _quant_size(size)
    if key in _trap_photos:
        return _trap_photos[key]
    src = _load_trap_src()
    if src is None:
        # Pillow missing/unusable — fall back to Tk's built-in GIF reader.
        return _trap_photo_tk(size)
    side = max(8, int(key))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _trap_photos[key] = photo
    return photo


# ── skeleton photo support (assets/skeleton.png, white background) ──
SKELETON_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "assets", "skeleton.png")
_skel_src = None          # cached RGBA PIL image, or False when unavailable
_skel_photos: dict[int, object] = {}  # cell size -> PhotoImage


def _load_skel_src():
    """Load the skeleton art keyed to RGBA (cached, incl. the miss)."""
    global _skel_src
    if _skel_src is not None:
        return _skel_src or None
    _skel_src = _white_keyed_src(SKELETON_IMAGE) or False
    return _skel_src or None


def _skel_photo(size: int):
    """PhotoImage of the skeleton fitted into a `size`px cell (cached)."""
    _check_photo_root()
    key = _quant_size(size)
    if key in _skel_photos:
        return _skel_photos[key]
    src = _load_skel_src()
    if src is None:
        return None
    side = max(8, int(key * 0.92))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _skel_photos[key] = photo
    return photo


# ── lever photo support (assets/lever.png, white background) ──
LEVER_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "lever.png")
_lever_src = None          # cached RGBA PIL image, or False when unavailable
_lever_photos: dict[tuple, object] = {}  # (size, active) -> PhotoImage


def _load_lever_src():
    """Load the lever art keyed to RGBA (cached, incl. the miss)."""
    global _lever_src
    if _lever_src is not None:
        return _lever_src or None
    _lever_src = _white_keyed_src(LEVER_IMAGE) or False
    return _lever_src or None


def _lever_photo(size: int, active: bool = False):
    """PhotoImage of the lever fitted into a `size`px cell (cached).

    Inactive (handle up) uses the art as-is. Active (handle down) uses a
    vertically flipped copy so the handle visibly drops.
    """
    _check_photo_root()
    key = (_quant_size(size), bool(active))
    if key in _lever_photos:
        return _lever_photos[key]
    src = _load_lever_src()
    if src is None:
        return None
    side = max(8, int(key[0] * 0.92))
    fit = src.copy()
    if active:
        try:
            fit = fit.transpose(_PILImage.FLIP_TOP_BOTTOM)
        except Exception:
            pass
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _lever_photos[key] = photo
    return photo


def draw_lever(canvas: tk.Canvas, x: int, y: int, size: int,
               active: bool = False, fast: bool = False):
    """Lever pedestal from assets/lever.png, else procedural.

    Inactive handle points up, active handle points down.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    photo = None
    try:
        photo = _lever_photo(size, active=active)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        m = max(2, size // 6)
        canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                                fill="#5a5e78", outline="#383b52", width=1)
        return
    # Procedural fallback: grey base + orange handle up/down.
    cx = x + size // 2
    base_y0 = y + int(size * 0.62)
    base_y1 = y + size - max(2, size // 10)
    m = max(2, size // 6)
    canvas.create_rectangle(x + m, base_y0, x + size - m, base_y1,
                            fill="#5a5e78", outline="#0a0a0a",
                            width=max(1, size // 20))
    canvas.create_rectangle(x + m, base_y0, x + size - m, base_y0 + max(2, size // 12),
                            fill="#9aa0bd", outline="")
    _gleam(canvas, x, y, size)
    # rod
    rod_w = max(2, size // 12)
    if not active:
        # handle up
        canvas.create_rectangle(cx - rod_w // 2, y + max(2, size // 8),
                                cx + rod_w // 2 + 1, base_y0,
                                fill="#c0c0c0", outline="#0a0a0a")
        hw, hh = max(4, size // 4), max(6, size // 3)
        canvas.create_rectangle(cx - hw // 2, y + max(1, size // 12),
                                cx + hw // 2, y + max(1, size // 12) + hh,
                                fill="#d96b1a", outline="#0a0a0a",
                                width=max(1, size // 24))
    else:
        # handle down (pulled toward the base, angled right)
        canvas.create_line(cx, base_y0 - max(1, size // 8),
                           cx + int(size * 0.28), base_y0,
                           fill="#c0c0c0", width=rod_w)
        hr = max(3, size // 6)
        hx, hy = cx + int(size * 0.28), base_y0 - max(1, size // 12)
        canvas.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                           fill="#d96b1a", outline="#0a0a0a",
                           width=max(1, size // 24))


def draw_skeleton(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False):
    """Skeleton left when a live trap kills the character.

    Pixel skull from assets/skeleton.png on the floor.  Without Pillow /
    the asset / a Tk root, falls back to a procedural skull so tests stay
    headless-safe.
    """
    draw_floor(canvas, x, y, size, fast=fast)
    # Photo first in both modes (see draw_door_closed).
    photo = None
    try:
        photo = _skel_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    if fast:
        cx, cy = x + size // 2, y + size // 2
        r = max(4, size // 2 - max(2, size // 8))
        canvas.create_oval(cx - r, cy - r, cx + r, cy + int(r * 0.7),
                           fill="#d8d8dc", outline="#0a0a0a")
        return
    # Procedural fallback: pale skull oval, dark eye sockets, jaw lines.
    cx, cy = x + size // 2, y + size // 2
    r = max(4, size // 2 - max(2, size // 8))
    canvas.create_oval(cx - r, cy - r, cx + r, cy + int(r * 0.7),
                       fill="#d8d8dc", outline="#0a0a0a",
                       width=max(1, size // 24))
    er = max(2, r // 3)
    for dx in (-1, 1):
        ex = cx + dx * int(r * 0.45)
        ey = cy - int(r * 0.1)
        canvas.create_oval(ex - er, ey - er, ex + er, ey + er,
                           fill="#0a0a0a", outline="#0a0a0a")
