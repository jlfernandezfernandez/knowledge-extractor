"""Authenticated audio transcription HTTP contract."""

import httpx
import pytest
from fastapi import FastAPI

from knowli.domain.user import User
from knowli.interfaces.http import auth, transcription
from knowli.interfaces.http.errors import register_error_handlers


class FakeTranscriber:
    def __init__(self):
        self.audio = b""

    def transcribe(self, audio, filename) -> str:
        assert filename == "recording.webm"
        self.audio = audio.read()
        return "Deploy production on Tuesdays."


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_authenticated_user_can_transcribe_microphone_audio() -> None:
    transcriber = FakeTranscriber()
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(transcription.router)
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="ada@example.test", display_name="Ada"
    )
    app.dependency_overrides[transcription.get_transcriber] = lambda: transcriber

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/transcriptions",
            files={"audio": ("recording.webm", b"recording", "audio/webm")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "Deploy production on Tuesdays."}
    assert transcriber.audio == b"recording"


@pytest.mark.anyio
async def test_transcription_rejects_non_audio_uploads() -> None:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(transcription.router)
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="ada@example.test", display_name="Ada"
    )
    app.dependency_overrides[transcription.get_transcriber] = FakeTranscriber

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/transcriptions",
            files={"audio": ("notes.txt", b"not audio", "text/plain")},
        )

    assert response.status_code == 415
