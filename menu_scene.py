"""menu_scene.py — animated main-menu scene for "Type Is Code".

Replaces the old widget-based home screen with a multi-layered,
dt-driven animated environment inspired by the cover art:

    Background corridor -> floor & props -> portals & consoles
    -> bombs & chests -> knight -> title -> text menu -> overlays

Structure:
    Scene          -- reusable base (update / draw / input hooks)
    SceneManager   -- owns the Tk window + fixed-step-ish loop w/ dt
    MainMenuScene  -- the cover-art scene (knight, rifts, bombs, ...)
    run_animated_menu(...) -- entry point used by multiplayer.menus

All motion is scaled by delta time so animation speed is independent
of frame rate.  Pure helpers (layout, particles, fuses, consoles) are
headless-safe and covered by tests/test_menu_scene.py.

On-screen labels match the cover art
(NEW GAME / LOAD GAME / SETTINGS / EXIT).  There is no save system
yet, so LOAD GAME shows a toast until saves/*.json exists (an on_load
callback seam is ready for it).  MULTIPLAYER is one keypress away
(M, handled in MainMenuScene.on_key) so the LAN race flow stays
reachable -- run_animated_menu takes on_multiplayer for it.
"""

from __future__ import annotations

import math
import os
import time

# Photo sprites reused from the in-game renderer (each degrades to
# procedural art when Pillow / the asset is missing -- same contract
# as tile_renderer).
from tile_renderer import _boom_photo, _player_photo, _portal_photo

MENU_ITEMS = ("NEW GAME", "LOAD GAME", "SETTINGS", "EXIT")
TITLE_TEXT = "TYPE IS CODE"  # the upper bold text is always this

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "settings.json")
DEFAULT_SETTINGS = {"particles": True, "fullscreen": False}

# Consoles periodically cycle through these (text, colour) programs.
CONSOLE_PROGRAMS = (
    ((("[ LEVER : ACTIVE + ]", "#7dff8a"), ("[ SET : FALSE ]", "#8fb8ff"))),
    ((("[ GATE : XOR ]", "#ffcf5a"), ("[ OUT : TRUE ]", "#7dff8a"))),
    ((("[ GATE : AND ]", "#ffcf5a"), ("[ OUT : FALSE ]", "#ff7d6a"))),
    ((("[ GATE : OR ]", "#ffcf5a"), ("[ FLOW : 1011 ]", "#5fc9ff"))),
)
CONSOLE_CYCLE_S = 2.2  # seconds per program

# Bomb fuse burn-down (seconds of fuse, then a relight flash).
FUSE_START = 1.0
FUSE_MIN = 0.18
FUSE_BURN_S = 12.0
FUSE_FLASH_S = 0.3

TARGET_FPS = 30
TICK_MS = int(1000 / TARGET_FPS)
MAX_DT = 0.05  # clamp tab-out jumps so particles don't teleport


# ── headless-safe pure logic ──────────────────────────────────────────

def clamp_dt(dt: float) -> float:
    """Clamp raw frame delta into a sane simulation step."""
    return max(0.0, min(MAX_DT, dt))


def menu_layout(w: int, h: int) -> dict:
    """Pixel rects for every scene element, as fractions of (w, h).

    Everything scales with the window: resize the window and the whole
    composition (title at ~10% height, centred knight, wall props)
    keeps its relative placement.
    """
    w, h = max(320, w), max(240, h)
    vpx, vpy = 0.5 * w, 0.54 * h  # vanishing point
    return {
        "w": w, "h": h,
        "vp": (vpx, vpy),
        # back wall (the far end of the corridor)
        "back": (0.34 * w, 0.30 * h, 0.66 * w, 0.74 * h),
        # title centre + menu row (menu sits right under the title)
        "title": (0.5 * w, 0.125 * h),
        "menu_y": 0.29 * h,
        # wall portals (left big, right cropped by the edge)
        "portal_l": (0.155 * w, 0.53 * h, 0.075 * h),
        "portal_r": (0.965 * w, 0.50 * h, 0.085 * h),
        "portal_far": (0.615 * w, 0.56 * h, 0.028 * h),
        # consoles on the walls
        "console_l": (0.015 * w, 0.40 * h, 0.155 * w, 0.20 * h),
        "console_m": (0.295 * w, 0.49 * h, 0.075 * w, 0.115 * h),
        "console_r": (0.855 * w, 0.53 * h, 0.030 * w, 0.09 * h),
        # floor props: bombs (x, feet-y, body radius scale)
        "bomb_big": (0.085 * w, 0.92 * h, 1.2),
        "bomb_mid": (0.735 * w, 0.79 * h, 0.80),
        "bomb_a": (0.665 * w, 0.655 * h, 0.45),
        "bomb_b": (0.795 * w, 0.655 * h, 0.42),
        "barrel": (0.355 * w, 0.70 * h, 0.075 * h),
        "chest_a": (0.615 * w, 0.685 * h, 0.62),
        "chest_b": (0.855 * w, 0.75 * h, 0.80),
        "chest_big": (0.985 * w, 0.93 * h, 1.5),
        # the knight: centre stage, feet planted in the dust
        "knight": (0.5 * w, 0.88 * h, 0.42 * h),
    }


def bezier(p0, p1, p2, t: float) -> tuple[float, float]:
    """Point on a quadratic bezier curve (fuse arcs, wires)."""
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def walk_polyline(points, dist: float) -> tuple[float, float]:
    """Position `dist` px along a polyline (data-flow dots on wires)."""
    if not points:
        return (0.0, 0.0)
    if len(points) == 1 or dist <= 0:
        return points[0]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if dist <= seg:
            f = dist / seg if seg else 0.0
            return (x1 + (x2 - x1) * f, y1 + (y2 - y1) * f)
        dist -= seg
    return points[-1]


