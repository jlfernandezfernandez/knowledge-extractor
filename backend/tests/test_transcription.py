"""Where the adapter cuts the microphone, and what it sends when it does."""

import math
import wave
from array import array
from collections.abc import AsyncIterator

import pytest

from knowli.infrastructure.transcription import PAUSE_MS, SAMPLE_RATE, SegmentingTranscriber


def _tone(milliseconds: int) -> bytes:
    samples = array("h", (
        int(8000 * math.sin(index / 8)) for index in range(int(SAMPLE_RATE * milliseconds / 1000))
    ))
    return samples.tobytes()


def _silence(milliseconds: int) -> bytes:
    return b"\x00" * int(SAMPLE_RATE * 2 * milliseconds / 1000)


async def _microphone(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


class FakeTranscriptions:
    def __init__(self):
        self.durations: list[float] = []

    async def create(self, *, file, **_kwargs) -> str:
        with wave.open(file[1]) as turn:
            self.durations.append(turn.getnframes() / turn.getframerate())
        return f"turn {len(self.durations)} "


class FakeClient:
    def __init__(self):
        self.transcriptions = FakeTranscriptions()
        self.audio = type("Audio", (), {"transcriptions": self.transcriptions})()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_a_pause_ends_a_turn_and_the_turn_is_transcribed_on_its_own() -> None:
    client = FakeClient()
    microphone = _microphone(_tone(600), _silence(PAUSE_MS + 100), _tone(600), _silence(PAUSE_MS + 100))

    transcripts = [text async for text in SegmentingTranscriber(client).transcribe(microphone)]

    assert transcripts == ["turn 1", "turn 2"]
    assert len(client.transcriptions.durations) == 2


@pytest.mark.anyio
async def test_speech_still_going_when_the_microphone_closes_is_not_dropped() -> None:
    """Releasing the button mid-sentence has to transcribe the sentence, not discard it."""
    client = FakeClient()

    transcripts = [text async for text in SegmentingTranscriber(client).transcribe(_microphone(_tone(900)))]

    assert transcripts == ["turn 1"]


@pytest.mark.anyio
async def test_a_quiet_room_is_never_sent_anywhere() -> None:
    client = FakeClient()
    microphone = _microphone(_silence(3000), _tone(50), _silence(3000))

    transcripts = [text async for text in SegmentingTranscriber(client).transcribe(microphone)]

    assert transcripts == []
    assert client.transcriptions.durations == []
