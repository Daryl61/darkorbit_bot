"""Helper tool to capture template images from the game screen.

Usage:
    python -m src.template_capture

Instructions:
    1. Open DarkOrbit in your browser.
    2. Run this script.
    3. A full-screen screenshot will appear.
    4. Draw a rectangle around the object you want to use as a template.
    5. Enter a name (e.g. "bonus_box_purple") and it will be saved
       to config/templates/.
    6. Press 'q' to quit, or any other key to capture another template.
"""
from __future__ import annotations

import os
import cv2
import numpy as np
import mss

from .config import TEMPLATES_DIR


class TemplateCapturer:
    def __init__(self):
        self._sct = mss.mss()
        self._drawing = False
        self._start = (0, 0)
        self._end = (0, 0)
        self._image: np.ndarray | None = None
        self._clone: np.ndarray | None = None

    def run(self):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        print("=== DarkOrbit Template Capture Tool ===")
        print("Ekranin goruntusu alinacak. Cikan pencerede bir kutu etrafina dikdortgen cizin.")
        print("'q' = cikis | 's' = yeni ekran goruntusu | herhangi tus = tekrar yakala\n")

        while True:
            self._capture_screen()
            if self._image is None:
                break

            self._clone = self._image.copy()
            window = "Template Sec (dikdortgen ciz, sonra ENTER)"
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(window, self._mouse_cb)

            while True:
                display = self._clone.copy()
                if self._drawing:
                    cv2.rectangle(display, self._start, self._end, (0, 255, 0), 2)
                cv2.imshow(window, display)
                key = cv2.waitKey(30) & 0xFF

                if key == ord("q"):
                    cv2.destroyAllWindows()
                    print("Cikis yapildi.")
                    return
                if key == ord("s"):
                    break
                if key == 13:  # Enter
                    self._save_selection()

            cv2.destroyAllWindows()

    def _capture_screen(self):
        monitor = self._sct.monitors[0]
        raw = self._sct.grab(monitor)
        self._image = np.array(raw, dtype=np.uint8)[:, :, :3]
        print(f"Ekran yakalandi: {self._image.shape[1]}x{self._image.shape[0]}")

    def _mouse_cb(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._drawing = True
            self._start = (x, y)
            self._end = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self._drawing:
            self._end = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self._drawing = False
            self._end = (x, y)

    def _save_selection(self):
        x1, y1 = self._start
        x2, y2 = self._end
        if x1 == x2 or y1 == y2:
            print("Gecersiz secim, tekrar deneyin.")
            return

        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        cropped = self._image[top:bottom, left:right]

        if cropped.size == 0:
            print("Bos secim, tekrar deneyin.")
            return

        cv2.imshow("Onizleme", cropped)
        cv2.waitKey(500)

        name = input("Template ismi (orn: bonus_box_purple): ").strip()
        if not name:
            print("Isim bos, kaydedilmedi.")
            return

        if not name.endswith(".png"):
            name += ".png"

        path = os.path.join(TEMPLATES_DIR, name)
        cv2.imwrite(path, cropped)
        print(f"Kaydedildi: {path}  ({cropped.shape[1]}x{cropped.shape[0]} px)\n")


def main():
    capturer = TemplateCapturer()
    capturer.run()


if __name__ == "__main__":
    main()
