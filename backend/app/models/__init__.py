from .models import (
    Tenant, User, Profile, Photoshoot, Photo, Analysis, Report, Evaluation,
    # Vision Core v0.1
    DigitalTwinAsset, Casting, CastingMatch, ContentItem, ContentApproval,
    AITask, AuditLog, VoiceCommand, Workflow, WorkflowRun, Notification,
    # Etapa 1: Career Memory / Talent Graph
    ProfessionalExperience, Character, Campaign,
    Agency, AgencyContact, CareerFeedback,
    AppearanceRecord, StylePreference, ContentPerformance,
    # Etapas 2, 3 e 5: Digital Twin / Identity Preservation
    DigitalTwinVersion, IdentityTrait, AppearanceState, CharacterTransformation,
    IdentityReference, AssetOriginLog,
)

__all__ = [
    "Tenant", "User", "Profile", "Photoshoot", "Photo", "Analysis", "Report", "Evaluation",
    "DigitalTwinAsset", "Casting", "CastingMatch", "ContentItem", "ContentApproval",
    "AITask", "AuditLog", "VoiceCommand", "Workflow", "WorkflowRun", "Notification",
    # Etapa 1
    "ProfessionalExperience", "Character", "Campaign",
    "Agency", "AgencyContact", "CareerFeedback",
    "AppearanceRecord", "StylePreference", "ContentPerformance",
    # Etapas 2, 3 e 5
    "DigitalTwinVersion", "IdentityTrait", "AppearanceState", "CharacterTransformation",
    "IdentityReference", "AssetOriginLog",
]
