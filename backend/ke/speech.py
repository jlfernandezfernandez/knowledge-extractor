"""Speech to text, streamed.

Two backends behind one interface, chosen by `SPEECH_PROVIDER`:

- **parakeet** (default) — NVIDIA Parakeet TDT 0.6B v3, INT8 ONNX, via
  sherpa-onnx. 600M parameters, ~640 MB on disk, 25 European languages with
  automatic language identification, and roughly 10x realtime on CPU. It is a
  transducer, so it does not hallucinate text during silence the way Whisper
  does on empty audio.
- **whisper** — faster-whisper, batch only. Kept because it is the thing most
  people already have, and because Parakeet's 25 languages are all European.

Live text comes from segmentation, not from a streaming model: a Silero VAD
splits the incoming audio on pauses, and each closed segment is decoded on its
own and appended. Decoding one short segment is fast, so the transcript grows
roughly a phrase at a time while you keep talking — which is what dictation
UIs actually show. Re-decoding the whole buffer every tick would get slower the
longer you speak, which is the wrong direction.
"""

from __future__ import annotations

import logging
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np

from . import config

log = logging.getLogger(__name__)

SAMPLE_RATE = 16_000

# 628 KB, fetched on first use rather than committed. Model weights do not
# belong in git, and fastembed already does the same for the embedder.
VAD_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"


def _vad_model() -> Path:
    path = Path(__file__).resolve().parent.parent / "models" / "silero_vad.onnx"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Fetching the voice-activity model (628 KB), once: %s", VAD_URL)
        urllib.request.urlretrieve(VAD_URL, path)  # noqa: S310 — pinned release URL
    return path


class Transcriber(Protocol):
    def feed(self, samples: np.ndarray) -> Iterator[str]:
        """Accept mono float32 audio at 16 kHz; yield finalised segments."""

    def flush(self) -> Iterator[str]:
        """Yield whatever is left when the speaker stops."""


class ParakeetTranscriber:
    def __init__(self, model_dir: Path, vad_model: Path) -> None:
        import sherpa_onnx

        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(model_dir / "encoder.int8.onnx"),
            decoder=str(model_dir / "decoder.int8.onnx"),
            joiner=str(model_dir / "joiner.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=config.SPEECH_THREADS,
            model_type="nemo_transducer",
        )
        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = str(vad_model)
        vad_config.silero_vad.min_silence_duration = 0.4
        vad_config.silero_vad.min_speech_duration = 0.2
        vad_config.sample_rate = SAMPLE_RATE
        self._vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)

    def _decode(self, samples: np.ndarray) -> str:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, samples)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()

    def feed(self, samples: np.ndarray) -> Iterator[str]:
        self._vad.accept_waveform(samples)
        while not self._vad.empty():
            text = self._decode(np.asarray(self._vad.front.samples, dtype=np.float32))
            self._vad.pop()
            if text:
                yield text

    def flush(self) -> Iterator[str]:
        self._vad.flush()
        yield from self.feed(np.zeros(0, dtype=np.float32))


class WhisperTranscriber:
    """Batch fallback. Buffers everything and decodes once at the end, so the
    live transcript stays empty until you stop talking."""

    def __init__(self, model_name: str) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self._buffer: list[np.ndarray] = []

    def feed(self, samples: np.ndarray) -> Iterator[str]:
        self._buffer.append(samples)
        return iter(())

    def flush(self) -> Iterator[str]:
        if not self._buffer:
            return
        audio = np.concatenate(self._buffer)
        self._buffer.clear()
        segments, _ = self._model.transcribe(audio, vad_filter=True)
        for segment in segments:
            text = segment.text.strip()
            if text:
                yield text


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
        return WhisperTranscriber(config.WHISPER_MODEL)
    return ParakeetTranscriber(model_dir, _vad_model())
