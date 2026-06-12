"""Thread-safe audio playback with device selection."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import sounddevice as sd
import soundfile as sf


class AudioPlayer:
    """Plays a sound file without blocking the caller.

    Features:
    * Cooldown to prevent audio spam.
    * Hot-swappable sound file and output device.
    * Thread-safe ``play()`` — safe to call from any thread.
    """

    def __init__(
        self,
        file_path: str | Path = "",
        device_index: int | None = None,
        cooldown: float = 1.0,
    ) -> None:
        self._lock = threading.Lock()
        self._is_playing = False
        self._cooldown = cooldown
        self._device = device_index
        self._data = None
        self._sr = 0
        if file_path:
            self.load(file_path)

    # --- public -------------------------------------------------------

    def load(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Sound file not found: {path}")
        data, sr = sf.read(str(path))
        with self._lock:
            self._data = data
            self._sr = sr

    def play(self) -> None:
        if self._data is None:
            return
        with self._lock:
            if self._is_playing:
                return
            self._is_playing = True
        threading.Thread(target=self._worker, daemon=True).start()

    def set_device(self, device_index: int | None) -> None:
        self._device = device_index

    def set_cooldown(self, seconds: float) -> None:
        self._cooldown = max(0, seconds)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @staticmethod
    def list_devices() -> list[dict]:
        """Return available audio output devices."""
        devices = sd.query_devices()
        out = []
        for i, d in enumerate(devices):  # type: ignore[arg-type]
            if d["max_output_channels"] > 0:  # type: ignore[index]
                out.append({"index": i, "name": d["name"], "channels": d["max_output_channels"]})  # type: ignore[index]
        return out

    # --- internal -----------------------------------------------------

    def _worker(self) -> None:
        try:
            with self._lock:
                data, sr = self._data, self._sr
            sd.play(data, sr, device=self._device)
            sd.wait()
        except Exception as exc:
            print(f"[AudioPlayer] error: {exc}")
        finally:
            time.sleep(self._cooldown)
            with self._lock:
                self._is_playing = False
