
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont






_KEYSYM_ALIASES = {
    "+": "plus",
    "=": "equal",
    "-": "minus",
}


def _lighten(color: str, factor: float = 1.3) -> str:
    try:
        hexs = color.lstrip("#")
        if len(hexs) != 6:
            return color
        r, g, b = (int(hexs[i:i + 2], 16) for i in (0, 2, 4))

        def clamp(v):
            return max(0, min(255, int(v * factor)))

        return "#%02x%02x%02x" % (clamp(r), clamp(g), clamp(b))
    except Exception:
        return color


def _make_scrollbar(parent, bg: str):
    style = ttk.Style(parent)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    name = "Panel.Vertical.TScrollbar"
    trough = _lighten(bg, 1.5)
    thumb = _lighten(bg, 3.2)
    style.configure(
        name, background=thumb, troughcolor=trough, bordercolor=trough,
        lightcolor=thumb, darkcolor=thumb, arrowcolor=trough, relief="flat")
    style.map(
        name,
        background=[("active", _lighten(bg, 4.6)),
                    ("pressed", _lighten(bg, 4.6))],
        arrowcolor=[("active", _lighten(bg, 3.2))])
    return ttk.Scrollbar(parent, orient="vertical", style=name)


class Window:
    def __init__(self, title: str, width: int, height: int, bg: str = "#111111",
                 min_width: int = 900, min_height: int = 500):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=bg)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min_width, min_height)
        self.root.resizable(True, True)
        self._key_handler = None
        self._resize_handler = None
        self._bg = bg
        self._last_size = (width, height)
        self.root.bind("<Key>", self._handle_key)
        self.root.bind("<Configure>", self._handle_configure)

    def _handle_key(self, event: tk.Event):
        if self._key_handler is None:
            return
        sym = (event.keysym or "").lower() or (event.char or "").lower()
        self._key_handler(_KEYSYM_ALIASES.get(sym, sym))

    def _handle_configure(self, event: tk.Event):
        if event.widget is not self.root:
            return
        new_size = (event.width, event.height)
        if new_size != self._last_size:
            self._last_size = new_size
            if self._resize_handler is not None:




                self.root.update_idletasks()
                self._resize_handler(event.width, event.height)

    def on_key_down(self, handler):
        self._key_handler = handler

    def on_resize(self, handler):
        self._resize_handler = handler

    def focus(self):
        self.root.focus_set()

    def create_canvas(self, bg: str = "#222222") -> "Canvas":
        canvas = tk.Canvas(
            self.root,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left", fill="both", expand=True)
        return Canvas(canvas)

    def create_frame(self, width: int = 430, bg: str | None = None) -> "Frame":
        frame_bg = bg or self._bg
        outer = tk.Frame(self.root, bg=frame_bg, width=width)
        outer.pack(side="right", fill="y")
        outer.pack_propagate(False)

        bar = _make_scrollbar(outer, frame_bg)
        canvas = tk.Canvas(
            outer, bg=frame_bg, highlightthickness=0, bd=0,
            yscrollcommand=bar.set)
        bar.configure(command=canvas.yview)
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=frame_bg)
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _sync(event=None):
            bbox = canvas.bbox("all")
            if not bbox:
                return
            canvas.configure(scrollregion=bbox)
            if event is None or event.widget is canvas:
                canvas.itemconfigure(window_id, width=canvas.winfo_width())


            overflowing = (bbox[3] - bbox[1]) > canvas.winfo_height() + 1
            if overflowing != frame._bar_visible:
                frame._bar_visible = overflowing
                if overflowing:
                    bar.pack(side="right", fill="y")
                else:
                    bar.pack_forget()
                    canvas.yview_moveto(0)

        frame = Frame(outer, body=body, canvas=canvas, bar=bar)
        canvas.bind("<Configure>", _sync)
        body.bind("<Configure>", _sync)
        return frame

    def get_size(self) -> tuple[int, int]:
        self.root.update_idletasks()
        return self.root.winfo_width(), self.root.winfo_height()

    def run(self):
        self.root.mainloop()


