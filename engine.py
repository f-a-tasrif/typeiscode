"""
engine.py
---------
GameEngine drives the terminal UI: prints the grid + circuit status
each tick, reads a key from the player, and forwards it to the current
Level. Also handles level progression, restart, help and quit commands.
"""

from __future__ import annotations
from levels_data import ALL_LEVELS

HELP_TEXT = """
Controls:
  w/a/s/d  - move up/left/down/right (push code blocks by walking into them)
  r        - restart the current level
  h        - show this help again
  q        - quit the game

How to win:
  - Each level has a workshop with a 4-slot circuit line.
  - The slots are: CLASS PROP = VALUE
  - Push the right block into each slot to form a valid statement.
  - When the circuit compiles, every object of that class updates live.
  - Use the changed behavior to reach the goal tile.
"""


class GameEngine:
    def __init__(self):
        self.level_index = 0
        self.level = ALL_LEVELS[self.level_index]()

    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self):
        self.level = self.current_builder()()
        self.level.reset()

    def next_level(self) -> bool:
        """Advance to the next level. Returns False if the game is finished."""
        self.level_index += 1
        if self.level_index >= len(ALL_LEVELS):
            return False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        return True

    def render_frame(self, message: str = ""):
        print("\n" * 2)
        print(f"=== TYPE IS CODE ===  Level {self.level_index + 1}/{len(ALL_LEVELS)}: {self.level.name}")
        print(f"Moves: {self.level.moves}")
        print()
        print(self.level.render())
        print()
        print("Circuit status:")
        print(self.level.render_circuits())
        print()
        print("Live property registry:")
        print(" " + self.level.render_registry())
        if message:
            print()
            print(">> " + message)
        print()

    def run(self):
        print(HELP_TEXT)
        self.render_frame("Welcome! Rewrite the circuit line to solve the puzzle.")
        while True:
            cmd = input("Move (w/a/s/d, r=restart, h=help, q=quit) > ").strip().lower()
            if cmd == "":
                continue
            if cmd == "q":
                print("Thanks for playing Type Is Code!")
                break
            if cmd == "h":
                print(HELP_TEXT)
                continue
            if cmd == "r":
                self.restart_level()
                self.render_frame("Level restarted.")
                continue
            if cmd not in ("w", "a", "s", "d"):
                print("Unknown command. Press 'h' for help.")
                continue

            msg = self.level.move_player(cmd)

            if self.level.won:
                self.render_frame(msg)
                print(f"Level {self.level_index + 1} solved in {self.level.moves} moves!")
                if not self.next_level():
                    print("\nCongratulations -- you compiled your way through every level!")
                    break
                self.render_frame("New level loaded.")
                continue

            if self.level.dead:
                self.render_frame(msg)
                again = input("You died. Restart level? (y/n) > ").strip().lower()
                if again == "y":
                    self.restart_level()
                    self.render_frame("Level restarted.")
                else:
                    print("Thanks for playing Type Is Code!")
                    break
                continue

            self.render_frame(msg)
