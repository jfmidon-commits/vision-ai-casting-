"""
Tests for CareerMemoryService — Talent Graph / Career Memory.

Covers:
- CRUD operations for all entities
- searchMemory() — textual search across all entities
- getTalentContext() — full talent context generation
- getRelevantHistory() — context-aware history filtering
"""

import pytest
from datetime import datetime, date
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock

from app.memory.career_memory_service import CareerMemoryService
from app.models import (
    ProfessionalExperience, Character, Campaign,
    Agency, AgencyContact, CareerFeedback,
    AppearanceRecord, StylePreference, ContentPerformance,
    Profile
)


@pytest.fixture
def career_service():
    return CareerMemoryService()


@pytest.fixture
def sample_tenant_id():
    return uuid4()


@pytest.fixture
def sample_profile_id():
    return uuid4()


# ========== MOCK HELPERS ==========

def create_mock_experience(**kwargs):
    """Create a mock ProfessionalExperience."""
    mock = MagicMock(spec=ProfessionalExperience)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.title = kwargs.get("title", "Test Experience")
    mock.company = kwargs.get("company", "Test Company")
    mock.project_name = kwargs.get("project_name", "Test Project")
    mock.role = kwargs.get("role", "Lead")
    mock.character_name = kwargs.get("character_name", None)
    mock.production_type = kwargs.get("production_type", "film")
    mock.director = kwargs.get("director", "Test Director")
    mock.agency = kwargs.get("agency", "Test Agency")
    mock.start_date = kwargs.get("start_date", date(2023, 1, 1))
    mock.end_date = kwargs.get("end_date", date(2023, 6, 1))
    mock.location = kwargs.get("location", "Sao Paulo")
    mock.description = kwargs.get("description", "A test experience")
    mock.skills_used = kwargs.get("skills_used", ["acting", "modeling"])
    mock.photos_used = kwargs.get("photos_used", [])
    mock.video_url = kwargs.get("video_url", None)
    mock.is_featured = kwargs.get("is_featured", "false")
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_character(**kwargs):
    """Create a mock Character."""
    mock = MagicMock(spec=Character)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.name = kwargs.get("name", "Test Character")
    mock.archetype = kwargs.get("archetype", "hero")
    mock.age_range = kwargs.get("age_range", "25-35")
    mock.gender_presentation = kwargs.get("gender_presentation", "masculine")
    mock.physical_description = kwargs.get("physical_description", "Tall, athletic")
    mock.personality_traits = kwargs.get("personality_traits", ["brave", "determined"])
    mock.wardrobe_description = kwargs.get("wardrobe_description", None)
    mock.makeup_description = kwargs.get("makeup_description", None)
    mock.hair_description = kwargs.get("hair_description", None)
    mock.accessories = kwargs.get("accessories", [])
    mock.era = kwargs.get("era", None)
    mock.profession = kwargs.get("profession", "detective")
    mock.social_status = kwargs.get("social_status", None)
    mock.emotional_state = kwargs.get("emotional_state", None)
    mock.photos = kwargs.get("photos", [])
    mock.videos = kwargs.get("videos", [])
    mock.experience_id = kwargs.get("experience_id", None)
    mock.is_simulated = kwargs.get("is_simulated", "false")
    mock.simulation_prompt = kwargs.get("simulation_prompt", None)
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_campaign(**kwargs):
    """Create a mock Campaign."""
    mock = MagicMock(spec=Campaign)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.name = kwargs.get("name", "Test Campaign")
    mock.brand = kwargs.get("brand", "Nike")
    mock.agency = kwargs.get("agency", "WPP")
    mock.campaign_type = kwargs.get("campaign_type", "commercial")
    mock.start_date = kwargs.get("start_date", date(2023, 3, 1))
    mock.end_date = kwargs.get("end_date", date(2023, 4, 1))
    mock.description = kwargs.get("description", "A test campaign")
    mock.deliverables = kwargs.get("deliverables", ["photo", "video"])
    mock.photos_used = kwargs.get("photos_used", [])
    mock.videos_used = kwargs.get("videos_used", [])
    mock.results = kwargs.get("results", {"reach": 10000})
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_feedback(**kwargs):
    """Create a mock CareerFeedback."""
    mock = MagicMock(spec=CareerFeedback)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.source = kwargs.get("source", "director")
    mock.source_name = kwargs.get("source_name", "John Doe")
    mock.feedback_type = kwargs.get("feedback_type", "performance")
    mock.feedback_text = kwargs.get("feedback_text", "Excellent performance")
    mock.rating = kwargs.get("rating", 4.5)
    mock.related_experience_id = kwargs.get("related_experience_id", None)
    mock.related_casting_id = kwargs.get("related_casting_id", None)
    mock.related_content_id = kwargs.get("related_content_id", None)
    mock.is_positive = kwargs.get("is_positive", "true")
    mock.action_taken = kwargs.get("action_taken", None)
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_appearance(**kwargs):
    """Create a mock AppearanceRecord."""
    mock = MagicMock(spec=AppearanceRecord)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.record_type = kwargs.get("record_type", "approved")
    mock.title = kwargs.get("title", "Test Appearance")
    mock.description = kwargs.get("description", "A test appearance")
    mock.photos = kwargs.get("photos", [])
    mock.related_character_id = kwargs.get("related_character_id", None)
    mock.related_experience_id = kwargs.get("related_experience_id", None)
    mock.related_casting_id = kwargs.get("related_casting_id", None)
    mock.feedback = kwargs.get("feedback", "Great look")
    mock.rating = kwargs.get("rating", 4.0)
    mock.tags = kwargs.get("tags", ["casual", "urban"])
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_style_preference(**kwargs):
    """Create a mock StylePreference."""
    mock = MagicMock(spec=StylePreference)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.preference_type = kwargs.get("preference_type", "caption_style")
    mock.preference_value = kwargs.get("preference_value", "professional")
    mock.context = kwargs.get("context", "Instagram posts")
    mock.is_active = kwargs.get("is_active", "true")
    mock.usage_count = kwargs.get("usage_count", 10)
    mock.success_rate = kwargs.get("success_rate", 0.85)
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_content_performance(**kwargs):
    """Create a mock ContentPerformance."""
    mock = MagicMock(spec=ContentPerformance)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.profile_id = kwargs.get("profile_id", uuid4())
    mock.content_item_id = kwargs.get("content_item_id", None)
    mock.platform = kwargs.get("platform", "instagram")
    mock.metrics = kwargs.get("metrics", {"likes": 1000, "comments": 50})
    mock.engagement_rate = kwargs.get("engagement_rate", 0.05)
    mock.best_performing = kwargs.get("best_performing", "false")
    mock.audience_demographics = kwargs.get("audience_demographics", {})
    mock.peak_hours = kwargs.get("peak_hours", ["18:00", "20:00"])
    mock.status = kwargs.get("status", "active")
    mock.metadata = kwargs.get("metadata", {})
    mock.created_at = datetime.utcnow()
    mock.updated_at = datetime.utcnow()
    return mock


