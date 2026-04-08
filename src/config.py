import json
import os
from typing import Any

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "settings.json"
)
TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "templates"
)


class Config:
    """Loads and provides access to bot settings from settings.json."""

    def __init__(self, path: str | None = None):
        self._path = path or CONFIG_PATH
        self._data: dict[str, Any] = {}
        self.reload()

    def reload(self):
        with open(self._path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, ensure_ascii=False)

    # --- Screen region ---
    @property
    def screen_region(self) -> dict:
        return self._data["screen_region"]

    @property
    def capture_fps(self) -> int:
        return self._data.get("capture_fps", 10)

    # --- Detection ---
    @property
    def template_threshold(self) -> float:
        return self._data["detection"]["template_threshold"]

    @property
    def color_detection_enabled(self) -> bool:
        return self._data["detection"].get("color_detection_enabled", True)

    @property
    def nms_threshold(self) -> int:
        return self._data["detection"].get("nms_threshold", 30)

    @property
    def bonus_box_hsv(self) -> dict:
        return self._data["detection"]["bonus_box_hsv"]

    # --- Navigator ---
    @property
    def click_delay(self) -> tuple[float, float]:
        nav = self._data["navigator"]
        return nav["click_delay_min"], nav["click_delay_max"]

    @property
    def move_delay(self) -> tuple[float, float]:
        nav = self._data["navigator"]
        return nav["move_delay_min"], nav["move_delay_max"]

    @property
    def random_walk_radius(self) -> int:
        return self._data["navigator"]["random_walk_radius"]

    @property
    def collection_wait(self) -> float:
        return self._data["navigator"]["collection_wait"]

    # --- Safety ---
    @property
    def hp_bar_region(self) -> dict:
        return self._data["safety"]["hp_bar_region"]

    @property
    def hp_critical_percent(self) -> int:
        return self._data["safety"]["hp_critical_percent"]

    @property
    def flee_enabled(self) -> bool:
        return self._data["safety"].get("flee_enabled", True)

    @property
    def safety_check_interval(self) -> float:
        return self._data["safety"].get("check_interval", 0.5)

    # --- Hotkeys ---
    @property
    def hotkey_start_stop(self) -> str:
        return self._data["hotkeys"]["start_stop"]

    @property
    def hotkey_pause_resume(self) -> str:
        return self._data["hotkeys"]["pause_resume"]

    # --- Generic access ---
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    @property
    def raw(self) -> dict:
        return self._data
