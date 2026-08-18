import asyncio
import time
from typing import List, Dict
from uuid import UUID

from app.ai.preprocessing.preprocessor import ImagePreprocessor
from app.ai.facial_analysis.analyzer import FacialAnalyzer
from app.ai.visagism.analyzer import VisagismAnalyzer
from app.ai.expressions.analyzer import ExpressionAnalyzer
from app.ai.casting.analyzer import CastingAnalyzer
from app.ai.branding.analyzer import BrandingAnalyzer
from app.ai.colorimetry.analyzer import ColorimetryAnalyzer
from app.ai.grooming.analyzer import GroomingAnalyzer
from app.ai.photogenic.analyzer import PhotogenicAnalyzer
from app.ai.consolidator.consolidator import ResultConsolidator

class AIService:
    @classmethod
    async def run_analysis(cls, analysis_id: str, photoshoot_id: str, analysis_types: List[str], tenant_id: str):
        from app.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import Analysis, Photo, Photoshoot

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

            photos_data = [{"id": str(p.id), "url": p.url, "angle": p.angle} for p in photos]

            preprocessor = ImagePreprocessor()
            preprocessed = await preprocessor.process_batch(photos_data)

            parallel_results = {}
            if "facial" in analysis_types:
                parallel_results["facial_structure"] = await FacialAnalyzer().analyze(preprocessed)
            if "expressions" in analysis_types:
                parallel_results["expressions"] = await ExpressionAnalyzer().analyze(preprocessed)
            if "photogenic" in analysis_types:
                parallel_results["photogenic"] = await PhotogenicAnalyzer().analyze(preprocessed)
            if "colorimetry" in analysis_types:
                parallel_results["colorimetry"] = await ColorimetryAnalyzer().analyze(preprocessed)
            if "grooming" in analysis_types:
                parallel_results["grooming"] = await GroomingAnalyzer().analyze(preprocessed)

            context = {"parallel_results": parallel_results}

            sequential_results = {}
            if "visagism" in analysis_types:
                sequential_results["visagism"] = await VisagismAnalyzer().analyze(preprocessed, context)
            if "casting" in analysis_types:
                sequential_results["casting"] = await CastingAnalyzer().analyze(preprocessed, context)
            if "branding" in analysis_types:
                sequential_results["branding"] = await BrandingAnalyzer().analyze(preprocessed, context)

            all_results = {**parallel_results, **sequential_results}

            consolidator = ResultConsolidator()
            consolidated = await consolidator.consolidate(photos_data, all_results, tenant_id)

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
        preprocessed = await preprocessor.process_single({"id": str(photo.id), "url": photo.url})
        analyzer = FacialAnalyzer()
        return await analyzer.analyze_single(preprocessed)

    @classmethod
    async def analyze_visagism(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single({"id": str(photo.id), "url": photo.url})
        analyzer = VisagismAnalyzer()
        return await analyzer.analyze_single(preprocessed)

    @classmethod
    async def analyze_casting(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single({"id": str(photo.id), "url": photo.url})
        analyzer = CastingAnalyzer()
        return await analyzer.analyze_single(preprocessed)
