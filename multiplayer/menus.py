"""menus.py — Tkinter home / multiplayer / lobby screens (GUI only).

Flow:
  Home [Play | Multiplayer | Exit Game]
    Play         -> callback into single-player GUIEngine
    Multiplayer  -> [I'm faster than you | Two player | Back]
      I'm faster than you -> LAN lobby menu (race mode fixed)
      Two player          -> [Duel | Win together | Back]
        Duel              -> LAN lobby menu (versus mode fixed)
        Win together      -> LAN lobby menu (co-op mode fixed)
      LAN lobby menu -> [Create Lobby | Join Lobby | Back]
        Create   -> enter name -> host lobby screen (mode fixed)
        Join     -> enter name, Refresh LAN list or type host IP, Join
        Lobby    -> host sees players + Start (placeholder until gamemode
                   level logic lands); client waits for host start.
"""
from __future__ import annotations

from .protocol import (
    DEFAULT_LOBBY_PORT,
    GAMEMODES,
    gamemode_label,
)

# Multiplayer hub mapping: hub button -> fixed lobby gamemode id.
FASTER_MODE = "race"          # "I'm faster than you" — race over LAN
DUEL_MODE = "versus"          # "Two player > Duel" — versus over LAN
TOGETHER_MODE = "co-op-puzzle"  # "Two player > Win together" — co-op over LAN

BG = "#0f1323"
PANEL = "#111528"
TEXT = "#eef1ff"
DIM = "#a8b0d0"
ACCENT = "#8aa2ff"