def create_mock_profile(**kwargs):
    """Create a mock Profile."""
    mock = MagicMock(spec=Profile)
    mock.id = kwargs.get("id", uuid4())
    mock.tenant_id = kwargs.get("tenant_id", uuid4())
    mock.full_name = kwargs.get("full_name", "John Talent")
    mock.artistic_name = kwargs.get("artistic_name", "John T")
    mock.gender = kwargs.get("gender", "male")
    mock.height_cm = kwargs.get("height_cm", 180)
    mock.weight_kg = kwargs.get("weight_kg", 75.0)
    mock.eye_color = kwargs.get("eye_color", "brown")
    mock.hair_color = kwargs.get("hair_color", "black")
    mock.skin_tone = kwargs.get("skin_tone", "medium")
    mock.body_type = kwargs.get("body_type", "athletic")
    mock.languages = kwargs.get("languages", ["pt-BR", "en"])
    mock.skills = kwargs.get("skills", ["acting", "modeling"])
    mock.experience_years = kwargs.get("experience_years", 5)
    mock.bio = kwargs.get("bio", "A talented actor")
    mock.instagram = kwargs.get("instagram", "@johntalent")
    mock.portfolio_url = kwargs.get("portfolio_url", None)
    return mock


# ========== TESTS: searchMemory ==========

