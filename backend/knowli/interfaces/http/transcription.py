"""Authenticated microphone transcription stream."""

import logging
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from starlette.concurrency import iterate_in_threadpool

from ... import wiring
from ...domain.ports import Transcriber
from .auth import CurrentUserDep

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])
log = logging.getLogger(__name__)


def get_transcriber(request: Request) -> Transcriber:
    return wiring.services(request.app).transcriber


def require_audio(audio: Annotated[UploadFile, File()]) -> UploadFile:
    # A dependency, not the first line of the route: once the stream opens there is
    # no status code left to send, so the rejection has to happen before it.
    if not (audio.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="audio_file_required")
    return audio


TranscriberDep = Annotated[Transcriber, Depends(get_transcriber)]
AudioDep = Annotated[UploadFile, Depends(require_audio)]


# `response_class` is what makes FastAPI frame these events; see review.events.
@router.post("", response_class=EventSourceResponse)
async def transcribe(
    audio: AudioDep,
    _: CurrentUserDep,
    transcriber: TranscriberDep,
) -> AsyncIterable[ServerSentEvent]:
    # The response has already started, so failures travel as an event, not a status.
    spoke = False
    try:
        deltas = transcriber.transcribe(audio.file, audio.filename or "recording.webm")
        async for delta in iterate_in_threadpool(deltas):
            spoke = True
            yield ServerSentEvent(data={"type": "delta", "text": delta})
    except Exception:
        log.exception("Microphone transcription failed")
        yield ServerSentEvent(data={"type": "error", "code": "transcription_unavailable"})
        return

    if not spoke:
        yield ServerSentEvent(data={"type": "error", "code": "no_speech_detected"})
