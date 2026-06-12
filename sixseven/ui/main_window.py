"""Main application window — camera preview + minimal controls."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sixseven.config import AppConfig
from sixseven.core.audio import AudioPlayer
from sixseven.core.camera import CameraThread
from sixseven.core.detector import DetectionResult, GestureDetector, GestureState
from sixseven.core.virtual_cam import VirtualCamera


class MainWindow(QMainWindow):
    """Compact main window with camera preview and control sidebar."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._cfg = config

        self.setWindowTitle("SixSeven")
        self.setMinimumSize(780, 500)
        self.resize(960, 580)

        # --- Core objects ---
        self._detector = GestureDetector(
            movement_threshold=config.movement_threshold,
            elbow_angle_limit=config.elbow_angle_limit,
            cooldown_seconds=config.cooldown_seconds,
            smoothing_window=config.smoothing_window,
            show_landmarks=config.show_landmarks,
        )

        sound = config.sound_file or self._find_default_sound()
        self._audio = AudioPlayer(file_path=sound, device_index=config.audio_device, cooldown=config.cooldown_seconds)

        self._camera = CameraThread(camera_index=config.camera_index)
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.error.connect(self._on_camera_error)

        self._vcam = VirtualCamera(
            width=config.virtual_cam_width,
            height=config.virtual_cam_height,
            fps=config.virtual_cam_fps,
        )

        self._running = False

        self._build_ui()
        self._apply_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Camera preview (stretches) ──
        self._preview = QLabel()
        self._preview.setObjectName("previewLabel")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview.setMinimumSize(480, 360)
        self._preview.setText("Camera off")
        root.addWidget(self._preview, stretch=3)

        # ── Sidebar ──
        sidebar = QVBoxLayout()
        sidebar.setSpacing(8)

        # Status
        self._status = QLabel("IDLE")
        self._status.setObjectName("statusLabel")
        self._status.setAlignment(Qt.AlignCenter)
        sidebar.addWidget(self._status)

        # Start / stop
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("▶  Start")
        self._btn_start.setObjectName("btnStart")
        self._btn_start.clicked.connect(self._start)
        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setObjectName("btnStop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        sidebar.addLayout(btn_row)

        # --- Settings group ---
        grp = QGroupBox("Settings")
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)

        # Camera selector
        gl.addWidget(QLabel("Camera"))
        self._combo_cam = QComboBox()
        self._populate_cameras()
        gl.addWidget(self._combo_cam)

        # Sound file
        sound_row = QHBoxLayout()
        self._lbl_sound = QLabel("sound.mp3")
        self._lbl_sound.setToolTip(self._cfg.sound_file or "default")
        sound_row.addWidget(self._lbl_sound, stretch=1)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_sound)
        sound_row.addWidget(btn_browse)
        gl.addLayout(sound_row)

        # Audio device
        gl.addWidget(QLabel("Audio device"))
        self._combo_audio = QComboBox()
        self._populate_audio_devices()
        gl.addWidget(self._combo_audio)

        # Sensitivity
        gl.addWidget(QLabel("Sensitivity (threshold)"))
        self._spin_thresh = QDoubleSpinBox()
        self._spin_thresh.setRange(0.005, 0.2)
        self._spin_thresh.setSingleStep(0.005)
        self._spin_thresh.setDecimals(3)
        self._spin_thresh.valueChanged.connect(self._on_settings_changed)
        gl.addWidget(self._spin_thresh)

        # Cooldown
        gl.addWidget(QLabel("Cooldown (s)"))
        self._spin_cd = QDoubleSpinBox()
        self._spin_cd.setRange(0.1, 10.0)
        self._spin_cd.setSingleStep(0.1)
        self._spin_cd.setDecimals(1)
        self._spin_cd.valueChanged.connect(self._on_settings_changed)
        gl.addWidget(self._spin_cd)

        # Smoothing
        gl.addWidget(QLabel("Smoothing window"))
        self._spin_smooth = QSpinBox()
        self._spin_smooth.setRange(1, 20)
        self._spin_smooth.valueChanged.connect(self._on_settings_changed)
        gl.addWidget(self._spin_smooth)

        # Landmarks
        self._chk_landmarks = QCheckBox("Show landmarks")
        self._chk_landmarks.stateChanged.connect(self._on_settings_changed)
        gl.addWidget(self._chk_landmarks)

        # Virtual camera
        self._chk_vcam = QCheckBox("Virtual camera (Discord)")
        self._chk_vcam.setToolTip(
            "Stream processed video to a virtual webcam.\n"
            "Requires pyvirtualcam + a virtual camera backend."
        )
        self._chk_vcam.stateChanged.connect(self._on_vcam_toggled)
        gl.addWidget(self._chk_vcam)

        sidebar.addWidget(grp)
        sidebar.addStretch()

        root.addLayout(sidebar, stretch=1)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _apply_config(self) -> None:
        c = self._cfg
        self._combo_cam.setCurrentIndex(c.camera_index)
        self._spin_thresh.setValue(c.movement_threshold)
        self._spin_cd.setValue(c.cooldown_seconds)
        self._spin_smooth.setValue(c.smoothing_window)
        self._chk_landmarks.setChecked(c.show_landmarks)
        self._chk_vcam.setChecked(c.virtual_cam_enabled)
        if c.sound_file:
            self._lbl_sound.setText(Path(c.sound_file).name)

    def _save_config(self) -> None:
        c = self._cfg
        c.camera_index = self._combo_cam.currentIndex()
        c.movement_threshold = self._spin_thresh.value()
        c.cooldown_seconds = self._spin_cd.value()
        c.smoothing_window = self._spin_smooth.value()
        c.show_landmarks = self._chk_landmarks.isChecked()
        c.virtual_cam_enabled = self._chk_vcam.isChecked()
        idx = self._combo_audio.currentIndex()
        c.audio_device = self._combo_audio.currentData() if idx > 0 else None
        c.save()

    # ------------------------------------------------------------------
    # Populate helpers
    # ------------------------------------------------------------------

    def _populate_cameras(self) -> None:
        self._combo_cam.clear()
        # Probe first 5 indices
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self._combo_cam.addItem(f"Camera {i}", i)
                cap.release()
            else:
                break

    def _populate_audio_devices(self) -> None:
        self._combo_audio.clear()
        self._combo_audio.addItem("Default", None)
        for dev in AudioPlayer.list_devices():
            self._combo_audio.addItem(dev["name"], dev["index"])

    @staticmethod
    def _find_default_sound() -> str:
        """Look for sound.mp3 next to the package."""
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "sound.mp3",
            Path.cwd() / "sound.mp3",
        ]
        for p in candidates:
            if p.is_file():
                return str(p)
        return ""

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def _start(self) -> None:
        if self._running:
            return
        cam_idx = self._combo_cam.currentData()
        if cam_idx is None:
            cam_idx = 0
        self._camera.set_camera(cam_idx)
        self._camera.start()
        self._running = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

        if self._chk_vcam.isChecked():
            self._vcam.start()

    @Slot()
    def _stop(self) -> None:
        if not self._running:
            return
        self._camera.stop()
        self._vcam.stop()
        self._running = False
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._preview.setText("Camera off")
        self._status.setText("IDLE")
        self._status.setStyleSheet("")
        self._save_config()

    @Slot(np.ndarray)
    def _on_frame(self, frame: np.ndarray) -> None:
        result: DetectionResult = self._detector.process(frame)

        if result.triggered:
            self._audio.play()

        # Status indicator
        self._update_status(result.state, result.confidence)

        # Overlay status text on frame
        annotated = result.frame
        if result.state == GestureState.TRIGGERED:
            cv2.putText(annotated, "6-7 DETECTED!", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 70, 255), 2, cv2.LINE_AA)
        elif result.state == GestureState.COOLDOWN:
            cv2.putText(annotated, "cooldown...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 40), 2, cv2.LINE_AA)

        # Virtual camera
        if self._vcam.active:
            self._vcam.send(annotated)

        # Preview
        self._show_frame(annotated)

    @Slot(str)
    def _on_camera_error(self, msg: str) -> None:
        self._preview.setText(f"⚠ {msg}")
        self._stop()

    @Slot()
    def _on_settings_changed(self) -> None:
        self._detector.update_settings(
            movement_threshold=self._spin_thresh.value(),
            cooldown_seconds=self._spin_cd.value(),
            smoothing_window=self._spin_smooth.value(),
            show_landmarks=self._chk_landmarks.isChecked(),
        )
        self._audio.set_cooldown(self._spin_cd.value())

    @Slot()
    def _on_vcam_toggled(self) -> None:
        if self._chk_vcam.isChecked() and self._running:
            self._vcam.start()
        else:
            self._vcam.stop()

    @Slot()
    def _browse_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Sound File", "", "Audio (*.mp3 *.wav *.ogg *.flac);;All (*)"
        )
        if path:
            try:
                self._audio.load(path)
                self._cfg.sound_file = path
                self._lbl_sound.setText(Path(path).name)
            except FileNotFoundError:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_status(self, state: GestureState, confidence: float) -> None:
        style_map = {
            GestureState.IDLE: ("IDLE", "color: #888;"),
            GestureState.DETECTING: ("DETECTING…", "color: #f0c040;"),
            GestureState.TRIGGERED: ("6-7 TRIGGERED!", "color: #e94560; font-size:16px;"),
            GestureState.COOLDOWN: ("COOLDOWN", "color: #888;"),
        }
        text, style = style_map.get(state, ("", ""))
        if state == GestureState.DETECTING:
            text += f" ({confidence:.0%})"
        self._status.setText(text)
        self._status.setStyleSheet(style)

    def _show_frame(self, bgr: np.ndarray) -> None:
        h, w, ch = bgr.shape
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        scaled = QPixmap.fromImage(img).scaled(
            self._preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._preview.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._stop()
        self._detector.release()
        self._save_config()
        event.accept()