@pytest.mark.asyncio
async def test_search_memory_experiences(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory finds experiences."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_experience = create_mock_experience(
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        title="Action Movie",
        production_type="film"
    )
    mock_result.scalars.return_value.all.return_value = [mock_experience]
    mock_db.execute.return_value = mock_result

    with patch("app.memory.career_memory_service.emit_event", new_callable=AsyncMock):
        results = await career_service.searchMemory(
            db=mock_db,
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            query="action",
            entity_types=["experiences"],
            limit=10
        )

    assert results["query"] == "action"
    assert results["total_results"] == 1
    assert "experiences" in results["results"]
    assert results["results"]["experiences"][0]["title"] == "Action Movie"


@pytest.mark.asyncio
async def test_search_memory_characters(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory finds characters."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_character = create_mock_character(
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        name="The Detective",
        archetype="hero"
    )
    mock_result.scalars.return_value.all.return_value = [mock_character]
    mock_db.execute.return_value = mock_result

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="detective",
        entity_types=["characters"],
        limit=10
    )

    assert results["total_results"] == 1
    assert "characters" in results["results"]
    assert results["results"]["characters"][0]["name"] == "The Detective"


@pytest.mark.asyncio
async def test_search_memory_campaigns(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory finds campaigns."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_campaign = create_mock_campaign(
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        name="Summer Collection",
        brand="Nike"
    )
    mock_result.scalars.return_value.all.return_value = [mock_campaign]
    mock_db.execute.return_value = mock_result

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="summer",
        entity_types=["campaigns"],
        limit=10
    )

    assert results["total_results"] == 1
    assert "campaigns" in results["results"]
    assert results["results"]["campaigns"][0]["name"] == "Summer Collection"


@pytest.mark.asyncio
async def test_search_memory_feedbacks(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory finds feedbacks."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_feedback = create_mock_feedback(
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        feedback_text="Amazing performance in the drama scene"
    )
    mock_result.scalars.return_value.all.return_value = [mock_feedback]
    mock_db.execute.return_value = mock_result

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="drama",
        entity_types=["feedbacks"],
        limit=10
    )

    assert results["total_results"] == 1
    assert "feedbacks" in results["results"]
    assert "drama" in results["results"]["feedbacks"][0]["feedback_text"]


@pytest.mark.asyncio
async def test_search_memory_appearances(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory finds appearances."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_appearance = create_mock_appearance(
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        title="Fashion Week Appearance"
    )
    mock_result.scalars.return_value.all.return_value = [mock_appearance]
    mock_db.execute.return_value = mock_result

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="fashion",
        entity_types=["appearances"],
        limit=10
    )

    assert results["total_results"] == 1
    assert "appearances" in results["results"]
    assert "Fashion" in results["results"]["appearances"][0]["title"]


@pytest.mark.asyncio
async def test_search_memory_no_results(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory returns empty when no matches."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="xyznonexistent",
        limit=10
    )

    assert results["total_results"] == 0
    assert results["results"] == {}


@pytest.mark.asyncio
async def test_search_memory_multiple_entity_types(career_service, sample_profile_id, sample_tenant_id):
    """Test searchMemory searches multiple entity types."""
    mock_db = AsyncMock()
    
    # First call (experiences)
    mock_exp_result = MagicMock()
    mock_exp_result.scalars.return_value.all.return_value = [
        create_mock_experience(profile_id=sample_profile_id, tenant_id=sample_tenant_id, title="Test")
    ]
    
    # Second call (characters) 
    mock_char_result = MagicMock()
    mock_char_result.scalars.return_value.all.return_value = [
        create_mock_character(profile_id=sample_profile_id, tenant_id=sample_tenant_id, name="Test")
    ]
    
    # Third call (campaigns)
    mock_camp_result = MagicMock()
    mock_camp_result.scalars.return_value.all.return_value = []
    
    # Fourth call (feedbacks)
    mock_fb_result = MagicMock()
    mock_fb_result.scalars.return_value.all.return_value = []
    
    # Fifth call (appearances)
    mock_app_result = MagicMock()
    mock_app_result.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [
        mock_exp_result, mock_char_result, mock_camp_result,
        mock_fb_result, mock_app_result
    ]

    results = await career_service.searchMemory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        query="test",
        limit=10
    )

    assert results["total_results"] == 2
    assert "experiences" in results["results"]
    assert "characters" in results["results"]


