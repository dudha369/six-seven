"""Persistent application settings backed by QSettings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

_SETTINGS_DIR = Path.home() / ".sixseven"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


@dataclass
class AppConfig:
    """Runtime-mutable application configuration.

    All values have sensible defaults; changes are persisted to
    ``~/.sixseven/settings.json`` via :meth:`save`.
    """

    # --- Camera ---
    camera_index: int = 0

    # --- Detection ---
    movement_threshold: float = 0.03
    elbow_angle_limit: float = 110.0
    cooldown_seconds: float = 1.0
    smoothing_window: int = 5

    # --- Audio ---
    sound_file: str = ""
    audio_device: int | None = None

    # --- Virtual camera ---
    virtual_cam_enabled: bool = False
    virtual_cam_width: int = 1280
    virtual_cam_height: int = 720
    virtual_cam_fps: int = 30

    # --- UI ---
    show_landmarks: bool = True
    start_minimized: bool = False

    # ------------------------------------------------------------------

    def save(self) -> None:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        _SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls) -> "AppConfig":
        if not _SETTINGS_FILE.exists():
            return cls()
        try:
            raw = json.loads(_SETTINGS_FILE.read_text())
            valid = {f.name: raw[f.name] for f in fields(cls) if f.name in raw}
            return cls(**valid)
        except Exception:
            return cls()
