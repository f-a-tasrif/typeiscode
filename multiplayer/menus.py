from __future__ import annotations

from .protocol import (
    DEFAULT_LOBBY_PORT,
    GAMEMODES,
    gamemode_label,
)


FASTER_MODE = "race"
DUEL_MODE = "versus"
TOGETHER_MODE = "co-op-puzzle"


BG = "#0d0a1a"
PANEL = "#2a1f3d"
TEXT = "#e8d5a3"
DIM = "#9a8860"
ACCENT = "#d4aa44"
BTN_BG = "#2a1f3d"
BTN_FG = "#e8d5a3"
BTN_ACTIVE = "#5a3f7a"
BTN_BORDER = "#7a5fa8"
ENTRY_BG = "#1a1030"
TITLE_GOLD = "#d4aa44"
SHADOW = "#0a0a0a"
DUNGEON_DIM = 0.40
BTN_WIDTH = 26
BTN_HEIGHT = 2


class MenuApp:
    def __init__(self, on_play, on_race=None):
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

        self._bg_label = None
        self._bg_photo = None
        self._bg_size = None
        self.root.bind("<Configure>", self._apply_backdrop, add="+")
        self.show_home()


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
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        self._bg_label = tk.Label(outer, bg=BG, borderwidth=0,
                                  highlightthickness=0)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_size = None
        self._apply_backdrop()
        content = tk.Frame(outer, bg=BG)

        content.grid(row=1, column=0, sticky="n")
        content.columnconfigure(0, weight=1)
        self.frame = outer
        return content


    def _tile_backdrop(self, w: int, h: int):
        w, h = int(w), int(h)
        if w < 50 or h < 50:
            return None
        try:
            from PIL import Image, ImageTk
            from tile_renderer import DungeonSheet
            frame = DungeonSheet.frame_image("walls_floor.png", 0, 0)
            if frame is None:
                return None
            tile = frame.convert("RGB")
            base = Image.new("RGB", (w, h))
            for _y in range(0, h, tile.height):
                for _x in range(0, w, tile.width):
                    base.paste(tile, (_x, _y))
            base = base.point(lambda v: int(v * DUNGEON_DIM))
            return ImageTk.PhotoImage(base)
        except Exception:
            return None

    def _apply_backdrop(self, *_event):
        label = getattr(self, "_bg_label", None)
        if label is None:
            return
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if w < 50 or h < 50:
            return
        if (w, h) == self._bg_size:
            return
        photo = self._tile_backdrop(w, h)
        if photo is None:
            return
        self._bg_size = (w, h)
        self._bg_photo = photo
        try:
            label.configure(image=photo)
        except Exception:
            pass


    def _title(self, parent, text, sub="", big=False):
        tk = self.tk
        if big:
            holder = tk.Frame(parent, bg=BG)
            font = ("Consolas", 44, "bold")



            for offset in (2, 1):
                shadow = tk.Label(holder, text=text, font=font,
                                  fg=SHADOW, bg=BG)
                shadow.grid(row=0, column=0, sticky="nw",
                            padx=(offset, 0), pady=(offset, 0))
            t = tk.Label(holder, text=text, font=font, fg=TITLE_GOLD, bg=BG)
            t.grid(row=0, column=0, sticky="nw")
            holder.pack(pady=(0, 20 if not sub else 4))
        else:
            t = tk.Label(parent, text=text, font=("Consolas", 22, "bold"),
                         fg=TITLE_GOLD, bg=BG)
            t.pack(pady=(6, 20 if not sub else 2))
        if sub:
            s = tk.Label(parent, text=sub, font=("Consolas", 11),
                         fg=DIM, bg=BG, wraplength=460, justify="center")
            s.pack(pady=(0, 20))
        return t

    def _btn(self, parent, text, cmd):
        tk = self.tk
        border = tk.Frame(parent, bg=BTN_BORDER, padx=2, pady=2)
        button = tk.Button(
            border, text=text, command=cmd,
            font=("Consolas", 14, "bold"),
            fg=BTN_FG, bg=BTN_BG, activebackground=BTN_ACTIVE,
            activeforeground=BTN_FG, relief="flat", bd=0,
            width=BTN_WIDTH, height=BTN_HEIGHT,
            padx=16, pady=10, cursor="hand2")
        button.pack(fill="x")
        return border

    def _entry(self, parent, var, width=28):
        return self.tk.Entry(
            parent, textvariable=var, width=width,
            font=("Consolas", 13), bg=ENTRY_BG, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0,
            highlightbackground=BTN_BORDER, highlightthickness=1)

    def _field(self, parent, row, label, widget, sticky="w"):
        lab = self.tk.Label(parent, text=label, font=("Consolas", 13),
                            fg=TEXT, bg=BG)
        lab.grid(row=row, column=0, sticky="e", padx=(0, 10), pady=4)
        widget.grid(row=row, column=1, sticky=sticky, pady=4)
        return lab

    def _form(self, parent):
        form = self.tk.Frame(parent, bg=BG)
        form.pack(fill="x", pady=(0, 6))
        form.columnconfigure(1, weight=1)
        return form


    def show_home(self):
        self._leave_net()
        f = self._new_frame()
        self._title(f, "TYPE IS CODE",
                    "Rewrite the source code of the world.", big=True)
        self._btn(f, "▶  Single Player", self._on_play_pressed).pack(fill="x", pady=6)
        self._btn(f, "🌐  Multiplayer", self.show_multiplayer).pack(fill="x", pady=6)
        self._btn(f, "✕  Exit Game", self.root.destroy).pack(fill="x", pady=6)
        hint = self.tk.Label(
            f, text="",
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
                  lambda: self._coming_soon("DUEL")).pack(fill="x", pady=6)
        self._btn(f, "🤝  Win together",
                  lambda: self._coming_soon("WIN TOGETHER")).pack(fill="x", pady=6)
        self._btn(f, "←  Back", self.show_multiplayer).pack(fill="x", pady=6)

    def _coming_soon(self, mode_title: str):
        tk = self.tk
        pop = tk.Toplevel(self.root)
        pop.title(f"{mode_title} — Coming Soon")
        pop.configure(bg=BG)
        pop.geometry("380x220")
        pop.minsize(320, 180)
        pop.resizable(False, False)
        try:
            pop.transient(self.root)
            pop.grab_set()
        except Exception:
            pass

        try:
            self.root.update_idletasks()
            rx, ry = self.root.winfo_x(), self.root.winfo_y()
            rw, rh = self.root.winfo_width(), self.root.winfo_height()
            pop.update_idletasks()
            pw, ph = pop.winfo_width(), pop.winfo_height()
            pop.geometry("+%d+%d" % (rx + max(0, (rw - pw) // 2),
                                     ry + max(0, (rh - ph) // 2)))
        except Exception:
            pass
        border = tk.Frame(pop, bg=BTN_BORDER, padx=2, pady=2)
        border.pack(fill="both", expand=True, padx=14, pady=14)
        body = tk.Frame(border, bg=BG)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=mode_title, font=("Consolas", 18, "bold"),
                 fg=TITLE_GOLD, bg=BG).pack(pady=(16, 4))
        tk.Label(body, text="Coming Soon...",
                 font=("Consolas", 14, "bold"),
                 fg=TEXT, bg=BG).pack(pady=(0, 12))
        tk.Label(body, text="This mode is not playable yet.",
                 font=("Consolas", 10),
                 fg=DIM, bg=BG).pack(pady=(0, 12))
        ok_border = tk.Frame(body, bg=BTN_BORDER, padx=2, pady=2)
        ok_border.pack(pady=(0, 14))
        tk.Button(ok_border, text="OK", command=pop.destroy,
                  font=("Consolas", 12, "bold"),
                  fg=BTN_FG, bg=BTN_BG, activebackground=BTN_ACTIVE,
                  activeforeground=BTN_FG, relief="flat", bd=0,
                  width=12, cursor="hand2").pack()
        try:
            pop.wait_window()
        except Exception:
            pass

    def _lan_title(self, gamemode: str) -> str:
        if gamemode == FASTER_MODE:
            return "I'M FASTER THAN YOU"
        if gamemode == DUEL_MODE:
            return "DUEL"
        if gamemode == TOGETHER_MODE:
            return "WIN TOGETHER"
        return gamemode.upper()

    def _lan_back(self, gamemode: str):


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
        form = self._form(f)
        name_var = self.tk.StringVar(value="Host")
        self._field(form, 0, "Your name:", self._entry(form, name_var))
        if fixed is not None:
            mode_var = self.tk.StringVar(value=fixed)
            self._field(form, 1, "Mode:",
                        self.tk.Label(form, text=gamemode_label(fixed),
                                      font=("Consolas", 13, "bold"),
                                      fg=ACCENT, bg=BG, anchor="w"))
        else:
            mode_var = self.tk.StringVar(value=GAMEMODES[0]["id"])
            labels = [g["label"] for g in GAMEMODES]
            ids = [g["id"] for g in GAMEMODES]
            label_var = self.tk.StringVar(value=labels[0])

            def _on_mode_pick(choice):
                try:
                    mode_var.set(ids[labels.index(choice)])
                except ValueError:
                    pass
            menu = self.tk.OptionMenu(
                form, label_var, *labels, command=_on_mode_pick)
            menu.configure(font=("Consolas", 13), bg=ENTRY_BG, fg=TEXT,
                           activebackground=BTN_ACTIVE, activeforeground=TEXT,
                           highlightthickness=1, highlightbackground=BTN_BORDER,
                           relief="flat", bd=0, width=26, anchor="w")
            self._field(form, 1, "Gamemode:", menu)
        note = self.tk.Label(
            f, text="",
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
        form = self._form(f)
        name_var = self.tk.StringVar(value="Player")
        self._field(form, 0, "Your name:", self._entry(form, name_var))
        listbox = self.tk.Listbox(
            form, font=("Consolas", 11), height=5,
            bg=ENTRY_BG, fg=TEXT, selectbackground=BTN_ACTIVE,
            selectforeground=TEXT, relief="flat", bd=0,
            highlightbackground=BTN_BORDER, highlightthickness=1)
        self._field(form, 1, "LAN lobbies:", listbox, sticky="nsew")
        form.rowconfigure(1, weight=1)
        ip_var = self.tk.StringVar(value="127.0.0.1")
        self._field(form, 2, "Host IP:", self._entry(form, ip_var, width=16))
        port_var = self.tk.StringVar(value=str(DEFAULT_LOBBY_PORT))
        self._field(form, 3, "Port:", self._entry(form, port_var, width=7))

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



                listbox.selection_set(0)
                listbox.see(0)
        refresh_btn = self._btn(f, "↻  Refresh", refresh)
        refresh_btn.pack(fill="x", pady=(0, 8))

        def _do_join():
            sel = listbox.curselection()
            if sel and self.discovered and sel[0] < len(self.discovered):
                info = self.discovered[sel[0]]
                addr, port = info.address, str(info.port)
            elif len(self.discovered) == 1:

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
        plist = self.tk.Listbox(f, font=("Consolas", 12), height=6,
                                bg=ENTRY_BG, fg=TEXT, selectbackground=BTN_ACTIVE,
                                selectforeground=TEXT, relief="flat", bd=0,
                                highlightbackground=BTN_BORDER,
                                highlightthickness=1)
        plist.pack(fill="both", expand=True, pady=(0, 8))
        status = self.tk.Label(f, text="Waiting…", font=("Consolas", 13),
                               fg=TEXT, bg=BG, wraplength=460, justify="left")
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
                                note or "Host started the game.")
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
        self.messagebox.showinfo("Game started", note + "\n\nLobby stays open.")

    def _stop_poll(self):
        job, self.poll_job = self.poll_job, None
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass

    def run(self):
        self.root.mainloop()


def run_menus(on_play, on_race=None):
    app = MenuApp(on_play, on_race=on_race)
    app.run()
