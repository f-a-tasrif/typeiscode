
from __future__ import annotations
import tkinter as tk

from graficial import Window
from levels_data import ALL_LEVELS
from registry import PropertyRegistry
from tile_renderer import (
    draw_wall, draw_floor, draw_goal, draw_player,
    draw_void,
    draw_door_closed, draw_door_open,
    draw_trap_lethal, draw_trap_safe,
    draw_boom_explosion,
    draw_ash,
    draw_skeleton,
    draw_code_block,
    draw_stone,
    draw_laser, draw_lever,
    draw_latch_closed, draw_latch_open,
    draw_seal_wall, draw_warp, draw_mine,
    get_canvas_photo, get_panel_photo, get_panel_slice,
    advance_trap_animation, _tagged, SEAL_SHEET_COL,
)
from multiplayer.race import (Standing, compute_standings, fmt_time,
                              board_lines)


BACKGROUND     = "#0f1323"
PANEL_BG       = "#0d0a1a"
PANEL_SECTION  = "#1a0f2e"
TEXT_COLOR      = "#f0e6c0"
TEXT_BODY       = "#d9defa"
TEXT_DIM        = "#9a8860"
ACCENT         = "#c8a84b"
SUCCESS_COLOR   = "#f0d060"
DANGER_COLOR    = "#e05565"
SEPARATOR_COLOR = "#c8a84b"
SECTION_TEXT_BG = "#12091e"
SECTION_TEXT_FG = "#d4c090"

FONT_HEADING  = ("Georgia", 13, "bold")
FONT_BODY     = ("Georgia", 11)
FONT_CODE     = ("Courier New", 11)
FONT_CODE_SM  = ("Courier New", 10)
FONT_FALLBACK = ("Consolas", 11)


BOARD_BG       = "#0e1225"
BOARD_BORDER   = "#3a4a80"
BOARD_PADDING  = 8





CAM_VIEW_COLS  = 20
CAM_VIEW_ROWS  = 13
CAM_MAX_CELL   = 56
CAM_MIN_CELL   = 8
TARGET_FPS     = 120
CAM_FRAME_MS   = 8
RESIZE_DEBOUNCE_MS = 60
CAM_LERP       = 0.35
CAM_EPS        = 0.03
CAM_ZOOM_LERP  = 0.35
CAM_ZOOM_EPS   = 0.01
CAM_ZOOM_MIN   = 0.2
CAM_ZOOM_MAX   = 2.0





LEVEL_HINTS = [
"",

"",

"",

"",

"",

"",

"",

"",

"Access meets a point to let you inside,\n"
"Add a turn to that place where pathways collide.\n"
"Two simple pieces, when joined side by side,\n"
"Reveal what swings open to welcome the ride.\n",

"The shadows fall across the night,\n"
    "And wrap the weary in their might,\n"
    "Yet if beacon is lit a new hope of escape comes shining bright,\n"
    "To guide our freedom through the dark and out of sight.\n",

"1. There lies hidden bombs,\n"
        "where the player must succumb,\n"
        "discovers a path without turning into crumbs.\n"
    "2. Two meaningful blocks can be fused into one.\n",
]


HELP_PANEL_TEXT = (
    "── CONTROLS ──────────────────\n"
    "WASD / ↑↓←→  → move & push\n"
    "R            → restart level\n"
    "C            → centre camera\n"
    "+  /  -      → zoom in / out\n"
    "0 / F        → fit full map\n"
    "M            → mute toggle\n"
    "[ / ]        → volume down/up\n"
    "Q            → quit\n"
    
)


SFX_EXPLOSION = "assets/sfx_explosion.mp3"
SFX_STONE     = "assets/sfx_stone.mp3"
SFX_DOOR      = "assets/sfx_door.mp3"
BOOM_BLAST_MS = 750