def polyline_length(points) -> float:
    """Total length of a polyline."""
    return sum(math.hypot(x2 - x1, y2 - y1)
               for (x1, y1), (x2, y2) in zip(points, points[1:]))


def fuse_length(fuse_t: float) -> float:
    """Visible fuse fraction: subtly shortens, then the relight resets it."""
    cycle = FUSE_BURN_S + FUSE_FLASH_S
    t = fuse_t % cycle
    if t >= FUSE_BURN_S:
        return FUSE_MIN  # flashing: about to relight
    return FUSE_START - (FUSE_START - FUSE_MIN) * (t / FUSE_BURN_S)


def fuse_flashing(fuse_t: float) -> bool:
    """True during the brief relight pop at the end of a burn cycle."""
    return (fuse_t % (FUSE_BURN_S + FUSE_FLASH_S)) >= FUSE_BURN_S


def console_program(t: float) -> int:
    """Which console program is on screen at time t."""
    return int(t // CONSOLE_CYCLE_S) % len(CONSOLE_PROGRAMS)


def console_flicker(t: float, line: int) -> bool:
    """Occasional per-line dropout so screens feel electric, not painted."""
    tick = int(t * 9)
    h = (tick * 2654435761 + line * 40503) & 0xFFFF
    return (h % 23) != 0


def portal_pulse(t: float, seed: float = 0.0) -> float:
    """0..1 breathing pulse driving rift glow + cast light."""
    return 0.5 + 0.5 * math.sin(t * 2.1 + seed)


def make_particle(x, y, vx, vy, life, size, col, grav=0.0) -> dict:
    """One spark / mote / dust puff."""
    return {"x": x, "y": y, "vx": vx, "vy": vy,
            "life": life, "max": life, "size": size,
            "col": col, "grav": grav}


def advance_particles(parts: list, dt: float) -> list:
    """Integrate + age a particle list; drop the dead. Pure & testable."""
    out = []
    for p in parts:
        life = p["life"] - dt
        if life <= 0:
            continue
        q = dict(p)
        q["life"] = life
        q["vy"] += q.get("grav", 0.0) * dt
        q["x"] += q["vx"] * dt
        q["y"] += q["vy"] * dt
        out.append(q)
    return out


def load_settings() -> dict:
    """Read settings.json; defaults when missing/corrupt (never raises)."""
    try:
        import json as _json
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            data = _json.load(fh)
        if isinstance(data, dict):
            return {**DEFAULT_SETTINGS,
                    **{k: data[k] for k in DEFAULT_SETTINGS if k in data}}
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    """Persist settings.json (never raises -- menu must not crash)."""
    try:
        import json as _json
        with open(SETTINGS_PATH, "w", encoding="utf-8") as fh:
            _json.dump({k: settings.get(k, v)
                        for k, v in DEFAULT_SETTINGS.items()}, fh)
    except Exception:
        pass


# ── scene framework ───────────────────────────────────────────────────

class Scene:
    """Reusable scene: simulate with update(dt), paint with draw()."""

    def attach(self, manager: "SceneManager") -> None:
        self.mgr = manager

    def update(self, dt: float) -> None:
        """Advance simulation by dt seconds."""

    def draw(self) -> None:
        """Paint one frame (render order lives here)."""

    def on_key(self, key: str) -> None:
        """keysym, lowercased (arrows arrive as up/down/left/right)."""

    def on_click(self, x: int, y: int) -> None:
        """Mouse click in canvas pixels."""

    def on_resize(self, w: int, h: int) -> None:
        """Window (and canvas) changed size."""


class SceneManager:
    """Owns the Tk window and pumps update(dt) -> draw() at ~30fps."""

    def __init__(self, title="Type Is Code", width=1100, height=620):
        from graficial import Window
        self.window = Window(title, width, height, bg="#14101f",
                             min_width=640, min_height=400)
        self.canvas = self.window.create_canvas(bg="#14101f")
        self.scene: Scene | None = None
        self._last = time.perf_counter()
        self._job = None
        self.window.on_key_down(self._handle_key)
        self.window.on_resize(self._handle_resize)
        self.canvas.raw.bind("<Button-1>", self._handle_click)
        try:
            self.window.root.protocol("WM_DELETE_WINDOW", self.close)
        except Exception:
            pass

    # -- plumbing ---------------------------------------------------
    def switch_to(self, scene: Scene) -> None:
        self.scene = scene
        scene.attach(self)

    def size(self) -> tuple[int, int]:
        return self.canvas.get_size()

    def run(self) -> None:
        self._last = time.perf_counter()
        self._tick()
        self.window.run()

    def tick_once(self) -> None:
        """Advance exactly one frame (drives smoke tests, no mainloop)."""
        now = time.perf_counter()
        dt = clamp_dt(now - self._last)
        self._last = now
        if self.scene is not None:
            self.scene.update(dt)
            self.scene.draw()

    def close(self) -> None:
        job, self._job = self._job, None
        if job is not None:
            try:
                self.window.root.after_cancel(job)
            except Exception:
                pass
        try:
            self.window.root.destroy()
        except Exception:
            pass

    def _tick(self) -> None:
        self._job = None
        try:
            self.tick_once()
        except Exception:
            pass
        try:
            self._job = self.window.root.after(TICK_MS, self._tick)
        except Exception:
            self._job = None

    def _handle_key(self, key: str) -> None:
        if self.scene is not None:
            try:
                self.scene.on_key(key)
            except Exception:
                pass

    def _handle_resize(self, w: int, h: int) -> None:
        if self.scene is not None:
            try:
                self.scene.on_resize(w, h)
            except Exception:
                pass

    def _handle_click(self, event) -> None:
        if self.scene is not None:
            try:
                self.scene.on_click(event.x, event.y)
            except Exception:
                pass


# ── the main-menu scene ───────────────────────────────────────────────

class MainMenuScene(Scene):
    """Cover-art menu: corridor, rifts, bombs, consoles, knight, title.

    Callbacks (all optional): on_new_game, on_multiplayer, on_exit.
    """

    def __init__(self, on_new_game=None, on_multiplayer=None, on_exit=None,
                 on_load=None, settings=None):
        import random as _rand
        self.on_new_game = on_new_game
        self.on_multiplayer = on_multiplayer
        self.on_exit = on_exit
        self.on_load = on_load  # seam for when saves/*.json exists
        self.settings = settings if settings is not None else load_settings()
        self.t = 0.0
        self.sel = 0
        self.items = list(MENU_ITEMS)
        self.item_boxes: list[tuple] = []  # (x1, y1, x2, y2, index)
        self.sparks: list = []             # fuse emitters
        self.motes: list = []              # ambient floating dust
        self.dust: list = []               # knight footstep puffs
        self.bombs = [{"fuse": 2.0 * i} for i in range(4)]
        self.toast = ""
        self.toast_until = 0.0
        self.set_panel = False
        self.set_sel = 0
        self._rand = _rand.Random(20261004)
        self._dust_timer = 0.0
        self._photos = {}  # keep PhotoImages referenced per size

    # -- simulation -------------------------------------------------
    def update(self, dt: float) -> None:
        self.t += dt
        for b in self.bombs:
            b["fuse"] += dt
        if self.toast and self.t >= self.toast_until:
            self.toast = ""
        # knight footstep dust every ~1.1s
        self._dust_timer += dt
        if self._dust_timer > 1.1:
            self._dust_timer = 0.0
            if self.settings.get("particles", True):
                w, h = self.mgr.size()
                lay = menu_layout(w, h)
                kx, ky, _kh = lay["knight"]
                self.dust.append(make_particle(
                    kx - 10, ky - 6, -14, -26, 0.9, 5, "#8a7fa8", grav=-6))
                self.dust.append(make_particle(
                    kx + 14, ky - 2, 18, -18, 0.7, 4, "#6a6088", grav=-6))
        if self.settings.get("particles", True):
            w, h = self.mgr.size()
            lay = menu_layout(w, h)
            self._emit_fuse_sparks(dt, lay)
            self._drift_motes(dt, w, h)
            self.sparks = advance_particles(self.sparks, dt)
            self.motes = advance_particles(self.motes, dt)
        else:
            self.sparks = []
            self.motes = []
        self.dust = advance_particles(self.dust, dt)

    def _photo(self, kind: str, size: int):
        """Cached sprite photo (None when art/Pillow unavailable)."""
        key = (kind, max(8, int(size)))
        if key in self._photos:
            return self._photos[key]
        try:
            if kind == "knight":
                photo = _player_photo(key[1], sharp=True)
            elif kind == "portal":
                photo = _portal_photo(key[1])
            else:
                photo = _boom_photo(key[1])
        except Exception:
            photo = None
        self._photos[key] = photo
        return photo

    def _emit_fuse_sparks(self, dt: float, lay: dict) -> None:
        """One emitter per bomb tip; rate-limited, dt-scaled."""
        import random as _r
        keys = ("bomb_big", "bomb_mid", "bomb_a", "bomb_b")
        for key, bomb in zip(keys, self.bombs):
            if fuse_flashing(bomb["fuse"]):
                continue  # relight pop handles its own flash
            bx, feet, scl = lay[key]
            body = int(30 * scl) + 14
            tip, _arc = self._fuse_tip(bx, feet - 2 * body, body,
                                       fuse_length(bomb["fuse"]))
            n = int(46 * dt) + (1 if _r.random() < (46 * dt) % 1 else 0)
            for _ in range(n):
                ang = _r.uniform(-math.pi, 0.4)
                sp = _r.uniform(30, 130)
                col = _r.choice(("#fff6c8", "#ffd45a", "#ff9d2e"))
                self.sparks.append(make_particle(
                    tip[0], tip[1], math.cos(ang) * sp,
                    math.sin(ang) * sp - 20, _r.uniform(0.25, 0.6),
                    _r.uniform(1, 3), col, grav=160))

    def _drift_motes(self, dt: float, w: int, h: int) -> None:
        """Ambient dust keeps ~60 motes floating through the corridor."""
        import random as _r
        while len(self.motes) < 60:
            self.motes.append(make_particle(
                _r.uniform(0, w), _r.uniform(0.2 * h, h),
                _r.uniform(-8, 8), _r.uniform(-14, -4),
                _r.uniform(2, 5), _r.uniform(1, 2.5), "#5a4f7a"))
        for m in self.motes:
            if m["x"] < 0:
                m["x"] = w
            elif m["x"] > w:
                m["x"] = 0

    @staticmethod
    def _fuse_tip(bx: float, top: float, body: int, frac: float):
        """Fuse arc tip: shortens toward the bomb as frac shrinks."""
        p0 = (bx + body * 0.15, top + body * 0.25)
        p1 = (bx + body * 0.55, top - body * 0.75)
        p2 = (bx + body * 0.95, top - body * 1.05)
        # frac=1 -> full-length tip; frac=FUSE_MIN -> nearly home
        t = 0.35 + 0.65 * min(1.0, frac)
        return bezier(p0, p1, p2, t), (p0, p1, p2)

    # -- input ------------------------------------------------------
    def on_key(self, key: str) -> None:
        if self.set_panel:
            if key in ("escape", "backspace", "q"):
                self.set_panel = False
            elif key in ("up", "w"):
                self.set_sel = (self.set_sel - 1) % 2
            elif key in ("down", "s"):
                self.set_sel = (self.set_sel + 1) % 2
            elif key in ("left", "a", "right", "d", "return", "space"):
                self._toggle_setting(self.set_sel)
            return
        if key in ("left", "a"):
            self.sel = (self.sel - 1) % len(self.items)
        elif key in ("right", "d", "tab"):
            self.sel = (self.sel + 1) % len(self.items)
        elif key in ("up", "w"):
            self.sel = (self.sel - 1) % len(self.items)
        elif key in ("down", "s"):
            self.sel = (self.sel + 1) % len(self.items)
        elif key in ("return", "space"):
            self.activate(self.sel)
        elif key == "m":
            self._do_multiplayer()
        elif key in ("escape", "q"):
            self._do_exit()

    def on_click(self, x: int, y: int) -> None:
        if self.set_panel:
            return  # panel is keyboard-driven
        for (x1, y1, x2, y2, i) in self.item_boxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.sel = i
                self.activate(i)
                return

    def activate(self, i: int) -> None:
        name = self.items[i]
        if name == "NEW GAME":
            if self.on_new_game is not None:
                self.mgr.close()
                self.on_new_game()
        elif name == "LOAD GAME":
            if self.on_load is not None:
                self.mgr.close()
                self.on_load()
            else:
                # No save system yet: honest toast, stay on the menu.
                self._say("No saved expeditions yet — choose NEW GAME.")
        elif name == "MULTIPLAYER":
            self._do_multiplayer()
        elif name == "SETTINGS":
            self.set_panel = True
        elif name == "EXIT":
            self._do_exit()

    def _do_multiplayer(self) -> None:
        if self.on_multiplayer is not None:
            self.mgr.close()
            self.on_multiplayer()
        else:
            self._say("Multiplayer is not wired up.")

    def _do_exit(self) -> None:
        if self.on_exit is not None:
            self.mgr.close()
            self.on_exit()
        else:
            self.mgr.close()

    def _toggle_setting(self, row: int) -> None:
        key = "particles" if row == 0 else "fullscreen"
        self.settings[key] = not self.settings.get(key, False)
        save_settings(self.settings)
        if key == "fullscreen":
            try:
                self.mgr.window.root.attributes(
                    "-fullscreen", bool(self.settings[key]))
            except Exception:
                pass

    def _say(self, text: str, secs: float = 2.5) -> None:
        self.toast = text
        self.toast_until = self.t + secs

    # -- painting (render order is the method order) ----------------
    def draw(self) -> None:
        raw = self.mgr.canvas.raw
        raw.delete("all")
        w, h = self.mgr.size()
        if w < 10 or h < 10:
            return
        lay = menu_layout(w, h)
        self._draw_corridor(raw, lay)
        self._draw_floor_props_back(raw, lay)   # barrel, far chest, schematic
        self._draw_portals(raw, lay)            # rifts + cast light
        self._draw_consoles(raw, lay)           # flickering logic panels
        self._draw_floor_props(raw, lay)        # bombs, chests, dust
        self._draw_knight(raw, lay)             # breathing hero + glint
        self._draw_title(raw, lay)              # electric glow + sheen
        self._draw_menu(raw, lay)               # pulsing selection
        if self.set_panel:
            self._draw_settings(raw, lay)
        if self.toast:
            self._draw_toast(raw, lay)

    # 1. background corridor ---------------------------------------
    def _draw_corridor(self, raw, lay: dict) -> None:
        w, h = lay["w"], lay["h"]
        vpx, vpy = lay["vp"]
        x1, y1, x2, y2 = lay["back"]
        # room tone + soft ceiling light well
        raw.create_rectangle(0, 0, w, h, fill="#14101f", outline="")
        raw.create_oval(vpx - 0.3 * w, -0.25 * h, vpx + 0.3 * w, 0.45 * h,
                        fill="#2c2148", outline="")
        # back wall + perspective grid
        raw.create_rectangle(x1, y1, x2, y2, fill="#37295a", outline="#5a4486")
        for i in range(1, 5):
            f = i / 5
            raw.create_line(x1 + (vpx - x1) * 0, y1 + (y2 - y1) * f,
                            x2, y1 + (y2 - y1) * f, fill="#4c3880")
            bx = x1 + (x2 - x1) * i / 5
            raw.create_line(bx, y1, vpx + (bx - vpx) * 0.2, y2,
                            fill="#4c3880")
        # side walls: converging brick courses (cheap lines, big depth)
        for side in (0, 1):
            x0 = 0 if side == 0 else w
            xb = x1 if side == 0 else x2
            raw.create_polygon(x0, 0, xb, y1, xb, y2, x0, h,
                               fill="#2a1f45" if side == 0 else "#241a3a",
                               outline="")
            for i in range(1, 9):
                f = (i / 9) ** 1.6  # courses bunch up toward the back
                y = y1 + (vpy - y1) * f if f < 1 else y1 + (y2 - y1) * f
                y = min(y, y2 - 2)
                xa = x0 + (xb - x0) * f
                raw.create_line(xa if side == 0 else x0,
                                y, xb if side == 0 else xa, y,
                                fill="#453366")
            # vertical joints slanting to the vanishing point
            for i in range(1, 7):
                f = i / 7
                xt = x0 + (xb - x0) * f
                raw.create_line(x0 + (w * 0.12 if side == 0 else -w * 0.12) * f,
                                f * h * 0.9, xt, y1 + (y2 - y1) * f,
                                fill="#372a58")
        # floor: dark base + perspective slab lines to the back wall
        raw.create_polygon(0, h, x1, y2, x2, y2, w, h,
                           fill="#33295c", outline="")
        for i in range(1, 7):
            f = (i / 7) ** 1.4
            y = y2 + (h - y2) * f
            raw.create_line((0 + (x1 - 0) * f), y,
                            (w - (w - x2) * f), y, fill="#4a3a78")
            fx = (x1 + (x2 - x1) * i / 7)
            raw.create_line(fx, y2, (fx - vpx) * 3 + vpx, h,
                            fill="#423273")

    # 2a. rear props + far schematic --------------------------------
    def _draw_floor_props_back(self, raw, lay: dict) -> None:
        self._draw_schematic(raw, lay)
        # small far chest by the back wall
        self._draw_chest(raw, lay["chest_a"][0], lay["chest_a"][1],
                         lay["chest_a"][2], seed=3)
        # red barrel left of the knight
        bx, by, bh = lay["barrel"]
        bw = bh * 0.75
        raw.create_rectangle(bx - bw / 2, by - bh, bx + bw / 2, by,
                             fill="#a02323", outline="#5e1212", width=2)
        raw.create_oval(bx - bw / 2, by - bh - bw * 0.18,
                        bx + bw / 2, by - bh + bw * 0.18,
                        fill="#c23a3a", outline="#5e1212", width=2)
        for f in (0.3, 0.7):
            raw.create_line(bx - bw / 2, by - bh * f, bx + bw / 2,
                            by - bh * f, fill="#5e1212", width=2)
        raw.create_line(bx - bw / 4, by - bh, bx - bw / 4, by - 2,
                        fill="#e06a6a", width=2)

    def _draw_schematic(self, raw, lay: dict) -> None:
        """Far-wall circuit print with travelling data-flow dots."""
        x1, y1, x2, y2 = lay["back"]
        ox, oy = x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.18
        s = (x2 - x1) / 220
        wires = [
            [(ox, oy), (ox + 60 * s, oy), (ox + 60 * s, oy + 34 * s),
             (ox + 110 * s, oy + 34 * s)],
            [(ox + 20 * s, oy + 60 * s), (ox + 90 * s, oy + 60 * s),
             (ox + 90 * s, oy + 20 * s)],
            [(ox, oy + 90 * s), (ox + 130 * s, oy + 90 * s)],
        ]
        for pts in wires:
            flat = [c for p in pts for c in p]
            raw.create_line(*flat, fill="#3f6a8a", width=1)
            total = polyline_length(pts)
            for k in range(2):
                d = (self.t * 46 + k * total / 2) % total
                dx, dy = walk_polyline(pts, d)
                raw.create_oval(dx - 2, dy - 2, dx + 2, dy + 2,
                                fill="#7de3ff", outline="")
        # two logic gates + one register block
        gx, gy = ox + 110 * s, oy + 34 * s
        raw.create_arc(gx - 12 * s, gy - 12 * s, gx + 12 * s, gy + 12 * s,
                       start=270, extent=180, style="arc",
                       outline="#ff9d5a", width=2)
        raw.create_line(gx - 12 * s, gy - 12 * s, gx - 12 * s, gy + 12 * s,
                        fill="#ff9d5a", width=2)
        raw.create_text(gx + 22 * s, gy, text="XOR",
                        fill="#ffcf5a", font=("Consolas", max(6, int(9 * s))),
                        anchor="w")
        rx, ry = ox + 60 * s, oy + 90 * s
        raw.create_rectangle(rx - 16 * s, ry - 9 * s, rx + 16 * s, ry + 9 * s,
                             fill="#12283a", outline="#3f6a8a")
        raw.create_text(rx, ry, text="1011", fill="#7de3ff",
                        font=("Consolas", max(6, int(9 * s))), anchor="center")

    # 2b. live portals ----------------------------------------------
    def _draw_portals(self, raw, lay: dict) -> None:
        for key, seed in (("portal_l", 0.0), ("portal_r", 2.4),
                          ("portal_far", 4.1)):
            cx, cy, r = lay[key]
            self._draw_portal(raw, cx, cy, r, seed)

    def _draw_portal(self, raw, cx: float, cy: float, r: float,
                     seed: float) -> None:
        import math as _m
        pulse = portal_pulse(self.t, seed)
        # shifting blue light cast on the nearby wall/floor
        glow_r = r * (1.45 + 0.3 * pulse)
        for i, col in (0, "#1c3a66"), (1, "#16294d"):
            rr = glow_r - i * r * 0.35
            raw.create_oval(cx - rr, cy - rr * 1.25, cx + rr,
                            cy + rr * 1.25, fill="", outline=col, width=2)
        # luminous rift body: stacked discs from dark maw to bright rim
        raw.create_oval(cx - r, cy - r * 1.25, cx + r, cy + r * 1.25,
                        fill="#0a1440", outline="")
        raw.create_oval(cx - r * 0.74, cy - r * 0.92, cx + r * 0.74,
                        cy + r * 0.92, fill="#14407f", outline="")
        raw.create_oval(cx - r * 0.46, cy - r * 0.58, cx + r * 0.46,
                        cy + r * 0.58, fill="#1c5fb0", outline="")
        # light pool spilling onto the floor below the rift
        raw.create_oval(cx - r * 1.6, cy + r * 1.9, cx + r * 1.6,
                        cy + r * 2.6, fill="", outline="#1c4fa8", width=2)
        # stone rim pillars either side of the rift
        for sx in (-1, 1):
            px = cx + sx * r * 1.15
            raw.create_rectangle(px - r * 0.18, cy - r * 1.6,
                                 px + r * 0.18, cy + r * 1.6,
                                 fill="#3a2c5c", outline="#241b40")
        # chaotic vortex: sine-warped arcs spinning opposite ways
        for k in range(5):
            rr = r * (0.35 + 0.13 * k)
            wob = 1 + 0.10 * _m.sin(self.t * 3.2 + seed + k * 1.7)
            rr *= wob
            start = (self.t * (64 if k % 2 else -46) + seed * 57
                     + k * 72) % 360
            raw.create_arc(cx - rr, cy - rr * 1.25, cx + rr, cy + rr * 1.25,
                           start=start, extent=250, style="arc",
                           outline="#9adfff" if k % 2 else "#2a7fff",
                           width=max(1, int(r / 18)))
        # bright core (photo when available, procedural maw otherwise)
        core = self._photo("portal", int(r * 1.1))
        if core is not None:
            raw.create_image(cx, cy, image=core, anchor="center")
        else:
            raw.create_oval(cx - r * 0.28, cy - r * 0.34,
                            cx + r * 0.28, cy + r * 0.34,
                            fill="#04060d", outline="#9adfff", width=2)
        # orbiting sparks thrown off the rim
        if self.settings.get("particles", True):
            for i in range(3):
                a = self.t * 2.6 + seed + i * 2.094
                ox = _m.cos(a) * r * 1.05
                oy = _m.sin(a) * r * 1.3
                raw.create_oval(cx + ox - 2, cy + oy - 2, cx + ox + 2,
                                cy + oy + 2, fill="#cfecff", outline="")

    # 2c. consoles ----------------------------------------------------
    def _draw_consoles(self, raw, lay: dict) -> None:
        prog = CONSOLE_PROGRAMS[console_program(self.t)]
        for key, big in (("console_l", True), ("console_m", False),
                         ("console_r", False)):
            x, y, cw, chh = lay[key]
            self._draw_console(raw, x, y, cw, chh, prog, big)

    def _draw_console(self, raw, x, y, cw, chh, prog, big: bool) -> None:
        raw.create_rectangle(x, y, x + cw, y + chh, fill="#0d1626",
                             outline="#5fc9ff", width=2)
        raw.create_rectangle(x + 3, y + 3, x + cw - 3, y + chh - 3,
                             fill="", outline="#1c3a5a")
        fs = max(6, int(chh * (0.16 if big else 0.20)))
        # fit the longest program line inside the frame at any size
        longest = max(len(text) for text, _col in prog)
        fs = min(fs, max(6, int(cw / (0.62 * longest))))
        for i, (text, col) in enumerate(prog):
            if not console_flicker(self.t, i):
                col = "#2a3a4a"  # dropout frame
            raw.create_text(x + cw / 2, y + chh * (0.32 + 0.26 * i),
                            text=text, fill=col,
                            font=("Consolas", fs, "bold"), anchor="center")
        # status LEDs along the bottom edge
        for i, col in enumerate(("#4adc6e", "#e05565", "#ffcf5a")):
            lx = x + cw * (0.2 + 0.3 * i)
            on = (int(self.t * 2) + i) % 2 == 0
            raw.create_oval(lx - 3, y + chh - 9, lx + 3, y + chh - 3,
                            fill=col if on else "#1a2233", outline="")

    # 3. floor props: bombs, chests, dust ------------------------------
    def _draw_floor_props(self, raw, lay: dict) -> None:
        keys = ("bomb_big", "bomb_mid", "bomb_a", "bomb_b")
        for key, bomb in zip(keys, self.bombs):
            bx, feet, scl = lay[key]
            body = int(30 * scl) + 14
            self._draw_bomb(raw, bx, feet, body, bomb)
        self._draw_chest(raw, lay["chest_b"][0], lay["chest_b"][1],
                         lay["chest_b"][2], seed=7)
        self._draw_chest(raw, lay["chest_big"][0], lay["chest_big"][1],
                         lay["chest_big"][2], seed=11, open_lid=True)
        for p in self.dust:
            a = p["life"] / p["max"]
            r = p["size"] * (1.6 - a * 0.6)
            raw.create_oval(p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r,
                            fill="", outline="#8a7fa8", width=1)
        for p in self.sparks:
            r = p["size"]
            raw.create_oval(p["x"] - r, p["y"] - r, p["x"] + r, p["y"] + r,
                            fill=p["col"], outline=p["col"])
        for m in self.motes:
            r = m["size"]
            raw.create_oval(m["x"] - r, m["y"] - r, m["x"] + r, m["y"] + r,
                            fill="", outline="#4a4270")

    def _draw_bomb(self, raw, bx: float, feet: float, body: int,
                   bomb: dict) -> None:
        import math as _m
        cy = feet - body
        # warm aura breathing with the fuse
        pulse = 0.5 + 0.5 * _m.sin(self.t * 5 + bx)
        raw.create_oval(bx - body * (1.25 + 0.15 * pulse),
                        cy - body * (1.25 + 0.15 * pulse),
                        bx + body * (1.25 + 0.15 * pulse),
                        cy + body * (1.25 + 0.15 * pulse),
                        fill="", outline="#7a3a1a", width=2)
        photo = self._photo("boom", body * 2)
        if photo is not None:
            raw.create_image(bx, cy, image=photo, anchor="center")
        else:
            raw.create_oval(bx - body, cy - body, bx + body, cy + body,
                            fill="#3a3f4a", outline="#0a0a0a", width=3)
            raw.create_oval(bx - body * 0.55, cy - body * 0.45,
                            bx + body * 0.55, cy + body * 0.45,
                            fill="#d63a2f", outline="#7a1a1a", width=2)
        # fuse: bezier from the crown, visibly shortening as it burns
        frac = fuse_length(bomb["fuse"])
        tip, (p0, p1, p2) = self._fuse_tip(bx, cy - body, body, frac)
        raw.create_line(p0[0], p0[1],
                        *bezier(p0, p1, p2, 0.33),
                        *bezier(p0, p1, p2, 0.66), tip[0], tip[1],
                        fill="#8a5a2a", width=max(2, body // 10),
                        smooth=True)
        if fuse_flashing(bomb["fuse"]):
            raw.create_oval(tip[0] - 14, tip[1] - 14, tip[0] + 14,
                            tip[1] + 14, fill="#fff6c8",
                            outline="#ffd45a", width=2)
        else:
            raw.create_oval(tip[0] - 4, tip[1] - 4, tip[0] + 4, tip[1] + 4,
                            fill="#fff6c8", outline="#ff9d2e", width=2)

    def _draw_chest(self, raw, cx: float, base: float, scl: float,
                    seed: int, open_lid: bool = False) -> None:
        import math as _m
        w = 44 * scl + 16
        h = 30 * scl + 12
        x1, y1 = cx - w / 2, base - h
        # warm gold light spilling out
        pulse = 0.5 + 0.5 * _m.sin(self.t * 2.4 + seed)
        raw.create_oval(cx - w * (0.8 + 0.2 * pulse), base - h * 2.2,
                        cx + w * (0.8 + 0.2 * pulse), base + 4,
                        fill="", outline="#a8842a", width=3)
        raw.create_rectangle(x1, y1, x1 + w, base, fill="#7a5527",
                             outline="#3a2410", width=2)
        raw.create_rectangle(x1, y1, x1 + w, y1 + h * 0.35,
                             fill="#ffe9a8" if open_lid else "#a87c3e",
                             outline="#3a2410", width=2)
        raw.create_line(x1 + w / 2, y1, x1 + w / 2, base,
                        fill="#ffdf7a", width=3)
        # glinting gold: brief refractive star flashes
        if (self.t * 0.7 + seed) % 2.0 < 0.3:
            gx, gy = cx - w * 0.2, y1 + h * 0.18
            L = 6 + 4 * pulse
            raw.create_line(gx - L, gy, gx + L, gy,
                            fill="#ffffff", width=2)
            raw.create_line(gx, gy - L, gx, gy + L,
                            fill="#fff6c8", width=2)

    # 4. the knight -----------------------------------------------------
    def _draw_knight(self, raw, lay: dict) -> None:
        import math as _m
        kx, feet, kh = lay["knight"]
        # looping breath: gentle rise + head-bob (whole-sprite drift)
        bob = 3 * _m.sin(self.t * 2 * _m.pi * 0.5)
        sway = 1.5 * _m.sin(self.t * 2 * _m.pi * 0.25 + 1)
        # grounded shadow while the armour floats
        raw.create_oval(kx - kh * 0.20, feet - 6, kx + kh * 0.20, feet + 6,
                        fill="#05070f", outline="")
        photo = self._photo("knight", int(kh))
        if photo is not None:
            raw.create_image(kx + sway, feet - kh / 2 + bob,
                             image=photo, anchor="center")
        else:
            r = kh * 0.28
            raw.create_oval(kx - r + sway, feet - kh + bob,
                            kx + r + sway, feet - kh + r * 2 + bob,
                            fill="#9aa0b0", outline="#0a0a0a", width=3)
            raw.create_rectangle(kx - r * 0.7 + sway, feet - kh + r * 1.6,
                                 kx + r * 0.7 + sway, feet - 8,
                                 fill="#7a7f99", outline="#0a0a0a", width=3)
        # sword glint: bright edge-light sweeping the blade ~every 2.4s
        cyc = (self.t % 2.4) / 2.4
        if 0.55 < cyc < 0.8:
            f = (cyc - 0.55) / 0.25
            gx = kx + kh * (0.05 + 0.30 * f) + sway
            gy = feet - kh * (0.45 - 0.25 * f) + bob
            raw.create_line(gx - 12, gy + 8, gx + 12, gy - 8,
                            fill="#ffffff", width=3)

    # 5. title ------------------------------------------------------------
    def _draw_title(self, raw, lay: dict) -> None:
        import math as _m
        import random as _r
        cx, cy = lay["title"]
        h = lay["h"]
        w = lay["w"]
        # fit the single line inside ~68% of the window at any resolution
        fs = max(28, int(h * 0.125))
        for _ in range(3):
            font = ("Consolas", fs, "bold")
            probe = raw.create_text(cx, cy, text=TITLE_TEXT, font=font,
                                    anchor="center")
            bx1, by1, bx2, by2 = raw.bbox(probe)
            raw.delete(probe)
            if (bx2 - bx1) <= 0.68 * w or fs <= 12:
                break
            fs = max(12, int(fs * 0.68 * w / (bx2 - bx1)))
        font = ("Consolas", fs, "bold")
        glow = 0.5 + 0.5 * _m.sin(self.t * 2.4)  # soft electric breathing
        # dark plate behind the chrome
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)):
            raw.create_text(cx + dx, cy + dy, text=TITLE_TEXT,
                            fill="#05070f", font=font, anchor="center")
        # blue halo (brighter on the pulse)
        halo = "#2a7fff" if glow > 0.5 else "#1c4faa"
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            raw.create_text(cx + dx, cy + dy, text=TITLE_TEXT,
                            fill=halo, font=font, anchor="center")
        raw.create_text(cx, cy, text=TITLE_TEXT, fill="#e8f0ff",
                        font=font, anchor="center")
        # crawling lightning: re-rolled a few times a second so the arcs
        # snap and writhe AROUND the letters like the reference video
        # (never through them)
        seed = int(self.t / 0.33)
        rng = _r.Random(77 + seed)
        self._draw_bolt(raw, bx1 - 8, by1 - 12, bx2 + 8, by1 - 5, rng)
        self._draw_bolt(raw, bx1 - 8, by2 + 5, bx2 + 8, by2 + 12, rng)
        # shimmer: a sheen bar sweeping across the title, dt-driven
        span = (bx2 - bx1) + 120
        sx = bx1 - 60 + ((self.t * 130) % span)
        raw.create_rectangle(sx - 8, by1 - 6, sx + 8, by2 + 6,
                             fill="#bfe6ff", outline="",
                             stipple="gray25")
        raw.create_rectangle(sx - 2, by1 - 6, sx + 2, by2 + 6,
                             fill="#ffffff", outline="")

    @staticmethod
    def _draw_bolt(raw, x1: float, y1: float, x2: float, y2: float,
                   rng) -> None:
        """One jagged electric arc: blue under-copy + white-hot core."""
        n = max(6, int(abs(x2 - x1) / 22))
        pts = []
        for i in range(n + 1):
            f = i / n
            jx = (rng.random() - 0.5) * 16 if 0 < i < n else 0
            jy = (rng.random() - 0.5) * 20 if 0 < i < n else 0
            pts.append((x1 + (x2 - x1) * f + jx,
                        y1 + (y2 - y1) * f + jy))
        flat = [c for p in pts for c in p]
        raw.create_line(*flat, fill="#2a7fff", width=3, smooth=False)
        raw.create_line(*flat, fill="#cfecff", width=1, smooth=False)

    # 6. text menu ----------------------------------------------------------
    def _draw_menu(self, raw, lay: dict) -> None:
        import math as _m
        w = lay["w"]
        fs = max(13, int(lay["h"] * 0.028))
        font = ("Consolas", fs, "bold")
        total = len(self.items)
        spacing = min(0.19 * w, 210)
        x0 = w / 2 - spacing * (total - 1) / 2
        self.item_boxes = []
        for i, name in enumerate(self.items):
            cx = x0 + spacing * i
            cy = lay["menu_y"]
            pad_x, pad_y = 14, 8
            # measure via a probe item, then frame it
            probe = raw.create_text(cx, cy, text=name, font=font,
                                    anchor="center")
            bx1, by1, bx2, by2 = raw.bbox(probe)
            raw.delete(probe)
            self.item_boxes.append((bx1 - pad_x, by1 - pad_y,
                                    bx2 + pad_x, by2 + pad_y, i))
            if i == self.sel:
                pulse = 0.5 + 0.5 * _m.sin(self.t * 4.2)
                # cyan electric frame, hot on the pulse
                raw.create_rectangle(bx1 - pad_x - 3, by1 - pad_y - 3,
                                     bx2 + pad_x + 3, by2 + pad_y + 3,
                                     fill="", outline="#2a7fff", width=3)
                raw.create_rectangle(bx1 - pad_x, by1 - pad_y,
                                     bx2 + pad_x, by2 + pad_y,
                                     fill="", outline="#9adfff",
                                     width=1 + int(2 * pulse))
                raw.create_text(cx, cy, text=name, fill="#ffffff",
                                font=font, anchor="center")
            else:
                raw.create_text(cx, cy, text=name, fill="#8a93b8",
                                font=font, anchor="center")

    # overlays ------------------------------------------------------------
    def _draw_settings(self, raw, lay: dict) -> None:
        w, h = lay["w"], lay["h"]
        bw, bh = min(420, w * 0.6), 150
        x1, y1 = w / 2 - bw / 2, h / 2 - bh / 2
        raw.create_rectangle(0, 0, w, h, fill="#05070f",
                             outline="", stipple="gray50")
        raw.create_rectangle(x1, y1, x1 + bw, y1 + bh, fill="#111528",
                             outline="#8aa2ff", width=2)
        raw.create_text(w / 2, y1 + 26, text="SETTINGS", fill="#eef1ff",
                        font=("Consolas", 16, "bold"), anchor="center")
        rows = (("PARTICLES", self.settings.get("particles", True)),
                ("FULLSCREEN", self.settings.get("fullscreen", False)))
        for i, (name, on) in enumerate(rows):
            cy = y1 + 62 + i * 32
            col = "#e8f0ff" if i == self.set_sel else "#8a93b8"
            raw.create_text(x1 + 24, cy, text=name, fill=col,
                            font=("Consolas", 13, "bold"), anchor="w")
            raw.create_text(x1 + bw - 24, cy,
                            text="ON" if on else "OFF",
                            fill="#4adc6e" if on else "#e05565",
                            font=("Consolas", 13, "bold"), anchor="e")
        raw.create_text(w / 2, y1 + bh - 14,
                        text="Arrows + Enter toggle, Esc back",
                        fill="#a8b0d0", font=("Consolas", 10),
                        anchor="center")

    def _draw_toast(self, raw, lay: dict) -> None:
        raw.create_text(lay["w"] / 2, lay["h"] - 28, text=self.toast,
                        fill="#ffcf5a", font=("Consolas", 12, "bold"),
                        anchor="center")


# ── entry point ─────────────────────────────────────────────────────────

def run_animated_menu(on_play=None, on_new_game=None, on_multiplayer=None,
                      on_exit=None, on_race=None, on_load=None) -> None:
    """Show the animated main menu (blocking).

    NEW GAME starts solo via on_play/on_new_game; LOAD GAME uses on_load
    when a save system provides one (otherwise a toast); M opens the
    lobby flow; SETTINGS is handled inside the scene; EXIT closes.
    `on_race` is accepted for run_menus signature compatibility.
    """
    new_cb = on_new_game if on_new_game is not None else on_play
    mgr = SceneManager()
    if bool(load_settings().get("fullscreen", False)):
        try:
            mgr.window.root.attributes("-fullscreen", True)
        except Exception:
            pass
    mgr.switch_to(MainMenuScene(on_new_game=new_cb,
                                on_multiplayer=on_multiplayer,
                                on_exit=on_exit,
                                on_load=on_load))
    mgr.window.focus()
    mgr.run()
