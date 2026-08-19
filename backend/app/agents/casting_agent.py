"""CastingAgent - Análise e matching de castings."""
from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability

class CastingAgent(VisionAgent):
    def __init__(self):
        super().__init__(
            name="CastingAgent",
            description="Análise e matching de castings",
            capabilities=[
                AgentCapability.CASTING_ANALYSIS,
                AgentCapability.CASTING_MATCHING,
                AgentCapability.CASTING_APPLICATION,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in ["ANALYZE_CASTING", "SEARCH_CASTINGS", "PREPARE_APPLICATION"]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()
        return AgentResult(
            success=True,
            data={"message": "CastingAgent mock execution", "intent": context.intent},
            message="Casting analisado com sucesso",
        )

    def validate(self, result: AgentResult) -> bool:
        return result.success