class Canvas:
    def __init__(self, tk_canvas: tk.Canvas):
        self._canvas = tk_canvas

    @property
    def raw(self) -> tk.Canvas:
        return self._canvas

    def clear(self):
        self._canvas.delete("all")

    def draw_rect(self, x: int, y: int, width: int, height: int,
                  fill: str, outline: str | None = None, **kw):
        self._canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=fill, outline=outline or fill, **kw
        )

    def draw_text(self, x: int, y: int, text: str, fill: str = "white",
                  anchor: str = "nw", font=None):
        default_font = font or ("Courier New", 11, "bold")
        self._canvas.create_text(x, y, text=text, fill=fill,
                                 anchor=anchor, font=default_font)

    def get_size(self) -> tuple[int, int]:



        return self._canvas.winfo_width(), self._canvas.winfo_height()

    def set_size(self, width: int, height: int):
        self._canvas.config(width=width, height=height)


class TextView:
    def __init__(self, tk_text: tk.Text):
        self._text = tk_text

    def set_text(self, text: str):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.configure(state="disabled")


class Frame:
    def __init__(self, tk_frame: tk.Frame, body: "tk.Frame | None" = None,
                 canvas: "tk.Canvas | None" = None, bar=None):


        self._outer = tk_frame
        self._frame = body if body is not None else tk_frame
        self._canvas = canvas
        self._bar = bar
        self._bar_visible = False

        self._bg_label = tk.Label(self._frame, borderwidth=0, highlightthickness=0,
                                  anchor="nw")
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_photo = None
        if canvas is not None:
            self._bind_wheel()

    def _bind_wheel(self):
        def _wheel(event):
            if not self._bar_visible or self._canvas is None:
                return
            outer = self._outer
            ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
            if not (ox <= event.x_root < ox + outer.winfo_width()
                    and oy <= event.y_root < oy + outer.winfo_height()):
                return
            if getattr(event, "delta", 0):
                steps = int(event.delta / 120) or (1 if event.delta > 0 else -1)
            else:
                num = getattr(event, "num", 0)
                steps = -1 if num == 4 else (1 if num == 5 else 0)
            if steps:
                self._canvas.yview_scroll(-steps, "units")

        try:
            root = self._outer.winfo_toplevel()
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                root.bind_all(seq, _wheel, add="+")
        except Exception:
            pass

    @property
    def widget(self) -> tk.Frame:
        return self._frame

    def set_background(self, photo):
        if photo is None:
            self._bg_label.place_forget()
            self._bg_photo = None
            return
        self._bg_photo = photo
        self._bg_label.configure(image=photo)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_label.lower()

    def add_label(self, text: str, font=None, fg: str = "white",
                  bg: str | None = None, anchor: str = "nw",
                  wraplength: int = 0) -> tk.Label:
        label = tk.Label(
            self._frame,
            text=text,
            fg=fg,
            bg=bg or self._frame["bg"],
            justify="left",
            anchor=anchor,
            font=font or ("Georgia", 12),
            wraplength=wraplength or 405,
        )
        label.pack(fill="x", padx=12, pady=5, anchor="nw")
        return label

    def add_text_view(self, width: int = 44, height: int = 4,
                      font=None, fg: str = "white",
                      bg: str | None = None) -> TextView:
        tk_text = tk.Text(
            self._frame,
            width=width,
            height=height,
            fg=fg,
            bg=bg or self._frame["bg"],
            font=font or ("Courier New", 11),
            wrap="word",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=8,
            spacing1=3,
            spacing2=2,
            spacing3=3,
            relief="flat",
        )
        tk_text.pack(fill="x", padx=12, pady=4, anchor="nw")
        tk_text.configure(state="disabled")
        return TextView(tk_text)
