"""Speech to text, streamed.

Two backends behind one interface (`domain.ports.Transcriber`), chosen by
`SPEECH_PROVIDER`:

- **parakeet** (default) — NVIDIA Parakeet TDT 0.6B v3, INT8 ONNX, via
  sherpa-onnx. See `parakeet.py`.
- **whisper** — faster-whisper, batch only. See `whisper.py`.

Both are imported lazily by the backend module itself (sherpa-onnx and
faster-whisper are heavy, and whisper is an optional dependency), so this module
can be imported on a machine with neither installed.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from ... import config
from ...domain.ports import Transcriber

log = logging.getLogger(__name__)

# 628 KB, fetched on first use rather than committed. Model weights do not
# belong in git, and fastembed already does the same for the embedder.
VAD_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"


def _vad_model() -> Path:
    # backend/models/, i.e. next to the package rather than inside it: it is
    # downloaded state, not source. transcriber.py is four levels deep now, so
    # this walks up knowli/infrastructure/speech/ to get there.
    path = Path(__file__).resolve().parents[3] / "models" / "silero_vad.onnx"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Fetching the voice-activity model (628 KB), once: %s", VAD_URL)
        urllib.request.urlretrieve(VAD_URL, path)  # noqa: S310 — pinned release URL
    return path


def available() -> bool:
    return _resolve() is not None


def _resolve() -> tuple[str, Path] | None:
    """Which backend can actually run, given what is installed and on disk."""
    if config.SPEECH_PROVIDER == "whisper":
        return ("whisper", Path())
    model_dir = Path(config.SPEECH_MODEL_DIR).expanduser()
    if (model_dir / "encoder.int8.onnx").exists():
        return ("parakeet", model_dir)
    return None


def create() -> Transcriber:
    resolved = _resolve()
    if resolved is None:
        raise RuntimeError(
            f"No speech model found at {config.SPEECH_MODEL_DIR}. Either download "
            f"Parakeet (see docs/local-models.md) or set SPEECH_PROVIDER=whisper."
        )
    provider, model_dir = resolved
    if provider == "whisper":
        from .whisper import WhisperTranscriber

        return WhisperTranscriber(config.WHISPER_MODEL)

    from .parakeet import ParakeetTranscriber

    return ParakeetTranscriber(model_dir, _vad_model())
