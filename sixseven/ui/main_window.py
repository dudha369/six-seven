"""Main application window — camera preview + settings sidebar + GIF overlay."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Slot, QSize
from PySide6.QtGui import QImage, QMovie, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
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


class _GifOverlay(QLabel):
    """Transparent GIF overlay — displayed on top of the camera preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;")
        self._movie: QMovie | None = None
        self._gif_path: str = ""
        self.hide()

    def load_gif(self, path: str) -> None:
        if not Path(path).is_file():
            return
        self._gif_path = path

    def play(self, duration_ms: int = 3000) -> None:
        """Show the GIF for *duration_ms*, then hide it."""
        if not self._gif_path:
            return
        self.stop()
        movie = QMovie(self._gif_path)
        if not movie.isValid():
            return
        self._movie = movie
        # Scale GIF to fit nicely in top-right
        movie.setScaledSize(QSize(180, 180))
        self.setMovie(movie)
        self.show()
        self.raise_()
        movie.start()
        QTimer.singleShot(duration_ms, self.stop)

    def stop(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie = None
        self.hide()

    def reposition(self, parent_size) -> None:
        """Place in top-right corner of parent."""
        margin = 12
        w, h = 180, 180
        x = parent_size.width() - w - margin
        y = margin
        self.setGeometry(x, y, w, h)


class MainWindow(QMainWindow):
    """Modern main window with camera preview, settings sidebar, and GIF overlay."""

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._cfg = config

        self.setWindowTitle("SixSeven")
        self.setMinimumSize(820, 520)
        self.resize(1020, 620)

        # --- Core objects ---
        self._detector = GestureDetector(
            movement_threshold=config.movement_threshold,
            elbow_angle_limit=config.elbow_angle_limit,
            cooldown_seconds=config.cooldown_seconds,
            smoothing_window=config.smoothing_window,
            show_landmarks=config.show_landmarks,
        )

        sound = config.sound_file or self._find_default_sound()
        self._audio = AudioPlayer(
            file_path=sound,
            device_index=config.audio_device,
            cooldown=config.cooldown_seconds,
        )

        self._camera = CameraThread(camera_index=config.camera_index, target_fps=30)
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.error.connect(self._on_camera_error)

        self._vcam = VirtualCamera(
            width=config.virtual_cam_width,
            height=config.virtual_cam_height,
            fps=config.virtual_cam_fps,
        )

        self._running = False

        # Frame throttle: skip if previous frame hasn't been painted yet
        self._frame_pending = False

        self._build_ui()
        self._apply_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── Left: camera preview container ──
        preview_container = QWidget()
        preview_container.setObjectName("previewContainer")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)

        self._preview = QLabel()
        self._preview.setObjectName("previewLabel")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview.setMinimumSize(480, 360)
        self._preview.setText("Camera off")
        preview_layout.addWidget(self._preview)

        # GIF overlay (parented to preview so it floats on top)
        self._gif_overlay = _GifOverlay(self._preview)
        gif_path = self._find_animation_gif()
        if gif_path:
            self._gif_overlay.load_gif(gif_path)

        root.addWidget(preview_container, stretch=3)

        # ── Right: sidebar ──
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)

        # Status badge
        self._status = QLabel("IDLE")
        self._status.setObjectName("statusLabel")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setMinimumHeight(38)
        sidebar.addWidget(self._status)

        # Start / Stop buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_start = QPushButton("▶  Start")
        self._btn_start.setObjectName("btnStart")
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.clicked.connect(self._start)
        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setObjectName("btnStop")
        self._btn_stop.setCursor(Qt.PointingHandCursor)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_stop)
        sidebar.addLayout(btn_row)

        # Thin separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sidebar.addWidget(sep)

        # --- Scrollable settings area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        settings_widget = QWidget()
        sl = QVBoxLayout(settings_widget)
        sl.setContentsMargins(0, 4, 0, 4)
        sl.setSpacing(10)

        # ─ Camera group ─
        grp_cam = QGroupBox("Camera")
        gl_cam = QVBoxLayout(grp_cam)
        gl_cam.setSpacing(6)
        self._combo_cam = QComboBox()
        self._populate_cameras()
        gl_cam.addWidget(self._combo_cam)
        sl.addWidget(grp_cam)

        # ─ Audio group ─
        grp_audio = QGroupBox("Audio")
        gl_audio = QVBoxLayout(grp_audio)
        gl_audio.setSpacing(6)

        sound_row = QHBoxLayout()
        self._lbl_sound = QLabel("sound.mp3")
        self._lbl_sound.setObjectName("soundLabel")
        self._lbl_sound.setToolTip(self._cfg.sound_file or "default")
        sound_row.addWidget(self._lbl_sound, stretch=1)
        btn_browse = QPushButton("Browse…")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._browse_sound)
        sound_row.addWidget(btn_browse)
        gl_audio.addLayout(sound_row)

        gl_audio.addWidget(QLabel("Output device"))
        self._combo_audio = QComboBox()
        self._populate_audio_devices()
        gl_audio.addWidget(self._combo_audio)
        sl.addWidget(grp_audio)

        # ─ Detection group ─
        grp_det = QGroupBox("Detection")
        gl_det = QVBoxLayout(grp_det)
        gl_det.setSpacing(6)

        gl_det.addWidget(QLabel("Sensitivity (threshold)"))
        self._spin_thresh = QDoubleSpinBox()
        self._spin_thresh.setRange(0.005, 0.2)
        self._spin_thresh.setSingleStep(0.005)
        self._spin_thresh.setDecimals(3)
        self._spin_thresh.valueChanged.connect(self._on_settings_changed)
        gl_det.addWidget(self._spin_thresh)

        gl_det.addWidget(QLabel("Cooldown (s)"))
        self._spin_cd = QDoubleSpinBox()
        self._spin_cd.setRange(0.1, 10.0)
        self._spin_cd.setSingleStep(0.1)
        self._spin_cd.setDecimals(1)
        self._spin_cd.valueChanged.connect(self._on_settings_changed)
        gl_det.addWidget(self._spin_cd)

        gl_det.addWidget(QLabel("Smoothing window"))
        self._spin_smooth = QSpinBox()
        self._spin_smooth.setRange(1, 20)
        self._spin_smooth.valueChanged.connect(self._on_settings_changed)
        gl_det.addWidget(self._spin_smooth)

        sl.addWidget(grp_det)

        # ─ Display group ─
        grp_disp = QGroupBox("Display")
        gl_disp = QVBoxLayout(grp_disp)
        gl_disp.setSpacing(8)

        self._chk_landmarks = QCheckBox("Show landmarks")
        self._chk_landmarks.setCursor(Qt.PointingHandCursor)
        self._chk_landmarks.stateChanged.connect(self._on_settings_changed)
        gl_disp.addWidget(self._chk_landmarks)

        self._chk_vcam = QCheckBox("Virtual camera (Discord)")
        self._chk_vcam.setCursor(Qt.PointingHandCursor)
        self._chk_vcam.setToolTip(
            "Stream processed video to a virtual webcam.\n"
            "Requires pyvirtualcam + a virtual camera backend."
        )
        self._chk_vcam.stateChanged.connect(self._on_vcam_toggled)
        gl_disp.addWidget(self._chk_vcam)

        sl.addWidget(grp_disp)

        sl.addStretch()
        scroll.setWidget(settings_widget)
        sidebar.addWidget(scroll, stretch=1)

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
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "sound.mp3",
            Path.cwd() / "sound.mp3",
        ]
        for p in candidates:
            if p.is_file():
                return str(p)
        return ""

    @staticmethod
    def _find_animation_gif() -> str:
        """Look for animation.gif shipped with the project."""
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "animation.gif",
            Path.cwd() / "animation.gif",
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
        self._update_status(GestureState.IDLE, 0.0)
        self._save_config()

    @Slot(np.ndarray)
    def _on_frame(self, frame: np.ndarray) -> None:
        # Frame-drop: skip if last frame hasn't been painted yet
        if self._frame_pending:
            return
        self._frame_pending = True

        result: DetectionResult = self._detector.process(frame)

        if result.triggered:
            self._audio.play()
            self._gif_overlay.play(duration_ms=3500)

        self._update_status(result.state, result.confidence)

        # Overlay status text on frame
        annotated = result.frame
        if result.state == GestureState.TRIGGERED:
            self._draw_status_badge(annotated, "6-7 DETECTED!", (0, 70, 255))
        elif result.state == GestureState.COOLDOWN:
            self._draw_status_badge(annotated, "cooldown…", (80, 80, 40))

        # Virtual camera
        if self._vcam.active:
            self._vcam.send(annotated)

        # Preview
        self._show_frame(annotated)
        self._frame_pending = False

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

    @staticmethod
    def _draw_status_badge(
        frame: np.ndarray, text: str, color: tuple[int, int, int]
    ) -> None:
        """Draw a rounded status badge on the bottom-left of the frame."""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.7
        thickness = 2
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        pad = 10
        x, y = 16, h - 20
        # Background pill
        cv2.rectangle(
            frame,
            (x - pad, y - th - pad),
            (x + tw + pad, y + baseline + pad),
            color,
            -1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA
        )

    def _update_status(self, state: GestureState, confidence: float) -> None:
        style_map = {
            GestureState.IDLE: (
                "IDLE",
                "color: #555568; background: #14141f; border-radius: 8px;",
            ),
            GestureState.DETECTING: (
                "DETECTING…",
                "color: #f0c040; background: #2a2510; border-radius: 8px;",
            ),
            GestureState.TRIGGERED: (
                "6-7 TRIGGERED!",
                "color: #ffffff; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #e94560, stop:1 #d63651); border-radius: 8px;",
            ),
            GestureState.COOLDOWN: (
                "COOLDOWN",
                "color: #555568; background: #14141f; border-radius: 8px;",
            ),
        }
        text, style = style_map.get(state, ("", ""))
        if state == GestureState.DETECTING:
            text += f"  {confidence:.0%}"
        self._status.setText(text)
        self._status.setStyleSheet(style)

    def _show_frame(self, bgr: np.ndarray) -> None:
        h, w, ch = bgr.shape
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img)
        # Use FastTransformation for performance; SmoothTransformation was causing lag
        scaled = pix.scaled(
            self._preview.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self._preview.setPixmap(scaled)

        # Reposition GIF overlay on top of preview
        self._gif_overlay.reposition(self._preview.size())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._stop()
        self._gif_overlay.stop()
        self._detector.release()
        self._save_config()
        event.accept()
