"""tests/test_view.py -- GameView seam contract (headless)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from view import GameView, NullView  # noqa: E402


def test_interface_is_abstract():
    try:
        GameView()
    except TypeError:
        pass
    else:
        raise AssertionError("GameView must not instantiate directly")
    assert set(GameView.__abstractmethods__) == {"render", "run", "close"}


def test_null_view_contract():
    v = NullView()
    v.render("hi")
    v.render()
    v.run()
    assert v.renders == ["hi", ""]
    assert v.ran and not v.closed
    v.close()
    assert v.closed


def test_guiengine_implements_view():
    # No window is opened: subclass + resolved abstractmethods only.
    from gui_engine import GUIEngine  # noqa: E402
    assert issubclass(GUIEngine, GameView)
    assert not getattr(GUIEngine, "__abstractmethods__", set())
    for name in ("render", "run", "close", "on_key"):
        assert callable(getattr(GUIEngine, name, None)), name


def test_null_view_drives_level():
    # The seam direction: logic runs headless, the view only records.
    from levels_data import ALL_LEVELS  # noqa: E402
    level = ALL_LEVELS[0]()
    level.reset()
    v = NullView()
    v.render("start")
    m0 = level.moves
    for direction in ("d", "s", "a", "w"):
        level.move_player(direction)
    assert level.moves >= m0
    v.render("moved")
    assert v.renders == ["start", "moved"]


if __name__ == "__main__":
    tests = [test_interface_is_abstract, test_null_view_contract,
             test_guiengine_implements_view, test_null_view_drives_level]
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
