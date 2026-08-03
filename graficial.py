from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont


class Window:
    def __init__(self, title: str, width: int, height: int, bg: str = "#111111"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.configure(bg=bg)
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self._key_handler = None
        self._bg = bg
        self.root.bind("<Key>", self._handle_key)

    def _handle_key(self, event: tk.Event):
        if self._key_handler is not None:
            self._key_handler(event.keysym.lower())

    def on_key_down(self, handler):
        self._key_handler = handler

    def focus(self):
        self.root.focus_set()

    def create_canvas(self, width: int, height: int, bg: str = "#222222") -> "Canvas":
        canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left", anchor="nw")
        return Canvas(canvas)

    def create_frame(self) -> "Frame":
        frame = tk.Frame(self.root, bg=self._bg)
        frame.pack(side="right", fill="both", expand=True)
        return Frame(frame)

    def run(self):
        self.root.mainloop()


class Canvas:
    def __init__(self, tk_canvas: tk.Canvas):
        self._canvas = tk_canvas
        self._font = tkfont.Font(family="Courier", size=11, weight="bold")

    def clear(self):
        self._canvas.delete("all")

    def draw_rect(self, x: int, y: int, width: int, height: int, fill: str, outline: str | None = None):
        self._canvas.create_rectangle(x, y, x + width, y + height, fill=fill, outline=outline or fill)

    def draw_text(self, x: int, y: int, text: str, fill: str = "white", anchor: str = "nw", font=None):
        self._canvas.create_text(x, y, text=text, fill=fill, anchor=anchor, font=font or self._font)

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

    def add_label(self, text: str, font=None, fg: str = "white", bg: str | None = None, anchor: str = "nw") -> tk.Label:
        label = tk.Label(
            self._frame,
            text=text,
            fg=fg,
            bg=bg or self._frame["bg"],
            justify="left",
            anchor=anchor,
            font=font or ("Courier", 12),
        )
        label.pack(fill="x", padx=8, pady=4, anchor="nw")
        return label

    def add_text_view(self, width: int, height: int, font=None, fg: str = "white", bg: str | None = None) -> TextView:
        tk_text = tk.Text(
            self._frame,
            width=width,
            height=height,
            fg=fg,
            bg=bg or self._frame["bg"],
            font=font or ("Courier", 11),
            wrap="word",
            bd=0,
            highlightthickness=0,
        )
        tk_text.pack(fill="both", padx=8, pady=4, anchor="nw", expand=True)
        tk_text.configure(state="disabled")
        return TextView(tk_text)
