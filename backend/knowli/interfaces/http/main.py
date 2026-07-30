"""`knowli-api` — the web app's backend."""

from . import create_app

app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
