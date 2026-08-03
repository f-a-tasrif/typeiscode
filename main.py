try:
    from gui_engine import GUIEngine
except ImportError:
    GUIEngine = None

from engine import GameEngine


def main():
    if GUIEngine is not None:
        try:
            GUIEngine().run()
            return
        except Exception as exc:
            print("GUI unavailable, falling back to terminal mode:", exc)

    engine = GameEngine()
    try:
        engine.run()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