class GUIEngine:




    _MSG_ROWS = 3


    def __init__(self, start_index: int = 0, race=None, audio=None):
        if not 0 <= start_index < len(ALL_LEVELS):
            raise ValueError(f"Invalid start_index {start_index}. Choose 0-{len(ALL_LEVELS) - 1}.")
        self.level_index = start_index
        self.game_completed = False
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()

        self.audio = audio
        self._volume_pct = 80

        self.race = race
        self._race_over = False
        self._race_time_up = False
        self._race_job = None
        self._race_levels = 0
        self._race_moves = 0
        self._race_restarts = 0
        self._race_standings: list[Standing] = []
        self._race_ends_at: float | None = None
        self._final_popup_shown = False



        self._boom_anim: dict | None = None
        self._goal_entry_frame = 0
        self._goal_entry_job = None
        self._goal_entry_speed = 180
        self._last_player_pos = None
        self._last_push_frame = -1
        self._last_anim_frame = -1
        if race is not None:
            import time as _time
            self._race_ends_at = _time.time() + float(race.get("duration_s", 600))
        self._last_message = ""
        self._show_warps = True
        self._label_photos: dict[str, object] = {}
        self._panel_bg_key = None




        self._zoom = 1.0
        self._zoom_cur = 1.0
        self._cam_cx: float | None = None
        self._cam_cy: float | None = None
        self._cam_anim: str | None = None
        self._panel_cache: tuple | None = None

        self._resize_pending: str | None = None
        self._last_win_size: tuple[int, int] | None = None
        self._last_render_ms: float = 0.0



        self._board_geom = None
        self._cell_sigs: dict[tuple[int, int], tuple] = {}



        self._trap_in_view = False
        self._last_trap_frame = -1


        self.window = Window("Type Is Code", 1280, 680, bg=BACKGROUND,
                             min_width=980, min_height=560)
        self.canvas = self.window.create_canvas(bg=BOARD_BG)
        self._build_info_panel()
        self._sync_mute_button()


        self.window.on_key_down(self.on_key)
        self.window.on_resize(self._on_resize)
        self.window.focus()


        self.window.root.after(50, lambda: self.render_frame(self._last_message))
        if self.race is not None:
            self._race_report()
            self.window.root.after(500, self._race_tick)

    def _build_info_panel(self):
        self.info_frame = self.window.create_frame(width=430, bg=PANEL_BG)

        self.status_label = self.info_frame.add_label(
            "", font=FONT_HEADING, fg=TEXT_COLOR, bg=PANEL_BG,
            wraplength=405)
        self.moves_label = self.info_frame.add_label(
            "", font=FONT_BODY, fg=TEXT_DIM, bg=PANEL_BG)
        self.sep_status = self._panel_sep()

        self.race_title = self.info_frame.add_label(
            "", font=FONT_HEADING, fg=ACCENT, bg=PANEL_BG)
        self.race_view = self.info_frame.add_text_view(
            width=44, height=9, font=FONT_CODE,
            fg=SECTION_TEXT_FG, bg=SECTION_TEXT_BG)
        self.race_title.pack_forget()
        try:
            self.race_view._text.pack_forget()
        except Exception:
            pass

        self.message_label = self.info_frame.add_label(
            "", font=FONT_BODY, fg=TEXT_BODY, bg=PANEL_BG,
            wraplength=405)






        _v_inset = 2 * (int(self.message_label.cget("pady"))
                        + int(self.message_label.cget("bd"))
                        + int(self.message_label.cget("highlightthickness")))
        self.message_label.configure(text="X")
        self._msg_line_px = max(
            1, self.message_label.winfo_reqheight() - _v_inset)
        self.message_label.configure(text="\n" * (self._MSG_ROWS - 1))
        self.sep_circuit = self._panel_sep()

        self.controls_label = self.info_frame.add_label(
            "🎮 Controls", font=FONT_HEADING,
            fg=ACCENT, bg=PANEL_BG)
        self.help_view = self.info_frame.add_text_view(
            width=44, height=7, font=FONT_CODE_SM,
            fg=SECTION_TEXT_FG, bg=SECTION_TEXT_BG)
        self.sep_registry = self._panel_sep()

        self.hints_label = self.info_frame.add_label(
            "💡 HINTS", font=FONT_HEADING,
            fg=ACCENT, bg=PANEL_BG)
        self.hints_view = self.info_frame.add_text_view(
            width=44, height=8, font=FONT_BODY,
            fg=SECTION_TEXT_FG, bg=SECTION_TEXT_BG)



        self.help_view.set_text(HELP_PANEL_TEXT)
        self._last_hint: str | None = None

        self.sep_volume = self._panel_sep()
        self.volume_scale = tk.Scale(
            self.info_frame.widget, from_=0, to=100,
            orient="horizontal", label="🔊 Volume",
            font=("Consolas", 11), bg=PANEL_BG, fg=TEXT_COLOR,
            troughcolor="#2a1f3d", activebackground=ACCENT,
            highlightthickness=0, relief="flat", bd=0,
            command=self._on_volume_change)
        self.volume_scale.set(self._volume_pct)
        self.volume_scale.pack(fill="x", padx=12, pady=(4, 2))
        self.volume_scale.bind("<ButtonRelease-1>", self._on_volume_change)
        self.volume_scale.bind("<Motion>", self._on_volume_change)
        self.mute_button = tk.Button(
            self.info_frame.widget, text="🔇 Mute",
            command=self._on_mute_toggle,
            font=("Consolas", 12, "bold"), fg=TEXT_COLOR, bg=PANEL_SECTION,
            activebackground=ACCENT, activeforeground=PANEL_BG,
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2")
        self.mute_button.pack(anchor="w", padx=12, pady=(2, 8))


    def _panel_sep(self):
        sep = tk.Frame(self.info_frame.widget, height=1, bg="#c8a84b")
        sep.pack(fill="x", padx=12, pady=6)
        return sep


    def _on_volume_change(self, val):
        # Handle both scale command callback (string value) and direct calls (int/float)
        if hasattr(val, "widget"):
            event = val
            # Only process ButtonRelease and actual value changes, ignore drag motion without click
            if event.type == "Motion" and not (int(getattr(event, "state", 0)) & 0x100):
                return
            try:
                val = event.widget.get()
            except Exception:
                return
        pct = self._clamp_volume(val)
        if pct is None:
            return
        self._volume_pct = pct
        if self.audio is not None:
            self.audio.set_volume(pct / 100.0)

    def _clamp_volume(self, val) -> int | None:
        try:
            pct = int(round(float(val)))
        except (TypeError, ValueError):
            return None
        return max(0, min(100, pct))

    def _bump_volume(self, delta: int):
        pct = self._clamp_volume(self._volume_pct + delta)
        if pct is None:
            return
        self._volume_pct = pct
        try:
            self.volume_scale.set(pct)
        except Exception:
            pass
        if self.audio is not None:
            self.audio.set_volume(pct / 100.0)
        self.render_frame(f"Volume {pct}%.")

    def _on_mute_toggle(self):
        if self.audio is None:
            self.render_frame("Audio is off (no backend available).")
            return
        muted = self.audio.toggle_mute()
        self._sync_mute_button(muted)
        self.render_frame("Sound " + ("muted." if muted else "on."))

    def _sync_mute_button(self, muted: bool | None = None):
        button = getattr(self, "mute_button", None)
        if button is None:
            return
        if muted is None:
            muted = self.audio.is_muted() if self.audio is not None else False
        try:
            button.configure(text="🔊 Unmute" if muted else "🔇 Mute")
        except Exception:
            pass


    def current_builder(self):
        return ALL_LEVELS[self.level_index]

    def restart_level(self, from_start: bool = False):
        if from_start or self.game_completed:
            self.level_index = 0
            self.game_completed = False
        self._boom_anim = None
        try:
            if self._goal_entry_job is not None:
                self.window.root.after_cancel(self._goal_entry_job)
        except Exception:
            pass
        self._goal_entry_job = None
        self._goal_entry_frame = 0
        self._last_player_pos = None
        self._last_push_frame = -1
        self._last_anim_frame = -1
        self._cancel_camera_anim()
        self.level = self.current_builder()()
        self.level.reset()
        self._snap_camera_to_player()

    def next_level(self) -> bool:
        if self.level_index + 1 >= len(ALL_LEVELS):
            self.game_completed = True
            return False
        self._boom_anim = None
        self._last_player_pos = None
        self._last_push_frame = -1
        self._last_anim_frame = -1
        self._cancel_camera_anim()
        self.level_index += 1
        self.level = ALL_LEVELS[self.level_index]()
        self.level.reset()
        self._snap_camera_to_player()
        return True


    def _play_sfx(self, path: str):
        try:
            audio = getattr(self, "audio", None)
            fn = getattr(audio, "play_sfx", None) if audio is not None else None
            if callable(fn):
                fn(path)
        except Exception:
            pass

    def _draw_mine_aftermath(self, cv, px, py, cell, fast=False):
        try:
            phase = (self._boom_anim or {}).get("phase")
        except Exception:
            phase = None
        if phase == "blast":
            draw_boom_explosion(cv, px, py, cell, fast=fast)
        else:
            draw_ash(cv, px, py, cell, fast=fast)

    def _draw_goal_cell(self, cv, gx, gy, px, py, cell, fast=False):
        try:
            p = self.level.player
            if self._goal_entry_frame > 0 and p is not None and (p.x, p.y) == (gx, gy):
                draw_goal(cv, px, py, cell, fast=fast, entry_frame=self._goal_entry_frame, player_inside=True)
                return
        except Exception:
            pass
        draw_goal(cv, px, py, cell, fast=fast)

    def _player_on_goal_art(self):
        try:
            p = self.level.player
            if p is None:
                return False
            pos = (p.x, p.y)
            if self.level.tile_at(*pos).__class__.__name__ == "Goal":
                return not bool(PropertyRegistry.get("Flag", "moved", False))
            if bool(PropertyRegistry.get("Flag", "moved", False)) and getattr(self.level, "flag2", None) == pos:
                return True
            if bool(PropertyRegistry.get("Gate", "at", False)) and getattr(self.level, "gate2", None) == pos:
                return True
            if bool(PropertyRegistry.get("Beacon", "lit", False)) and getattr(self.level, "beacon2", None) == pos:
                return True
            return False
        except Exception:
            return False

    def _render_board_only(self):
        self.render_frame(self._last_message, board_only=True)

    def _start_goal_entry_animation(self):
        self._goal_entry_frame = 1
        self._render_board_only()
        def _next_frame():
            try:
                self._goal_entry_frame += 1
                self._render_board_only()
                if self._goal_entry_frame < 3:
                    self._goal_entry_job = self.window.root.after(self._goal_entry_speed, _next_frame)
                else:
                    self._goal_entry_job = self.window.root.after(self._goal_entry_speed, self._finish_win)
            except Exception:
                pass
        self._goal_entry_job = self.window.root.after(self._goal_entry_speed, _next_frame)

    def _finish_win(self):
        self._goal_entry_frame = 0
        self._goal_entry_job = None
        if not self.next_level():
            self.render_frame(
                "🎉 Congratulations!  You compiled your way through every level!  "
                "Press R to play again or Q to quit.")
            return
        self.render_frame("Level solved!  New level loaded.")


    def _race_is_host(self) -> bool:
        return self.race is not None and self.race.get("role") == "host"

    def _race_report(self):
        if self.race is None:
            return
        try:
            if self._race_is_host():
                self.race["net"].race_update(
                    self.race.get("name", "Host"),
                    self._race_levels, self._race_moves, self._race_restarts)
                self._race_refresh_from_host()
            else:
                self.race["net"].send_progress(
                    self._race_levels, self._race_moves, self._race_restarts)
        except Exception:
            pass

    def _race_refresh_from_host(self):
        try:
            self._race_standings = compute_standings(
                self.race["net"].race)
        except Exception:
            pass

    def _fmt_standings_table(self, standings: list) -> str:
        if not standings:
            return "  Waiting for players…"
        glyphs = ["①", "②", "③", "④", "⑤"]
        lines = ["%-4s  %-12s  %3s   %5s" % ("RANK", "NAME", "LVL", "MOVES"),
                 "%-4s  %-12s  %3s   %5s" % ("────", "────────────",
                                             "───", "─────")]
        for i, s in enumerate(standings):
            glyph = glyphs[i] if i < 5 else "%d." % (i + 1)
            try:
                name = str(s.name)
            except Exception:
                name = "?"
            if len(name) > 12:
                name = name[:11] + "…"
            try:
                lvl = int(s.levels)
            except Exception:
                lvl = 0
            try:
                mov = int(s.moves)
            except Exception:
                mov = 0
            lines.append("%-4s  %-12s  %3d   %5d" % (glyph, name, lvl, mov))
        return "\n".join(lines)

    def _race_text(self) -> str:
        return self._fmt_standings_table(self._race_standings)

    def _cancel_race_tick(self):
        job, self._race_job = self._race_job, None
        if job is not None:
            try:
                self.window.root.after_cancel(job)
            except Exception:
                pass

    def _race_drain_events(self) -> bool:
        if self.race is None:
            return False
        net = self.race.get("net")
        changed = False
        if self._race_is_host():
            try:
                while True:
                    try:
                        kind, _payload = net.events.get_nowait()
                    except Exception:
                        break
                    if kind in ("join", "leave", "race_progress"):
                        changed = True
                    elif kind == "race_end":
                        try:
                            rows = _payload.get("standings", [])
                            self._race_standings = [Standing(**r) for r in rows]
                        except Exception:
                            pass
                        self._race_over = True
                        changed = True
            except Exception:
                pass
            if changed and not self._race_over:
                self._race_refresh_from_host()
            return changed
        try:
            while True:
                try:
                    kind, payload = net.events.get_nowait()
                except Exception:
                    break
                if kind == "race_board":
                    try:
                        rows = payload.get("standings", []) if isinstance(payload, dict) else []
                        self._race_standings = [Standing(**r) for r in rows]
                    except Exception:
                        pass
                    changed = True
                elif kind == "race_end":
                    try:
                        rows = payload.get("standings", []) if isinstance(payload, dict) else []
                        self._race_standings = [Standing(**r) for r in rows]
                    except Exception:
                        pass
                    self._race_over = True
                    self._race_time_up = False
                    changed = True
                elif kind == "disconnected":
                    self._last_message = "Lost connection to host."
                    changed = True
        except Exception:
            pass
        return changed

    def _race_tick(self):
        self._race_job = None
        if self.race is None:
            return
        try:
            import time as _time
            changed = self._race_drain_events()
            now = _time.time()
            if not self._race_over and self._race_ends_at is not None \
                    and now >= self._race_ends_at:
                if self._race_is_host():
                    self._race_report()
                    try:
                        self.race["net"].end_race()
                    except Exception:
                        pass
                    changed = self._race_drain_events() or changed
                else:
                    self._race_time_up = True
                    changed = True
            if self.race is not None and (self._race_over or self._race_time_up) \
                    and not self._final_popup_shown:
                self._final_popup_shown = True
                self._show_final_standings_popup()
            try:
                if self._race_over:
                    self.race_title.configure(text="RACE OVER")
                elif self._race_time_up:
                    self.race_title.configure(text="TIME! 00:00")
                else:
                    self.race_title.configure(
                        text="Timer: %s Minute left" % fmt_time(self._race_ends_at - now))
            except Exception:
                pass
            if changed:
                self.render_frame(self._last_message)
            self._race_job = self.window.root.after(500, self._race_tick)
        except Exception:

            self._race_job = None

    def _show_final_standings_popup(self):
        popup = tk.Toplevel(self.window.root)
        popup.title("── FINAL STANDINGS ──")
        popup.geometry("480x460")
        popup.resizable(False, False)
        popup.configure(bg="#0d0a1a")

        self.window.root.update_idletasks()
        rx = self.window.root.winfo_x()
        ry = self.window.root.winfo_y()
        rw = self.window.root.winfo_width()
        rh = self.window.root.winfo_height()
        px = rx + (rw - 480) // 2
        py = ry + (rh - 460) // 2
        popup.geometry(f"480x460+{px}+{py}")
        popup.grab_set()
        popup.focus_set()
        tk.Label(popup, text="⚔  TYPE IS CODE  ⚔",
                 font=("Georgia", 16, "bold"), fg="#c8a84b", bg="#0d0a1a"
                 ).pack(pady=(22, 2))
        tk.Label(popup, text="RACE COMPLETE — FINAL STANDINGS",
                 font=("Courier New", 10), fg="#9a8860", bg="#0d0a1a"
                 ).pack(pady=(0, 10))
        tk.Frame(popup, height=1, bg="#c8a84b").pack(fill="x", padx=24, pady=(0, 8))
        body_text = self._fmt_standings_table(self._race_standings)
        for _old, _new in (("①", "🥇 ①"), ("②", "🥈 ②"), ("③", "🥉 ③")):
            body_text = body_text.replace(_old, _new)
        board = tk.Text(popup, bg="#12091e", fg="#d4c090",
                        font=("Courier New", 11),
                        bd=0, highlightthickness=0,
                        padx=14, pady=10, relief="flat", height=10)
        board.pack(fill="both", expand=True, padx=24)
        board.insert("1.0", body_text)
        board.configure(state="disabled")
        tk.Frame(popup, height=1, bg="#c8a84b").pack(fill="x", padx=24, pady=(8, 0))
        tk.Button(popup, text="CLOSE  ✕",
                  font=("Georgia", 11, "bold"),
                  bg="#1a0f2e", fg="#c8a84b",
                  activebackground="#c8a84b", activeforeground="#0d0a1a",
                  relief="flat", cursor="hand2", bd=0,
                  command=popup.destroy
                  ).pack(pady=18, ipadx=18, ipady=6)
        popup.bind("<Escape>", lambda _e: popup.destroy())


    def _on_resize(self, w: int, h: int):



        try:
            if self._resize_pending is not None:
                self.window.root.after_cancel(self._resize_pending)
        except Exception:
            pass
        try:
            self._resize_pending = self.window.root.after(
                RESIZE_DEBOUNCE_MS, self._do_resize)
        except Exception:
            self._resize_pending = None

    def _do_resize(self):
        self._resize_pending = None
        self.render_frame(self._last_message)


    def _snap_camera_to_player(self):
        self._cancel_camera_anim()
        p = getattr(self.level, "player", None)
        if p is not None:
            self._cam_cx = p.x + 0.5
            self._cam_cy = p.y + 0.5
        else:
            self._cam_cx = self.level.width / 2
            self._cam_cy = self.level.height / 2
        self._zoom_cur = self._zoom

    def _camera_target(self) -> tuple[float, float]:
        p = getattr(self.level, "player", None)
        if p is not None:
            return p.x + 0.5, p.y + 0.5
        return self.level.width / 2, self.level.height / 2

    def _camera_needs_anim(self) -> bool:
        if self._cam_cx is None or self._cam_cy is None:
            return True
        tx, ty = self._camera_target()
        if abs(tx - self._cam_cx) > CAM_EPS:
            return True
        if abs(ty - self._cam_cy) > CAM_EPS:
            return True
        if abs(self._zoom - self._zoom_cur) > CAM_ZOOM_EPS:
            return True
        return False

    def _cancel_camera_anim(self):
        anim, self._cam_anim = self._cam_anim, None
        if anim is not None:
            try:
                self.window.root.after_cancel(anim)
            except Exception:
                pass

    def _nudge_camera_toward_target(self, alpha: float = 0.6):
        try:
            tx, ty = self._camera_target()
        except Exception:
            return
        if self._cam_cx is None or self._cam_cy is None:
            self._cam_cx, self._cam_cy = tx, ty
        else:
            self._cam_cx += (tx - self._cam_cx) * alpha
            self._cam_cy += (ty - self._cam_cy) * alpha
        try:
            self._zoom_cur += (self._zoom - self._zoom_cur) * alpha
        except Exception:
            pass

    def _request_camera_anim(self):
        if self._cam_anim is not None:
            return



        if not self._camera_needs_anim() and not self._trap_in_view:
            return
        try:
            self._cam_anim = self.window.root.after(CAM_FRAME_MS, self._camera_tick)
        except Exception:
            self._cam_anim = None

    def _camera_tick(self):
        self._cam_anim = None
        try:

            frame = advance_trap_animation()
            trap_changed = frame != self._last_trap_frame
            self._last_trap_frame = frame

            tx, ty = self._camera_target()
            if self._cam_cx is None or self._cam_cy is None:
                self._cam_cx, self._cam_cy = tx, ty
                self._zoom_cur = self._zoom
            else:
                self._cam_cx += (tx - self._cam_cx) * CAM_LERP
                self._cam_cy += (ty - self._cam_cy) * CAM_LERP
                self._zoom_cur += (self._zoom - self._zoom_cur) * CAM_ZOOM_LERP
                if not self._camera_needs_anim():

                    self._cam_cx, self._cam_cy = tx, ty
                    self._zoom_cur = self._zoom

            if not trap_changed and not self._camera_needs_anim():
                self._request_camera_anim()
                return
            self.render_frame(self._last_message, board_only=True)
        except Exception:




            self._cancel_camera_anim()

    def _compute_camera(self, cols: int, rows: int,
                        cw: int, ch: int, avail_w: int, avail_h: int):
        import math

        zoom_cur = getattr(self, "_zoom_cur", getattr(self, "_zoom", 1.0))
        fit = min(avail_w // max(1, cols), avail_h // max(1, rows))
        fit = max(1, fit)
        want = min(avail_w // CAM_VIEW_COLS, avail_h // CAM_VIEW_ROWS)
        want = max(CAM_MIN_CELL, want)
        want = min(want, CAM_MAX_CELL)
        want = max(1, int(round(want * zoom_cur)))

        if want <= fit:

            cell = fit
            view_cols, view_rows = cols, rows
            cam_x0 = 0.0
            cam_y0 = 0.0
            board_w = cell * cols
            board_h = cell * rows
            ox = (cw - board_w) // 2
            oy = (ch - board_h) // 2
            return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy


        cell = want
        view_cols = max(1, avail_w // cell)
        view_rows = max(1, avail_h // cell)
        view_cols = min(view_cols, cols)
        view_rows = min(view_rows, rows)

        tx, ty = self._camera_target()
        if self._cam_cx is None or self._cam_cy is None:
            self._cam_cx, self._cam_cy = tx, ty

        max_x0 = max(0.0, float(cols - view_cols))
        max_y0 = max(0.0, float(rows - view_rows))
        cam_x0 = min(max(self._cam_cx - view_cols / 2, 0.0), max_x0)
        cam_y0 = min(max(self._cam_cy - view_rows / 2, 0.0), max_y0)

        board_w = view_cols * cell
        board_h = view_rows * cell
        ox = (cw - board_w) // 2
        oy = (ch - board_h) // 2
        return cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy

    def _zoom_for_full_map(self, avail_w: int, avail_h: int) -> float:
        cols = max(1, self.level.width)
        rows = max(1, self.level.height)
        fit = min(avail_w // cols, avail_h // rows)
        fit = max(1, fit)
        want_base = min(avail_w // CAM_VIEW_COLS, avail_h // CAM_VIEW_ROWS)
        want_base = max(CAM_MIN_CELL, want_base)
        want_base = min(want_base, CAM_MAX_CELL)
        if want_base <= 0:
            return CAM_ZOOM_MIN
        needed = fit / float(want_base)
        return max(CAM_ZOOM_MIN, min(float(CAM_ZOOM_MAX), needed))

    def fit_map_to_screen(self) -> float:
        try:
            cw, ch = self.canvas.get_size()
        except Exception:
            cw, ch = 0, 0
        if cw < 10 or ch < 10:


            self._zoom = CAM_ZOOM_MIN
        else:
            avail_w = cw - 2 * BOARD_PADDING
            avail_h = ch - 2 * BOARD_PADDING
            self._zoom = self._zoom_for_full_map(avail_w, avail_h)
        self._nudge_camera_toward_target(0.6)
        return self._zoom




    REGISTRY_KEYS = {
        "Wall": ("Wall",),
        "Platform": ("Platform",),
        "Door": ("Door",),
        "Trap": ("Trap",),
        "HiddenBoom": ("Trap",),
        "Stone": ("Stone",),
        "SealWall": ("Seal",),
        "Seal2Wall": ("Seal2",),
        "Seal3Wall": ("Seal3",),
        "Seal4Wall": ("Seal4",),
        "Seal5Wall": ("Seal5",),
        "Seal6Wall": ("Seal6",),
        "LaserDoor": ("Laser",),
        "LatchDoor": ("Latch",),
        "LeverPedestal": ("Lever", "Lever2", "Lever3", "Lever4"),
        "LeverWall": ("Lever", "Lever2", "Lever3", "Lever4"),
        "Warp": (),
        "HardMine": (),
    }


    TILE_REGISTRY_KEYS = ("Flag", "Gate", "Beacon")

    def _any_lethal_trap(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        level = self.level
        for gy in range(y0, y1):
            for gx in range(x0, x1):
                obj = level.terrain_at(gx, gy)
                if obj is None or obj.__class__.__name__ != "Trap":
                    continue
                try:
                    if obj.is_lethal():
                        return True
                except Exception:
                    return True
        return False

    def _registry_digest(self) -> dict:
        try:
            snap = PropertyRegistry.snapshot()
        except Exception:
            snap = {}
        return {cls: tuple(sorted(props.items()))
                for cls, props in snap.items()}

    def _goal_overlay_at(self, x: int, y: int) -> bool:
        if bool(PropertyRegistry.get("Flag", "moved", False)) and \
                getattr(self.level, "flag2", None) == (x, y):
            return True
        if bool(PropertyRegistry.get("Gate", "at", False)) and \
                getattr(self.level, "gate2", None) == (x, y):
            return True
        if bool(PropertyRegistry.get("Beacon", "lit", False)) and \
                getattr(self.level, "beacon2", None) == (x, y):
            return True
        return False

    def _cell_signature(self, x: int, y: int, reg: dict | None = None) -> tuple:
        tile = self.level.tile_at(x, y)
        tile_cls = tile.__class__.__name__
        terr = self.level.terrain_at(x, y)
        blk = self.level.block_at(x, y)
        player = getattr(self.level, "player", None)
        on_player = player is not None and player.x == x and player.y == y
        overlay = self._goal_overlay_at(x, y)
        obj_type = terr.__class__.__name__ if terr is not None else None

        if (obj_type is None and blk is None and not on_player
                and not overlay and tile_cls == "Floor"):
            return ("floor",)


        if reg is None:
            reg = self._registry_digest()
        keys = set(self.REGISTRY_KEYS.get(obj_type, ()))
        keys.update(self.TILE_REGISTRY_KEYS)
        registry = tuple((k, reg.get(k)) for k in sorted(keys))


        flags: list = []
        if terr is not None:
            for name in ("is_blocking", "is_lethal", "is_void", "is_active"):
                fn = getattr(terr, name, None)
                try:
                    flags.append(fn() if callable(fn) else None)
                except Exception:
                    flags.append(None)
            if obj_type == "Warp":

                flags.append(bool(getattr(self, "_show_warps", True)))
            else:
                flags.append(None)
            if obj_type == "Trap" and (len(flags) < 2 or flags[1]):

                flags.append(self._last_trap_frame)
            else:
                flags.append(None)

        glyph = ""
        if blk is not None:
            try:
                glyph = blk.glyph().strip()
            except Exception:
                glyph = "%s%s" % (getattr(blk, "kind", ""),
                                  getattr(blk, "value", ""))

        return (
            tile_cls,
            obj_type,
            tuple(flags),
            glyph,
            (bool(on_player), bool(getattr(self.level, "dead", False)),
             bool(getattr(self.level, "player_invisible", False))),
            bool(overlay),
            registry,
        )


    _cell_sig = _cell_signature


    def render_frame(self, message: str = "", board_only: bool = False):
        import time as _time
        _t0 = _time.perf_counter()



        if not board_only:
            self._last_message = message or ""
        else:
            message = self._last_message
        if not board_only:





            try:
                _ww = self.window.root.winfo_width()
                _wh = self.window.root.winfo_height()
            except Exception:
                _ww, _wh = 0, 0
            if (_ww, _wh) != self._last_win_size:
                try:
                    self.window.root.update_idletasks()
                except Exception:
                    pass
                try:
                    _ww = self.window.root.winfo_width()
                    _wh = self.window.root.winfo_height()
                except Exception:
                    pass
                self._last_win_size = (_ww, _wh)
        raw = self.canvas.raw

        cols = self.level.width
        rows = self.level.height


        cw, ch = self.canvas.get_size()
        if cw < 10 or ch < 10:
            return
        win_w, win_h = self.window.root.winfo_width(), self.window.root.winfo_height()

        avail_w = cw - 2 * BOARD_PADDING
        avail_h = ch - 2 * BOARD_PADDING
        cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy = \
            self._compute_camera(cols, rows, cw, ch, avail_w, avail_h)




        fast = False
        board_w = view_cols * cell
        board_h = view_rows * cell
        _state = "idle"
        try:
            _lp = getattr(self, "_last_player_pos", None)
            if (not self.level.dead and _lp is not None
                    and getattr(self, "_last_anim_frame", -1) == self.level.moves
                    and self.level.player is not None
                    and _lp != (self.level.player.x, self.level.player.y)):
                _dx = self.level.player.x - _lp[0]
                _state = "walk_r" if _dx > 0 else "walk_l"
            if (not self.level.dead
                    and getattr(self, "_last_push_frame", -1) == self.level.moves):
                _state = "push"
        except Exception:
            _state = "idle"

        import math as _math
        x0i = max(0, int(_math.floor(cam_x0)))
        y0i = max(0, int(_math.floor(cam_y0)))
        x1i = min(cols, int(_math.ceil(cam_x0 + view_cols)))
        y1i = min(rows, int(_math.ceil(cam_y0 + view_rows)))








        geom_key = (cell, cam_x0, cam_y0, view_cols, view_rows, ox, oy,
                    cw, ch, self.level_index, id(self.level))
        full = (geom_key != self._board_geom)



        reg = self._registry_digest()
        changed: set[tuple[int, int]] | None = None
        if not full:
            changed = set()
            fresh: dict[tuple[int, int], tuple] = {}
            for _gy in range(y0i, y1i):
                for _gx in range(x0i, x1i):
                    _sig = self._cell_signature(_gx, _gy, reg)
                    fresh[(_gx, _gy)] = _sig
                    if _sig != self._cell_sigs.get((_gx, _gy)):
                        changed.add((_gx, _gy))


            p = getattr(self.level, "player", None)
            if p is not None:
                changed.add((p.x, p.y))
            self._cell_sigs = fresh
        else:
            self._cell_sigs = {}
            self._board_geom = geom_key




        self._trap_in_view = self._any_lethal_trap(x0i, y0i, x1i, y1i)

        def _px(gx: int) -> int:
            return int(round(ox + (gx - cam_x0) * cell))

        def _py(gy: int) -> int:
            return int(round(oy + (gy - cam_y0) * cell))

        if full:
            self.canvas.clear()


            try:
                bg_photo = get_canvas_photo(win_w, win_h, cw, ch)
            except Exception:
                bg_photo = None
            if bg_photo is not None:
                self._bg_photo = bg_photo
                raw.create_image(0, 0, image=bg_photo, anchor="nw")


            raw.create_rectangle(ox - 3 + 6, oy - 3 + 8,
                                 ox + board_w + 3 + 6, oy + board_h + 3 + 8,
                                 fill="#05070f", outline="")


            for pad, color in ((10, "#0e3a40"), (7, "#155e63"), (4, "#2aa5a0")):
                raw.create_rectangle(ox - pad, oy - pad,
                                     ox + board_w + pad, oy + board_h + pad,
                                     fill="", outline=color, width=2)


            raw.create_rectangle(ox - 3, oy - 3,
                                 ox + board_w + 3, oy + board_h + 3,
                                 fill="", outline=BOARD_BORDER, width=2)





        is_global = getattr(self.level, "rule_mode", "circuit") == "global"


        flag_moved = bool(PropertyRegistry.get("Flag", "moved", False))
        flag2 = getattr(self.level, "flag2", None)
        gate_on = bool(PropertyRegistry.get("Gate", "at", False))
        gate2 = getattr(self.level, "gate2", None)
        beacon_on = bool(PropertyRegistry.get("Beacon", "lit", False))
        beacon2 = getattr(self.level, "beacon2", None)
        if is_global:
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
                    if not full and (gx, gy) not in changed:
                        continue
                    cell_tag = f"cell_{gx}_{gy}"
                    raw.delete(f"cell_{gx}_{gy}")
                    cv = _tagged(raw, cell_tag)
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__


                    if tile_cls == "Wall":
                        draw_wall(cv, px, py, cell, fast=fast)
                    elif tile_cls == "Goal":
                        if flag_moved:
                            draw_floor(cv, px, py, cell, fast=fast)
                        else:
                            self._draw_goal_cell(cv, gx, gy, px, py, cell, fast=fast)
                    else:
                        draw_floor(cv, px, py, cell, fast=fast)
                        if flag_moved and flag2 is not None and (gx, gy) == flag2:
                            self._draw_goal_cell(cv, gx, gy, px, py, cell, fast=fast)
                        elif gate_on and gate2 is not None and (gx, gy) == gate2:
                            self._draw_goal_cell(cv, gx, gy, px, py, cell, fast=fast)
                        elif beacon_on and beacon2 is not None and (gx, gy) == beacon2:
                            self._draw_goal_cell(cv, gx, gy, px, py, cell, fast=fast)


                    terr = self.level.terrain_at(gx, gy)
                    tcls = terr.__class__.__name__ if terr is not None else ""
                    if tcls == "Door":
                        if terr.is_blocking():
                            draw_door_closed(cv, px, py, cell, fast=fast)
                        else:
                            draw_door_open(cv, px, py, cell, fast=fast)
                    elif tcls == "Trap":
                        if terr.is_lethal():
                            draw_trap_lethal(cv, px, py, cell, fast=fast)
                        else:
                            draw_trap_safe(cv, px, py, cell, fast=fast)
                    elif tcls == "Platform":
                        if terr.is_void():
                            draw_void(cv, px, py, cell, fast=fast)
                        else:
                            draw_floor(cv, px, py, cell, fast=fast)
                    elif tcls == "Stone":
                        if terr.is_blocking():
                            draw_stone(cv, px, py, cell, fast=fast)
                        else:
                            draw_floor(cv, px, py, cell, fast=fast)
                    elif tcls == "SealWall":
                        if terr.is_blocking():
                            draw_seal_wall(cv, px, py, cell, fast=fast,
                                col=SEAL_SHEET_COL.get(tcls, 1))
                        else:
                            draw_floor(cv, px, py, cell, fast=fast)
                    elif tcls in ("Seal2Wall", "Seal3Wall", "Seal4Wall", "Seal5Wall", "Seal6Wall"):
                        if terr.is_blocking():
                            draw_seal_wall(cv, px, py, cell, fast=fast,
                                col=SEAL_SHEET_COL.get(tcls, 1))
                        else:
                            draw_floor(cv, px, py, cell, fast=fast)
                    elif tcls == "LeverPedestal":
                        _active = bool(terr.is_active()) if hasattr(terr, "is_active") else False
                        draw_lever(cv, px, py, cell, active=_active, fast=fast)
                    elif tcls == "LeverWall":
                        draw_wall(cv, px, py, cell, fast=fast)
                    elif tcls == "LatchDoor":
                        if terr.is_blocking():
                            draw_latch_closed(cv, px, py, cell, fast=fast)
                        else:
                            draw_latch_open(cv, px, py, cell, fast=fast)
                    elif tcls == "LaserDoor":
                        if terr.is_blocking():
                            draw_laser(cv, px, py, cell, active=True, fast=fast)
                        else:
                            draw_laser(cv, px, py, cell, active=False, fast=fast)
                    elif tcls == "Warp":

                        if getattr(self, "_show_warps", True):
                            draw_warp(cv, px, py, cell, fast=fast)

                    elif tcls in ("HiddenBoom", "HardMine"):


                        draw_mine(cv, px, py, cell, fast=fast)


                    blk = self.level.block_at(gx, gy)
                    if blk is not None:
                        draw_code_block(cv, px, py, cell,
                                        blk.glyph().strip(), blk.kind, fast=fast)


                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)
                    if is_player and self._goal_entry_frame > 0 and not self.level.dead:
                        pass
                    elif is_player:
                        if self.level.dead:
                            under = self.level.terrain_at(gx, gy)
                            if self.level.player_invisible:

                                draw_void(cv, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ == "LaserDoor"
                                    and under.is_lethal()):

                                draw_ash(cv, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ in (
                                        "HiddenBoom", "BorderMine", "HardMine")):

                                self._draw_mine_aftermath(cv, px, py, cell, fast=fast)
                            elif (under is not None
                                    and under.__class__.__name__ == "Trap"
                                    and under.is_lethal()):

                                draw_player(cv, px, py, cell, fast=fast, dead=True, death_type="trap", state="idle")
                            elif under is not None and under.is_lethal():
                                draw_boom_explosion(cv, px, py, cell, fast=fast)
                            else:
                                draw_player(cv, px, py, cell, fast=fast, dead=True, death_type=None, state="idle")
                        else:
                            draw_player(cv, px, py, cell, fast=fast, dead=False, state=_state)
        else:
            for gy in range(y0i, y1i):
                for gx in range(x0i, x1i):
                    px = _px(gx)
                    py = _py(gy)
                    if not full and (gx, gy) not in changed:
                        continue
                    cell_tag = f"cell_{gx}_{gy}"
                    raw.delete(f"cell_{gx}_{gy}")
                    cv = _tagged(raw, cell_tag)
                    tile = self.level.tile_at(gx, gy)
                    tile_cls = tile.__class__.__name__


                    if tile_cls == "Wall":
                        draw_wall(cv, px, py, cell, fast=fast)
                    elif tile_cls == "Goal":
                        self._draw_goal_cell(cv, gx, gy, px, py, cell, fast=fast)
                    else:
                        draw_floor(cv, px, py, cell, fast=fast)


                    occ = self.level.object_at(gx, gy)
                    cls = occ.__class__.__name__ if occ is not None else ""
                    is_player = (self.level.player and
                                 self.level.player.x == gx and
                                 self.level.player.y == gy)

                    if is_player and not self.level.dead and self._goal_entry_frame > 0:
                        pass
                    elif is_player and self.level.dead and cls in ("HiddenBoom", "BorderMine", "HardMine"):
                        self._draw_mine_aftermath(cv, px, py, cell, fast=fast)
                    elif (is_player and self.level.dead and cls == "LaserDoor"
                            and occ is not None and occ.is_lethal()):
                        draw_ash(cv, px, py, cell, fast=fast)
                    elif (is_player and self.level.dead and cls == "Trap"
                            and occ is not None and occ.is_lethal()):
                        draw_player(cv, px, py, cell, fast=fast, dead=True, death_type="trap", state="idle")
                    elif is_player and self.level.dead and self.level.player_invisible:


                        draw_void(cv, px, py, cell, fast=fast)
                    elif is_player:
                        draw_player(cv, px, py, cell, fast=fast, dead=self.level.dead, death_type=None, state=_state if not self.level.dead else "idle")
                    elif occ is not None:
                        if cls == "Platform":
                            if occ.is_void():
                                draw_void(cv, px, py, cell, fast=fast)
                            else:

                                draw_floor(cv, px, py, cell, fast=fast)
                        elif cls == "Door":
                            if occ.is_blocking():
                                draw_door_closed(cv, px, py, cell, fast=fast)
                            else:
                                draw_door_open(cv, px, py, cell, fast=fast)
                        elif cls == "Trap":
                            if occ.is_lethal():
                                draw_trap_lethal(cv, px, py, cell, fast=fast)
                            else:
                                draw_trap_safe(cv, px, py, cell, fast=fast)
                        elif cls == "Stone":
                            if occ.is_blocking():
                                draw_stone(cv, px, py, cell, fast=fast)
                            else:
                                draw_floor(cv, px, py, cell, fast=fast)
                        elif cls == "SealWall":
                            if occ.is_blocking():
                                draw_seal_wall(cv, px, py, cell, fast=fast,
                                    col=SEAL_SHEET_COL.get(cls, 1))
                            else:
                                draw_floor(cv, px, py, cell, fast=fast)
                        elif cls in ("Seal2Wall", "Seal3Wall", "Seal4Wall", "Seal5Wall", "Seal6Wall"):
                            if occ.is_blocking():
                                draw_seal_wall(cv, px, py, cell, fast=fast,
                                    col=SEAL_SHEET_COL.get(cls, 1))
                            else:
                                draw_floor(cv, px, py, cell, fast=fast)
                        elif cls == "LeverPedestal":
                            _active = bool(occ.is_active()) if hasattr(occ, "is_active") else False
                            draw_lever(cv, px, py, cell, active=_active, fast=fast)
                        elif cls == "LeverWall":
                            draw_wall(cv, px, py, cell, fast=fast)
                        elif cls == "LatchDoor":
                            if occ.is_blocking():
                                draw_latch_closed(cv, px, py, cell, fast=fast)
                            else:
                                draw_latch_open(cv, px, py, cell, fast=fast)
                        elif cls == "LaserDoor":
                            draw_laser(cv, px, py, cell, active=bool(occ.is_blocking()), fast=fast)
                        elif cls == "Warp":

                            if getattr(self, "_show_warps", True):
                                draw_warp(cv, px, py, cell, fast=fast)

                        elif cls == "CodeBlock":
                            label = occ.glyph().strip()
                            kind = occ.kind
                            draw_code_block(cv, px, py, cell, label, kind, fast=fast)

        if full and not board_only:




            fresh: dict[tuple[int, int], tuple] = {}
            for _gy in range(y0i, y1i):
                for _gx in range(x0i, x1i):
                    fresh[(_gx, _gy)] = self._cell_signature(_gx, _gy, reg)
            self._cell_sigs = fresh




        if board_only:
            self._request_camera_anim()
            return
        press = getattr(self.level, "fusion_press_count", 0)
        hint = LEVEL_HINTS[self.level_index] if 0 <= self.level_index < len(LEVEL_HINTS) else ""
        race_text = self._race_text() if self.race is not None else ""
        panel_key = (self.level_index, self.level.moves, self._last_message,
                     press, self.game_completed, hint, race_text,
                     self._race_over, self._race_time_up)
        panel_dirty = (panel_key != self._panel_cache)
        if panel_dirty:
            self._panel_cache = panel_key
            lvl_num = min(self.level_index + 1, len(ALL_LEVELS))
            if self.game_completed:
                self.status_label.configure(
                    text=f"✅  ALL {len(ALL_LEVELS)} LEVELS COMPLETE!",
                    fg=SUCCESS_COLOR)
            else:
                self.status_label.configure(
                    text=f"Level {lvl_num}/{len(ALL_LEVELS)}:  {self.level.name}",
                    fg=TEXT_COLOR)

            self.moves_label.configure(text=f"Moves: {self.level.moves}")
            if self.race is not None:
                import time as _time3
                if self._race_over:
                    self.race_title.configure(text="RACE OVER")
                elif self._race_time_up:
                    self.race_title.configure(text="TIME! 00:00")
                elif self._race_ends_at is not None:
                    self.race_title.configure(
                        text="Timer: %s Minute left" % fmt_time(self._race_ends_at - _time3.time()))
                if not self.race_title.winfo_ismapped():
                    self.race_title.pack(fill="x", padx=12, pady=5, anchor="nw",
                                         after=self.sep_status)
                if not self.race_view._text.winfo_ismapped():



                    self.race_view._text.pack(fill="x", padx=12, pady=4, anchor="nw",
                                              after=self.race_title)
                self.race_view.set_text(race_text)
            else:
                self.race_title.pack_forget()
                try:
                    self.race_view._text.pack_forget()
                except Exception:
                    pass




            if press > 0:
                msg_text, msg_fg = (
                    f"⚙ Stone. + open: {press}/3 presses to fuse", ACCENT)
            elif self._last_message:
                msg_text = f"▶ {self._last_message}"
                msg_fg = DANGER_COLOR if self.level.dead else TEXT_BODY
            else:
                msg_text, msg_fg = "", TEXT_BODY
            self.message_label.configure(text=msg_text, fg=msg_fg)
            self._pad_message_row()





            if not self.game_completed and hint:
                if not self.sep_registry.winfo_ismapped():
                    self.sep_registry.pack(fill="x", padx=12, pady=6,
                                           before=self.sep_volume)
                if not self.hints_label.winfo_ismapped():
                    self.hints_label.pack(fill="x", padx=12, pady=5, anchor="nw",
                                          before=self.sep_volume)
                if not self.hints_view._text.winfo_ismapped():
                    self.hints_view._text.pack(fill="x", padx=12, pady=4, anchor="nw",
                                               before=self.sep_volume)


                if self._last_hint != hint:
                    self.hints_view.set_text(hint)
                    self._last_hint = hint
            else:
                self.hints_label.pack_forget()
                self.hints_view._text.pack_forget()
                self.sep_registry.pack_forget()
                self._last_hint = None

        self._paint_panel_backdrop()

        self._request_camera_anim()
        try:
            import time as _time2
            self._last_render_ms = (_time2.perf_counter() - _t0) * 1000.0
        except Exception:
            pass

    def _pad_message_row(self):
        lab = self.message_label
        try:
            art = lab.cget("image")
            if art:
                lab.configure(image="")
            inset = 2 * (int(lab.cget("pady")) + int(lab.cget("bd"))
                         + int(lab.cget("highlightthickness")))
            rows = (lab.winfo_reqheight() - inset) // self._msg_line_px
            rows = max(1, rows)
            if rows < self._MSG_ROWS:
                lab.configure(text=str(lab.cget("text"))
                              + "\n" * (self._MSG_ROWS - rows))
            if art:
                lab.configure(image=art, compound="center")
        except Exception:
            pass

    def _paint_panel_backdrop(self):
        try:
            frame = self.info_frame._frame
            root = self.window.root
            win_w, win_h = root.winfo_width(), root.winfo_height()
            panel_w, panel_h = frame.winfo_width(), frame.winfo_height()
            if win_w < 50 or win_h < 50 or panel_w < 50 or panel_h < 50:
                return
            key = (win_w, win_h, panel_w, panel_h)
            if key == self._panel_bg_key:
                return
            root.update_idletasks()
            win_w, win_h = root.winfo_width(), root.winfo_height()
            panel_w, panel_h = frame.winfo_width(), frame.winfo_height()
            if win_w < 50 or win_h < 50 or panel_w < 50 or panel_h < 50:
                return
            key = (win_w, win_h, panel_w, panel_h)
            if key == self._panel_bg_key:
                return
            self._panel_bg_key = key
            bg = get_panel_photo(win_w, win_h, panel_w)
            if bg is None:
                return
            self.info_frame.set_background(bg)
            for name, lab in (("status", self.status_label),
                              ("moves", self.moves_label),
                              ("message", self.message_label),
                              ("controls", self.controls_label),
                              ("hints", self.hints_label)):
                if not lab.winfo_ismapped():
                    continue









                prev = self._label_photos.get(name)
                try:
                    if lab.cget("image"):
                        lab.configure(image="")
                    inset_x = (int(lab.cget("padx")) + int(lab.cget("bd"))
                               + int(lab.cget("highlightthickness")))
                    inset_y = (int(lab.cget("pady")) + int(lab.cget("bd"))
                               + int(lab.cget("highlightthickness")))
                    lx = lab.winfo_x() + inset_x
                    ly = lab.winfo_y() + inset_y
                    lw = lab.winfo_width() - 2 * inset_x
                    lh = lab.winfo_reqheight() - 2 * inset_y
                    photo = get_panel_slice(lx, ly, lw, lh, win_w, win_h,
                                            panel_w)
                    if photo is None:
                        continue
                    self._label_photos[name] = photo
                    lab.configure(image=photo, compound="center")
                except Exception:
                    try:
                        if prev is not None:
                            lab.configure(image=prev, compound="center")
                    except Exception:
                        pass
        except Exception:
            return


    def on_key(self, key: str):

        arrow_map = {"up": "w", "down": "s", "left": "a", "right": "d"}
        key = arrow_map.get(key, key)

        if key == "q":
            self._cancel_camera_anim()
            self._cancel_race_tick()
            if self.race is not None:
                try:
                    if self._race_is_host():
                        self.race["net"].stop()
                    else:
                        self.race["net"].leave()
                except Exception:
                    pass
            self.window.root.destroy()
            return
        if key == "h":
            self.render_frame("Arrows/WASD move. R=restart. +/-=zoom. 0/F=fit map. "
                              "C=center. M=mute. [/]=volume. Q=quit.")
            return
        if key == "r":
            from_start = self.game_completed
            if self.race is not None and self.game_completed:
                self.render_frame("Roster complete! Waiting for the clock.")
                return
            self.restart_level(from_start=from_start)
            if self.race is not None:
                self._race_restarts += 1
                self._race_report()
            msg = "Game restarted from Level 1." if from_start else "Level restarted."
            self.render_frame(msg)
            return
        if key == "p":
            self._show_warps = not getattr(self, "_show_warps", False)
            self.render_frame("Portals " + ("revealed." if self._show_warps else "hidden."))
            return
        if key == "m":
            self._on_mute_toggle()
            return
        if key in ("bracketleft", "["):
            self._bump_volume(-10)
            return
        if key in ("bracketright", "]"):
            self._bump_volume(+10)
            return
        if key in ("plus", "equal", "kp_add", "+", "="):
            self._zoom = min(CAM_ZOOM_MAX, self._zoom + 0.15)
            self._nudge_camera_toward_target(0.6)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- rooms closer.")
            return
        if key in ("minus", "kp_subtract", "-"):
            self._zoom = max(CAM_ZOOM_MIN, self._zoom - 0.15)
            self._nudge_camera_toward_target(0.6)
            self.render_frame(f"Zoom {self._zoom:.2f}x -- see more rooms.")
            return
        if key in ("0", "f", "fit"):
            zoom = self.fit_map_to_screen()
            self.render_frame(f"Zoom {zoom:.2f}x -- full map in view.")
            return
        if key == "c":


            self.render_frame("Camera gliding to player.")
            return
        if key not in ("w", "a", "s", "d"):
            return


        # Ignore movement input during goal entry animation (prevents double level advance)
        if self._goal_entry_job is not None:
            return

        if self.game_completed:
            if self.race is not None:
                self.render_frame("Roster complete! Waiting for the clock.")
            else:
                self.render_frame(
                    "All levels complete!  Press R to restart from Level 1, or Q to quit.")
            return
        if self.race is not None and (self._race_over or self._race_time_up):
            self.render_frame("Race over! Waiting for final standings." if self._race_over
                              else "Time! Waiting for host results.")
            return

        m0 = self.level.moves
        _door_was_open = bool(PropertyRegistry.get("Door", "isOpen", False))
        _latch_was_open = bool(PropertyRegistry.get("Latch", "isOpen", False))
        _stone_was_solid = bool(PropertyRegistry.get("Stone", "solid", True))
        _was_dead = bool(self.level.dead)
        _pre_pos = (self.level.player.x, self.level.player.y) if self.level.player else None
        try:
            _pre_blocks = set(self.level.blocks_by_pos().keys())
        except Exception:
            _pre_blocks = set()
        msg = self.level.move_player(key)

        try:
            if bool(PropertyRegistry.get("Door", "isOpen", False)) and not _door_was_open:
                self._play_sfx(SFX_DOOR)
            elif bool(PropertyRegistry.get("Latch", "isOpen", False)) and not _latch_was_open:
                self._play_sfx(SFX_DOOR)
            if not bool(PropertyRegistry.get("Stone", "solid", True)) and _stone_was_solid:
                self._play_sfx(SFX_STONE)
        except Exception:
            pass
        if self.level.dead and not _was_dead and "BOOM!" in msg:

            self._play_sfx(SFX_EXPLOSION)
            self._boom_anim = {"phase": "blast"}
            try:
                _bm, _bl = self.level.moves, self.level_index

                def _settle_boom(moves=_bm, lvl=_bl):
                    try:
                        if (self.level.dead and self.level.moves == moves
                                and self.level_index == lvl):
                            self._boom_anim = {"phase": "ash"}
                            self.render_frame(self._last_message)
                    except Exception:
                        pass

                self.window.root.after(BOOM_BLAST_MS, _settle_boom)
            except Exception:
                self._boom_anim = {"phase": "ash"}
        try:
            _post_pos = (self.level.player.x, self.level.player.y) if self.level.player else None
            _moved = _pre_pos is not None and _post_pos is not None and _post_pos != _pre_pos
            try:
                _blocks_moved = set(self.level.blocks_by_pos().keys()) != _pre_blocks
            except Exception:
                _blocks_moved = False
            if _moved:
                self._last_player_pos = _pre_pos
                self._last_anim_frame = self.level.moves
            if _moved and (_blocks_moved or "push" in msg.lower()):
                self._last_push_frame = self.level.moves
        except Exception:
            pass
        if self.race is not None and self.level.moves > m0:
            self._race_moves += self.level.moves - m0
            self._race_report()
        if self.level.won:
            if self.race is not None:
                self._race_levels += 1
                self._race_report()
                if not self.next_level():
                    self.render_frame(
                        "🎉 Congratulations!  You compiled your way through every level!  "
                        "Press R to play again or Q to quit.")
                    return
                self.render_frame("Level solved!  New level loaded.")
                return
            if self._player_on_goal_art():
                self._start_goal_entry_animation()
                return
            self._finish_win()
            return
        if self.level.dead:
            self._nudge_camera_toward_target(1.0)
            self.render_frame(msg + "  Press R to restart.")
            return



        self._nudge_camera_toward_target(1.0)
        self.render_frame(msg)


    def run(self):
        self.window.run()
