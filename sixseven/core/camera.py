"""Camera capture running on a dedicated QThread.

Emits frames as QImage to avoid cross-thread OpenCV window issues and
integrates cleanly with PySide6 signals/slots.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QMutex, QThread, Signal


class CameraThread(QThread):
    """Captures frames from a webcam in a background thread.

    Signals:
        frame_ready(np.ndarray): Emitted for every captured BGR frame.
        error(str): Emitted when the camera cannot be opened.
    """

    frame_ready = Signal(np.ndarray)
    error = Signal(str)

    def __init__(self, camera_index: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        self._running = False
        self._mutex = QMutex()
        self._mirror = True

    # --- public -------------------------------------------------------

    def set_camera(self, index: int) -> None:
        self._mutex.lock()
        self._camera_index = index
        self._mutex.unlock()

    def set_mirror(self, enabled: bool) -> None:
        self._mirror = enabled

    def stop(self) -> None:
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
        self.wait(5000)

    # --- QThread ------------------------------------------------------

    def run(self) -> None:
        self._running = True
        cap = cv2.VideoCapture(self._camera_index)

        if not cap.isOpened():
            self.error.emit(f"Cannot open camera {self._camera_index}")
            return

        while True:
            self._mutex.lock()
            running = self._running
            self._mutex.unlock()
            if not running:
                break

            ok, frame = cap.read()
            if not ok:
                continue

            if self._mirror:
                frame = cv2.flip(frame, 1)

            self.frame_ready.emit(frame)
            self.msleep(1)  # yield to event loop

        cap.release()
