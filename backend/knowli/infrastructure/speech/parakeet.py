"""NVIDIA Parakeet TDT 0.6B v3, INT8 ONNX, via sherpa-onnx.

600M parameters, ~640 MB on disk, 25 European languages with automatic language
identification, and roughly 10x realtime on CPU. It is a transducer, so it does
not hallucinate text during silence the way Whisper does on empty audio.

Live text comes from segmentation, not from a streaming model: a Silero VAD
splits the incoming audio on pauses, and each closed segment is decoded on its
own and appended. Decoding one short segment is fast, so the transcript grows
roughly a phrase at a time while you keep talking — which is what dictation
UIs actually show. Re-decoding the whole buffer every tick would get slower the
longer you speak, which is the wrong direction.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np

from ... import config

SAMPLE_RATE = 16_000


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