# ========== TESTS: getTalentContext ==========

@pytest.mark.asyncio
async def test_get_talent_context_basic(career_service, sample_profile_id, sample_tenant_id):
    """Test getTalentContext returns structured context."""
    mock_db = AsyncMock()
    
    # Mock profile
    mock_profile_result = MagicMock()
    mock_profile_result.scalar_one_or_none.return_value = create_mock_profile(
        id=sample_profile_id, tenant_id=sample_tenant_id
    )
    
    # Mock experiences
    mock_exp_result = MagicMock()
    mock_exp_result.scalars.return_value.all.return_value = [
        create_mock_experience(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            title="Film A",
            production_type="film",
            skills_used=["acting", "fighting"]
        ),
        create_mock_experience(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            title="Commercial B",
            production_type="commercial",
            skills_used=["modeling", "acting"]
        )
    ]
    
    # Mock characters
    mock_char_result = MagicMock()
    mock_char_result.scalars.return_value.all.return_value = [
        create_mock_character(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            name="Hero",
            archetype="protagonist"
        )
    ]
    
    # Mock campaigns
    mock_camp_result = MagicMock()
    mock_camp_result.scalars.return_value.all.return_value = [
        create_mock_campaign(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            name="Campaign X"
        )
    ]
    
    # Mock agency contacts
    mock_agency_contact = MagicMock(spec=AgencyContact)
    mock_agency_contact.id = uuid4()
    mock_agency_contact.agency_id = uuid4()
    mock_agency_contact.profile_id = sample_profile_id
    mock_agency_contact.contact_type = "agent"
    mock_agency_contact.contract_type = "exclusive"
    mock_agency_contact.commission_rate = 0.20
    mock_agency_contact.start_date = date(2022, 1, 1)
    mock_agency_contact.status = "active"
    
    mock_agency = MagicMock(spec=Agency)
    mock_agency.id = mock_agency_contact.agency_id
    mock_agency.name = "Elite Agency"
    mock_agency.type = "talent"
    mock_agency.city = "Sao Paulo"
    mock_agency.country = "Brazil"
    mock_agency.specialties = ["film", "commercial"]
    
    mock_agency_result = MagicMock()
    mock_agency_result.all.return_value = [(mock_agency_contact, mock_agency)]
    
    # Mock feedbacks
    mock_fb_result = MagicMock()
    mock_fb_result.scalars.return_value.all.return_value = [
        create_mock_feedback(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            is_positive="true",
            rating=4.5
        ),
        create_mock_feedback(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            is_positive="false",
            rating=2.0
        )
    ]
    
    # Mock appearances
    mock_app_result = MagicMock()
    mock_app_result.scalars.return_value.all.return_value = [
        create_mock_appearance(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            record_type="approved"
        )
    ]
    
    # Mock style preferences
    mock_style_result = MagicMock()
    mock_style_result.scalars.return_value.all.return_value = [
        create_mock_style_preference(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            preference_type="caption_style",
            preference_value="professional"
        )
    ]
    
    # Mock content performance
    mock_perf_result = MagicMock()
    mock_perf_result.scalars.return_value.all.return_value = [
        create_mock_content_performance(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            engagement_rate=0.05
        )
    ]
    
    mock_db.execute.side_effect = [
        mock_profile_result,   # profile
        mock_exp_result,       # experiences
        mock_char_result,      # characters
        mock_camp_result,      # campaigns
        mock_agency_result,    # agencies
        mock_fb_result,        # feedbacks
        mock_app_result,       # approved appearances
        mock_app_result,       # rejected appearances
        mock_style_result,     # style preferences
        mock_perf_result,      # content performance
    ]

    context = await career_service.getTalentContext(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
    )

    # Assertions
    assert context["profile_id"] == str(sample_profile_id)
    assert context["profile"] is not None
    assert context["profile"]["full_name"] == "John Talent"
    
    assert len(context["experiences"]) == 2
    assert context["career_summary"]["total_experiences"] == 2
    
    assert len(context["characters"]) == 1
    assert context["characters"][0]["name"] == "Hero"
    
    assert len(context["campaigns"]) == 1
    
    assert len(context["agencies"]) == 1
    assert context["agencies"][0]["agency_name"] == "Elite Agency"
    
    assert "summary" in context["feedbacks"]
    assert context["feedbacks"]["summary"]["total_count"] == 2
    assert context["feedbacks"]["summary"]["positive_count"] == 1
    assert context["feedbacks"]["summary"]["negative_count"] == 1
    
    assert len(context["appearances"]["approved"]) == 1
    
    assert len(context["style_preferences"]) == 1
    
    assert len(context["content_performance"]) == 1
    
    # Career summary
    assert "production_types_breakdown" in context["career_summary"]
    assert context["career_summary"]["production_types_breakdown"]["film"] == 1
    assert context["career_summary"]["production_types_breakdown"]["commercial"] == 1
    
    # Top skills
    assert "acting" in context["career_summary"]["top_skills"]
    assert context["career_summary"]["top_skills"]["acting"] == 2
    
    # Talent Graph
    assert "frequent_directors" in context["talent_graph"]
    assert "character_archetypes" in context["talent_graph"]


