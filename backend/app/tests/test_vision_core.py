"""
Testes unitários do Vision Core.

Cobertura:
- VisionCoreService
- AgentRouter
- IntentRecognizer
- EventBus
- Mock Connectors
"""

import pytest
import asyncio
from uuid import uuid4

from app.vision_core import VisionCoreService, IntentRecognizer, IntentType
from app.vision_core.agent_router import AgentRouter
from app.agents.base import AgentContext, AgentCapability
from app.agents.social_agent import SocialAgent
from app.agents.casting_agent import CastingAgent
from app.agents.identity_agent import IdentityAgent
from app.core.event_bus import event_bus, VisionEventType, emit_event


# ========== FIXTURES ==========

@pytest.fixture
def vision_core():
    """Fixture do Vision Core com agentes registrados."""
    service = VisionCoreService()
    service.register_agents([
        SocialAgent(),
        CastingAgent(),
        IdentityAgent(),
    ])
    return service


@pytest.fixture
def agent_router():
    """Fixture do Agent Router."""
    router = AgentRouter()
    router.register(SocialAgent())
    router.register(CastingAgent())
    return router


@pytest.fixture
def sample_context():
    """Fixture de contexto de exemplo."""
    return AgentContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        intent="CREATE_CONTENT",
        input_data={"text": "cria uma postagem"},
    )


# ========== INTENT RECOGNIZER TESTS ==========

class TestIntentRecognizer:
    """Testes do reconhecedor de intenções."""

    def test_recognize_create_content(self):
        recognizer = IntentRecognizer()
        intent = recognizer.recognize("cria uma postagem minha")
        assert intent == IntentType.CREATE_CONTENT

    def test_recognize_analyze_casting(self):
        recognizer = IntentRecognizer()
        intent = recognizer.recognize("analisa esse casting")
        assert intent == IntentType.ANALYZE_CASTING

    def test_recognize_update_profile(self):
        recognizer = IntentRecognizer()
        intent = recognizer.recognize("atualiza meu perfil")
        assert intent == IntentType.UPDATE_PROFILE

    def test_recognize_search_opportunities(self):
        recognizer = IntentRecognizer()
        intent = recognizer.recognize("procura oportunidades")
        assert intent == IntentType.SEARCH_OPPORTUNITIES

    def test_recognize_unknown(self):
        recognizer = IntentRecognizer()
        intent = recognizer.recognize("texto sem sentido algum")
        assert intent == IntentType.UNKNOWN

    def test_recognize_with_confidence(self):
        recognizer = IntentRecognizer()
        result = recognizer.recognize_with_confidence("cria um carrossel")
        assert result["intent"] == "CREATE_CONTENT"
        assert result["confidence"] == 0.9
        assert result["raw_text"] == "cria um carrossel"

    def test_recognize_unknown_confidence(self):
        recognizer = IntentRecognizer()
        result = recognizer.recognize_with_confidence("xyz abc 123")
        assert result["intent"] == "UNKNOWN"
        assert result["confidence"] == 0.0


# ========== AGENT ROUTER TESTS ==========

class TestAgentRouter:
    """Testes do roteador de agentes."""

    def test_register_agent(self, agent_router):
        agents = agent_router.get_all_agents()
        assert len(agents) == 2

    def test_get_agent_by_intent(self, agent_router, sample_context):
        agent = agent_router.get_agent(sample_context)
        assert agent is not None
        assert agent.name == "SocialAgent"

    def test_get_agent_casting_intent(self, agent_router):
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="ANALYZE_CASTING",
            input_data={"text": "analisa casting"},
        )
        agent = agent_router.get_agent(context)
        assert agent is not None
        assert agent.name == "CastingAgent"

    def test_get_agent_not_found(self, agent_router):
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="UNKNOWN_INTENT",
            input_data={"text": "xyz"},
        )
        agent = agent_router.get_agent(context)
        assert agent is None

    def test_get_agent_by_name(self, agent_router):
        agent = agent_router.get_agent_by_name("SocialAgent")
        assert agent is not None
        assert agent.name == "SocialAgent"

    def test_get_agent_by_name_not_found(self, agent_router):
        agent = agent_router.get_agent_by_name("NonExistent")
        assert agent is None

    def test_get_health(self, agent_router):
        health = agent_router.get_health()
        assert health["total_agents"] == 2
        assert len(health["agents"]) == 2


# ========== AGENT TESTS ==========

