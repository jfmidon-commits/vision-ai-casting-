import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Date, DateTime, Text, ForeignKey, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="starter")
    settings = Column(JSONB, default=dict)
    branding = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    users = relationship("User", back_populates="tenant")
    profiles = relationship("Profile", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id = Column(String(255), unique=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    role = Column(String(50), default="user")
    avatar_url = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    tenant = relationship("Tenant", back_populates="users")
    evaluations = relationship("Evaluation", back_populates="evaluator")

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    code = Column(String(50), unique=True)
    full_name = Column(String(255), nullable=False)
    artistic_name = Column(String(255))
    birth_date = Column(Date)
    gender = Column(String(50))
    height_cm = Column(Integer)
    weight_kg = Column(Numeric(5, 2))
    eye_color = Column(String(50))
    hair_color = Column(String(50))
    skin_tone = Column(String(50))
    body_type = Column(String(50))
    shoe_size = Column(String(20))
    dress_size = Column(String(20))
    pants_size = Column(String(20))
    shirt_size = Column(String(20))
    languages = Column(ARRAY(String))
    skills = Column(ARRAY(String))
    experience_years = Column(Integer)
    bio = Column(Text)
    instagram = Column(String(100))
    portfolio_url = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    tenant = relationship("Tenant", back_populates="profiles")
    photoshoots = relationship("Photoshoot", back_populates="profile")
    analyses = relationship("Analysis", back_populates="profile")
    reports = relationship("Report", back_populates="profile")

class Photoshoot(Base):
    __tablename__ = "photoshoots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    photographer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255))
    type = Column(String(50))
    date = Column(Date)
    location = Column(String(255))
    notes = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    profile = relationship("Profile", back_populates="photoshoots")
    photos = relationship("Photo", back_populates="photoshoot")
    analyses = relationship("Analysis", back_populates="photoshoot")
    reports = relationship("Report", back_populates="photoshoot")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    photoshoot_id = Column(UUID(as_uuid=True), ForeignKey("photoshoots.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    angle = Column(String(50))
    format = Column(String(20))
    file_size_bytes = Column(Integer)
    dimensions = Column(String(50))
    color_space = Column(String(50))
    _metadata = Column(JSONB, default=dict)
    analysis_status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    photoshoot = relationship("Photoshoot", back_populates="photos")
    profile = relationship("Profile")
    analyses = relationship("Analysis", back_populates="photo")

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    photoshoot_id = Column(UUID(as_uuid=True), ForeignKey("photoshoots.id"), nullable=False)
    status = Column(String(50), default="pending")
    facial_structure = Column(JSONB)
    visagism = Column(JSONB)
    photogenic = Column(JSONB)
    expressions = Column(JSONB)
    body_language = Column(JSONB)
    posture = Column(JSONB)
    colorimetry = Column(JSONB)
    grooming = Column(JSONB)
    styling = Column(JSONB)
    archetypes = Column(JSONB)
    market_potential = Column(JSONB)
    branding = Column(JSONB)
    casting = Column(JSONB)
    confidence_score = Column(Numeric(3, 2))
    raw_results = Column(JSONB)
    processing_time_ms = Column(Integer)
    model_version = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    photo = relationship("Photo", back_populates="analyses")
    profile = relationship("Profile", back_populates="analyses")
    photoshoot = relationship("Photoshoot", back_populates="analyses")

class Report(Base):
    __tablename__ = "reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    photoshoot_id = Column(UUID(as_uuid=True), ForeignKey("photoshoots.id"), nullable=False)
    title = Column(String(255))
    status = Column(String(50), default="draft")
    executive_summary = Column(Text)
    technical_analysis = Column(JSONB)
    artistic_analysis = Column(JSONB)
    commercial_analysis = Column(JSONB)
    development_plan = Column(JSONB)
    priorities = Column(JSONB)
    checklist = Column(JSONB)
    evolution_timeline = Column(JSONB)
    indicators = Column(JSONB)
    confidence_index = Column(Numeric(3, 2))
    pdf_url = Column(Text)
    version = Column(Integer, default=1)
    previous_version_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    profile = relationship("Profile", back_populates="reports")
    photoshoot = relationship("Photoshoot", back_populates="reports")

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    photoshoot_id = Column(UUID(as_uuid=True), ForeignKey("photoshoots.id"))
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"))
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    overall_score = Column(Numeric(3, 2))
    scores = Column(JSONB)
    observations = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    evaluator = relationship("User", back_populates="evaluations")


# ========== VISION CORE v0.1 - NOVOS MODELOS ==========

class DigitalTwinAsset(Base):
    __tablename__ = "digital_twin_assets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    media_type = Column(String(50), nullable=False)  # photo, video, scan
    file_url = Column(Text, nullable=False)
    angle = Column(String(50))  # front, left_profile, right_profile, 360
    pose = Column(String(50))
    expression = Column(String(50))
    capture_date = Column(DateTime(timezone=True))
    tags = Column(ARRAY(String))
    quality_score = Column(Numeric(3, 2))
    _metadata = Column(JSONB, default=dict)
    embedding = Column(JSONB)  # Futuro: vetor de embedding
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Casting(Base):
    __tablename__ = "castings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    production = Column(String(255))
    role = Column(String(255))
    age_range = Column(String(50))
    gender_presentation = Column(String(50))
    physical_requirements = Column(JSONB, default=dict)
    skills_required = Column(ARRAY(String))
    location = Column(String(255))
    shooting_dates = Column(ARRAY(DateTime))
    payment = Column(String(255))
    deadline = Column(DateTime(timezone=True))
    source = Column(String(100))
    source_url = Column(Text)
    status = Column(String(50), default="open")  # open, closed, filled, cancelled
    requirements = Column(JSONB, default=dict)
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CastingMatch(Base):
    __tablename__ = "casting_matches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    casting_id = Column(UUID(as_uuid=True), ForeignKey("castings.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    compatibility_score = Column(Numeric(3, 2))
    matching_attributes = Column(JSONB, default=dict)
    missing_attributes = Column(JSONB, default=dict)
    recommendation = Column(Text)
    status = Column(String(50), default="pending")  # pending, recommended, applied, rejected
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentItem(Base):
    __tablename__ = "content_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    content_type = Column(String(50), nullable=False)  # PHOTO, CAROUSEL, REEL, STORY, PORTFOLIO_UPDATE
    title = Column(String(255))
    description = Column(Text)
    caption = Column(Text)
    media_urls = Column(ARRAY(Text))
    hashtags = Column(ARRAY(String))
    status = Column(String(50), default="draft")  # draft, generated, waiting_approval, approved, published, rejected
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    platform = Column(String(50), default="instagram")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentApproval(Base):
    __tablename__ = "content_approvals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=False)
    approval_type = Column(String(50), nullable=False)  # CONTENT, CASTING_APPLICATION, PROFILE_CHANGE, EXTERNAL_ACTION
    status = Column(String(50), default="pending")  # pending, approved, rejected, revision_requested
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    responded_at = Column(DateTime(timezone=True))
    response_notes = Column(Text)
    revision_notes = Column(Text)
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AITask(Base):
    __tablename__ = "ai_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_type = Column(String(100), nullable=False)
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    status = Column(String(50), default="pending")  # pending, processing, waiting_approval, completed, failed, cancelled
    agent_name = Column(String(100))
    engine_name = Column(String(100))
    provider_name = Column(String(100))
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    correlation_id = Column(String(100))
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    agent_name = Column(String(100))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100))
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    severity = Column(String(20), default="info")  # info, warning, error, critical
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class UserMemory(Base):
    """Memorias persistentes de usuarios no Vision Ecosystem."""
    __tablename__ = "user_memories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    memory_key = Column(String(255), nullable=False)
    category = Column(String(100), default="general")
    value = Column(JSONB, default=dict)
    access_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))
    last_accessed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Constraint unica: um usuario nao pode ter duas memorias com a mesma chave
        {'schema': 'public'},
    )


