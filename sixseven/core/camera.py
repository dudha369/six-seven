"""Camera capture running on a dedicated QThread.

Emits frames as numpy arrays and respects a configurable FPS cap
to avoid flooding the main thread with more frames than it can process.
"""

from __future__ import annotations

import time

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

    def __init__(
        self,
        camera_index: int = 0,
        target_fps: int = 30,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        self._target_fps = max(target_fps, 1)
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

        # Try to set camera resolution and FPS for lower latency
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, self._target_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_interval = 1.0 / self._target_fps

        while True:
            self._mutex.lock()
            running = self._running
            self._mutex.unlock()
            if not running:
                break

            t0 = time.perf_counter()

            ok, frame = cap.read()
            if not ok:
                self.msleep(5)
                continue

            if self._mirror:
                frame = cv2.flip(frame, 1)

            self.frame_ready.emit(frame)

            # Sleep to respect FPS cap — avoids CPU spin and frame flooding
            elapsed = time.perf_counter() - t0
            sleep_ms = max(1, int((frame_interval - elapsed) * 1000))
            self.msleep(sleep_ms)

        cap.release()
