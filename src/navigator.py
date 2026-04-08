from __future__ import annotations

import random
import time
import math

import pyautogui

from .config import Config
from .detector import Detection
from .utils import setup_logger

logger = setup_logger("navigator")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class Navigator:
    """Controls mouse movement and clicking to collect detected items."""

    def __init__(self, config: Config):
        self._config = config
        self._last_click_time = 0.0
        self._last_move_time = 0.0
        self._last_target: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def click_nearest(
        self, detections: list[Detection], reference: tuple[int, int] | None = None
    ) -> Detection | None:
        """Click on the nearest detection relative to *reference* (screen center by default)."""
        if not detections:
            return None

        if reference is None:
            region = self._config.screen_region
            reference = (
                region["left"] + region["width"] // 2,
                region["top"] + region["height"] // 2,
            )

        nearest = min(detections, key=lambda d: self._distance(d.center, reference))
        self._click_at(*self._screen_coords(nearest.center))
        logger.info(
            "Clicking %s at (%d, %d) conf=%.2f",
            nearest.label,
            *nearest.center,
            nearest.confidence,
        )
        return nearest

    def random_walk(self):
        """Click a random point within the game area to roam around."""
        now = time.time()
        min_delay, max_delay = self._config.move_delay
        if now - self._last_move_time < random.uniform(min_delay, max_delay):
            return

        region = self._config.screen_region
        cx = region["left"] + region["width"] // 2
        cy = region["top"] + region["height"] // 2
        radius = self._config.random_walk_radius

        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(radius * 0.3, radius)
        tx = int(cx + dist * math.cos(angle))
        ty = int(cy + dist * math.sin(angle))

        tx = max(region["left"] + 50, min(tx, region["left"] + region["width"] - 50))
        ty = max(region["top"] + 50, min(ty, region["top"] + region["height"] - 50))

        self._move_and_click(tx, ty)
        self._last_move_time = now
        logger.debug("Random walk to (%d, %d)", tx, ty)

    def flee(self):
        """Attempt to flee by clicking near a map edge (toward the portal)."""
        region = self._config.screen_region
        edge_x = region["left"] + random.choice([50, region["width"] - 50])
        edge_y = region["top"] + random.choice([50, region["height"] - 50])

        self._move_and_click(edge_x, edge_y)
        logger.warning("FLEEING -> clicked (%d, %d)", edge_x, edge_y)

    def click_respawn(self):
        """Click the center of the screen where the respawn button typically appears."""
        region = self._config.screen_region
        cx = region["left"] + region["width"] // 2
        cy = region["top"] + region["height"] // 2 + 100
        self._click_at(cx, cy)
        logger.info("Clicked respawn at (%d, %d)", cx, cy)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _screen_coords(self, detection_center: tuple[int, int]) -> tuple[int, int]:
        """Convert detection-relative coords to absolute screen coords."""
        region = self._config.screen_region
        return (
            region["left"] + detection_center[0],
            region["top"] + detection_center[1],
        )

    def _click_at(self, sx: int, sy: int):
        """Move to (sx, sy) with slight randomisation and click."""
        now = time.time()
        min_delay, max_delay = self._config.click_delay
        wait = random.uniform(min_delay, max_delay)
        elapsed = now - self._last_click_time
        if elapsed < wait:
            time.sleep(wait - elapsed)

        offset_x = random.randint(-3, 3)
        offset_y = random.randint(-3, 3)
        target_x = sx + offset_x
        target_y = sy + offset_y

        duration = random.uniform(0.08, 0.25)
        pyautogui.moveTo(target_x, target_y, duration=duration)
        pyautogui.click()

        self._last_click_time = time.time()
        self._last_target = (target_x, target_y)

    def _move_and_click(self, sx: int, sy: int):
        duration = random.uniform(0.15, 0.4)
        pyautogui.moveTo(sx, sy, duration=duration)
        pyautogui.click()
        self._last_move_time = time.time()

    @staticmethod
    def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])
