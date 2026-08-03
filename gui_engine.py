
from __future__ import annotations
from graficial import Window
from levels_data import ALL_LEVELS

CELL_SIZE = 64
MIN_CELL_SIZE = 28
BOARD_PADDING = 12
BACKGROUND = "#0f1323"
BOARD_BG = "#161a33"
BOARD_BORDER_COLOR = "#5f7fff"
WALL_COLOR = "#4b4f6e"
FLOOR_COLOR = "#1b1f3f"
GOAL_COLOR = "#2e8f4c"
PLAYER_COLOR = "#f4f874"
PLATFORM_COLOR = "#7b5cff"
PLATFORM_GHOST_COLOR = "#574d87"
DOOR_COLOR = "#d96b3d"
DOOR_OPEN_COLOR = "#f1b56f"
TRAP_COLOR = "#c74555"
TRAP_OFF_COLOR = "#8d5968"
BLOCK_COLOR = "#42a7ff"
TEXT_COLOR = "#f1f2ff"
SEPARATOR_COLOR = "#2f3353"
MESSAGE_BG = "#182046"

SYMBOL_STYLE = {
    "Wall": WALL_COLOR,
    "Floor": FLOOR_COLOR,
    "Goal": GOAL_COLOR,
    "Player": PLAYER_COLOR,
    "Platform": PLATFORM_COLOR,
    "Door": DOOR_COLOR,
    "Trap": TRAP_COLOR,
    "CodeBlock": BLOCK_COLOR,
}