@pytest.mark.asyncio
async def test_get_talent_context_no_profile(career_service, sample_profile_id, sample_tenant_id):
    """Test getTalentContext handles missing profile."""
    mock_db = AsyncMock()
    
    mock_profile_result = MagicMock()
    mock_profile_result.scalar_one_or_none.return_value = None
    
    mock_empty_result = MagicMock()
    mock_empty_result.scalars.return_value.all.return_value = []
    mock_empty_result.all.return_value = []
    
    mock_db.execute.side_effect = [
        mock_profile_result,   # profile (None)
        mock_empty_result,     # experiences
        mock_empty_result,     # characters
        mock_empty_result,     # campaigns
        mock_empty_result,     # agencies
        mock_empty_result,     # feedbacks
        mock_empty_result,     # approved
        mock_empty_result,     # rejected
        mock_empty_result,     # style preferences
        mock_empty_result,     # content performance
    ]

    context = await career_service.getTalentContext(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
    )

    assert context["profile"] is None
    assert context["career_summary"]["total_experiences"] == 0
    assert context["career_summary"]["years_active"] == 0


# ========== TESTS: getRelevantHistory ==========

@pytest.mark.asyncio
async def test_get_relevant_history_casting(career_service, sample_profile_id, sample_tenant_id):
    """Test getRelevantHistory for casting context."""
    mock_db = AsyncMock()
    
    # Mock experiences
    mock_exp_result = MagicMock()
    mock_exp_result.scalars.return_value.all.return_value = [
        create_mock_experience(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            title="Action Film",
            production_type="film",
            role="Lead"
        )
    ]
    
    # Mock feedbacks
    mock_fb_result = MagicMock()
    mock_fb_result.scalars.return_value.all.return_value = [
        create_mock_feedback(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            feedback_type="performance",
            is_positive="true"
        )
    ]
    
    # Mock approved appearances
    mock_app_result = MagicMock()
    mock_app_result.scalars.return_value.all.return_value = [
        create_mock_appearance(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            record_type="approved",
            title="Casting Approved"
        )
    ]
    
    mock_db.execute.side_effect = [
        mock_exp_result, mock_fb_result, mock_app_result
    ]

    history = await career_service.getRelevantHistory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        context="casting",
        keywords=["action"],
        limit=10
    )

    assert history["context"] == "casting"
    assert len(history["relevant_items"]) > 0
    
    # Check experience item
    exp_items = [i for i in history["relevant_items"] if i["type"] == "experience"]
    assert len(exp_items) == 1
    assert exp_items[0]["relevance_score"] > 0
    
    # Check insights
    assert len(history["insights"]) == 3
    assert "experiencias profissionais" in history["insights"][0]


