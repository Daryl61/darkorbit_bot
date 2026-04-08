"""Tkinter control panel for the DarkOrbit bot."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from .config import Config
from .main import DarkOrbitBot
from .state import BotState
from .utils import setup_logger

logger = setup_logger("ui")

REFRESH_MS = 500


class BotControlPanel:
    """Simple Tkinter GUI to start/stop/pause the bot and view stats."""

    def __init__(self):
        self.config = Config()
        self.bot = DarkOrbitBot(self.config)

        self.root = tk.Tk()
        self.root.title("DarkOrbit Bot")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._update_loop()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Control frame ---
        ctrl = ttk.LabelFrame(self.root, text="Kontrol", padding=10)
        ctrl.grid(row=0, column=0, sticky="ew", **pad)

        self.btn_start = ttk.Button(ctrl, text="Baslat (F6)", command=self._toggle_start)
        self.btn_start.grid(row=0, column=0, **pad)

        self.btn_pause = ttk.Button(ctrl, text="Duraklat (F7)", command=self._toggle_pause, state="disabled")
        self.btn_pause.grid(row=0, column=1, **pad)

        self.btn_stop = ttk.Button(ctrl, text="Durdur", command=self._stop, state="disabled")
        self.btn_stop.grid(row=0, column=2, **pad)

        # --- Status frame ---
        status_frame = ttk.LabelFrame(self.root, text="Durum", padding=10)
        status_frame.grid(row=1, column=0, sticky="ew", **pad)

        self.lbl_state = ttk.Label(status_frame, text="Durum: DURDU", font=("Consolas", 11, "bold"))
        self.lbl_state.grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        self.lbl_hp = ttk.Label(status_frame, text="HP: ---%")
        self.lbl_hp.grid(row=1, column=0, sticky="w", **pad)

        self.lbl_fps = ttk.Label(status_frame, text="FPS: --")
        self.lbl_fps.grid(row=1, column=1, sticky="w", **pad)

        # --- Stats frame ---
        stats_frame = ttk.LabelFrame(self.root, text="Istatistikler", padding=10)
        stats_frame.grid(row=2, column=0, sticky="ew", **pad)

        self.lbl_boxes = ttk.Label(stats_frame, text="Kutu: 0")
        self.lbl_boxes.grid(row=0, column=0, sticky="w", **pad)

        self.lbl_deaths = ttk.Label(stats_frame, text="Olum: 0")
        self.lbl_deaths.grid(row=0, column=1, sticky="w", **pad)

        self.lbl_flees = ttk.Label(stats_frame, text="Kacis: 0")
        self.lbl_flees.grid(row=1, column=0, sticky="w", **pad)

        self.lbl_runtime = ttk.Label(stats_frame, text="Sure: 00:00:00")
        self.lbl_runtime.grid(row=1, column=1, sticky="w", **pad)

        # --- Screen region frame ---
        region_frame = ttk.LabelFrame(self.root, text="Ekran Bolgesi", padding=10)
        region_frame.grid(row=3, column=0, sticky="ew", **pad)

        labels = ["Sol (X):", "Ust (Y):", "Genislik:", "Yukseklik:"]
        keys = ["left", "top", "width", "height"]
        self._region_vars: dict[str, tk.IntVar] = {}

        for i, (lbl, key) in enumerate(zip(labels, keys)):
            ttk.Label(region_frame, text=lbl).grid(row=i // 2, column=(i % 2) * 2, sticky="e", **pad)
            var = tk.IntVar(value=self.config.screen_region[key])
            self._region_vars[key] = var
            ttk.Entry(region_frame, textvariable=var, width=8).grid(
                row=i // 2, column=(i % 2) * 2 + 1, sticky="w", **pad
            )

        ttk.Button(region_frame, text="Bolgeyi Guncelle", command=self._update_region).grid(
            row=2, column=0, columnspan=4, **pad
        )

        # --- Hotkeys ---
        self.root.bind(f"<{self.config.hotkey_start_stop}>", lambda e: self._toggle_start())
        self.root.bind(f"<{self.config.hotkey_pause_resume}>", lambda e: self._toggle_pause())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _toggle_start(self):
        if not self.bot._running:
            self.bot.start()
            self.btn_start.config(text="Calisiyor...", state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_stop.config(state="normal")
        else:
            self._stop()

    def _toggle_pause(self):
        self.bot.toggle_pause()
        if self.bot.state.state == BotState.PAUSED:
            self.btn_pause.config(text="Devam (F7)")
        else:
            self.btn_pause.config(text="Duraklat (F7)")

    def _stop(self):
        self.bot.stop()
        self.btn_start.config(text="Baslat (F6)", state="normal")
        self.btn_pause.config(text="Duraklat (F7)", state="disabled")
        self.btn_stop.config(state="disabled")

    def _update_region(self):
        try:
            self.bot.capture.update_region(
                top=self._region_vars["top"].get(),
                left=self._region_vars["left"].get(),
                width=self._region_vars["width"].get(),
                height=self._region_vars["height"].get(),
            )
        except Exception as exc:
            messagebox.showerror("Hata", str(exc))

    def _on_close(self):
        if self.bot._running:
            self.bot.stop()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Periodic UI refresh
    # ------------------------------------------------------------------

    def _update_loop(self):
        state = self.bot.state
        stats = state.stats

        state_names = {
            BotState.IDLE: "BEKLENIYOR",
            BotState.COLLECTING: "TOPLUYOR",
            BotState.MOVING: "HAREKET EDIYOR",
            BotState.FLEEING: "KACIYOR!",
            BotState.DEAD: "OLU",
            BotState.PAUSED: "DURAKLATILDI",
            BotState.STOPPED: "DURDU",
        }
        self.lbl_state.config(text=f"Durum: {state_names.get(state.state, '?')}")
        self.lbl_hp.config(text=f"HP: {self.bot.safety.hp:.0f}%")
        self.lbl_boxes.config(text=f"Kutu: {stats.boxes_collected}")
        self.lbl_deaths.config(text=f"Olum: {stats.deaths}")
        self.lbl_flees.config(text=f"Kacis: {stats.flee_count}")
        self.lbl_runtime.config(text=f"Sure: {stats.runtime_str}")

        self.root.after(REFRESH_MS, self._update_loop)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()


def launch_ui():
    panel = BotControlPanel()
    panel.run()
