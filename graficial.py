"""
graficial.py
------------
Thin Tkinter wrapper providing a Canvas, Frame, Labels, and TextViews.
Now supports resizable windows with an on-resize callback so that the
game can re-render when the user drags the window edge.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont


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
        if self._key_handler is not None:
            self._key_handler(event.keysym.lower())

    def _handle_configure(self, event: tk.Event):
        if event.widget is not self.root:
            return
        new_size = (event.width, event.height)
        if new_size != self._last_size:
            self._last_size = new_size
            if self._resize_handler is not None:
                # The toplevel <Configure> event arrives *before* the pack
                # geometry manager has given children (canvas, info panel)
                # their new sizes.  Flush pending layout so the redraw
                # below uses the current canvas size, not the old one.
                self.root.update_idletasks()
                self._resize_handler(event.width, event.height)

    def on_key_down(self, handler):
        self._key_handler = handler

    def on_resize(self, handler):
        """Register a callback(width, height) invoked when the window is resized."""
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

    def create_frame(self, width: int = 430) -> "Frame":
        frame = tk.Frame(self.root, bg=self._bg, width=width)
        frame.pack(side="right", fill="y")
        frame.pack_propagate(False)
        return Frame(frame)

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
        """Direct access to the underlying tk.Canvas for entity drawing."""
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
        default_font = font or ("Consolas", 11, "bold")
        self._canvas.create_text(x, y, text=text, fill=fill,
                                 anchor=anchor, font=default_font)

    def get_size(self) -> tuple[int, int]:
        # Do not flush idle drawing work here.  The game clears and redraws
        # this canvas in one render pass; forcing Tk to process idle tasks
        # between those steps briefly presents the empty canvas as a flash.
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
    def __init__(self, tk_frame: tk.Frame):
        self._frame = tk_frame
        # backdrop photo pinned behind all panel widgets (see set_background)
        self._bg_label = tk.Label(tk_frame, borderwidth=0, highlightthickness=0,
                                  anchor="nw")
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_photo = None

    def set_background(self, photo):
        """Pin a backdrop photo behind all panel widgets (None hides it)."""
        if photo is None:
            self._bg_label.place_forget()
            self._bg_photo = None
            return
        self._bg_photo = photo  # hold a ref so Tk does not blank it
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
            font=font or ("Consolas", 12),
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
            font=font or ("Consolas", 12),
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
