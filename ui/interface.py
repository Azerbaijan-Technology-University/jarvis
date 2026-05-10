"""
jarvis/ui/interface.py
───────────────────────
JARVIS v3.0 — Tam animasiyalı Tkinter interfeysi.
  - Iron Man reaktor animasiyası + SIRI-styl dalğalar
  - Söhbət paneli (real-time mətn)
  - Mic toggle düyməsi
  - HUD məlumatlar
"""

from __future__ import annotations

import math
import queue
import random
import time
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable

from core.config import OWNER_NAME, UI_FPS, UI_PARTICLES
from core.logger import log

# ── Rəng palitesi ──────────────────────────────────────────────────
_PALETTE = {
    "bg": "#000000",
    "panel": "#000810",
    "border": "#001a33",
    # Status rəngləri (main, secondary, dim)
    "ready": ("#00cfff", "#0099cc", "#001a33"),
    "listening": ("#00ff88", "#00cc66", "#003322"),
    "thinking": ("#ffcc00", "#cc9900", "#332200"),
    "speaking": ("#ff7700", "#cc5500", "#331500"),
    "muted": ("#ff3333", "#cc2222", "#330000"),
    "error": ("#ff0055", "#cc0044", "#330011"),
    # UI elementləri
    "text_user": "#e0f4ff",
    "text_jarvis": "#00eeff",
    "text_label": "#004466",
    "text_hud": "#002233",
    "sep": "#001a33",
    "input_bg": "#000d1a",
    "btn_bg": "#001a33",
}


