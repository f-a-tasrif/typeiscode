"""tests/test_menu_scene.py -- animated menu pure logic (headless)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from menu_scene import (  # noqa: E402
    CONSOLE_CYCLE_S, FUSE_BURN_S, FUSE_FLASH_S, FUSE_MIN, FUSE_START,
    MAX_DT, advance_particles, bezier, clamp_dt, console_flicker,
    console_program, fuse_flashing, fuse_length, load_settings,
    make_particle, menu_layout, polyline_length, portal_pulse,
    walk_polyline,
)


def test_layout_scales():
    small = menu_layout(800, 600)
    big = menu_layout(1600, 1200)
    assert small["knight"][0] == 400 and big["knight"][0] == 800
    assert big["title"][0] == 2 * small["title"][0]
    assert big["menu_y"] == 2 * small["menu_y"]
    assert small["portal_l"][2] * 2 == big["portal_l"][2]


def test_clamp_dt():
    assert clamp_dt(-1.0) == 0.0
    assert clamp_dt(10.0) == MAX_DT
    assert clamp_dt(0.016) == 0.016


def test_fuse_shortens_then_resets():
    assert fuse_length(0.0) == FUSE_START
    assert fuse_length(1.0) < FUSE_START
    assert fuse_length(FUSE_BURN_S - 0.01) > FUSE_MIN
    assert fuse_length(FUSE_BURN_S + 0.1) == FUSE_MIN
    assert abs(fuse_length(FUSE_BURN_S + FUSE_FLASH_S + 0.01)
               - FUSE_START) < 0.01  # fresh fuse after the relight
    assert not fuse_flashing(1.0)
    assert fuse_flashing(FUSE_BURN_S + 0.1)
    assert not fuse_flashing(FUSE_BURN_S + FUSE_FLASH_S + 0.01)


def test_console_cycles():
    assert console_program(0.0) == 0
    assert console_program(CONSOLE_CYCLE_S) == 1
    assert console_program(CONSOLE_CYCLE_S * 4) == 0
    assert isinstance(console_flicker(1.23, 0), bool)


def test_particles_advance():
    p = make_particle(10, 20, 100, -50, 1.0, 2, "#fff", grav=10)
    out = advance_particles([p], 0.5)
    assert len(out) == 1
    assert out[0]["x"] == 60
    assert out[0]["y"] == -2.5  # vy += grav*dt first, then y += vy*dt
    assert out[0]["life"] == 0.5
    assert advance_particles([p], 1.5) == []


def test_bezier_endpoints():
    p0, p1, p2 = (0, 0), (5, 10), (10, 0)
    assert bezier(p0, p1, p2, 0.0) == (0, 0)
    assert bezier(p0, p1, p2, 1.0) == (10, 0)
    mx, my = bezier(p0, p1, p2, 0.5)
    assert (mx, my) == (5.0, 5.0)


def test_walk_polyline():
    pts = [(0, 0), (10, 0), (10, 10)]
    assert walk_polyline(pts, 0) == (0, 0)
    assert walk_polyline(pts, 5) == (5, 0)
    assert walk_polyline(pts, 15) == (10, 5)
    assert walk_polyline(pts, 999) == (10, 10)
    assert polyline_length(pts) == 20


def test_portal_pulse_range():
    for t in (0.0, 0.7, 2.5, 10.0):
        v = portal_pulse(t)
        assert 0.0 <= v <= 1.0, v


def test_load_settings_keys():
    s = load_settings()
    assert set(s) == {"particles", "fullscreen"}


def test_menu_nav_wraps():
    from menu_scene import MainMenuScene  # noqa: E402
    sc = MainMenuScene()
    n = len(sc.items)
    sc.sel = 0
    sc.on_key("left")
    assert sc.sel == n - 1
    sc.on_key("right")
    assert sc.sel == 0


def test_title_text_fixed():
    from menu_scene import TITLE_TEXT  # noqa: E402
    assert TITLE_TEXT == "TYPE IS CODE"


def test_load_game_toast_without_saves():
    from menu_scene import MainMenuScene  # noqa: E402
    sc = MainMenuScene()  # no on_load wired: no save system yet
    sc.activate(1)
    assert sc.items[1] == "LOAD GAME"
    assert sc.toast != ""


if __name__ == "__main__":
    tests = [test_layout_scales, test_clamp_dt, test_fuse_shortens_then_resets,
             test_console_cycles, test_particles_advance,
             test_bezier_endpoints, test_walk_polyline,
             test_portal_pulse_range, test_load_settings_keys,
             test_menu_nav_wraps, test_title_text_fixed,
             test_load_game_toast_without_saves]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
