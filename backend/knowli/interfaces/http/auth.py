"""HTTP parsing and cookie serialization for local account sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from ... import config, wiring
from ...application.auth import AuthService, SessionExpired
from ...domain.user import User
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse, UsersResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])
COOKIE = "knowli_session"


def get_auth_service(request: Request) -> AuthService:
    return wiring.services(request.app).auth


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def require_user(request: Request) -> User:
    token = request.cookies.get(COOKIE)
    if token is None:
        raise SessionExpired()
    override = request.app.dependency_overrides.get(get_auth_service)
    service = override() if override is not None else get_auth_service(request)
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


@users_router.get("", response_model=UsersResponse)
def users(user: CurrentUserDep, service: AuthServiceDep) -> UsersResponse:
    return UsersResponse(
        items=[
            UserResponse(id=person.id, email=person.email, display_name=person.display_name)
            for person in service.list_users(user.id)
        ]
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, service: AuthServiceDep) -> None:
    if token := request.cookies.get(COOKIE):
        service.logout(token)
    response.delete_cookie(COOKIE)
