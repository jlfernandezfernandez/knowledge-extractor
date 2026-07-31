"""Idempotent seed script to populate initial users, vector claims, and demo UI state."""

from __future__ import annotations

import logging
from pwdlib import PasswordHash

from .application.auth import DEMO_DISPLAY_NAME, DEMO_EMAIL, DEMO_PASSWORD
from .domain.claim import ClaimToCommit
from .domain.user import DuplicateEmail, User
from .wiring import AppServices

ALICE_EMAIL = "alice@knowli.local"
ALICE_PASSWORD = "demo"
ALICE_DISPLAY_NAME = "Alice Developer"

logger = logging.getLogger(__name__)

INITIAL_SEED_KNOWLEDGE = [
    {
        "source_text": "Los despliegues a producción se realizan exclusivamente los martes a las 10:00 AM tras superar la suite de pruebas.",
        "claims": [
            {
                "draft_key": "seed-1",
                "title": "Horario de despliegues",
                "statement": "Los despliegues a producción se realizan exclusivamente los martes a las 10:00 AM tras superar la suite de pruebas.",
                "tags": ["ops", "deployment"],
            }
        ],
    },
    {
        "source_text": "Knowli utiliza FastAPI en backend, PostgreSQL pgvector para búsqueda híbrida RRF y React en frontend.",
        "claims": [
            {
                "draft_key": "seed-2",
                "title": "Stack Tecnológico",
                "statement": "Knowli está construido con FastAPI en el backend, PostgreSQL pgvector para búsqueda híbrida RRF y React en el frontend.",
                "tags": ["architecture", "stack"],
            }
        ],
    },
    {
        "source_text": "El modelo de texto por defecto es Ollama ejecutando qwen3.5:9b y las transcripciones de voz utilizan Whisper.",
        "claims": [
            {
                "draft_key": "seed-3",
                "title": "Modelos de IA Locales",
                "statement": "El modelo de lenguaje por defecto es Ollama ejecutando qwen3.5:9b y las transcripciones de voz utilizan Whisper.",
                "tags": ["ai", "models"],
            }
        ],
    },
    {
        "source_text": "Las sesiones de usuario se gestionan mediante tokens opacos almacenados en cookies HTTP-only de desarrollo.",
        "claims": [
            {
                "draft_key": "seed-4",
                "title": "Seguridad y Sesiones",
                "statement": "Las sesiones de usuario utilizan tokens opacos guardados en cookies HTTP-only de desarrollo.",
                "tags": ["security", "auth"],
            }
        ],
    },
]


def ensure_seed_users(services: AppServices) -> tuple[User, User]:
    """Ensure demo and alice users exist."""
    password_hash = PasswordHash.recommended().hash(DEMO_PASSWORD)

    demo_creds = services.store.get_user_credentials(DEMO_EMAIL)
    if demo_creds is None:
        try:
            demo_user = services.store.create_user(
                DEMO_EMAIL, DEMO_DISPLAY_NAME, password_hash
            )
        except DuplicateEmail:
            demo_user = services.store.get_user_credentials(DEMO_EMAIL).user
    else:
        demo_user = demo_creds.user

    alice_creds = services.store.get_user_credentials(ALICE_EMAIL)
    if alice_creds is None:
        try:
            alice_user = services.store.create_user(
                ALICE_EMAIL, ALICE_DISPLAY_NAME, password_hash
            )
        except DuplicateEmail:
            alice_user = services.store.get_user_credentials(ALICE_EMAIL).user
    else:
        alice_user = alice_creds.user

    return demo_user, alice_user


def seed_database(services: AppServices | None = None) -> None:
    """Populate initial users, vectorized knowledge claims, and demo UI state."""
    services = services or AppServices()
    demo_user, alice_user = ensure_seed_users(services)

    # Check if knowledge claims already exist
    history, _ = services.store.list_history(cursor=None, limit=1)
    if not history:
        logger.info("Seeding initial vectorized knowledge claims...")
        for item in INITIAL_SEED_KNOWLEDGE:
            raw_text = item["source_text"]
            contribution = services.store.create_contribution(
                demo_user.id, raw_text, source="text"
            )

            claims_to_commit = []
            for c in item["claims"]:
                vectors = services.embedder.embed([c["statement"]])
                claims_to_commit.append(
                    ClaimToCommit(
                        draft_key=c["draft_key"],
                        title=c["title"],
                        statement=c["statement"],
                        tags=tuple(c["tags"]),
                        embedding=tuple(vectors[0]),
                        supersedes=(),
                    )
                )

            summary = " ".join(c.statement for c in claims_to_commit)
            saved = services.store.save_review(
                contribution.id, contribution.revision, "commit", summary
            )
            services.store.commit_claims(
                contribution.id, saved.revision, claims_to_commit
            )

        # Seed 1 pending contribution in 'claims' stage created by Alice (for testing UI review flow)
        services.store.create_contribution(
            alice_user.id,
            "Política de retención de logs y auditoría en entornos locales.",
            source="text",
        )

        # Seed 1 pending interview from Alice to Demo
        services.store.create_interview(
            requester_id=alice_user.id,
            assignee_id=demo_user.id,
            title="Políticas de retención de datos en PostgreSQL",
            brief="Por favor aclara cuánto tiempo se conservan los datos de auditoría en desarrollo.",
        )
        logger.info("Seed completed successfully!")
    else:
        logger.info("Seed skipping: knowledge claims already exist.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    seed_database()


if __name__ == "__main__":
    main()
