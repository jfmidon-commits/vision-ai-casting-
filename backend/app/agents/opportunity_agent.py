"""OpportunityAgent - Busca e matching de oportunidades."""
from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability

class OpportunityAgent(VisionAgent):
    def __init__(self):
        super().__init__(
            name="OpportunityAgent",
            description="Busca e matching de oportunidades",
            capabilities=[
                AgentCapability.OPPORTUNITY_SEARCH,
                AgentCapability.OPPORTUNITY_MATCHING,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in ["SEARCH_OPPORTUNITIES", "FIND_MATCHES"]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()
        return AgentResult(
            success=True,
            data={"message": "OpportunityAgent mock execution", "intent": context.intent},
            message="Oportunidades encontradas com sucesso",
        )

    def validate(self, result: AgentResult) -> bool:
        return result.success
