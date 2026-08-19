"""
Configuração compartilhada para testes pytest.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_db_session():
    """Fixture de sessão de banco mockada."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session
