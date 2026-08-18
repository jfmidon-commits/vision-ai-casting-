"""
Testes para Etapas 1-5 do Vision Ecosystem v0.2.

Coverage:
- Etapa 1: CareerMemory (remember, registerProfessionalResult)
- Etapa 2: Digital Twin Versioning
- Etapa 3: Identity/Appearance/Character separation
- Etapa 4: Character Specification Engine
- Etapa 5: Identity Preservation Service
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ========== ETAPA 1: CAREER MEMORY ==========

class TestCareerMemoryRemember:
    """Testes para CareerMemoryService.remember() e registerProfessionalResult()."""

    @pytest.fixture
    def career_service(self):
        from app.memory.career_memory_service import CareerMemoryService
        return CareerMemoryService()

    @pytest.mark.asyncio
    async def test_remember_experience(self, career_service):
        """Testa remember com memory_type='experience'."""
        db = AsyncMock()
        tenant_id = uuid4()
        profile_id = uuid4()

        with patch.object(career_service, 'create_experience', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db,
                tenant_id=tenant_id,
                profile_id=profile_id,
                memory_type="experience",
                data={"title": "Test Job", "company": "Test Co"}
            )

            assert result["type"] == "experience"
            assert result["created"] is True
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_remember_character(self, career_service):
        """Testa remember com memory_type='character'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_character', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="character", data={"name": "Hero"}
            )

            assert result["type"] == "character"
            assert result["created"] is True

    @pytest.mark.asyncio
    async def test_remember_campaign(self, career_service):
        """Testa remember com memory_type='campaign'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_campaign', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="campaign", data={"name": "Summer Campaign"}
            )

            assert result["type"] == "campaign"

    @pytest.mark.asyncio
    async def test_remember_feedback(self, career_service):
        """Testa remember com memory_type='feedback'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_feedback', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="feedback", data={"feedback_text": "Great work"}
            )

            assert result["type"] == "feedback"

    @pytest.mark.asyncio
    async def test_remember_appearance(self, career_service):
        """Testa remember com memory_type='appearance'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_appearance_record', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="appearance", data={"record_type": "approved", "description": "New haircut"}
            )

            assert result["type"] == "appearance"

    @pytest.mark.asyncio
    async def test_remember_style_preference(self, career_service):
        """Testa remember com memory_type='style_preference'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_style_preference', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="style_preference", data={"category": "hair", "preference": "short"}
            )

            assert result["type"] == "style_preference"

    @pytest.mark.asyncio
    async def test_remember_content_performance(self, career_service):
        """Testa remember com memory_type='content_performance'."""
        db = AsyncMock()
        with patch.object(career_service, 'create_content_performance', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = MagicMock(id=uuid4())

            result = await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="content_performance", data={"platform": "instagram"}
            )

            assert result["type"] == "content_performance"

    @pytest.mark.asyncio
    async def test_remember_unknown_type(self, career_service):
        """Testa remember com tipo desconhecido."""
        db = AsyncMock()
        with pytest.raises(ValueError, match="Unknown memory_type"):
            await career_service.remember(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                memory_type="unknown", data={}
            )

    @pytest.mark.asyncio
    async def test_register_professional_result_success(self, career_service):
        """Testa registro de resultado profissional com sucesso."""
        db = AsyncMock()
        tenant_id = uuid4()
        profile_id = uuid4()

        with patch.object(career_service, 'create_experience', new_callable=AsyncMock) as mock_exp,              patch.object(career_service, 'create_feedback', new_callable=AsyncMock) as mock_fb:
            mock_exp.return_value = MagicMock(id=uuid4())

            result = await career_service.registerProfessionalResult(
                db=db,
                tenant_id=tenant_id,
                profile_id=profile_id,
                result_type="job_completed",
                outcome="success",
                details={"title": "Commercial", "company": "Agency X"}
            )

            assert result["registered"] is True
            assert result["outcome"] == "success"
            assert result["result_type"] == "job_completed"

    @pytest.mark.asyncio
    async def test_register_professional_result_rejection(self, career_service):
        """Testa registro de resultado com rejeicao."""
        db = AsyncMock()
        with patch.object(career_service, 'create_feedback', new_callable=AsyncMock) as mock_fb:
            result = await career_service.registerProfessionalResult(
                db=db, tenant_id=uuid4(), profile_id=uuid4(),
                result_type="casting_applied",
                outcome="rejection",
                details={"feedback_text": "Not the right fit"}
            )

            assert result["outcome"] == "rejection"


