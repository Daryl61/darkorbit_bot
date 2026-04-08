"""DarkOrbit Collection Bot -- main entry point.

Usage:
    python -m src.main          (launches the Tkinter control panel)
    python -m src.main --nogui  (headless mode, controlled via hotkeys)
"""
from __future__ import annotations

import sys
import time
import threading

from .config import Config
from .capture import ScreenCapture
from .detector import ObjectDetector
from .navigator import Navigator
from .safety import SafetyModule
from .state import StateManager, BotState
from .utils import setup_logger, FPSCounter

logger = setup_logger("main")


class DarkOrbitBot:
    """Top-level bot controller that orchestrates every module."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.capture = ScreenCapture(self.config)
        self.detector = ObjectDetector(self.config)
        self.navigator = Navigator(self.config)
        self.safety = SafetyModule(self.config)
        self.state = StateManager()

        self._running = False
        self._thread: threading.Thread | None = None
        self._fps = FPSCounter()
        self._debug_view = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._running:
            logger.warning("Bot is already running.")
            return
        self.state.start()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Bot started.")

    def stop(self):
        self._running = False
        self.state.stop()
        self.capture.release()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Bot stopped. %s", self._summary())

    def toggle_pause(self):
        if self.state.state == BotState.PAUSED:
            self.state.resume()
            logger.info("Bot resumed.")
        elif self.state.is_running():
            self.state.pause()
            logger.info("Bot paused.")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self):
        target_delay = 1.0 / max(self.config.capture_fps, 1)

        while self._running:
            loop_start = time.perf_counter()

            if self.state.state == BotState.PAUSED:
                time.sleep(0.2)
                continue

            if self.state.state == BotState.STOPPED:
                break

            try:
                self._tick()
            except Exception:
                logger.exception("Error in bot loop")
                time.sleep(1)

            elapsed = time.perf_counter() - loop_start
            sleep_time = target_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            self._fps.tick()

    def _tick(self):
        """Single iteration of the bot logic."""
        frame = self.capture.grab()

        # --- Safety first ---
        if self.safety.should_check():
            hp = self.safety.check_hp(frame)

            if self.safety.is_dead():
                self.state.transition(BotState.DEAD)
                self.state.stats.deaths += 1
                logger.warning("Ship destroyed! Deaths: %d", self.state.stats.deaths)
                time.sleep(3)
                self.navigator.click_respawn()
                time.sleep(5)
                self.state.transition(BotState.IDLE)
                return

            if self.config.flee_enabled and self.safety.is_critical():
                if self.state.state != BotState.FLEEING:
                    self.state.transition(BotState.FLEEING)
                    self.state.stats.flee_count += 1
                    logger.warning("HP critical (%.0f%%), fleeing!", hp)
                self.navigator.flee()
                return

            if self.state.state == BotState.FLEEING and not self.safety.is_critical():
                logger.info("HP recovered (%.0f%%), resuming collection.", hp)
                self.state.transition(BotState.IDLE)

        # --- Detect objects ---
        detections = self.detector.detect(frame)

        if detections:
            if self.state.state != BotState.COLLECTING:
                self.state.transition(BotState.COLLECTING)

            clicked = self.navigator.click_nearest(detections)
            if clicked:
                self.state.stats.boxes_collected += 1
                time.sleep(self.config.collection_wait)
        else:
            if self.state.state != BotState.MOVING:
                self.state.transition(BotState.MOVING)
            self.navigator.random_walk()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _summary(self) -> str:
        s = self.state.stats
        return (
            f"Boxes: {s.boxes_collected} | Deaths: {s.deaths} | "
            f"Flees: {s.flee_count} | Runtime: {s.runtime_str}"
        )


def run_headless():
    """Run the bot without GUI, using keyboard listener for start/stop."""
    import keyboard  # optional dependency for headless mode

    config = Config()
    bot = DarkOrbitBot(config)

    def on_start_stop():
        if bot._running:
            bot.stop()
        else:
            bot.start()

    def on_pause():
        bot.toggle_pause()

    keyboard.add_hotkey(config.hotkey_start_stop, on_start_stop)
    keyboard.add_hotkey(config.hotkey_pause_resume, on_pause)

    logger.info(
        "Headless mode. Press %s to start/stop, %s to pause/resume.",
        config.hotkey_start_stop,
        config.hotkey_pause_resume,
    )

    try:
        keyboard.wait("esc")
    except KeyboardInterrupt:
        pass
    finally:
        bot.stop()


def main():
    if "--nogui" in sys.argv:
        run_headless()
    else:
        from .ui import launch_ui
        launch_ui()


if __name__ == "__main__":
    main()
