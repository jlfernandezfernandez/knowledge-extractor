"""The one OpenAI-compatible transcription adapter."""

from __future__ import annotations

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

    def transcribe(self, audio: BinaryIO, filename: str) -> str:
        response = self.client.audio.transcriptions.create(
            file=(filename, audio), model=config.TRANSCRIPTION_MODEL
        )
        return response.text.strip()


def create_transcriber() -> Transcriber:
    return OpenAICompatibleTranscriber()
