"""
Career Memory Router — Rotas REST para o Talent Graph.

Endpoints para gerenciar e consultar a memoria de carreira do talento:
- Experiencias profissionais
- Personagens
- Campanhas
- Feedbacks
- Aparicoes
- Busca textual (searchMemory)
- Contexto completo (getTalentContext)
- Historico relevante (getRelevantHistory)
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.memory.career_memory_service import CareerMemoryService
from app.middleware.auth import get_current_user
from app.middleware.tenant import get_tenant_id
from app.schemas.schemas import (
    ProfessionalExperienceCreate,
    ProfessionalExperienceResponse,
    CharacterCreate,
    CharacterResponse,
    CampaignCreate,
    CampaignResponse,
    CareerFeedbackCreate,
    CareerFeedbackResponse,
    AppearanceRecordCreate,
    AppearanceRecordResponse,
    StylePreferenceCreate,
    StylePreferenceResponse,
    ContentPerformanceCreate,
    ContentPerformanceResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/career", tags=["Career Memory"])
career_service = CareerMemoryService()


# ========== PROFESSIONAL EXPERIENCES ==========


@router.post(
    "/experiences",
    response_model=ProfessionalExperienceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_experience(
    data: ProfessionalExperienceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra uma nova experiencia profissional no Talent Graph."""
    experience = await career_service.create_experience(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        title=data.title,
        company=data.company,
        project_name=data.project_name,
        role=data.role,
        character_name=data.character_name,
        production_type=data.production_type,
        director=data.director,
        agency=data.agency,
        start_date=data.start_date,
        end_date=data.end_date,
        location=data.location,
        description=data.description,
        skills_used=data.skills_used,
        photos_used=data.photos_used,
        video_url=data.video_url,
        is_featured=data.is_featured,
        metadata=data.metadata,
    )
    return experience


