"""Improved SixSeven gesture detector using MediaPipe Tasks API.

Uses PoseLandmarker (modern Tasks API) instead of the deprecated
``mp.solutions.pose``.  The model file is auto-downloaded on first run
and cached in ``~/.sixseven/models/``.
"""

from __future__ import annotations

import enum
import time
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    PoseLandmarkerResult,
    PoseLandmarksConnections,
)
from mediapipe.tasks.python.vision.core.image import Image as MpImage, ImageFormat
from mediapipe.tasks.python.vision.core.vision_task_running_mode import (
    VisionTaskRunningMode,
)

# ---------------------------------------------------------------------------
# Model auto-download
# ---------------------------------------------------------------------------
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/latest/"
    "pose_landmarker_lite.task"
)
_MODEL_DIR = Path.home() / ".sixseven" / "models"
_MODEL_PATH = _MODEL_DIR / "pose_landmarker_lite.task"


def _ensure_model() -> str:
    """Download the pose-landmarker model if it doesn't exist yet."""
    if _MODEL_PATH.is_file():
        return str(_MODEL_PATH)
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Detector] Downloading model → {_MODEL_PATH} …")
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    print("[Detector] Download complete.")
    return str(_MODEL_PATH)


# ---------------------------------------------------------------------------
# Pose skeleton connections for drawing
# ---------------------------------------------------------------------------
_POSE_CONNECTIONS = PoseLandmarksConnections.POSE_LANDMARKS


class GestureState(enum.Enum):
    IDLE = "idle"
    DETECTING = "detecting"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"


@dataclass
class DetectionResult:
    """Holds per-frame detection output."""

    frame: np.ndarray
    state: GestureState = GestureState.IDLE
    triggered: bool = False
    left_angle: float = 0.0
    right_angle: float = 0.0
    confidence: float = 0.0