class UserFeedback(Base):
    """Feedbacks de usuarios sobre itens do sistema."""
    __tablename__ = "user_feedbacks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    item_type = Column(String(100), nullable=False)  # analysis, report, casting, etc.
    item_id = Column(String(255), nullable=False)
    feedback_text = Column(Text)
    rating = Column(Integer)  # 1-5
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class VoiceCommand(Base):
    __tablename__ = "voice_commands"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    audio_url = Column(Text)
    transcription = Column(Text)
    recognized_intent = Column(String(100))
    confidence_score = Column(Numeric(3, 2))
    status = Column(String(50), default="received")  # received, transcribed, processed, failed
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at = Column(DateTime(timezone=True))


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    workflow_type = Column(String(100), nullable=False)
    steps = Column(JSONB, default=list)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="running")  # running, completed, failed, cancelled
    current_step = Column(Integer, default=0)
    step_results = Column(JSONB, default=list)
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(100), nullable=False)
    title = Column(String(255))
    message = Column(Text)
    data = Column(JSONB, default=dict)
    read = Column(String(50), default="unread")
    read_at = Column(DateTime(timezone=True))
    sent_via = Column(String(50))  # whatsapp, email, push, in_app
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_at = Column(DateTime(timezone=True))


# ========== ETAPA 1: CAREER MEMORY / TALENT GRAPH ==========

