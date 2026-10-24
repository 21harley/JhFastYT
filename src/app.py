import io
import os
import sqlite3
import sys
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import yt_dlp
from PIL import Image

VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav"]
QUALITIES = ["Mejor", "2160", "1440", "1080", "720", "480", "360"]
ACCENT = "#e5383b"
HOVER = "#c1272d"
THUMB = (128, 72)
# Instalado: <raiz>/app/JhFastYT.exe. Desarrollo: <raiz>/src/app.py. Herramientas y datos viven en <raiz>.
ROOT = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent.parent
TOOLS = ROOT / "tools"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "descargas.db"
if sys.stderr is None:  # exe sin consola: yt-dlp escribe a stderr
    sys.stdout = sys.stderr = open(os.devnull, "w")


def yt_opts():
    """Opciones comunes de yt-dlp; usa tools/ si existe, si no lo que haya en el PATH."""
    deno = TOOLS / "deno.exe"
    o = {"quiet": True, "noplaylist": True, "js_runtimes": {"deno": {"path": str(deno)}} if deno.exists() else {"node": {}}}
    if (TOOLS / "ffmpeg.exe").exists():
        o["ffmpeg_location"] = str(TOOLS)
    return o


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


def q(sql, *args):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    with c:
        rows = c.execute(sql, args).fetchall()
    c.close()
    return rows


q("""CREATE TABLE IF NOT EXISTS videos(
    id TEXT PRIMARY KEY, url TEXT, title TEXT, uploader TEXT, duration INT, thumb BLOB,
    status TEXT, fmt TEXT, added_at TEXT, downloaded_at TEXT)""")


