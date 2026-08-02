"""Authenticated live microphone transcription over a websocket."""

import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.requests import HTTPConnection

from ... import wiring
from ...domain.ports import Transcriber
from .auth import CurrentUserDep

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])
log = logging.getLogger(__name__)


def get_transcriber(connection: HTTPConnection) -> Transcriber:
    return wiring.services(connection.app).transcriber


TranscriberDep = Annotated[Transcriber, Depends(get_transcriber)]


async def _microphone(socket: WebSocket) -> AsyncIterator[bytes]:
    """16 kHz mono PCM16, until the empty frame the browser sends on stop."""
    async for chunk in socket.iter_bytes():
        if not chunk:
            return
        yield chunk


@router.websocket("")
async def transcribe(socket: WebSocket, _: CurrentUserDep, transcriber: TranscriberDep) -> None:
    await socket.accept()
    try:
        async for transcript in transcriber.transcribe(_microphone(socket)):
            await socket.send_json({"type": "transcript", "text": transcript})
    except WebSocketDisconnect:
        # The speaker closed the tab mid-turn; nothing left to transcribe for.
        return
    except Exception:
        log.exception("Live transcription failed")
        await socket.send_json({"type": "error", "code": "transcription_unavailable"})
    finally:
        # The last transcript is already sent, so this close is what tells the browser
        # the dictation is over: there is no other end-of-stream marker.
        with suppress(RuntimeError):
            await socket.close()
