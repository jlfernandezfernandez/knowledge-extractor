from io import BytesIO
from types import SimpleNamespace

from knowli.infrastructure.transcription import OpenAICompatibleTranscriber


class FakeTranscriptions:
    def __init__(self):
        self.received = None

    def create(self, **kwargs):
        self.received = kwargs
        return [
            SimpleNamespace(type="transcript.text.delta", delta="Captured"),
            SimpleNamespace(type="transcript.text.delta", delta=" knowledge."),
            SimpleNamespace(type="transcript.text.done", text="Captured knowledge."),
        ]


class FakeClient:
    def __init__(self):
        self.transcriptions = FakeTranscriptions()
        self.audio = type("Audio", (), {"transcriptions": self.transcriptions})()


def test_compatible_transcriber_streams_the_deltas_it_is_given():
    """The `done` event repeats text the deltas already carried, so it is not re-emitted."""
    client = FakeClient()

    deltas = list(OpenAICompatibleTranscriber(client).transcribe(BytesIO(b"recording"), "recording.webm"))

    assert deltas == ["Captured", " knowledge."]
    assert client.transcriptions.received["stream"] is True
    assert client.transcriptions.received["model"]
    assert client.transcriptions.received["file"][0] == "recording.webm"
