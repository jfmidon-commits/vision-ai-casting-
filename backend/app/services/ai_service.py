import asyncio
import os
import tempfile
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import httpx

from app.ai.branding.analyzer import BrandingAnalyzer
from app.ai.casting.analyzer import CastingAnalyzer
from app.ai.colorimetry.analyzer import ColorimetryAnalyzer
from app.ai.consolidator.consolidator import ResultConsolidator
from app.ai.expressions.analyzer import ExpressionAnalyzer
from app.ai.facial_analysis.analyzer import FacialAnalyzer
from app.ai.grooming.analyzer import GroomingAnalyzer
from app.ai.photogenic.analyzer import PhotogenicAnalyzer
from app.ai.preprocessing.preprocessor import ImagePreprocessor
from app.ai.visagism.analyzer import VisagismAnalyzer
from app.pipelines.visagism import RealVisagismPipeline
from app.pipelines.visagism.simulation import (
    NullHairSimulationProvider,
    OpenAIHairSimulationProvider,
)
from app.services.storage_service import StorageService


class AIService:
    @classmethod
    async def run_analysis(
        cls,
        analysis_id: str,
        photoshoot_id: str,
        analysis_types: List[str],
        tenant_id: str,
    ):
        from app.database import AsyncSessionLocal
        from app.models import Analysis, Photo
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one()
            analysis.status = "processing"
            await db.commit()

            start_time = time.time()
            result = await db.execute(
                select(Photo).where(Photo.photoshoot_id == photoshoot_id)
            )
            photos = result.scalars().all()
            photos_data = [
                {"id": str(p.id), "url": p.url, "angle": p.angle} for p in photos
            ]

            preprocessor = ImagePreprocessor()
            preprocessed = await preprocessor.process_batch(photos_data)

            parallel_results = {}
            if "facial" in analysis_types:
                parallel_results["facial_structure"] = await FacialAnalyzer().analyze(
                    preprocessed
                )
            if "expressions" in analysis_types:
                parallel_results["expressions"] = await ExpressionAnalyzer().analyze(
                    preprocessed
                )
            if "photogenic" in analysis_types:
                parallel_results["photogenic"] = await PhotogenicAnalyzer().analyze(
                    preprocessed
                )
            if "colorimetry" in analysis_types:
                parallel_results["colorimetry"] = await ColorimetryAnalyzer().analyze(
                    preprocessed
                )
            if "grooming" in analysis_types:
                parallel_results["grooming"] = await GroomingAnalyzer().analyze(
                    preprocessed
                )

            context = {"parallel_results": parallel_results}
            sequential_results = {}
            if "visagism" in analysis_types:
                sequential_results["visagism"] = await VisagismAnalyzer().analyze(
                    preprocessed, context
                )
            if "casting" in analysis_types:
                sequential_results["casting"] = await CastingAnalyzer().analyze(
                    preprocessed, context
                )
            if "branding" in analysis_types:
                sequential_results["branding"] = await BrandingAnalyzer().analyze(
                    preprocessed, context
                )

            all_results = {**parallel_results, **sequential_results}
            consolidated = await ResultConsolidator().consolidate(
                photos_data, all_results, tenant_id
            )
            processing_time = int((time.time() - start_time) * 1000)

            analysis.facial_structure = parallel_results.get("facial_structure")
            analysis.visagism = sequential_results.get("visagism")
            analysis.expressions = parallel_results.get("expressions")
            analysis.photogenic = parallel_results.get("photogenic")
            analysis.colorimetry = parallel_results.get("colorimetry")
            analysis.grooming = parallel_results.get("grooming")
            analysis.casting = sequential_results.get("casting")
            analysis.branding = sequential_results.get("branding")
            analysis.confidence_score = consolidated.get("confidence_score", 0.5)
            analysis.raw_results = all_results
            analysis.processing_time_ms = processing_time
            analysis.status = "completed"
            analysis.completed_at = datetime.utcnow()
            await db.commit()

    @classmethod
    async def run_full_visagism_analysis(
        cls,
        analysis_id: str,
        photoshoot_id: str,
        tenant_id: str,
        cut_limit: int = 5,
        generate_card: bool = True,
    ) -> None:
        """Execute the reproducible multi-photo visagism pipeline and persist it."""
        from app.database import AsyncSessionLocal
        from app.models import Analysis, Photo
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            analysis_result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis = analysis_result.scalar_one()
            analysis.status = "processing"
            await db.commit()
            started = time.time()

            try:
                photo_result = await db.execute(
                    select(Photo).where(
                        Photo.photoshoot_id == photoshoot_id,
                        Photo.tenant_id == tenant_id,
                    )
                )
                photos = list(photo_result.scalars().all())
                if not photos:
                    raise ValueError("photoshoot_has_no_photos")

                with tempfile.TemporaryDirectory(prefix="vision-visagism-") as temp_dir:
                    dataset_path = os.path.join(temp_dir, "dataset")
                    os.makedirs(dataset_path, exist_ok=True)
                    await cls._materialize_photos(photos, dataset_path)

                    card_path = (
                        os.path.join(temp_dir, "barber_card.png")
                        if generate_card
                        else None
                    )
                    manifest_path = os.path.join(temp_dir, "artifacts.json")
                    # Inject simulation provider based on API key availability
                    api_key = os.environ.get("OPENAI_API_KEY", "")
                    sim_provider = (
                        OpenAIHairSimulationProvider(api_key=api_key)
                        if api_key
                        else NullHairSimulationProvider()
                    )
                    pipeline = RealVisagismPipeline(simulation_provider=sim_provider)
                    runner = partial(
                        pipeline.run,
                        dataset_path,
                        cut_limit=cut_limit,
                        card_output_path=card_path,
                        include_report=True,
                        artifact_manifest_path=manifest_path,
                    )
                    pipeline_result = await asyncio.to_thread(runner)

                    card_url = None
                    if card_path and os.path.isfile(card_path):
                        card_key = f"visagism/{analysis_id}/barber_card.png"
                        card_url = await StorageService.upload_bytes(
                            Path(card_path).read_bytes(), card_key, "image/png"
                        )

                    manifest_url = None
                    if os.path.isfile(manifest_path):
                        manifest_key = f"visagism/{analysis_id}/artifacts.json"
                        manifest_url = await StorageService.upload_bytes(
                            Path(manifest_path).read_bytes(),
                            manifest_key,
                            "application/json",
                        )

                    # Upload simulation image if generated and validated
                    simulation_url = None
                    simulation_result = pipeline_result.get("simulation", {})
                    if simulation_result.get("available"):
                        sim_path = simulation_result.get("output_path")
                        if sim_path and os.path.isfile(sim_path):
                            sim_key = f"visagism/{analysis_id}/simulation.png"
                            simulation_url = await StorageService.upload_bytes(
                                Path(sim_path).read_bytes(), sim_key, "image/png"
                            )

                    public_result = cls._build_full_visagism_payload(
                        analysis_id,
                        photoshoot_id,
                        pipeline_result,
                        card_url,
                        manifest_url,
                        simulation_url,
                    )

                analysis.visagism = public_result
                analysis.raw_results = {"visagism_full": public_result}
                analysis.confidence_score = cls._visagism_confidence(public_result)
                analysis.processing_time_ms = int((time.time() - started) * 1000)
                analysis.model_version = "visagism-real-pipeline-v1"
                analysis.status = "completed"
                analysis.completed_at = datetime.utcnow()
                await db.commit()
            except Exception as exc:
                analysis.status = "failed"
                analysis.raw_results = {
                    "visagism_full_error": {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                }
                analysis.processing_time_ms = int((time.time() - started) * 1000)
                analysis.completed_at = datetime.utcnow()
                await db.commit()

    @classmethod
    async def _materialize_photos(cls, photos, dataset_path: str) -> None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            async def download(photo) -> None:
                response = await client.get(photo.url)
                response.raise_for_status()
                extension = cls._photo_extension(photo.url, response.headers.get("content-type"))
                target = Path(dataset_path) / f"{photo.id}{extension}"
                target.write_bytes(response.content)

            await asyncio.gather(*(download(photo) for photo in photos))

    @staticmethod
    def _photo_extension(url: str, content_type: str | None) -> str:
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
        media = (content_type or "").split(";", 1)[0].strip().lower()
        return {
            "image/png": ".png",
            "image/webp": ".webp",
            "image/jpeg": ".jpg",
        }.get(media, ".jpg")

    @staticmethod
    def _build_full_visagism_payload(
        analysis_id: str,
        photoshoot_id: str,
        pipeline_result: Dict,
        card_url: str | None,
        manifest_url: str | None,
        simulation_url: str | None = None,
    ) -> Dict:
        report = pipeline_result.get("report", {})
        recommendations = report.get("recommendations", {})
        options = []
        for rank, item in enumerate(recommendations.get("options", []), start=1):
            enriched = dict(item)
            enriched["rank"] = rank
            options.append(enriched)
        primary = dict(options[0]) if options else None
        evidence = report.get("evidence", {})
        facial = report.get("facial_analysis", {})
        return {
            "schema_version": report.get("schema_version", "1.0"),
            "analysis_id": analysis_id,
            "photoshoot_id": photoshoot_id,
            "status": "completed",
            "processed_images": evidence.get("processed_images", 0),
            "selected_views": evidence.get("selected_views", {}),
            "face_shape": facial.get("face_shape"),
            "measurements": facial.get("measurements", {}),
            "hair_analysis": report.get("hair_analysis", {}),
            "recommendations": options,
            "top_recommendation": primary,
            "card_url": card_url,
            "manifest_url": manifest_url,
            "analysis_sources": evidence.get("sources", []),
            "limitations": report.get("limitations", []),
            "integrity": report.get("integrity", {}),
            "simulation_url": simulation_url,
        }

    @staticmethod
    def _visagism_confidence(payload: Dict) -> float:
        primary = payload.get("top_recommendation") or {}
        score = primary.get("compatibility_score", 0.5)
        try:
            return max(0.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            return 0.5

    @classmethod
    async def analyze_facial(cls, photo):
        preprocessed = await ImagePreprocessor().process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        return await FacialAnalyzer().analyze_single(preprocessed)

    @classmethod
    async def analyze_visagism(cls, photo):
        preprocessed = await ImagePreprocessor().process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        return await VisagismAnalyzer().analyze_single(preprocessed)

    @classmethod
    async def analyze_casting(cls, photo):
        preprocessed = await ImagePreprocessor().process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        return await CastingAnalyzer().analyze_single(preprocessed)
