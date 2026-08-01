"""The one OpenAI-compatible transcription adapter."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, BinaryIO

from .. import config
from ..domain.ports import Transcriber


class OpenAICompatibleTranscriber:
    """OpenAI and compatible `/audio/transcriptions` endpoints."""

    def __init__(self, client: Any | None = None):
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client

        from openai import OpenAI

        self._client = OpenAI(
            api_key=config.TRANSCRIPTION_API_KEY,
            base_url=config.TRANSCRIPTION_BASE_URL or None,
        )
        return self._client

    def transcribe(self, audio: BinaryIO, filename: str) -> Iterator[str]:
        """Whisper decodes segment by segment, so `stream=True` is what makes the
        transcript arrive while it is still being produced instead of after."""
        stream = self.client.audio.transcriptions.create(
            file=(filename, audio), model=config.TRANSCRIPTION_MODEL, stream=True
        )
        for event in stream:
            # ponytail: only the OpenAI delta event is read. A provider that streams
            # under other event names transcribes to nothing, which the endpoint
            # reports as `no_speech_detected`.
            if getattr(event, "type", None) == "transcript.text.delta" and event.delta:
                yield event.delta


def create_transcriber() -> Transcriber:
    return OpenAICompatibleTranscriber()
