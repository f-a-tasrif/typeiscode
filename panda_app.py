"""panda_app.py — Panda3D renderer (Phase 2: textured, lit, animated).

A GameView that renders levels as real 3D geometry: procedural PIL
textures (brick / pavement / brushed metal / portal swirl), a
shadow-casting sun, warp point-lights with flicker, CPU spark/ember/
dust pools stepped on a Panda3D task, a primitive-composed knight
with idle motion, and billboarded code-block labels on dark plates.
Game logic is untouched -- the view only reads Level state and sends
input through Level.move_player (see view.py for the contract).
"""

from __future__ import annotations

import math
import random

from view import GameView

BLOCK_COLORS = {
    "CLASS": "#1a4a7a",
    "PROP": "#1a5a4a",
    "OP": "#4a3a1a",
    "VALUE": "#3a1a5a",
    "NOT": "#5a1a3a",
}

TERRAIN_COLORS = {
    "Door": "#d96b3d",
    "Trap": "#c74555",
    "Stone": "#5a5e78",
    "SealWall": "#8b5cf6",
    "LeverPedestal": "#d96b1a",
    "LatchDoor": "#c44a8c",
    "LaserDoor": "#e34b3e",
    "Warp": "#6366f1",
    "HiddenBoom": "#3a3f4a",
    "HardMine": "#3a3f4a",
    "BorderMine": "#3a3f4a",
}


def hex_color(spec: str, alpha: float = 1.0, tint: float = 1.0):
    """'#rrggbb' -> LColor (import here: no panda3d at module import)."""
    from panda3d.core import LColor
    spec = spec.lstrip("#")
    r, g, b = (int(spec[i:i + 2], 16) / 255.0 * tint for i in (0, 2, 4))
    return LColor(min(1.0, r), min(1.0, g), min(1.0, b), alpha)


