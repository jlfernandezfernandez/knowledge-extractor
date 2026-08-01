"""Authenticated audio transcription HTTP contract."""

import json

import httpx
import pytest
from fastapi import FastAPI

from knowli.domain.user import User
from knowli.interfaces.http import auth, transcription
from knowli.interfaces.http.errors import register_error_handlers


class FakeTranscriber:
    def __init__(self, deltas=("Deploy production", " on Tuesdays.")):
        self.audio = b""
        self.deltas = deltas

    def transcribe(self, audio, filename):
        assert filename == "recording.webm"
        self.audio = audio.read()
        yield from self.deltas


def _app(transcriber) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(transcription.router)
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="ada@example.test", display_name="Ada"
    )
    app.dependency_overrides[transcription.get_transcriber] = lambda: transcriber
    return app


def _events(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: "):])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _deltas(body: str) -> list[str]:
    return [event["text"] for event in _events(body) if event["type"] == "delta"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_authenticated_user_can_transcribe_microphone_audio() -> None:
    transcriber = FakeTranscriber()
    app = _app(transcriber)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/transcriptions",
            files={"audio": ("recording.webm", b"recording", "audio/webm")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert _deltas(response.text) == ["Deploy production", " on Tuesdays."]
    assert transcriber.audio == b"recording"


@pytest.mark.anyio
async def test_silent_recording_reports_no_speech_on_the_stream() -> None:
    """The response has already started, so an empty transcript cannot be a 4xx."""
    app = _app(FakeTranscriber(deltas=()))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/transcriptions",
            files={"audio": ("recording.webm", b"silence", "audio/webm")},
        )

    assert response.status_code == 200
    assert _events(response.text) == [{"type": "error", "code": "no_speech_detected"}]


@pytest.mark.anyio
async def test_transcription_rejects_non_audio_uploads() -> None:
    app = _app(FakeTranscriber())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/transcriptions",
            files={"audio": ("notes.txt", b"not audio", "text/plain")},
        )

    assert response.status_code == 415