class ProfessionalExperience(Base):
    __tablename__ = "professional_experiences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255))
    project_name = Column(String(255))
    role = Column(String(255))
    character_name = Column(String(255))
    production_type = Column(String(100))  # film, series, commercial, theater, etc.
    director = Column(String(255))
    agency = Column(String(255))
    start_date = Column(Date)
    end_date = Column(Date)
    location = Column(String(255))
    description = Column(Text)
    skills_used = Column(ARRAY(String))
    photos_used = Column(ARRAY(Text))  # URLs das fotos utilizadas
    video_url = Column(Text)
    is_featured = Column(String(50), default="false")
    status = Column(String(50), default="completed")  # completed, ongoing, upcoming
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Character(Base):
    __tablename__ = "characters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    name = Column(String(255), nullable=False)
    archetype = Column(String(100))
    age_range = Column(String(50))
    gender_presentation = Column(String(50))
    physical_description = Column(Text)
    personality_traits = Column(ARRAY(String))
    wardrobe_description = Column(Text)
    makeup_description = Column(Text)
    hair_description = Column(Text)
    accessories = Column(ARRAY(String))
    era = Column(String(100))
    profession = Column(String(100))
    social_status = Column(String(100))
    emotional_state = Column(String(100))
    photos = Column(ARRAY(Text))
    videos = Column(ARRAY(Text))
    experience_id = Column(UUID(as_uuid=True), ForeignKey("professional_experiences.id"))
    is_simulated = Column(String(50), default="false")
    simulation_prompt = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    agency = Column(String(255))
    campaign_type = Column(String(100))  # commercial, editorial, digital, etc.
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)
    deliverables = Column(ARRAY(String))
    photos_used = Column(ARRAY(Text))
    videos_used = Column(ARRAY(Text))
    results = Column(JSONB, default=dict)  # reach, engagement, etc.
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Agency(Base):
    __tablename__ = "agencies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100))  # casting, modeling, talent, etc.
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(Text)
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    specialties = Column(ARRAY(String))
    notes = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class AgencyContact(Base):
    __tablename__ = "agency_contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agency_id = Column(UUID(as_uuid=True), ForeignKey("agencies.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    contact_type = Column(String(100))  # agent, manager, scout, etc.
    start_date = Column(Date)
    end_date = Column(Date)
    contract_type = Column(String(100))  # exclusive, non_exclusive, etc.
    commission_rate = Column(Numeric(5, 2))
    notes = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class CareerFeedback(Base):
    __tablename__ = "career_feedbacks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    source = Column(String(100))  # director, photographer, agency, client, self
    source_name = Column(String(255))
    source_id = Column(UUID(as_uuid=True))  # pode referenciar user, agency, etc.
    feedback_type = Column(String(100))  # appearance, performance, professionalism, etc.
    feedback_text = Column(Text)
    rating = Column(Numeric(3, 2))
    related_experience_id = Column(UUID(as_uuid=True), ForeignKey("professional_experiences.id"))
    related_casting_id = Column(UUID(as_uuid=True), ForeignKey("castings.id"))
    related_content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"))
    is_positive = Column(String(50), default="true")
    action_taken = Column(Text)
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class AppearanceRecord(Base):
    __tablename__ = "appearance_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    record_type = Column(String(100), nullable=False)  # approved, rejected, simulated, real
    title = Column(String(255))
    description = Column(Text)
    photos = Column(ARRAY(Text))
    related_character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"))
    related_experience_id = Column(UUID(as_uuid=True), ForeignKey("professional_experiences.id"))
    related_casting_id = Column(UUID(as_uuid=True), ForeignKey("castings.id"))
    feedback = Column(Text)
    rating = Column(Numeric(3, 2))
    tags = Column(ARRAY(String))
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class StylePreference(Base):
    __tablename__ = "style_preferences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    preference_type = Column(String(100), nullable=False)  # caption_style, photo_style, color_palette, etc.
    preference_value = Column(Text, nullable=False)
    context = Column(String(255))  # quando/quando aplicar
    is_active = Column(String(50), default="true")
    usage_count = Column(Integer, default=0)
    success_rate = Column(Numeric(5, 2))
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class ContentPerformance(Base):
    __tablename__ = "content_performances"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"))
    platform = Column(String(50), default="instagram")
    metrics = Column(JSONB, default=dict)  # likes, comments, shares, saves, reach, impressions
    engagement_rate = Column(Numeric(5, 4))
    best_performing = Column(String(50), default="false")
    audience_demographics = Column(JSONB, default=dict)
    peak_hours = Column(ARRAY(String))
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ========== ETAPA 2: DIGITAL TWIN VERSIONING ==========

