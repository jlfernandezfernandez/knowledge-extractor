"""HTTP parsing and cookie serialization for local account sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from ... import config, wiring
from ...application.auth import AuthService
from ...domain.user import User
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE = "knowli_session"


def get_auth_service() -> AuthService:
    return wiring.auth_service


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def require_user(request: Request, service: AuthServiceDep) -> User:
    token = request.cookies.get(COOKIE)
    if token is None:
        from ...application.auth import SessionExpired

        raise SessionExpired()
    return service.authenticate(token)


CurrentUserDep = Annotated[User, Depends(require_user)]


def _response(user: User) -> AuthResponse:
    return AuthResponse(user=UserResponse(id=user.id, email=user.email, display_name=user.display_name))


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        max_age=config.SESSION_DAYS * 24 * 60 * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, service: AuthServiceDep) -> AuthResponse:
    result = service.register(body.email, body.password, body.display_name)
    _set_session_cookie(response, result.token)
    return _response(result.user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, response: Response, service: AuthServiceDep) -> AuthResponse:
    result = service.login(body.email, body.password)
    _set_session_cookie(response, result.token)
    return _response(result.user)


@router.get("/me", response_model=AuthResponse)
def me(user: CurrentUserDep) -> AuthResponse:
    return _response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, service: AuthServiceDep) -> None:
    if token := request.cookies.get(COOKIE):
        service.logout(token)
    response.delete_cookie(COOKIE)