class MenuApp:
    def __init__(self, on_play, on_race=None, start="home"):
        import tkinter as tk
        from tkinter import messagebox
        self.tk = tk
        self.messagebox = messagebox
        self.on_play = on_play
        self.on_race = on_race
        self.root = tk.Tk()
        self.root.title("Type Is Code")
        self.root.configure(bg=BG)
        self.root.geometry("560x520")
        self.root.minsize(480, 440)
        self.frame = None
        self.host = None
        self.client = None
        self.is_host = False
        self.poll_job = None
        self.discovered = []
        self.show_home()
        if start == "multiplayer":
            # Entered from the animated menu's MULTIPLAYER option.
            self.show_multiplayer()

    # -- frame helpers ------------------------------------------------
    def _leave_net(self):
        self._stop_poll()
        if self.client is not None:
            try:
                self.client.leave()
            except Exception:
                pass
            self.client = None
        if self.host is not None:
            try:
                self.host.stop()
            except Exception:
                pass
            self.host = None

    def _clear(self):
        self._stop_poll()
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None

    def _new_frame(self):
        import tkinter as tk
        self._clear()
        self.frame = tk.Frame(self.root, bg=BG)
        self.frame.pack(fill="both", expand=True, padx=28, pady=24)
        return self.frame

    def _title(self, parent, text, sub=""):
        t = self.tk.Label(parent, text=text, font=("Consolas", 22, "bold"),
                          fg=TEXT, bg=BG)
        t.pack(pady=(6, 2))
        if sub:
            s = self.tk.Label(parent, text=sub, font=("Consolas", 11),
                              fg=DIM, bg=BG, wraplength=460, justify="center")
            s.pack(pady=(0, 12))
        return t

    def _btn(self, parent, text, cmd):
        return self.tk.Button(parent, text=text, command=cmd,
                              font=("Consolas", 13, "bold"),
                              fg=TEXT, bg=PANEL, activebackground=ACCENT,
                              relief="flat", padx=12, pady=10)

    # -- screens ------------------------------------------------------
    def show_home(self):
        self._leave_net()
        f = self._new_frame()
        self._title(f, "TYPE IS CODE", "Rewrite the source code of the world.")
        self._btn(f, "▶  Play", self._on_play_pressed).pack(fill="x", pady=6)
        self._btn(f, "🌐  Multiplayer", self.show_multiplayer).pack(fill="x", pady=6)
        self._btn(f, "✕  Exit Game", self.root.destroy).pack(fill="x", pady=6)
        hint = self.tk.Label(
            f, text="Single-player puzzle on Play. LAN lobbies under Multiplayer.",
            font=("Consolas", 10), fg=DIM, bg=BG, wraplength=460)
        hint.pack(pady=(14, 0))

    def _on_play_pressed(self):
        play = self.on_play
        self.root.destroy()
        play()

    def show_multiplayer(self):
        self._leave_net()
        f = self._new_frame()
        self._title(f, "MULTIPLAYER", "Pick a mode.")
        self._btn(f, "⚡  I'm faster than you",
                  lambda: self.show_lan_menu(FASTER_MODE)).pack(fill="x", pady=6)
        self._btn(f, "👥  Two player", self.show_two_player).pack(fill="x", pady=6)
        self._btn(f, "←  Back", self.show_home).pack(fill="x", pady=6)

    def show_two_player(self):
        f = self._new_frame()
        self._title(f, "TWO PLAYER", "Pick a two-player mode.")
        self._btn(f, "⚔  Duel",
                  lambda: self.show_lan_menu(DUEL_MODE)).pack(fill="x", pady=6)
        self._btn(f, "🤝  Win together",
                  lambda: self.show_lan_menu(TOGETHER_MODE)).pack(fill="x", pady=6)
        self._btn(f, "←  Back", self.show_multiplayer).pack(fill="x", pady=6)

    def _lan_title(self, gamemode: str) -> str:
        if gamemode == FASTER_MODE:
            return "I'M FASTER THAN YOU"
        if gamemode == DUEL_MODE:
            return "DUEL"
        if gamemode == TOGETHER_MODE:
            return "WIN TOGETHER"
        return gamemode.upper()

    def _lan_back(self, gamemode: str):
        # "I'm faster than you" lives directly under Multiplayer;
        # Duel / Win together live under Two player.
        if gamemode == FASTER_MODE:
            self.show_multiplayer()
        else:
            self.show_two_player()

    def show_lan_menu(self, gamemode: str):
        f = self._new_frame()
        self._title(f, self._lan_title(gamemode),
                    f"Same-network (LAN) lobby — {gamemode_label(gamemode)}.")
        self._btn(f, "＋  Create Lobby",
                  lambda m=gamemode: self.show_create(m)).pack(fill="x", pady=6)
        self._btn(f, "🔍  Join Lobby",
                  lambda m=gamemode: self.show_join(m)).pack(fill="x", pady=6)
        self._btn(f, "←  Back",
                  lambda m=gamemode: self._lan_back(m)).pack(fill="x", pady=6)

    def show_create(self, gamemode: str | None = None):
        f = self._new_frame()
        fixed = gamemode if gamemode in (FASTER_MODE, DUEL_MODE, TOGETHER_MODE) else None
        title_sub = (f"{self._lan_title(fixed)} — create the LAN lobby."
                     if fixed else "Pick a gamemode, then create the lobby.")
        self._title(f, "CREATE LOBBY", title_sub)
        self.tk.Label(f, text="Your name:", font=("Consolas", 11),
                      fg=TEXT, bg=BG).pack(anchor="w")
        name_var = self.tk.StringVar(value="Host")
        self.tk.Entry(f, textvariable=name_var,
                      font=("Consolas", 12)).pack(fill="x", pady=(0, 10))
        if fixed is not None:
            mode_var = self.tk.StringVar(value=fixed)
            self.tk.Label(f, text=f"Mode: {gamemode_label(fixed)}",
                          font=("Consolas", 11, "bold"),
                          fg=TEXT, bg=BG).pack(anchor="w", pady=(0, 4))
        else:
            self.tk.Label(f, text="Gamemode:", font=("Consolas", 11),
                          fg=TEXT, bg=BG).pack(anchor="w")
            mode_var = self.tk.StringVar(value=GAMEMODES[0]["id"])
            labels = [g["label"] for g in GAMEMODES]
            ids = [g["id"] for g in GAMEMODES]
            label_var = self.tk.StringVar(value=labels[0])

            def _on_mode_pick(choice):
                try:
                    mode_var.set(ids[labels.index(choice)])
                except ValueError:
                    pass
            self.tk.OptionMenu(f, label_var, *labels,
                               command=_on_mode_pick).pack(fill="x", pady=(0, 4))
        note = self.tk.Label(
            f, text="Gamemode level plan + logic will be added later —\n"
                    "the lobby stores your pick for now.",
            font=("Consolas", 10), fg=DIM, bg=BG, justify="left")
        note.pack(anchor="w", pady=(0, 12))
        self._btn(
            f, "Create",
            lambda: self._do_create(name_var.get(), mode_var.get())).pack(
                fill="x", pady=6)
        back_target = (lambda m=fixed: self.show_lan_menu(m)) if fixed else self.show_multiplayer
        self._btn(f, "←  Back", back_target).pack(fill="x", pady=6)

    def show_join(self, gamemode: str | None = None):
        from .lobby import LobbyClient
        f = self._new_frame()
        fixed = gamemode if gamemode in (FASTER_MODE, DUEL_MODE, TOGETHER_MODE) else None
        title_sub = (f"{self._lan_title(fixed)} — join a lobby on the same network."
                     if fixed else "Join a lobby on the same network as the host.")
        self._title(f, "JOIN LOBBY", title_sub + "\nNo lobby listed? Type the HOST IP shown on the "
                    "host's lobby screen. Both PCs need the same Wi-Fi, and the "
                    "host must allow Python through its firewall.")
        self.tk.Label(f, text="Your name:", font=("Consolas", 11),
                      fg=TEXT, bg=BG).pack(anchor="w")
        name_var = self.tk.StringVar(value="Player")
        self.tk.Entry(f, textvariable=name_var,
                      font=("Consolas", 12)).pack(fill="x", pady=(0, 8))
        self.tk.Label(f, text="LAN lobbies:", font=("Consolas", 11),
                      fg=TEXT, bg=BG).pack(anchor="w")
        listbox = self.tk.Listbox(f, font=("Consolas", 11), height=5)
        listbox.pack(fill="both", expand=True, pady=(0, 8))

        def refresh():
            listbox.delete(0, "end")
            all_found = LobbyClient.discover(timeout=1.5)
            if fixed is not None:
                self.discovered = [i for i in all_found if i.gamemode == fixed]
            else:
                self.discovered = all_found
            if not self.discovered:
                if fixed is not None:
                    listbox.insert("end", f"(no {fixed} lobbies — check same Wi-Fi/LAN)")
                else:
                    listbox.insert("end", "(no lobbies found — check same Wi-Fi/LAN)")
            for info in self.discovered:
                listbox.insert(
                    "end",
                    f"{info.host_name}  [{info.gamemode}]  "
                    f"{info.players}p  {info.address}:{info.port}")
            if self.discovered:
                # Pre-select the first lobby: Join then uses it even if the
                # user never clicks the row (the previous silent fallback to
                # the manual 127.0.0.1 field caused bogus refused errors).
                listbox.selection_set(0)
                listbox.see(0)
        refresh_btn = self._btn(f, "↻  Refresh", refresh)
        refresh_btn.pack(fill="x", pady=(0, 8))

        row = self.tk.Frame(f, bg=BG)
        row.pack(fill="x", pady=(0, 8))
        self.tk.Label(row, text="Host IP:", font=("Consolas", 11),
                      fg=TEXT, bg=BG).pack(side="left")
        ip_var = self.tk.StringVar(value="127.0.0.1")
        self.tk.Entry(row, textvariable=ip_var, font=("Consolas", 12),
                      width=16).pack(side="left", padx=6)
        self.tk.Label(row, text="Port:", font=("Consolas", 11),
                      fg=TEXT, bg=BG).pack(side="left")
        port_var = self.tk.StringVar(value=str(DEFAULT_LOBBY_PORT))
        self.tk.Entry(row, textvariable=port_var, font=("Consolas", 12),
                      width=7).pack(side="left", padx=6)

        def _do_join():
            sel = listbox.curselection()
            if sel and self.discovered and sel[0] < len(self.discovered):
                info = self.discovered[sel[0]]
                addr, port = info.address, str(info.port)
            elif len(self.discovered) == 1:
                # One lobby on the LAN and nothing selected: use it.
                info = self.discovered[0]
                addr, port = info.address, str(info.port)
            elif self.discovered:
                self.messagebox.showerror(
                    "Join", "Select a lobby from the LAN list first, "
                             "or type the host IP manually below.")
                return
            else:
                addr, port = ip_var.get().strip(), port_var.get().strip()
                if addr in ("127.0.0.1", "localhost"):
                    confirm = self.messagebox.askokcancel(
                        "Join",
                        "No lobby selected and Host IP is still 127.0.0.1 "
                        "(this machine only).\n\nTo join another PC, type the "
                        "HOST IP shown on the host's lobby screen.\n\nJoin "
                        "127.0.0.1 anyway?")
                    if not confirm:
                        return
            try:
                port_i = int(port)
            except ValueError:
                self.messagebox.showerror("Join", "Port must be a number.")
                return
            self._do_join(addr, port_i, name_var.get())
        self._btn(f, "Join", _do_join).pack(fill="x", pady=6)
        back_target = (lambda m=fixed: self.show_lan_menu(m)) if fixed else self.show_multiplayer
        self._btn(f, "←  Back", back_target).pack(fill="x", pady=6)

    # -- actions ------------------------------------------------------
    def _do_create(self, name, gamemode):
        from .lobby import LobbyHost
        name = (name or "").strip()
        if not name:
            self.messagebox.showerror("Create", "Enter your name first.")
            return
        try:
            self.host = LobbyHost(name, gamemode)
            self.host.start()
        except Exception as exc:
            self.messagebox.showerror("Create", f"Could not host lobby:\n{exc}")
            self.host = None
            return
        self.is_host = True
        self.show_lobby()

    def _do_join(self, address, port, name):
        from .lobby import LobbyClient
        name = (name or "").strip()
        if not name:
            self.messagebox.showerror("Join", "Enter your name first.")
            return
        if not address:
            self.messagebox.showerror("Join", "Enter the host IP first.")
            return
        client = LobbyClient(name)
        try:
            client.connect(address, port)
        except Exception as exc:
            self.messagebox.showerror(
                "Join",
                f"Could not join {address}:{port} — same network as host?\n{exc}")
            return
        self.client = client
        self.is_host = False
        self.show_lobby()

    def show_lobby(self):
        f = self._new_frame()
        host, client, is_host = self.host, self.client, self.is_host
        if is_host:
            info_name = host.host_name
            info_mode = f"{host.gamemode} — {gamemode_label(host.gamemode)}"
            from .lobby import lan_ips
            info_addr = (f"Lobby {host.lobby_id}  |  port {host.bound_port}\n"
                         f"HOST IP (guests type this): {', '.join(lan_ips())}")
        else:
            info_name = client.you
            info_mode = f"{client.gamemode}"
            info_addr = f"Lobby {client.lobby_id}  |  host {client.host_name}"
        role = "HOST" if is_host else "GUEST"
        self._title(f, f"LOBBY ({role})", f"{info_name}  •  {info_mode}\n{info_addr}")
        plist = self.tk.Listbox(f, font=("Consolas", 12), height=6)
        plist.pack(fill="both", expand=True, pady=(0, 8))
        status = self.tk.Label(f, text="Waiting…", font=("Consolas", 11),
                               fg=DIM, bg=BG, wraplength=460, justify="left")
        status.pack(anchor="w", pady=(0, 8))

        def refresh_players(players):
            plist.delete(0, "end")
            for p in players:
                tag = ""
                if is_host and host is not None and p == host.host_name:
                    tag = " (host)"
                plist.insert("end", p + tag)

        if is_host:
            refresh_players(host.players)
            if host.gamemode == FASTER_MODE:
                from .race import fmt_time, RACE_DURATION_S
                status.configure(
                    text="Guests on the same network can discover + join. "
                         "Press Start Race when ready -- %s on the clock."
                         % fmt_time(RACE_DURATION_S))
                self._btn(f, "Start Race", self._do_start_race).pack(
                    fill="x", pady=6)
            else:
                status.configure(text="Guests on the same network can discover + join. "
                                      "Press Start when ready.")
                self._btn(f, "▶  Start Game", lambda: self._do_start(status)).pack(
                    fill="x", pady=6)
        else:
            refresh_players(client.players)
            status.configure(text="Waiting for host to start…")

        def leave():
            mode = None
            if is_host and host is not None:
                mode = host.gamemode
            elif not is_host and client is not None:
                mode = client.gamemode
            if is_host:
                try:
                    host.stop()
                except Exception:
                    pass
                self.host = None
            else:
                try:
                    client.leave()
                except Exception:
                    pass
                self.client = None
            if mode in (FASTER_MODE, DUEL_MODE, TOGETHER_MODE):
                self.show_lan_menu(mode)
            else:
                self.show_multiplayer()
        self._btn(f, "✕  Leave Lobby", leave).pack(fill="x", pady=6)

        # poll host/client events into the UI
        def poll():
            try:
                if is_host and host is not None:
                    while True:
                        try:
                            kind, payload = host.events.get_nowait()
                        except Exception:
                            break
                        if kind == "join":
                            status.configure(text=f"{payload} joined.")
                        elif kind == "leave":
                            status.configure(text=f"{payload} left.")
                        refresh_players(host.players)
                elif not is_host and client is not None:
                    while True:
                        try:
                            kind, payload = client.events.get_nowait()
                        except Exception:
                            break
                        if kind == "start":
                            note = payload.get("note", "") if isinstance(payload, dict) else ""
                            status.configure(
                                text=f"Host started the game!\n{note}")
                            self.messagebox.showinfo(
                                "Game started",
                                note or "Host started the game. "
                                       "Gamemode logic coming soon — lobby stays open.")
                        elif kind == "race_start":
                            self._begin_race("client")
                            return
                        elif kind == "disconnected":
                            status.configure(text="Disconnected from host.")
                            return
                        refresh_players(client.players)
            except Exception:
                pass
            self.poll_job = self.root.after(400, poll)
        poll()

    def _do_start_race(self):
        from .race import RACE_DURATION_S
        try:
            self.host.start_race(duration_s=RACE_DURATION_S)
        except Exception as exc:
            self.messagebox.showerror("Start Race", f"Could not start:\n{exc}")
            return
        self._begin_race("host")

    def _begin_race(self, role):
        """Leave the menu (keeping the lobby connection) and start racing."""
        if self.on_race is None:
            self.messagebox.showerror("Race", "Race launcher is not wired up.")
            return
        from .race import RACE_DURATION_S
        net = self.host if role == "host" else self.client
        name = (self.host.host_name if role == "host" and self.host is not None
                else self.client.you if self.client is not None else "Player")
        duration = (self.host.race_duration_s
                    if role == "host" and self.host is not None
                    else RACE_DURATION_S)
        launch = self.on_race
        self._stop_poll()
        try:
            self.root.destroy()
        except Exception:
            pass
        self.host = None
        self.client = None
        launch(role, net, name, duration)

    def _do_start(self, status_label):
        try:
            msg = self.host.start_game()
        except Exception as exc:
            self.messagebox.showerror("Start", f"Could not start:\n{exc}")
            return
        note = msg.get("note", "")
        status_label.configure(text=f"Started!\n{note}\nLobby stays open.")
        self.messagebox.showinfo("Game started", note + "\n\nLobby stays open — "
                                 "gamemode level plan + logic lands later.")

    def _stop_poll(self):
        job, self.poll_job = self.poll_job, None
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

    def run(self):
        self.root.mainloop()


def run_menus(on_play, on_race=None, animated=True):
    """Open the home menu window (blocking).

    `on_play` starts the solo game; `on_race(role, net, name, duration_s)`
    starts a LAN race (role "host"/"client").  The animated cover-art
    menu is the default; pass animated=False for the classic menu.
    """
    if animated:
        from menu_scene import run_animated_menu

        def _to_multiplayer():
            MenuApp(on_play, on_race=on_race, start="multiplayer").run()

        run_animated_menu(on_new_game=on_play,
                          on_multiplayer=_to_multiplayer)
        return
    app = MenuApp(on_play, on_race=on_race)
    app.run()
