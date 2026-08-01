from io import BytesIO

from knowli.infrastructure.transcription import OpenAICompatibleTranscriber


class FakeTranscriptions:
    def __init__(self):
        self.received = None

    def create(self, **kwargs):
        self.received = kwargs
        return type("Transcript", (), {"text": "Captured knowledge."})()


class FakeClient:
    def __init__(self):
        self.transcriptions = FakeTranscriptions()
        self.audio = type("Audio", (), {"transcriptions": self.transcriptions})()


def test_compatible_transcriber_forwards_audio_with_its_filename():
    client = FakeClient()
    transcript = OpenAICompatibleTranscriber(client).transcribe(
        BytesIO(b"recording"), "recording.webm"
    )

    assert transcript == "Captured knowledge."
    assert client.transcriptions.received["model"]
    assert client.transcriptions.received["file"][0] == "recording.webm"
