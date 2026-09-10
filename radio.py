import tkinter as tk
from tkinter import font as tkfont
import subprocess
import threading
import time
import os
import sys
import json
import re
import requests

V103_URL = "https://live.amperwave.net/direct/audacy-wveefmaac-imc"
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
PLAYLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist.json")

COLORS = {
    "bg": "#0a0a0f",
    "surface": "#1a1a2e",
    "accent": "#E91E63",
    "accent2": "#9C27B0",
    "text": "#ffffff",
    "muted": "#8888aa",
    "success": "#00e676",
    "saved": "#FFD700",
    "glow": "#E91E63",
}

def load_playlist():
    try:
        if os.path.exists(PLAYLIST_PATH):
            return json.loads(open(PLAYLIST_PATH, "r", encoding="utf-8").read())
    except Exception:
        pass
    return []

def save_playlist(songs):
    try:
        with open(PLAYLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

class RadioWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("V-103 Atlanta")
        self.root.geometry("360x240+50+50")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg=COLORS["bg"])

        self.drag_data = {"x": 0, "y": 0}
        self.is_playing = False
        self.vlc_proc = None
        self.stop_event = threading.Event()
        self.meta_stop_event = threading.Event()
        self.watch_thread = None
        self.meta_thread = None
        self.volume = 100
        self.bars = []
        self.current_song = ""
        self.playlist = load_playlist()
        self.show_playlist = False

        self._build_ui()
        self._start_drag_bindings()

        self.root.after(500, self.play)

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.root, width=360, height=240, bg=COLORS["bg"],
            highlightthickness=0, bd=0
        )
        self.canvas.place(x=0, y=0)

        self.canvas.create_rectangle(0, 0, 360, 4, fill=COLORS["accent"], outline="")
        self.canvas.create_text(180, 22, text="V-103", font=("Segoe UI", 16, "bold"),
                                fill=COLORS["text"])
        self.canvas.create_text(180, 42, text="ATLANTA", font=("Segoe UI", 8),
                                fill=COLORS["accent"])

        self.status_text = self.canvas.create_text(180, 60, text="Connecting...",
                                                   font=("Segoe UI", 8), fill=COLORS["muted"])

        self._create_equalizer(180, 82)

        self.canvas.create_text(180, 108, text="NOW PLAYING", font=("Segoe UI", 7),
                                fill=COLORS["muted"])

        self.song_text = self.canvas.create_text(180, 128, text="Loading...",
                                                  font=("Segoe UI", 10, "bold"),
                                                  fill=COLORS["text"], width=320)

        self.save_btn = self.canvas.create_rectangle(140, 145, 220, 168,
                                                       fill=COLORS["surface"], outline=COLORS["accent2"])
        self.save_label = self.canvas.create_text(180, 156, text="♡ Save to Playlist",
                                                    font=("Segoe UI", 8), fill=COLORS["text"])
        self.canvas.tag_bind(self.save_btn, "<Button-1>", self.save_song)
        self.canvas.tag_bind(self.save_label, "<Button-1>", self.save_song)

        self.play_btn = self.canvas.create_oval(155, 178, 205, 228,
                                                 fill=COLORS["accent"], outline=COLORS["accent2"],
                                                 width=2)
        self.play_icon = self.canvas.create_text(180, 203, text="▶",
                                                  font=("Segoe UI", 18, "bold"), fill=COLORS["text"])
        self.canvas.tag_bind(self.play_btn, "<Button-1>", self.toggle_play)
        self.canvas.tag_bind(self.play_icon, "<Button-1>", self.toggle_play)

        self.playlist_btn = self.canvas.create_text(50, 203, text="📋",
                                                     font=("Segoe UI", 12), fill=COLORS["muted"])
        self.canvas.tag_bind(self.playlist_btn, "<Button-1>", self.toggle_playlist_view)

        self.close_btn = self.canvas.create_text(345, 15, text="✕",
                                                  font=("Segoe UI", 10), fill=COLORS["muted"])
        self.canvas.tag_bind(self.close_btn, "<Button-1>", self.quit)

        self.canvas.create_text(180, 235, text="The People's Station · 24/7",
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
            bar = self.canvas.create_rectangle(x, cy - 10, x + bar_w, cy + 10,
                                                fill=COLORS["accent2"], outline="")
            self.bars.append(bar)

    def _animate_bars(self):
        import random
        if self.is_playing:
            for bar in self.bars:
                h = random.randint(4, 20)
                cx = (self.canvas.coords(bar)[0] + self.canvas.coords(bar)[2]) / 2
                self.canvas.coords(bar, cx - 2, 82 - h, cx + 2, 82 + h)
                color = COLORS["accent"] if random.random() > 0.5 else COLORS["accent2"]
                self.canvas.itemconfig(bar, fill=color)
        else:
            for bar in self.bars:
                cx = (self.canvas.coords(bar)[0] + self.canvas.coords(bar)[2]) / 2
                self.canvas.coords(bar, cx - 2, 80, cx + 2, 84)
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
        self.meta_stop_event.clear()
        self.is_playing = True
        self.canvas.itemconfig(self.play_icon, text="⏸")
        self.canvas.itemconfig(self.status_text, text="● LIVE", fill=COLORS["success"])
        self.watch_thread = threading.Thread(target=self._vlc_loop, daemon=True)
        self.watch_thread.start()
        self.meta_thread = threading.Thread(target=self._metadata_loop, daemon=True)
        self.meta_thread.start()

    def pause(self):
        if not self.is_playing:
            return
        self.is_playing = False
        self.stop_event.set()
        self.meta_stop_event.set()
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

    def _metadata_loop(self):
        while not self.meta_stop_event.is_set():
            try:
                r = requests.get(V103_URL, stream=True,
                                 headers={'Icy-MetaData': '1'},
                                 timeout=10, verify=False)
                metaint = int(r.headers.get('icy-metaint', 2048))
                while not self.meta_stop_event.is_set():
                    r.raw.read(metaint)
                    ml = ord(r.raw.read(1))
                    if ml > 0:
                        meta = r.raw.read(ml * 16).decode('utf-8', 'ignore').strip('\x00')
                        m = re.search(r"StreamTitle='([^']*)'", meta)
                        if m:
                            title = m.group(1).strip()
                            if title and title != self.current_song:
                                self.current_song = title
                                self.root.after(0, self._update_song_display)
                r.close()
            except Exception:
                time.sleep(5)

    def _update_song_display(self):
        song = self.current_song if self.current_song else "No info available"
        self.canvas.itemconfig(self.song_text, text=song)
        is_saved = any(s["title"] == self.current_song for s in self.playlist)
        if is_saved:
            self.canvas.itemconfig(self.save_btn, fill=COLORS["saved"])
            self.canvas.itemconfig(self.save_label, text="♥ Saved",
                                    fill=COLORS["bg"])
        else:
            self.canvas.itemconfig(self.save_btn, fill=COLORS["surface"])
            self.canvas.itemconfig(self.save_label, text="♡ Save to Playlist",
                                    fill=COLORS["text"])

    def save_song(self, event=None):
        if not self.current_song:
            return
        if any(s["title"] == self.current_song for s in self.playlist):
            self.playlist = [s for s in self.playlist if s["title"] != self.current_song]
            save_playlist(self.playlist)
            self._update_song_display()
            if self.show_playlist:
                self._draw_playlist_panel()
            return
        self.playlist.append({
            "title": self.current_song,
            "station": "V-103 Atlanta",
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        })
        save_playlist(self.playlist)
        self._update_song_display()
        if self.show_playlist:
            self._draw_playlist_panel()

    def toggle_playlist_view(self, event=None):
        self.show_playlist = not self.show_playlist
        if self.show_playlist:
            self.root.geometry("360x500")
            self.canvas.config(height=500)
            self._draw_playlist_panel()
        else:
            self.canvas.config(height=240)
            self.root.geometry("360x240")
            self._clear_playlist_panel()

    def _draw_playlist_panel(self):
        self._clear_playlist_panel()
        py = 240
        self.pl_items = []
        self.pl_items.append(self.canvas.create_rectangle(0, py, 360, py+4, fill=COLORS["accent2"], outline=""))
        self.pl_items.append(self.canvas.create_text(180, py+22, text="MY PLAYLIST", font=("Segoe UI", 12, "bold"), fill=COLORS["text"]))
        self.pl_items.append(self.canvas.create_text(180, py+40, text=f"{len(self.playlist)} songs saved", font=("Segoe UI", 8), fill=COLORS["muted"]))
        y = py + 60
        for song in self.playlist[-12:]:
            self.pl_items.append(self.canvas.create_text(15, y, text=f"♪ {song['title'][:48]}", font=("Segoe UI", 8), fill=COLORS["text"], anchor="w"))
            y += 18
        if not self.playlist:
            self.pl_items.append(self.canvas.create_text(180, y+10, text="No songs saved yet", font=("Segoe UI", 8), fill=COLORS["muted"]))

    def _clear_playlist_panel(self):
        if hasattr(self, "pl_items"):
            for item in self.pl_items:
                self.canvas.delete(item)
            self.pl_items = []

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

    def quit(self, event=None):
        self.stop_event.set()
        self.meta_stop_event.set()
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
