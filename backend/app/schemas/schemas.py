from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

# ========== BASE RESPONSES ==========
class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None

class PaginatedResponse(BaseModel):
    success: bool = True
    data: List[Any] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]

# ========== AUTH ==========
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ========== TENANT ==========
class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    plan: str = "starter"

class TenantCreate(TenantBase):
    pass

class TenantResponse(TenantBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    settings: Dict = {}
    branding: Dict = {}
    created_at: datetime
    updated_at: datetime

# ========== USER ==========
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "user"
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    clerk_id: str
    tenant_id: UUID

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    created_at: datetime

# ========== PROFILE ==========
class ProfileBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    artistic_name: Optional[str] = Field(None, max_length=255)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, pattern=r"^(male|female|non_binary|other)$")
    height_cm: Optional[int] = Field(None, ge=100, le=250)
    weight_kg: Optional[Decimal] = Field(None, ge=30, le=300)
    eye_color: Optional[str] = None
    hair_color: Optional[str] = None
    skin_tone: Optional[str] = None
    body_type: Optional[str] = None
    shoe_size: Optional[str] = None
    dress_size: Optional[str] = None
    pants_size: Optional[str] = None
    shirt_size: Optional[str] = None
    languages: Optional[List[str]] = []
    skills: Optional[List[str]] = []
    experience_years: Optional[int] = Field(None, ge=0, le=80)
    bio: Optional[str] = Field(None, max_length=2000)
    instagram: Optional[str] = Field(None, max_length=100)
    portfolio_url: Optional[str] = None

class ProfileCreate(ProfileBase):
    code: Optional[str] = Field(None, max_length=50)

class ProfileUpdate(ProfileBase):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[str] = Field(None, pattern=r"^(active|inactive|archived)$")

