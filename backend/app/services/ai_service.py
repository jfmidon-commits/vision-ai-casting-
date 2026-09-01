import ctypes
import gc
import io
import os
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.ai.preprocessing.preprocessor import ImagePreprocessor
from app.utils.memory import log_rss


def _pil_to_jpeg_bytes(img) -> Optional[bytes]:
    """Convert PIL Image from preprocessor to JPEG bytes for byte-based analyzers."""
    if img is None:
        return None
    try:
        buf = io.BytesIO()
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
        vals = list(sources.values())
        if vals and all(v == "mock" for v in vals):
            return True
    if result.get("is_mock") is True or result.get("source") == "mock":
        return True
    return False


def _close_native_resource(obj: Any) -> None:
    """Best-effort close of MediaPipe/native resources held by an analyzer."""
    if obj is None:
        return

    candidates = [obj]
    mediapipe_service = getattr(obj, "mediapipe", None)
    if mediapipe_service is not None:
        candidates.append(mediapipe_service)

    for candidate in candidates:
        for attr in ("_face_mesh", "_face_landmarker", "_pose_landmarker"):
            resource = getattr(candidate, attr, None)
            if resource is None:
                continue
            try:
                close = getattr(resource, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
            try:
                setattr(candidate, attr, None)
            except Exception:
                pass


def _release_process_memory(*objects: Any) -> None:
    """Release analyzer references and return free glibc arenas to the OS when possible."""
    for obj in objects:
        _close_native_resource(obj)

    gc.collect()

    # Render runs Linux/glibc. malloc_trim returns free heap pages to the OS,
    # which matters for a long-lived 512 MiB worker doing repeated analyses.
    try:
        libc = ctypes.CDLL("libc.so.6")
        trim = getattr(libc, "malloc_trim", None)
        if trim is not None:
            trim(0)
    except Exception:
        pass


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
        from sqlalchemy import and_, select

        # A previous analysis may have left native allocator arenas behind.
        _release_process_memory()
        log_rss("analysis_start_after_gc", analysis_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Analysis).where(
                    and_(
                        Analysis.id == analysis_id,
                        Analysis.photoshoot_id == photoshoot_id,
                        Analysis.tenant_id == tenant_id,
                    )
                )
            )
            analysis = result.scalar_one()
            analysis.status = "processing"
            await db.commit()

            start_time = time.time()

            result = await db.execute(
                select(Photo).where(
                    and_(
                        Photo.photoshoot_id == photoshoot_id,
                        Photo.tenant_id == tenant_id,
                    )
                )
            )
            photos = result.scalars().all()

            photos_data = [
                {
                    "id": str(p.id),
                    "url": p.url,
                    "angle": getattr(p, "angle", None),
                }
                for p in photos
            ]

            log_rss("preprocessing_start", analysis_id)
            preprocessor = ImagePreprocessor()
            preprocessed = await preprocessor.process_batch(
                photos_data,
                analysis_id=analysis_id,
            )
            log_rss("preprocessing_end", analysis_id)

            triage_results: List[Dict] = []
            approved_preprocessed = list(preprocessed)
            triage_blocked = False

            if "visagism" in analysis_types:
                approved_preprocessed = []
                bypass_triage = os.environ.get("VISION_BYPASS_TRIAGE", "").lower() in (
                    "1",
                    "true",
                    "yes",
                )

                if bypass_triage:
                    for photo_meta, prep in zip(photos_data, preprocessed):
                        triage_results.append(
                            {
                                "filename": photo_meta.get("id", "unknown"),
                                "category": "frontal",
                                "confidence": 1.0,
                                "selected": True,
                                "rejection_reasons": [],
                            }
                        )
                        approved_preprocessed.append(prep)
                else:
                    from app.ai.image_triage.engine import (
                        ImageTriageEngine,
                        TriageCategory,
                    )

                    triage_engine = ImageTriageEngine()
                    for photo_meta, prep in zip(photos_data, preprocessed):
                        entry = {
                            "filename": photo_meta.get("id", "unknown"),
                            "category": TriageCategory.UNKNOWN.value,
                            "confidence": 0.0,
                            "selected": False,
                            "rejection_reasons": [],
                        }

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
                                if tr.selected and tr.category not in (
                                    TriageCategory.REJECTED,
                                    TriageCategory.UNKNOWN,
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

                    _release_process_memory(triage_engine)
                    log_rss("triage_released", analysis_id)

                if not approved_preprocessed:
                    triage_blocked = True

            pipeline_photos = (
                approved_preprocessed if "visagism" in analysis_types else preprocessed
            )
            image_bytes = _first_image_bytes(pipeline_photos)

            parallel_results: Dict[str, Any] = {}
            engine_errors: List[str] = []

            if not triage_blocked:
                if "facial" in analysis_types and pipeline_photos:
                    from app.ai.facial_analysis.analyzer import FacialAnalyzer

                    facial_analyzer = FacialAnalyzer()
                    try:
                        log_rss("facial_start", analysis_id)
                        facial_out = await facial_analyzer.analyze(pipeline_photos)
                        if _is_facial_mock(facial_out):
                            parallel_results["facial_structure"] = {
                                "is_mock": True,
                                "face_shape": None,
                                "sources": (facial_out or {}).get("sources")
                                or {"mock": "mock"},
                            }
                            engine_errors.append("facial_result_is_mock")
                        else:
                            parallel_results["facial_structure"] = facial_out
                        log_rss("facial_end", analysis_id)
                    except Exception as exc:
                        engine_errors.append(f"facial_error:{type(exc).__name__}:{exc}")
                        parallel_results["facial_structure"] = {
                            "error": str(exc),
                            "is_mock": True,
                            "face_shape": None,
                            "sources": {"facial": "failed"},
                        }
                    finally:
                        _release_process_memory(facial_analyzer)
                        facial_analyzer = None
                        log_rss("facial_released", analysis_id)

                if "expressions" in analysis_types:
                    if image_bytes:
                        from app.ai.expressions.analyzer import ExpressionAnalyzer

                        expression_analyzer = ExpressionAnalyzer()
                        try:
                            log_rss("expressions_start", analysis_id)
                            parallel_results["expressions"] = (
                                expression_analyzer.analyze(image_bytes)
                            )
                            log_rss("expressions_end", analysis_id)
                        except Exception as exc:
                            engine_errors.append(
                                f"expressions_error:{type(exc).__name__}:{exc}"
                            )
                            parallel_results["expressions"] = {
                                "error": str(exc),
                                "confidence": 0.0,
                            }
                        finally:
                            _release_process_memory(expression_analyzer)
                            expression_analyzer = None
                            log_rss("expressions_released", analysis_id)
                    else:
                        engine_errors.append("expressions_no_image_bytes")

                if "photogenic" in analysis_types:
                    if image_bytes:
                        from app.ai.photogenic.analyzer import PhotogenicAnalyzer

                        photogenic_analyzer = PhotogenicAnalyzer()
                        try:
                            log_rss("photogenic_start", analysis_id)
                            parallel_results["photogenic"] = (
                                photogenic_analyzer.analyze(image_bytes)
                            )
                            log_rss("photogenic_end", analysis_id)
                        except Exception as exc:
                            engine_errors.append(
                                f"photogenic_error:{type(exc).__name__}:{exc}"
                            )
                            parallel_results["photogenic"] = {
                                "error": str(exc),
                                "confidence": 0.0,
                            }
                        finally:
                            _release_process_memory(photogenic_analyzer)
                            photogenic_analyzer = None
                            log_rss("photogenic_released", analysis_id)
                    else:
                        engine_errors.append("photogenic_no_image_bytes")

                if "colorimetry" in analysis_types:
                    if image_bytes:
                        from app.ai.colorimetry.analyzer import ColorimetryAnalyzer

                        colorimetry_analyzer = ColorimetryAnalyzer()
                        try:
                            log_rss("colorimetry_start", analysis_id)
                            parallel_results["colorimetry"] = (
                                colorimetry_analyzer.analyze(image_bytes)
                            )
                            log_rss("colorimetry_end", analysis_id)
                        except Exception as exc:
                            engine_errors.append(
                                f"colorimetry_error:{type(exc).__name__}:{exc}"
                            )
                            parallel_results["colorimetry"] = {
                                "error": str(exc),
                                "confidence": 0.0,
                            }
                        finally:
                            _release_process_memory(colorimetry_analyzer)
                            colorimetry_analyzer = None
                            log_rss("colorimetry_released", analysis_id)
                    else:
                        engine_errors.append("colorimetry_no_image_bytes")

                if "grooming" in analysis_types:
                    if image_bytes:
                        from app.ai.grooming.analyzer import GroomingAnalyzer

                        grooming_analyzer = GroomingAnalyzer()
                        try:
                            log_rss("grooming_start", analysis_id)
                            parallel_results["grooming"] = grooming_analyzer.analyze(
                                image_bytes
                            )
                            log_rss("grooming_end", analysis_id)
                        except Exception as exc:
                            # Grooming is useful but must never abort the whole visagism
                            # pipeline. The analyzer can hit image-dependent CV edge cases;
                            # surface them as a limitation and keep producing the report.
                            engine_errors.append(
                                f"grooming_error:{type(exc).__name__}:{exc}"
                            )
                            parallel_results["grooming"] = (
                                grooming_analyzer._error_result(
                                    f"Grooming indisponivel nesta foto: {exc}"
                                )
                            )
                        finally:
                            _release_process_memory(grooming_analyzer)
                            grooming_analyzer = None
                            log_rss("grooming_released", analysis_id)
                    else:
                        engine_errors.append("grooming_no_image_bytes")

            # Byte-based analyzers are done. Drop the JPEG buffer before the
            # visagism/consolidation stages and aggressively return free arenas.
            image_bytes = None
            _release_process_memory()
            log_rss("heavy_analyzers_released", analysis_id)

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
                        "data_source": {
                            "measured": False,
                            "llm_interpretation": False,
                        },
                    }
                else:
                    from app.ai.visagism.analyzer import VisagismAnalyzer

                    visagism_analyzer = VisagismAnalyzer()
                    try:
                        log_rss("visagism_start", analysis_id)
                        sequential_results["visagism"] = (
                            await visagism_analyzer.analyze(
                                pipeline_photos,
                                context,
                            )
                        )
                        log_rss("visagism_end", analysis_id)
                    finally:
                        _release_process_memory(visagism_analyzer)
                        visagism_analyzer = None
                        log_rss("visagism_released", analysis_id)

            if "casting" in analysis_types:
                from app.ai.casting.analyzer import CastingAnalyzer

                casting_analyzer = CastingAnalyzer()
                try:
                    sequential_results["casting"] = await casting_analyzer.analyze(
                        pipeline_photos or preprocessed,
                        context,
                    )
                finally:
                    _release_process_memory(casting_analyzer)

            if "branding" in analysis_types:
                from app.ai.branding.analyzer import BrandingAnalyzer

                branding_analyzer = BrandingAnalyzer()
                try:
                    sequential_results["branding"] = await branding_analyzer.analyze(
                        pipeline_photos or preprocessed,
                        context,
                    )
                finally:
                    _release_process_memory(branding_analyzer)

            all_results = {**parallel_results, **sequential_results}

            from app.ai.consolidator.consolidator import ResultConsolidator

            log_rss("consolidation_start", analysis_id)
            consolidator = ResultConsolidator()
            consolidated = await consolidator.consolidate(
                photos_data,
                all_results,
                tenant_id,
            )
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

            # Do not let native CV/MediaPipe allocations accumulate across
            # analyses in the same long-lived Render worker.
            _release_process_memory(consolidator)
            log_rss("analysis_end_after_gc", analysis_id)

    @classmethod
    async def analyze_facial(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        from app.ai.facial_analysis.analyzer import FacialAnalyzer

        analyzer = FacialAnalyzer()
        try:
            return await analyzer.analyze_single(preprocessed)
        finally:
            _release_process_memory(analyzer)

    @classmethod
    async def analyze_visagism(cls, photo, parallel_results: Dict = None):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )

        from app.ai.image_triage.engine import ImageTriageEngine, TriageCategory

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
            triage_results.append(
                {
                    "filename": tr.filename,
                    "category": tr.category.value,
                    "confidence": tr.confidence,
                    "selected": tr.selected,
                    "rejection_reasons": tr.rejection_reasons or [],
                }
            )
            approved = tr.selected and tr.category not in (
                TriageCategory.REJECTED,
                TriageCategory.UNKNOWN,
            )
        except Exception as exc:
            triage_results.append(
                {
                    "filename": str(getattr(photo, "id", "unknown")),
                    "category": TriageCategory.REJECTED.value,
                    "confidence": 0.0,
                    "selected": False,
                    "rejection_reasons": [f"triage_error: {exc}"],
                }
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            _release_process_memory(triage_engine)

        if not approved:
            return {
                "error": "Foto não aprovada na triagem",
                "limitations": ["photo_rejected_by_triage"],
                "triage_results": triage_results,
                "recommended_hairstyles": [],
                "primary_hairstyle": None,
                "confidence": 0.0,
                "measured_data_used": {},
                "data_source": {
                    "measured": False,
                    "llm_interpretation": False,
                },
            }

        pr = dict(parallel_results or {})
        image_bytes = _pil_to_jpeg_bytes(
            preprocessed.get("image") if isinstance(preprocessed, dict) else None
        )

        if image_bytes:
            if "grooming" not in pr:
                grooming_analyzer = None
                try:
                    from app.ai.grooming.analyzer import GroomingAnalyzer

                    grooming_analyzer = GroomingAnalyzer()
                    pr["grooming"] = grooming_analyzer.analyze(image_bytes)
                except Exception as exc:
                    pr["grooming"] = {"error": str(exc), "confidence": "low"}
                finally:
                    _release_process_memory(grooming_analyzer)
            if "colorimetry" not in pr:
                colorimetry_analyzer = None
                try:
                    from app.ai.colorimetry.analyzer import ColorimetryAnalyzer

                    colorimetry_analyzer = ColorimetryAnalyzer()
                    pr["colorimetry"] = colorimetry_analyzer.analyze(image_bytes)
                except Exception:
                    pass
                finally:
                    _release_process_memory(colorimetry_analyzer)
            if "photogenic" not in pr:
                photogenic_analyzer = None
                try:
                    from app.ai.photogenic.analyzer import PhotogenicAnalyzer

                    photogenic_analyzer = PhotogenicAnalyzer()
                    pr["photogenic"] = photogenic_analyzer.analyze(image_bytes)
                except Exception:
                    pass
                finally:
                    _release_process_memory(photogenic_analyzer)
            if "expressions" not in pr:
                expression_analyzer = None
                try:
                    from app.ai.expressions.analyzer import ExpressionAnalyzer

                    expression_analyzer = ExpressionAnalyzer()
                    pr["expressions"] = expression_analyzer.analyze(image_bytes)
                except Exception:
                    pass
                finally:
                    _release_process_memory(expression_analyzer)

        if "facial_structure" not in pr:
            facial_analyzer = None
            try:
                from app.ai.facial_analysis.analyzer import FacialAnalyzer

                facial_analyzer = FacialAnalyzer()
                facial_out = await facial_analyzer.analyze_single(preprocessed)
                if _is_facial_mock(facial_out):
                    pr["facial_structure"] = {
                        "is_mock": True,
                        "face_shape": None,
                        "sources": (facial_out or {}).get("sources")
                        or {"mock": "mock"},
                    }
                else:
                    pr["facial_structure"] = facial_out
            except Exception:
                pass
            finally:
                _release_process_memory(facial_analyzer)

        context = {
            "parallel_results": pr,
            "triage_results": triage_results,
        }
        from app.ai.visagism.analyzer import VisagismAnalyzer

        analyzer = VisagismAnalyzer()
        try:
            return await analyzer.analyze_single(preprocessed, context=context)
        finally:
            _release_process_memory(analyzer)

    @classmethod
    async def analyze_casting(cls, photo):
        preprocessor = ImagePreprocessor()
        preprocessed = await preprocessor.process_single(
            {"id": str(photo.id), "url": photo.url}
        )
        from app.ai.casting.analyzer import CastingAnalyzer

        analyzer = CastingAnalyzer()
        try:
            return await analyzer.analyze_single(preprocessed)
        finally:
            _release_process_memory(analyzer)
