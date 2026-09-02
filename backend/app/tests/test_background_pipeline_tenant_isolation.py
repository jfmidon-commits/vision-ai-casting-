"""Tenant-isolation tests for queries executed after the HTTP request ends."""

from types import SimpleNamespace

import pytest

from app.memory.career_memory_service import CareerMemoryService
from app.services.ai_service import AIService


class _Scalars:
    def all(self):
        return []


class _CareerResult:
    def scalars(self):
        return _Scalars()


class _CareerDB:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _CareerResult()


@pytest.mark.asyncio
async def test_experience_type_filter_is_tenant_scoped():
    db = _CareerDB()

    await CareerMemoryService().get_experiences_by_type(
        db=db,
        profile_id="profile-a",
        tenant_id="tenant-a",
        production_type="commercial",
    )

    sql = str(db.statements[0])
    assert "professional_experiences.profile_id" in sql
    assert "professional_experiences.tenant_id" in sql
    assert "professional_experiences.production_type" in sql


@pytest.mark.asyncio
async def test_character_archetype_filter_is_tenant_scoped():
    db = _CareerDB()

    await CareerMemoryService().get_character_by_archetype(
        db=db,
        profile_id="profile-a",
        tenant_id="tenant-a",
        archetype="hero",
    )

    sql = str(db.statements[0])
    assert "characters.profile_id" in sql
    assert "characters.tenant_id" in sql
    assert "characters.archetype" in sql


class _StopPipeline(Exception):
    pass


class _AnalysisResult:
    def __init__(self, analysis=None):
        self.analysis = analysis

    def scalar_one(self):
        if self.analysis is None:
            raise _StopPipeline
        return self.analysis


class _PhotoResult:
    def scalars(self):
        raise _StopPipeline


class _PipelineDB:
    def __init__(self, allow_analysis=False):
        self.allow_analysis = allow_analysis
        self.statements = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 1:
            analysis = SimpleNamespace(status="queued") if self.allow_analysis else None
            return _AnalysisResult(analysis)
        return _PhotoResult()

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_background_analysis_lookup_requires_tenant_and_photoshoot(monkeypatch):
    import app.database as database

    db = _PipelineDB()
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: db)

    with pytest.raises(_StopPipeline):
        await AIService.run_analysis(
            analysis_id="analysis-a",
            photoshoot_id="photoshoot-a",
            analysis_types=[],
            tenant_id="tenant-a",
        )

    sql = str(db.statements[0])
    assert "analyses.id" in sql
    assert "analyses.photoshoot_id" in sql
    assert "analyses.tenant_id" in sql


@pytest.mark.asyncio
async def test_background_photo_lookup_is_tenant_scoped(monkeypatch):
    import app.database as database

    db = _PipelineDB(allow_analysis=True)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: db)

    with pytest.raises(_StopPipeline):
        await AIService.run_analysis(
            analysis_id="analysis-a",
            photoshoot_id="photoshoot-a",
            analysis_types=[],
            tenant_id="tenant-a",
        )

    sql = str(db.statements[1])
    assert "photos.photoshoot_id" in sql
    assert "photos.tenant_id" in sql
