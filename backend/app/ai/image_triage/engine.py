"""
backend/app/ai/image_triage/engine.py

Motor de triagem inteligente de imagens.

Recebe uma pasta de imagens, analisa cada uma, classifica por ângulo
facial, pontua qualidade e seleciona as melhores candidatas para o
protocolo de visagismo.

Nunca modifica os originais. Copia as selecionadas para pasta de saída.
"""

import os
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageStat
import cv2

from app.ai.mediapipe.analyzer import MediaPipeService
from app.ai.image_triage.schemas import (
    TriageInput, TriageResult, ImageCandidate,
    FaceAngle, QualityScore, QualityDimension,
    TriageConfig,
)

logger = logging.getLogger(__name__)


class ImageTriageEngine:
    """
    Motor de triagem de imagens para visagismo.
    
    Fluxo:
    1. Descobrir imagens na pasta fonte
    2. Para cada imagem:
       a. Carregar e verificar formato/dimensões
       b. Detectar face(s) via MediaPipe
       c. Classificar ângulo facial
       d. Pontuar qualidade (nitidez, iluminação, etc)
       e. Decidir: selecionar / rejeitar
    3. Selecionar top-N por ângulo
    4. Copiar selecionadas para pasta de saída
    5. Gerar relatório
    """
    
    def __init__(self, config: Optional[TriageConfig] = None):
        self.config = config or TriageConfig()
        self.mediapipe = MediaPipeService()
    
    async def triage(self, input_data: TriageInput) -> TriageResult:
        """
        Executa triagem completa.
        
        Args:
            input_data: Configuração e pasta fonte
            
        Returns:
            TriageResult com candidatos selecionados e rejeitados
        """
        start_time = time.time()
        source_dir = Path(input_data.source_dir)
        
        # 1. Descobrir imagens
        image_paths = self._discover_images(source_dir)
        logger.info(f"Triagem: {len(image_paths)} imagens encontradas em {source_dir}")
        
        # 2. Analisar cada imagem
        candidates = []
        for img_path in image_paths:
            try:
                candidate = await self._analyze_image(img_path)
                candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Erro ao analisar {img_path}: {e}")
                candidates.append(self._create_error_candidate(img_path, str(e)))
        
        # 3. Selecionar melhores por ângulo
        selected, rejected = self._select_candidates(candidates)
        
        # 4. Copiar selecionadas
        output_dir = None
        if self.config.copy_selected and selected:
            output_dir = self._copy_selected(selected, input_data)
        
        # 5. Gerar relatório
        report_path = None
        if self.config.generate_report and output_dir:
            report_path = self._generate_report(selected, rejected, output_dir)
        
        # 6. Organizar por ângulo
        by_angle: Dict[str, List[ImageCandidate]] = {}
        for c in selected:
            angle = c.face_angle.value
            if angle not in by_angle:
                by_angle[angle] = []
            by_angle[angle].append(c)
        
        # Ordenar por qualidade dentro de cada ângulo
        for angle in by_angle:
            by_angle[angle].sort(key=lambda x: x.overall_quality, reverse=True)
            for i, c in enumerate(by_angle[angle], 1):
                c.rank_in_category = i
        
        return TriageResult(
            total_images_found=len(image_paths),
            total_images_analyzed=len(candidates),
            total_faces_detected=sum(c.face_count for c in candidates),
            selected_count=len(selected),
            rejected_count=len(rejected),
            selected=selected,
            rejected=rejected,
            by_angle=by_angle,
            config=self.config,
            processing_time_seconds=round(time.time() - start_time, 2),
            output_dir=str(output_dir) if output_dir else None,
            report_path=str(report_path) if report_path else None,
        )
    
    def _discover_images(self, source_dir: Path) -> List[Path]:
        """Descobre todas as imagens suportadas na pasta."""
        image_paths = []
        for ext in self.config.supported_formats:
            image_paths.extend(source_dir.rglob(f"*{ext}"))
            image_paths.extend(source_dir.rglob(f"*{ext.upper()}"))
        
        # Remover duplicatas e ordenar
        seen = set()
        unique = []
        for p in image_paths:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        
        return sorted(unique)
    
    async def _analyze_image(self, img_path: Path) -> ImageCandidate:
        """Analisa uma imagem individual."""
        
        # Carregar imagem
        image = Image.open(img_path)
        width, height = image.size
        
        # Verificar resolução mínima
        if width < self.config.min_width or height < self.config.min_height:
            return ImageCandidate(
                source_path=str(img_path),
                filename=img_path.name,
                face_angle=FaceAngle.UNKNOWN,
                width=width,
                height=height,
                file_size_bytes=img_path.stat().st_size,
                is_usable=False,
                rejection_reasons=[
                    f"Resolucao insuficiente: {width}x{height} "
                    f"(minimo: {self.config.min_width}x{self.config.min_height})"
                ],
            )
        
        # Detectar face via MediaPipe
        mesh_result = await self.mediapipe.analyze_face_mesh(image)
        face_count = mesh_result.get("landmarks_count", 0) // 468 if mesh_result.get("landmarks_count", 0) >= 468 else 0
        
        if face_count == 0:
            return ImageCandidate(
                source_path=str(img_path),
                filename=img_path.name,
                face_angle=FaceAngle.NO_FACE,
                face_count=0,
                width=width,
                height=height,
                file_size_bytes=img_path.stat().st_size,
                is_usable=False,
                rejection_reasons=["Nenhuma face detectada"],
            )
        
        # Se múltiplas faces, usar a primeira (mais provável = maior)
        face_confidence = 0.85  # MediaPipe não retorna confidence diretamente
        
        # Classificar ângulo
        face_angle = self._classify_angle(mesh_result, image)
        
        # Pontuar qualidade
        quality_scores = self._score_quality(image, mesh_result)
        
        # Calcular overall_quality
        overall = self._calculate_overall_quality(quality_scores)
        
        # Verificar dimensões críticas
        rejection_reasons = []
        for qs in quality_scores:
            if qs.is_critical and qs.score < 0.3:
                rejection_reasons.append(
                    f"{qs.dimension.value}: {qs.score:.2f} (minimo critico: 0.3)"
                )
        
        # Verificar face confidence
        if face_confidence < self.config.min_face_confidence:
            rejection_reasons.append(
                f"Confianca da face: {face_confidence:.2f} "
                f"(minimo: {self.config.min_face_confidence})"
            )
        
        # Verificar overall
        is_usable = overall >= self.config.min_overall_quality and len(rejection_reasons) == 0
        
        if overall < self.config.min_overall_quality:
            rejection_reasons.append(
                f"Qualidade geral: {overall:.2f} (minimo: {self.config.min_overall_quality})"
            )
        
        return ImageCandidate(
            source_path=str(img_path),
            filename=img_path.name,
            face_angle=face_angle,
            face_count=face_count,
            face_confidence=face_confidence,
            quality_scores=quality_scores,
            overall_quality=round(overall, 3),
            width=width,
            height=height,
            file_size_bytes=img_path.stat().st_size,
            is_usable=is_usable,
            rejection_reasons=rejection_reasons,
        )
    
    def _classify_angle(self, mesh_result: Dict, image: Image.Image) -> FaceAngle:
        """
        Classifica o ângulo facial a partir dos landmarks.
        
        Usa heurísticas baseadas na posição relativa dos landmarks:
        - Frontal: simetria alta, ambos olhos visíveis igualmente
        - 3/4: um olho mais visível que o outro, nariz deslocado
        - Perfil: apenas um olho visível, nariz em projeção lateral
        - Sorriso: boca aberta/curvada (MAR alto)
        """
        landmarks = mesh_result.get("landmarks", [])
        if len(landmarks) < 468:
            return FaceAngle.UNKNOWN
        
        # Extrair pontos relevantes
        try:
            left_eye_outer = landmarks[33]
            left_eye_inner = landmarks[133]
            right_eye_outer = landmarks[362]
            right_eye_inner = landmarks[263]
            nose_tip = landmarks[1]
            mouth_top = landmarks[13]
            mouth_bottom = landmarks[14]
            chin = landmarks[152]
            forehead = landmarks[10]
        except IndexError:
            return FaceAngle.UNKNOWN
        
        # 1. Verificar sorriso primeiro (boca aberta/curvada)
        mouth_height = abs(mouth_top['y'] - mouth_bottom['y'])
        face_height = abs(forehead['y'] - chin['y'])
        if face_height > 0:
            mar = mouth_height / face_height
            if mar > 0.08:  # Mouth Aspect Ratio alto = sorriso
                return FaceAngle.SMILING
        
        # 2. Calcular visibilidade dos olhos (proxy para ângulo)
        left_eye_width = abs(left_eye_outer['x'] - left_eye_inner['x'])
        right_eye_width = abs(right_eye_outer['x'] - right_eye_inner['x'])
        
        eye_ratio = 0
        if left_eye_width + right_eye_width > 0:
            eye_ratio = min(left_eye_width, right_eye_width) / max(left_eye_width, right_eye_width)
        
        # 3. Posição do nariz relativa ao centro
        face_width = abs(landmarks[234]['x'] - landmarks[454]['x']) if len(landmarks) > 454 else 1
        nose_offset = abs(nose_tip['x'] - 0.5) / face_width if face_width > 0 else 0
        
        # Classificação
        if eye_ratio > 0.85 and nose_offset < 0.05:
            # Frontal: olhos simétricos, nariz central
            return FaceAngle.FRONTAL
        
        if eye_ratio < 0.3:
            # Perfil: um olho muito menor (oculto)
            if left_eye_width > right_eye_width:
                return FaceAngle.PROFILE_RIGHT  # Olho esquerdo maior = perfil direito
            else:
                return FaceAngle.PROFILE_LEFT
        
        if 0.3 <= eye_ratio <= 0.85:
            # 3/4: visibilidade intermediária
            if left_eye_width > right_eye_width:
                return FaceAngle.THREE_QUARTER_RIGHT
            else:
                return FaceAngle.THREE_QUARTER_LEFT
        
        # Fallback: verificar se é posterior (sem face frontal visível)
        # Heurística: testa muito alta, olhos muito baixos
        eye_to_chin = abs(left_eye_outer['y'] - chin['y'])
        forehead_to_eyes = abs(forehead['y'] - left_eye_outer['y'])
        if forehead_to_eyes > eye_to_chin * 1.5:
            return FaceAngle.POSTERIOR
        
        # Verificar hairline (testa muito exposta)
        if forehead_to_eyes > face_height * 0.4:
            return FaceAngle.HAIRLINE
        
        return FaceAngle.UNKNOWN
    
    def _score_quality(self, image: Image.Image, mesh_result: Dict) -> List[QualityScore]:
        """Pontua qualidade da imagem em múltiplas dimensões."""
        scores = []
        
        # 1. Nitidez (sharpness) — variância do Laplaciano
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, laplacian_var / 500.0)  # Normalizar
        scores.append(QualityScore(
            dimension=QualityDimension.SHARPNESS,
            score=round(sharpness_score, 3),
            confidence=0.85,
            details=f"Variancia do Laplaciano: {laplacian_var:.1f}",
            is_critical=False,
        ))
        
        # 2. Resolução
        width, height = image.size
        min_dim = min(width, height)
        resolution_score = min(1.0, min_dim / 1000.0)
        scores.append(QualityScore(
            dimension=QualityDimension.RESOLUTION,
            score=round(resolution_score, 3),
            confidence=1.0,
            details=f"{width}x{height} (min: {min_dim}px)",
            is_critical=True,
        ))
        
        # 3. Iluminação — desvio padrão dos pixels
        stat = ImageStat.Stat(image)
        brightness = sum(stat.mean) / len(stat.mean) / 255.0
        std_dev = sum(stat.stddev) / len(stat.stddev) / 255.0
        
        # Iluminação ideal: nem escura demais, nem com contraste extremo
        illum_score = 1.0 - abs(brightness - 0.5) * 2  # Centro = melhor
        illum_score *= (0.5 + std_dev)  # Algum contraste é bom
        illum_score = max(0.0, min(1.0, illum_score))
        
        scores.append(QualityScore(
            dimension=QualityDimension.ILLUMINATION,
            score=round(illum_score, 3),
            confidence=0.80,
            details=f"Brilho medio: {brightness:.2f}, Desvio: {std_dev:.2f}",
            is_critical=False,
        ))
        
        # 4. Oclusão — verificar se há objetos cobrindo a face
        # Heurística: se landmarks estão incompletos, possível oclusão
        landmarks = mesh_result.get("landmarks", [])
        occlusion_score = 1.0
        if len(landmarks) < 468:
            occlusion_score = len(landmarks) / 468.0
        
        # Verificar landmarks de olhos (possíveis óculos)
        eye_landmarks = [33, 133, 362, 263, 159, 145, 386, 374]
        missing_eye = sum(1 for i in eye_landmarks if i >= len(landmarks))
        if missing_eye > 0:
            occlusion_score *= (1 - missing_eye / len(eye_landmarks))
        
        scores.append(QualityScore(
            dimension=QualityDimension.OCCLUSION,
            score=round(occlusion_score, 3),
            confidence=0.70,
            details=f"Landmarks detectados: {len(landmarks)}/468",
            is_critical=False,
        ))
        
        # 5. Enquadramento — face ocupa proporção adequada da imagem
        if len(landmarks) >= 468:
            face_left = min(lm['x'] for lm in landmarks)
            face_right = max(lm['x'] for lm in landmarks)
            face_top = min(lm['y'] for lm in landmarks)
            face_bottom = max(lm['y'] for lm in landmarks)
            
            face_area = (face_right - face_left) * (face_bottom - face_top)
            
            # Ideal: face ocupa 20-60% da imagem
            if face_area < 0.1:
                framing_score = face_area / 0.1
            elif face_area > 0.6:
                framing_score = max(0, 1.0 - (face_area - 0.6) / 0.4)
            else:
                framing_score = 1.0
            
            # Centralização
            face_center_x = (face_left + face_right) / 2
            face_center_y = (face_top + face_bottom) / 2
            center_distance = ((face_center_x - 0.5)**2 + (face_center_y - 0.5)**2) ** 0.5
            center_score = max(0, 1.0 - center_distance * 2)
            
            framing_score = framing_score * 0.7 + center_score * 0.3
        else:
            framing_score = 0.0
        
        scores.append(QualityScore(
            dimension=QualityDimension.FRAMING,
            score=round(framing_score, 3),
            confidence=0.80,
            details=f"Face ocupa {face_area:.1%} da imagem" if len(landmarks) >= 468 else "Face nao detectada",
            is_critical=True,
        ))
        
        # 6. Contraste
        contrast_score = std_dev  # Já normalizado 0-1
        scores.append(QualityScore(
            dimension=QualityDimension.CONTRAST,
            score=round(contrast_score, 3),
            confidence=0.75,
            details=f"Desvio padrao: {std_dev:.2f}",
            is_critical=False,
        ))
        
        # 7. Ruído — estimativa via diferença entre pixel e média local
        # Simplificado: usar std_dev como proxy invertido
        noise_estimate = max(0, 1.0 - std_dev * 2) if std_dev < 0.5 else max(0, 0.5 - (std_dev - 0.5))
        scores.append(QualityScore(
            dimension=QualityDimension.NOISE,
            score=round(noise_estimate, 3),
            confidence=0.60,
            details=f"Estimativa via desvio: {noise_estimate:.2f}",
            is_critical=False,
        ))
        
        # 8. Visibilidade dos olhos — EAR (Eye Aspect Ratio)
        if len(landmarks) >= 374:
            left_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144])
            right_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 380, 373])
            avg_ear = (left_ear + right_ear) / 2
            
            # EAR ~0.25-0.35 = olhos abertos; <0.2 = fechados/piscando
            if avg_ear > 0.2:
                eye_score = min(1.0, (avg_ear - 0.1) / 0.25)
            else:
                eye_score = 0.0
            
            scores.append(QualityScore(
                dimension=QualityDimension.EYE_VISIBILITY,
                score=round(eye_score, 3),
                confidence=0.85,
                details=f"EAR medio: {avg_ear:.3f}",
                is_critical=False,
            ))
        
        return scores
    
    def _calculate_ear(self, landmarks: List[Dict], indices: List[int]) -> float:
        """Calcula Eye Aspect Ratio."""
        try:
            p = [landmarks[i] for i in indices]
            A = ((p[1]['x'] - p[5]['x'])**2 + (p[1]['y'] - p[5]['y'])**2) ** 0.5
            B = ((p[2]['x'] - p[4]['x'])**2 + (p[2]['y'] - p[4]['y'])**2) ** 0.5
            C = ((p[0]['x'] - p[3]['x'])**2 + (p[0]['y'] - p[3]['y'])**2) ** 0.5
            return (A + B) / (2.0 * C) if C > 0 else 0
        except (IndexError, ZeroDivisionError):
            return 0
    
    def _calculate_overall_quality(self, scores: List[QualityScore]) -> float:
        """Calcula qualidade geral ponderada."""
        if not scores:
            return 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for qs in scores:
            weight = self.config.quality_weights.get(qs.dimension.value, 0.1)
            weighted_sum += qs.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _select_candidates(
        self,
        candidates: List[ImageCandidate],
    ) -> Tuple[List[ImageCandidate], List[ImageCandidate]]:
        """Seleciona melhores candidatos por ângulo."""
        
        # Separar usáveis e rejeitados
        usable = [c for c in candidates if c.is_usable]
        rejected = [c for c in candidates if not c.is_usable]
        
        # Agrupar por ângulo
        by_angle: Dict[str, List[ImageCandidate]] = {}
        for c in usable:
            angle = c.face_angle.value
            if angle not in by_angle:
                by_angle[angle] = []
            by_angle[angle].append(c)
        
        # Selecionar top-N por ângulo
        selected = []
        for angle, cands in by_angle.items():
            # Ordenar por qualidade
            cands.sort(key=lambda x: x.overall_quality, reverse=True)
            
            # Pegar top max_per_angle
            top = cands[:self.config.max_per_angle]
            selected.extend(top)
        
        # Se exceder max_total, manter apenas os melhores
        if len(selected) > self.config.max_total:
            selected.sort(key=lambda x: x.overall_quality, reverse=True)
            moved_to_rejected = selected[self.config.max_total:]
            selected = selected[:self.config.max_total]
            
            for c in moved_to_rejected:
                c.rejection_reasons.append(f"Excede limite total de {self.config.max_total} imagens")
                rejected.append(c)
        
        return selected, rejected
    
    def _copy_selected(
        self,
        selected: List[ImageCandidate],
        input_data: TriageInput,
    ) -> Path:
        """Copia imagens selecionadas para pasta de saída."""
        
        # Criar pasta de saída
        if self.config.output_dir:
            output_dir = Path(self.config.output_dir)
        else:
            source = Path(input_data.source_dir)
            profile_suffix = f"_{input_data.profile_id}" if input_data.profile_id else ""
            output_dir = source.parent / f"{source.name}_triage{profile_suffix}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Criar subpastas por ângulo
        for c in selected:
            angle_dir = output_dir / c.face_angle.value
            angle_dir.mkdir(exist_ok=True)
            
            src = Path(c.source_path)
            dst = angle_dir / f"{c.rank_in_category:02d}_{c.filename}"
            
            shutil.copy2(src, dst)
            logger.info(f"Copiado: {src.name} -> {dst}")
        
        return output_dir
    
    def _generate_report(
        self,
        selected: List[ImageCandidate],
        rejected: List[ImageCandidate],
        output_dir: Path,
    ) -> Path:
        """Gera relatório de triagem em Markdown."""
        
        report_path = output_dir / "TRIAGE_REPORT.md"
        
        lines = [
            "# Relatorio de Triagem de Imagens",
            "",
            f"**Gerado em:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total analisadas:** {len(selected) + len(rejected)}",
            f"**Selecionadas:** {len(selected)}",
            f"**Rejeitadas:** {len(rejected)}",
            "",
            "## Imagens Selecionadas",
            "",
        ]
        
        # Agrupar por ângulo
        by_angle: Dict[str, List[ImageCandidate]] = {}
        for c in selected:
            angle = c.face_angle.value
            if angle not in by_angle:
                by_angle[angle] = []
            by_angle[angle].append(c)
        
        for angle in sorted(by_angle.keys()):
            lines.append(f"### {angle}")
            lines.append("")
            for c in by_angle[angle]:
                lines.append(f"- **{c.filename}** — Qualidade: {c.overall_quality:.2f}")
                for qs in c.quality_scores:
                    lines.append(f"  - {qs.dimension.value}: {qs.score:.2f}")
            lines.append("")
        
        # Cobertura do protocolo
        protocol_angles = [
            "frontal", "three_quarter_left", "three_quarter_right",
            "profile_left", "profile_right", "smiling",
            "hairline", "posterior", "half_body",
        ]
        lines.append("## Cobertura do Protocolo")
        lines.append("")
        for angle in protocol_angles:
            has = angle in by_angle and len(by_angle[angle]) > 0
            status = "✅" if has else "❌"
            lines.append(f"- {status} {angle}")
        lines.append("")
        
        # Rejeitadas
        if rejected:
            lines.append("## Imagens Rejeitadas")
            lines.append("")
            for c in rejected:
                lines.append(f"- **{c.filename}** — {c.face_angle.value}")
                for reason in c.rejection_reasons:
                    lines.append(f"  - ❌ {reason}")
            lines.append("")
        
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Relatorio gerado: {report_path}")
        
        return report_path
    
    def _create_error_candidate(self, img_path: Path, error: str) -> ImageCandidate:
        """Cria candidato para imagem com erro."""
        return ImageCandidate(
            source_path=str(img_path),
            filename=img_path.name,
            face_angle=FaceAngle.UNKNOWN,
            is_usable=False,
            rejection_reasons=[f"Erro na analise: {error}"],
        )
