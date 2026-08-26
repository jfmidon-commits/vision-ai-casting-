import asyncio
import io
import os
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
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
from app.utils.memory import log_rss
from app.ai.image_triage.engine import ImageTriageEngine, TriageCategory


def _pil_to_jpeg_bytes(img) -> Optional[bytes]:
    """Convert PIL Image from preprocessor to JPEG bytes for byte-based analyzers."""
    if img is None:
        return None
    try:
        buf = io.BytesIO()
        # Ensure RGB for JPEG
        if hasattr(img, "mode") and img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()
    except Exception:
        return None


def _first_image_bytes(preprocessed: List[Dict]) -> Optional[bytes]:
    for item in preprocessed or []:
        if not isinstance(item, dict):
            continue
        img = item.get("image")
        data = _pil_to_jpeg_bytes(img)
        if data:
            return data
    return None


def _is_facial_mock(result: Any) -> bool:
    """Detect FacialAnalyzer._mock_result so it never counts as measured data."""
    if not isinstance(result, dict):
        return True
    sources = result.get("sources") or {}
    if isinstance(sources, dict) and sources:
        # mock marks every source as "mock"
        vals = list(sources.values())
        if vals and all(v == "mock" for v in vals):
            return True
    if result.get("is_mock") is True or result.get("source") == "mock":
        return True
    return False


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

            photos_data = [{"id": str(p.id), "url": p.url, "angle": getattr(p, "angle", None)} for p in photos]

            log_rss("preprocessing_start", analysis_id)
            preprocessor = ImagePreprocessor()
            preprocessed = await preprocessor.process_batch(photos_data)
            log_rss("preprocessing_end", analysis_id)

            # ------------------------------------------------------------------
            # P0.1-C — Triagem obrigatória quando visagism está no pedido
            # ------------------------------------------------------------------
            triage_results: List[Dict] = []
            approved_preprocessed = list(preprocessed)
            triage_blocked = False

            if "visagism" in analysis_types:
                triage_engine = ImageTriageEngine()
                approved_preprocessed = []
                for photo_meta, prep in zip(photos_data, preprocessed):
                    entry = {
                        "filename": photo_meta.get("id", "unknown"),
                        "category": TriageCategory.UNKNOWN.value,
                        "confidence": 0.0,
                        "selected": False,
                        "rejection_reasons": [],
                    }

                    # BYPASS: aceitar todas as fotos quando VISION_BYPASS_TRIAGE está ativo
                    if os.environ.get("VISION_BYPASS_TRIAGE", "").lower() in ("1", "true", "yes"):
                        entry = {
                            "filename": photo_meta.get("id", "unknown"),
                            "category": TriageCategory.FRONTAL.value,
                            "confidence": 1.0,
                            "selected": True,
                            "rejection_reasons": [],
                        }
                        approved_preprocessed.append(prep)
                        triage_results.append(entry)
                        continue

                    # Download to temp for triage (engine expects local path)
                    url = photo_meta.get("url")
                    tmp_path = None
                    try:
                        if url:
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as resp:
                                    raw = await resp.read()
                            fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
                            os.write(fd, raw)
                            os.close(fd)
                            tr = triage_engine.process_image(tmp_path)
                            entry = {
                                "filename": tr.filename,
                                "category": tr.category.value,
                                "confidence": tr.confidence,
                                "selected": tr.selected,
                                "rejection_reasons": tr.rejection_reasons or [],
                            }
                            if (
                                tr.selected
                                and tr.category
                                not in (TriageCategory.REJECTED, TriageCategory.UNKNOWN)
                            ):
                                approved_preprocessed.append(prep)
                        else:
                            entry["rejection_reasons"] = ["url_missing_for_triage"]
                    except Exception as exc:
                        entry["rejection_reasons"] = [f"triage_error: {exc}"]
                        entry["selected"] = False
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass
                    triage_results.append(entry)

                if not approved_preprocessed:
                    triage_blocked = True

            # Use only approved photos for motor pipeline when visagism requested
            pipeline_photos = approved_preprocessed if "visagism" in analysis_types else preprocessed
            image_bytes = _first_image_bytes(pipeline_photos)

            parallel_results: Dict[str, Any] = {}
            engine_errors: List[str] = []

            if not triage_blocked:
                if "facial" in analysis_types and pipeline_photos:
                    log_rss("facial_start", analysis_id)
                    facial_out = await FacialAnalyzer().analyze(pipeline_photos)
                    # P0.1-B — never treat mock as measured
                    if _is_facial_mock(facial_out):
                        parallel_results["facial_structure"] = {
                            "is_mock": True,
                            "face_shape": None,
                            "sources": (facial_out or {}).get("sources") or {"mock": "mock"},
                        }
                        engine_errors.append("facial_result_is_mock")
                    else:
                        parallel_results["facial_structure"] = facial_out
                    log_rss("facial_end", analysis_id)

                if "expressions" in analysis_types:
                    if image_bytes:
                        log_rss("expressions_start", analysis_id)
                        parallel_results["expressions"] = ExpressionAnalyzer().analyze(image_bytes)
                        log_rss("expressions_end", analysis_id)
                    else:
                        engine_errors.append("expressions_no_image_bytes")

                if "photogenic" in analysis_types:
                    if image_bytes:
                        log_rss("photogenic_start", analysis_id)
                        parallel_results["photogenic"] = PhotogenicAnalyzer().analyze(image_bytes)
                        log_rss("photogenic_end", analysis_id)
                    else:
                        engine_errors.append("photogenic_no_image_bytes")

                if "colorimetry" in analysis_types:
                    if image_bytes:
                        log_rss("colorimetry_start", analysis_id)
                        parallel_results["colorimetry"] = ColorimetryAnalyzer().analyze(image_bytes)
                        log_rss("colorimetry_end", analysis_id)
                    else:
                        engine_errors.append("colorimetry_no_image_bytes")

                if "grooming" in analysis_types:
                    if image_bytes:
                        log_rss("grooming_start", analysis_id)
                        parallel_results["grooming"] = GroomingAnalyzer().analyze(image_bytes)
                        log_rss("grooming_end", analysis_id)
                    else:
                        engine_errors.append("grooming_no_image_bytes")

            context = {
                "parallel_results": parallel_results,
                "triage_results": triage_results,
                "engine_errors": engine_errors,
            }

            sequential_results: Dict[str, Any] = {}
            if "visagism" in analysis_types:
                if triage_blocked:
                    sequential_results["visagism"] = {
                        "error": "Nenhuma foto passou na triagem",
                        "limitations": ["all_photos_rejected_by_triage"],
                        "recommended_hairstyles": [],
                        "primary_hairstyle": None,
                        "primary_justification": None,
                        "confidence": 0.0,
                        "measured_data_used": {},
                        "current_hair": {
                            "summary": "Triagem bloqueou todas as fotos",
                            "density": "não medido",
                            "hairline": "não medido",
                        },
                        "data_source": {"measured": False, "llm_interpretation": False},
                    }
                else:
                    log_rss("visagism_start", analysis_id)
                    sequential_results["visagism"] = await VisagismAnalyzer().analyze(
                        pipeline_photos, context
                    )
                    log_rss("visagism_end", analysis_id)
            if "casting" in analysis_types:
                sequential_results["casting"] = await CastingAnalyzer().analyze(
                    pipeline_photos or preprocessed, context
                )
            if "branding" in analysis_types:
                sequential_results["branding"] = await BrandingAnalyzer().analyze(
                    pipeline_photos or preprocessed, context
                )

            all_results = {**parallel_results, **sequential_results}

            log_rss("consolidation_start", analysis_id)
            consolidator = ResultConsolidator()
            consolidated = await consolidator.consolidate(photos_data, all_results, tenant_id)
            log_rss("consolidation_end", analysis_id)

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
    async def analyze_visagism(cls, photo, parallel_results: Dict = None):
        """
        Endpoint direto de visagismo.

        P0.1-D: não aparenta pipeline completo se parallel_results não foi
        fornecido. Executa preprocess + triagem mínima + analyzers reais
        quando possible; caso contrário registra limitations explícitas.
        """
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )

        # Triagem mínima (uma foto)
        triage_results = []
        triage_engine = ImageTriageEngine()
        tmp_path = None
        approved = False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(photo.url) as resp:
                    raw = await resp.read()
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            os.write(fd, raw)
            os.close(fd)
            tr = triage_engine.process_image(tmp_path)
            triage_results.append({
                "filename": tr.filename,
                "category": tr.category.value,
                "confidence": tr.confidence,
                "selected": tr.selected,
                "rejection_reasons": tr.rejection_reasons or [],
            })
            approved = (
                tr.selected
                and tr.category not in (TriageCategory.REJECTED, TriageCategory.UNKNOWN)
            )
        except Exception as exc:
            triage_results.append({
                "filename": str(getattr(photo, "id", "unknown")),
                "category": TriageCategory.REJECTED.value,
                "confidence": 0.0,
                "selected": False,
                "rejection_reasons": [f"triage_error: {exc}"],
            })
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if not approved:
            return {
                "error": "Foto não aprovada na triagem",
                "limitations": ["photo_rejected_by_triage"],
                "triage_results": triage_results,
                "recommended_hairstyles": [],
                "primary_hairstyle": None,
                "confidence": 0.0,
                "measured_data_used": {},
                "data_source": {"measured": False, "llm_interpretation": False},
            }

        # Build parallel_results if caller did not supply them
        pr = dict(parallel_results or {})
        image_bytes = _pil_to_jpeg_bytes(preprocessed.get("image") if isinstance(preprocessed, dict) else None)

        if image_bytes:
            if "grooming" not in pr:
                try:
                    pr["grooming"] = GroomingAnalyzer().analyze(image_bytes)
                except Exception:
                    pass
            if "colorimetry" not in pr:
                try:
                    pr["colorimetry"] = ColorimetryAnalyzer().analyze(image_bytes)
                except Exception:
                    pass
            if "photogenic" not in pr:
                try:
                    pr["photogenic"] = PhotogenicAnalyzer().analyze(image_bytes)
                except Exception:
                    pass
            if "expressions" not in pr:
                try:
                    pr["expressions"] = ExpressionAnalyzer().analyze(image_bytes)
                except Exception:
                    pass

        if "facial_structure" not in pr:
            try:
                facial_out = await FacialAnalyzer().analyze_single(preprocessed)
                if _is_facial_mock(facial_out):
                    pr["facial_structure"] = {
                        "is_mock": True,
                        "face_shape": None,
                        "sources": (facial_out or {}).get("sources") or {"mock": "mock"},
                    }
                else:
                    pr["facial_structure"] = facial_out
            except Exception:
                pass

        context = {
            "parallel_results": pr,
            "triage_results": triage_results,
        }
        analyzer = VisagismAnalyzer()
        return await analyzer.analyze_single(preprocessed, context=context)

    @classmethod
    async def analyze_casting(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single({"id": str(photo.id), "url": photo.url})
        analyzer = CastingAnalyzer()
        return await analyzer.analyze_single(preprocessed)