# ========== ETAPA 2: DIGITAL TWIN VERSIONING ==========

class TestDigitalTwinVersioning:
    """Testes para DigitalTwinService com versionamento v0.2."""

    @pytest.fixture
    def dt_service(self):
        from app.modules.digital_twin.service import DigitalTwinService
        return DigitalTwinService()

    @pytest.mark.asyncio
    async def test_create_version(self, dt_service):
        """Testa criacao de versao do Digital Twin."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch.object(dt_service, 'get_assets_by_profile', new_callable=AsyncMock) as mock_assets:
            mock_assets.return_value = []

            result = await dt_service.create_version(
                db=db,
                tenant_id=uuid4(),
                profile_id=uuid4(),
                version_name="Summer 2026",
                created_reason="new_photoshoot"
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_versions_by_profile(self, dt_service):
        """Testa listagem de versoes."""
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await dt_service.get_versions_by_profile(db, uuid4(), uuid4())
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_active_version(self, dt_service):
        """Testa busca de versao ativa."""
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await dt_service.get_active_version(db, uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_archive_version(self, dt_service):
        """Testa arquivamento de versao."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()

        mock_version = MagicMock()
        mock_version.status = "active"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_version
        db.execute.return_value = mock_result

        result = await dt_service.archive_version(db, uuid4(), uuid4())
        assert result.status == "archived"

    @pytest.mark.asyncio
    async def test_compare_versions(self, dt_service):
        """Testa comparacao de versoes."""
        db = AsyncMock()
        v1_id = uuid4()
        v2_id = uuid4()

        mock_v1 = MagicMock()
        mock_v1.version_number = 1
        mock_v1.version_name = "V1"
        mock_v1.created_at = datetime.utcnow()
        mock_v1.appearance_state_snapshot = {"hair": "short"}
        mock_v1.identity_traits_snapshot = {"height": "175"}
        mock_v1.assets_summary = {"total": 5}

        mock_v2 = MagicMock()
        mock_v2.version_number = 2
        mock_v2.version_name = "V2"
        mock_v2.created_at = datetime.utcnow()
        mock_v2.appearance_state_snapshot = {"hair": "long"}
        mock_v2.identity_traits_snapshot = {"height": "175"}
        mock_v2.assets_summary = {"total": 8}

        call_count = [0]
        def mock_execute(query):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.scalar_one_or_none.return_value = mock_v1
            else:
                mock_result.scalar_one_or_none.return_value = mock_v2
            return mock_result

        db.execute = mock_execute

        result = await dt_service.compare_versions(db, v1_id, v2_id, uuid4())

        assert "appearance_changes" in result
        assert result["identity_preserved"] is True
        assert "assets_summary_comparison" in result

    def test_compare_dicts(self, dt_service):
        """Testa metodo utilitario de comparacao de dicts."""
        d1 = {"hair": "short", "beard": "none"}
        d2 = {"hair": "long", "beard": "none", "new_key": "value"}

        result = dt_service._compare_dicts(d1, d2)

        assert "hair" in result
        assert result["hair"] == {"from": "short", "to": "long"}
        assert "new_key" in result


# ========== ETAPA 3: IDENTITY / APPEARANCE / CHARACTER ==========

