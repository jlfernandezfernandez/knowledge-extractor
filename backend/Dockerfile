FROM python:3.12-slim AS builder

WORKDIR /app
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/knowli ./knowli
COPY README.md /README.md
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim AS runtime

RUN groupadd --system knowli && useradd --system --gid knowli --create-home knowli
COPY --from=builder /opt/venv /opt/venv
USER knowli
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "python -c 'from knowli.infrastructure.postgres.pool import init; init()' && exec uvicorn knowli.interfaces.http.main:app --host 0.0.0.0 --port 8000"]
