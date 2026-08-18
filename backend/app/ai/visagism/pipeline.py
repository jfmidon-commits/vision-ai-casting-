"""
backend/app/ai/visagism/pipeline.py

Orquestrador do pipeline completo do VisagismAgent Real.

Coordena as 7 fases:
1. Validacao multifoto
2. Medicao facial (Vision Core)
3. Analise de cabelo
4. Interpretacao multimodal
5. Regras proprietarias de visagismo
6. Consolidacao e rastreabilidade
7. Geracao de saidas (JSON, relatorio, visualizacao)
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from PIL import Image
import io
import httpx

from app.ai.visagism.schemas import (
    VisagismAnalysisInput, VisagismAnalysisResult,
    PhotoQualityAssessment, FacialMeasurement, FacialProportion,
    FacialRegionAssessment, HairAssessment, HeadNeckShoulderRelation,
    AsymmetryAssessment, ExpressionComparison,
    HaircutRecommendation, DiscouragedCut,
    PhotoAngle, FaceShape, ConfidenceLevel, EvidenceSource,
    PipelineStageResult, PipelineContext,
)
from app.ai.visagism.evidence_tracker import EvidenceTracker
from app.ai.visagism.confidence_scorer import ConfidenceScorer, ConfidenceBreakdown
from app.ai.visagism.measurement_engine import VisagismMeasurementEngine
from app.ai.visagism.hair_analyzer import HairAnalyzer
from app.ai.visagism.multimodal_interpreter import VisagismMultimodalInterpreter
from app.ai.visagism.rule_engine import VisagismRuleEngine
from app.ai.visagism.report_generator import VisagismReportGenerator


class VisagismPipeline:
    """
    Pipeline orquestrado de analise de visagismo.
    
    Executa as fases em sequencia, propagando contexto e evidencias
    entre elas. Cada fase pode falhar parcialmente sem quebrar o pipeline.
    """
    
    def __init__(self):
        self.measurement_engine = VisagismMeasurementEngine()
        self.hair_analyzer = HairAnalyzer()
        self.multimodal_interpreter = VisagismMultimodalInterpreter()
        self.rule_engine = VisagismRuleEngine()
        self.report_generator = VisagismReportGenerator()
        self.confidence_scorer = ConfidenceScorer()
    
    async def execute(
        self,
        input_data: VisagismAnalysisInput,
    ) -> VisagismAnalysisResult:
        """
        Executa o pipeline completo de analise de visagismo.
        
        Args:
            input_data: Dados de entrada com fotos e contexto
            
        Returns:
            VisagismAnalysisResult completo
        """
        start_time = time.time()
        tracker = EvidenceTracker()
        
        # Inicializar resultado
        result = VisagismAnalysisResult(
            correlation_id=input_data.correlation_id,
            photos_analyzed=len(input_data.photos),
        )
        
        # FASE 1: Validacao multifoto
        stage1 = await self._stage_validate_photos(input_data, tracker)
        usable_photos = stage1.data.get('usable_photos', [])
        
        result.photo_assessments = stage1.data.get('assessments', [])
        result.photos_usable = len(usable_photos)
        result.photos_rejected = result.photos_analyzed - result.photos_usable
        
        # Se menos de 1 foto usavel, retornar insuficiente
        if len(usable_photos) < 1:
            result.overall_confidence = 0.0
            result.overall_confidence_explanation = "Nenhuma foto usavel para analise"
            result.analysis_limitations.append("Protocolo multifoto nao atendido — fotos insuficientes ou de baixa qualidade")
            return result
        
        # FASE 2: Medicao facial
        stage2 = await self._stage_measurements(usable_photos, tracker)
        
        result.facial_measurements = stage2.data.get('measurements', [])
        result.facial_proportions = stage2.data.get('proportions', [])
        result.face_shape_category = stage2.data.get('face_shape', FaceShape.UNKNOWN)
        result.face_shape_evidence = stage2.data.get('face_shape_evidence', [])
        result.face_shape_confidence = stage2.data.get('face_shape_confidence', 0.0)
        
        # FASE 3: Analise de cabelo
        stage3 = await self._stage_hair_analysis(usable_photos, stage2.data, tracker)
        result.hair = stage3.data.get('hair_assessment')
        
        # FASE 4: Interpretacao multimodal
        stage4 = await self._stage_multimodal(usable_photos, stage2.data, input_data, tracker)
        
        # FASE 5: Regras de visagismo
        stage5 = await self._stage_rules(
            stage2.data, stage3.data, stage4.data,
            input_data.profile, tracker,
        )
        
        result.primary_recommendation = stage5.data.get('primary')
        result.alternative_recommendations = stage5.data.get('alternatives', [])
        result.discouraged_cuts = stage5.data.get('discouraged', [])
        
        # FASE 6: Consolidacao
        stage6 = await self._stage_consolidation(
            result, stage2.data, stage3.data, stage4.data, stage5.data,
            input_data, tracker,
        )
        
        result.visual_strengths = stage6.data.get('strengths', [])
        result.modifiable_aspects = stage6.data.get('modifiable', [])
        result.preserve_aspects = stage6.data.get('preserve', [])
        result.asymmetries = stage6.data.get('asymmetries')
        result.head_neck_shoulder = stage6.data.get('head_neck_shoulder')
        result.expression_comparison = stage6.data.get('expression_comparison')
        result.analysis_limitations = stage6.data.get('limitations', [])
        
        # FASE 7: Geracao de saidas
        if input_data.include_report:
            result.human_report = self.report_generator.generate(result)
        
        if input_data.include_visualization_data:
            result.visualization_data = self._prepare_visualization_data(stage2.data)
        
        # Confidence global
        result.overall_confidence = stage6.data.get('overall_confidence', 0.0)
        result.overall_confidence_explanation = stage6.data.get('confidence_explanation', '')
        
        # Rastreabilidade
        result.evidence_map = tracker.get_evidence_map()
        
        # Regioes faciais
        regions = stage2.data.get('regions', {})
        result.forehead = self._region_to_assessment('forehead', regions, tracker)
        result.eyebrows = self._region_to_assessment('eyebrows', regions, tracker)
        result.eyes = self._region_to_assessment('eyes', regions, tracker)
        result.nose = self._region_to_assessment('nose', regions, tracker)
        result.cheekbones = self._region_to_assessment('cheekbones', regions, tracker)
        result.mouth = self._region_to_assessment('mouth', regions, tracker)
        result.jaw = self._region_to_assessment('jaw', regions, tracker)
        result.chin = self._region_to_assessment('chin', regions, tracker)
        result.neck = self._region_to_assessment('neck', regions, tracker)
        
        return result
    
    async def _stage_validate_photos(
        self,
        input_data: VisagismAnalysisInput,
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 1: Validacao do protocolo multifoto."""
        start = time.time()
        
        assessments = []
        usable = []
        
        for photo in input_data.photos:
            assessment = await self._validate_single_photo(photo)
            assessments.append(assessment)
            
            if assessment.is_usable:
                usable.append(photo)
            
            # Registrar
            tracker.register(
                category="observation",
                description=f"Foto {photo.angle.value}: {'usavel' if assessment.is_usable else 'rejeitada'}",
                value={
                    'photo_id': str(photo.photo_id),
                    'angle': photo.angle.value,
                    'usable': assessment.is_usable,
                    'face_detected': assessment.face_detected,
                    'quality': assessment.confidence,
                },
                source="mediapipe_landmark",
                confidence=assessment.confidence,
                photo_id=str(photo.photo_id),
            )
        
        return PipelineStageResult(
            stage_name="validation",
            success=True,
            data={
                'assessments': assessments,
                'usable_photos': usable,
                'usable_count': len(usable),
            },
            processing_time_ms=int((time.time() - start) * 1000),
        )
    
    async def _validate_single_photo(self, photo) -> PhotoQualityAssessment:
        """Valida uma foto individual."""
        
        # Tentar carregar imagem
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(photo.url, timeout=10.0)
                image = Image.open(io.BytesIO(response.content))
        except Exception:
            return PhotoQualityAssessment(
                photo_id=photo.photo_id,
                angle=photo.angle,
                is_usable=False,
                unusable_reason="Nao foi possivel carregar a imagem",
                face_detected=False,
                lighting_quality=ConfidenceLevel.INSUFFICIENT_DATA,
                focus_quality=ConfidenceLevel.INSUFFICIENT_DATA,
                angle_accuracy=ConfidenceLevel.INSUFFICIENT_DATA,
                confidence=0.0,
            )
        
        # Verificar dimensoes minimas
        if image.width < 200 or image.height < 200:
            return PhotoQualityAssessment(
                photo_id=photo.photo_id,
                angle=photo.angle,
                is_usable=False,
                unusable_reason="Dimensoes insuficientes",
                face_detected=False,
                lighting_quality=ConfidenceLevel.LOW,
                focus_quality=ConfidenceLevel.LOW,
                angle_accuracy=ConfidenceLevel.UNCERTAIN,
                confidence=0.1,
            )
        
        # Tentar detectar face
        mesh_result = await self.measurement_engine.mediapipe.analyze_face_mesh(image)
        face_detected = mesh_result.get('landmarks_count', 0) >= 468
        
        if not face_detected:
            return PhotoQualityAssessment(
                photo_id=photo.photo_id,
                angle=photo.angle,
                is_usable=False,
                unusable_reason="Face nao detectada",
                face_detected=False,
                lighting_quality=ConfidenceLevel.UNCERTAIN,
                focus_quality=ConfidenceLevel.UNCERTAIN,
                angle_accuracy=ConfidenceLevel.UNCERTAIN,
                confidence=0.0,
            )
        
        # Qualidade estimada (simplificada)
        quality = photo.quality_score or 0.7
        
        lighting = ConfidenceLevel.HIGH if quality > 0.7 else ConfidenceLevel.MODERATE if quality > 0.5 else ConfidenceLevel.LOW
        focus = ConfidenceLevel.HIGH if quality > 0.8 else ConfidenceLevel.MODERATE if quality > 0.6 else ConfidenceLevel.LOW
        angle_acc = ConfidenceLevel.HIGH if photo.angle in [PhotoAngle.FRONT_NEUTRAL, PhotoAngle.FRONT_SMILING] else ConfidenceLevel.MODERATE
        
        return PhotoQualityAssessment(
            photo_id=photo.photo_id,
            angle=photo.angle,
            is_usable=True,
            face_detected=True,
            face_count=1,
            lighting_quality=lighting,
            focus_quality=focus,
            angle_accuracy=angle_acc,
            confidence=quality,
        )
    
    async def _stage_measurements(
        self,
        usable_photos: List[Any],
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 2: Medicao facial."""
        start = time.time()
        
        all_measurements = []
        all_proportions = []
        face_shapes = []
        all_regions = {}
        all_landmarks = {}
        
        for photo in usable_photos:
            try:
                # Carregar imagem
                async with httpx.AsyncClient() as client:
                    response = await client.get(photo.url, timeout=10.0)
                    image = Image.open(io.BytesIO(response.content))
                
                # Medir
                result = await self.measurement_engine.measure_photo(
                    photo_id=photo.photo_id,
                    image=image,
                    angle=photo.angle,
                    tracker=tracker,
                )
                
                if result.get('success'):
                    all_measurements.extend(result.get('measurements', []))
                    all_proportions.extend(result.get('proportions', []))
                    face_shapes.append(result.get('face_shape'))
                    all_regions[photo.angle.value] = result.get('regions', {})
                    all_landmarks[str(photo.photo_id)] = result.get('visualization_landmarks', [])
                    
            except Exception as e:
                tracker.register(
                    category="observation",
                    description=f"Erro na medicao da foto {photo.photo_id}: {str(e)}",
                    value=str(e),
                    source="unknown",
                    confidence=0.0,
                    photo_id=str(photo.photo_id),
                )
        
        # Determinar formato facial consensual
        face_shape, shape_confidence, shape_evidence = self._consensus_face_shape(face_shapes, tracker)
        
        return PipelineStageResult(
            stage_name="measurements",
            success=len(all_measurements) > 0,
            data={
                'measurements': all_measurements,
                'proportions': all_proportions,
                'face_shape': face_shape,
                'face_shape_evidence': shape_evidence,
                'face_shape_confidence': shape_confidence,
                'regions': all_regions,
                'landmarks': all_landmarks,
            },
            processing_time_ms=int((time.time() - start) * 1000),
        )
    
    def _consensus_face_shape(
        self,
        face_shapes: List[FaceShape],
        tracker: EvidenceTracker,
    ) -> Tuple[FaceShape, float, List[str]]:
        """Determina formato facial por consenso entre multiplas fotos."""
        
        if not face_shapes:
            return FaceShape.UNKNOWN, 0.0, []
        
        # Contar ocorrencias
        counts = {}
        for fs in face_shapes:
            counts[fs] = counts.get(fs, 0) + 1
        
        # Mais frequente
        consensus = max(counts, key=counts.get)
        confidence = counts[consensus] / len(face_shapes)
        
        # Evidencias
        evidence_ids = []
        for i, fs in enumerate(face_shapes):
            eid = tracker.register(
                category="observation",
                description=f"Formato detectado na foto {i+1}: {fs.value}",
                value=fs.value,
                source="computed_ratio",
                confidence=0.85,
            )
            evidence_ids.append(eid)
        
        # Registrar consenso
        consensus_eid = tracker.register(
            category="interpretation",
            description=f"Formato facial consensual: {consensus.value} ({counts[consensus]}/{len(face_shapes)} fotos)",
            value=consensus.value,
            source="computed_ratio",
            confidence=confidence,
            derived_from=evidence_ids,
        )
        
        return consensus, round(confidence, 3), evidence_ids + [consensus_eid]
    
    async def _stage_hair_analysis(
        self,
        usable_photos: List[Any],
        measurement_data: Dict[str, Any],
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 3: Analise de cabelo."""
        start = time.time()
        
        # Usar foto frontal para analise de cabelo
        frontal_photos = [p for p in usable_photos if p.angle in [PhotoAngle.FRONT_NEUTRAL, PhotoAngle.FRONT_SMILING]]
        
        if not frontal_photos:
            frontal_photos = usable_photos[:1]
        
        photo = frontal_photos[0]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(photo.url, timeout=10.0)
                image = Image.open(io.BytesIO(response.content))
            
            # Obter landmarks da foto
            landmarks = []
            landmarks_data = measurement_data.get('landmarks', {})
            if str(photo.photo_id) in landmarks_data:
                landmarks = landmarks_data[str(photo.photo_id)]
            
            hair = await self.hair_analyzer.analyze(
                photo_id=photo.photo_id,
                image=image,
                angle=photo.angle,
                landmarks=landmarks,
                tracker=tracker,
            )
            
            return PipelineStageResult(
                stage_name="hair_analysis",
                success=True,
                data={'hair_assessment': hair},
                processing_time_ms=int((time.time() - start) * 1000),
            )
            
        except Exception as e:
            return PipelineStageResult(
                stage_name="hair_analysis",
                success=False,
                data={'hair_assessment': None},
                errors=[str(e)],
                processing_time_ms=int((time.time() - start) * 1000),
            )
    
    async def _stage_multimodal(
        self,
        usable_photos: List[Any],
        measurement_data: Dict[str, Any],
        input_data: VisagismAnalysisInput,
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 4: Interpretacao multimodal."""
        start = time.time()
        
        # Preparar fotos para o LLM
        photos_for_llm = []
        for photo in usable_photos[:3]:  # Max 3
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(photo.url, timeout=10.0)
                    image = Image.open(io.BytesIO(response.content))
                
                photos_for_llm.append({
                    'photo_id': photo.photo_id,
                    'image': image,
                    'angle': photo.angle,
                    'is_usable': True,
                })
            except Exception:
                pass
        
        # Contexto do perfil
        profile_ctx = {
            'gender': input_data.profile.gender,
            'age_estimate': input_data.profile.age_estimate,
            'current_hair_length': input_data.profile.current_hair_length,
        }
        
        # Medicoes como dicts
        measurements = [m.model_dump() for m in measurement_data.get('measurements', [])]
        proportions = [p.model_dump() for p in measurement_data.get('proportions', [])]
        
        try:
            result = await self.multimodal_interpreter.interpret(
                photos=photos_for_llm,
                measurements=measurements,
                proportions=proportions,
                face_shape=measurement_data.get('face_shape', FaceShape.UNKNOWN).value,
                profile_context=profile_ctx,
                tracker=tracker,
            )
            
            return PipelineStageResult(
                stage_name="multimodal",
                success=result.get('success', False),
                data=result,
                processing_time_ms=int((time.time() - start) * 1000),
            )
            
        except Exception as e:
            return PipelineStageResult(
                stage_name="multimodal",
                success=False,
                data={},
                errors=[str(e)],
                processing_time_ms=int((time.time() - start) * 1000),
            )
    
    async def _stage_rules(
        self,
        measurement_data: Dict[str, Any],
        hair_data: Dict[str, Any],
        multimodal_data: Dict[str, Any],
        profile: Any,
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 5: Regras de visagismo."""
        start = time.time()
        
        face_shape = measurement_data.get('face_shape', FaceShape.UNKNOWN)
        proportions = {p.name: p.model_dump() for p in measurement_data.get('proportions', [])}
        
        # Consolidar regioes
        regions = {}
        for angle_regs in measurement_data.get('regions', {}).values():
            for region_name, region_data in angle_regs.items():
                if region_name not in regions:
                    regions[region_name] = region_data
        
        hair = hair_data.get('hair_assessment')
        hair_dict = hair.model_dump() if hair else {}
        
        # Assimetrias (placeholder)
        asymmetries = {'is_detectable': False}
        
        # Contexto do perfil
        profile_ctx = {
            'gender': profile.gender,
            'age_estimate': profile.age_estimate,
            'current_hair_length': profile.current_hair_length,
        }
        
        try:
            primary, alternatives, discouraged = self.rule_engine.generate_recommendations(
                face_shape=face_shape,
                proportions=proportions,
                regions=regions,
                hair=hair_dict,
                asymmetries=asymmetries,
                profile_context=profile_ctx,
                tracker=tracker,
            )
            
            return PipelineStageResult(
                stage_name="rules",
                success=primary is not None,
                data={
                    'primary': primary,
                    'alternatives': alternatives,
                    'discouraged': discouraged,
                },
                processing_time_ms=int((time.time() - start) * 1000),
            )
            
        except Exception as e:
            return PipelineStageResult(
                stage_name="rules",
                success=False,
                data={},
                errors=[str(e)],
                processing_time_ms=int((time.time() - start) * 1000),
            )
    
    async def _stage_consolidation(
        self,
        result: VisagismAnalysisResult,
        measurement_data: Dict[str, Any],
        hair_data: Dict[str, Any],
        multimodal_data: Dict[str, Any],
        rules_data: Dict[str, Any],
        input_data: VisagismAnalysisInput,
        tracker: EvidenceTracker,
    ) -> PipelineStageResult:
        """Fase 6: Consolidacao e calculo de confidence."""
        start = time.time()
        
        # Pontos fortes
        strengths = []
        if result.face_shape_category == FaceShape.OVAL:
            strengths.append("Formato facial equilibrado — base versatil para variacoes")
        
        # Do multimodal
        for obs in multimodal_data.get('data', {}).get('observations', []):
            if 'strong' in obs.get('visual_impact', '').lower():
                strengths.append(obs.get('observation', ''))
        
        # Aspectos modificaveis
        modifiable = []
        if result.face_shape_category in [FaceShape.OBLONG, FaceShape.ROUND]:
            modifiable.append(f"Proporcao {result.face_shape_category.value} — ajustavel via distribuicao de volume")
        
        # Aspectos a preservar
        preserve = []
        if result.face_shape_category == FaceShape.OVAL:
            preserve.append("Proporcao geral ja equilibrada — evitar mudancas drasticas")
        
        # Limitacoes
        limitations = []
        if result.photos_usable < 3:
            limitations.append(f"Apenas {result.photos_usable} foto(s) usavel(is) — analise limitada")
        if not any(p.angle == PhotoAngle.POSTERIOR for p in input_data.photos if p.is_usable):
            limitations.append("Angulo posterior ausente — analise 360 do cabelo incompleta")
        if not any(p.angle in [PhotoAngle.PROFILE_LEFT, PhotoAngle.PROFILE_RIGHT] for p in input_data.photos if p.is_usable):
            limitations.append("Perfil ausente — profundidade facial nao avaliada")
        
        # PLACEHOLDER: verificar se hair assessment tem campos placeholder
        if result.hair and any(
            'PLACEHOLDER' in str(v) 
            for v in [result.hair.texture, result.hair.thickness, result.hair.volume]
            if v is not None
        ):
            limitations.append("Analise de textura/espessura/volume do cabelo parcial — requer modelo especializado futuro")
        
        # PLACEHOLDER: verificar se regioes faciais tem campos placeholder
        placeholder_regions = []
        for region in [result.forehead, result.eyebrows, result.eyes, result.nose, 
                       result.cheekbones, result.mouth, result.jaw, result.chin, result.neck]:
            if region and region.observations:
                for obs in region.observations:
                    if 'PLACEHOLDER' in str(obs):
                        placeholder_regions.append(region.region_name)
        if placeholder_regions:
            limitations.append(
                f"Regioes com medicoes placeholder: {', '.join(set(placeholder_regions))} — "
                f"requerem fotos adicionais ou modelo especializado"
            )
        
        # Assimetrias
        asym = AsymmetryAssessment(
            is_detectable=False,
            confidence=0.5,
            source=EvidenceSource.INFERRED,
        )
        
        # Head/neck/shoulder (placeholder)
        hns = HeadNeckShoulderRelation(
            confidence=0.4,
            source=EvidenceSource.INFERRED,
        )
        
        # Expression comparison
        has_neutral = any(p.angle == PhotoAngle.FRONT_NEUTRAL for p in input_data.photos if p.is_usable)
        has_smiling = any(p.angle == PhotoAngle.FRONT_SMILING for p in input_data.photos if p.is_usable)
        expr = ExpressionComparison(
            has_comparison=has_neutral and has_smiling,
            confidence=0.7 if (has_neutral and has_smiling) else 0.3,
            evidence_ids=[],
        )
        
        # Confidence global
        module_scores = {
            'validation': 0.9 if result.photos_usable > 0 else 0.0,
            'measurement': 0.85 if measurement_data.get('measurements') else 0.3,
            'hair_analysis': 0.7 if hair_data.get('hair_assessment') else 0.3,
            'multimodal': multimodal_data.get('data', {}).get('confidence', 0.0),
            'rules': 0.8 if rules_data.get('data', {}).get('primary') else 0.0,
        }
        
        has_critical = {
            'measurement': len(measurement_data.get('measurements', [])) > 0,
            'rules': rules_data.get('data', {}).get('primary') is not None,
        }
        
        inference_ratio = 0.3  # Estimativa
        
        overall = self.confidence_scorer.score_overall(
            module_scores=module_scores,
            has_critical_modules=has_critical,
            inference_ratio=inference_ratio,
        )
        
        return PipelineStageResult(
            stage_name="consolidation",
            success=True,
            data={
                'strengths': strengths,
                'modifiable': modifiable,
                'preserve': preserve,
                'asymmetries': asym,
                'head_neck_shoulder': hns,
                'expression_comparison': expr,
                'limitations': limitations,
                'overall_confidence': overall.score,
                'confidence_explanation': overall.explanation,
            },
            processing_time_ms=int((time.time() - start) * 1000),
        )
    
    def _region_to_assessment(
        self,
        region_name: str,
        regions: Dict[str, Any],
        tracker: EvidenceTracker,
    ) -> Optional[FacialRegionAssessment]:
        """Converte dados de regiao para FacialRegionAssessment."""
        
        region_data = None
        for angle_regs in regions.values():
            if region_name in angle_regs:
                region_data = angle_regs[region_name]
                break
        
        if not region_data:
            return None
        
        observations = []
        if isinstance(region_data, dict):
            for key, value in region_data.items():
                if key != 'measurements' and value is not None:
                    observations.append(f"{key}: {value}")
        
        return FacialRegionAssessment(
            region_name=region_name,
            observations=observations,
            confidence=0.7,
            source=EvidenceSource.MEDIAPIPE_LANDMARK,
        )
    
    def _prepare_visualization_data(self, measurement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados para visualizacao futura."""
        return {
            'landmarks': measurement_data.get('landmarks', {}),
            'measurements': [m.model_dump() for m in measurement_data.get('measurements', [])],
            'proportions': [p.model_dump() for p in measurement_data.get('proportions', [])],
        }
