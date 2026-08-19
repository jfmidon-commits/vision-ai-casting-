from .models import (
    Tenant, User, Profile, Photoshoot, Photo, Analysis, Report, Evaluation,
    # Vision Core v0.1
    DigitalTwinAsset, Casting, CastingMatch, ContentItem, ContentApproval,
    AITask, AuditLog, VoiceCommand, Workflow, WorkflowRun, Notification,
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

__all__ = [
    "Tenant", "User", "Profile", "Photoshoot", "Photo", "Analysis", "Report", "Evaluation",
    "DigitalTwinAsset", "Casting", "CastingMatch", "ContentItem", "ContentApproval",
    "AITask", "AuditLog", "VoiceCommand", "Workflow", "WorkflowRun", "Notification",
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
