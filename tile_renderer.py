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
import tkinter as tk
import math

# ── colour palette ───────────────────────────────────────────────────
WALL_BASE      = "#3b3f5e"
WALL_MORTAR    = "#2a2d48"
FLOOR_BASE     = "#1b1f3f"
FLOOR_LINE     = "#242850"
GOAL_GREEN     = "#2e8f4c"
GOAL_FLAG      = "#4adc6e"
GOAL_POLE      = "#c0c0c0"
PLAYER_BODY    = "#f4f874"
PLAYER_EYE     = "#333333"
PLAYER_OUTLINE = "#c8c840"
PLATFORM_SOLID = "#7b5cff"
PLATFORM_PILLAR= "#5a3fd6"
PLATFORM_GHOST = "#574d87"
PLATFORM_GHOST_DASH = "#7b6baf"
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
FRAGMENT_COLOR = "#f4f874"
BLOCK_BG       = "#1a3a6a"
BLOCK_BORDER   = "#42a7ff"
BLOCK_TEXT     = "#e8f0ff"
CIRCUIT_SLOT_BG    = "#1e2850"
CIRCUIT_SLOT_BORDER= "#5f7fff"


# ── helper ──────────────────────────────────────────────────────────
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


# ── entity drawing functions ────────────────────────────────────────

def draw_wall(canvas: tk.Canvas, x: int, y: int, size: int):
    """Brick-pattern wall."""
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


def draw_floor(canvas: tk.Canvas, x: int, y: int, size: int):
    """Subtle dark floor tile."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=FLOOR_BASE, outline=FLOOR_LINE, width=1)
    # inner accent line
    m = max(1, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill="", outline=FLOOR_LINE, width=1)


def draw_goal(canvas: tk.Canvas, x: int, y: int, size: int):
    """Green flag on a pole."""
    # floor background
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1a3020", outline="#2e4a3a", width=1)
    # pulsing glow
    m = max(2, size // 6)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=GOAL_GREEN, outline="#3ab85e", width=2)
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


def draw_player(canvas: tk.Canvas, x: int, y: int, size: int):
    """Yellow circle character with an eye."""
    # floor underneath
    draw_floor(canvas, x, y, size)
    # body circle
    m = max(2, size // 6)
    cx, cy = x + size // 2, y + size // 2
    r = size // 2 - m
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                       fill=PLAYER_BODY, outline=PLAYER_OUTLINE, width=max(1, size // 20))
    # eye
    er = max(2, r // 4)
    ex = cx + r // 4
    ey = cy - r // 4
    canvas.create_oval(ex - er, ey - er, ex + er, ey + er,
                       fill=PLAYER_EYE, outline=PLAYER_EYE)
    # highlight
    hr = max(1, r // 5)
    hx = cx - r // 3
    hy = cy - r // 3
    canvas.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                       fill="#fffff0", outline="#fffff0")


def draw_boom_explosion(canvas: tk.Canvas, x: int, y: int, size: int):
    """A blast cloud and scattered character fragments after the hidden boom fires."""
    draw_floor(canvas, x, y, size)
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

    # The yellow fragments make the character visibly break apart.
    fragment = max(2, size // 11)
    for dx, dy in ((-0.34, -0.31), (0.31, -0.25), (-0.38, 0.29), (0.35, 0.33)):
        fx, fy = cx + int(size * dx), cy + int(size * dy)
        canvas.create_polygon(fx, fy - fragment,
                              fx + fragment, fy,
                              fx, fy + fragment,
                              fx - fragment, fy,
                              fill=FRAGMENT_COLOR, outline=PLAYER_OUTLINE)


def draw_platform_solid(canvas: tk.Canvas, x: int, y: int, size: int):
    """Solid purple bridge with support pillars."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
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


def draw_platform_ghost(canvas: tk.Canvas, x: int, y: int, size: int):
    """Ghost/non-solid platform — dashed outline of the bridge shape."""
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


def draw_door_closed(canvas: tk.Canvas, x: int, y: int, size: int):
    """Closed orange door with keyhole."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
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


def draw_door_open(canvas: tk.Canvas, x: int, y: int, size: int):
    """Open door — split panels revealing passage."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1a2a1a", outline="#2e4a2e", width=1)
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


def draw_trap_lethal(canvas: tk.Canvas, x: int, y: int, size: int):
    """Red danger zone with spike triangles."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#2a1015", outline="#4a2025", width=1)
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


def draw_trap_safe(canvas: tk.Canvas, x: int, y: int, size: int):
    """Disarmed trap — grayed out, no spikes."""
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f2f", outline="#2a2f40", width=1)
    m = max(2, size // 6)
    cx, cy = x + size // 2, y + size // 2
    half = size // 2 - m
    canvas.create_polygon(cx, cy - half,
                          cx + half, cy,
                          cx, cy + half,
                          cx - half, cy,
                          fill="", outline=TRAP_SAFE_LINE,
                          width=max(1, size // 24), dash=(4, 3))


def draw_code_block(canvas: tk.Canvas, x: int, y: int, size: int,
                    label: str, kind: str):
    """Rounded-rectangle 'chip' with a label.  Colour varies by kind."""
    kind_colors = {
        "CLASS":  ("#1a4a7a", "#52b0ff"),
        "PROP":   ("#1a5a4a", "#40d8a0"),
        "OP":     ("#4a3a1a", "#d0a840"),
        "VALUE":  ("#3a1a5a", "#b070e0"),
    }
    bg, border = kind_colors.get(kind, (BLOCK_BG, BLOCK_BORDER))
    m = max(1, size // 10)
    r = max(3, size // 6)
    x1, y1, x2, y2 = x + m, y + m, x + size - m, y + size - m
    _rounded_rect(canvas, x1, y1, x2, y2, r, fill=bg, outline=border,
                  width=max(1, size // 20))
    # inner highlight line at top
    canvas.create_line(x1 + r, y1 + 2, x2 - r, y1 + 2,
                       fill=border, width=1)
    # label text
    cx = x + size // 2
    cy = y + size // 2
    font_size = max(7, min(size // 5, 14))
    canvas.create_text(cx, cy, text=label, fill=BLOCK_TEXT,
                       font=("Consolas", font_size, "bold"), anchor="center")


def draw_circuit_slot(canvas: tk.Canvas, x: int, y: int, size: int):
    """Dashed rounded-rect outline marking a compiler slot."""
    draw_floor(canvas, x, y, size)
    m = max(2, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=CIRCUIT_SLOT_BG, outline=CIRCUIT_SLOT_BORDER,
                            width=max(1, size // 16), dash=(5, 3))
    # small dot in center
    cx, cy = x + size // 2, y + size // 2
    dr = max(1, size // 16)
    canvas.create_oval(cx - dr, cy - dr, cx + dr, cy + dr,
                       fill=CIRCUIT_SLOT_BORDER, outline=CIRCUIT_SLOT_BORDER)
