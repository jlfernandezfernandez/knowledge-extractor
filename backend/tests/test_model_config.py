"""The default text model is a local OpenAI-compatible endpoint."""


def test_model_defaults_point_to_the_installed_local_ollama_service():
    from knowli import config

    assert config.MODEL_NAME == "qwen3.5:9b"
    assert config.MODEL_API_KEY == "ollama"
    assert config.MODEL_BASE_URL == "http://host.docker.internal:11434/v1"
