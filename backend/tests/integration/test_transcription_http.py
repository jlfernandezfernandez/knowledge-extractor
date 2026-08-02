"""Authenticated live transcription websocket contract."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from knowli.domain.user import User
from knowli.interfaces.http import auth, transcription
from knowli.interfaces.http.errors import register_error_handlers


class FakeTranscriber:
    """Answers every chunk while the microphone is still open, as a live session does."""

    def __init__(self, failure: Exception | None = None):
        self.audio = b""
        self.failure = failure

    async def transcribe(self, audio):
        async for chunk in audio:
            if self.failure is not None:
                raise self.failure
            self.audio += chunk
            yield f"heard {chunk.decode()}"


def _app(transcriber: FakeTranscriber) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(transcription.router)
    app.dependency_overrides[auth.require_user] = lambda: User(
        id="user-1", email="ada@example.test", display_name="Ada"
    )
    app.dependency_overrides[transcription.get_transcriber] = lambda: transcriber
    return app


def test_transcripts_arrive_while_the_microphone_is_still_open() -> None:
    transcriber = FakeTranscriber()

    with TestClient(_app(transcriber)).websocket_connect("/api/transcriptions") as socket:
        socket.send_bytes(b"first turn")
        assert socket.receive_json() == {"type": "transcript", "text": "heard first turn"}
        socket.send_bytes(b"second turn")
        assert socket.receive_json() == {"type": "transcript", "text": "heard second turn"}
        socket.send_bytes(b"")

    assert transcriber.audio == b"first turnsecond turn"


def test_a_failing_session_reports_itself_before_the_socket_closes() -> None:
    """The socket is already accepted, so the failure travels as an event, not a status."""
    app = _app(FakeTranscriber(failure=RuntimeError("speaches is down")))

    with TestClient(app).websocket_connect("/api/transcriptions") as socket:
        socket.send_bytes(b"anything")

        assert socket.receive_json() == {"type": "error", "code": "transcription_unavailable"}
