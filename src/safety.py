from __future__ import annotations

import time

import cv2
import numpy as np

from .config import Config
from .utils import setup_logger

logger = setup_logger("safety")


class SafetyModule:
    """Monitors HP bar and detects threats to trigger flee/respawn."""

    HP_GREEN_LOWER = np.array([35, 100, 100], dtype=np.uint8)
    HP_GREEN_UPPER = np.array([85, 255, 255], dtype=np.uint8)
    HP_RED_LOWER = np.array([0, 100, 100], dtype=np.uint8)
    HP_RED_UPPER = np.array([10, 255, 255], dtype=np.uint8)

    def __init__(self, config: Config):
        self._config = config
        self._last_check = 0.0
        self._last_hp: float = 100.0
        self._hp_history: list[float] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def should_check(self) -> bool:
        return time.time() - self._last_check >= self._config.safety_check_interval

    def check_hp(self, frame: np.ndarray) -> float:
        """Return estimated HP percentage (0-100) from the HP bar region."""
        self._last_check = time.time()
        hp_region = self._crop_hp_bar(frame)
        if hp_region is None or hp_region.size == 0:
            return self._last_hp

        hp_pct = self._estimate_hp(hp_region)
        self._hp_history.append(hp_pct)
        if len(self._hp_history) > 20:
            self._hp_history.pop(0)

        self._last_hp = hp_pct
        return hp_pct

    def is_critical(self) -> bool:
        return self._last_hp <= self._config.hp_critical_percent

    def is_taking_damage(self) -> bool:
        """True if HP dropped significantly in recent checks."""
        if len(self._hp_history) < 3:
            return False
        recent = self._hp_history[-3:]
        return recent[0] - recent[-1] > 10

    def is_dead(self) -> bool:
        return self._last_hp <= 0

    @property
    def hp(self) -> float:
        return self._last_hp

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _crop_hp_bar(self, frame: np.ndarray) -> np.ndarray | None:
        r = self._config.hp_bar_region
        top, left = r["top"], r["left"]
        bottom = top + r["height"]
        right = left + r["width"]

        if bottom > frame.shape[0] or right > frame.shape[1]:
            logger.warning("HP bar region out of frame bounds")
            return None

        return frame[top:bottom, left:right]

    def _estimate_hp(self, hp_bar: np.ndarray) -> float:
        """Estimate HP % by measuring the ratio of green/red pixels in the bar."""
        hsv = cv2.cvtColor(hp_bar, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(hsv, self.HP_GREEN_LOWER, self.HP_GREEN_UPPER)
        red_mask = cv2.inRange(hsv, self.HP_RED_LOWER, self.HP_RED_UPPER)

        green_pixels = cv2.countNonZero(green_mask)
        red_pixels = cv2.countNonZero(red_mask)
        total = green_pixels + red_pixels

        if total == 0:
            return self._last_hp

        return (green_pixels / total) * 100.0
