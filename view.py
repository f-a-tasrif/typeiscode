"""view.py — renderer seam (Phase 0 of the 3D port).

The game logic (level.py / blocks.py / registry.py) never draws; a
*view* reads level state and paints it, and forwards input back via
`Level.move_player`.  Every renderer -- Tkinter today, Panda3D
tomorrow -- implements GameView, so the port replaces views without
touching logic:

    logic  ──reads──▶  GameView.render(level state)
    player ──input──▶  GameView ──move_player()──▶ logic

NullView is the headless member of the family: it records renders and
opens no window, so tests can drive the contract without a display.
"""

from __future__ import annotations

import abc


class GameView(abc.ABC):
    """Output + lifecycle contract every renderer implements."""

    @abc.abstractmethod
    def render(self, message: str = "") -> None:
        """Paint the current level state (plus an optional message)."""

    @abc.abstractmethod
    def run(self) -> None:
        """Enter the renderer's event loop (blocking)."""

    @abc.abstractmethod
    def close(self) -> None:
        """Shut the renderer down (cancel clocks, destroy windows)."""


class NullView(GameView):
    """Headless view: records renders, never opens a window."""

    def __init__(self):
        self.renders: list = []
        self.ran = False
        self.closed = False

    def render(self, message: str = "") -> None:
        self.renders.append(message)

    def run(self) -> None:
        self.ran = True

    def close(self) -> None:
        self.closed = True