@pytest.mark.asyncio
async def test_get_relevant_history_character(career_service, sample_profile_id, sample_tenant_id):
    """Test getRelevantHistory for character context."""
    mock_db = AsyncMock()
    
    # Mock characters
    mock_char_result = MagicMock()
    mock_char_result.scalars.return_value.all.return_value = [
        create_mock_character(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            name="The Villain",
            archetype="antagonist"
        )
    ]
    
    # Mock experiences with character
    mock_exp_result = MagicMock()
    mock_exp_result.scalars.return_value.all.return_value = [
        create_mock_experience(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            title="Drama Series",
            character_name="The Villain"
        )
    ]
    
    mock_db.execute.side_effect = [mock_char_result, mock_exp_result]

    history = await career_service.getRelevantHistory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        context="character",
        keywords=["villain"],
        limit=10
    )

    assert history["context"] == "character"
    
    char_items = [i for i in history["relevant_items"] if i["type"] == "character"]
    assert len(char_items) == 1
    assert char_items[0]["name"] == "The Villain"
    
    exp_items = [i for i in history["relevant_items"] if i["type"] == "experience_with_character"]
    assert len(exp_items) == 1


@pytest.mark.asyncio
async def test_get_relevant_history_campaign(career_service, sample_profile_id, sample_tenant_id):
    """Test getRelevantHistory for campaign context."""
    mock_db = AsyncMock()
    
    # Mock campaigns
    mock_camp_result = MagicMock()
    mock_camp_result.scalars.return_value.all.return_value = [
        create_mock_campaign(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            name="Winter Campaign",
            brand="Adidas"
        )
    ]
    
    # Mock content performance
    mock_perf_result = MagicMock()
    mock_perf_result.scalars.return_value.all.return_value = [
        create_mock_content_performance(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            best_performing="true",
            engagement_rate=0.08
        )
    ]
    
    mock_db.execute.side_effect = [mock_camp_result, mock_perf_result]

    history = await career_service.getRelevantHistory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        context="campaign",
        keywords=["winter"],
        limit=10
    )

    assert history["context"] == "campaign"
    
    camp_items = [i for i in history["relevant_items"] if i["type"] == "campaign"]
    assert len(camp_items) == 1
    
    perf_items = [i for i in history["relevant_items"] if i["type"] == "content_performance"]
    assert len(perf_items) == 1


@pytest.mark.asyncio
async def test_get_relevant_history_content(career_service, sample_profile_id, sample_tenant_id):
    """Test getRelevantHistory for content context."""
    mock_db = AsyncMock()
    
    # Mock style preferences
    mock_style_result = MagicMock()
    mock_style_result.scalars.return_value.all.return_value = [
        create_mock_style_preference(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            preference_type="hashtag_style",
            preference_value="minimal",
            usage_count=15
        )
    ]
    
    # Mock content performance
    mock_perf_result = MagicMock()
    mock_perf_result.scalars.return_value.all.return_value = [
        create_mock_content_performance(
            profile_id=sample_profile_id,
            tenant_id=sample_tenant_id,
            engagement_rate=0.06
        )
    ]
    
    mock_db.execute.side_effect = [mock_style_result, mock_perf_result]

    history = await career_service.getRelevantHistory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        context="content",
        limit=10
    )

    assert history["context"] == "content"
    
    style_items = [i for i in history["relevant_items"] if i["type"] == "style_preference"]
    assert len(style_items) == 1
    assert style_items[0]["preference_type"] == "hashtag_style"
    
    perf_items = [i for i in history["relevant_items"] if i["type"] == "content_performance"]
    assert len(perf_items) == 1


