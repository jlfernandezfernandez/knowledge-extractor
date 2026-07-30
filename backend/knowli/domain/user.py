"""Typed account values that may cross the application boundary."""

from dataclasses import dataclass


class DuplicateEmail(Exception):
    """Raised when an account already owns a normalized email address."""


@dataclass(frozen=True)
class User:
    id: str
    email: str
    display_name: str


@dataclass(frozen=True)
class UserCredentials:
    """The store-only value used to verify a submitted password."""

    user: User
    password_hash: str
