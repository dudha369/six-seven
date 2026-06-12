"""Virtual camera output for streaming the processed feed to Discord.

Works like VB-Cable but for video: creates a virtual webcam that Discord
(or OBS, Zoom, etc.) can select as a camera source.

Requirements:
* **Windows:** Install OBS and enable the OBS Virtual Camera, or use
  `UnityCapture`.  ``pyvirtualcam`` will use the first available backend.
* **Linux:** ``sudo modprobe v4l2loopback devices=1 video_nr=10
  card_label="SixSeven" exclusive_caps=1``
* **macOS:** Install OBS (provides the virtual camera automatically).

The module is optional — if ``pyvirtualcam`` is not installed or no
backend is available, the app works normally without virtual camera.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    import pyvirtualcam

_HAS_PYVIRTUALCAM = False
try:
    import pyvirtualcam as _pvc

    _HAS_PYVIRTUALCAM = True
except ImportError:
    _pvc = None  # type: ignore[assignment]


class VirtualCamera:
    """Wraps ``pyvirtualcam`` behind a thread-safe interface.

    Usage::

        vcam = VirtualCamera(1280, 720)
        vcam.start()          # opens the virtual device
        vcam.send(bgr_frame)  # push a frame (BGR, any size — resized internally)
        vcam.stop()
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ) -> None:
        self._width = width
        self._height = height
        self._fps = fps
        self._cam: pyvirtualcam.Camera | None = None
        self._lock = threading.Lock()
        self._active = False

    # --- public -------------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """Return True if pyvirtualcam is installed and a backend exists."""
        if not _HAS_PYVIRTUALCAM:
            return False
        try:
            with _pvc.Camera(width=2, height=2, fps=1) as _:
                pass
            return True
        except Exception:
            return False

    def start(self) -> bool:
        """Open the virtual camera. Returns True on success."""
        if not _HAS_PYVIRTUALCAM:
            print("[VirtualCamera] pyvirtualcam not installed — skipping.")
            return False
        with self._lock:
            if self._active:
                return True
            try:
                self._cam = _pvc.Camera(
                    width=self._width,
                    height=self._height,
                    fps=self._fps,
                )
                self._active = True
                print(f"[VirtualCamera] started → {self._cam.device}")
                return True
            except Exception as exc:
                print(f"[VirtualCamera] failed to start: {exc}")
                return False

    def send(self, bgr_frame: np.ndarray) -> None:
        """Send a BGR frame to the virtual camera (resized + converted)."""
        with self._lock:
            if not self._active or self._cam is None:
                return
        resized = cv2.resize(bgr_frame, (self._width, self._height))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        try:
            self._cam.send(rgb)
            self._cam.sleep_until_next_frame()
        except Exception:
            pass  # frame drop — non-critical

    def stop(self) -> None:
        with self._lock:
            if self._cam is not None:
                try:
                    self._cam.close()
                except Exception:
                    pass
                self._cam = None
            self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def device_name(self) -> str:
        with self._lock:
            if self._cam:
                return self._cam.device
        return ""