def fmt_duration(s):
    if not s:
        return ""
    h, r = divmod(int(s), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


class Item(ctk.CTkFrame):
    """Tarjeta de un video: preview, datos y (si está pendiente) progreso."""

    def __init__(self, master, row, on_remove, on_requeue=None, on_download=None):
        super().__init__(master, corner_radius=12, fg_color="#1f1f26")
        self.row, self.state, self.on_download = row, "loading", on_download
        self.mode, self.fmt, self.quality = ctk.StringVar(value="Video"), ctk.StringVar(value="mp4"), ctk.StringVar(value="Mejor")
        self.columnconfigure(1, weight=1)
        self.thumb = ctk.CTkLabel(self, text="…", width=THUMB[0], height=THUMB[1], fg_color="#2a2a33", corner_radius=8)
        self.thumb.grid(row=0, column=0, rowspan=3, padx=10, pady=10)
        self.title = ctk.CTkLabel(self, text=row["url"], anchor="w", justify="left", wraplength=300, font=ctk.CTkFont(weight="bold"))
        self.title.grid(row=0, column=1, sticky="ew", pady=(10, 0))
        self.meta = ctk.CTkLabel(self, text="Cargando información…", anchor="w", text_color="#9a9aa5")
        self.meta.grid(row=1, column=1, sticky="ew")
        self.bar = ctk.CTkProgressBar(self, height=6, progress_color=ACCENT)
        self.bar.set(0)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=3, padx=6, sticky="n", pady=8)
        if on_requeue:
            ctk.CTkButton(btns, text="↻", width=28, height=28, fg_color="transparent", hover_color="#3a3a45",
                          command=lambda: on_requeue(self)).pack()
        ctk.CTkButton(btns, text="✕", width=28, height=28, fg_color="transparent", hover_color="#3a3a45",
                      command=lambda: on_remove(self)).pack()
        if row.get("title"):
            self.set_data(row)

    def set_data(self, row):
        self.row = row
        done = row["status"] == "done"
        self.state = "done" if done else "ready"
        self.title.configure(text=row["title"])
        meta = f"{row['uploader'] or ''} · {fmt_duration(row['duration'])}"
        if done:
            meta += f" · {row['fmt']} · {row['downloaded_at']}"
        else:
            self.bar.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(2, 10))
            if not hasattr(self, "dl_btn"):
                self.build_options()
        self.meta.configure(text=meta)
        if row["thumb"]:
            ci = ctk.CTkImage(Image.open(io.BytesIO(row["thumb"])).convert("RGB"), size=THUMB)
            self.thumb.configure(image=ci, text="")
            self.thumb.image = ci

    def build_options(self):
        r = ctk.CTkFrame(self, fg_color="#17171c", corner_radius=10)
        r.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        r.columnconfigure(3, weight=1)
        ctk.CTkSegmentedButton(r, values=["Video", "Audio"], variable=self.mode, command=self.on_mode,
                               selected_color=ACCENT, selected_hover_color=HOVER).grid(row=0, column=0, padx=8, pady=8)
        self.fmt_box = ctk.CTkOptionMenu(r, values=VIDEO_FORMATS, variable=self.fmt, width=80)
        self.fmt_box.grid(row=0, column=1, padx=4)
        self.q_box = ctk.CTkOptionMenu(r, values=QUALITIES, variable=self.quality, width=80)
        self.q_box.grid(row=0, column=2, padx=4)
        self.dl_btn = ctk.CTkButton(r, text="Descargar", height=34, fg_color=ACCENT, hover_color=HOVER,
                                    command=lambda: self.on_download([self]))
        self.dl_btn.grid(row=0, column=3, sticky="e", padx=8)

    def on_mode(self, _=None):
        audio = self.mode.get() == "Audio"
        vals = AUDIO_FORMATS if audio else VIDEO_FORMATS
        self.fmt_box.configure(values=vals)
        self.fmt.set(vals[0])
        self.q_box.configure(state="disabled" if audio else "normal")

    def label(self):
        audio = self.mode.get() == "Audio"
        return self.fmt.get() + ("" if audio or self.quality.get() == "Mejor" else f" {self.quality.get()}p")

    def set_status(self, text, pct=None):
        self.meta.configure(text=text)
        if pct is not None:
            self.bar.set(pct / 100)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JhFastYT")
        self.geometry("660x740")
        self.minsize(580, 560)
        self.out = ctk.StringVar(value=str(Path.home() / "Downloads" / "JhFastYT"))
        self.pending, self.history = [], []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.columnconfigure(0, weight=1)
        self.url = ctk.CTkEntry(top, placeholder_text="Pega una URL de YouTube y presiona Enter", height=38)
        self.url.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.url.bind("<Return>", lambda e: self.add())
        ctk.CTkButton(top, text="Agregar", width=90, height=38, fg_color=ACCENT, hover_color=HOVER,
                      command=self.add).grid(row=0, column=1)

        folder = ctk.CTkFrame(self, corner_radius=12)
        folder.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        folder.columnconfigure(1, weight=1)
        ctk.CTkButton(folder, text="📁", width=36, command=self.pick).grid(row=0, column=0, padx=10, pady=8)
        ctk.CTkLabel(folder, textvariable=self.out, anchor="w", text_color="#9a9aa5").grid(row=0, column=1, sticky="ew", padx=4)

        tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_selected_color=ACCENT,
                              segmented_button_selected_hover_color=HOVER)
        tabs.grid(row=2, column=0, sticky="nsew", padx=8)
        self.tabs = tabs
        self.lists, self.empties = {}, {}
        for name, msg in (("Pendientes", "Agrega videos para armar tu lista"), ("Descargados", "Aún no hay descargas")):
            tab = tabs.add(name)
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
            sf = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            sf.grid(sticky="nsew")
            self.lists[name] = sf
            self.empties[name] = ctk.CTkLabel(sf, text=msg, text_color="#6a6a75")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        bottom.columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(bottom, text="Listo", anchor="w", text_color="#9a9aa5")
        self.status.grid(row=0, column=0, sticky="ew")
        self.btn = ctk.CTkButton(bottom, text="Descargar todo", height=38, fg_color=ACCENT, hover_color=HOVER,
                                 command=self.download)
        self.btn.grid(row=0, column=1)
        self.btn.grid_remove()

        for r in q("SELECT * FROM videos WHERE status='pending' ORDER BY added_at"):
            self.place("Pendientes", Item(self.lists["Pendientes"], dict(r), self.remove, None, self.download))
        for r in q("SELECT * FROM videos WHERE status='done' ORDER BY downloaded_at DESC"):
            self.place("Descargados", Item(self.lists["Descargados"], dict(r), self.remove, self.requeue))
        self.refresh_empty()

    def place(self, tab, item, top=False):
        lst = self.pending if tab == "Pendientes" else self.history
        first = lst[0] if lst and top else None
        if first:
            item.pack(fill="x", padx=8, pady=4, before=first)
            lst.insert(0, item)
        else:
            item.pack(fill="x", padx=8, pady=4)
            lst.append(item)
        self.refresh_empty()

    def refresh_empty(self):
        for name, lst in (("Pendientes", self.pending), ("Descargados", self.history)):
            e = self.empties[name]
            e.pack_forget()
            if not lst:
                e.pack(pady=60)
        self.sync_btn()

    def sync_btn(self):
        if sum(i.state == "ready" for i in self.pending) >= 2:
            self.btn.grid()
        else:
            self.btn.grid_remove()

    def pick(self):
        d = filedialog.askdirectory(initialdir=self.out.get())
        if d:
            self.out.set(d)

    def add(self):
        url = self.url.get().strip()
        if not url:
            return
        self.url.delete(0, "end")
        self.tabs.set("Pendientes")
        item = Item(self.lists["Pendientes"], {"url": url}, self.remove, None, self.download)
        self.place("Pendientes", item)
        threading.Thread(target=self.fetch, args=(item,), daemon=True).start()

    def remove(self, item):
        if item.state == "downloading":
            return
        if item.row.get("id"):
            q("DELETE FROM videos WHERE id=?", item.row["id"])
        (self.pending if item in self.pending else self.history).remove(item)
        item.destroy()
        self.refresh_empty()

    def requeue(self, item):
        q("UPDATE videos SET status='pending', downloaded_at=NULL WHERE id=?", item.row["id"])
        row = dict(q("SELECT * FROM videos WHERE id=?", item.row["id"])[0])
        self.history.remove(item)
        item.destroy()
        self.place("Pendientes", Item(self.lists["Pendientes"], row, self.remove, None, self.download))

    def fetch(self, item):
        try:
            with yt_dlp.YoutubeDL({**yt_opts(), "skip_download": True}) as y:
                info = y.extract_info(item.row["url"], download=False)
            thumb = None
            try:
                with urllib.request.urlopen(info["thumbnail"], timeout=10) as r:
                    thumb = r.read()
            except Exception:
                pass
            self.after(0, self.loaded, item, info, thumb)
        except Exception as e:
            item.state = "error"
            self.after(0, item.set_status, f"Error: {str(e)[:90]}")

    def loaded(self, item, info, thumb):
        old = q("SELECT status FROM videos WHERE id=?", info["id"])
        if old:
            self.status.configure(text="Ya está en " + ("Descargados" if old[0]["status"] == "done" else "Pendientes"))
            self.pending.remove(item)
            item.destroy()
            return self.refresh_empty()
        q("INSERT INTO videos VALUES(?,?,?,?,?,?,'pending',NULL,?,NULL)", info["id"], item.row["url"], info.get("title"),
          info.get("uploader"), info.get("duration"), thumb, datetime.now().isoformat(timespec="seconds"))
        item.set_data(dict(q("SELECT * FROM videos WHERE id=?", info["id"])[0]))
        self.sync_btn()

    def opts(self, item):
        fmt, out = item.fmt.get(), self.out.get()

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    self.after(0, item.set_status, f"Descargando {d['downloaded_bytes'] / total * 100:.0f}%  {d.get('_speed_str', '').strip()}",
                               d["downloaded_bytes"] / total * 100)
            elif d["status"] == "finished":
                self.after(0, item.set_status, "Procesando…")

        o = {**yt_opts(), "outtmpl": f"{out}/%(title)s.%(ext)s", "progress_hooks": [hook]}
        if item.mode.get() == "Audio":
            o["format"] = "bestaudio/best"
            o["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": fmt}]
        else:
            qual = item.quality.get()
            h = "" if qual == "Mejor" else f"[height<={qual}]"
            o["format"] = f"bv*{h}+ba/b{h}"
            o["merge_output_format"] = fmt
        return o

    def download(self, items=None):
        todo = [i for i in (items or self.pending) if i.state == "ready"]
        if not todo:
            return
        for i in todo:
            i.state = "downloading"
            i.dl_btn.configure(state="disabled")
            i.set_status("En cola…")
        self.sync_btn()
        threading.Thread(target=self.run, args=(todo,), daemon=True).start()

    def run(self, todo):
        for item in todo:
            label = item.label()
            try:
                with yt_dlp.YoutubeDL(self.opts(item)) as y:
                    y.download([item.row["url"]])
                self.after(0, self.mark_done, item, label)
            except Exception as e:
                item.state = "ready"
                self.after(0, self.failed, item, str(e)[:90])

    def failed(self, item, msg):
        item.dl_btn.configure(state="normal")
        item.set_status(f"Error: {msg}")
        self.sync_btn()

    def mark_done(self, item, label):
        q("UPDATE videos SET status='done', fmt=?, downloaded_at=? WHERE id=?", label,
          datetime.now().strftime("%Y-%m-%d %H:%M"), item.row["id"])
        row = dict(q("SELECT * FROM videos WHERE id=?", item.row["id"])[0])
        self.pending.remove(item)
        item.destroy()
        self.place("Descargados", Item(self.lists["Descargados"], row, self.remove, self.requeue), top=True)


if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception:
        import traceback

        (DATA / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