@router.get(
    "/experiences/{profile_id}", response_model=List[ProfessionalExperienceResponse]
)
async def get_experiences(
    profile_id: UUID,
    production_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista experiencias profissionais de um perfil."""
    if production_type:
        experiences = await career_service.get_experiences_by_type(
            db=db,
            profile_id=profile_id,
            tenant_id=tenant_id,
            production_type=production_type,
        )
    else:
        experiences = await career_service.get_experiences(
            db=db, profile_id=profile_id, tenant_id=tenant_id, limit=limit
        )
    return experiences


# ========== CHARACTERS ==========


@router.post(
    "/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED
)
async def create_character(
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra um novo personagem no Talent Graph."""
    character = await career_service.create_character(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        name=data.name,
        archetype=data.archetype,
        age_range=data.age_range,
        gender_presentation=data.gender_presentation,
        physical_description=data.physical_description,
        personality_traits=data.personality_traits,
        wardrobe_description=data.wardrobe_description,
        makeup_description=data.makeup_description,
        hair_description=data.hair_description,
        accessories=data.accessories,
        era=data.era,
        profession=data.profession,
        social_status=data.social_status,
        emotional_state=data.emotional_state,
        photos=data.photos,
        videos=data.videos,
        experience_id=data.experience_id,
        is_simulated=data.is_simulated,
        simulation_prompt=data.simulation_prompt,
        metadata=data.metadata,
    )
    return character


@router.get("/characters/{profile_id}", response_model=List[CharacterResponse])
async def get_characters(
    profile_id: UUID,
    include_simulated: bool = Query(True),
    archetype: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista personagens de um perfil."""
    if archetype:
        characters = await career_service.get_character_by_archetype(
            db=db,
            profile_id=profile_id,
            tenant_id=tenant_id,
            archetype=archetype,
        )
    else:
        characters = await career_service.get_characters(
            db=db,
            profile_id=profile_id,
            tenant_id=tenant_id,
            include_simulated=include_simulated,
        )
    return characters


# ========== CAMPAIGNS ==========


@router.post(
    "/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra uma nova campanha no Talent Graph."""
    campaign = await career_service.create_campaign(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        name=data.name,
        brand=data.brand,
        agency=data.agency,
        campaign_type=data.campaign_type,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description,
        deliverables=data.deliverables,
        photos_used=data.photos_used,
        videos_used=data.videos_used,
        results=data.results,
        metadata=data.metadata,
    )
    return campaign


@router.get("/campaigns/{profile_id}", response_model=List[CampaignResponse])
async def get_campaigns(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista campanhas de um perfil."""
    campaigns = await career_service.get_campaigns(
        db=db, profile_id=profile_id, tenant_id=tenant_id
    )
    return campaigns


# ========== FEEDBACKS ==========


@router.post(
    "/feedbacks",
    response_model=CareerFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    data: CareerFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra um novo feedback no Talent Graph."""
    feedback = await career_service.create_feedback(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        source=data.source,
        source_name=data.source_name,
        feedback_type=data.feedback_type,
        feedback_text=data.feedback_text,
        rating=data.rating,
        related_experience_id=data.related_experience_id,
        related_casting_id=data.related_casting_id,
        related_content_id=data.related_content_id,
        is_positive=data.is_positive,
        action_taken=data.action_taken,
        metadata=data.metadata,
    )
    return feedback


@router.get("/feedbacks/{profile_id}", response_model=List[CareerFeedbackResponse])
async def get_feedbacks(
    profile_id: UUID,
    feedback_type: Optional[str] = None,
    is_positive: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista feedbacks de um perfil."""
    feedbacks = await career_service.get_feedbacks(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        feedback_type=feedback_type,
        is_positive=is_positive,
    )
    return feedbacks


# ========== APPEARANCE RECORDS ==========


@router.post(
    "/appearances",
    response_model=AppearanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_appearance_record(
    data: AppearanceRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra uma nova aparicao no Talent Graph."""
    record = await career_service.create_appearance_record(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        record_type=data.record_type,
        title=data.title,
        description=data.description,
        photos=data.photos,
        related_character_id=data.related_character_id,
        related_experience_id=data.related_experience_id,
        related_casting_id=data.related_casting_id,
        feedback=data.feedback,
        rating=data.rating,
        tags=data.tags,
        metadata=data.metadata,
    )
    return record


@router.get(
    "/appearances/{profile_id}/approved", response_model=List[AppearanceRecordResponse]
)
async def get_approved_appearances(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista aparicoes aprovadas de um perfil."""
    appearances = await career_service.get_approved_appearances(
        db=db, profile_id=profile_id, tenant_id=tenant_id
    )
    return appearances


@router.get(
    "/appearances/{profile_id}/rejected", response_model=List[AppearanceRecordResponse]
)
async def get_rejected_appearances(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista aparicoes rejeitadas de um perfil."""
    appearances = await career_service.get_rejected_appearances(
        db=db, profile_id=profile_id, tenant_id=tenant_id
    )
    return appearances


# ========== STYLE PREFERENCES ==========


@router.post(
    "/style-preferences",
    response_model=StylePreferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_style_preference(
    data: StylePreferenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra uma preferencia de estilo."""
    pref = await career_service.create_style_preference(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        preference_type=data.preference_type,
        preference_value=data.preference_value,
        context=data.context,
        metadata=data.metadata,
    )
    return pref


@router.get(
    "/style-preferences/{profile_id}", response_model=List[StylePreferenceResponse]
)
async def get_style_preferences(
    profile_id: UUID,
    preference_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista preferencias de estilo de um perfil."""
    prefs = await career_service.get_style_preferences(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        preference_type=preference_type,
    )
    return prefs


# ========== CONTENT PERFORMANCE ==========


@router.post(
    "/content-performance",
    response_model=ContentPerformanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_performance(
    data: ContentPerformanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Registra performance de conteudo."""
    perf = await career_service.create_content_performance(
        db=db,
        tenant_id=tenant_id,
        profile_id=data.profile_id,
        content_item_id=data.content_item_id,
        platform=data.platform,
        metrics=data.metrics,
        engagement_rate=data.engagement_rate,
        best_performing=data.best_performing,
        audience_demographics=data.audience_demographics,
        peak_hours=data.peak_hours,
        metadata=data.metadata,
    )
    return perf


@router.get(
    "/content-performance/{profile_id}", response_model=List[ContentPerformanceResponse]
)
async def get_content_performances(
    profile_id: UUID,
    best_performing_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Lista performances de conteudo de um perfil."""
    performances = await career_service.get_content_performances(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        best_performing_only=best_performing_only,
    )
    return performances


# ========== TALENT GRAPH: CONSULTA INTEGRADA ==========


@router.get("/search/{profile_id}")
async def search_memory(
    profile_id: UUID,
    q: str = Query(..., min_length=1, description="Termo de busca"),
    entity_types: Optional[List[str]] = Query(
        None,
        description="Tipos de entidade: experiences, characters, campaigns, feedbacks, appearances",
    ),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Busca textual inteligente em toda a memoria de carreira do talento.

    Busca em experiencias, personagens, campanhas, feedbacks e aparicoes.
    Retorna resultados agrupados por tipo com score de relevancia.
    """
    results = await career_service.searchMemory(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        query=q,
        entity_types=entity_types,
        limit=limit,
    )
    return results


@router.get("/context/{profile_id}")
async def get_talent_context(
    profile_id: UUID,
    include_private: bool = Query(
        False, description="Incluir dados privados (simulation prompts)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Retorna o contexto completo do talento para uso pelos agentes.

    Inclui: perfil, experiencias, personagens, campanhas, agencias,
    feedbacks, aparicoes, preferencias de estilo, performance de conteudo
    e o Talent Graph (relacoes e sumario de carreira).
    """
    context = await career_service.getTalentContext(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        include_private=include_private,
    )
    return context


@router.get("/relevant/{profile_id}")
async def get_relevant_history(
    profile_id: UUID,
    context: str = Query(
        ..., description="Contexto: casting, character, campaign, content"
    ),
    keywords: Optional[List[str]] = Query(
        None, description="Palavras-chave para filtrar"
    ),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """
    Retorna o historico do talento relevante para um contexto especifico.

    Contextos suportados:
    - casting: experiencias similares, feedbacks, aparicoes aprovadas
    - character: personagens similares, experiencias com personagens
    - campaign: campanhas similares, performance de conteudo
    - content: preferencias de estilo, performance, melhores posts
    """
    history = await career_service.getRelevantHistory(
        db=db,
        profile_id=profile_id,
        tenant_id=tenant_id,
        context=context,
        keywords=keywords,
        limit=limit,
    )
    return history
