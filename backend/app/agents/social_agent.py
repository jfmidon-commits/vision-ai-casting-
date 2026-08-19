"""SocialAgent - Criação e gestão de conteúdo social."""
from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability

class SocialAgent(VisionAgent):
    def __init__(self):
        super().__init__(
            name="SocialAgent",
            description="Criação e gestão de conteúdo social",
            capabilities=[
                AgentCapability.CONTENT_CREATION,
                AgentCapability.CONTENT_SCHEDULING,
                AgentCapability.SOCIAL_PUBLISHING,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in ["CREATE_CONTENT", "SCHEDULE_CONTENT", "PUBLISH_CONTENT"]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()
        return AgentResult(
            success=True,
            data={"message": "SocialAgent mock execution", "intent": context.intent},
            message="Conteúdo social criado com sucesso",
            requires_approval=True,
            approval_type="CONTENT",
        )

    def validate(self, result: AgentResult) -> bool:
        return result.success
