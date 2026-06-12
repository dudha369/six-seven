"""Improved SixSeven gesture detector with smoothing and state machine."""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field

import cv2
import mediapipe as mp
import numpy as np


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
    * Rolling-window smoothing of wrist Y positions to filter micro-jitter.
    * State machine (IDLE → DETECTING → TRIGGERED → COOLDOWN) to avoid
      duplicate triggers and provide UI-friendly status.
    * Configurable elbow-angle limit, movement threshold, and cooldown.
    * Separate ``detect`` (pure logic) from ``draw`` (visualisation).
    """

    # MediaPipe Pose landmark indices
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

        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_style = mp.solutions.drawing_styles

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
        results = self._pose.process(rgb)

        result = DetectionResult(frame=frame, state=self._state)

        if results.pose_landmarks is None:
            self._reset_tracking()
            result.state = GestureState.IDLE
            return result

        if self._show_landmarks:
            self._draw_landmarks(frame, results.pose_landmarks)

        lm = results.pose_landmarks.landmark
        l_angle = self._angle(lm, self._L_SHOULDER, self._L_ELBOW, self._L_WRIST)
        r_angle = self._angle(lm, self._R_SHOULDER, self._R_ELBOW, self._R_WRIST)
        result.left_angle = l_angle
        result.right_angle = r_angle

        elbows_bent = l_angle < self._angle_limit and r_angle < self._angle_limit

        # Smooth wrist Y
        self._left_y_buf.append(lm[self._L_WRIST].y)
        self._right_y_buf.append(lm[self._R_WRIST].y)
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
        self._pose.close()

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
        pose_landmarks: object,
    ) -> None:
        self._mp_draw.draw_landmarks(
            frame,
            pose_landmarks,
            self._mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self._mp_draw.DrawingSpec(
                color=(0, 255, 128), thickness=2, circle_radius=3
            ),
            connection_drawing_spec=self._mp_draw.DrawingSpec(
                color=(200, 200, 200), thickness=1
            ),
        )
