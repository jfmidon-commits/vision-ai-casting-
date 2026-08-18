"""
Testes dos serviços de domínio.
"""

import pytest
from uuid import uuid4
from datetime import datetime


class TestDigitalTwinService:
    """Testes do DigitalTwinService."""

    @pytest.mark.asyncio
    async def test_create_asset(self):
        from app.modules.digital_twin.service import DigitalTwinService
        service = DigitalTwinService()
        # Teste básico de instanciação
        assert service is not None


class TestCastingService:
    """Testes do CastingService."""

    @pytest.mark.asyncio
    async def test_create_casting(self):
        from app.modules.casting.service import CastingService
        service = CastingService()
        assert service is not None


class TestContentService:
    """Testes do ContentService."""

    @pytest.mark.asyncio
    async def test_create_content(self):
        from app.modules.content.service import ContentService
        service = ContentService()
        assert service is not None


class TestApprovalService:
    """Testes do ApprovalService."""

    @pytest.mark.asyncio
    async def test_service_init(self):
        from app.modules.approval.service import ApprovalService
        service = ApprovalService()
        assert service.whatsapp is not None

    @pytest.mark.asyncio
    async def test_whatsapp_mock(self):
        from app.modules.approval.service import ApprovalService
        service = ApprovalService()

        result = await service.whatsapp.send_approval_request(
            recipient="+5511999999999",
            content_preview="Test",
            approval_id="test_001",
        )

        assert result["type"] == "approval_request"


class TestAITaskService:
    """Testes do AITaskService."""

    @pytest.mark.asyncio
    async def test_service_init(self):
        from app.tasks.service import AITaskService
        service = AITaskService()
        assert service is not None


class TestAuditService:
    """Testes do AuditService."""

    @pytest.mark.asyncio
    async def test_service_init(self):
        from app.audit.service import AuditService
        service = AuditService()
        assert service is not None


class TestMemoryService:
    """Testes do MemoryService."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        from app.memory.service import MemoryService
        service = MemoryService()

        user_id = uuid4()
        await service.store(user_id, "preference", "dark_mode", "preferences")

        value = await service.retrieve(user_id, "preference", "preferences")
        assert value == "dark_mode"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self):
        from app.memory.service import MemoryService
        service = MemoryService()

        value = await service.retrieve(uuid4(), "nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_add_feedback(self):
        from app.memory.service import MemoryService
        service = MemoryService()

        user_id = uuid4()
        await service.add_feedback(
            user_id=user_id,
            item_type="content",
            item_id="123",
            feedback="Gostei muito!",
            rating=5,
        )

        memory = await service.get_user_memory(user_id)
        assert "feedback" in memory