class ProfileResponse(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    code: Optional[str]
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime
    age: Optional[int] = None
    photoshoot_count: int = 0
    latest_analysis: Optional[Dict] = None
    latest_report: Optional[Dict] = None

# ========== PHOTOSHOOT ==========
class PhotoshootBase(BaseModel):
    profile_id: UUID
    photographer_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(studio|location|composite|update)$")
    date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class PhotoshootCreate(PhotoshootBase):
    pass

class PhotoshootResponse(PhotoshootBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    status: str
    photo_count: int = 0
    analysis_status: str = "pending"
    created_at: datetime

# ========== PHOTO ==========
class PhotoBase(BaseModel):
    photoshoot_id: UUID
    profile_id: UUID
    angle: str = Field(..., pattern=r"^(front|left_profile|right_profile|left_45|right_45|smiling|neutral|full_body|half_body|seated|movement|video)$")
    format: str = Field(..., pattern=r"^(jpeg|jpg|png|raw|heic|webp)$")
    file_size_bytes: Optional[int] = None
    dimensions: Optional[str] = None
    color_space: Optional[str] = None

class PhotoUploadResponse(BaseModel):
    id: UUID
    url: str
    thumbnail_url: str
    upload_url: str
    expires_at: datetime

class PhotoResponse(PhotoBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    url: str
    thumbnail_url: Optional[str] = None
    metadata: Dict = {}
    analysis_status: str = "pending"
    created_at: datetime

# ========== ANALYSIS MODULES ==========
class FacialStructure(BaseModel):
    face_shape: str
    symmetry_score: float = Field(..., ge=0, le=1)
    golden_ratio_score: float = Field(..., ge=0, le=1)
    facial_thirds: Dict
    jaw_line: str
    cheekbones: str
    forehead: str
    chin: str
    nose: str
    lips: str
    eyes: str
    eyebrows: str
    landmarks: List[Dict]
    observations: str

class VisagismAnalysis(BaseModel):
    face_shape_category: str
    recommended_hairstyles: List[str]
    recommended_eyebrow_shapes: List[str]
    recommended_makeup_styles: List[str]
    contouring_tips: List[str]
    highlighting_tips: List[str]
    overall_recommendation: str
    confidence: float

class ExpressionMap(BaseModel):
    neutral: float
    happy: float
    sad: float
    angry: float
    surprised: float
    fearful: float
    disgusted: float
    dominant_expression: str
    expression_range: float
    recommendations: List[str]

class CastingSuggestion(BaseModel):
    character_types: List[str]
    age_range: str
    market_segments: List[str]
    media_types: List[str]
    archetypes: List[str]
    strong_suits: List[str]
    avoid: List[str]
    confidence: float
    disclaimer: str = "Estas sao hipoteses fundamentadas baseadas em analise de dados, nao verdades absolutas."

# ========== ANALYSIS ==========
class AnalysisCreate(BaseModel):
    analysis_types: List[str] = ["facial", "visagism", "expressions", "casting", "branding"]
    priority: str = "normal"
    notify_on_complete: bool = True

class AnalysisResult(BaseModel):
    id: UUID
    profile_id: UUID
    photoshoot_id: UUID
    status: str
    facial_structure: Optional[FacialStructure] = None
    visagism: Optional[VisagismAnalysis] = None
    photogenic: Optional[Dict] = None
    expressions: Optional[ExpressionMap] = None
    body_language: Optional[Dict] = None
    posture: Optional[Dict] = None
    colorimetry: Optional[Dict] = None
    grooming: Optional[Dict] = None
    styling: Optional[Dict] = None
    archetypes: Optional[Dict] = None
    market_potential: Optional[Dict] = None
    branding: Optional[Dict] = None
    casting: Optional[CastingSuggestion] = None
    confidence_score: float
    processing_time_ms: int
    model_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    photo_id: UUID
    profile_id: UUID
    photoshoot_id: UUID
    status: str
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    model_version: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# ========== WEBSOCKET MESSAGES ==========
class AnalysisProgress(BaseModel):
    type: str = "analysis_progress"
    analysis_id: str
    photoshoot_id: str
    progress: Dict
    timestamp: datetime

class AnalysisComplete(BaseModel):
    type: str = "analysis_complete"
    analysis_id: str
    data: Dict

# ========== REPORT ==========
class ReportSection(BaseModel):
    title: str
    content: str
    score: Optional[float] = None
    priority: Optional[str] = None
    recommendations: Optional[List[str]] = []

class ReportCreate(BaseModel):
    profile_id: UUID
    photoshoot_id: UUID
    title: str
    sections: Optional[List[str]] = None
    template: str = "premium"
    language: str = "pt-BR"

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    photoshoot_id: UUID
    title: str
    status: str
    version: int = 1
    executive_summary: Optional[str] = None
    technical_analysis: Optional[Dict] = None
    artistic_analysis: Optional[Dict] = None
    commercial_analysis: Optional[Dict] = None
    development_plan: Optional[Dict] = None
    priorities: Optional[List[Dict]] = None
    checklist: Optional[List[Dict]] = None
    evolution_timeline: Optional[Dict] = None
    indicators: Optional[Dict] = None
    confidence_index: Optional[float] = None
    pdf_url: Optional[str] = None
    previous_version_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

# ========== EVALUATION ==========
class EvaluationCreate(BaseModel):
    profile_id: UUID
    photoshoot_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    overall_score: Optional[float] = Field(None, ge=0, le=1)
    scores: Optional[Dict] = None
    observations: Optional[str] = None
    recommendations: Optional[str] = None

class EvaluationResponse(EvaluationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    evaluator_id: UUID
    created_at: datetime


# ========== VISION CORE v0.1 - NOVOS SCHEMAS ==========

# ========== CAREER MEMORY / TALENT GRAPH (ETAPA 1) ==========

class ProfessionalExperienceCreate(BaseModel):
    profile_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    project_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=255)
    character_name: Optional[str] = Field(None, max_length=255)
    production_type: Optional[str] = Field(None, max_length=100)
    director: Optional[str] = Field(None, max_length=255)
    agency: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    skills_used: Optional[List[str]] = []
    photos_used: Optional[List[str]] = []
    video_url: Optional[str] = None
    is_featured: bool = False
    metadata: Optional[Dict] = {}

class ProfessionalExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    title: str
    company: Optional[str] = None
    project_name: Optional[str] = None
    role: Optional[str] = None
    character_name: Optional[str] = None
    production_type: Optional[str] = None
    director: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    description: Optional[str] = None
    skills_used: List[str] = []
    photos_used: List[str] = []
    video_url: Optional[str] = None
    is_featured: str = "false"
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class CharacterCreate(BaseModel):
    profile_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    archetype: Optional[str] = Field(None, max_length=100)
    age_range: Optional[str] = Field(None, max_length=50)
    gender_presentation: Optional[str] = Field(None, max_length=50)
    physical_description: Optional[str] = None
    personality_traits: Optional[List[str]] = []
    wardrobe_description: Optional[str] = None
    makeup_description: Optional[str] = None
    hair_description: Optional[str] = None
    accessories: Optional[List[str]] = []
    era: Optional[str] = Field(None, max_length=100)
    profession: Optional[str] = Field(None, max_length=100)
    social_status: Optional[str] = Field(None, max_length=100)
    emotional_state: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = []
    videos: Optional[List[str]] = []
    experience_id: Optional[UUID] = None
    is_simulated: bool = False
    simulation_prompt: Optional[str] = None
    metadata: Optional[Dict] = {}

class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    name: str
    archetype: Optional[str] = None
    age_range: Optional[str] = None
    gender_presentation: Optional[str] = None
    physical_description: Optional[str] = None
    personality_traits: List[str] = []
    wardrobe_description: Optional[str] = None
    makeup_description: Optional[str] = None
    hair_description: Optional[str] = None
    accessories: List[str] = []
    era: Optional[str] = None
    profession: Optional[str] = None
    social_status: Optional[str] = None
    emotional_state: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    experience_id: Optional[UUID] = None
    is_simulated: str = "false"
    simulation_prompt: Optional[str] = None
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class CampaignCreate(BaseModel):
    profile_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    agency: Optional[str] = Field(None, max_length=255)
    campaign_type: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    deliverables: Optional[List[str]] = []
    photos_used: Optional[List[str]] = []
    videos_used: Optional[List[str]] = []
    results: Optional[Dict] = {}
    metadata: Optional[Dict] = {}

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    name: str
    brand: Optional[str] = None
    agency: Optional[str] = None
    campaign_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    deliverables: List[str] = []
    photos_used: List[str] = []
    videos_used: List[str] = []
    results: Dict = {}
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class CareerFeedbackCreate(BaseModel):
    profile_id: UUID
    source: str = Field(..., max_length=100)
    source_name: str = Field(..., max_length=255)
    feedback_type: str = Field(..., max_length=100)
    feedback_text: str
    rating: Optional[float] = Field(None, ge=0, le=5)
    related_experience_id: Optional[UUID] = None
    related_casting_id: Optional[UUID] = None
    related_content_id: Optional[UUID] = None
    is_positive: bool = True
    action_taken: Optional[str] = None
    metadata: Optional[Dict] = {}

class CareerFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    source: str
    source_name: str
    feedback_type: str
    feedback_text: str
    rating: Optional[float] = None
    related_experience_id: Optional[UUID] = None
    related_casting_id: Optional[UUID] = None
    related_content_id: Optional[UUID] = None
    is_positive: str = "true"
    action_taken: Optional[str] = None
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class AppearanceRecordCreate(BaseModel):
    profile_id: UUID
    record_type: str = Field(..., pattern=r"^(approved|rejected|simulated|real)$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    photos: Optional[List[str]] = []
    related_character_id: Optional[UUID] = None
    related_experience_id: Optional[UUID] = None
    related_casting_id: Optional[UUID] = None
    feedback: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    tags: Optional[List[str]] = []
    metadata: Optional[Dict] = {}

class AppearanceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    record_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    photos: List[str] = []
    related_character_id: Optional[UUID] = None
    related_experience_id: Optional[UUID] = None
    related_casting_id: Optional[UUID] = None
    feedback: Optional[str] = None
    rating: Optional[float] = None
    tags: List[str] = []
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class StylePreferenceCreate(BaseModel):
    profile_id: UUID
    preference_type: str = Field(..., max_length=100)
    preference_value: str
    context: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict] = {}

class StylePreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    preference_type: str
    preference_value: str
    context: Optional[str] = None
    is_active: str = "true"
    usage_count: int = 0
    success_rate: Optional[float] = None
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

class ContentPerformanceCreate(BaseModel):
    profile_id: UUID
    content_item_id: Optional[UUID] = None
    platform: str = Field(default="instagram", max_length=50)
    metrics: Optional[Dict] = {}
    engagement_rate: Optional[float] = Field(None, ge=0, le=1)
    best_performing: bool = False
    audience_demographics: Optional[Dict] = {}
    peak_hours: Optional[List[str]] = []
    metadata: Optional[Dict] = {}

class ContentPerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    content_item_id: Optional[UUID] = None
    platform: str
    metrics: Dict = {}
    engagement_rate: Optional[float] = None
    best_performing: str = "false"
    audience_demographics: Dict = {}
    peak_hours: List[str] = []
    status: str
    metadata: Dict = {}
    created_at: datetime
    updated_at: datetime

# Commands
class CommandRequest(BaseModel):
    input_type: str = Field(default="text", pattern=r"^(text|voice)$")
    text: str = Field(..., min_length=1, max_length=5000)
    metadata: Optional[Dict[str, Any]] = {}

class CommandResponse(BaseModel):
    command_id: str
    success: bool
    intent: str
    agent: Optional[str] = None
    result: Optional[Dict] = None
    requires_approval: bool = False
    correlation_id: str

# Approvals
class ApprovalResponse(BaseModel):
    id: UUID
    content_item_id: UUID
    approval_type: str
    status: str
    requested_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

class ApprovalActionRequest(BaseModel):
    notes: Optional[str] = None

# AI Tasks
class AITaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    user_id: UUID
    task_type: str
    status: str
    agent_name: Optional[str] = None
    engine_name: Optional[str] = None
    provider_name: Optional[str] = None
    processing_time_ms: Optional[int] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# Digital Twin
class DigitalTwinAssetCreate(BaseModel):
    profile_id: UUID
    media_type: str = Field(..., pattern=r"^(photo|video|scan)$")
    file_url: str
    angle: Optional[str] = None
    pose: Optional[str] = None
    expression: Optional[str] = None
    tags: Optional[List[str]] = []
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    metadata: Optional[Dict] = {}

class DigitalTwinAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    media_type: str
    file_url: str
    angle: Optional[str] = None
    pose: Optional[str] = None
    expression: Optional[str] = None
    tags: List[str] = []
    quality_score: Optional[float] = None
    status: str
    created_at: datetime

# Casting
class CastingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    production: Optional[str] = None
    role: Optional[str] = None
    age_range: Optional[str] = None
    gender_presentation: Optional[str] = None
    physical_requirements: Optional[Dict] = {}
    skills_required: Optional[List[str]] = []
    location: Optional[str] = None
    payment: Optional[str] = None
    deadline: Optional[datetime] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    requirements: Optional[Dict] = {}

class CastingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    title: str
    description: Optional[str] = None
    production: Optional[str] = None
    role: Optional[str] = None
    age_range: Optional[str] = None
    status: str
    created_at: datetime

# Content
class ContentItemCreate(BaseModel):
    profile_id: UUID
    content_type: str = Field(..., pattern=r"^(PHOTO|CAROUSEL|REEL|STORY|PORTFOLIO_UPDATE)$")
    title: Optional[str] = None
    description: Optional[str] = None
    caption: Optional[str] = None
    media_urls: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    platform: str = "instagram"

class ContentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    content_type: str
    title: Optional[str] = None
    caption: Optional[str] = None
    status: str
    platform: str
    created_at: datetime

# Vision Core Health
class VisionCoreHealth(BaseModel):
    status: str
    total_commands_processed: int
    agents: Dict[str, Any]
    intent_recognizer: str

class EventBusStats(BaseModel):
    total_events_emitted: int
    registered_event_types: int
    total_handlers: int
    global_handlers: int
    event_type_counts: Dict[str, int]
