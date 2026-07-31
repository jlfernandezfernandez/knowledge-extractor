"""Unit tests for the seed module."""

from unittest.mock import MagicMock
from knowli.seed import ensure_seed_users, seed_database
from knowli.domain.user import User


def test_ensure_seed_users_creates_demo_and_alice():
    mock_store = MagicMock()
    mock_store.get_user_credentials.return_value = None
    mock_store.create_user.side_effect = lambda email, name, pwd: User(
        id=f"id-{email}", email=email, display_name=name
    )

    mock_services = MagicMock()
    mock_services.store = mock_store

    demo, alice = ensure_seed_users(mock_services)
    assert demo.email == "demo@knowli.local"
    assert alice.email == "alice@knowli.local"


def test_seed_database_skips_when_history_exists():
    mock_store = MagicMock()
    mock_store.get_user_credentials.return_value = None
    mock_store.create_user.side_effect = lambda email, name, pwd: User(
        id=f"id-{email}", email=email, display_name=name
    )
    # Simulate history existing
    mock_store.list_history.return_value = (["item1"], None)

    mock_services = MagicMock()
    mock_services.store = mock_store

    seed_database(mock_services)
    # Should not create contributions if history already exists
    mock_store.create_contribution.assert_not_called()
