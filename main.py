import argparse
import sys

try:
    from gui_engine import GUIEngine
except ImportError:
    GUIEngine = None

from engine import GameEngine
from levels_data import ALL_LEVELS


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Type Is Code - start at a specific level."
    )
    parser.add_argument(
        "-l", "--level",
        type=int,
        default=1,
        help="Level number to start at (1-%d). Default: 1." % len(ALL_LEVELS),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available levels and exit.",
    )
    return parser.parse_args(argv)


def list_levels():
    for i, builder in enumerate(ALL_LEVELS, start=1):
        try:
            name = builder().name
        except Exception:
            name = builder.__name__
        print("%d: %s" % (i, name))


def main(argv=None):
    args = parse_args(argv)

    if args.list:
        list_levels()
        return

    if not 1 <= args.level <= len(ALL_LEVELS):
        print(
            "Invalid level %s. Choose 1-%d." % (args.level, len(ALL_LEVELS)),
            file=sys.stderr,
        )
        sys.exit(2)

    start_index = args.level - 1

    if GUIEngine is not None:
        try:
            GUIEngine(start_index=start_index).run()
            return
        except Exception as exc:
            print("GUI unavailable, falling back to terminal mode:", exc)

    engine = GameEngine(start_index=start_index)
    try:
        engine.run()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
