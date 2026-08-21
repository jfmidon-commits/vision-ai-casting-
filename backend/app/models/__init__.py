from enum import Enum

from .models import (
    Tenant, User, Profile, Photoshoot, Photo, Analysis, Report, Evaluation,
    # Vision Core v0.1
    DigitalTwinAsset, Casting, CastingMatch, ContentItem, ContentApproval,
    AITask, AuditLog, VoiceCommand, Workflow, WorkflowRun, Notification,
    # Memory & Feedback
    UserMemory, UserFeedback,
    # Etapa 1: Career Memory / Talent Graph
    ProfessionalExperience, Character, Campaign,
    Agency, AgencyContact, CareerFeedback,
    AppearanceRecord, StylePreference, ContentPerformance,
    # Etapa 2: Digital Twin Versioning
    DigitalTwinVersion,
    # Etapa 3: Identity / Appearance / Character
    IdentityTrait, AppearanceState, CharacterTransformation,
    # Etapa 5: Identity Preservation
    IdentityReference, AssetOriginLog,
)


class MemoryCategory(str, Enum):
    """Categorias estáveis aceitas pela camada de memória.

    O banco persiste a categoria como string; o enum existe como contrato de
    domínio para consumidores legados sem exigir uma coluna enum no banco.
    """

    GENERAL = "general"
    PREFERENCE = "preference"
    DECISION = "decision"
    FEEDBACK = "feedback"
    CONTEXT = "context"


__all__ = [
    "Tenant", "User", "Profile", "Photoshoot", "Photo", "Analysis", "Report", "Evaluation",
    "DigitalTwinAsset", "Casting", "CastingMatch", "ContentItem", "ContentApproval",
    "AITask", "AuditLog", "VoiceCommand", "Workflow", "WorkflowRun", "Notification",
    # Memory & Feedback
    "UserMemory", "UserFeedback", "MemoryCategory",
    # Etapa 1
    "ProfessionalExperience", "Character", "Campaign",
    "Agency", "AgencyContact", "CareerFeedback",
    "AppearanceRecord", "StylePreference", "ContentPerformance",
    # Etapa 2
    "DigitalTwinVersion",
    # Etapa 3
    "IdentityTrait", "AppearanceState", "CharacterTransformation",
    # Etapa 5
    "IdentityReference", "AssetOriginLog",
]
