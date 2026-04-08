from __future__ import annotations

import os
import glob
from dataclasses import dataclass

import cv2
import numpy as np

from .config import Config, TEMPLATES_DIR
from .utils import setup_logger

logger = setup_logger("detector")


@dataclass
class Detection:
    """A single detected object on screen."""

    x: int
    y: int
    w: int
    h: int
    confidence: float
    label: str
    source: str  # "template" or "color"

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    @property
    def area(self) -> int:
        return self.w * self.h


class ObjectDetector:
    """Detects collectible items via template matching and HSV color filtering."""

    def __init__(self, config: Config):
        self._config = config
        self._templates: list[tuple[str, np.ndarray]] = []
        self._load_templates()

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def _load_templates(self):
        """Load all template images from config/templates/."""
        self._templates.clear()
        if not os.path.isdir(TEMPLATES_DIR):
            logger.warning("Templates directory not found: %s", TEMPLATES_DIR)
            return

        patterns = ["*.png", "*.jpg", "*.bmp"]
        files: list[str] = []
        for pat in patterns:
            files.extend(glob.glob(os.path.join(TEMPLATES_DIR, pat)))

        for path in sorted(files):
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("Could not load template: %s", path)
                continue
            label = os.path.splitext(os.path.basename(path))[0]
            self._templates.append((label, img))
            logger.info("Loaded template '%s' (%dx%d)", label, img.shape[1], img.shape[0])

        if not self._templates:
            logger.warning(
                "No templates loaded. Place .png/.jpg images in %s", TEMPLATES_DIR
            )

    def reload_templates(self):
        self._load_templates()

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------

    def detect_by_template(self, frame: np.ndarray) -> list[Detection]:
        """Run template matching for every loaded template image."""
        detections: list[Detection] = []
        threshold = self._config.template_threshold

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for label, tmpl in self._templates:
            gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
            th, tw = gray_tmpl.shape[:2]

            if th > gray_frame.shape[0] or tw > gray_frame.shape[1]:
                continue

            result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)

            for pt_y, pt_x in zip(*locations):
                conf = float(result[pt_y, pt_x])
                detections.append(
                    Detection(
                        x=int(pt_x),
                        y=int(pt_y),
                        w=tw,
                        h=th,
                        confidence=conf,
                        label=label,
                        source="template",
                    )
                )

        return self._non_max_suppression(detections)

    # ------------------------------------------------------------------
    # Color-based detection (HSV)
    # ------------------------------------------------------------------

    def detect_by_color(self, frame: np.ndarray) -> list[Detection]:
        """Detect bonus-box-like blobs using HSV color ranges."""
        if not self._config.color_detection_enabled:
            return []

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detections: list[Detection] = []

        for color_name, bounds in self._config.bonus_box_hsv.items():
            lower = np.array(bounds["lower"], dtype=np.uint8)
            upper = np.array(bounds["upper"], dtype=np.uint8)

            mask = cv2.inRange(hsv, lower, upper)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 100 or area > 10000:
                    continue

                x, y, w, h = cv2.boundingRect(cnt)
                aspect = w / h if h > 0 else 0
                if aspect < 0.3 or aspect > 3.0:
                    continue

                detections.append(
                    Detection(
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                        confidence=min(area / 2000.0, 1.0),
                        label=f"box_{color_name}",
                        source="color",
                    )
                )

        return self._non_max_suppression(detections)

    # ------------------------------------------------------------------
    # Combined detection
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run all detection methods and merge results."""
        results = self.detect_by_template(frame)
        results.extend(self.detect_by_color(frame))
        merged = self._non_max_suppression(results)
        merged.sort(key=lambda d: d.confidence, reverse=True)
        return merged

    # ------------------------------------------------------------------
    # Non-maximum suppression
    # ------------------------------------------------------------------

    def _non_max_suppression(self, detections: list[Detection]) -> list[Detection]:
        """Remove overlapping detections, keeping the highest-confidence one."""
        if not detections:
            return []

        dist_thresh = self._config.nms_threshold
        detections.sort(key=lambda d: d.confidence, reverse=True)
        kept: list[Detection] = []

        for det in detections:
            cx, cy = det.center
            too_close = False
            for existing in kept:
                ex, ey = existing.center
                if abs(cx - ex) < dist_thresh and abs(cy - ey) < dist_thresh:
                    too_close = True
                    break
            if not too_close:
                kept.append(det)

        return kept

    # ------------------------------------------------------------------
    # Debug visualization
    # ------------------------------------------------------------------

    def draw_detections(
        self, frame: np.ndarray, detections: list[Detection]
    ) -> np.ndarray:
        """Draw bounding boxes and labels on a frame copy (for debugging)."""
        vis = frame.copy()
        for det in detections:
            color = (0, 255, 0) if det.source == "template" else (255, 200, 0)
            cv2.rectangle(vis, (det.x, det.y), (det.x + det.w, det.y + det.h), color, 2)
            text = f"{det.label} {det.confidence:.2f}"
            cv2.putText(
                vis, text, (det.x, det.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
            )
        return vis
