"""``python -m sixseven`` entry point."""

# Suppress noisy warnings *before* importing anything else
import os as _os

_os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")           # TensorFlow / TFLite
_os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")           # force CPU (more stable)
_os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")           # OpenCV FFMPEG/obsensor
_os.environ.setdefault("GLOG_minloglevel", "3")                # glog (protobuf etc.)

import warnings as _warnings

_warnings.filterwarnings("ignore", category=UserWarning)
_warnings.filterwarnings("ignore", category=FutureWarning)

# Suppress absl logging (used internally by mediapipe)
try:
    import absl.logging as _absl_logging  # type: ignore[import-untyped]

    _absl_logging.set_verbosity(_absl_logging.ERROR)
    _absl_logging.set_stderrthreshold(_absl_logging.ERROR)
except ImportError:
    pass

import logging as _logging

_logging.getLogger("mediapipe").setLevel(_logging.ERROR)
_logging.getLogger("tensorflow").setLevel(_logging.ERROR)

from sixseven.app import run

run()
