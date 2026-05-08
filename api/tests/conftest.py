"""Pytest fixtures and configuration for MiganCore API tests."""

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def secret_key():
    """Test secret key for license validation."""
    return "test-secret-key-32-chars-long!!!"
