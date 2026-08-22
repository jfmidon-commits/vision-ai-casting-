"""
Configuração compartilhada para testes pytest.

O pytest-asyncio moderno gerencia o event loop automaticamente. Manter um
fixture ``event_loop`` próprio conflita com esse gerenciamento e pode deixar
os testes seguintes sem loop corrente no Python 3.11+.
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
