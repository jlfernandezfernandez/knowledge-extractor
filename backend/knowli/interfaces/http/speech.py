"""Dictation over a websocket."""

import asyncio
from contextlib import suppress

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ... import wiring

router = APIRouter(tags=["capture"])


@router.websocket("/api/transcribe/live")
async def transcribe_live(websocket: WebSocket) -> None:
    """Dictation, transcribed while you speak.

    The client streams raw 16 kHz mono PCM16; the server pushes back each
    segment as a voice-activity detector closes it, so the text arrives roughly
    a phrase at a time instead of all at once when you stop.

    Decoding blocks, so it runs in a worker thread — otherwise a long segment
    would stall the event loop and stop the socket draining.
    """
    await websocket.accept()
    try:
        transcriber = await asyncio.to_thread(wiring.create_transcriber)
    except Exception as error:
        await websocket.send_json({"type": "error", "detail": str(error)})
        await websocket.close()
        return

    await websocket.send_json({"type": "ready"})
    try:
        while True:
            message = await websocket.receive()
            if chunk := message.get("bytes"):
                samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                for text in await asyncio.to_thread(lambda: list(transcriber.feed(samples))):
                    await websocket.send_json({"type": "segment", "text": text})
            elif message.get("text") == "stop":
                for text in await asyncio.to_thread(lambda: list(transcriber.flush())):
                    await websocket.send_json({"type": "segment", "text": text})
                await websocket.send_json({"type": "done"})
                break
            elif message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        with suppress(RuntimeError):
            await websocket.close()
