
from __future__ import annotations
import math
import os
import tkinter as tk

try:
    from PIL import Image as _PILImage, ImageTk as _PILImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PILImage = None
    _PILImageTk = None
    _PIL_AVAILABLE = False




_photo_root = None


def _check_photo_root():
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
            DungeonSheet.clear()
        except NameError:
            pass
        for _cache in ("_trap_anim_frames", "_trap_scaled", "_trap_tk_photos"):
            _obj = globals().get(_cache)
            if _obj is not None:
                try:
                    _obj.clear()
                except Exception:
                    pass
        _photo_root = cur


def _quant_size(size: int) -> int:
    return max(8, int(round(float(size) / 2.0) * 2))



class DungeonSheet:

    DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "assets", "dungeon")



    FRAMES = {
        "walls_floor.png": (16, 16),
        "trap_animation.png": (48, 48),
        "fire_animation.png": (16, 16),
        "fire_animation2.png": (16, 16),
        "doors_lever_chest_animation.png": (32, 32),
        "Objects.png": (16, 16),
        "decorative_cracks_floor.png": (16, 16),
        "decorative_cracks_walls.png": (16, 16),
    }

    _images: dict[str, object] = {}
    _frames: dict[tuple, object] = {}


    @classmethod
    def path_of(cls, sheet_name: str) -> str:
        return os.path.join(cls.DIR, sheet_name)

    @classmethod
    def clear(cls):
        cls._frames.clear()

    @classmethod
    def _image(cls, sheet_name: str):
        if sheet_name in cls._images:
            cached = cls._images[sheet_name]
            return cached if cached else None
        if not _PIL_AVAILABLE:
            cls._images[sheet_name] = False
            return None
        try:
            img = _PILImage.open(cls.path_of(sheet_name)).convert("RGBA")
        except Exception:
            cls._images[sheet_name] = False
            return None
        cls._images[sheet_name] = img
        return img

    @classmethod
    def available(cls, sheet_name: str) -> bool:
        return cls._image(sheet_name) is not None

    @classmethod
    def frame_size(cls, sheet_name: str):
        return cls.FRAMES.get(sheet_name)

    @classmethod
    def grid(cls, sheet_name: str):
        img = cls._image(sheet_name)
        size = cls.FRAMES.get(sheet_name)
        if img is None or not size:
            return None
        return (max(0, img.width // size[0]), max(0, img.height // size[1]))

    @classmethod
    def frame_image(cls, sheet_name: str, col: int, row: int):
        img = cls._image(sheet_name)
        size = cls.FRAMES.get(sheet_name)
        if img is None or not size:
            return None
        fw, fh = size
        try:
            col, row = int(col), int(row)
        except (TypeError, ValueError):
            return None
        cols, rows = img.width // fw, img.height // fh
        if not (0 <= col < cols and 0 <= row < rows):
            return None
        try:
            return img.crop((col * fw, row * fh,
                             col * fw + fw, row * fh + fh))
        except Exception:
            return None


    @classmethod
    def get_frame(cls, sheet_name: str, col: int, row: int,
                  scale_to_px: int):
        try:
            _check_photo_root()
            px = _quant_size(scale_to_px)
            key = (sheet_name, int(col), int(row), int(px))
            cached = cls._frames.get(key)
            if cached is not None:
                return cached
            frame = cls.frame_image(sheet_name, col, row)
            if frame is None:
                return None
            side = max(8, int(px))
            out = frame.copy()
            if out.size != (side, side):



                out = out.resize((side, side), _PILImage.NEAREST)
            photo = _PILImageTk.PhotoImage(out)
        except Exception:
            return None
        if len(cls._frames) >= 400:
            cls._frames.pop(next(iter(cls._frames)))
        cls._frames[key] = photo
        return photo


def _sheet_photo(sheet_name: str, col: int, row: int, size: int):
    try:
        return DungeonSheet.get_frame(sheet_name, col, row, size)
    except Exception:
        return None



class _TaggedCanvas:

    __slots__ = ("_canvas", "_tags")

    def __init__(self, canvas, tags):
        self._canvas = canvas
        self._tags = tags

    def __getattr__(self, name):
        return getattr(self._canvas, name)

    def _stamp(self, kw):
        kw["tags"] = self._tags
        return kw

    def create_rectangle(self, *args, **kw):
        return self._canvas.create_rectangle(*args, **self._stamp(kw))

    def create_line(self, *args, **kw):
        return self._canvas.create_line(*args, **self._stamp(kw))

    def create_oval(self, *args, **kw):
        return self._canvas.create_oval(*args, **self._stamp(kw))

    def create_polygon(self, *args, **kw):
        return self._canvas.create_polygon(*args, **self._stamp(kw))

    def create_text(self, *args, **kw):
        return self._canvas.create_text(*args, **self._stamp(kw))

    def create_image(self, *args, **kw):
        return self._canvas.create_image(*args, **self._stamp(kw))

    def create_arc(self, *args, **kw):
        return self._canvas.create_arc(*args, **self._stamp(kw))

    def create_bitmap(self, *args, **kw):
        return self._canvas.create_bitmap(*args, **self._stamp(kw))


def _tagged(canvas, tags):
    if not tags:
        return canvas
    if isinstance(canvas, _TaggedCanvas):
        return _TaggedCanvas(canvas._canvas, tags)
    return _TaggedCanvas(canvas, tags)




WALL_BASE      = "#8a90b0"
WALL_MORTAR    = "#4a4e6e"
FLOOR_BASE     = "#12152c"
FLOOR_LINE     = "#1e2342"
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
GOOMBA_OUTLINE = "#0a0a0a"
GOOMBA_DARK    = "#5a3018"
GOOMBA_BODY    = "#a65e2e"
GOOMBA_LIGHT   = "#d18a4d"
GOOMBA_EYE     = "#ffffff"
GOOMBA_PUPIL   = "#101018"
GOOMBA_FANG    = "#ffffff"
GOOMBA_STEM    = "#e3cda3"
GOOMBA_FOOT    = "#6b4423"
GOOMBA_FOOT_HI = "#a67c3d"

KNIGHT_OUTLINE = "#0a0a0a"
KNIGHT_LIGHT   = "#d9dbe4"
KNIGHT_MID     = "#a8aab8"
KNIGHT_DARK    = "#6e7288"
KNIGHT_VISOR   = "#14141c"
KNIGHT_SHINE   = "#ffffff"
KNIGHT_HILT    = "#d97a2b"
KNIGHT_HILT_D  = "#7a3a18"
KNIGHT_BLADE   = "#eef1f8"
KNIGHT_BLADE_D = "#9aa0b0"




WALL_SHEET_COL = 1
WALL_SHEET_ROW = 5
FLOOR_SHEET_COL = 0
FLOOR_SHEET_ROW = 22
PLATFORM_SOLID = "#7b5cff"
PLATFORM_PILLAR= "#5a3fd6"
PLATFORM_GHOST = "#574d87"
PLATFORM_GHOST_DASH = "#7b6baf"
VOID_BG        = "#0a0812"
VOID_RING      = "#1a0f2e"
VOID_CORE      = "#000000"
VOID_RIM       = "#c8a84b"
VOID_GLOW      = "#c8a84b"
VOID_EMBER     = "#e05565"
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




SEAL_SHEET_COL = {
    "SealWall": 1,
    "Seal2Wall": 2,
    "Seal3Wall": 3,
    "Seal4Wall": 4,
    "Seal5Wall": 5,
    "Seal6Wall": 1,
}



WALL_HI          = "#c8cde6"
WALL_SHADOW      = "#2a2d48"
FLOOR_HI         = "#2e345e"
FLOOR_SHADOW     = "#05060f"
STONE_FACE_HI    = "#9aa0bd"
STONE_SIDE       = "#3c3f58"
CODE_SHADOW      = "#0a0c1a"
DOOR_HI          = "#f5c080"
DOOR_SHADOW      = "#5a2810"



def _bevel(canvas, x, y, size, light, dark, depth=None):
    d = max(2, size // 8) if depth is None else max(1, int(depth))
    d = min(d, size // 3)
    x2, y2 = x + size, y + size

    canvas.create_polygon(x, y, x2, y, x2 - d, y + d, x + d, y + d,
                          fill=light, outline="")

    canvas.create_polygon(x, y, x + d, y + d, x + d, y2 - d, x, y2,
                          fill=light, outline="")

    canvas.create_polygon(x, y2, x + d, y2 - d, x2 - d, y2 - d, x2, y2,
                          fill=dark, outline="")

    canvas.create_polygon(x2, y, x2, y2, x2 - d, y2 - d, x2 - d, y + d,
                          fill=dark, outline="")


def _drop_shadow(canvas, x, y, size, dx=None, dy=None, fill=CODE_SHADOW):
    dx = max(1, size // 12) if dx is None else dx
    dy = max(2, size // 8) if dy is None else dy
    canvas.create_rectangle(x + dx, y + dy, x + size + dx, y + size + dy,
                            fill=fill, outline="")


def _inset(x, y, size, frac=0.08):
    m = max(1, int(size * frac))
    return x + m, y + m, x + size - m, y + size - m


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    points = []

    for i in range(r + 1):
        angle = math.pi + math.pi / 2 * (i / max(r, 1))
        points.append((x1 + r + int(r * math.cos(angle)),
                        y1 + r + int(r * math.sin(angle))))

    for i in range(r + 1):
        angle = 3 * math.pi / 2 + math.pi / 2 * (i / max(r, 1))
        points.append((x2 - r + int(r * math.cos(angle)),
                        y1 + r + int(r * math.sin(angle))))

    for i in range(r + 1):
        angle = 0 + math.pi / 2 * (i / max(r, 1))
        points.append((x2 - r + int(r * math.cos(angle)),
                        y2 - r + int(r * math.sin(angle))))

    for i in range(r + 1):
        angle = math.pi / 2 + math.pi / 2 * (i / max(r, 1))
        points.append((x1 + r + int(r * math.cos(angle)),
                        y2 - r + int(r * math.sin(angle))))
    flat = []
    for px, py in points:
        flat.extend([px, py])
    canvas.create_polygon(flat, smooth=False, **kw)




def draw_wall(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    photo = _sheet_photo("walls_floor.png", WALL_SHEET_COL, WALL_SHEET_ROW, size)
    if photo is not None:



        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=WALL_MORTAR, width=1)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")

        _bevel(canvas, x, y, size, WALL_HI, WALL_SHADOW)
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="", outline=WALL_HI, width=1)
        return
    if fast:

        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=WALL_MORTAR, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=WALL_BASE, outline=WALL_MORTAR, width=1)

    rows = max(2, size // 10)
    row_h = size / rows
    for r in range(rows):
        ry = y + int(r * row_h)
        canvas.create_line(x, ry, x + size, ry, fill=WALL_MORTAR, width=1)

        cols = max(2, size // 14)
        col_w = size / cols
        offset = col_w / 2 if r % 2 else 0
        for c in range(cols + 1):
            cx = x + int(c * col_w + offset)
            if x <= cx <= x + size:
                canvas.create_line(cx, ry, cx, ry + int(row_h),
                                   fill=WALL_MORTAR, width=1)

    _bevel(canvas, x, y, size, WALL_HI, WALL_SHADOW)


def draw_floor(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    photo = _sheet_photo("walls_floor.png", FLOOR_SHEET_COL, FLOOR_SHEET_ROW, size)
    if photo is not None:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=FLOOR_BASE, outline="#05060f", width=1)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
               depth=max(1, size // 12))
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="", outline="#05060f", width=1)
        return
    if fast:

        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=FLOOR_BASE, outline=FLOOR_LINE, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=FLOOR_BASE, outline=FLOOR_LINE, width=1)

    m = max(1, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill="", outline=FLOOR_LINE, width=1)

    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 12))


def draw_goal(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None, entry_frame=0, player_inside=False):
    canvas = _tagged(canvas, tags)
    u = size / 16
    C_STONE_MID = "#1c1630"
    C_STONE_HI = "#2a2040"
    C_OUTLINE = "#0d0a1a"
    C_GOLD = "#c8a84b"
    C_GOLD_DIM = "#7a5a10"
    C_TUNNEL = "#06040e"
    C_TUNNEL_MID = "#0a1830"
    C_TUNNEL_FAR = "#0e2040"
    C_VISOR = "#7ab8f5"
    C_GLOW = "#f0d060"
    C_RUNE_BG = "#12091e"
    C_FLOOR = "#1a1030"
    C_DEEP = "#04020c"
    def mix(fg, bg, a):
        try:
            _f = fg.lstrip("#")
            _b = bg.lstrip("#")
            _fr = int(_f[0:2], 16)
            _fg = int(_f[2:4], 16)
            _fb = int(_f[4:6], 16)
            _br = int(_b[0:2], 16)
            _bg = int(_b[2:4], 16)
            _bb = int(_b[4:6], 16)
            _r = int(_fr * a + _br * (1 - a))
            _g = int(_fg * a + _bg * (1 - a))
            _bb2 = int(_fb * a + _bb * (1 - a))
            return "#%02x%02x%02x" % (_r, _g, _bb2)
        except Exception:
            return fg
    def R(rx, ry, rw, rh, colour):
        canvas.create_rectangle(int(x + rx * u), int(y + ry * u), int(x + (rx + rw) * u), int(y + (ry + rh) * u), fill=colour, outline="")
    if fast:
        R(0, 2, 16, 12.5, C_STONE_MID)
        R(3.5, 4, 9, 10.5, C_TUNNEL)
        if entry_frame > 0 or player_inside:
            R(4.5, 5, 7, 8.5, mix(C_VISOR, C_TUNNEL_FAR, 0.18))
        else:
            R(4.5, 5, 7, 8.5, C_TUNNEL_FAR)
        R(0, 1.8, 16, 0.4, C_GOLD)
        return
    R(0, 14.5, 16, 1.5, C_FLOOR)
    R(0, 14.5, 16, 0.4, C_STONE_HI)
    R(0, 4, 3.5, 11, C_STONE_MID)
    R(0, 4, 3.5, 0.6, C_STONE_HI)
    R(0, 5.8, 3.5, 0.4, C_STONE_HI)
    R(0, 7.6, 3.5, 0.4, C_STONE_HI)
    R(0, 9.4, 3.5, 0.4, C_STONE_HI)
    R(0, 11.2, 3.5, 0.4, C_STONE_HI)
    R(0, 13, 3.5, 0.4, C_STONE_HI)
    R(0, 4, 0.5, 11, C_OUTLINE)
    R(1.2, 4.5, 0.3, 10, mix(C_GOLD, C_STONE_MID, 0.25))
    for _i in range(6):
        R(1.6, 4.5 + _i * 1.7, 0.8, 0.4, mix(C_GOLD, C_STONE_MID, 0.4))
    R(12.5, 4, 3.5, 11, C_STONE_MID)
    R(12.5, 4, 3.5, 0.6, C_STONE_HI)
    R(12.5, 5.8, 3.5, 0.4, C_STONE_HI)
    R(12.5, 7.6, 3.5, 0.4, C_STONE_HI)
    R(12.5, 9.4, 3.5, 0.4, C_STONE_HI)
    R(12.5, 11.2, 3.5, 0.4, C_STONE_HI)
    R(12.5, 13, 3.5, 0.4, C_STONE_HI)
    R(15.5, 4, 0.5, 11, C_OUTLINE)
    R(14.5, 4.5, 0.3, 10, mix(C_GOLD, C_STONE_MID, 0.25))
    for _i in range(6):
        R(13.6, 4.5 + _i * 1.7, 0.8, 0.4, mix(C_GOLD, C_STONE_MID, 0.4))
    R(0, 2, 16, 2.5, C_STONE_MID)
    R(0, 2, 16, 0.5, C_STONE_HI)
    R(0, 2, 0.5, 2.5, C_OUTLINE)
    R(15.5, 2, 0.5, 2.5, C_OUTLINE)
    R(0, 1.8, 16, 0.4, mix(C_GOLD, C_STONE_MID, 0.6))
    R(0, 2, 1, 1, mix(C_GOLD, C_STONE_MID, 0.6))
    R(15, 2, 1, 1, mix(C_GOLD, C_STONE_MID, 0.6))
    canvas.create_rectangle(int(x + 5 * u), int(y + 2.3 * u), int(x + 11 * u), int(y + 4.3 * u), fill=C_RUNE_BG, outline=C_GOLD, width=max(1, int(u * 0.7)))
    R(5.4, 2.6, 5, 0.5, mix(C_GOLD, C_RUNE_BG, 0.7))
    R(5.4, 3.2, 3, 0.5, mix(C_VISOR, C_RUNE_BG, 0.6))
    R(5.4, 3.7, 4, 0.5, mix(C_GOLD, C_RUNE_BG, 0.4))
    R(3.5, 4, 9, 10.5, C_TUNNEL)
    R(4, 4.5, 8, 9.5, C_TUNNEL_MID)
    if player_inside:
        R(4.5, 5, 7, 8.5, mix(C_VISOR, C_TUNNEL_FAR, 0.08))
        R(5, 5.5, 6, 7.5, mix(C_VISOR, C_DEEP, 0.12))
    else:
        R(4.5, 5, 7, 8.5, C_TUNNEL_FAR)
        R(5, 5.5, 6, 7.5, C_DEEP)
    R(3.5, 4, 9, 0.4, mix(C_GOLD, C_TUNNEL, 0.55))
    R(3.5, 4, 0.4, 10.5, mix(C_GOLD, C_TUNNEL, 0.45))
    R(12.6, 4, 0.4, 10.5, mix(C_GOLD, C_TUNNEL, 0.45))
    R(3.5, 14.1, 9, 0.4, mix(C_GOLD, C_TUNNEL, 0.3))
    if size >= 24:
        for (_rrx, _rry, _rrw, _rrh, _ra) in ((4, 4.5, 8, 9, 0.06), (5, 5.5, 6, 7, 0.05), (6, 6.5, 4, 5, 0.04)):
            canvas.create_rectangle(int(x + _rrx * u), int(y + _rry * u), int(x + (_rrx + _rrw) * u), int(y + (_rry + _rrh) * u), fill="", outline=mix(C_GOLD, C_OUTLINE, _ra))
    R(7.5, 9, 1, 2, mix(C_GOLD_DIM, C_DEEP, 0.08))
    R(7.8, 9.5, 0.4, 1, mix(C_GOLD, C_DEEP, 0.12))
    if entry_frame == 1:
        R(4, 4.5, 8, 9, mix(C_VISOR, C_TUNNEL_MID, 0.10))
        R(6.5, 8, 3, 5.5, C_OUTLINE)
        R(7, 8.8, 2, 0.8, C_VISOR)
    elif entry_frame == 2:
        R(4.5, 5, 7, 8, mix(C_VISOR, C_TUNNEL_FAR, 0.18))
        R(6.5, 8, 3, 5.5, mix(C_STONE_MID, C_DEEP, 0.3))
        R(7, 8.8, 2, 0.8, mix(C_VISOR, C_DEEP, 0.6))
    elif entry_frame >= 3:
        R(5, 6, 6, 7, mix(C_VISOR, C_DEEP, 0.22))
        R(6.5, 9.5, 1.2, 0.6, mix(C_VISOR, C_DEEP, 0.8))
        R(8.3, 9.5, 1.2, 0.6, mix(C_VISOR, C_DEEP, 0.8))
        R(6.8, 9.6, 0.6, 0.3, mix(C_GLOW, C_DEEP, 0.6))
        R(8.6, 9.6, 0.6, 0.3, mix(C_GLOW, C_DEEP, 0.6))


def draw_player(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None, dead=False, death_type=None, state="idle"):
    canvas = _tagged(canvas, tags)
    u = size / 16
    C_OUTLINE = "#2a2030"
    C_PLATE_HI = "#e8e8e8"
    C_PLATE_MID = "#a0a0a8"
    C_PLATE_SHD = "#58586a"
    C_GOLD = "#c8a84b"
    C_GOLD_DIM = "#7a5a10"
    C_VISOR = "#1a3a6b"
    C_VISOR_LIT = "#7ab8f5"
    C_VISOR_DIM = "#2a2a4a"
    C_GLOW = "#f0d060"
    C_SWORD_WD = "#8b3a10"
    C_SWORD_GRP = "#c06820"
    C_SWORD_BLD = "#d0d0d8"
    C_DEAD_EYE = "#e05565"
    C_SHADOW = "#060410"
    C_BLOCK = "#1a0f2e"
    def px(rx, ry, rw, rh, colour, tag=None):
        canvas.create_rectangle(int(x + rx * u), int(y + ry * u), int(x + (rx + rw) * u), int(y + (ry + rh) * u), fill=colour, outline="")
    canvas.create_oval(int(x + 2 * u), int(y + 18 * u), int(x + 14 * u), int(y + 19.5 * u), fill=C_SHADOW, outline="")
    if dead and death_type == "void":
        return
    if dead and death_type == "ash":
        _s = max(2, int(size / 8))
        _cx = x + size // 2
        _cy = y + size // 2
        _jit = (0, 1, -1)
        for _j in range(3):
            for _i in range(3):
                _ax = _cx + int((_i - 1) * _s * 1.6) + _jit[(_i + _j) % 3]
                _ay = _cy + int((_j - 1) * _s * 1.6) + _jit[(_i * 2 + _j) % 3]
                _col = "#3a2a1a" if (_i + _j) % 2 == 0 else "#2a1a0a"
                canvas.create_rectangle(_ax, _ay, _ax + _s, _ay + _s, fill=_col, outline="")
        return
    if fast:
        canvas.create_rectangle(int(x + 2 * u), int(y + 2 * u), int(x + 14 * u), int(y + 7 * u), fill=C_PLATE_MID, outline="")
        canvas.create_rectangle(int(x + 2 * u), int(y + 3.5 * u), int(x + 14 * u), int(y + 6 * u), fill=C_VISOR_DIM if dead else C_VISOR, outline="")
        if not dead:
            canvas.create_rectangle(int(x + 3 * u), int(y + 3.9 * u), int(x + 13 * u), int(y + 5.2 * u), fill=C_VISOR_LIT, outline="")
        canvas.create_rectangle(int(x + 2 * u), int(y + 7 * u), int(x + 14 * u), int(y + 15 * u), fill=C_PLATE_SHD, outline="")
        if not dead:
            canvas.create_line(int(x + 15.5 * u), int(y + 14 * u), int(x + 16 * u), int(y + 6 * u), fill=C_SWORD_BLD, width=max(1, size // 16))
        return
    detail = size >= 12
    push = state == "push" and not dead
    sgn = 0
    if state == "walk_l":
        sgn = 1
    elif state == "walk_r":
        sgn = -1
    la_dy = -2 * sgn
    ra_dy = 2 * sgn
    ll_dx = sgn
    rl_dx = -sgn
    sw_dx = sgn
    la_dx = -2 if push else 0
    ra_dx = 2.5 if push else 0
    px(3 + ll_dx, 15.5, 4, 2.5, C_OUTLINE)
    px(3.5 + ll_dx, 15.5, 3, 1.5, C_PLATE_SHD)
    px(3.5 + ll_dx, 15.5, 3, 0.7, C_GOLD)
    px(9 + rl_dx, 15.5, 4, 2.5, C_OUTLINE)
    px(9.5 + rl_dx, 15.5, 3, 1.5, C_PLATE_SHD)
    px(9.5 + rl_dx, 15.5, 3, 0.7, C_GOLD)
    px(3 + ll_dx, 11.5, 4, 4.5, C_PLATE_SHD)
    px(3 + ll_dx, 11.5, 1, 4.5, C_OUTLINE)
    px(3 + ll_dx, 11.5, 4, 0.7, C_GOLD)
    px(9 + rl_dx, 11.5, 4, 4.5, C_PLATE_SHD)
    px(12 + rl_dx, 11.5, 1, 4.5, C_OUTLINE)
    px(9 + rl_dx, 11.5, 4, 0.7, C_GOLD)
    px(2, 7, 12, 5.5, C_OUTLINE)
    px(2.5, 7, 11, 5.5, C_PLATE_MID)
    px(2.5, 7, 11, 1, C_PLATE_HI)
    px(2.5, 7, 1, 5.5, C_OUTLINE)
    px(12.5, 7, 1, 5.5, C_OUTLINE)
    px(2.5, 11.5, 11, 1, C_GOLD)
    if detail:
        if dead:
            _l1 = _l2 = _l3 = C_PLATE_SHD
        elif push:
            _l1 = C_GOLD
            _l2 = C_GLOW
            _l3 = C_GOLD
        else:
            _l1 = C_GOLD
            _l2 = C_VISOR_LIT
            _l3 = C_GOLD
        px(5, 7.8, 6, 3, C_BLOCK)
        px(5.2, 8.2, 5.6, 0.6, _l1)
        px(5.2, 9.2, 3.5, 0.6, _l2)
        px(5.2, 10.1, 4.5, 0.6, _l3)
    px(0.5, 7, 2.5, 2.5, C_PLATE_MID)
    px(0.5, 7, 2.5, 1, C_PLATE_HI)
    px(0.5, 7, 0.5, 2.5, C_OUTLINE)
    px(0.5, 8.8, 2.5, 0.6, C_GOLD)
    px(13, 7, 2.5, 2.5, C_PLATE_MID)
    px(13, 7, 2.5, 1, C_PLATE_HI)
    px(15, 7, 0.5, 2.5, C_OUTLINE)
    px(13, 8.8, 2.5, 0.6, C_GOLD)
    px(0.5 + la_dx, 9 + la_dy, 2.5, 5, C_PLATE_SHD)
    px(0.5 + la_dx, 9 + la_dy, 0.5, 5, C_OUTLINE)
    px(0 + la_dx, 13.5 + la_dy, 3.5, 3, C_OUTLINE)
    px(0.5 + la_dx, 14 + la_dy, 2.5, 2, C_PLATE_SHD)
    px(0.5 + la_dx, 14 + la_dy, 2.5, 0.8, C_GOLD)
    px(13 + ra_dx, 9 + ra_dy, 2.5, 5, C_PLATE_SHD)
    px(15 + ra_dx, 9 + ra_dy, 0.5, 5, C_OUTLINE)
    px(12.5 + ra_dx, 13.5 + ra_dy, 3.5, 3, C_OUTLINE)
    px(13 + ra_dx, 14 + ra_dy, 2.5, 2, C_PLATE_SHD)
    px(13 + ra_dx, 14 + ra_dy, 2.5, 0.8, C_GOLD)
    px(15.5 + sw_dx, 10, 1, 5, C_SWORD_WD)
    if detail:
        px(15.5 + sw_dx, 10.5, 1, 0.8, C_SWORD_GRP)
        px(15.8 + sw_dx, 6, 0.7, 4.5, C_SWORD_BLD)
        px(15.8 + sw_dx, 6, 0.7, 0.8, C_PLATE_HI)
        px(15 + sw_dx, 10, 2, 0.7, C_PLATE_SHD)
    px(3, 0.5, 10, 1.5, C_OUTLINE)
    px(2, 2, 12, 5, C_PLATE_MID)
    px(2, 2, 12, 1.5, C_PLATE_HI)
    px(2, 2, 1, 5, C_OUTLINE)
    px(13, 2, 1, 5, C_OUTLINE)
    px(2, 6.5, 12, 0.7, C_GOLD)
    px(2, 3.5, 12, 2.5, C_OUTLINE)
    px(2.5, 3.7, 11, 2, C_VISOR_DIM if dead else C_VISOR)
    if not dead:
        px(3, 3.9, 10, 1.3, C_VISOR_LIT)
        if push:
            px(3, 4, 10, 1, C_GLOW)
        else:
            px(5, 4, 6, 1, C_GLOW)
    else:
        px(3.5, 4, 1, 1, C_DEAD_EYE)
        px(11.5, 4, 1, 1, C_DEAD_EYE)
    if dead:
        px(7.5, 0, 1, 2, C_GOLD_DIM)
        px(7.5, 0, 1, 0.8, C_GOLD_DIM)
    else:
        px(7.5, 0, 1, 2, C_GOLD)
        px(7.5, 0, 1, 0.8, C_GLOW)
    if push:
        canvas.create_rectangle(int(x + -5 * u), int(y + 9 * u), int(x + -1 * u), int(y + 13 * u), fill=C_BLOCK, outline=C_GOLD, width=1.2)
        px(-4.5, 9.8, 3, 0.6, C_GOLD)
        px(-4.5, 10.8, 2, 0.6, C_VISOR_LIT)


def draw_boom_explosion(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
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


    fragment = max(2, size // 11)
    for dx, dy, col in ((-0.34, -0.31, KNIGHT_MID),
                        (0.31, -0.25, KNIGHT_OUTLINE),
                        (-0.38, 0.29, KNIGHT_OUTLINE),
                        (0.35, 0.33, KNIGHT_MID)):
        fx, fy = cx + int(size * dx), cy + int(size * dy)
        canvas.create_polygon(fx, fy - fragment,
                              fx + fragment, fy,
                              fx, fy + fragment,
                              fx - fragment, fy,
                              fill=col, outline=FRAGMENT_OUTLINE)


def draw_platform_solid(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=PLATFORM_SOLID, outline=PLATFORM_PILLAR, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    _bevel(canvas, x, y, size, FLOOR_SHADOW, FLOOR_HI,
           depth=max(1, size // 14))
    m = max(1, size // 8)

    deck_y1 = y + size // 4
    deck_y2 = y + size // 2 + m
    canvas.create_rectangle(x + 1, deck_y1, x + size - 1, deck_y2,
                            fill=PLATFORM_SOLID, outline=PLATFORM_PILLAR, width=1)

    pw = max(3, size // 6)

    canvas.create_rectangle(x + m + 2, deck_y2, x + m + 2 + pw, y + size - m,
                            fill=PLATFORM_PILLAR, outline="#4a2fb0", width=1)

    canvas.create_rectangle(x + size - m - 2 - pw, deck_y2,
                            x + size - m - 2, y + size - m,
                            fill=PLATFORM_PILLAR, outline="#4a2fb0", width=1)

    canvas.create_line(x + 2, deck_y1 + 1, x + size - 2, deck_y1 + 1,
                       fill="#a080ff", width=max(1, size // 24))

    dh = max(2, size // 12)
    canvas.create_rectangle(x + 1, deck_y2, x + size - 1, deck_y2 + dh,
                            fill=PLATFORM_PILLAR, outline="")


def draw_platform_ghost(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill="", outline=PLATFORM_GHOST_DASH, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill="#1b1f3f", outline="#242850", width=1)
    m = max(1, size // 8)
    deck_y1 = y + size // 4
    deck_y2 = y + size // 2 + m

    canvas.create_rectangle(x + 1, deck_y1, x + size - 1, deck_y2,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=max(1, size // 20), dash=(4, 3))

    pw = max(3, size // 6)
    canvas.create_rectangle(x + m + 2, deck_y2, x + m + 2 + pw, y + size - m,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=1, dash=(3, 3))
    canvas.create_rectangle(x + size - m - 2 - pw, deck_y2,
                            x + size - m - 2, y + size - m,
                            fill="", outline=PLATFORM_GHOST_DASH,
                            width=1, dash=(3, 3))


def draw_void(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)

    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=VOID_BG, outline=VOID_RIM, width=1)
        cx, cy = x + size // 2, y + size // 2
        cc = max(1, size // 10)
        canvas.create_oval(cx - cc, cy - cc, cx + cc, cy + cc,
                           fill=VOID_CORE, outline="")
        return

    # 1. Tile base — very dark navy fill, gold border
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=VOID_BG, outline=VOID_RIM,
                            width=max(1, size // 20))

    # 2. Sunken bevel — black top-left, gold bottom-right
    #    Inverted vs a normal bevel so the tile reads as a recessed pit
    _bevel(canvas, x, y, size, "#000000", VOID_GLOW,
           depth=max(2, size // 6))

    cx, cy = x + size // 2, y + size // 2
    m     = max(2, size // 8)
    outer = max(3, size // 2 - m)

    # 3. Four concentric filled ovals — dark rings simulating depth
    #    No outlines, no dashes — solid bands only
    for frac, col in (
        (0.92, "#1a0f2e"),
        (0.70, "#130b22"),
        (0.50, "#0d0718"),
        (0.32, "#08040e"),
    ):
        r = max(1, int(outer * frac))
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           fill=col, outline="")

    # 4. Indigo shimmer — purple-blue oval with WARP_INDIGO outline ring
    #    This is the "bottomless pit glow" seen in the design
    if size >= 16:
        sc = max(2, size // 7)
        canvas.create_oval(cx - sc, cy - sc, cx + sc, cy + sc,
                           fill="#2a1a4a", outline=WARP_INDIGO,
                           width=max(1, size // 28))

    # 5. Black pit centre
    cc = max(1, size // 10)
    canvas.create_oval(cx - cc, cy - cc, cx + cc, cy + cc,
                       fill=VOID_CORE, outline="")

    # 6. Ember dot — tiny crimson point at absolute centre
    if size >= 20:
        e = max(1, cc // 2)
        canvas.create_oval(cx - e, cy - e, cx + e, cy + e,
                           fill=VOID_EMBER, outline="")

def draw_door_closed(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)


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

    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=DOOR_CLOSED, outline=DOOR_FRAME, width=max(1, size // 16))

    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill=DOOR_FRAME, outline=DOOR_FRAME)

    cx, cy = x + size // 2, y + size // 2
    kr = max(2, size // 10)
    canvas.create_oval(cx - kr, cy - kr, cx + kr, cy + kr,
                       fill=DOOR_KEYHOLE, outline="#333")

    canvas.create_rectangle(cx - max(1, kr // 2), cy, cx + max(1, kr // 2), cy + kr * 2,
                            fill=DOOR_KEYHOLE, outline=DOOR_KEYHOLE)

    hx = x + size - m - max(3, size // 6)
    hy = cy
    hr = max(2, size // 14)
    canvas.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                       fill="#ffd080", outline="#cc9040")

    _bevel(canvas, x + m, y + m, size - 2 * m, DOOR_HI, DOOR_SHADOW,
           depth=max(1, size // 14))


def draw_door_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
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

    canvas.create_rectangle(x + m, y + m, x + m + half // 2, y + size - m,
                            fill=DOOR_OPEN_CLR, outline="#c89040", width=1)

    canvas.create_rectangle(x + size - m - half // 2, y + m,
                            x + size - m, y + size - m,
                            fill=DOOR_OPEN_CLR, outline="#c89040", width=1)

    canvas.create_rectangle(x + m + half // 2, y + m,
                            x + size - m - half // 2, y + size - m,
                            fill="#2a3a2a", outline="#3a5a3a", width=1)

    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill="#c89040", outline="#a07030")



LATCH_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "latch.webp")
_latch_src = None
_latch_photos: dict[int, object] = {}


def _load_latch_src():
    global _latch_src
    if _latch_src is not None:
        return _latch_src or None
    _latch_src = _white_keyed_src(LATCH_IMAGE) or False
    return _latch_src or None


def _latch_photo(size: int):
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






LATCH_BASE   = "#c44a8c"
LATCH_FRAME  = "#7a2a58"
LATCH_HI     = "#f2a4cc"
LATCH_SHADOW = "#4a1030"
LATCH_OPEN_CLR = "#e89ac0"
LATCH_OPEN_GAP = "#3a1a2e"


def draw_latch_closed(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)

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

    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=LATCH_BASE, outline=LATCH_FRAME,
                            width=max(1, size // 16))

    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill=LATCH_FRAME, outline=LATCH_FRAME)

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


def draw_latch_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
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

    canvas.create_rectangle(x + m, y + m, x + m + half // 2, y + size - m,
                            fill=LATCH_OPEN_CLR, outline="#a05880", width=1)

    canvas.create_rectangle(x + size - m - half // 2, y + m,
                            x + size - m, y + size - m,
                            fill=LATCH_OPEN_CLR, outline="#a05880", width=1)

    canvas.create_rectangle(x + m + half // 2, y + m,
                            x + size - m - half // 2, y + size - m,
                            fill=LATCH_OPEN_GAP, outline="#6a2a48", width=1)

    canvas.create_rectangle(x + m - 1, y + m - 1, x + size - m + 1, y + m + max(2, size // 10),
                            fill="#a05880", outline="#7a2a58")


def draw_trap_lethal(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)

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
    m = max(2, size // 6)

    cx, cy = x + size // 2, y + size // 2
    half = size // 2 - m
    canvas.create_polygon(cx, cy - half,
                          cx + half, cy,
                          cx, cy + half,
                          cx - half, cy,
                          fill=TRAP_RED, outline="#e05565", width=max(1, size // 20))

    spikes = max(3, size // 12)
    sw = (size - 2 * m) // spikes
    for i in range(spikes):
        sx = x + m + i * sw
        canvas.create_polygon(sx, y + m + size // 5,
                              sx + sw // 2, y + m,
                              sx + sw, y + m + size // 5,
                              fill=TRAP_SPIKE, outline=TRAP_RED)

    canvas.create_text(cx, cy, text="!", fill="white",
                       font=("Arial", max(8, size // 4), "bold"), anchor="center")


def draw_trap_safe(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)


def draw_code_block(canvas: tk.Canvas, x: int, y: int, size: int,
                    label: str, kind: str, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    kind_colors = {
        "CLASS":  ("#1a4a7a", "#52b0ff"),
        "PROP":   ("#1a5a4a", "#40d8a0"),
        "OP":     ("#4a3a1a", "#d0a840"),
        "VALUE":  ("#3a1a5a", "#b070e0"),
        "NOT":    ("#5a1a3a", "#ff5f8f"),
    }
    bg, border = kind_colors.get(kind, (BLOCK_BG, BLOCK_BORDER))
    if fast:

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

    sx, sy = max(1, size // 16), max(2, size // 10)
    x1s, y1s, x2s, y2s = x + m + sx, y + m + sy, x + size - m + sx, y + size - m + sy
    _rounded_rect(canvas, x1s, y1s, x2s, y2s, r, fill=CODE_SHADOW, outline="")
    x1, y1, x2, y2 = x + m, y + m, x + size - m, y + size - m
    _rounded_rect(canvas, x1, y1, x2, y2, r, fill=bg, outline=border,
                  width=max(1, size // 20))

    canvas.create_line(x1 + r, y1 + 2, x2 - r, y1 + 2,
                       fill=border, width=1)

    cx = x + size // 2
    cy = y + size // 2
    font_size = max(7, min(size // 5, 14))
    canvas.create_text(cx, cy, text=label, fill=BLOCK_TEXT,
                       font=("Consolas", font_size, "bold"), anchor="center")


def draw_circuit_slot(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)
    if fast:
        return
    m = max(2, size // 8)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill=CIRCUIT_SLOT_BG, outline=CIRCUIT_SLOT_BORDER,
                            width=max(1, size // 16), dash=(5, 3))

    cx, cy = x + size // 2, y + size // 2
    dr = max(1, size // 16)
    canvas.create_oval(cx - dr, cy - dr, cx + dr, cy + dr,
                       fill=CIRCUIT_SLOT_BORDER, outline=CIRCUIT_SLOT_BORDER)


def draw_stone(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)

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

    canvas.create_line(x + 1, y + 1, x + size - 1, y + 1,
                       fill=STONE_TOP, width=max(1, size // 16))
    _bevel(canvas, x, y, size, STONE_FACE_HI, STONE_SIDE)


def draw_stone_open(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)
    if fast:
        return
    m = max(2, size // 6)
    w = max(1, size // 20)
    canvas.create_rectangle(x + m, y + m, x + size - m, y + size - m,
                            fill="", outline=STONE_BASE,
                            width=w, dash=(4, 3))

    canvas.create_line(x + m, y + m, x + size - m, y + size - m,
                       fill=STONE_BASE, width=max(1, size // 24), dash=(4, 3))
    canvas.create_line(x + m, y + size - m, x + size - m, y + m,
                       fill=STONE_BASE, width=max(1, size // 24), dash=(4, 3))


def draw_seal_wall(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, col: int = 1, tags=None):
    canvas = _tagged(canvas, tags)
    photo = _sheet_photo("walls_floor.png", int(col), 2, size)
    if photo is not None:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=SEAL_PURPLE, width=1)
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        if size >= 28:
            canvas.create_text(x + size // 2, y + size // 2, text="🔒",
                               font=("Arial", max(8, size // 3)),
                               anchor="center")
        return
    if fast:
        canvas.create_rectangle(x, y, x + size, y + size,
                                fill=WALL_BASE, outline=SEAL_PURPLE, width=1)
        return
    canvas.create_rectangle(x, y, x + size, y + size,
                            fill=WALL_BASE, outline=WALL_MORTAR, width=1)

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


def draw_warp(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)

    photo = None
    try:
        photo = _portal_photo(size)
    except Exception:
        photo = None
    if photo is not None:
        canvas.create_image(x + size // 2, y + size // 2,
                            image=photo, anchor="center")
        return
    # PIL-unavailable fallback.
    # Design: rounded stone arch silhouette + layered teal vortex ovals
    # + keystone triangle at crown + glow spill below the arch mouth.
    # Colors from the design sheet image — teal portal, gold trim, dark arch.
    u = size / 16.0
    def R(rx, ry, rw, rh, col):
        canvas.create_rectangle(
            int(x + rx * u), int(y + ry * u),
            int(x + (rx + rw) * u), int(y + (ry + rh) * u),
            fill=col, outline="")
    # ── fast path ────────────────────────────────────────────────────
    if fast:
        R(0,  2, 16, 14, "#1c1630")          # arch body
        R(0,  1.8, 16, 0.35, "#c8a84b")      # gold cap line
        cx_f = x + size // 2
        cy_f = y + int(size * 0.60)
        rw_f = max(2, int(size * 0.22))
        rh_f = max(2, int(size * 0.30))
        canvas.create_oval(cx_f - rw_f, cy_f - rh_f,
                           cx_f + rw_f, cy_f + rh_f,
                           fill="#0c3a4c", outline="#1a7888",
                           width=max(1, size // 20))
        return
    # ── 1. arch body — dark stone colour from the design ─────────────
    # The arch is a single dark rounded rectangle covering top 7/8 of tile
    arch_x1 = int(x + 1 * u)
    arch_y1 = int(y + 1 * u)
    arch_x2 = int(x + 15 * u)
    arch_y2 = int(y + 15 * u)
    arch_r  = max(4, int(5 * u))   # large radius = rounded arch top
    _rounded_rect(canvas, arch_x1, arch_y1, arch_x2, arch_y2,
                  arch_r, fill="#1c1630", outline="#0d0a1a",
                  width=max(1, size // 24))
    # ── 2. arch highlight — lighter top edge course ───────────────────
    R(0.5, 1.0, 15, 0.5, "#2a2040")
    # ── 3. gold cap line across the very top ──────────────────────────
    R(0, 1.6, 16, 0.35, "#c8a84b")
    # ── 4. horizontal mortar lines on arch body ───────────────────────
    for i in range(5):
        R(1.0, 3.5 + i * 2.0, 14, 0.22, "#0d0a1a")
    # ── 5. thin gold inner-edge strips on left and right ─────────────
    R(2.5, 2.5, 0.3, 12, "#c8a84b")    # left inner gold strip
    R(13.2, 2.5, 0.3, 12, "#c8a84b")   # right inner gold strip
    # ── 6. keystone triangle at the crown ────────────────────────────
    # Small teal triangle at top-centre, gold outline
    canvas.create_polygon(
        int(x + 7.5 * u), int(y + 1.6 * u),
        int(x + 8.0 * u), int(y + 2.6 * u),
        int(x + 8.5 * u), int(y + 1.6 * u),
        fill="#1a7888", outline="#c8a84b",
        width=max(1, int(u * 0.5)))
    # ── 7. portal interior — layered teal vortex ovals ───────────────
    # Centred inside the arch opening, each ring slightly smaller + brighter
    # Colors match the teal vortex in the design sheet exactly
    cx = x + size // 2
    cy = y + int(size * 0.60)          # centre of arch opening
    for frac, col in (
        (0.90, "#061820"),
        (0.70, "#082838"),
        (0.50, "#0c3a4c"),
        (0.32, "#1a6070"),
        (0.16, "#2a9aaa"),
    ):
        rw = max(1, int(size * 0.30 * frac))
        rh = max(1, int(size * 0.40 * frac))
        canvas.create_oval(cx - rw, cy - rh, cx + rw, cy + rh,
                           fill=col, outline="")
    # ── 8. teal glow rim outline around the portal mouth ─────────────
    rw0 = max(2, int(size * 0.30))
    rh0 = max(2, int(size * 0.40))
    canvas.create_oval(cx - rw0, cy - rh0, cx + rw0, cy + rh0,
                       fill="", outline="#1a7888",
                       width=max(1, size // 20))
    # ── 9. glow spill — faint oval below arch mouth ───────────────────
    if size >= 20:
        spill_h = max(1, size // 9)
        canvas.create_oval(cx - rw0, cy + rh0,
                           cx + rw0, cy + rh0 + spill_h,
                           fill="#061820", outline="")

def draw_mine(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)

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












BACKGROUND_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "assets", "background.jpeg")
BACKGROUND_GENERATED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "assets", "background_generated.png")
BG_TILE_DARKEN = 0.40
BG_TEXTURE_PX = 16 * 48
_background_path = None
_bg_src = None
_bg_tiled = False


def ensure_background_image():
    global _background_path
    if _background_path is not None:
        return _background_path or None
    if os.path.isfile(BACKGROUND_GENERATED):
        _background_path = BACKGROUND_GENERATED
        return _background_path
    if not _PIL_AVAILABLE:
        _background_path = False
        return None
    try:
        tile = DungeonSheet.frame_image("walls_floor.png", FLOOR_SHEET_COL, FLOOR_SHEET_ROW)
        if tile is None:
            tile = DungeonSheet.frame_image("walls_floor.png", 0, 0)
        if tile is None:
            raise OSError("dungeon floor tile unavailable")
        tile = tile.convert("RGB")
        side = int(BG_TEXTURE_PX)
        tex = _PILImage.new("RGB", (side, side))
        for _y in range(0, side, tile.height):
            for _x in range(0, side, tile.width):
                tex.paste(tile, (_x, _y))
        tex = tex.point(lambda v: int(v * BG_TILE_DARKEN))
        tex.save(BACKGROUND_GENERATED, "PNG")
        _background_path = BACKGROUND_GENERATED
    except Exception:
        _background_path = (BACKGROUND_IMAGE
                            if os.path.isfile(BACKGROUND_IMAGE) else False)
    return _background_path or None


def _tile_to(img, size):
    w, h = int(size[0]), int(size[1])
    tw, th = img.size
    if tw >= w and th >= h:
        return img.crop((0, 0, w, h))
    out = _PILImage.new("RGB", (w, h))
    for _y in range(0, h, th):
        for _x in range(0, w, tw):
            out.paste(img, (_x, _y))
    return out


def get_canvas_photo(win_w: int, win_h: int, cw: int, ch: int):
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






_panel_base: dict[tuple[int, int], object] = {}
_panel_photos: dict[tuple, object] = {}
PANEL_DARKEN = 0.45


def _panel_base_image(win_w: int, win_h: int):
    key = (int(win_w), int(win_h))
    if key in _panel_base:
        return _panel_base[key]
    if not _PIL_AVAILABLE:
        return None
    global _bg_src, _bg_tiled
    if _bg_src is None:

        path = ensure_background_image()
        if path is None:
            _bg_src = False
            return None
        try:
            _bg_src = _PILImage.open(path).convert("RGB")
        except (OSError, FileNotFoundError):
            _bg_src = False
            return None
        _bg_tiled = (path == BACKGROUND_GENERATED)
    if _bg_src is False:
        return None



    img = _tile_to(_bg_src, key) if _bg_tiled else _bg_src.resize(key, _PILImage.BILINEAR)
    if len(_panel_base) >= 3:
        _panel_base.pop(next(iter(_panel_base)))
    _panel_base[key] = img
    return img


def _darken(img, factor: float = PANEL_DARKEN):
    return img.point(lambda v: int(v * factor))


def get_panel_photo(win_w: int, win_h: int, panel_w: int):
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



PORTAL_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "portal.jpeg")
_portal_src = None
_portal_photos: dict[int, object] = {}


def _load_portal_src():
    # Disabled: portal.jpeg is too dark and renders transparent.
    # Fallback programmatic drawing in draw_warp() is used instead.
    global _portal_src
    _portal_src = False
    return None


def _portal_photo(size: int):
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



BOOM_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "boom.jpeg")
_boom_src = None
_boom_photos: dict[int, object] = {}


def _load_boom_src():
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

    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _boom_src = img
    return img


def _boom_photo(size: int):
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



LASER_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "laser.png")
_laser_src = None
_laser_photos: dict[int, object] = {}


def _load_laser_src():
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
               active: bool = True, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)
    if not active:
        return

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



ASH_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "ash.jpeg")
_ash_src = None
_ash_photos: dict[int, object] = {}


def _load_ash_src():
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

    alpha = gray.point(
        lambda v: 0 if v >= 245 else (255 if v <= 190 else int((245 - v) * 255 / 55)))
    img = img.convert("RGBA")
    img.putalpha(alpha)
    _ash_src = img
    return img


def _ash_photo(size: int):
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


def draw_ash(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)

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



STONE_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "stone.jpeg")
_stone_src = None
_stone_photos: dict[int, object] = {}


def _load_stone_src():
    global _stone_src
    if _stone_src is not None:
        return _stone_src or None
    _stone_src = _white_keyed_src(STONE_IMAGE) or False
    return _stone_src or None


def _stone_photo(size: int):
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



DOOR_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "door.jpeg")
_door_src = None
_door_photos: dict[int, object] = {}


def _load_door_src():
    global _door_src
    if _door_src is not None:
        return _door_src or None
    _door_src = _white_keyed_src(DOOR_IMAGE) or False
    return _door_src or None


def _door_photo(size: int):
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



TRAP_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "assets", "trap.gif")
_trap_src = None
_trap_photos: dict[int, object] = {}
_trap_tk_photos: dict[int, object] = {}


def _load_trap_src():
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





TRAP_SHEET = "trap_animation.png"
TRAP_FRAME_PX = 48

_trap_anim_frames: list = []
_trap_anim_index: int = 0
_trap_anim_tick: int = 0
_trap_anim_src: list = []
_trap_anim_ready = False
_trap_scaled: dict[tuple, object] = {}


def _ensure_trap_anim() -> bool:
    global _trap_anim_ready, _trap_anim_src
    if not _trap_anim_ready:
        _trap_anim_ready = True
        if _PIL_AVAILABLE:
            try:
                sheet = _PILImage.open(
                    DungeonSheet.path_of(TRAP_SHEET)).convert("RGBA")
                fw = fh = int(TRAP_FRAME_PX)
                cols = max(0, sheet.width // fw)
                rows = max(0, sheet.height // fh)
                _trap_anim_src = [
                    sheet.crop((c * fw, r * fh, c * fw + fw, r * fh + fh))
                    for r in range(rows) for c in range(cols)
                ]
            except Exception:
                _trap_anim_src = []
    if not _trap_anim_src:
        return False
    if not _trap_anim_frames and tk._default_root is not None:
        for frame in _trap_anim_src:
            try:
                _trap_anim_frames.append(_PILImageTk.PhotoImage(frame))
            except Exception:
                break
    return True


def advance_trap_animation(tick_interval: int = 4) -> int:
    global _trap_anim_index, _trap_anim_tick
    if not _ensure_trap_anim():
        return _trap_anim_index
    try:
        interval = max(1, int(tick_interval))
    except (TypeError, ValueError):
        interval = 4
    _trap_anim_tick += 1
    if _trap_anim_tick >= interval:
        _trap_anim_tick = 0
        _trap_anim_index = (_trap_anim_index + 1) % len(_trap_anim_src)
    return _trap_anim_index


def _trap_photo(size: int):
    _check_photo_root()
    if tk._default_root is None:
        return None
    if not _ensure_trap_anim():
        return _trap_photo_legacy(size)
    if not 0 <= _trap_anim_index < len(_trap_anim_src):
        return _trap_photo_legacy(size)
    key = (_trap_anim_index, _quant_size(size))
    if key in _trap_scaled:
        return _trap_scaled[key]

    if key[1] == TRAP_FRAME_PX and _trap_anim_index < len(_trap_anim_frames):
        return _trap_anim_frames[_trap_anim_index]
    try:
        side = max(8, int(key[1]))
        out = _trap_anim_src[_trap_anim_index].copy()
        if out.size != (side, side):


            out = out.resize((side, side), _PILImage.NEAREST)
        photo = _PILImageTk.PhotoImage(out)
    except Exception:
        return _trap_photo_legacy(size)
    if len(_trap_scaled) >= 200:
        _trap_scaled.pop(next(iter(_trap_scaled)))
    _trap_scaled[key] = photo
    return photo


def _trap_photo_legacy(size: int):
    _check_photo_root()
    if tk._default_root is None:
        return None
    key = _quant_size(size)
    if key in _trap_photos:
        return _trap_photos[key]
    src = _load_trap_src()
    if src is None:

        return _trap_photo_tk(size)
    side = max(8, int(key))
    fit = src.copy()
    fit.thumbnail((side, side), _PILImage.BILINEAR)
    photo = _PILImageTk.PhotoImage(fit)
    _trap_photos[key] = photo
    return photo



SKELETON_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "assets", "skeleton.png")
_skel_src = None
_skel_photos: dict[int, object] = {}


def _load_skel_src():
    global _skel_src
    if _skel_src is not None:
        return _skel_src or None
    _skel_src = _white_keyed_src(SKELETON_IMAGE) or False
    return _skel_src or None


def _skel_photo(size: int):
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



LEVER_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "assets", "lever.png")
_lever_src = None
_lever_photos: dict[tuple, object] = {}


def _load_lever_src():
    global _lever_src
    if _lever_src is not None:
        return _lever_src or None
    _lever_src = _white_keyed_src(LEVER_IMAGE) or False
    return _lever_src or None


def _lever_photo(size: int, active: bool = False):
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
               active: bool = False, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
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

    cx = x + size // 2
    base_y0 = y + int(size * 0.62)
    base_y1 = y + size - max(2, size // 10)
    m = max(2, size // 6)
    canvas.create_rectangle(x + m, base_y0, x + size - m, base_y1,
                            fill="#5a5e78", outline="#0a0a0a",
                            width=max(1, size // 20))
    canvas.create_rectangle(x + m, base_y0, x + size - m, base_y0 + max(2, size // 12),
                            fill="#9aa0bd", outline="")

    rod_w = max(2, size // 12)
    if not active:

        canvas.create_rectangle(cx - rod_w // 2, y + max(2, size // 8),
                                cx + rod_w // 2 + 1, base_y0,
                                fill="#c0c0c0", outline="#0a0a0a")
        hw, hh = max(4, size // 4), max(6, size // 3)
        canvas.create_rectangle(cx - hw // 2, y + max(1, size // 12),
                                cx + hw // 2, y + max(1, size // 12) + hh,
                                fill="#d96b1a", outline="#0a0a0a",
                                width=max(1, size // 24))
    else:

        canvas.create_line(cx, base_y0 - max(1, size // 8),
                           cx + int(size * 0.28), base_y0,
                           fill="#c0c0c0", width=rod_w)
        hr = max(3, size // 6)
        hx, hy = cx + int(size * 0.28), base_y0 - max(1, size // 12)
        canvas.create_oval(hx - hr, hy - hr, hx + hr, hy + hr,
                           fill="#d96b1a", outline="#0a0a0a",
                           width=max(1, size // 24))


def draw_skeleton(canvas: tk.Canvas, x: int, y: int, size: int, fast: bool = False, tags=None):
    canvas = _tagged(canvas, tags)
    draw_floor(canvas, x, y, size, fast=fast)

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
