import time
from datetime import datetime
from typing import Dict, List

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
from app.ai.visagism.image_simulator import VisagismImageSimulator
from app.ai.visagism.recommendation_presenter import (
    present_recommendation,
    present_recommendations,
)


class AIService:
    @classmethod
    async def run_analysis(
        cls,
        analysis_id: str,
        photoshoot_id: str,
        analysis_types: List[str],
        tenant_id: str,
    ):
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models import Analysis, Photo

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

            parallel_results: Dict = {}
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

            sequential_results: Dict = {}
            if "visagism" in analysis_types:
                visagism = await VisagismAnalyzer().analyze(preprocessed, context)
                source_url = photos_data[0]["url"] if photos_data else ""
                sequential_results["visagism"] = await cls._enrich_visagism_result(
                    visagism, source_url
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

            consolidator = ResultConsolidator()
            consolidated = await consolidator.consolidate(
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
    async def analyze_facial(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        analyzer = FacialAnalyzer()
        return await analyzer.analyze_single(preprocessed)

    @classmethod
    async def analyze_visagism(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url, "angle": photo.angle or "front"}
        )
        analyzer = VisagismAnalyzer()
        result = await analyzer.analyze(preprocessed, {})
        return await cls._enrich_visagism_result(result, photo.url)

    @classmethod
    async def _enrich_visagism_result(
        cls, result: Dict, source_photo_url: str
    ) -> Dict:
        canonical = result.get("visagism_analysis") or {}
        primary = canonical.get("primary_recommendation")
        alternatives = canonical.get("alternative_recommendations") or []

        if not primary:
            result["user_facing_result"] = {
                "complete": False,
                "visual_status": "skipped",
                "visual_error": "Nenhuma recomendacao principal disponivel",
                "recommendations": [],
            }
            return result

        primary_user = present_recommendation(primary)
        alternatives_user = present_recommendations(alternatives)
        face_shape = canonical.get("face_shape_category")
        face_shape = getattr(face_shape, "value", face_shape)

        simulator = VisagismImageSimulator()
        visual = await simulator.generate(
            source_photo_url=source_photo_url,
            recommendation=primary_user,
            face_shape=face_shape,
        )

        result["user_facing_result"] = {
            "complete": visual.status == "completed",
            "face_shape": face_shape,
            "primary_recommendation": primary_user,
            "alternative_recommendations": alternatives_user,
            "recommendations": [primary_user, *alternatives_user],
            "visual_status": visual.status,
            "visual_simulation": visual.model_dump(),
            "visual_error": visual.error,
        }
        return result

    @classmethod
    async def analyze_casting(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        analyzer = CastingAnalyzer()
        return await analyzer.analyze_single(preprocessed)
