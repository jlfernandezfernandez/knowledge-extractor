"""The one transcription adapter: cuts the microphone at its pauses, transcribes each turn."""

import asyncio
import io
import wave
from array import array
from collections.abc import AsyncIterator
from typing import Any

from .. import config
from ..domain.ports import Transcriber

SAMPLE_RATE = 16_000
"""Whisper's own rate. The browser resamples to it, so nothing has to resample here."""

PAUSE_MS = 700
"""Silence that ends a turn. Long enough to survive the gap between two words."""

MIN_SPEECH_MS = 400
MAX_TURN_MS = 20_000
"""A turn is cut here even mid-sentence: whisper degrades on long audio, and a speaker
who never pauses would otherwise never see a word appear."""

SILENCE_RMS = 400
"""Root-mean-square below which a frame counts as silence, on the int16 scale.
ponytail: a fixed floor, measured against a laptop microphone in a quiet room. A noisy
room keeps every frame above it and turns end on MAX_TURN_MS instead; swap in a real
voice-activity model (silero) if that becomes the common case."""


def _milliseconds(pcm: bytes) -> float:
    return len(pcm) / 2 / SAMPLE_RATE * 1000


def _is_silence(pcm: bytes) -> bool:
    samples = array("h", pcm)
    if not samples:
        return True
    return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5 < SILENCE_RMS


def _as_wav(pcm: bytes) -> io.BytesIO:
    file = io.BytesIO()
    with wave.open(file, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE)
        target.writeframes(pcm)
    file.seek(0)
    return file


async def _turns(audio: AsyncIterator[bytes], turns: asyncio.Queue[bytes | None]) -> None:
    """Splits the stream at every pause, so a turn can be transcribed while the next is spoken."""
    spoken, silence_ms = bytearray(), 0.0

    async for chunk in audio:
        if _is_silence(chunk):
            # Silence before anything was said is not a turn, it is just a quiet room.
            if spoken:
                silence_ms += _milliseconds(chunk)
                spoken += chunk
        else:
            silence_ms = 0.0
            spoken += chunk

        ended = silence_ms >= PAUSE_MS or _milliseconds(spoken) >= MAX_TURN_MS
        if ended:
            if _milliseconds(spoken) - silence_ms >= MIN_SPEECH_MS:
                await turns.put(bytes(spoken))
            spoken, silence_ms = bytearray(), 0.0

    if _milliseconds(spoken) - silence_ms >= MIN_SPEECH_MS:
        await turns.put(bytes(spoken))
    await turns.put(None)


class SegmentingTranscriber:
    """Turns arrive at an OpenAI-compatible `/audio/transcriptions` one at a time."""

    def __init__(self, client: Any | None = None):
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=config.TRANSCRIPTION_API_KEY,
            base_url=config.TRANSCRIPTION_BASE_URL or None,
        )
        return self._client

    async def transcribe(self, audio: AsyncIterator[bytes]) -> AsyncIterator[str]:
        turns: asyncio.Queue[bytes | None] = asyncio.Queue()
        # A task, not a loop here: transcribing a turn takes seconds, and the microphone
        # has to keep being read during them or the speaker gets further and further ahead.
        segmenting = asyncio.create_task(_turns(audio, turns))
        try:
            while (turn := await turns.get()) is not None:
                response = await self.client.audio.transcriptions.create(
                    file=("turn.wav", _as_wav(turn)),
                    model=config.TRANSCRIPTION_MODEL,
                    response_format="text",
                )
                if transcript := str(response).strip():
                    yield transcript
        finally:
            segmenting.cancel()


def create_transcriber() -> Transcriber:
    return SegmentingTranscriber()
