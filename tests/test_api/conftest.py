"""
Pytest configuration and fixtures for API tests.
"""
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session():
    """
    Create a mock database session for testing.

    Returns:
        Mock Session object
    """
    session = MagicMock(spec=Session)
    return session