class TestSocialAgent:
    """Testes do SocialAgent."""

    @pytest.mark.asyncio
    async def test_can_handle_create_content(self):
        agent = SocialAgent()
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="CREATE_CONTENT",
            input_data={},
        )
        assert agent.can_handle(context) is True

    @pytest.mark.asyncio
    async def test_cannot_handle_casting(self):
        agent = SocialAgent()
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="ANALYZE_CASTING",
            input_data={},
        )
        assert agent.can_handle(context) is False

    @pytest.mark.asyncio
    async def test_execute_returns_approval_required(self):
        agent = SocialAgent()
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="CREATE_CONTENT",
            input_data={"text": "cria post"},
        )
        result = await agent.execute(context)
        assert result.success is True
        assert result.requires_approval is True
        assert result.approval_type == "CONTENT"

    def test_validate_success(self):
        agent = SocialAgent()
        from app.agents.base import AgentResult
        result = AgentResult(success=True, data={})
        assert agent.validate(result) is True


class TestCastingAgent:
    """Testes do CastingAgent."""

    @pytest.mark.asyncio
    async def test_execute(self):
        agent = CastingAgent()
        context = AgentContext(
            user_id=uuid4(),
            tenant_id=uuid4(),
            intent="ANALYZE_CASTING",
            input_data={"text": "analisa casting"},
        )
        result = await agent.execute(context)
        assert result.success is True
        assert result.requires_approval is False


# ========== VISION CORE SERVICE TESTS ==========

class TestVisionCoreService:
    """Testes do serviço principal do Vision Core."""

    @pytest.mark.asyncio
    async def test_process_command_create_content(self, vision_core):
        result = await vision_core.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="cria uma postagem minha",
        )
        assert result["success"] is True
        assert result["intent"] == "CREATE_CONTENT"
        assert "command_id" in result
        assert "correlation_id" in result
        assert result["requires_approval"] is True

    @pytest.mark.asyncio
    async def test_process_command_analyze_casting(self, vision_core):
        result = await vision_core.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="analisa esse casting",
        )
        assert result["success"] is True
        assert result["intent"] == "ANALYZE_CASTING"
        assert result["agent"] == "CastingAgent"

    @pytest.mark.asyncio
    async def test_process_command_unknown(self, vision_core):
        result = await vision_core.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="xyz abc comando desconhecido",
        )
        # Deve retornar sucesso mas com agente que pode não ser ideal
        assert "command_id" in result
        assert "intent" in result

    @pytest.mark.asyncio
    async def test_process_command_empty_text(self, vision_core):
        result = await vision_core.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="",
        )
        assert result["success"] is False  # texto vazio deve falhar

    def test_get_command_history(self, vision_core):
        history = vision_core.get_command_history(limit=10)
        assert isinstance(history, list)

    def test_get_health(self, vision_core):
        health = vision_core.get_health()
        assert health["status"] == "healthy"
        assert "agents" in health
        assert "intent_recognizer" in health


# ========== EVENT BUS TESTS ==========

class TestEventBus:
    """Testes do barramento de eventos."""

    @pytest.mark.asyncio
    async def test_emit_and_receive(self):
        events_received = []

        async def handler(event):
            events_received.append(event)

        event_bus.subscribe(VisionEventType.AI_TASK_CREATED, handler)

        await emit_event(
            event_type=VisionEventType.AI_TASK_CREATED,
            payload={"test": True, "value": 42},
        )

        assert len(events_received) == 1
        assert events_received[0].event_type == VisionEventType.AI_TASK_CREATED
        assert events_received[0].payload["test"] is True

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        events_1 = []
        events_2 = []

        async def handler1(event):
            events_1.append(event)

        async def handler2(event):
            events_2.append(event)

        event_bus.subscribe(VisionEventType.AI_TASK_COMPLETED, handler1)
        event_bus.subscribe(VisionEventType.AI_TASK_COMPLETED, handler2)

        await emit_event(
            event_type=VisionEventType.AI_TASK_COMPLETED,
            payload={"task_id": "123"},
        )

        assert len(events_1) == 1
        assert len(events_2) == 1

    @pytest.mark.asyncio
    async def test_global_handler(self):
        all_events = []

        async def global_handler(event):
            all_events.append(event)

        event_bus.subscribe_all(global_handler)

        await emit_event(
            event_type=VisionEventType.CONTENT_CREATED,
            payload={"content_id": "456"},
        )

        assert len(all_events) == 1

    def test_get_stats(self):
        stats = event_bus.get_stats()
        assert "total_events_emitted" in stats
        assert "registered_event_types" in stats

    def test_singleton(self):
        from app.core.event_bus import EventBus
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2


# ========== MOCK CONNECTOR TESTS ==========