class GestureDetector:
    """Detects the SixSeven alternating-hand gesture via MediaPipe Pose.

    Improvements over the original:
    * Uses the modern MediaPipe Tasks API (``PoseLandmarker``).
    * Rolling-window smoothing of wrist Y positions to filter micro-jitter.
    * State machine (IDLE → DETECTING → TRIGGERED → COOLDOWN) to avoid
      duplicate triggers and provide UI-friendly status.
    * Configurable elbow-angle limit, movement threshold, and cooldown.
    * Separate ``detect`` (pure logic) from ``draw`` (visualisation).
    """

    # MediaPipe Pose landmark indices (BlazePose topology)
    _L_SHOULDER, _L_ELBOW, _L_WRIST = 11, 13, 15
    _R_SHOULDER, _R_ELBOW, _R_WRIST = 12, 14, 16

    def __init__(
        self,
        movement_threshold: float = 0.03,
        elbow_angle_limit: float = 110.0,
        cooldown_seconds: float = 1.0,
        smoothing_window: int = 5,
        show_landmarks: bool = True,
    ) -> None:
        self._threshold = movement_threshold
        self._angle_limit = elbow_angle_limit
        self._cooldown = cooldown_seconds
        self._smooth_n = max(smoothing_window, 1)
        self._show_landmarks = show_landmarks

        # ---- MediaPipe Tasks PoseLandmarker ----
        model_path = _ensure_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionTaskRunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)
        self._frame_ts: int = 0  # monotonically increasing timestamp (ms)

        # Smoothing buffers (deques of Y-values)
        self._left_y_buf: deque[float] = deque(maxlen=self._smooth_n)
        self._right_y_buf: deque[float] = deque(maxlen=self._smooth_n)
        self._prev_left_y: float | None = None
        self._prev_right_y: float | None = None

        # State machine
        self._state = GestureState.IDLE
        self._last_trigger_time: float = 0.0

        # Consecutive detection counter for DETECTING → TRIGGERED
        self._detect_streak: int = 0
        self._STREAK_THRESHOLD = 2  # need N consecutive frames

    # --- public API ---------------------------------------------------

    def process(self, frame: np.ndarray) -> DetectionResult:
        """Run detection on *frame* (BGR) and return annotated result."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create MediaPipe Image and run pose detection
        mp_image = MpImage(image_format=ImageFormat.SRGB, data=rgb)
        self._frame_ts += 33  # ~30 fps increments
        pose_result: PoseLandmarkerResult = self._landmarker.detect_for_video(
            mp_image, self._frame_ts
        )

        result = DetectionResult(frame=frame, state=self._state)

        if not pose_result.pose_landmarks:
            self._reset_tracking()
            result.state = GestureState.IDLE
            return result

        # First detected person's landmarks
        landmarks = pose_result.pose_landmarks[0]

        if self._show_landmarks:
            self._draw_landmarks(frame, landmarks)

        l_angle = self._angle(landmarks, self._L_SHOULDER, self._L_ELBOW, self._L_WRIST)
        r_angle = self._angle(landmarks, self._R_SHOULDER, self._R_ELBOW, self._R_WRIST)
        result.left_angle = l_angle
        result.right_angle = r_angle

        elbows_bent = l_angle < self._angle_limit and r_angle < self._angle_limit

        # Smooth wrist Y
        self._left_y_buf.append(landmarks[self._L_WRIST].y)
        self._right_y_buf.append(landmarks[self._R_WRIST].y)
        curr_left_y = float(np.mean(self._left_y_buf))
        curr_right_y = float(np.mean(self._right_y_buf))

        gesture_detected = False
        if elbows_bent and self._prev_left_y is not None:
            dy_l = curr_left_y - self._prev_left_y
            dy_r = curr_right_y - self._prev_right_y  # type: ignore[operator]
            opposite = (dy_l * dy_r) < 0
            amplitude = abs(dy_l) > self._threshold and abs(dy_r) > self._threshold
            if opposite and amplitude:
                gesture_detected = True
                # Confidence based on amplitude relative to threshold
                amp = (abs(dy_l) + abs(dy_r)) / 2
                result.confidence = min(amp / (self._threshold * 3), 1.0)

        self._prev_left_y = curr_left_y
        self._prev_right_y = curr_right_y

        # State transitions
        now = time.monotonic()
        if self._state == GestureState.COOLDOWN:
            if now - self._last_trigger_time >= self._cooldown:
                self._state = GestureState.IDLE
                self._detect_streak = 0

        if self._state in (GestureState.IDLE, GestureState.DETECTING):
            if gesture_detected:
                self._detect_streak += 1
                if self._detect_streak >= self._STREAK_THRESHOLD:
                    self._state = GestureState.TRIGGERED
                    self._last_trigger_time = now
                    result.triggered = True
                else:
                    self._state = GestureState.DETECTING
            else:
                self._detect_streak = max(0, self._detect_streak - 1)
                if self._detect_streak == 0:
                    self._state = GestureState.IDLE

        if self._state == GestureState.TRIGGERED:
            self._state = GestureState.COOLDOWN

        result.state = self._state if not result.triggered else GestureState.TRIGGERED
        return result

    def update_settings(
        self,
        movement_threshold: float | None = None,
        elbow_angle_limit: float | None = None,
        cooldown_seconds: float | None = None,
        smoothing_window: int | None = None,
        show_landmarks: bool | None = None,
    ) -> None:
        if movement_threshold is not None:
            self._threshold = movement_threshold
        if elbow_angle_limit is not None:
            self._angle_limit = elbow_angle_limit
        if cooldown_seconds is not None:
            self._cooldown = cooldown_seconds
        if smoothing_window is not None:
            n = max(smoothing_window, 1)
            self._smooth_n = n
            self._left_y_buf = deque(self._left_y_buf, maxlen=n)
            self._right_y_buf = deque(self._right_y_buf, maxlen=n)
        if show_landmarks is not None:
            self._show_landmarks = show_landmarks

    def release(self) -> None:
        self._landmarker.close()

    # --- internals ----------------------------------------------------

    def _reset_tracking(self) -> None:
        self._prev_left_y = None
        self._prev_right_y = None
        self._left_y_buf.clear()
        self._right_y_buf.clear()
        self._detect_streak = 0

    @staticmethod
    def _angle(
        landmarks: list,
        idx_a: int,
        idx_b: int,
        idx_c: int,
    ) -> float:
        a = np.array([landmarks[idx_a].x, landmarks[idx_a].y])
        b = np.array([landmarks[idx_b].x, landmarks[idx_b].y])
        c = np.array([landmarks[idx_c].x, landmarks[idx_c].y])
        rad = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        deg = float(np.abs(rad * 180.0 / np.pi))
        return 360 - deg if deg > 180 else deg

    def _draw_landmarks(
        self,
        frame: np.ndarray,
        landmarks: list,
    ) -> None:
        """Draw pose landmarks and connections on the frame."""
        h, w = frame.shape[:2]

        def _px(lm) -> tuple[int, int] | None:
            x, y = int(lm.x * w), int(lm.y * h)
            if 0 <= x < w and 0 <= y < h:
                return (x, y)
            return None

        # Draw connections
        for conn in _POSE_CONNECTIONS:
            pt1 = _px(landmarks[conn.start])
            pt2 = _px(landmarks[conn.end])
            if pt1 and pt2:
                cv2.line(frame, pt1, pt2, (200, 200, 200), 1, cv2.LINE_AA)

        # Draw landmark points
        for lm in landmarks:
            pt = _px(lm)
            if pt:
                cv2.circle(frame, pt, 3, (0, 255, 128), -1, cv2.LINE_AA)