class TestIdentityService:
    """Testes para IdentityService - separacao Identity/Appearance/Character."""

    @pytest.fixture
    def identity_service(self):
        from app.services.identity_service import IdentityService
        return IdentityService()

    @pytest.mark.asyncio
    async def test_register_identity_trait(self, identity_service):
        """Testa registro de trait identitario."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await identity_service.register_identity_trait(
            db=db,
            tenant_id=uuid4(),
            profile_id=uuid4(),
            trait_category="facial_structure",
            trait_name="face_shape",
            trait_value="oval",
            confidence=0.95,
            verified_by="Dr. Silva"
        )

        assert result is not None
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_identity_traits(self, identity_service):
        """Testa busca de traits."""
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_trait = MagicMock()
        mock_trait.trait_category = "facial_structure"
        mock_trait.trait_name = "face_shape"
        mock_trait.trait_value = "oval"
        mock_trait.confidence = 0.95
        mock_trait.verified_by = "Dr. Silva"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_trait]
        db.execute.return_value = mock_result

        result = await identity_service.get_identity_traits(db, uuid4(), uuid4())
        assert len(result) == 1
        assert result[0].trait_name == "face_shape"

    @pytest.mark.asyncio
    async def test_get_identity_summary(self, identity_service):
        """Testa resumo de identidade."""
        db = AsyncMock()

        mock_trait1 = MagicMock()
        mock_trait1.trait_category = "facial_structure"
        mock_trait1.trait_name = "face_shape"
        mock_trait1.trait_value = "oval"
        mock_trait1.confidence = 0.95
        mock_trait1.verified_by = "Dr. Silva"

        mock_trait2 = MagicMock()
        mock_trait2.trait_category = "eye_characteristics"
        mock_trait2.trait_name = "eye_color"
        mock_trait2.trait_value = "brown"
        mock_trait2.confidence = 1.0
        mock_trait2.verified_by = None

        with patch.object(identity_service, 'get_identity_traits', new_callable=AsyncMock) as mock_traits:
            mock_traits.return_value = [mock_trait1, mock_trait2]

            result = await identity_service.get_identity_summary(db, uuid4(), uuid4())

            assert "facial_structure" in result
            assert result["facial_structure"]["face_shape"]["value"] == "oval"
            assert result["facial_structure"]["face_shape"]["verified"] is True
            assert result["eye_characteristics"]["eye_color"]["verified"] is False

    @pytest.mark.asyncio
    async def test_update_appearance(self, identity_service):
        """Testa atualizacao de aparencia."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await identity_service.update_appearance(
            db=db,
            tenant_id=uuid4(),
            profile_id=uuid4(),
            category="hair",
            attribute="length",
            new_value="short",
            changed_reason="new_photoshoot"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_current_appearance(self, identity_service):
        """Testa busca de aparencia atual."""
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_state = MagicMock()
        mock_state.category = "hair"
        mock_state.attribute = "length"
        mock_state.current_value = "short"
        mock_state.previous_value = "long"
        mock_state.changed_at = datetime.utcnow()
        mock_state.changed_reason = "new_photoshoot"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_state]
        db.execute.return_value = mock_result

        result = await identity_service.get_current_appearance(db, uuid4(), uuid4())

        assert "hair" in result
        assert result["hair"]["length"]["current_value"] == "short"
        assert result["hair"]["length"]["previous_value"] == "long"

    @pytest.mark.asyncio
    async def test_register_character_transformation(self, identity_service):
        """Testa registro de transformacao de personagem."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await identity_service.register_character_transformation(
            db=db,
            tenant_id=uuid4(),
            profile_id=uuid4(),
            character_id=uuid4(),
            transformation_type="wardrobe",
            attribute="suit_type",
            value="business_suit",
            simulation_prompt_fragment="dark suit, executive look"
        )

        assert result is not None
        assert result.is_simulated == "true"

    @pytest.mark.asyncio
    async def test_get_complete_profile_context(self, identity_service):
        """Testa contexto completo de perfil."""
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_transform = MagicMock()
        mock_transform.character_id = uuid4()
        mock_transform.transformation_type = "wardrobe"
        mock_transform.attribute = "suit_type"
        mock_transform.value = "business_suit"
        mock_transform.is_simulated = "true"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_transform]
        db.execute.return_value = mock_result

        with patch.object(identity_service, 'get_identity_summary', new_callable=AsyncMock) as mock_id,              patch.object(identity_service, 'get_current_appearance', new_callable=AsyncMock) as mock_app:
            mock_id.return_value = {"facial_structure": {"face_shape": {"value": "oval"}}}
            mock_app.return_value = {"hair": {"length": {"current_value": "short"}}}

            result = await identity_service.get_complete_profile_context(db, uuid4(), uuid4())

            assert "identity" in result
            assert "appearance" in result
            assert "character_transformations" in result
            assert result["separation_warning"] == "NUNCA confundir character_transformations com identity ou appearance"
            assert result["character_transformations"]["count"] == 1
            assert result["character_transformations"]["transformations"][0]["is_simulated"] is True


# ========== ETAPA 4: CHARACTER SPECIFICATION ENGINE ==========

class TestCharacterSpecificationEngine:
    """Testes para CharacterSpecificationEngine."""

    @pytest.fixture
    def engine(self):
        from app.engines.character_specification import CharacterSpecificationEngine
        return CharacterSpecificationEngine()

    @pytest.mark.asyncio
    async def test_parse_executive_request(self, engine):
        """Testa parsing de solicitacao de executivo."""
        spec = await engine.parse_request(
            "Mostre este talento como executivo, barba de tres dias, terno escuro e expressao seria"
        )

        assert spec.character.archetype == "executive"
        assert spec.character.expression == "serious"
        assert spec.appearance_changes.beard is not None
        assert spec.appearance_changes.beard["type"] == "stubble"
        assert spec.appearance_changes.beard["length_days"] == 3
        assert spec.wardrobe.type == "business_suit"
        assert spec.wardrobe.tone == "dark"
        assert spec.identity_preservation.face is True
        assert spec.identity_preservation.body_proportions is True
        assert spec.confidence > 0.5

    @pytest.mark.asyncio
    async def test_parse_athlete_request(self, engine):
        """Testa parsing de solicitacao de atleta."""
        spec = await engine.parse_request(
            "Transforme em atleta sorridente, roupa esportiva"
        )

        assert spec.character.archetype == "athlete"
        assert spec.character.expression == "happy"
        assert spec.wardrobe.type == "athletic"

    @pytest.mark.asyncio
    async def test_parse_villain_request(self, engine):
        """Testa parsing de solicitacao de vilao."""
        spec = await engine.parse_request(
            "Mostre como vilao intenso, barba longa, roupa escura"
        )

        assert spec.character.archetype == "villain"
        assert spec.character.expression == "intense"
        assert spec.appearance_changes.beard is not None
        assert spec.appearance_changes.beard["type"] == "long_beard"

    @pytest.mark.asyncio
    async def test_parse_doctor_request(self, engine):
        """Testa parsing de solicitacao de medico."""
        spec = await engine.parse_request(
            "Como medico neutro, jaleco branco, expressao seria"
        )

        assert spec.character.archetype == "doctor"
        assert spec.character.expression == "serious"
        assert spec.wardrobe.type == "uniform"
        assert spec.wardrobe.tone == "light"

    @pytest.mark.asyncio
    async def test_parse_generic_request(self, engine):
        """Testa parsing de solicitacao generica."""
        spec = await engine.parse_request(
            "Apenas uma foto normal"
        )

        assert spec.character.archetype == "generic"
        assert spec.character.expression == "neutral"
        assert spec.confidence >= 0.1

    @pytest.mark.asyncio
    async def test_parse_with_environment(self, engine):
        """Testa parsing com contexto de ambiente."""
        spec = await engine.parse_request(
            "Executivo em escritorio, luz natural, terno escuro"
        )

        assert spec.environment.setting == "office"
        assert spec.environment.lighting == "natural"

    @pytest.mark.asyncio
    async def test_parse_with_accessories(self, engine):
        """Testa parsing com acessorios."""
        spec = await engine.parse_request(
            "Executivo com oculos e relogio, terno escuro"
        )

        assert "oculos" in spec.wardrobe.accessories
        assert "relogio" in spec.wardrobe.accessories

    @pytest.mark.asyncio
    async def test_validate_specification_valid(self, engine):
        """Testa validacao de especificacao valida."""
        spec = await engine.parse_request("Executivo com barba")

        identity_traits = {
            "facial_structure": {"face_shape": "oval"},
            "physical_identifiers": {"height_cm": "175"}
        }

        validation = await engine.validate_specification(spec, identity_traits)

        assert validation["valid"] is True
        assert validation["identity_preserved"] is True
        assert len(validation["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_validate_specification_with_warnings(self, engine):
        """Testa validacao com warnings."""
        spec = await engine.parse_request("Executivo")

        # Forcar body changes com height
        spec.appearance_changes.body = {"height": "180cm"}

        identity_traits = {
            "physical_identifiers": {"height_cm": "175"}
        }

        validation = await engine.validate_specification(spec, identity_traits)

        assert validation["valid"] is False
        assert any("height" in w.lower() for w in validation["warnings"])

    def test_to_dict(self, engine):
        """Testa serializacao para dict."""
        import asyncio
        spec = asyncio.run(engine.parse_request(
            "Executivo, barba de tres dias, terno escuro"
        ))

        d = spec.to_dict()

        assert "character" in d
        assert "appearance_changes" in d
        assert "wardrobe" in d
        assert "identity_preservation" in d
        assert "environment" in d
        assert "raw_input" in d
        assert "confidence" in d
        assert d["character"]["archetype"] == "executive"


# ========== ETAPA 5: IDENTITY PRESERVATION SERVICE ==========

class TestIdentityPreservationService:
    """Testes para IdentityPreservationService."""

    @pytest.fixture
    def preservation_service(self):
        from app.services.identity_preservation import IdentityPreservationService, AssetOrigin
        return IdentityPreservationService(), AssetOrigin

    @pytest.mark.asyncio
    async def test_register_real_reference(self, preservation_service):
        """Testa registro de referencia real."""
        service, AssetOrigin = preservation_service
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch.object(service, '_log_asset_origin', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = MagicMock()

            result = await service.register_reference(
                db=db,
                tenant_id=uuid4(),
                profile_id=uuid4(),
                file_url="https://s3.amazonaws.com/bucket/photo.jpg",
                reference_type="face_frontal",
                origin=AssetOrigin.REAL,
                quality_score=0.95,
                is_primary=True
            )

            assert result is not None
            assert result.origin == "REAL"
            db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_simulated_reference(self, preservation_service):
        """Testa registro de referencia simulada."""
        service, AssetOrigin = preservation_service
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch.object(service, '_log_asset_origin', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = MagicMock()

            result = await service.register_reference(
                db=db,
                tenant_id=uuid4(),
                profile_id=uuid4(),
                file_url="https://s3.amazonaws.com/bucket/simulated.jpg",
                reference_type="character_simulation",
                origin=AssetOrigin.SIMULATED,
                quality_score=0.88
            )

            assert result.origin == "SIMULATED"

    @pytest.mark.asyncio
    async def test_get_identity_references(self, preservation_service):
        """Testa busca de referencias."""
        service, AssetOrigin = preservation_service
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_ref = MagicMock()
        mock_ref.origin = "REAL"
        mock_ref.reference_type = "face_frontal"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_ref]
        db.execute.return_value = mock_result

        result = await service.get_identity_references(db, uuid4(), uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_identity_references_by_origin(self, preservation_service):
        """Testa busca filtrada por origem."""
        service, AssetOrigin = preservation_service
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_ref = MagicMock()
        mock_ref.origin = "REAL"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_ref]
        db.execute.return_value = mock_result

        result = await service.get_identity_references(
            db, uuid4(), uuid4(), origin=AssetOrigin.REAL
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_validate_unknown_asset(self, preservation_service):
        """Testa validacao de asset sem registro."""
        service, _ = preservation_service
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await service.validate_asset_origin(db, uuid4(), uuid4())

        assert result["origin"] == "UNKNOWN"
        assert result["can_be_used_for_identity"] is False
        assert result["can_be_used_for_simulation"] is False

    @pytest.mark.asyncio
    async def test_validate_real_asset(self, preservation_service):
        """Testa validacao de asset real."""
        service, _ = preservation_service
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_log = MagicMock()
        mock_log.origin = "REAL"
        mock_log.is_saved_as_real = "false"
        mock_log.source_description = "Foto real"
        mock_log.generated_by = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_log
        db.execute.return_value = mock_result

        result = await service.validate_asset_origin(db, uuid4(), uuid4())

        assert result["origin"] == "REAL"
        assert result["can_be_used_for_identity"] is True
        assert result["can_be_used_for_simulation"] is True
        assert result["is_safe"] is True

    @pytest.mark.asyncio
    async def test_validate_ai_generated_asset(self, preservation_service):
        """Testa validacao de asset gerado por IA."""
        service, _ = preservation_service
        db = AsyncMock()
        db.execute = AsyncMock()

        mock_log = MagicMock()
        mock_log.origin = "AI_GENERATED"
        mock_log.is_saved_as_real = "false"
        mock_log.source_description = "Imagem IA"
        mock_log.generated_by = "OpenAI"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_log
        db.execute.return_value = mock_result

        result = await service.validate_asset_origin(db, uuid4(), uuid4())

        assert result["origin"] == "AI_GENERATED"
        assert result["can_be_used_for_identity"] is False
        assert result["can_be_used_for_simulation"] is True
        assert result["is_safe"] is False
        assert any("CRITICAL" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_prevent_confusion(self, preservation_service):
        """Testa prevencao de confusao de identidade."""
        service, _ = preservation_service
        db = AsyncMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()

        mock_log = MagicMock()
        mock_log.origin = "SIMULATED"
        mock_log.is_saved_as_real = "false"
        mock_log.warning_flags = []

        mock_asset = MagicMock()
        mock_asset._metadata = {"some": "data"}

        call_count = [0]
        def mock_execute(query):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] <= 2:  # validate_asset_origin calls
                mock_result.scalar_one_or_none.return_value = mock_log
            else:
                mock_result.scalar_one_or_none.return_value = mock_asset
            return mock_result

        db.execute = mock_execute

        result = await service.prevent_confusion(db, uuid4(), uuid4())

        assert result["is_protected"] is True
        assert any(a["action"] == "block_save_as_real" for a in result["actions_taken"])

    @pytest.mark.asyncio
    async def test_get_identity_preservation_set(self, preservation_service):
        """Testa conjunto completo de preservacao."""
        service, AssetOrigin = preservation_service
        db = AsyncMock()

        mock_primary = MagicMock()
        mock_primary.file_url = "https://s3.com/primary.jpg"
        mock_primary.reference_type = "face_frontal"
        mock_primary.quality_score = 0.95
        mock_primary.metadata = {}

        mock_real = MagicMock()
        mock_real.id = uuid4()
        mock_real.reference_type = "face_profile"
        mock_real.file_url = "https://s3.com/profile.jpg"
        mock_real.quality_score = 0.90

        with patch.object(service, 'get_primary_references', new_callable=AsyncMock) as mock_p,              patch.object(service, 'get_identity_references', new_callable=AsyncMock) as mock_r:
            mock_p.return_value = {"face_frontal": mock_primary}
            mock_r.side_effect = [[mock_real], []]  # REAL refs, then CURRENT refs

            result = await service.get_identity_preservation_set(db, uuid4(), uuid4())

            assert "primary_references" in result
            assert "real_references" in result
            assert "current_appearance_references" in result
            assert "usage_instructions" in result
            assert result["usage_instructions"]["forbidden"] == "NUNCA usar SIMULATED ou AI_GENERATED como referencia de identidade"


# ========== TESTES DE INTEGRACAO ==========

class TestIntegrationEtapas1a5:
    """Testes de integracao entre os novos modulos v0.2."""

    @pytest.mark.asyncio
    async def test_full_pipeline_identity_to_character(self):
        """Testa pipeline completo: Identity -> Appearance -> Character -> Preservation."""
        from app.services.identity_service import IdentityService
        from app.engines.character_specification import CharacterSpecificationEngine
        from app.services.identity_preservation import IdentityPreservationService, AssetOrigin

        identity_service = IdentityService()
        char_engine = CharacterSpecificationEngine()
        preservation_service = IdentityPreservationService()

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        tenant_id = uuid4()
        profile_id = uuid4()

        # 1. Registra trait identitario
        with patch.object(identity_service, 'register_identity_trait', new_callable=AsyncMock) as mock_trait:
            mock_trait.return_value = MagicMock(id=uuid4())

            trait = await identity_service.register_identity_trait(
                db, tenant_id, profile_id,
                "facial_structure", "face_shape", "oval",
                confidence=0.95, verified_by="Dr. Silva"
            )
            assert trait is not None

        # 2. Atualiza aparencia
        with patch.object(identity_service, 'update_appearance', new_callable=AsyncMock) as mock_app:
            mock_app.return_value = MagicMock(id=uuid4())

            appearance = await identity_service.update_appearance(
                db, tenant_id, profile_id,
                "hair", "length", "short", "new_photoshoot"
            )
            assert appearance is not None

        # 3. Cria especificacao de personagem
        spec = await char_engine.parse_request(
            "Mostre como executivo, barba de tres dias, terno escuro"
        )
        assert spec.character.archetype == "executive"
        assert spec.identity_preservation.face is True

        # 4. Registra referencia de preservacao
        with patch.object(preservation_service, 'register_reference', new_callable=AsyncMock) as mock_ref:
            mock_ref.return_value = MagicMock(id=uuid4(), origin="REAL")

            ref = await preservation_service.register_reference(
                db, tenant_id, profile_id,
                "https://s3.amazonaws.com/photo.jpg",
                "face_frontal", AssetOrigin.REAL,
                quality_score=0.95, is_primary=True
            )
            assert ref.origin == "REAL"

    @pytest.mark.asyncio
    async def test_character_specification_flow(self):
        """Testa fluxo completo de especificacao de personagem."""
        from app.engines.character_specification import CharacterSpecificationEngine

        engine = CharacterSpecificationEngine()

        # Entrada natural
        request = "Mostre este talento como executivo, barba de tres dias, terno escuro e expressao seria"

        # Parse
        spec = await engine.parse_request(request)

        # Validacao
        identity_traits = {
            "facial_structure": {"face_shape": "oval", "jaw_line": "defined"},
            "eye_characteristics": {"eye_color": "brown", "shape": "almond"},
            "physical_identifiers": {"height_cm": "175", "distinctive_features": ["beauty_mark"]}
        }

        validation = await engine.validate_specification(spec, identity_traits)

        # Asserts
        assert spec.character.archetype == "executive"
        assert spec.character.expression == "serious"
        assert spec.appearance_changes.beard["type"] == "stubble"
        assert spec.wardrobe.type == "business_suit"
        assert spec.wardrobe.tone == "dark"
        assert validation["valid"] is True
        assert validation["identity_preserved"] is True

        # Verificar serializacao
        spec_dict = spec.to_dict()
        assert spec_dict["character"]["archetype"] == "executive"
        assert "beard" in spec_dict["appearance_changes"]
        assert spec_dict["identity_preservation"]["face"] is True

    @pytest.mark.asyncio
    async def test_identity_separation_enforcement(self):
        """Testa que simulacoes NUNCA sao confundidas com reais."""
        from app.services.identity_service import IdentityService
        from app.services.identity_preservation import IdentityPreservationService, AssetOrigin

        identity_service = IdentityService()
        preservation_service = IdentityPreservationService()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        tenant_id = uuid4()
        profile_id = uuid4()
        character_id = uuid4()

        # 1. Registra transformacao de personagem
        transform = await identity_service.register_character_transformation(
            db, tenant_id, profile_id, character_id,
            "wardrobe", "suit_type", "business_suit",
            simulation_prompt_fragment="executive dark suit"
        )

        # 2. Verifica que is_simulated e sempre true
        assert transform.is_simulated == "true"

        # 3. Tenta validar como asset real (deve falhar)
        with patch.object(preservation_service, 'validate_asset_origin', new_callable=AsyncMock) as mock_val:
            mock_val.return_value = {
                "origin": "SIMULATED",
                "can_be_used_for_identity": False,
                "is_safe": False,
                "warnings": ["WARNING: Asset simulado"]
            }

            validation = await preservation_service.validate_asset_origin(
                db, uuid4(), tenant_id
            )

            assert validation["can_be_used_for_identity"] is False
            assert validation["is_safe"] is False
