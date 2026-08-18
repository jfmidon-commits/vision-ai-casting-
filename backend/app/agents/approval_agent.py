"""ApprovalAgent - Gestão de workflows de aprovação."""
from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability

class ApprovalAgent(VisionAgent):
    def __init__(self):
        super().__init__(
            name="ApprovalAgent",
            description="Gestão de workflows de aprovação",
            capabilities=[
                AgentCapability.APPROVAL_WORKFLOW,
                AgentCapability.HUMAN_REVIEW,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in ["REQUEST_APPROVAL", "CHECK_APPROVAL_STATUS"]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()
        return AgentResult(
            success=True,
            data={"message": "ApprovalAgent mock execution", "intent": context.intent},
            message="Solicitação de aprovação enviada",
        )

    def validate(self, result: AgentResult) -> bool:
        return result.success