@pytest.mark.asyncio
async def test_get_relevant_history_limit(career_service, sample_profile_id, sample_tenant_id):
    """Test getRelevantHistory respects limit."""
    mock_db = AsyncMock()
    
    mock_exp_result = MagicMock()
    mock_exp_result.scalars.return_value.all.return_value = [
        create_mock_experience(profile_id=sample_profile_id, tenant_id=sample_tenant_id, title=f"Film {i}")
        for i in range(20)
    ]
    
    mock_fb_result = MagicMock()
    mock_fb_result.scalars.return_value.all.return_value = []
    
    mock_app_result = MagicMock()
    mock_app_result.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_exp_result, mock_fb_result, mock_app_result]

    history = await career_service.getRelevantHistory(
        db=mock_db,
        profile_id=sample_profile_id,
        tenant_id=sample_tenant_id,
        context="casting",
        limit=5
    )

    assert len(history["relevant_items"]) <= 5


# ========== TESTS: _calculate_years_active ==========

def test_calculate_years_active(career_service):
    """Test _calculate_years_active helper."""
    mock_exp1 = create_mock_experience(
        start_date=date(2020, 1, 1),
        end_date=date(2023, 1, 1)
    )
    mock_exp2 = create_mock_experience(
        start_date=date(2021, 6, 1),
        end_date=date(2022, 6, 1)
    )
    
    years = career_service._calculate_years_active([mock_exp1, mock_exp2])
    assert years == 3  # 2020 to 2023


def test_calculate_years_active_empty(career_service):
    """Test _calculate_years_active with empty list."""
    years = career_service._calculate_years_active([])
    assert years == 0


def test_calculate_years_active_no_dates(career_service):
    """Test _calculate_years_active with no dates."""
    mock_exp = create_mock_experience(start_date=None, end_date=None)
    years = career_service._calculate_years_active([mock_exp])
    assert years == 0


# ========== TESTS: CRUD Operations ==========

@pytest.mark.asyncio
async def test_create_experience(career_service, sample_profile_id, sample_tenant_id):
    """Test create_experience."""
    mock_db = AsyncMock()
    
    with patch("app.memory.career_memory_service.emit_event", new_callable=AsyncMock):
        result = await career_service.create_experience(
            db=mock_db,
            tenant_id=sample_tenant_id,
            profile_id=sample_profile_id,
            title="New Film",
            production_type="film"
        )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_character(career_service, sample_profile_id, sample_tenant_id):
    """Test create_character."""
    mock_db = AsyncMock()
    
    with patch("app.memory.career_memory_service.emit_event", new_callable=AsyncMock):
        result = await career_service.create_character(
            db=mock_db,
            tenant_id=sample_tenant_id,
            profile_id=sample_profile_id,
            name="New Character",
            archetype="hero"
        )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_feedback(career_service, sample_profile_id, sample_tenant_id):
    """Test create_feedback."""
    mock_db = AsyncMock()
    
    result = await career_service.create_feedback(
        db=mock_db,
        tenant_id=sample_tenant_id,
        profile_id=sample_profile_id,
        source="director",
        source_name="Jane Smith",
        feedback_type="performance",
        feedback_text="Great job!",
        rating=5.0
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_appearance_record(career_service, sample_profile_id, sample_tenant_id):
    """Test create_appearance_record."""
    mock_db = AsyncMock()
    
    result = await career_service.create_appearance_record(
        db=mock_db,
        tenant_id=sample_tenant_id,
        profile_id=sample_profile_id,
        record_type="approved",
        title="Fashion Show"
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_style_preference(career_service, sample_profile_id, sample_tenant_id):
    """Test create_style_preference."""
    mock_db = AsyncMock()
    
    result = await career_service.create_style_preference(
        db=mock_db,
        tenant_id=sample_tenant_id,
        profile_id=sample_profile_id,
        preference_type="photo_filter",
        preference_value="warm"
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_content_performance(career_service, sample_profile_id, sample_tenant_id):
    """Test create_content_performance."""
    mock_db = AsyncMock()
    
    result = await career_service.create_content_performance(
        db=mock_db,
        tenant_id=sample_tenant_id,
        profile_id=sample_profile_id,
        platform="instagram",
        engagement_rate=0.05
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