def _cell_hash(gx: int, gy: int, salt: int = 0) -> float:
    """Deterministic 0..1 variation per cell (stable across re-syncs)."""
    h = (int(gx) * 374761393 + int(gy) * 668265263
         + int(salt) * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 65535.0


def _gray_texture(name: str, size: int, painter) -> object:
    """Build a grayscale Panda3D texture via PNMImage (tinted by setColor)."""
    from panda3d.core import PNMImage, Texture
    img = PNMImage(size, size)
    rng = random.Random(7)
    for y in range(size):
        for x in range(size):
            v = painter(x, y, size, rng)
            img.setXel(x, y, v, v, v)
    tex = Texture(name)
    tex.load(img)
    tex.setMagfilter(Texture.FTLinear)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    return tex


def make_brick_texture():
    """Dark dungeon brick courses with mortar joints + stone speckle."""
    def paint(x, y, s, rng):
        row, course = y // 16, 64
        off = course // 2 if (row % 2) else 0
        mortar = (y % 16 == 0) or ((x + off) % course == 0)
        if mortar:
            return 0.48
        return 0.88 + rng.uniform(-0.09, 0.09)
    return _gray_texture("brick", 128, paint)


def make_floor_texture():
    """Worn pavement slabs with speckle grime."""
    def paint(x, y, s, rng):
        slab = 32
        joint = (x % slab == 0) or (y % slab == 0)
        if joint:
            return 0.46
        v = 0.82 + rng.uniform(-0.07, 0.07)
        if rng.random() < 0.03:
            v -= 0.18  # grime fleck
        return v
    return _gray_texture("floor", 64, paint)


def make_metal_texture():
    """Brushed metal: vertical gradient bands + faint machining lines."""
    def paint(x, y, s, rng):
        band = 0.86 + 0.10 * (x / max(1, s - 1))
        if x % 7 == 0:
            band -= 0.08
        return band + rng.uniform(-0.02, 0.02)
    return _gray_texture("metal", 64, paint)


def make_swirl_texture():
    """Blue portal swirl: bent bands around a dark maw (colored)."""
    from panda3d.core import PNMImage, Texture
    s = 128
    img = PNMImage(s, s)
    for y in range(s):
        for x in range(s):
            dx, dy = (x - s / 2) / (s / 2), (y - s / 2) / (s / 2)
            d = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            band = 0.5 + 0.5 * math.sin(d * 9.0 - ang * 3.0)
            core = max(0.0, 1.0 - d * 1.6)
            r = 0.10 + 0.25 * band * (1 - core)
            g = 0.25 + 0.45 * band * (1 - core)
            b = 0.70 + 0.30 * band
            img.setXel(x, y, r, g, b)
    tex = Texture("swirl")
    tex.load(img)
    tex.setMagfilter(Texture.FTLinear)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    return tex


class SparkPool:
    """CPU particle pool: pre-made sphere instances, dt-stepped.

    Mirrors the menu_scene emitter style (no ParticleEffect config
    files): emit() spawns, step(dt) integrates + retires. Deterministic
    enough to unit-test headless.
    """

    def __init__(self, base, ball_model, cap: int, name: str):
        self.root = base.render.attachNewNode(name)
        self.items = []
        for _ in range(cap):
            node = ball_model.copyTo(self.root)
            node.hide()
            self.items.append({"node": node, "life": 0.0, "max": 1.0,
                               "vx": 0.0, "vy": 0.0, "vz": 0.0,
                               "grav": 0.0, "size": 0.05})
        self._cursor = 0
        self.cap = cap

    def alive(self) -> int:
        return sum(1 for s in self.items if s["life"] > 0)

    def emit(self, pos, vel, life: float, size: float, color,
             grav: float = 0.0) -> None:
        s = self.items[self._cursor]
        self._cursor = (self._cursor + 1) % self.cap
        node = s["node"]
        node.show()
        node.setPos(*pos)
        node.setScale(size, size, size)
        node.setColor(*color)
        s.update({"life": life, "max": life, "vx": vel[0], "vy": vel[1],
                  "vz": vel[2], "grav": grav, "size": size})

    def step(self, dt: float) -> None:
        for s in self.items:
            if s["life"] <= 0:
                continue
            s["life"] -= dt
            if s["life"] <= 0:
                s["node"].hide()
                continue
            s["vz"] += s["grav"] * dt
            node = s["node"]
            x, y, z = node.getPos()
            node.setPos(x + s["vx"] * dt, y + s["vy"] * dt,
                        z + s["vz"] * dt)
            frac = s["life"] / s["max"]
            sc = s["size"] * (0.35 + 0.65 * frac)
            node.setScale(sc, sc, sc)


def _make_cube():
    """Unit cube centred on the origin, no textures/vertex colours.

    The stock models/box carries rainbow vertex colours, so the
    graybox builds its own cube from six CardMaker quads (correct
    outward normals, flat shading under the scene lights).
    """
    from panda3d.core import CardMaker
    from panda3d.core import NodePath
    root = NodePath("cube")
    cm = CardMaker("face")
    cm.setFrame(-0.5, 0.5, -0.5, 0.5)
    for hpr, pos in (((0, 0, 0), (0, 0, 0.5)),       # top
                     ((0, 180, 0), (0, 0, -0.5)),    # bottom
                     ((0, -90, 0), (0, 0.5, 0)),     # +Y
                     ((0, 90, 0), (0, -0.5, 0)),     # -Y
                     ((0, 0, 90), (0.5, 0, 0)),      # +X
                     ((0, 0, -90), (-0.5, 0, 0))):   # -X
        face = root.attachNewNode(cm.generate())
        face.setHpr(*hpr)
        face.setPos(*pos)
    return root


class PandaView(GameView):
    """Graybox 3D renderer. One unit per cell, X right, Y up-map, Z up.

    Composition (not inheritance): ShowBase owns an attribute literally
    named ``render`` (the scene-graph root), which would shadow
    GameView.render. The ShowBase instance lives on ``self._base``.
    """

    def __init__(self, start_index: int = 0, headless: bool = False):
        # Config must land before ShowBase opens its window.
        from panda3d.core import loadPrcFileData
        if headless:
            loadPrcFileData("", "window-type none")
        from direct.showbase.ShowBase import ShowBase

        from levels_data import ALL_LEVELS
        if not 0 <= start_index < len(ALL_LEVELS):
            raise ValueError(
                f"Invalid start_index {start_index}. "
                f"Choose 0-{len(ALL_LEVELS) - 1}.")
        self.level_index = start_index
        self.game_completed = False
        self._message = ""
        self._closed = False

        # ShowBase.__init__ opens the window (unless headless above).
        # NOTE: self.render must stay ShowBase's scene root, so the app
        # instance is composed (self._base), never inherited.
        self._base = ShowBase()
        base = self._base
        base.disableMouse()
        base.setBackgroundColor(0.06, 0.05, 0.12, 1)

        from panda3d.core import AmbientLight, DirectionalLight, Fog
        amb = AmbientLight("ambient")
        amb.setColor((0.58, 0.58, 0.68, 1))
        base.render.setLight(base.render.attachNewNode(amb))
        sun = DirectionalLight("sun")
        sun.setColor((1.1, 1.06, 0.98, 1))
        sun_np = base.render.attachNewNode(sun)
        sun_np.setHpr(45, -60, 0)
        base.render.setLight(sun_np)
        # shadow-casting sun + per-pixel lighting for the whole scene
        try:
            sun.setShadowCaster(True, 2048, 2048)
            sun.getLens().setFilmSize(120, 120)
            base.render.setShaderAuto()
            self._shadows = True
        except Exception:
            self._shadows = False
        # dungeon depth haze
        fog = Fog("dungeon")
        fog.setColor(0.06, 0.05, 0.12)
        fog.setExpDensity(0.011)
        base.render.setFog(fog)

        self._box = _make_cube()
        self._box.reparentTo(base.hidden)  # template stash, never rendered
        from panda3d.core import CardMaker
        _cm = CardMaker("quad")
        _cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        self._quad = base.hidden.attachNewNode(_cm.generate())
        self._ball = base.loader.loadModel("models/misc/sphere")
        self.world = base.render.attachNewNode("world")

        # shared procedural textures (built once, tinted per instance)
        self._tex_brick = make_brick_texture()
        self._tex_floor = make_floor_texture()
        self._tex_metal = make_metal_texture()
        self._tex_swirl = make_swirl_texture()

        # CPU particle pools (sparks / embers / dust) + fx clock
        self._sparks = SparkPool(base, self._ball, 140, "sparks")
        self._wisps = SparkPool(base, self._ball, 70, "wisps")
        self._dust = SparkPool(base, self._ball, 70, "dust")
        self._fx_t = 0.0
        self._emitters: list = []      # rebuilt per sync: pos/kind/rate/acc
        self._warp_discs: list = []   # (node, seed) for UV scroll
        self._warp_lights: list = []  # (PointLight node, seed) for flicker
        self._actor = None            # knight root, refreshed per sync
        self._actor_cell = None
        self._rand = random.Random(99)
        base.taskMgr.add(self._fx_step, "dungeon-fx")

        from direct.gui.OnscreenText import OnscreenText
        self._hud = OnscreenText(
            text="", pos=(-1.28, 0.92), align=0, scale=0.055,
            fg=(0.93, 0.95, 1, 1), mayChange=True)

        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()

        for key, direction in (("w", "w"), ("s", "s"), ("a", "a"),
                               ("d", "d"), ("arrow_up", "w"),
                               ("arrow_down", "s"), ("arrow_left", "a"),
                               ("arrow_right", "d")):
            self._base.accept(key, self._move, [direction])
        self._base.accept("r", self._restart_key)
        self._base.accept("q", self.close)
        self._base.accept("escape", self.close)

        self.sync()

    # ── GameView contract ─────────────────────────────────────────
    def render(self, message: str = "") -> None:
        self._message = message or ""
        self.sync()

    def run(self) -> None:
        self._base.run()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._base.ignoreAll()
        except Exception:
            pass
        try:
            self._base.destroy()
        except Exception:
            pass

    def screenshot(self, path: str) -> bool:
        """Save the back buffer to `path` (windowed mode only)."""
        try:
            win = self._base.win
            if win is None:
                return False
            from panda3d.core import Filename
            return bool(win.saveScreenshot(Filename.fromOsSpecific(path)))
        except Exception:
            return False

    # ── level lifecycle (mirrors GUIEngine) ───────────────────────
    def load_level(self, index: int) -> None:
        from levels_data import ALL_LEVELS
        if not 0 <= index < len(ALL_LEVELS):
            raise ValueError(f"Invalid level {index}.")
        self.level_index = index
        self.game_completed = False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self.sync()

    def _restart(self, from_start: bool = False) -> None:
        from levels_data import ALL_LEVELS
        if from_start or self.game_completed:
            self.level_index = 0
            self.game_completed = False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self.sync()

    def _next_level(self) -> bool:
        from levels_data import ALL_LEVELS
        if self.level_index + 1 >= len(ALL_LEVELS):
            self.game_completed = True
            return False
        self.level_index += 1
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        return True

    def _move(self, direction: str) -> None:
        if self.game_completed:
            self.render("All levels complete! Press R to restart, Q to quit.")
            return
        msg = self.level.move_player(direction)
        if self.level.won:
            if not self._next_level():
                self.render("All levels complete! Press R to restart, Q to quit.")
                return
            self.render("Level solved! New level loaded.")
            return
        if self.level.dead:
            self.render(msg + " Press R to restart.")
            return
        self.render(msg)

    def _restart_key(self) -> None:
        self._restart(from_start=self.game_completed)
        self.render("Level restarted.")

    # ── scene sync (full rebuild: levels are small; fx pools persist) ─
    def sync(self) -> None:
        self.world.node().removeAllChildren()
        self._emitters = []
        self._warp_discs = []
        self._warp_lights = []
        self._actor = None
        level = self.level
        for gy in range(level.height):
            for gx in range(level.width):
                self._build_cell(gx, gy)
        # share the spark budget across mines so dense minefields can't
        # saturate the pool (sparks would churn and never visibly rise)
        spark_emitters = [e for e in self._emitters if e["kind"] == "spark"]
        if spark_emitters:
            share = min(24.0, 220.0 / len(spark_emitters))
            for e in spark_emitters:
                e["rate"] = share
        self._build_knight()
        self._frame_camera()
        self._update_hud()

    def _block(self, name: str, model, x: float, y: float, z: float,
               sx: float, sy: float, sz: float, color, tex=None) -> None:
        node = model.copyTo(self.world)
        node.setName(name)
        node.setPos(x, y, z)
        node.setScale(sx, sy, sz)
        node.setColor(color)
        if tex is not None:
            node.setTexture(tex)

    def _build_cell(self, gx: int, gy: int) -> None:
        from panda3d.core import TextNode, TransparencyAttrib
        level = self.level
        x, y = float(gx), float(-gy)
        tile = level.tile_at(gx, gy)
        tcls = tile.__class__.__name__
        is_global = getattr(level, "rule_mode", "circuit") == "global"

        if tcls == "Wall":
            tint = 0.92 + 0.16 * _cell_hash(gx, gy, 11)
            self._block(f"wall_{gx}_{gy}", self._box, x, y, 0.45,
                        1.0, 1.0, 0.9, hex_color("#3b3f5e", tint=tint),
                        tex=self._tex_brick)
        elif tcls == "Goal":
            self._block(f"goal_{gx}_{gy}", self._box, x, y, 0.08,
                        0.9, 0.9, 0.15, hex_color("#2e8f4c"),
                        tex=self._tex_floor)
            # light beam rising off the pad
            beam = self._box.copyTo(self.world)
            beam.setName(f"goalbeam_{gx}_{gy}")
            beam.setPos(x, y, 1.5)
            beam.setScale(0.22, 0.22, 2.8)
            beam.setColor(hex_color("#4adc6e", 0.35))
            beam.setTransparency(TransparencyAttrib.MAlpha)
            beam.setDepthWrite(False)
        else:
            tint = 0.94 + 0.12 * _cell_hash(gx, gy, 21)
            self._block(f"floor_{gx}_{gy}", self._box, x, y, -0.1,
                        1.0, 1.0, 0.2, hex_color("#1b1f3f", tint=tint),
                        tex=self._tex_floor)

        if is_global:
            terr = level.terrain_at(gx, gy)
            if terr is not None:
                occ_name, occ = terr.__class__.__name__, terr
            else:
                occ_name, occ = None, None
            blocks = [level.block_at(gx, gy)]
        else:
            occ = level.object_at(gx, gy)
            occ_name = occ.__class__.__name__ if occ is not None else None
            blocks = []
            if occ_name == "CodeBlock":
                blocks = [occ]

        # Seal2..6 walls share the SealWall look.
        base_name = "SealWall" if (occ_name or "").startswith("Seal") \
            else occ_name
        if base_name in TERRAIN_COLORS:
            solid = True
            try:
                if base_name in ("Door", "Stone", "SealWall", "LatchDoor",
                                 "LaserDoor"):
                    solid = occ.is_blocking()
                elif base_name == "Trap":
                    solid = occ.is_lethal()
            except Exception:
                pass
            metal = self._tex_metal
            if base_name == "Warp":
                self._build_warp(x, y, gx, gy)
            elif base_name in ("HiddenBoom", "HardMine", "BorderMine"):
                self._build_mine(x, y, gx, gy)
            elif base_name == "Trap" and not solid:
                pass  # disarmed trap reads as plain floor
            elif base_name == "LaserDoor" and not solid:
                # dark unpowered posts stay behind
                self._build_laser_posts(x, y, gx, gy, live=False)
            elif base_name == "LaserDoor":
                self._build_laser_posts(x, y, gx, gy, live=True)
                beam = self._box.copyTo(self.world)
                beam.setName(f"laserbeam_{gx}_{gy}")
                beam.setPos(x, y, 0.5)
                beam.setScale(0.55, 0.12, 1.0)
                beam.setColor(hex_color("#ff3b30"))
                beam.setTransparency(TransparencyAttrib.MAlpha)
            elif base_name == "Door":
                self._block(f"prop_{gx}_{gy}", self._box, x, y, 0.35,
                            0.85, 0.85, 0.7,
                            hex_color(TERRAIN_COLORS[base_name]), tex=metal)
                if solid:  # raised wooden panel on the camera face
                    self._block(f"doorpanel_{gx}_{gy}", self._box,
                                x, y - 0.18, 0.35, 0.55, 0.1, 0.5,
                                hex_color("#f5c080"), tex=metal)
            elif base_name == "LatchDoor":
                self._block(f"prop_{gx}_{gy}", self._box, x, y, 0.35,
                            0.85, 0.85, 0.7,
                            hex_color(TERRAIN_COLORS[base_name]), tex=metal)
                if solid:  # gold padlock block
                    self._block(f"latchlock_{gx}_{gy}", self._box,
                                x, y - 0.2, 0.45, 0.22, 0.1, 0.22,
                                hex_color("#ffd45a"), tex=metal)
            elif base_name == "LeverPedestal":
                self._block(f"prop_{gx}_{gy}", self._box, x, y, 0.2,
                            0.7, 0.7, 0.4,
                            hex_color("#5a5e78"), tex=metal)
                try:
                    active = bool(occ.is_active())
                except Exception:
                    active = False
                handle = self._box.copyTo(self.world)
                handle.setName(f"leverarm_{gx}_{gy}")
                handle.setPos(x + (0.14 if active else -0.14), y, 0.55)
                handle.setScale(0.07, 0.07, 0.45)
                handle.setHpr(0, 0, -28 if active else 28)
                handle.setColor(hex_color("#c0c0c0"), )
                knob = self._ball.copyTo(self.world)
                knob.setName(f"leverknob_{gx}_{gy}")
                knob.setPos(x + (0.30 if active else -0.30), y, 0.72)
                knob.setScale(0.11, 0.11, 0.11)
                knob.setColor(hex_color("#d96b1a"))
            elif base_name == "Trap":
                # hot plate + a row of spikes
                self._block(f"prop_{gx}_{gy}", self._box, x, y, 0.06,
                            0.85, 0.85, 0.12, hex_color("#c74555"))
                for i, dx in enumerate((-0.25, 0.0, 0.25)):
                    self._block(f"spike_{gx}_{gy}_{i}", self._box,
                                x + dx, y, 0.2, 0.1, 0.1, 0.3,
                                hex_color("#e05565"))
            else:
                height = 0.7 if solid else 0.15
                self._block(f"prop_{gx}_{gy}", self._box, x, y,
                            height / 2, 0.8, 0.8, height,
                            hex_color(TERRAIN_COLORS[base_name]), tex=metal)

        for blk in blocks:
            if blk is None:
                continue
            self._block(f"block_{gx}_{gy}", self._box, x, y, 0.35,
                        0.7, 0.7, 0.7,
                        hex_color(BLOCK_COLORS.get(blk.kind, "#1a3a6a")),
                        tex=self._tex_metal)
            text = blk.glyph().strip()
            tn = TextNode(f"label_{gx}_{gy}")
            tn.setText(text)
            tn.setTextColor(0.91, 0.94, 1, 1)
            label = self.world.attachNewNode(tn)
            label.setName(f"label_{gx}_{gy}")
            label.setScale(min(0.42, 1.5 / max(1, len(text))))
            label.setBillboardPointEye()
            label.setPos(x - 0.28, y, 1.02)

    def _build_warp(self, x: float, y: float, gx: int, gy: int) -> None:
        from panda3d.core import PointLight, TransparencyAttrib
        disc = self._quad.copyTo(self.world)
        disc.setName(f"warp_{gx}_{gy}")
        disc.setPos(x, y, 0.75)
        disc.setScale(1.15, 1.45, 1.0)
        disc.setHpr(0, 90, 0)  # face -Y (camera side)
        disc.setTexture(self._tex_swirl)
        disc.setTransparency(TransparencyAttrib.MAlpha)
        disc.setDepthWrite(False)
        seed = _cell_hash(gx, gy, 90)
        self._warp_discs.append((disc, seed))
        if len(self._warp_lights) < 4:  # forward-renderer light budget
            pl = PointLight(f"warplight_{gx}_{gy}")
            pl.setColor((0.35, 0.5, 1.0, 1))
            pl.setAttenuation((0.3, 0.0, 0.25))
            lnp = self.world.attachNewNode(pl)
            lnp.setPos(x, y, 1.2)
            self.world.setLight(lnp)
            self._warp_lights.append((lnp, seed))
        self._emitters.append({"kind": "wisp", "pos": (x, y, 0.9),
                               "rate": 7.0, "acc": seed})

    def _build_mine(self, x: float, y: float, gx: int, gy: int) -> None:
        body = self._ball.copyTo(self.world)
        body.setName(f"mine_{gx}_{gy}")
        body.setPos(x, y, 0.3)
        body.setScale(0.32, 0.32, 0.3)
        body.setColor(hex_color("#23262e"))
        fuse = self._box.copyTo(self.world)
        fuse.setName(f"fuse_{gx}_{gy}")
        fuse.setPos(x + 0.22, y, 0.62)
        fuse.setScale(0.42, 0.06, 0.06)
        fuse.setHpr(0, 0, -32)
        fuse.setColor(hex_color("#7a4f2a"))
        self._emitters.append({"kind": "spark",
                               "pos": (x + 0.38, y, 0.78),
                               "rate": 22.0,
                               "acc": _cell_hash(gx, gy, 91)})

    def _build_laser_posts(self, x: float, y: float, gx: int, gy: int,
                           live: bool) -> None:
        for i, dx in enumerate((-0.38, 0.38)):
            self._block(f"laserpost_{gx}_{gy}_{i}", self._box,
                        x + dx, y, 0.45, 0.14, 0.5, 0.9,
                        hex_color("#5a5e78"), tex=self._tex_metal)

    def _build_knight(self) -> None:
        """Primitive-composed hero: legs, plate, arms, helm, sword."""
        p = getattr(self.level, "player", None)
        if p is None:
            return
        root = self.world.attachNewNode("player")
        root.setPos(float(p.x), float(-p.y), 0)
        silver = hex_color("#9aa0b0")
        dark = hex_color("#2e3138")
        bright = hex_color("#d8dce4")
        for name, model, pos, scl, col, tex in (
                ("player-leg-l", self._box, (-0.13, 0, 0.2),
                 (0.16, 0.16, 0.4), dark, None),
                ("player-leg-r", self._box, (0.13, 0, 0.2),
                 (0.16, 0.16, 0.4), dark, None),
                ("player-torso", self._box, (0, 0, 0.62),
                 (0.44, 0.3, 0.5), silver, self._tex_metal),
                ("player-arm-l", self._box, (-0.3, 0, 0.6),
                 (0.13, 0.13, 0.42), silver, None),
                ("player-arm-r", self._box, (0.3, 0, 0.6),
                 (0.13, 0.13, 0.42), silver, None),
                ("player-helm", self._ball, (0, 0, 1.02),
                 (0.24, 0.24, 0.26), bright, None)):
            n = model.copyTo(root)
            n.setName(name)
            n.setPos(*pos)
            n.setScale(*scl)
            n.setColor(col)
            if tex is not None:
                n.setTexture(tex)
        visor = self._box.copyTo(root)
        visor.setName("player-visor")
        visor.setPos(0, -0.21, 1.03)
        visor.setScale(0.3, 0.04, 0.09)
        visor.setColor(hex_color("#0a0a0a"))
        blade = self._box.copyTo(root)
        blade.setName("player-sword")
        blade.setPos(0.36, -0.1, 0.85)
        blade.setScale(0.07, 0.07, 0.95)
        blade.setHpr(0, 18, 0)
        blade.setColor(hex_color("#e8ecf4"), )
        guard = self._box.copyTo(root)
        guard.setName("player-guard")
        guard.setPos(0.35, -0.04, 0.4)
        guard.setScale(0.2, 0.08, 0.06)
        guard.setColor(hex_color("#c46a2a"))
        if self.level.dead:
            root.setColorScale(0.5, 0.16, 0.16, 1)
        self._actor = root
        self._actor_cell = (p.x, p.y)

    def _frame_camera(self) -> None:
        cam = self._base.cam
        if cam is None:
            return  # headless (window-type none): no camera to fit
        cols = max(1, self.level.width)
        rows = max(1, self.level.height)
        cx, cy = (cols - 1) / 2.0, -(rows - 1) / 2.0
        dist = max(cols, rows) * 0.66 + 4.0
        cam.setPos(cx, cy - dist, dist * 0.80)
        cam.lookAt(cx, cy, 0)

    def _update_hud(self) -> None:
        from levels_data import ALL_LEVELS
        num = min(self.level_index + 1, len(ALL_LEVELS))
        if self.game_completed:
            head = f"ALL {len(ALL_LEVELS)} LEVELS COMPLETE!"
        else:
            head = f"Level {num}/{len(ALL_LEVELS)}: {self.level.name}"
        self._hud.setText(f"{head}\nMoves: {self.level.moves}\n"
                          f"WASD/arrows move, R restart, Q quit.\n"
                          f"{self._message}")

    # ── ambient life: particles, portals, knight idle ───────────────
    def _fx_step(self, task) -> object:
        """Panda3D task: emitters, UV scroll, light flicker, idle bob."""
        from panda3d.core import ClockObject, TextureStage
        dt = min(0.05, ClockObject.getGlobalClock().getDt())
        self._fx_t += dt
        rnd = self._rand
        for e in self._emitters:
            e["acc"] += e["rate"] * dt
            while e["acc"] >= 1.0:
                e["acc"] -= 1.0
                px, py, pz = e["pos"]
                if e["kind"] == "spark":
                    warm = rnd.choice(((1, 0.96, 0.78, 1),
                                       (1, 0.83, 0.35, 1),
                                       (1, 0.62, 0.18, 1)))
                    self._sparks.emit(
                        (px + rnd.uniform(-.05, .05),
                         py + rnd.uniform(-.05, .05), pz),
                        (rnd.uniform(-.9, .9), rnd.uniform(-.9, .9),
                         rnd.uniform(1.4, 2.8)),
                        rnd.uniform(.3, .65), rnd.uniform(.03, .06),
                        warm, grav=-4.5)
                else:
                    cool = rnd.choice(((.6, .86, 1, 1), (.39, .4, .95, 1)))
                    self._wisps.emit(
                        (px + rnd.uniform(-.4, .4),
                         py + rnd.uniform(-.4, .4),
                         pz + rnd.uniform(-.3, .3)),
                        (rnd.uniform(-.2, .2), rnd.uniform(-.2, .2),
                         rnd.uniform(.25, .6)),
                        rnd.uniform(1.2, 2.2), rnd.uniform(.04, .08),
                        cool, grav=0.12)
        # ambient dust drifts until the set is full
        if self._dust.alive() < 26 and self.level is not None:
            w, h = self.level.width, self.level.height
            self._dust.emit(
                (rnd.uniform(0, w - 1), rnd.uniform(-h + 1, 0),
                 rnd.uniform(0.1, 0.6)),
                (rnd.uniform(-.15, .15), rnd.uniform(-.15, .15),
                 rnd.uniform(.02, .08)),
                rnd.uniform(2.5, 4.5), rnd.uniform(.05, .1),
                (0.35, 0.37, 0.47, 1))
        self._sparks.step(dt)
        self._wisps.step(dt)
        self._dust.step(dt)
        # portal energy scroll + breathing lights
        stage = TextureStage.getDefault()
        for node, seed in self._warp_discs:
            if node.is_empty():
                continue
            node.setTexOffset(stage, (self._fx_t * 0.22 + seed) % 1.0, 0.0)
        for lnp, seed in self._warp_lights:
            if lnp.is_empty():
                continue
            f = 0.72 + 0.38 * (0.5 + 0.5 * math.sin(self._fx_t * 7.0
                                                   + seed * 9.0))
            lnp.node().setColor((0.35 * f, 0.5 * f, 1.0 * f, 1))
        # knight idle: breath bob, faint rock, footstep dust on arrival
        actor = self._actor
        if actor is not None and not actor.is_empty():
            actor.setZ(0.05 * math.sin(self._fx_t * 3.1))
            actor.setR(2.0 * math.sin(self._fx_t * 1.55))
            p = getattr(self.level, "player", None)
            if p is not None and (p.x, p.y) != self._actor_cell:
                self._actor_cell = (p.x, p.y)
                for _ in range(2):
                    self._dust.emit(
                        (p.x + rnd.uniform(-.2, .2),
                         -p.y + rnd.uniform(-.2, .2), 0.1),
                        (rnd.uniform(-.4, .4), rnd.uniform(-.4, .4),
                         rnd.uniform(.3, .7)),
                        rnd.uniform(.5, .9), rnd.uniform(.05, .09),
                        (0.6, 0.63, 0.74, 1), grav=-0.4)
        return task.cont if task is not None else None
