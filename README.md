# SixSeven 🤙🤟

Gesture-driven audio overlay — detects the **6-7 meme** hand movement via webcam and plays a sound effect. Now with a clean PySide6 desktop UI, system tray support, and virtual camera output for Discord.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Gesture detection** | MediaPipe Pose tracks both arms; when elbows are bent and hands move in opposite vertical directions — boom, trigger. |
| **State machine** | IDLE → DETECTING → TRIGGERED → COOLDOWN prevents duplicate fires and gives clean UI feedback. |
| **Smoothing** | Rolling-window average on wrist positions filters micro-jitter for stable detection. |
| **PySide6 GUI** | Dark-themed desktop app with live camera preview, status indicator, and a compact settings sidebar. |
| **System tray** | Minimize to tray; single-click to show/hide. Keeps running in the background. |
| **Virtual camera** | Stream the processed video feed to a virtual webcam via `pyvirtualcam`. Discord, OBS, Zoom — any app can pick it up as a camera source. |
| **Audio overlay** | Plays any `.mp3`/`.wav`/`.ogg` file through the default or a specific audio device (e.g. VB-Cable for Discord). |
| **Configurable** | Adjust sensitivity, cooldown, smoothing window, audio device, and camera — all from the UI, persisted to `~/.sixseven/settings.json`. |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A webcam
- (Optional) [VB-Cable](https://vb-audio.com/Cable/) for routing audio to Discord
- (Optional) Virtual camera backend for video output — see [Virtual Camera Setup](#-virtual-camera-setup)

### Install

```bash
# Clone the repo
git clone https://github.com/dudha369/six-seven.git
cd six-seven

# Create a virtual environment and install dependencies (using uv)
uv sync

# Or with pip
pip install -e .
```

### Run

```bash
# Via the entry point
sixseven

# Or as a module
python -m sixseven
```

The GUI opens with a camera preview. Press **▶ Start** to begin detection.

---

## 🎮 How It Works

1. **Camera capture** runs on a background `QThread`, emitting BGR frames via Qt signals.
2. **`GestureDetector`** processes each frame with MediaPipe Pose:
   - Calculates elbow angles (shoulder → elbow → wrist).
   - Checks if both elbows are bent below the configured angle limit.
   - Computes smoothed wrist Y-velocity and checks for opposite-direction movement above the amplitude threshold.
   - A **state machine** requires multiple consecutive detections (`DETECTING` streak) before firing `TRIGGERED`, then enters `COOLDOWN`.
3. On trigger, **`AudioPlayer`** plays the sound file in a daemon thread (with cooldown to prevent spam).
4. The annotated frame is displayed in the PySide6 preview and optionally sent to the **virtual camera**.

---

## 📷 Virtual Camera Setup

Virtual camera lets you stream the processed (landmarks + overlay) video feed to Discord as if it were a real webcam.

### Windows
Install [OBS Studio](https://obsproject.com/) — it ships with *OBS Virtual Camera*. Then:
```bash
pip install pyvirtualcam
```
Enable the "Virtual camera (Discord)" checkbox in SixSeven. In Discord video settings, select **OBS Virtual Camera**.

### Linux
```bash
sudo apt install v4l2loopback-dkms
sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="SixSeven" exclusive_caps=1
pip install pyvirtualcam
```
In Discord, select the `/dev/video10` device.

### macOS
Install [OBS Studio](https://obsproject.com/) (includes the virtual camera plugin). Then:
```bash
pip install pyvirtualcam
```

---

## 🔊 Audio to Discord via VB-Cable

1. Install [VB-Cable](https://vb-audio.com/Cable/).
2. In SixSeven → *Settings → Audio device*, select **CABLE Input (VB-Audio Virtual Cable)**.
3. In Discord → *Voice Settings → Input Device*, select **CABLE Output**.

Now when the gesture triggers, Discord hears the sound.

---

## ⚙️ Configuration

All settings are adjustable in the UI and auto-saved to `~/.sixseven/settings.json`.

| Setting | Default | Description |
|---|---|---|
| Camera | `0` | Webcam index |
| Sensitivity (threshold) | `0.030` | Min wrist Y-delta to count as movement (lower = more sensitive) |
| Cooldown | `1.0 s` | Pause after a trigger before the next detection |
| Smoothing window | `5` | Number of frames for rolling-average smoothing |
| Show landmarks | `true` | Draw MediaPipe skeleton on the preview |
| Virtual camera | `false` | Enable `pyvirtualcam` output |

---

## 📁 Project Structure

```
six-seven/
├── sixseven/
│   ├── __init__.py          # Package version
│   ├── __main__.py          # python -m sixseven entry point
│   ├── app.py               # QApplication, system tray, icon
│   ├── config.py            # Persistent settings (JSON-backed dataclass)
│   ├── core/
│   │   ├── audio.py         # Thread-safe audio playback
│   │   ├── camera.py        # Camera capture QThread
│   │   ├── detector.py      # Gesture detection with state machine
│   │   └── virtual_cam.py   # pyvirtualcam wrapper
│   └── ui/
│       ├── main_window.py   # Main window with preview + controls
│       └── styles.py        # Dark-theme QSS
├── sound.mp3                # Default trigger sound
├── pyproject.toml           # Project metadata and dependencies
└── README.md
```

---

## 🛠 Development

```bash
# Install with dev/optional extras
pip install -e ".[virtualcam]"

# Lint
ruff check sixseven/

# Format
ruff format sixseven/
```

---

## 📝 License

MIT — do whatever you want.