class JarvisUI:
    """Bütün interfeys məntiqi bu sinifdə."""

    def __init__(
        self,
        on_text_input: Callable[[str], None],
        on_mic_toggle: Callable[[], None],
        status_queue: queue.Queue,
        chat_queue: queue.Queue,
        mic_active_ref: Callable[[], bool],
    ) -> None:
        self._on_text_input = on_text_input
        self._on_mic_toggle = on_mic_toggle
        self._status_q = status_queue
        self._chat_q = chat_queue
        self._mic_active = mic_active_ref

        # Animasiya state
        self.status = "ready"
        self.angle = 0.0
        self.pulse = 0.0
        self.mic_pulse = 0.0
        self.scanline_y = 0
        self.particles: list[dict] = []

        self._root_built = False
        self._build_root()
        self._init_particles()
        self._show_intro()
        self._build_ui()
        self._root_built = True
        log.info("UI hazır")

    # ═══════════════════════════════════════════════════════════════
    #   ROOT
    # ═══════════════════════════════════════════════════════════════
    def _build_root(self) -> None:
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S  v3.0")
        self.root.configure(bg=_PALETTE["bg"])
        self.root.attributes("-fullscreen", True)
        self.root.update()
        self.W = self.root.winfo_screenwidth()
        self.H = self.root.winfo_screenheight()
        self.root.bind("<Escape>", lambda _: self.root.attributes("-fullscreen", False))
        self.root.bind("<F11>", lambda _: self.root.attributes("-fullscreen", True))

    # ═══════════════════════════════════════════════════════════════
    #   INTRO
    # ═══════════════════════════════════════════════════════════════
    def _show_intro(self) -> None:
        W, H = self.W, self.H
        intro = tk.Toplevel(self.root)
        intro.attributes("-fullscreen", True)
        intro.configure(bg="black")
        intro.lift()
        intro.focus_force()
        intro.update()

        cv = tk.Canvas(intro, bg="black", highlightthickness=0)
        cv.pack(fill=tk.BOTH, expand=True)
        cx, cy = W // 2, H // 2

        def hx(r: int, g: int, b: int) -> str:
            return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"

        # Fon
        for i in range(0, W, 50):
            cv.create_line(i, 0, i, H, fill="#020b12", width=1)
        for j in range(0, H, 50):
            cv.create_line(0, j, W, j, fill="#020b12", width=1)

        for r in [400, 320, 240, 160, 90]:
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#040e18", width=1)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            cv.create_line(
                cx,
                cy,
                cx + 400 * math.cos(rad),
                cy + 400 * math.sin(rad),
                fill="#030b14",
                width=1,
            )

        # Reaktor glow layerlər
        glow_ids = []
        for gr in range(90, 10, -10):
            gid = cv.create_oval(
                cx - gr, cy - gr, cx + gr, cy + gr, outline="#000000", width=2
            )
            glow_ids.append((gid, gr))

        core_id = cv.create_oval(
            cx - 38,
            cy - 38,
            cx + 38,
            cy + 38,
            fill="#000d1a",
            outline="#000000",
            width=3,
        )
        dot_id = cv.create_oval(
            cx - 9, cy - 9, cx + 9, cy + 9, fill="#000000", outline=""
        )

        title_id = cv.create_text(
            cx,
            cy - 80,
            text="J.A.R.V.I.S",
            fill="#000000",
            font=("Courier New", 72, "bold"),
            anchor=tk.CENTER,
        )
        sub_id = cv.create_text(
            cx,
            cy + 8,
            text="JUST A RATHER VERY INTELLIGENT SYSTEM",
            fill="#000000",
            font=("Courier New", 15),
            anchor=tk.CENTER,
        )
        owner_id = cv.create_text(
            cx,
            cy + 48,
            text=f"{OWNER_NAME}  ·  AUTHORIZED USER",
            fill="#000000",
            font=("Courier New", 11),
            anchor=tk.CENTER,
        )

        bar_w = 520
        bar_x = cx - bar_w // 2
        bar_y = H - 88
        cv.create_rectangle(
            bar_x, bar_y, bar_x + bar_w, bar_y + 3, fill="#040e18", outline=""
        )
        bar_fill = cv.create_rectangle(
            bar_x, bar_y, bar_x, bar_y + 3, fill="#00cfff", outline=""
        )
        status_id = cv.create_text(
            cx,
            bar_y - 28,
            text="",
            fill="#002233",
            font=("Courier New", 12),
            anchor=tk.CENTER,
        )
        pct_id = cv.create_text(
            cx,
            bar_y + 16,
            text="0%",
            fill="#001a33",
            font=("Courier New", 10),
            anchor=tk.CENTER,
        )
        intro.update()

        # Fade in
        for step in range(40):
            t = step / 39.0
            cv.itemconfig(title_id, fill=hx(0, int(t * 207), int(t * 255)))
            cv.itemconfig(sub_id, fill=hx(0, int(t * 80), int(t * 120)))
            cv.itemconfig(owner_id, fill=hx(0, int(t * 50), int(t * 80)))
            for gid, gr in glow_ids:
                a = max(0, int(t * (90 - gr)))
                cv.itemconfig(gid, outline=hx(0, a * 2, a * 3))
            cv.itemconfig(core_id, outline=hx(0, int(t * 100), int(t * 180)))
            cv.itemconfig(dot_id, fill=hx(0, int(t * 207), int(t * 255)))
            intro.update()
            time.sleep(0.016)

        # Loading
        steps = [
            (14, "NEURAL NETWORKS ACTIVATING..."),
            (30, "VOICE ENGINE CALIBRATING..."),
            (46, "MEMORY BANKS LOADING..."),
            (60, "SENSOR ARRAY ONLINE..."),
            (75, "AI CORE INITIALIZED..."),
            (88, "SECURITY PROTOCOLS ACTIVE..."),
            (100, "ALL SYSTEMS NOMINAL  —  JARVIS ONLINE"),
        ]
        for pct, msg in steps:
            cv.itemconfig(status_id, text=msg)
            cv.itemconfig(pct_id, text=f"{pct}%")
            cv.coords(bar_fill, bar_x, bar_y, bar_x + int(bar_w * pct / 100), bar_y + 3)
            for gid, gr in glow_ids:
                a = max(0, int((1 - gr / 90) * 55 + 8))
                cv.itemconfig(gid, outline=hx(0, a * 2, a * 3))
            intro.update()
            time.sleep(0.26)

        for i in range(3, 0, -1):
            cv.itemconfig(status_id, text=f"HAZIRLAŞIN... {i}", fill="#00cfff")
            intro.update()
            time.sleep(0.5)

        # Flash
        cv.create_rectangle(0, 0, W, H, fill="#00cfff", outline="", tags="fl")
        intro.update()
        time.sleep(0.04)
        cv.delete("fl")

        for step in range(22):
            t = step / 21.0
            cv.itemconfig(title_id, fill=hx(0, int((1 - t) * 207), int((1 - t) * 255)))
            cv.itemconfig(sub_id, fill=hx(0, 0, 0))
            intro.update()
            time.sleep(0.02)

        intro.destroy()

    # ═══════════════════════════════════════════════════════════════
    #   UI QURULMASI
    # ═══════════════════════════════════════════════════════════════
    def _build_ui(self) -> None:
        W, H = self.W, self.H

        self.canvas = tk.Canvas(
            self.root, bg=_PALETTE["bg"], highlightthickness=0, cursor="crosshair"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Fontlar
        try:
            self.fn = {
                "title": tkfont.Font(family="Courier New", size=26, weight="bold"),
                "sub": tkfont.Font(family="Courier New", size=10),
                "status": tkfont.Font(family="Courier New", size=12, weight="bold"),
                "chat": tkfont.Font(family="Courier New", size=11),
                "input": tkfont.Font(family="Courier New", size=12),
                "small": tkfont.Font(family="Courier New", size=9),
                "hud": tkfont.Font(family="Courier New", size=8),
            }
        except Exception:
            self.fn = {
                k: tkfont.Font(size=11)
                for k in ["title", "sub", "status", "chat", "input", "small", "hud"]
            }

        # ── Chat paneli ──
        px = int(W * 0.515)
        py = int(H * 0.10)
        pw = int(W * 0.46)
        ph = int(H * 0.70)

        chat_frame = tk.Frame(
            self.root,
            bg=_PALETTE["panel"],
            highlightthickness=1,
            highlightbackground=_PALETTE["border"],
        )
        chat_frame.place(x=px, y=py, width=pw, height=ph)

        sb = tk.Scrollbar(
            chat_frame,
            bg="#001122",
            troughcolor=_PALETTE["panel"],
            width=6,
            bd=0,
            highlightthickness=0,
        )
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_text = tk.Text(
            chat_frame,
            bg=_PALETTE["panel"],
            fg=_PALETTE["text_jarvis"],
            font=self.fn["chat"],
            wrap=tk.WORD,
            bd=0,
            highlightthickness=0,
            state=tk.DISABLED,
            padx=16,
            pady=12,
            spacing1=4,
            spacing2=2,
            spacing3=8,
            cursor="arrow",
            yscrollcommand=sb.set,
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.chat_text.yview)

        self.chat_text.tag_config("user_lbl", foreground="#0088cc", font=self.fn["hud"])
        self.chat_text.tag_config(
            "user_msg",
            foreground=_PALETTE["text_user"],
            font=self.fn["chat"],
            lmargin1=8,
            lmargin2=8,
        )
        self.chat_text.tag_config(
            "jarvis_lbl", foreground="#00aaff", font=self.fn["hud"]
        )
        self.chat_text.tag_config(
            "jarvis_msg",
            foreground=_PALETTE["text_jarvis"],
            font=self.fn["chat"],
            lmargin1=8,
            lmargin2=8,
        )
        self.chat_text.tag_config(
            "sep", foreground=_PALETTE["sep"], font=self.fn["hud"]
        )

        # ── Giriş paneli ──
        iy = py + ph + 10
        inp_frame = tk.Frame(
            self.root,
            bg=_PALETTE["input_bg"],
            highlightthickness=1,
            highlightbackground="#003355",
        )
        inp_frame.place(x=px, y=iy, width=pw, height=52)

        self.input_var = tk.StringVar()
        entry = tk.Entry(
            inp_frame,
            textvariable=self.input_var,
            bg=_PALETTE["input_bg"],
            fg="#00ffff",
            font=self.fn["input"],
            bd=0,
            insertbackground="#00ffff",
            highlightthickness=0,
        )
        entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 4), pady=12)
        entry.bind("<Return>", self._on_send)

        send_btn = tk.Button(
            inp_frame,
            text="GÖNDƏR",
            bg=_PALETTE["btn_bg"],
            fg="#00cfff",
            font=self.fn["small"],
            bd=0,
            activebackground="#002a4d",
            activeforeground="#00ffff",
            cursor="hand2",
            relief=tk.FLAT,
            command=self._on_send,
            padx=12,
        )
        send_btn.pack(side=tk.RIGHT, padx=(4, 10), pady=10)

        # ── İnfo sətri ──
        info_y = iy + 58
        tk.Label(
            self.root,
            text="🎙 Avtomatik dinləyir  ·  ESC / F11 ekran  ·  Mic düyməsinə klik",
            bg=_PALETTE["bg"],
            fg="#001a33",
            font=self.fn["hud"],
        ).place(x=px, y=info_y)

        # Klik handler
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # İlk mesaj
        self.add_chat(
            "jarvis",
            f"Salam, Cənab {OWNER_NAME.split()[0]}. Bütün sistemlər aktiv vəziyyətdədir. "
            "Mən JARVIS — sizin şəxsi süni intellekt köməkçiniz. "
            "Bu gün sizə necə kömək edə bilərəm?",
        )

    # ═══════════════════════════════════════════════════════════════
    #   CHAT
    # ═══════════════════════════════════════════════════════════════
    def add_chat(self, role: str, text: str) -> None:
        """Thread-safe chat əlavə et."""
        self.root.after(0, self._insert_chat, role, text)

    def _insert_chat(self, role: str, text: str) -> None:
        ts = time.strftime("%H:%M")
        self.chat_text.config(state=tk.NORMAL)
        if role == "user":
            self.chat_text.insert(tk.END, f"  [ SİZ  {ts} ]\n", "user_lbl")
            self.chat_text.insert(tk.END, f"  {text}\n", "user_msg")
        else:
            self.chat_text.insert(tk.END, f"  [ JARVIS  {ts} ]\n", "jarvis_lbl")
            self.chat_text.insert(tk.END, f"  {text}\n", "jarvis_msg")
        self.chat_text.insert(tk.END, "  " + "─" * 48 + "\n", "sep")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    # ═══════════════════════════════════════════════════════════════
    #   KÖMƏKÇILƏR
    # ═══════════════════════════════════════════════════════════════
    def _on_send(self, _event=None) -> None:
        text = self.input_var.get().strip()
        if text:
            self.input_var.set("")
            self._on_text_input(text)

    def _on_canvas_click(self, event: tk.Event) -> None:
        bx = int(self.W * 0.26)
        by = int(self.H * 0.50) + 260
        if (event.x - bx) ** 2 + (event.y - by) ** 2 <= 32**2:
            self._on_mic_toggle()

    def set_status(self, status: str) -> None:
        self.status = status

    def _status_colors(self) -> tuple[str, str, str]:
        return _PALETTE.get(self.status, _PALETTE["ready"])  # type: ignore

    # ═══════════════════════════════════════════════════════════════
    #   PARTİKULLAR
    # ═══════════════════════════════════════════════════════════════
    def _init_particles(self) -> None:
        for _ in range(UI_PARTICLES):
            self.particles.append(
                {
                    "x": random.uniform(0, 1920),
                    "y": random.uniform(0, 1080),
                    "vx": random.uniform(-0.3, 0.3),
                    "vy": random.uniform(-0.3, 0.3),
                    "r": random.uniform(0.8, 2.5),
                    "col": random.choice(["#001a2e", "#002233", "#001833", "#003344"]),
                }
            )

    def _move_particles(self) -> None:
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0:
                p["x"] = self.W
            if p["x"] > self.W:
                p["x"] = 0
            if p["y"] < 0:
                p["y"] = self.H
            if p["y"] > self.H:
                p["y"] = 0

    # ═══════════════════════════════════════════════════════════════
    #   ÇƏKMƏ
    # ═══════════════════════════════════════════════════════════════
    def _draw(self) -> None:
        c = self.canvas
        W, H = self.W, self.H
        cx = int(W * 0.26)
        cy = int(H * 0.50)
        c.delete("all")

        mc, sc, dc = self._status_colors()

        # ── Fon ──
        c.create_rectangle(0, 0, W, H, fill="#000000", outline="")
        for i in range(0, H, 5):
            t = 1.0 - abs(i / H - 0.5) * 2
            v = int(t * t * 13)
            col = f"#{v:02x}{min(v + 2, 15):02x}{min(v * 3, 40):02x}"
            c.create_line(0, i, W, i, fill=col)

        # Scanline
        self.scanline_y = (self.scanline_y + 3) % H
        c.create_line(0, self.scanline_y, W, self.scanline_y, fill="#002233", width=1)

        # ── Partikullar ──
        self._move_particles()
        for p in self.particles:
            c.create_oval(
                p["x"] - p["r"],
                p["y"] - p["r"],
                p["x"] + p["r"],
                p["y"] + p["r"],
                fill=p["col"],
                outline="",
            )

        # ── Reaktor glow ──
        pr = int(72 + 16 * math.sin(self.pulse))
        for gr in range(pr + 55, pr + 5, -8):
            ratio = 1.0 - (gr - pr) / 55.0
            a = max(0, int(ratio * ratio * 40))
            c.create_oval(
                cx - gr,
                cy - gr,
                cx + gr,
                cy + gr,
                outline=f"#{a // 4:02x}{min(a * 2, 255):02x}{min(a * 3, 255):02x}",
                width=1,
            )

        # ── Halqalar ──
        ring_cfgs = [
            (240, 2, 1.0, False, (10, 14)),
            (200, 1, 1.5, True, (6, 18)),
            (165, 2, 0.8, False, (14, 8)),
            (132, 1, 2.2, True, (4, 12)),
            (105, 2, 1.2, False, (8, 10)),
            (80, 1, 1.8, True, (3, 8)),
        ]
        for i, (radius, width, speed, rev, dash) in enumerate(ring_cfgs):
            offset = self.angle * speed * (-1 if rev else 1)
            extent = (
                random.choice([260, 300, 330]) if self.status == "speaking" else 305
            )
            col = mc if i % 3 == 0 else (sc if i % 3 == 1 else dc)
            c.create_arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                start=offset,
                extent=extent,
                outline=col,
                width=width,
                style=tk.ARC,
                dash=dash,
            )

        # SIRI dalğa halqaları
        if self.status in ("speaking", "listening"):
            for wr in range(50, 260, 18):
                wob = int(8 * math.sin(self.pulse * 2 + wr * 0.05))
                r2 = wr + wob
                a = max(0, 30 - int(wr / 10))
                wc = f"#{a // 3:02x}{min(a * 2, 120):02x}{min(a * 3, 180):02x}"
                c.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline=wc, width=1)

        # Grid
        for ag in range(0, 360, 20):
            rad = math.radians(ag)
            c.create_line(
                cx,
                cy,
                cx + 230 * math.cos(rad),
                cy + 230 * math.sin(rad),
                fill="#010c18",
                width=1,
            )

        # ── Mərkəz reaktor ──
        rc = int(62 + 6 * math.sin(self.pulse * 1.4))
        c.create_oval(
            cx - rc, cy - rc, cx + rc, cy + rc, fill="#000a18", outline=mc, width=3
        )
        for qi in range(4):
            rad = math.radians(qi * 90 + self.angle * 3)
            dx = cx + 38 * math.cos(rad)
            dy = cy + 38 * math.sin(rad)
            c.create_oval(dx - 4, dy - 4, dx + 4, dy + 4, fill=mc, outline="")
        for di in range(8):
            rad = math.radians(di * 45 + self.angle * -2)
            dx = cx + 24 * math.cos(rad)
            dy = cy + 24 * math.sin(rad)
            c.create_oval(dx - 2, dy - 2, dx + 2, dy + 2, fill=sc, outline="")
        c.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill=mc, outline="")
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#ffffff", outline="")

        # ── Dalğa göstəriciləri ──
        if self.status == "speaking":
            bars = 32
            bw = 5
            bx0 = cx - (bars * (bw + 2)) // 2
            by0 = cy + 120
            for i in range(bars):
                hb = (
                    6
                    + int(20 * math.sin(self.pulse * 4 + i * 0.4))
                    + random.randint(0, 25)
                )
                c.create_rectangle(
                    bx0 + i * (bw + 2),
                    by0 - hb,
                    bx0 + i * (bw + 2) + bw,
                    by0,
                    fill=mc,
                    outline="",
                )
        elif self.status == "listening":
            pts = []
            by0 = cy + 130
            for xi in range(cx - 120, cx + 120, 3):
                ph2 = (xi - cx) / 15.0
                pts.append((xi, by0 + int(14 * math.sin(ph2 + self.pulse * 3))))
            for i in range(len(pts) - 1):
                alpha = 1.0 - abs(pts[i][0] - cx) / 120.0
                a = max(0, int(alpha * 180))
                lc = f"#{a // 4:02x}{min(a, 255):02x}{min(a, 255):02x}"
                c.create_line(
                    pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], fill=lc, width=2
                )
        elif self.status == "thinking":
            for i in range(12):
                rad = math.radians(i * 30 + self.angle * 4)
                px2 = cx + 100 * math.cos(rad)
                py2 = cy + 100 * math.sin(rad)
                br = 0.4 + 0.6 * ((i / 12.0 + self.angle / 360.0) % 1.0)
                a = max(30, int(br * 200))
                c.create_oval(
                    px2 - 4,
                    py2 - 4,
                    px2 + 4,
                    py2 + 4,
                    fill=f"#{a // 3:02x}{a // 2:02x}00",
                    outline="",
                )

        # ── Status mətni ──
        labels = {
            "ready": "●  SİSTEM HAZIRDIR",
            "listening": "◉  DİNLƏYİRƏM...",
            "thinking": "◈  ANALİZ EDİRƏM...",
            "speaking": "◎  DANIŞIRAM...",
            "muted": "✕  MİKROFON SÖNDÜRÜLÜB",
            "error": "⚠  XƏTA BAŞVERDI",
        }
        c.create_text(
            cx + 1,
            cy + 179,
            text=labels.get(self.status, "● HAZIR"),
            fill="#000000",
            font=self.fn["status"],
            anchor=tk.CENTER,
        )
        c.create_text(
            cx,
            cy + 178,
            text=labels.get(self.status, "● HAZIR"),
            fill=mc,
            font=self.fn["status"],
            anchor=tk.CENTER,
        )

        # ── Başlıq ──
        c.create_text(
            cx + 1,
            47,
            text="J . A . R . V . I . S",
            fill="#000000",
            font=self.fn["title"],
            anchor=tk.CENTER,
        )
        c.create_text(
            cx,
            46,
            text="J . A . R . V . I . S",
            fill=mc,
            font=self.fn["title"],
            anchor=tk.CENTER,
        )
        c.create_text(
            cx,
            74,
            text="JUST A RATHER VERY INTELLIGENT SYSTEM",
            fill=dc,
            font=self.fn["sub"],
            anchor=tk.CENTER,
        )

        # ── HUD ──
        hud = [
            "SİSTEM      : ONLİNE",
            "AI MODEL    : LLaMA-3",
            "SƏS MÜHİTİ : ElevenLabs",
            f"İSTİFADƏÇİ : {OWNER_NAME}",
            "─────────────────────",
            f"SAAT        : {time.strftime('%H:%M:%S')}",
            f"TARİX       : {time.strftime('%d.%m.%Y')}",
        ]
        for i, line in enumerate(hud):
            c.create_text(
                28,
                H - 185 + i * 17,
                text=line,
                fill=_PALETTE["text_hud"],
                font=self.fn["hud"],
                anchor=tk.W,
            )

        c.create_text(
            W - 28,
            H - 22,
            text="JARVIS v3.0  ·  Iron Man Interface",
            fill="#001a33",
            font=self.fn["hud"],
            anchor=tk.E,
        )

        # Ayırıcı
        sep_x = int(W * 0.505)
        c.create_line(sep_x, 20, sep_x, H - 20, fill="#001833", width=1, dash=(8, 10))

        # ── Mic düyməsi ──
        bx2 = int(W * 0.26)
        by2 = int(H * 0.50) + 260
        r2 = 30
        mic_on = self._mic_active()

        if mic_on:
            self.mic_pulse += 0.07
            for ri in range(3):
                pr2 = r2 + 14 + ri * 12 + int(6 * math.sin(self.mic_pulse + ri))
                a = max(0, 50 - ri * 16 - int(30 * abs(math.sin(self.mic_pulse + ri))))
                c.create_oval(
                    bx2 - pr2,
                    by2 - pr2,
                    bx2 + pr2,
                    by2 + pr2,
                    outline=f"#00{min(a * 3, 200):02x}{min(a * 2, 150):02x}",
                    width=1,
                )

        c.create_oval(
            bx2 - r2,
            by2 - r2,
            bx2 + r2,
            by2 + r2,
            fill="#001208" if mic_on else "#120000",
            outline="#00ff88" if mic_on else "#ff3333",
            width=2,
        )

        mic_col = "#00ff88" if mic_on else "#ff4444"
        c.create_rectangle(
            bx2 - 7, by2 - 14, bx2 + 7, by2 + 3, fill=mic_col, outline=""
        )
        c.create_arc(
            bx2 - 7,
            by2 - 18,
            bx2 + 7,
            by2 - 10,
            start=0,
            extent=180,
            fill=mic_col,
            outline="",
        )
        c.create_arc(
            bx2 - 13,
            by2 - 5,
            bx2 + 13,
            by2 + 15,
            start=0,
            extent=180,
            outline=mic_col,
            width=2,
            style=tk.ARC,
        )
        c.create_line(bx2, by2 + 15, bx2, by2 + 22, fill=mic_col, width=2)
        c.create_line(bx2 - 7, by2 + 22, bx2 + 7, by2 + 22, fill=mic_col, width=2)

        if not mic_on:
            c.create_line(
                bx2 - 20, by2 - 18, bx2 + 20, by2 + 20, fill="#ff3333", width=3
            )

        lbl = "MİKROFON SÖNDÜR" if mic_on else "MİKROFON AÇ"
        c.create_text(
            bx2,
            by2 + r2 + 16,
            text=lbl,
            fill="#004422" if mic_on else "#440000",
            font=self.fn["hud"],
            anchor=tk.CENTER,
        )

    # ═══════════════════════════════════════════════════════════════
    #   ƏSAS DÖNGƏ
    # ═══════════════════════════════════════════════════════════════
    def _update_loop(self) -> None:
        self.angle += 0.6
        self.pulse += 0.055
        self.scanline_y = (self.scanline_y + 3) % self.H

        # Status queue
        try:
            while True:
                self.status = self._status_q.get_nowait()
        except queue.Empty:
            pass

        # Chat queue
        try:
            while True:
                role, text = self._chat_q.get_nowait()
                self.add_chat(role, text)
        except queue.Empty:
            pass

        self._draw()
        interval = max(16, 1000 // UI_FPS)
        self.root.after(interval, self._update_loop)

    # ═══════════════════════════════════════════════════════════════
    #   RUN
    # ═══════════════════════════════════════════════════════════════
    def run(self) -> None:
        self._update_loop()
        self.root.mainloop()