class TestMockInstagramConnector:
    """Testes do conector mock do Instagram."""

    @pytest.mark.asyncio
    async def test_connect(self):
        from app.connectors import MockInstagramConnector
        connector = MockInstagramConnector()
        result = await connector.connect({})
        assert result is True
        assert connector.status.value == "connected"

    @pytest.mark.asyncio
    async def test_publish_post(self):
        from app.connectors import MockInstagramConnector
        connector = MockInstagramConnector()
        await connector.connect({})

        result = await connector.publish_post(
            content="Test post #vision",
            media_urls=["https://example.com/image.jpg"],
        )

        assert result.success is True
        assert result.post_id is not None
        assert result.post_id.startswith("mock_post_")
        assert "instagram.com" in result.url

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        from app.connectors import MockInstagramConnector
        connector = MockInstagramConnector()
        await connector.connect({})

        # Primeiro publica
        post = await connector.publish_post(
            content="Test",
            media_urls=["https://example.com/img.jpg"],
        )

        # Depois pega métricas
        metrics = await connector.get_metrics(post.post_id)
        assert metrics["post_id"] == post.post_id
        assert "metrics" in metrics
        assert "likes" in metrics["metrics"]

    @pytest.mark.asyncio
    async def test_schedule_post(self):
        from app.connectors import MockInstagramConnector
        connector = MockInstagramConnector()
        await connector.connect({})

        from datetime import datetime, timedelta
        scheduled = await connector.schedule_post(
            content="Scheduled post",
            media_urls=["https://example.com/img.jpg"],
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
        )

        assert scheduled["status"] == "scheduled"
        assert scheduled["mock"] is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        from app.connectors import MockInstagramConnector
        connector = MockInstagramConnector()
        await connector.connect({})

        health = await connector.health_check()
        assert health["status"] == "healthy"
        assert health["mock"] is True


class TestMockWhatsAppConnector:
    """Testes do conector mock do WhatsApp."""

    @pytest.mark.asyncio
    async def test_connect(self):
        from app.connectors import MockWhatsAppConnector
        connector = MockWhatsAppConnector()
        result = await connector.connect({})
        assert result is True

    @pytest.mark.asyncio
    async def test_send_message(self):
        from app.connectors import MockWhatsAppConnector
        connector = MockWhatsAppConnector()
        await connector.connect({})

        result = await connector.send_message(
            recipient="+5511999999999",
            content="Hello from Vision",
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "+5511999999999"

    @pytest.mark.asyncio
    async def test_send_approval_request(self):
        from app.connectors import MockWhatsAppConnector
        connector = MockWhatsAppConnector()
        await connector.connect({})

        result = await connector.send_approval_request(
            recipient="+5511999999999",
            content_preview="Nova postagem para aprovação",
            approval_id="approval_001",
        )

        assert result["type"] == "approval_request"
        assert result["approval_id"] == "approval_001"
        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_message_with_buttons(self):
        from app.connectors import MockWhatsAppConnector
        connector = MockWhatsAppConnector()
        await connector.connect({})

        buttons = [
            {"id": "approve", "text": "APROVAR"},
            {"id": "reject", "text": "REJEITAR"},
        ]

        result = await connector.send_message(
            recipient="+5511999999999",
            content="Escolha uma opção:",
            buttons=buttons,
        )

        assert result["status"] == "sent"


# ========== LLM PROVIDER TESTS ==========

class TestLLMProvider:
    """Testes dos provedores de LLM."""

    def test_openai_provider_config(self):
        from app.providers import OpenAIProvider
        provider = OpenAIProvider(
            api_key="test_key",
            model="gpt-4o",
        )
        config = provider.get_config()
        assert config["provider_type"] == "openai"
        assert config["model"] == "gpt-4o"
        assert "api_key" not in config  # Não deve expor a chave

    def test_provider_factory(self):
        from app.providers import LLMProviderFactory, LLMProviderType
        provider = LLMProviderFactory.create(
            LLMProviderType.OPENAI,
            api_key="test",
        )
        assert provider.provider_type == LLMProviderType.OPENAI


# ========== INTEGRATION TESTS ==========

class TestIntegration:
    """Testes de integração do fluxo completo."""

    @pytest.mark.asyncio
    async def test_full_command_flow(self):
        """Testa o fluxo completo: comando -> intenção -> agente -> evento."""
        service = VisionCoreService()
        service.register_agents([SocialAgent(), CastingAgent()])

        events = []
        async def track_events(event):
            events.append(event.event_type.value)

        event_bus.subscribe_all(track_events)

        result = await service.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="cria uma postagem",
        )

        assert result["success"] is True
        assert result["intent"] == "CREATE_CONTENT"
        assert len(events) >= 2  # AI_TASK_CREATED + AI_TASK_COMPLETED + CONTENT_APPROVAL_REQUESTED

    @pytest.mark.asyncio
    async def test_command_with_metadata(self):
        service = VisionCoreService()
        service.register_agents([SocialAgent()])

        result = await service.process_command(
            user_id=uuid4(),
            tenant_id=uuid4(),
            input_type="text",
            text="cria postagem",
            metadata={"platform": "instagram", "style": "professional"},
        )

        assert result["success"] is True