class DigitalTwinVersion(Base):
    """Versionamento do Gemeo Digital. Cada atualizacao importante gera uma nova versao."""
    __tablename__ = "digital_twin_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    version_name = Column(String(255))  # e.g., "Summer 2026", "Post-Cut"
    description = Column(Text)
    created_reason = Column(String(100))  # new_photoshoot, appearance_change, user_request, character_simulation
    status = Column(String(50), default="active")  # active, archived, deprecated
    assets_summary = Column(JSONB, default=dict)  # resumo dos assets por categoria
    identity_traits_snapshot = Column(JSONB, default=dict)  # snapshot de IdentityTraits
    appearance_state_snapshot = Column(JSONB, default=dict)  # snapshot de AppearanceState
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ========== ETAPA 3: IDENTITY / APPEARANCE / CHARACTER SEPARATION ==========

class IdentityTrait(Base):
    """Caracteristicas relativamente permanentes do talento."""
    __tablename__ = "identity_traits"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    trait_category = Column(String(100), nullable=False)  # facial_structure, eye_characteristics, physical_identifiers, proportions
    trait_name = Column(String(100), nullable=False)  # face_shape, eye_color, height_cm, etc.
    trait_value = Column(Text, nullable=False)  # oval, brown, 175, etc.
    confidence = Column(Numeric(3, 2), default=1.0)  # 0.0 - 1.0
    source = Column(String(100), default="analysis")  # analysis, user_input, measurement, verified
    verified_by = Column(String(255))  # quem verificou
    verified_at = Column(DateTime(timezone=True))
    is_permanent = Column(String(50), default="true")  # true = nao muda, false = raramente muda
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AppearanceState(Base):
    """Caracteristicas modificaveis do talento - estado atual da aparencia."""
    __tablename__ = "appearance_states"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_versions.id"))  # vinculado a uma versao
    category = Column(String(100), nullable=False)  # hair, facial_hair, body, makeup, grooming, accessories
    attribute = Column(String(100), nullable=False)  # length, color, style, weight_kg, tan, etc.
    current_value = Column(Text, nullable=False)
    previous_value = Column(Text)  # para tracking de mudancas
    changed_at = Column(DateTime(timezone=True))  # quando mudou
    changed_reason = Column(String(255))  # photoshoot, user_update, casting_requirement, etc.
    photos = Column(ARRAY(Text))  # fotos que comprovam este estado
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CharacterTransformation(Base):
    """Caracteristicas pertencentes apenas a simulacao de personagem."""
    __tablename__ = "character_transformations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.id"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_versions.id"))
    transformation_type = Column(String(100), nullable=False)  # wardrobe, simulated_appearance, context, environment
    attribute = Column(String(100), nullable=False)  # suit_type, simulated_beard, era, lighting, etc.
    value = Column(Text, nullable=False)
    is_simulated = Column(String(50), default="true")  # sempre true - este e o ponto
    simulation_prompt_fragment = Column(Text)  # fragmento do prompt que gerou esta transformacao
    generated_asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_assets.id"))
    status = Column(String(50), default="active")
    _metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ========== ETAPA 5: IDENTITY PRESERVATION ==========

class IdentityReference(Base):
    """Referencias necessarias para preservar identidade em geracoes futuras."""
    __tablename__ = "identity_references"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_assets.id"))
    reference_type = Column(String(100), nullable=False)  # face_frontal, face_profile, body_full, expression_set, etc.
    origin = Column(String(100), nullable=False)  # REAL, CURRENT_APPEARANCE, SIMULATED, AI_GENERATED
    file_url = Column(Text, nullable=False)
    quality_score = Column(Numeric(3, 2))
    embedding = Column(JSONB)  # vetor de embedding facial (futuro)
    landmarks = Column(JSONB)  # landmarks faciais (futuro)
    extra_metadata = Column(JSONB, default=dict)  # angle, pose, lighting, capture_date, source, tags
    is_primary = Column(String(50), default="false")  # referencia primaria para preservacao
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AssetOriginLog(Base):
    """Log de auditoria para rastrear a origem de todos os assets."""
    __tablename__ = "asset_origin_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_assets.id"))
    asset_type = Column(String(100), nullable=False)  # photo, video, scan, generated_image
    origin = Column(String(100), nullable=False)  # REAL, CURRENT_APPEARANCE, SIMULATED, AI_GENERATED
    source_description = Column(Text)  # descricao detalhada da origem
    generated_by = Column(String(100))  # nome do agente/servico que gerou
    generation_prompt = Column(Text)  # prompt usado (se aplicavel)
    parent_asset_id = Column(UUID(as_uuid=True), ForeignKey("digital_twin_assets.id"))  # asset pai (se derivado)
    is_saved_as_real = Column(String(50), default="false")  # flag de protecao: impedir confusao
    warning_flags = Column(ARRAY(String), default=list)  # flags de alerta
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
