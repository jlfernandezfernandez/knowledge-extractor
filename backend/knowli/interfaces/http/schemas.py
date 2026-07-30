"""Wire values for the HTTP routes migrated so far."""

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str


class AuthResponse(BaseModel):
    user: UserResponse
