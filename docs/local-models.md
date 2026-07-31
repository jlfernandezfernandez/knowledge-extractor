# Local models

Knowli keeps embeddings local by default. Its text model and microphone
transcription each use one OpenAI-compatible endpoint.

## Text model

The default is the local Ollama model used for development: `qwen3.5:9b`
(about 6.6 GB). Install and start it once:

```bash
ollama pull qwen3.5:9b
ollama serve
```

Docker reaches Ollama through `host.docker.internal`:

```bash
MODEL_BASE_URL=http://host.docker.internal:11434/v1
MODEL_API_KEY=ollama
MODEL_NAME=qwen3.5:9b
```

For OpenAI, Groq, OpenRouter, or another compatible provider, change only
those three values. When running the backend directly, replace
`host.docker.internal` with `localhost`.

## Microphone transcription

Knowli sends the microphone recording to an OpenAI-compatible
`/audio/transcriptions` endpoint. The recommended local setup is
[Speaches](https://github.com/speaches-ai/speaches), which runs Faster-Whisper
on your computer. Docker reaches it through `host.docker.internal`:

```bash
TRANSCRIPTION_BASE_URL=http://host.docker.internal:8000/v1
TRANSCRIPTION_API_KEY=local
TRANSCRIPTION_MODEL=Systran/faster-whisper-small
```

If you run the backend directly instead of through Docker, use `localhost` in
the base URL. The speech service owns its model download and storage; Knowli
does not add a model container or volume.

Use any other compatible service by changing those three values. For OpenAI:

```bash
TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
TRANSCRIPTION_API_KEY=your-key
TRANSCRIPTION_BASE_URL=https://api.openai.com/v1
```
