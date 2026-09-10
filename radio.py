import tkinter as tk
from tkinter import font as tkfont
import subprocess
import threading
import time
import os
import sys

V103_URL = "https://live.amperwave.net/direct/audacy-wveefmaac-imc"
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

COLORS = {
    "bg": "#0a0a0f",
    "surface": "#1a1a2e",
    "accent": "#E91E63",
    "accent2": "#9C27B0",
    "text": "#ffffff",
    "muted": "#8888aa",
    "success": "#00e676",
    "glow": "#E91E63",
}

class RadioWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("V-103 Atlanta")
        self.root.geometry("320x180+50+50")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg=COLORS["bg"])

        self.drag_data = {"x": 0, "y": 0}
        self.is_playing = False
        self.vlc_proc = None
        self.stop_event = threading.Event()
        self.watch_thread = None
        self.volume = 100
        self.bars = []

        self._build_ui()
        self._start_drag_bindings()

        self.root.after(500, self.play)

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.root, width=320, height=180, bg=COLORS["bg"],
            highlightthickness=0, bd=0
        )
        self.canvas.place(x=0, y=0)

        self.canvas.create_rectangle(0, 0, 320, 180, fill=COLORS["bg"], outline="")
        self.canvas.create_rectangle(0, 0, 320, 4, fill=COLORS["accent"], outline="")

        self.canvas.create_text(160, 22, text="V-103", font=("Segoe UI", 16, "bold"),
                                fill=COLORS["text"])
        self.canvas.create_text(160, 42, text="ATLANTA", font=("Segoe UI", 8),
                                fill=COLORS["accent"])

        self.status_text = self.canvas.create_text(160, 62, text="Connecting...",
                                                   font=("Segoe UI", 8), fill=COLORS["muted"])

        self._create_equalizer(160, 85)

        self.play_btn = self.canvas.create_oval(135, 115, 185, 165,
                                                 fill=COLORS["accent"], outline=COLORS["accent2"],
                                                 width=2)
        self.play_icon = self.canvas.create_text(160, 140, text="▶",
                                                  font=("Segoe UI", 18, "bold"), fill=COLORS["text"])
        self.canvas.tag_bind(self.play_btn, "<Button-1>", self.toggle_play)
        self.canvas.tag_bind(self.play_icon, "<Button-1>", self.toggle_play)

        self.close_btn = self.canvas.create_text(305, 15, text="✕",
                                                  font=("Segoe UI", 10), fill=COLORS["muted"])
        self.canvas.tag_bind(self.close_btn, "<Button-1>", self.quit)

        self.min_btn = self.canvas.create_text(288, 15, text="—",
                                                font=("Segoe UI", 10), fill=COLORS["muted"])
        self.canvas.tag_bind(self.min_btn, "<Button-1>", self.minimize)

        self.canvas.create_text(160, 172, text="The People's Station · 24/7",
                                font=("Segoe UI", 7), fill=COLORS["muted"])

        self._animate_bars()

    def _create_equalizer(self, cx, cy):
        bar_w = 4
        gap = 3
        n = 9
        total = n * bar_w + (n - 1) * gap
        start_x = cx - total // 2
        self.bars = []
        for i in range(n):
            x = start_x + i * (bar_w + gap)
            bar = self.canvas.create_rectangle(x, cy - 12, x + bar_w, cy + 12,
                                                fill=COLORS["accent2"], outline="")
            self.bars.append(bar)

    def _animate_bars(self):
        import random
        if self.is_playing:
            for bar in self.bars:
                h = random.randint(4, 24)
                cx = (self.canvas.coords(bar)[0] + self.canvas.coords(bar)[2]) / 2
                self.canvas.coords(bar, cx - 2, 85 - h, cx + 2, 85 + h)
                color = COLORS["accent"] if random.random() > 0.5 else COLORS["accent2"]
                self.canvas.itemconfig(bar, fill=color)
        else:
            for bar in self.bars:
                cx = (self.canvas.coords(bar)[0] + self.canvas.coords(bar)[2]) / 2
                self.canvas.coords(bar, cx - 2, 83, cx + 2, 87)
                self.canvas.itemconfig(bar, fill=COLORS["muted"])
        self.root.after(150, self._animate_bars)

    def _start_drag_bindings(self):
        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        x = self.root.winfo_x() + event.x - self.drag_data["x"]
        y = self.root.winfo_y() + event.y - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def play(self):
        if self.is_playing:
            return
        self.stop_event.clear()
        self.is_playing = True
        self.canvas.itemconfig(self.play_icon, text="⏸")
        self.canvas.itemconfig(self.status_text, text="● LIVE", fill=COLORS["success"])
        self.watch_thread = threading.Thread(target=self._vlc_loop, daemon=True)
        self.watch_thread.start()

    def pause(self):
        if not self.is_playing:
            return
        self.is_playing = False
        self.stop_event.set()
        self.canvas.itemconfig(self.play_icon, text="▶")
        self.canvas.itemconfig(self.status_text, text="Paused", fill=COLORS["muted"])
        self._kill_vlc()

    def toggle_play(self, event=None):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def _vlc_loop(self):
        while not self.stop_event.is_set():
            try:
                self.vlc_proc = subprocess.Popen(
                    [VLC_PATH, "--no-video", "--loop", "--no-one-instance",
                     f"--volume={self.volume}", "--intf=dummy", V103_URL],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x08000000
                )
                while not self.stop_event.is_set() and self.vlc_proc.poll() is None:
                    time.sleep(0.5)
                if self.stop_event.is_set():
                    break
                time.sleep(2)
            except Exception:
                time.sleep(5)

    def _kill_vlc(self):
        if self.vlc_proc and self.vlc_proc.poll() is None:
            try:
                self.vlc_proc.terminate()
                self.vlc_proc.wait(timeout=3)
            except Exception:
                try:
                    self.vlc_proc.kill()
                except Exception:
                    pass
        self.vlc_proc = None

    def minimize(self, event=None):
        self.root.withdraw()
        self.root.after(100, self._show_back)

    def _show_back(self):
        pass

    def quit(self, event=None):
        self.stop_event.set()
        self._kill_vlc()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    if not os.path.exists(VLC_PATH):
        alt = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        if os.path.exists(alt):
            VLC_PATH = alt
        else:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "VLC not found. Install it:\n\n  winget install VideoLAN.VLC",
                "V-103 Radio Widget", 0x10)
            sys.exit(1)
    RadioWidget().run()
