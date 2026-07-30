"""One translation point from application failures to stable HTTP errors."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ...application.auth import InvalidCredentials, InvalidRegistration, SessionExpired
from ...application.review import (
    ContributionUnavailable,
    InvalidReview,
    ReviewStageError,
)
from ...domain.contribution import StaleRevision
from ...domain.user import DuplicateEmail


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentials)
    def invalid_credentials(_: Request, __: InvalidCredentials) -> JSONResponse:
        return _error(401, "unauthenticated", "invalid email or password")

    @app.exception_handler(SessionExpired)
    def session_expired(_: Request, __: SessionExpired) -> JSONResponse:
        return _error(401, "unauthenticated", "sign in required")

    @app.exception_handler(DuplicateEmail)
    def duplicate_email(_: Request, __: DuplicateEmail) -> JSONResponse:
        return _error(409, "duplicate_email", "email is already registered")

    @app.exception_handler(InvalidRegistration)
    def invalid_registration(_: Request, error: InvalidRegistration) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": "invalid registration",
                "fields": error.fields,
            },
        )

    @app.exception_handler(RequestValidationError)
    def request_validation(_: Request, error: RequestValidationError) -> JSONResponse:
        fields = {".".join(str(part) for part in item["loc"]): item["msg"] for item in error.errors()}
        return JSONResponse(
            status_code=422,
            content={"code": "validation_error", "message": "invalid request", "fields": fields},
        )

    @app.exception_handler(ContributionUnavailable)
    def contribution_unavailable(_: Request, __: ContributionUnavailable) -> JSONResponse:
        return _error(404, "not_found", "contribution not found")

    @app.exception_handler(StaleRevision)
    def stale_revision(_: Request, __: StaleRevision) -> JSONResponse:
        return _error(409, "stale_revision", "contribution changed; refresh and try again")

    @app.exception_handler(ReviewStageError)
    def wrong_review_stage(_: Request, error: ReviewStageError) -> JSONResponse:
        return _error(409, "invalid_stage", str(error))

    @app.exception_handler(InvalidReview)
    def invalid_review(_: Request, error: InvalidReview) -> JSONResponse:
        return _error(400, "invalid_review", str(error))
