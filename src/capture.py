import time
import numpy as np
import mss

from .config import Config
from .utils import FPSCounter, setup_logger

logger = setup_logger("capture")


class ScreenCapture:
    """Captures the game window region at a target FPS using mss."""

    def __init__(self, config: Config):
        self._config = config
        self._sct = mss.mss()
        self._fps_counter = FPSCounter()
        self._frame: np.ndarray | None = None
        self._monitor = self._build_monitor()

    def _build_monitor(self) -> dict:
        r = self._config.screen_region
        return {
            "top": r["top"],
            "left": r["left"],
            "width": r["width"],
            "height": r["height"],
        }

    def update_region(self, top: int, left: int, width: int, height: int):
        self._monitor = {
            "top": top,
            "left": left,
            "width": width,
            "height": height,
        }
        logger.info("Screen region updated: %s", self._monitor)

    def grab(self) -> np.ndarray:
        """Capture a single frame and return it as a BGR numpy array."""
        raw = self._sct.grab(self._monitor)
        # mss returns BGRA; drop the alpha channel for OpenCV compatibility
        frame = np.array(raw, dtype=np.uint8)[:, :, :3]
        self._frame = frame
        self._fps_counter.tick()
        return frame

    @property
    def last_frame(self) -> np.ndarray | None:
        return self._frame

    @property
    def fps(self) -> float:
        return self._fps_counter.tick() if self._frame is not None else 0.0

    @property
    def monitor(self) -> dict:
        return dict(self._monitor)

    def release(self):
        self._sct.close()
        logger.info("Screen capture released.")
