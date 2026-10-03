"""tests/test_panda_view.py -- Panda3D graybox view (headless)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from view import GameView  # noqa: E402

VIEW = None


def get_view():
    global VIEW
    if VIEW is None:
        from panda_app import PandaView  # noqa: E402
        VIEW = PandaView(start_index=0, headless=True)
    return VIEW


def test_implements_view():
    from panda_app import PandaView  # noqa: E402
    assert issubclass(PandaView, GameView)
    assert not getattr(PandaView, "__abstractmethods__", set())


def test_board_covers_every_cell():
    v = get_view()
    w, h = v.level.width, v.level.height
    floors = len(v.world.findAllMatches("floor_*"))
    walls = len(v.world.findAllMatches("wall_*"))
    goals = len(v.world.findAllMatches("goal_*"))
    assert floors + walls + goals == w * h, (floors, walls, goals, w, h)


def test_player_node_tracks_level():
    v = get_view()
    p = v.level.player
    found = v.world.findAllMatches("player")
    assert len(found) == 1
    pos = found[0].getPos()
    assert (round(pos.x), round(-pos.y)) == (p.x, p.y)


def test_blocks_have_labels():
    from levels_data import ALL_LEVELS  # noqa: E402
    v = get_view()
    target = None
    for i in range(len(ALL_LEVELS)):
        lv = ALL_LEVELS[i]()
        lv.reset()
        if any(lv.block_at(x, y) is not None
               for y in range(lv.height) for x in range(lv.width)):
            target = i
            break
    assert target is not None, "no level carries code blocks"
    v.load_level(target)
    blocks = v.world.findAllMatches("block_*")
    labels = v.world.findAllMatches("label_*")
    assert len(blocks) > 0
    assert len(labels) == len(blocks)


def test_move_syncs_player_node():
    v = get_view()
    v.load_level(0)
    m0 = v.level.moves
    for direction in ("d", "s", "a", "w"):
        v._move(direction)
        if v.level.moves > m0:
            break
    assert v.level.moves > m0, "no direction moved the player"
    p = v.level.player
    pos = v.world.findAllMatches("player")[0].getPos()
    assert (round(pos.x), round(-pos.y)) == (p.x, p.y)


def test_headless_screenshot_is_false():
    v = get_view()
    assert v.screenshot(os.path.join("C:", "nope.png")) is False


def _first_level_with(predicate):
    from levels_data import ALL_LEVELS  # noqa: E402
    for i in range(len(ALL_LEVELS)):
        lv = ALL_LEVELS[i]()
        lv.reset()
        cells = [(x, y) for y in range(lv.height) for x in range(lv.width)]
        if any(predicate(lv, x, y) for x, y in cells):
            return i
    return None


def _occ_name(lv, x, y):
    if getattr(lv, "rule_mode", "circuit") == "global":
        terr = lv.terrain_at(x, y)
        blks = [lv.block_at(x, y)]
    else:
        terr = lv.object_at(x, y)
        blks = []
    name = terr.__class__.__name__ if terr is not None else None
    if name is not None and name.startswith("Seal"):
        name = "SealWall"
    return name, blks


def test_textures_and_pools_exist():
    v = get_view()
    for tex in (v._tex_brick, v._tex_floor, v._tex_metal, v._tex_swirl):
        assert tex is not None
    assert (v._sparks.cap, v._wisps.cap, v._dust.cap) == (140, 70, 70)
    assert isinstance(v._shadows, bool)


def test_knight_is_composed():
    v = get_view()
    v.load_level(0)
    root = v.world.find("player")
    assert not root.is_empty()
    parts = root.findAllMatches("player-*")
    assert len(parts) >= 8, len(parts)  # limbs, helm, visor, sword, guard
    assert not v.world.find("**/player-sword").is_empty()


def test_mines_carry_fuses_and_emitters():
    v = get_view()
    idx = _first_level_with(
        lambda lv, x, y: _occ_name(lv, x, y)[0]
        in ("HiddenBoom", "HardMine", "BorderMine"))
    assert idx is not None, "no level carries mines"
    v.load_level(idx)
    mines = [n for n in v.world.findAllMatches("mine_*")
             if not n.getName().startswith("mine_fuse")]
    fuses = v.world.findAllMatches("fuse_*")
    assert len(mines) > 0 and len(fuses) == len(mines)
    assert any(e["kind"] == "spark" for e in v._emitters)


def test_warps_have_discs_lights_and_wisps():
    v = get_view()
    idx = _first_level_with(lambda lv, x, y: _occ_name(lv, x, y)[0] == "Warp")
    assert idx is not None, "no level carries a warp"
    v.load_level(idx)
    assert len(v.world.findAllMatches("warp_*")) > 0
    assert len(v._warp_lights) <= 4
    assert any(e["kind"] == "wisp" for e in v._emitters)


def test_fx_step_emits_sparks():
    v = get_view()
    idx = _first_level_with(
        lambda lv, x, y: _occ_name(lv, x, y)[0]
        in ("HiddenBoom", "HardMine", "BorderMine"))
    v.load_level(idx if idx is not None else 0)
    assert v._emitters, "expected emitters on a mine level"
    v._emitters[0]["acc"] = 5.0  # force a burst regardless of clock dt
    v._fx_step(None)
    assert v._sparks.alive() + v._wisps.alive() > 0


if __name__ == "__main__":
    tests = [test_implements_view, test_board_covers_every_cell,
             test_player_node_tracks_level, test_blocks_have_labels,
             test_move_syncs_player_node, test_headless_screenshot_is_false,
             test_textures_and_pools_exist, test_knight_is_composed,
             test_mines_carry_fuses_and_emitters,
             test_warps_have_discs_lights_and_wisps,
             test_fx_step_emits_sparks]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    try:
        if VIEW is not None:
            VIEW.close()
    except Exception:
        pass
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
