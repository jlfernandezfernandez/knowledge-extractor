"""Authenticated microphone transcription endpoint."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from ... import wiring
from ...domain.ports import Transcriber
from .auth import CurrentUserDep
from .schemas import TranscriptionResponse

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])
log = logging.getLogger(__name__)


def get_transcriber(request: Request) -> Transcriber:
    return wiring.services(request.app).transcriber


TranscriberDep = Annotated[Transcriber, Depends(get_transcriber)]
AudioUpload = Annotated[UploadFile, File()]


@router.post("", response_model=TranscriptionResponse)
def transcribe(
    audio: AudioUpload,
    _: CurrentUserDep,
    transcriber: TranscriberDep,
) -> TranscriptionResponse:
    if not (audio.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="audio_file_required")

    try:
        text = transcriber.transcribe(audio.file, audio.filename or "recording.webm")
    except Exception as error:
        log.exception("Microphone transcription failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="transcription_unavailable") from error

    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_speech_detected")
    return TranscriptionResponse(text=text)
