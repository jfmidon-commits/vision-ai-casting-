"""
CareerMemoryService - Servico de Memoria de Carreira / Talent Graph.

Responsavel por:
- Persistir experiencias profissionais (trabalhos, personagens, campanhas)
- Registrar agencias e contatos
- Armazenar feedbacks recebidos
- Registrar aparicoes aprovadas vs rejeitadas
- Armazenar preferencias de estilo do usuario
- Registrar performance de conteudo
- Consultar memoria para agentes (contexto completo do talento)
- Gerar "Talent Graph" - grafo de relacionamentos do talento
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import VisionEventType, emit_event
from app.models import (
    Agency,
    AgencyContact,
    AppearanceRecord,
    Campaign,
    CareerFeedback,
    Character,
    ContentPerformance,
    ProfessionalExperience,
    Profile,
    StylePreference,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CareerMemoryService:
    """Servico de Memoria de Carreira / Talent Graph."""

    # ========== PROFESSIONAL EXPERIENCES ==========

    async def create_experience(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        title: str,
        company: Optional[str] = None,
        project_name: Optional[str] = None,
        role: Optional[str] = None,
        character_name: Optional[str] = None,
        production_type: Optional[str] = None,
        director: Optional[str] = None,
        agency: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        skills_used: Optional[List[str]] = None,
        photos_used: Optional[List[str]] = None,
        video_url: Optional[str] = None,
        is_featured: bool = False,
        metadata: Optional[Dict] = None,
    ) -> ProfessionalExperience:
        """Registra uma experiencia profissional no Talent Graph."""
        experience = ProfessionalExperience(
            tenant_id=tenant_id,
            profile_id=profile_id,
            title=title,
            company=company,
            project_name=project_name,
            role=role,
            character_name=character_name,
            production_type=production_type,
            director=director,
            agency=agency,
            start_date=start_date,
            end_date=end_date,
            location=location,
            description=description,
            skills_used=skills_used or [],
            photos_used=photos_used or [],
            video_url=video_url,
            is_featured="true" if is_featured else "false",
            metadata=metadata or {},
        )
        db.add(experience)
        await db.commit()
        await db.refresh(experience)

        await emit_event(
            event_type=VisionEventType.PROFILE_UPDATED,
            payload={
                "profile_id": str(profile_id),
                "action": "experience_added",
                "experience_id": str(experience.id),
            },
        )
        logger.info(f"Experience created: {experience.id} for profile {profile_id}")
        return experience

    async def get_experiences(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
    ) -> List[ProfessionalExperience]:
        """Lista experiencias de um perfil."""
        result = await db.execute(
            select(ProfessionalExperience)
            .where(
                and_(
                    ProfessionalExperience.profile_id == profile_id,
                    ProfessionalExperience.tenant_id == tenant_id,
                    ProfessionalExperience.status == "active",
                )
            )
            .order_by(desc(ProfessionalExperience.start_date))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_experiences_by_type(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        production_type: str,
    ) -> List[ProfessionalExperience]:
        """Filtra experiencias por tipo (film, series, commercial, etc)."""
        result = await db.execute(
            select(ProfessionalExperience)
            .where(
                and_(
                    ProfessionalExperience.profile_id == profile_id,
                    ProfessionalExperience.tenant_id == tenant_id,
                    ProfessionalExperience.production_type == production_type,
                    ProfessionalExperience.status == "active",
                )
            )
            .order_by(desc(ProfessionalExperience.start_date))
        )
        return result.scalars().all()

    # ========== CHARACTERS ==========

    async def create_character(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        name: str,
        archetype: Optional[str] = None,
        age_range: Optional[str] = None,
        gender_presentation: Optional[str] = None,
        physical_description: Optional[str] = None,
        personality_traits: Optional[List[str]] = None,
        wardrobe_description: Optional[str] = None,
        makeup_description: Optional[str] = None,
        hair_description: Optional[str] = None,
        accessories: Optional[List[str]] = None,
        era: Optional[str] = None,
        profession: Optional[str] = None,
        social_status: Optional[str] = None,
        emotional_state: Optional[str] = None,
        photos: Optional[List[str]] = None,
        videos: Optional[List[str]] = None,
        experience_id: Optional[UUID] = None,
        is_simulated: bool = False,
        simulation_prompt: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Character:
        """Registra um personagem no Talent Graph."""
        character = Character(
            tenant_id=tenant_id,
            profile_id=profile_id,
            name=name,
            archetype=archetype,
            age_range=age_range,
            gender_presentation=gender_presentation,
            physical_description=physical_description,
            personality_traits=personality_traits or [],
            wardrobe_description=wardrobe_description,
            makeup_description=makeup_description,
            hair_description=hair_description,
            accessories=accessories or [],
            era=era,
            profession=profession,
            social_status=social_status,
            emotional_state=emotional_state,
            photos=photos or [],
            videos=videos or [],
            experience_id=experience_id,
            is_simulated="true" if is_simulated else "false",
            simulation_prompt=simulation_prompt,
            metadata=metadata or {},
        )
        db.add(character)
        await db.commit()
        await db.refresh(character)

        await emit_event(
            event_type=VisionEventType.DIGITAL_TWIN_UPDATED,
            payload={
                "profile_id": str(profile_id),
                "action": "character_added",
                "character_id": str(character.id),
            },
        )
        logger.info(f"Character created: {character.id} for profile {profile_id}")
        return character

    async def get_characters(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        include_simulated: bool = True,
    ) -> List[Character]:
        """Lista personagens de um perfil."""
        query = select(Character).where(
            and_(
                Character.profile_id == profile_id,
                Character.tenant_id == tenant_id,
                Character.status == "active",
            )
        )
        if not include_simulated:
            query = query.where(Character.is_simulated == "false")

        result = await db.execute(query.order_by(desc(Character.created_at)))
        return result.scalars().all()

    async def get_character_by_archetype(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        archetype: str,
    ) -> List[Character]:
        """Busca personagens por arquetipo."""
        result = await db.execute(
            select(Character).where(
                and_(
                    Character.profile_id == profile_id,
                    Character.tenant_id == tenant_id,
                    Character.archetype == archetype,
                    Character.status == "active",
                )
            )
        )
        return result.scalars().all()

    # ========== CAMPAIGNS ==========

    async def create_campaign(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        name: str,
        brand: Optional[str] = None,
        agency: Optional[str] = None,
        campaign_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        description: Optional[str] = None,
        deliverables: Optional[List[str]] = None,
        photos_used: Optional[List[str]] = None,
        videos_used: Optional[List[str]] = None,
        results: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Campaign:
        """Registra uma campanha no Talent Graph."""
        campaign = Campaign(
            tenant_id=tenant_id,
            profile_id=profile_id,
            name=name,
            brand=brand,
            agency=agency,
            campaign_type=campaign_type,
            start_date=start_date,
            end_date=end_date,
            description=description,
            deliverables=deliverables or [],
            photos_used=photos_used or [],
            videos_used=videos_used or [],
            results=results or {},
            metadata=metadata or {},
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        logger.info(f"Campaign created: {campaign.id} for profile {profile_id}")
        return campaign

    async def get_campaigns(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> List[Campaign]:
        """Lista campanhas de um perfil."""
        result = await db.execute(
            select(Campaign)
            .where(
                and_(
                    Campaign.profile_id == profile_id,
                    Campaign.tenant_id == tenant_id,
                    Campaign.status == "active",
                )
            )
            .order_by(desc(Campaign.start_date))
        )
        return result.scalars().all()

    # ========== AGENCIES ==========

    async def create_agency(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        name: str,
        type: Optional[str] = None,
        contact_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        specialties: Optional[List[str]] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Agency:
        """Registra uma agencia no Talent Graph."""
        agency = Agency(
            tenant_id=tenant_id,
            name=name,
            type=type,
            contact_name=contact_name,
            email=email,
            phone=phone,
            website=website,
            address=address,
            city=city,
            country=country,
            specialties=specialties or [],
            notes=notes,
            metadata=metadata or {},
        )
        db.add(agency)
        await db.commit()
        await db.refresh(agency)
        logger.info(f"Agency created: {agency.id}")
        return agency

    async def create_agency_contact(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        agency_id: UUID,
        profile_id: UUID,
        contact_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        contract_type: Optional[str] = None,
        commission_rate: Optional[float] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AgencyContact:
        """Registra um contato de agencia para um perfil."""
        contact = AgencyContact(
            tenant_id=tenant_id,
            agency_id=agency_id,
            profile_id=profile_id,
            contact_type=contact_type,
            start_date=start_date,
            end_date=end_date,
            contract_type=contract_type,
            commission_rate=commission_rate,
            notes=notes,
            metadata=metadata or {},
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        logger.info(f"Agency contact created: {contact.id}")
        return contact

    # ========== FEEDBACKS ==========

    async def create_feedback(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        source: str,
        source_name: str,
        feedback_type: str,
        feedback_text: str,
        rating: Optional[float] = None,
        related_experience_id: Optional[UUID] = None,
        related_casting_id: Optional[UUID] = None,
        related_content_id: Optional[UUID] = None,
        is_positive: bool = True,
        action_taken: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> CareerFeedback:
        """Registra um feedback no Talent Graph."""
        feedback = CareerFeedback(
            tenant_id=tenant_id,
            profile_id=profile_id,
            source=source,
            source_name=source_name,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            rating=rating,
            related_experience_id=related_experience_id,
            related_casting_id=related_casting_id,
            related_content_id=related_content_id,
            is_positive="true" if is_positive else "false",
            action_taken=action_taken,
            metadata=metadata or {},
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        logger.info(f"Feedback created: {feedback.id} for profile {profile_id}")
        return feedback

    async def get_feedbacks(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        feedback_type: Optional[str] = None,
        is_positive: Optional[bool] = None,
    ) -> List[CareerFeedback]:
        """Lista feedbacks de um perfil com filtros."""
        query = select(CareerFeedback).where(
            and_(
                CareerFeedback.profile_id == profile_id,
                CareerFeedback.tenant_id == tenant_id,
                CareerFeedback.status == "active",
            )
        )
        if feedback_type:
            query = query.where(CareerFeedback.feedback_type == feedback_type)
        if is_positive is not None:
            query = query.where(
                CareerFeedback.is_positive == ("true" if is_positive else "false")
            )

        result = await db.execute(query.order_by(desc(CareerFeedback.created_at)))
        return result.scalars().all()

    # ========== APPEARANCE RECORDS ==========

    async def create_appearance_record(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        record_type: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        photos: Optional[List[str]] = None,
        related_character_id: Optional[UUID] = None,
        related_experience_id: Optional[UUID] = None,
        related_casting_id: Optional[UUID] = None,
        feedback: Optional[str] = None,
        rating: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> AppearanceRecord:
        """Registra uma aparicao (aprovada, rejeitada, simulada)."""
        record = AppearanceRecord(
            tenant_id=tenant_id,
            profile_id=profile_id,
            record_type=record_type,
            title=title,
            description=description,
            photos=photos or [],
            related_character_id=related_character_id,
            related_experience_id=related_experience_id,
            related_casting_id=related_casting_id,
            feedback=feedback,
            rating=rating,
            tags=tags or [],
            metadata=metadata or {},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info(f"Appearance record created: {record.id} type={record_type}")
        return record

    async def get_approved_appearances(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> List[AppearanceRecord]:
        """Lista aparicoes aprovadas."""
        result = await db.execute(
            select(AppearanceRecord)
            .where(
                and_(
                    AppearanceRecord.profile_id == profile_id,
                    AppearanceRecord.tenant_id == tenant_id,
                    AppearanceRecord.record_type == "approved",
                    AppearanceRecord.status == "active",
                )
            )
            .order_by(desc(AppearanceRecord.created_at))
        )
        return result.scalars().all()

    async def get_rejected_appearances(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
    ) -> List[AppearanceRecord]:
        """Lista aparicoes rejeitadas (para aprendizado)."""
        result = await db.execute(
            select(AppearanceRecord)
            .where(
                and_(
                    AppearanceRecord.profile_id == profile_id,
                    AppearanceRecord.tenant_id == tenant_id,
                    AppearanceRecord.record_type == "rejected",
                    AppearanceRecord.status == "active",
                )
            )
            .order_by(desc(AppearanceRecord.created_at))
        )
        return result.scalars().all()

    # ========== STYLE PREFERENCES ==========

    async def create_style_preference(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        preference_type: str,
        preference_value: str,
        context: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> StylePreference:
        """Registra uma preferencia de estilo."""
        pref = StylePreference(
            tenant_id=tenant_id,
            profile_id=profile_id,
            preference_type=preference_type,
            preference_value=preference_value,
            context=context,
            metadata=metadata or {},
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
        logger.info(f"Style preference created: {pref.id} type={preference_type}")
        return pref

    async def get_style_preferences(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        preference_type: Optional[str] = None,
    ) -> List[StylePreference]:
        """Lista preferencias de estilo."""
        query = select(StylePreference).where(
            and_(
                StylePreference.profile_id == profile_id,
                StylePreference.tenant_id == tenant_id,
                StylePreference.status == "active",
            )
        )
        if preference_type:
            query = query.where(StylePreference.preference_type == preference_type)

        result = await db.execute(query.order_by(desc(StylePreference.usage_count)))
        return result.scalars().all()

    # ========== CONTENT PERFORMANCE ==========

    async def create_content_performance(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        content_item_id: Optional[UUID] = None,
        platform: str = "instagram",
        metrics: Optional[Dict] = None,
        engagement_rate: Optional[float] = None,
        best_performing: bool = False,
        audience_demographics: Optional[Dict] = None,
        peak_hours: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> ContentPerformance:
        """Registra performance de conteudo."""
        perf = ContentPerformance(
            tenant_id=tenant_id,
            profile_id=profile_id,
            content_item_id=content_item_id,
            platform=platform,
            metrics=metrics or {},
            engagement_rate=engagement_rate,
            best_performing="true" if best_performing else "false",
            audience_demographics=audience_demographics or {},
            peak_hours=peak_hours or [],
            metadata=metadata or {},
        )
        db.add(perf)
        await db.commit()
        await db.refresh(perf)
        logger.info(f"Content performance created: {perf.id}")
        return perf

    async def get_content_performances(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        best_performing_only: bool = False,
    ) -> List[ContentPerformance]:
        """Lista performances de conteudo."""
        query = select(ContentPerformance).where(
            and_(
                ContentPerformance.profile_id == profile_id,
                ContentPerformance.tenant_id == tenant_id,
                ContentPerformance.status == "active",
            )
        )
        if best_performing_only:
            query = query.where(ContentPerformance.best_performing == "true")

        result = await db.execute(
            query.order_by(desc(ContentPerformance.engagement_rate))
        )
        return result.scalars().all()

    # ========== TALENT GRAPH: CONSULTA INTEGRADA (ETAPA 1) ==========

    async def searchMemory(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Busca textual inteligente em toda a memoria de carreira do talento.

        Busca em: experiencias, personagens, campanhas, feedbacks, aparicoes.
        Retorna resultados agrupados por tipo de entidade com relevancia.
        """
        search_term = f"%{query.lower()}%"
        entity_types = entity_types or [
            "experiences",
            "characters",
            "campaigns",
            "feedbacks",
            "appearances",
        ]
        results = {
            "query": query,
            "profile_id": str(profile_id),
            "total_results": 0,
            "results": {},
        }

        # 1. Buscar em ProfessionalExperiences
        if "experiences" in entity_types:
            exp_result = await db.execute(
                select(ProfessionalExperience)
                .where(
                    and_(
                        ProfessionalExperience.profile_id == profile_id,
                        ProfessionalExperience.tenant_id == tenant_id,
                        ProfessionalExperience.status == "active",
                        or_(
                            func.lower(ProfessionalExperience.title).like(search_term),
                            func.lower(ProfessionalExperience.company).like(
                                search_term
                            ),
                            func.lower(ProfessionalExperience.project_name).like(
                                search_term
                            ),
                            func.lower(ProfessionalExperience.role).like(search_term),
                            func.lower(ProfessionalExperience.character_name).like(
                                search_term
                            ),
                            func.lower(ProfessionalExperience.description).like(
                                search_term
                            ),
                            func.lower(ProfessionalExperience.director).like(
                                search_term
                            ),
                            func.lower(ProfessionalExperience.agency).like(search_term),
                            func.lower(ProfessionalExperience.production_type).like(
                                search_term
                            ),
                        ),
                    )
                )
                .order_by(desc(ProfessionalExperience.start_date))
                .limit(limit)
            )
            experiences = exp_result.scalars().all()
            if experiences:
                results["results"]["experiences"] = [
                    {
                        "id": str(e.id),
                        "title": e.title,
                        "company": e.company,
                        "project_name": e.project_name,
                        "role": e.role,
                        "character_name": e.character_name,
                        "production_type": e.production_type,
                        "start_date": (
                            e.start_date.isoformat() if e.start_date else None
                        ),
                        "description": e.description,
                        "relevance": (
                            "high"
                            if query.lower() in (e.title or "").lower()
                            else "medium"
                        ),
                    }
                    for e in experiences
                ]
                results["total_results"] += len(experiences)

        # 2. Buscar em Characters
        if "characters" in entity_types:
            char_result = await db.execute(
                select(Character)
                .where(
                    and_(
                        Character.profile_id == profile_id,
                        Character.tenant_id == tenant_id,
                        Character.status == "active",
                        or_(
                            func.lower(Character.name).like(search_term),
                            func.lower(Character.archetype).like(search_term),
                            func.lower(Character.physical_description).like(
                                search_term
                            ),
                            func.lower(Character.wardrobe_description).like(
                                search_term
                            ),
                            func.lower(Character.makeup_description).like(search_term),
                            func.lower(Character.hair_description).like(search_term),
                            func.lower(Character.profession).like(search_term),
                            func.lower(Character.emotional_state).like(search_term),
                        ),
                    )
                )
                .limit(limit)
            )
            characters = char_result.scalars().all()
            if characters:
                results["results"]["characters"] = [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "archetype": c.archetype,
                        "age_range": c.age_range,
                        "gender_presentation": c.gender_presentation,
                        "is_simulated": c.is_simulated == "true",
                        "relevance": (
                            "high"
                            if query.lower() in (c.name or "").lower()
                            else "medium"
                        ),
                    }
                    for c in characters
                ]
                results["total_results"] += len(characters)

        # 3. Buscar em Campaigns
        if "campaigns" in entity_types:
            camp_result = await db.execute(
                select(Campaign)
                .where(
                    and_(
                        Campaign.profile_id == profile_id,
                        Campaign.tenant_id == tenant_id,
                        Campaign.status == "active",
                        or_(
                            func.lower(Campaign.name).like(search_term),
                            func.lower(Campaign.brand).like(search_term),
                            func.lower(Campaign.agency).like(search_term),
                            func.lower(Campaign.description).like(search_term),
                            func.lower(Campaign.campaign_type).like(search_term),
                        ),
                    )
                )
                .order_by(desc(Campaign.start_date))
                .limit(limit)
            )
            campaigns = camp_result.scalars().all()
            if campaigns:
                results["results"]["campaigns"] = [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "brand": c.brand,
                        "agency": c.agency,
                        "campaign_type": c.campaign_type,
                        "start_date": (
                            c.start_date.isoformat() if c.start_date else None
                        ),
                        "relevance": (
                            "high"
                            if query.lower() in (c.name or "").lower()
                            else "medium"
                        ),
                    }
                    for c in campaigns
                ]
                results["total_results"] += len(campaigns)

        # 4. Buscar em Feedbacks
        if "feedbacks" in entity_types:
            fb_result = await db.execute(
                select(CareerFeedback)
                .where(
                    and_(
                        CareerFeedback.profile_id == profile_id,
                        CareerFeedback.tenant_id == tenant_id,
                        CareerFeedback.status == "active",
                        or_(
                            func.lower(CareerFeedback.feedback_text).like(search_term),
                            func.lower(CareerFeedback.source_name).like(search_term),
                            func.lower(CareerFeedback.feedback_type).like(search_term),
                        ),
                    )
                )
                .order_by(desc(CareerFeedback.created_at))
                .limit(limit)
            )
            feedbacks = fb_result.scalars().all()
            if feedbacks:
                results["results"]["feedbacks"] = [
                    {
                        "id": str(f.id),
                        "source": f.source,
                        "source_name": f.source_name,
                        "feedback_type": f.feedback_type,
                        "feedback_text": f.feedback_text,
                        "rating": float(f.rating) if f.rating else None,
                        "is_positive": f.is_positive == "true",
                        "relevance": (
                            "high"
                            if query.lower() in (f.feedback_text or "").lower()
                            else "medium"
                        ),
                    }
                    for f in feedbacks
                ]
                results["total_results"] += len(feedbacks)

        # 5. Buscar em AppearanceRecords
        if "appearances" in entity_types:
            app_result = await db.execute(
                select(AppearanceRecord)
                .where(
                    and_(
                        AppearanceRecord.profile_id == profile_id,
                        AppearanceRecord.tenant_id == tenant_id,
                        AppearanceRecord.status == "active",
                        or_(
                            func.lower(AppearanceRecord.title).like(search_term),
                            func.lower(AppearanceRecord.description).like(search_term),
                            func.lower(AppearanceRecord.feedback).like(search_term),
                            func.lower(AppearanceRecord.record_type).like(search_term),
                        ),
                    )
                )
                .order_by(desc(AppearanceRecord.created_at))
                .limit(limit)
            )
            appearances = app_result.scalars().all()
            if appearances:
                results["results"]["appearances"] = [
                    {
                        "id": str(a.id),
                        "record_type": a.record_type,
                        "title": a.title,
                        "description": a.description,
                        "feedback": a.feedback,
                        "rating": float(a.rating) if a.rating else None,
                        "tags": a.tags,
                        "relevance": (
                            "high"
                            if query.lower() in (a.title or "").lower()
                            else "medium"
                        ),
                    }
                    for a in appearances
                ]
                results["total_results"] += len(appearances)

        logger.info(
            f"searchMemory: query='{query}' found {results['total_results']} results for profile {profile_id}"
        )
        return results

    async def getTalentContext(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        include_private: bool = False,
    ) -> Dict[str, Any]:
        """
        Monta o contexto completo do talento para uso pelos agentes.

        Retorna um dicionario estruturado com toda a memoria de carreira,
        preferencias, performance e relacoes do talento.
        """
        # 1. Dados basicos do perfil
        profile_result = await db.execute(
            select(Profile).where(
                and_(Profile.id == profile_id, Profile.tenant_id == tenant_id)
            )
        )
        profile = profile_result.scalar_one_or_none()

        context = {
            "profile_id": str(profile_id),
            "generated_at": datetime.utcnow().isoformat(),
            "profile": None,
            "career_summary": {},
            "experiences": [],
            "characters": [],
            "campaigns": [],
            "agencies": [],
            "feedbacks": {"positive": [], "negative": [], "summary": {}},
            "appearances": {"approved": [], "rejected": [], "simulated": []},
            "style_preferences": [],
            "content_performance": [],
            "talent_graph": {},
        }

        if profile:
            context["profile"] = {
                "full_name": profile.full_name,
                "artistic_name": profile.artistic_name,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": float(profile.weight_kg) if profile.weight_kg else None,
                "eye_color": profile.eye_color,
                "hair_color": profile.hair_color,
                "skin_tone": profile.skin_tone,
                "body_type": profile.body_type,
                "languages": profile.languages or [],
                "skills": profile.skills or [],
                "experience_years": profile.experience_years,
                "bio": profile.bio,
                "instagram": profile.instagram,
                "portfolio_url": profile.portfolio_url,
            }

        # 2. Experiencias profissionais
        experiences = await self.get_experiences(db, profile_id, tenant_id, limit=50)
        context["experiences"] = [
            {
                "id": str(e.id),
                "title": e.title,
                "company": e.company,
                "project_name": e.project_name,
                "role": e.role,
                "character_name": e.character_name,
                "production_type": e.production_type,
                "director": e.director,
                "agency": e.agency,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "location": e.location,
                "description": e.description,
                "skills_used": e.skills_used or [],
                "is_featured": e.is_featured == "true",
            }
            for e in experiences
        ]

        # 3. Personagens
        characters = await self.get_characters(
            db, profile_id, tenant_id, include_simulated=True
        )
        context["characters"] = [
            {
                "id": str(c.id),
                "name": c.name,
                "archetype": c.archetype,
                "age_range": c.age_range,
                "gender_presentation": c.gender_presentation,
                "physical_description": c.physical_description,
                "personality_traits": c.personality_traits or [],
                "wardrobe_description": c.wardrobe_description,
                "makeup_description": c.makeup_description,
                "hair_description": c.hair_description,
                "profession": c.profession,
                "social_status": c.social_status,
                "emotional_state": c.emotional_state,
                "is_simulated": c.is_simulated == "true",
                "simulation_prompt": c.simulation_prompt if include_private else None,
            }
            for c in characters
        ]

        # 4. Campanhas
        campaigns = await self.get_campaigns(db, profile_id, tenant_id)
        context["campaigns"] = [
            {
                "id": str(c.id),
                "name": c.name,
                "brand": c.brand,
                "agency": c.agency,
                "campaign_type": c.campaign_type,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "description": c.description,
                "deliverables": c.deliverables or [],
                "results": c.results or {},
            }
            for c in campaigns
        ]

        # 5. Agencias e contatos
        agency_contacts_result = await db.execute(
            select(AgencyContact, Agency)
            .join(Agency, AgencyContact.agency_id == Agency.id)
            .where(
                and_(
                    AgencyContact.profile_id == profile_id,
                    AgencyContact.tenant_id == tenant_id,
                    AgencyContact.status == "active",
                )
            )
        )
        agency_contacts = agency_contacts_result.all()
        context["agencies"] = [
            {
                "contact_id": str(ac.id),
                "agency_id": str(a.id),
                "agency_name": a.name,
                "agency_type": a.type,
                "contact_type": ac.contact_type,
                "contract_type": ac.contract_type,
                "commission_rate": (
                    float(ac.commission_rate) if ac.commission_rate else None
                ),
                "start_date": ac.start_date.isoformat() if ac.start_date else None,
                "city": a.city,
                "country": a.country,
                "specialties": a.specialties or [],
            }
            for ac, a in agency_contacts
        ]

        # 6. Feedbacks
        all_feedbacks = await self.get_feedbacks(db, profile_id, tenant_id)
        positive_feedbacks = [f for f in all_feedbacks if f.is_positive == "true"]
        negative_feedbacks = [f for f in all_feedbacks if f.is_positive == "false"]

        context["feedbacks"]["positive"] = [
            {
                "id": str(f.id),
                "source": f.source,
                "source_name": f.source_name,
                "feedback_type": f.feedback_type,
                "feedback_text": f.feedback_text,
                "rating": float(f.rating) if f.rating else None,
            }
            for f in positive_feedbacks[:10]
        ]
        context["feedbacks"]["negative"] = [
            {
                "id": str(f.id),
                "source": f.source,
                "source_name": f.source_name,
                "feedback_type": f.feedback_type,
                "feedback_text": f.feedback_text,
                "rating": float(f.rating) if f.rating else None,
            }
            for f in negative_feedbacks[:10]
        ]

        # Sumario de feedbacks
        if all_feedbacks:
            avg_rating = (
                sum(float(f.rating) for f in all_feedbacks if f.rating)
                / len([f for f in all_feedbacks if f.rating])
                if [f for f in all_feedbacks if f.rating]
                else 0
            )
            context["feedbacks"]["summary"] = {
                "total_count": len(all_feedbacks),
                "positive_count": len(positive_feedbacks),
                "negative_count": len(negative_feedbacks),
                "average_rating": round(avg_rating, 2),
                "positive_ratio": (
                    round(len(positive_feedbacks) / len(all_feedbacks), 2)
                    if all_feedbacks
                    else 0
                ),
            }

        # 7. Aparicoes
        approved = await self.get_approved_appearances(db, profile_id, tenant_id)
        rejected = await self.get_rejected_appearances(db, profile_id, tenant_id)

        context["appearances"]["approved"] = [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "feedback": a.feedback,
                "rating": float(a.rating) if a.rating else None,
                "tags": a.tags or [],
            }
            for a in approved[:20]
        ]
        context["appearances"]["rejected"] = [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "feedback": a.feedback,
                "rating": float(a.rating) if a.rating else None,
                "tags": a.tags or [],
            }
            for a in rejected[:20]
        ]

        # 8. Preferencias de estilo
        style_prefs = await self.get_style_preferences(db, profile_id, tenant_id)
        context["style_preferences"] = [
            {
                "id": str(s.id),
                "preference_type": s.preference_type,
                "preference_value": s.preference_value,
                "context": s.context,
                "usage_count": s.usage_count,
                "success_rate": float(s.success_rate) if s.success_rate else None,
            }
            for s in style_prefs
        ]

        # 9. Performance de conteudo
        performances = await self.get_content_performances(db, profile_id, tenant_id)
        context["content_performance"] = [
            {
                "id": str(p.id),
                "platform": p.platform,
                "metrics": p.metrics or {},
                "engagement_rate": (
                    float(p.engagement_rate) if p.engagement_rate else None
                ),
                "best_performing": p.best_performing == "true",
                "audience_demographics": p.audience_demographics or {},
                "peak_hours": p.peak_hours or [],
            }
            for p in performances[:20]
        ]

        # 10. Career Summary / Talent Graph
        production_types = {}
        for e in experiences:
            pt = e.production_type or "unknown"
            production_types[pt] = production_types.get(pt, 0) + 1

        top_skills = {}
        for e in experiences:
            for skill in e.skills_used or []:
                top_skills[skill] = top_skills.get(skill, 0) + 1

        context["career_summary"] = {
            "total_experiences": len(experiences),
            "total_characters": len(characters),
            "total_campaigns": len(campaigns),
            "total_agencies": len(agency_contacts),
            "total_approved_appearances": len(approved),
            "total_rejected_appearances": len(rejected),
            "production_types_breakdown": production_types,
            "top_skills": dict(
                sorted(top_skills.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "years_active": self._calculate_years_active(experiences),
            "featured_works": len([e for e in experiences if e.is_featured == "true"]),
        }

        # Talent Graph — relacoes
        context["talent_graph"] = {
            "frequent_directors": list(
                set(e.director for e in experiences if e.director)
            )[:10],
            "frequent_agencies": list(set(e.agency for e in experiences if e.agency))[
                :10
            ],
            "character_archetypes": list(
                set(c.archetype for c in characters if c.archetype)
            )[:10],
            "worked_locations": list(
                set(e.location for e in experiences if e.location)
            )[:10],
        }

        logger.info(
            f"getTalentContext: generated full context for profile {profile_id}"
        )
        return context

    async def getRelevantHistory(
        self,
        db: AsyncSession,
        profile_id: UUID,
        tenant_id: UUID,
        context: str,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Filtra o historico do talento relevante para um contexto especifico.

        Exemplos de contexto:
        - "casting": retorna experiencias similares, feedbacks de castings, aparicoes aprovadas
        - "character": retorna personagens similares, experiencias com personagens
        - "campaign": retorna campanhas similares, performance de conteudo
        - "content": retorna preferencias de estilo, performance, melhores posts
        """
        keywords = keywords or []
        keywords_lower = [k.lower() for k in keywords]

        result = {
            "context": context,
            "profile_id": str(profile_id),
            "keywords": keywords,
            "relevant_items": [],
            "insights": [],
        }

        if context == "casting":
            experiences = await self.get_experiences(
                db, profile_id, tenant_id, limit=limit
            )
            for exp in experiences:
                relevance_score = 0
                if keywords_lower:
                    for kw in keywords_lower:
                        if kw in (exp.title or "").lower():
                            relevance_score += 3
                        if kw in (exp.production_type or "").lower():
                            relevance_score += 2
                        if kw in (exp.role or "").lower():
                            relevance_score += 2
                        if kw in (exp.description or "").lower():
                            relevance_score += 1

                if relevance_score > 0 or not keywords_lower:
                    result["relevant_items"].append(
                        {
                            "type": "experience",
                            "id": str(exp.id),
                            "title": exp.title,
                            "role": exp.role,
                            "production_type": exp.production_type,
                            "relevance_score": relevance_score,
                            "reason": (
                                f"Experiencia em {exp.production_type}"
                                if exp.production_type
                                else "Experiencia profissional"
                            ),
                        }
                    )

            feedbacks = await self.get_feedbacks(db, profile_id, tenant_id)
            for fb in feedbacks:
                if fb.feedback_type in ["appearance", "performance", "professionalism"]:
                    result["relevant_items"].append(
                        {
                            "type": "feedback",
                            "id": str(fb.id),
                            "source": fb.source_name,
                            "feedback_type": fb.feedback_type,
                            "is_positive": fb.is_positive == "true",
                            "relevance_score": 2 if fb.is_positive == "true" else 1,
                            "reason": f"Feedback de {fb.feedback_type}",
                        }
                    )

            approved = await self.get_approved_appearances(db, profile_id, tenant_id)
            for app in approved[:5]:
                result["relevant_items"].append(
                    {
                        "type": "approved_appearance",
                        "id": str(app.id),
                        "title": app.title,
                        "tags": app.tags or [],
                        "relevance_score": 2,
                        "reason": "Aparicao aprovada anteriormente",
                    }
                )

            result["insights"] = [
                f"Talento tem {len(experiences)} experiencias profissionais",
                f"Talento tem {len(approved)} aparicoes aprovadas",
                f"Talento tem {len([f for f in feedbacks if f.is_positive == 'true'])} feedbacks positivos",
            ]

        elif context == "character":
            characters = await self.get_characters(
                db, profile_id, tenant_id, include_simulated=True
            )
            for char in characters:
                relevance_score = 0
                if keywords_lower:
                    for kw in keywords_lower:
                        if kw in (char.name or "").lower():
                            relevance_score += 3
                        if kw in (char.archetype or "").lower():
                            relevance_score += 2
                        if kw in (char.physical_description or "").lower():
                            relevance_score += 1
                        if kw in (char.profession or "").lower():
                            relevance_score += 1

                if relevance_score > 0 or not keywords_lower:
                    result["relevant_items"].append(
                        {
                            "type": "character",
                            "id": str(char.id),
                            "name": char.name,
                            "archetype": char.archetype,
                            "is_simulated": char.is_simulated == "true",
                            "relevance_score": relevance_score,
                            "reason": (
                                f"Personagem tipo {char.archetype}"
                                if char.archetype
                                else "Personagem registrado"
                            ),
                        }
                    )

            experiences = await self.get_experiences(
                db, profile_id, tenant_id, limit=limit
            )
            for exp in experiences:
                if exp.character_name:
                    result["relevant_items"].append(
                        {
                            "type": "experience_with_character",
                            "id": str(exp.id),
                            "title": exp.title,
                            "character_name": exp.character_name,
                            "relevance_score": 2,
                            "reason": f"Interpretou {exp.character_name}",
                        }
                    )

            result["insights"] = [
                f"Talento tem {len(characters)} personagens registrados",
                f"Talento tem {len([c for c in characters if c.is_simulated == 'true'])} personagens simulados",
            ]

        elif context == "campaign":
            campaigns = await self.get_campaigns(db, profile_id, tenant_id)
            for camp in campaigns:
                relevance_score = 0
                if keywords_lower:
                    for kw in keywords_lower:
                        if kw in (camp.name or "").lower():
                            relevance_score += 3
                        if kw in (camp.brand or "").lower():
                            relevance_score += 2
                        if kw in (camp.campaign_type or "").lower():
                            relevance_score += 2

                if relevance_score > 0 or not keywords_lower:
                    result["relevant_items"].append(
                        {
                            "type": "campaign",
                            "id": str(camp.id),
                            "name": camp.name,
                            "brand": camp.brand,
                            "campaign_type": camp.campaign_type,
                            "relevance_score": relevance_score,
                            "reason": (
                                f"Campanha {camp.campaign_type}"
                                if camp.campaign_type
                                else "Campanha registrada"
                            ),
                        }
                    )

            performances = await self.get_content_performances(
                db, profile_id, tenant_id, best_performing_only=True
            )
            for perf in performances[:5]:
                result["relevant_items"].append(
                    {
                        "type": "content_performance",
                        "id": str(perf.id),
                        "platform": perf.platform,
                        "engagement_rate": (
                            float(perf.engagement_rate)
                            if perf.engagement_rate
                            else None
                        ),
                        "relevance_score": 3,
                        "reason": "Melhor performance de conteudo",
                    }
                )

            result["insights"] = [
                f"Talento participou de {len(campaigns)} campanhas",
                f"Talento tem {len(performances)} conteudos de alta performance",
            ]

        elif context == "content":
            style_prefs = await self.get_style_preferences(db, profile_id, tenant_id)
            for pref in style_prefs:
                result["relevant_items"].append(
                    {
                        "type": "style_preference",
                        "id": str(pref.id),
                        "preference_type": pref.preference_type,
                        "preference_value": pref.preference_value,
                        "usage_count": pref.usage_count,
                        "success_rate": (
                            float(pref.success_rate) if pref.success_rate else None
                        ),
                        "relevance_score": pref.usage_count or 1,
                        "reason": f"Preferencia de {pref.preference_type} (usada {pref.usage_count}x)",
                    }
                )

            performances = await self.get_content_performances(
                db, profile_id, tenant_id
            )
            for perf in performances[:10]:
                result["relevant_items"].append(
                    {
                        "type": "content_performance",
                        "id": str(perf.id),
                        "platform": perf.platform,
                        "metrics": perf.metrics,
                        "engagement_rate": (
                            float(perf.engagement_rate)
                            if perf.engagement_rate
                            else None
                        ),
                        "relevance_score": int((perf.engagement_rate or 0) * 100),
                        "reason": (
                            f"Engagement rate: {perf.engagement_rate}%"
                            if perf.engagement_rate
                            else "Performance registrada"
                        ),
                    }
                )

            result["insights"] = [
                f"Talento tem {len(style_prefs)} preferencias de estilo registradas",
                f"Talento tem {len(performances)} registros de performance",
            ]

        # Ordenar por relevance_score
        result["relevant_items"].sort(
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )
        result["relevant_items"] = result["relevant_items"][:limit]

        logger.info(
            f"getRelevantHistory: context='{context}' found {len(result['relevant_items'])} items for profile {profile_id}"
        )
        return result

    def _calculate_years_active(self, experiences: List[ProfessionalExperience]) -> int:
        """Calcula anos de atividade profissional."""
        if not experiences:
            return 0
        dates = []
        for e in experiences:
            if e.start_date:
                dates.append(e.start_date)
            if e.end_date:
                dates.append(e.end_date)
        if not dates:
            return 0
        min_date = min(dates)
        max_date = max(dates)
        return max(0, (max_date - min_date).days // 365)

    # ========== METODOS PADRONIZADOS V0.2 ==========

    async def remember(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        memory_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Metodo generico para registrar qualquer tipo de memoria no Talent Graph.

        Args:
            memory_type: Tipo de memoria - 'experience', 'character', 'campaign',
                        'feedback', 'appearance', 'style_preference', 'content_performance'
            data: Dados especificos do tipo de memoria
        """
        memory_type = memory_type.lower()

        if memory_type == "experience":
            result = await self.create_experience(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "experience", "id": str(result.id), "created": True}

        elif memory_type == "character":
            result = await self.create_character(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "character", "id": str(result.id), "created": True}

        elif memory_type == "campaign":
            result = await self.create_campaign(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "campaign", "id": str(result.id), "created": True}

        elif memory_type == "feedback":
            result = await self.create_feedback(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "feedback", "id": str(result.id), "created": True}

        elif memory_type == "appearance":
            result = await self.create_appearance_record(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "appearance", "id": str(result.id), "created": True}

        elif memory_type == "style_preference":
            result = await self.create_style_preference(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {"type": "style_preference", "id": str(result.id), "created": True}

        elif memory_type == "content_performance":
            result = await self.create_content_performance(
                db=db, tenant_id=tenant_id, profile_id=profile_id, **data
            )
            return {
                "type": "content_performance",
                "id": str(result.id),
                "created": True,
            }

        else:
            raise ValueError(f"Unknown memory_type: {memory_type}")

    async def registerProfessionalResult(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        profile_id: UUID,
        result_type: str,
        casting_id: Optional[UUID] = None,
        experience_id: Optional[UUID] = None,
        outcome: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Registra o resultado de uma acao profissional no Talent Graph.

        Fluxo: CASTING -> APPLICATION -> RESULT -> MEMORY
        """
        details = details or {}

        if result_type == "job_completed" and experience_id is None:
            experience = await self.create_experience(
                db=db,
                tenant_id=tenant_id,
                profile_id=profile_id,
                title=details.get("title", "Trabalho realizado"),
                company=details.get("company"),
                project_name=details.get("project_name"),
                role=details.get("role"),
                character_name=details.get("character_name"),
                production_type=details.get("production_type"),
                director=details.get("director"),
                agency=details.get("agency"),
                start_date=details.get("start_date"),
                end_date=details.get("end_date"),
                location=details.get("location"),
                description=details.get("description"),
                skills_used=details.get("skills_used", []),
                photos_used=details.get("photos_used", []),
                video_url=details.get("video_url"),
                is_featured=details.get("is_featured", False),
                metadata={"result_type": result_type, "outcome": outcome, **details},
            )
            experience_id = experience.id

        if outcome in ["success", "rejection"]:
            await self.create_feedback(
                db=db,
                tenant_id=tenant_id,
                profile_id=profile_id,
                source="system",
                source_name="Vision Career Memory",
                feedback_type="result",
                feedback_text=details.get("feedback_text", f"Resultado: {outcome}"),
                rating=details.get("rating"),
                related_experience_id=experience_id,
                related_casting_id=casting_id,
                is_positive=(outcome == "success"),
                action_taken=details.get("action_taken"),
                metadata={
                    "result_type": result_type,
                    "outcome": outcome,
                    "details": details,
                },
            )

        await emit_event(
            event_type=VisionEventType.AI_TASK_COMPLETED,
            payload={
                "type": "professional_result_registered",
                "profile_id": str(profile_id),
                "result_type": result_type,
                "outcome": outcome,
                "experience_id": str(experience_id) if experience_id else None,
            },
        )

        logger.info(
            f"registerProfessionalResult: {result_type} -> {outcome} for profile {profile_id}"
        )

        return {
            "registered": True,
            "result_type": result_type,
            "outcome": outcome,
            "experience_id": str(experience_id) if experience_id else None,
            "casting_id": str(casting_id) if casting_id else None,
        }
