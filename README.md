# Knowli

Human-in-the-loop knowledge extractor built with FastAPI, LangGraph, PostgreSQL, and React.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000) (Demo account: `demo@knowli.local` / `demo`).

## Development & Tests

```bash
# Backend tests
uv run --directory backend pytest --ignore=tests/integration -q

# Frontend tests
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

## License

Apache-2.0