class GUIEngine:
    def __init__(self):
        self.level_index = 0
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self.window = Window("Type Is Code", 1180, 580, bg=BACKGROUND)
        self.canvas = self.window.create_canvas(740, 560, bg=BOARD_BG)
        self.info_frame = self.window.create_frame()
        self.status_label = self.info_frame.add_label("", font=("Courier", 16, "bold"), fg=TEXT_COLOR, bg=BACKGROUND)
        self.moves_label = self.info_frame.add_label("", font=("Courier", 12), fg=TEXT_COLOR, bg=BACKGROUND)
        self.message_label = self.info_frame.add_label("", font=("Courier", 11), fg=TEXT_COLOR, bg=MESSAGE_BG)
        self.info_frame.add_label("Circuit lines", font=("Courier", 13, "bold"), fg=TEXT_COLOR, bg=BACKGROUND)
        self.circuit_view = self.info_frame.add_text_view(width=44, height=12, fg=TEXT_COLOR, bg="#141a33")
        self.info_frame.add_label("Live registry", font=("Courier", 13, "bold"), fg=TEXT_COLOR, bg=BACKGROUND)
        self.registry_view = self.info_frame.add_text_view(width=44, height=4, fg=TEXT_COLOR, bg="#141a33")
        self.info_frame.add_label("Controls", font=("Courier", 13, "bold"), fg=TEXT_COLOR, bg=BACKGROUND)
        self.help_view = self.info_frame.add_text_view(width=44, height=8, fg=TEXT_COLOR, bg="#141a33")
        self.window.on_key_down(self.on_key)
        self.window.focus()
        self.render_frame("Welcome! Press W/A/S/D to move, R to restart, H for help, Q to quit.")

    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self):
        self.level = self.current_builder()()
        self.level.reset()

    def next_level(self) -> bool:
        self.level_index += 1
        if self.level_index >= len(ALL_LEVELS):
            return False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        return True

    def render_frame(self, message: str = ""):
        self.canvas.clear()
        width = self.level.width
        height = self.level.height
        available_width = 720 - 2 * BOARD_PADDING
        available_height = 520 - 2 * BOARD_PADDING
        cell_size = max(
            MIN_CELL_SIZE,
            min(
                CELL_SIZE,
                available_width // width,
                available_height // height,
            ),
        )
        board_width = BOARD_PADDING * 2 + cell_size * width
        board_height = BOARD_PADDING * 2 + cell_size * height
        self.canvas.set_size(board_width, max(board_height, 560))

        self.canvas.draw_rect(0, 0, board_width, max(board_height, 560), fill=BOARD_BG, outline=BOARD_BORDER_COLOR)
        self.canvas.draw_rect(BOARD_PADDING - 2, BOARD_PADDING - 2, board_width - 2 * (BOARD_PADDING - 2), board_height - 2 * (BOARD_PADDING - 2), fill=BOARD_BG, outline=BOARD_BORDER_COLOR)

        # Collect all circuit slot positions for visual highlighting
        circuit_slots = set()
        for circ in self.level.circuits:
            for sp in circ.slot_positions:
                circuit_slots.add(sp)

        for y in range(height):
            for x in range(width):
                px = BOARD_PADDING + x * cell_size
                py = BOARD_PADDING + y * cell_size
                tile = self.level.tile_at(x, y)
                if (x, y) in circuit_slots:
                    fill = "#242d54"
                    outline = "#5f7fff"
                else:
                    fill = SYMBOL_STYLE.get(tile.__class__.__name__, FLOOR_COLOR)
                    outline = SEPARATOR_COLOR
                self.canvas.draw_rect(px, py, cell_size - 2, cell_size - 2, fill=fill, outline=outline)

                occ = self.level.object_at(x, y)
                if self.level.player and self.level.player.x == x and self.level.player.y == y:
                    glyph = "@"
                    fill = PLAYER_COLOR
                    glyph_color = "black"
                elif occ is not None:
                    cls_name = occ.__class__.__name__
                    if cls_name == "Platform":
                        if occ.is_blocking():
                            glyph = "P"
                            fill = PLATFORM_COLOR
                        else:
                            glyph = "p"
                            fill = PLATFORM_GHOST_COLOR
                    elif cls_name == "Door":
                        if occ.is_blocking():
                            glyph = "d"
                            fill = DOOR_COLOR
                        else:
                            glyph = "D"
                            fill = DOOR_OPEN_COLOR
                    elif cls_name == "Trap":
                        if occ.is_lethal():
                            glyph = "t"
                            fill = TRAP_COLOR
                        else:
                            glyph = "T"
                            fill = TRAP_OFF_COLOR
                    elif cls_name == "CodeBlock":
                        glyph = occ.glyph().strip()
                        fill = BLOCK_COLOR
                    else:
                        glyph = occ.glyph().strip() or "?"
                        fill = FLOOR_COLOR
                    glyph_color = "white"
                else:
                    glyph = tile.glyph().strip() or ""
                    glyph_color = "white"

                self.canvas.draw_rect(px, py, cell_size - 2, cell_size - 2, fill=fill, outline=SEPARATOR_COLOR)
                self.canvas.draw_text(px + cell_size // 2, py + cell_size // 2, glyph, fill=glyph_color, anchor="c")

        self.status_label.configure(text=f"Level {self.level_index + 1}/{len(ALL_LEVELS)}: {self.level.name}")
        self.moves_label.configure(text=f"Moves: {self.level.moves}")
        self.message_label.configure(text=message or "Ready for your next move.")
        self.circuit_view.set_text(self.level.render_circuits())
        self.registry_view.set_text(self.level.render_registry())
        self.help_view.set_text(
            "W/A/S/D = move\n"
            "R = restart\n"
            "H = help\n"
            "Q = quit\n\n"
            "Goal: arrange the circuit blocks so the statement compiles to the\n"
            "correct class property assignment. Valid circuits are: CLASS PROP = VALUE.\n"
            "Once a circuit is valid, all objects of that class update live."
        )

    def on_key(self, key: str):
        if key == "q":
            self.window.root.destroy()
            return
        if key == "h":
            self.render_frame("Press H to show help. Use arrow keys W/A/S/D.")
            return
        if key == "r":
            self.restart_level()
            self.render_frame("Level restarted.")
            return
        if key not in ("w", "a", "s", "d"):
            return

        msg = self.level.move_player(key)
        if self.level.won:
            self.render_frame(msg + " You solved the level!")
            if not self.next_level():
                self.render_frame("Congratulations! You completed all levels.")
                return
            self.render_frame("New level loaded.")
            return
        if self.level.dead:
            self.render_frame(msg + " Game over. Press R to restart.")
            return
        self.render_frame(msg)

    def run(self):
        self.window.run()
