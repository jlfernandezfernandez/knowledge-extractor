"""faster-whisper, batch only.

Kept because it is the thing most people already have, and because Parakeet's
25 languages are all European.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np


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
