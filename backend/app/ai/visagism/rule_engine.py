"""
backend/app/ai/visagism/rule_engine.py

Motor de regras proprietarias de visagismo.
Transforma evidencias (medicoes, proporcoes, analise de cabelo,
interpretacao multimodal) em recomendacoes de cortes de cabelo.

Separacao: OBSERVADO -> MEDIDO -> INTERPRETADO -> RECOMENDADO
"""

from typing import Dict, List, Optional, Any, Tuple

from app.ai.visagism.schemas import (
    FaceShape, HairTexture, HairThickness,
    ChangeLevel, MaintenanceDifficulty, SideTreatment, ForeheadExposure,
    HaircutRecommendation, DiscouragedCut,
)
from app.ai.visagism.evidence_tracker import EvidenceTracker


class VisagismRuleEngine:
    """
    Motor de regras de visagismo.
    Converte medicoes faciais e analises em recomendacoes de estilo.
    """

    def __init__(self):
        self._load_shape_rules()

    def _load_shape_rules(self):
        """Carrega regras por formato de rosto."""
        self._shape_rules = {
            FaceShape.OVAL: {
                "compatible": [
                    "layered_cut", "long_bob", "side_swept_bangs", "soft_waves",
                    "classic_bob", "textured_ends"
                ],
                "avoid": ["heavy_bangs", "boxy_cuts", "extreme_asymmetry"],
                "principle": "Formato oval e versatil; equilibrar proporcoes naturais",
                "volume": "Distribuicao equilibrada",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.LAYERED,
            },
            FaceShape.ROUND: {
                "compatible": [
                    "long_layers", "side_part", "height_on_top", "asymmetrical_cut",
                    "angular_bob", "volume_at_crown"
                ],
                "avoid": ["chin_length_bob", "round_layers", "center_part", "full_bangs"],
                "principle": "Criar ilusao de comprimento; evitar enfase na largura",
                "volume": "Volume no topo, laterais mais contidas",
                "forehead": ForeheadExposure.FULL,
                "side": SideTreatment.TAPERED,
            },
            FaceShape.SQUARE: {
                "compatible": [
                    "soft_layers", "side_swept_bangs", "waves", "textured_ends",
                    "long_hair", "curtain_bangs"
                ],
                "avoid": ["blunt_bob", "straight_across_bangs", "geometric_cuts", "sharp_angles"],
                "principle": "Suavizar angulos da mandibula; adicionar movimento",
                "volume": "Volume nas laterais para suavizar",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.LAYERED,
            },
            FaceShape.HEART: {
                "compatible": [
                    "chin_length_bob", "side_swept_bangs", "layers_around_jaw",
                    "pixie_with_volume", "soft_waves", "bangs"
                ],
                "avoid": ["top_volume", "short_layers_on_top", "high_crown", "heavy_top"],
                "principle": "Equilibrar testa larga com queixo fino; volume na mandibula",
                "volume": "Volume na regiao do queixo e mandibula",
                "forehead": ForeheadExposure.MINIMAL,
                "side": SideTreatment.KEPT_LENGTH,
            },
            FaceShape.DIAMOND: {
                "compatible": [
                    "bangs", "chin_length_bob", "volume_at_chin", "soft_layers",
                    "side_part", "curtain_bangs"
                ],
                "avoid": ["volume_at_cheekbones", "ear_exposing_cuts", "short_top"],
                "principle": "Suavizar ossos zigomaticos proeminentes; volume no queixo",
                "volume": "Volume no queixo, contido nas macas do rosto",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.LAYERED,
            },
            FaceShape.OBLONG: {
                "compatible": [
                    "volume_on_sides", "curtain_bangs", "layered_bob", "waves",
                    "rounded_layers", "medium_length"
                ],
                "avoid": ["height_on_top", "long_straight", "slicked_back", "very_long"],
                "principle": "Adicionar largura nas laterais; reduzir percepcao de comprimento",
                "volume": "Volume horizontal nas laterais",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.VOLUME_ON_SIDES,
            },
            FaceShape.TRIANGULAR: {
                "compatible": [
                    "volume_on_top", "layered_top", "side_swept", "asymmetrical",
                    "height_at_crown", "textured_top"
                ],
                "avoid": ["volume_at_jaw", "chin_length_bob", "blunt_ends_at_jaw", "full_sides"],
                "principle": "Adicionar volume na testa; reduzir enfase na mandibula",
                "volume": "Volume no topo e regiao frontal",
                "forehead": ForeheadExposure.FULL,
                "side": SideTreatment.TAPERED,
            },
            FaceShape.MIXED: {
                "compatible": [
                    "layered_cut", "medium_length", "soft_layers", "adaptable_bob",
                    "textured_cut"
                ],
                "avoid": ["extreme_cuts", "very_short", "very_long", "radical_asymmetry"],
                "principle": "Formato misto; opcoes equilibradas e adaptaveis",
                "volume": "Distribuicao moderada e equilibrada",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.LAYERED,
            },
            FaceShape.UNKNOWN: {
                "compatible": [
                    "layered_cut", "medium_length", "soft_layers", "classic_bob",
                    "natural_movement"
                ],
                "avoid": ["extreme_cuts", "very_short", "very_long"],
                "principle": "Formato indeterminado; opcoes seguras e versateis",
                "volume": "Distribuicao natural",
                "forehead": ForeheadExposure.PARTIAL,
                "side": SideTreatment.LAYERED,
            },
        }

    def generate_recommendations(
        self,
        face_shape: FaceShape,
        proportions: Dict[str, Dict[str, Any]],
        regions: Dict[str, Any],
        hair: Dict[str, Any],
        asymmetries: Dict[str, Any],
        profile_context: Dict[str, Any],
        tracker: EvidenceTracker,
    ) -> Tuple[Optional[HaircutRecommendation], List[HaircutRecommendation], List[DiscouragedCut]]:
        """
        Gera recomendacoes de cortes baseadas em evidencias.

        Returns:
            (primary, alternatives, discouraged)
        """
        shape_rule = self._shape_rules.get(face_shape, self._shape_rules[FaceShape.UNKNOWN])

        # Registrar evidencia de formato
        shape_eid = tracker.register(
            category="interpretation",
            description=f"Formato facial: {face_shape.value}",
            value=face_shape.value,
            source="rule_engine",
            confidence=0.8 if face_shape != FaceShape.UNKNOWN else 0.4,
        )

        # Determinar textura e espessura
        texture_str = hair.get("texture", "unknown")
        thickness_str = hair.get("thickness", "unknown")

        try:
            texture = HairTexture(texture_str) if texture_str != "unknown" else HairTexture.UNKNOWN
        except ValueError:
            texture = HairTexture.UNKNOWN

        try:
            thickness = HairThickness(thickness_str) if thickness_str != "unknown" else HairThickness.UNKNOWN
        except ValueError:
            thickness = HairThickness.UNKNOWN

        # Registrar evidencia de cabelo
        hair_eid = tracker.register(
            category="observation",
            description=f"Cabelo: textura={texture.value}, espessura={thickness.value}",
            value={"texture": texture.value, "thickness": thickness.value},
            source="rule_engine",
            confidence=0.6 if texture != HairTexture.UNKNOWN else 0.3,
        )

        # Analisar proporcoes
        prop_adjustments = self._analyze_proportions(proportions)
        prop_eids = []
        for adj in prop_adjustments:
            eid = tracker.register(
                category="interpretation",
                description=adj["description"],
                value=adj["value"],
                source="rule_engine",
                confidence=adj["confidence"],
            )
            prop_eids.append(eid)

        # Compilar listas
        compatible = list(shape_rule["compatible"])
        avoid = list(shape_rule["avoid"])

        # Ajustar por textura
        if texture == HairTexture.CURLY or texture == HairTexture.COILY:
            compatible = [c for c in compatible if c not in ["blunt_bob", "precision_cut"]]
            avoid.extend(["razor_cut", "thinning_heavy"])
        elif texture == HairTexture.STRAIGHT:
            compatible = [c for c in compatible if c not in ["heavy_layering"]]
            avoid.extend(["over_texturizing"])

        # Ajustar por espessura
        if thickness == HairThickness.FINE:
            compatible = [c for c in compatible if c not in ["heavy_undercut"]]
            avoid.extend(["over_layering", "too_much_texturizing"])
        elif thickness == HairThickness.COARSE:
            compatible = [c for c in compatible if c not in ["pixie_with_volume"]]
            avoid.extend(["volume_techniques", "round_shapes"])

        # Dados insuficientes
        if face_shape == FaceShape.UNKNOWN and not proportions:
            tracker.link_conclusion("insufficient_data", [shape_eid, hair_eid])
            primary = self._create_fallback(face_shape, shape_rule, tracker, [shape_eid, hair_eid])
            alternatives = [
                self._create_alternative("layered_cut", face_shape, shape_rule, tracker, 2, [shape_eid]),
                self._create_alternative("medium_length", face_shape, shape_rule, tracker, 3, [shape_eid]),
                self._create_alternative("soft_layers", face_shape, shape_rule, tracker, 4, [shape_eid]),
                self._create_alternative("classic_bob", face_shape, shape_rule, tracker, 5, [shape_eid]),
            ]
            return primary, alternatives, []

        # Recomendacao principal (rank=1)
        primary_name = compatible[0] if compatible else "layered_cut"
        primary = self._create_recommendation(
            name=primary_name,
            rank=1,
            face_shape=face_shape,
            shape_rule=shape_rule,
            texture=texture,
            thickness=thickness,
            tracker=tracker,
            evidence_ids=[shape_eid, hair_eid] + prop_eids,
        )
        tracker.link_conclusion(f"primary_{primary_name}", [shape_eid, hair_eid] + prop_eids)

        # Alternativas (ranks 2-5, max 4)
        alternatives = []
        alt_names = [c for c in compatible[1:5] if c != primary_name]
        fallbacks = ["soft_layers", "medium_length", "classic_bob", "textured_ends"]
        for fb in fallbacks:
            if fb not in alt_names and fb != primary_name:
                alt_names.append(fb)
            if len(alt_names) >= 4:
                break

        for i, alt_name in enumerate(alt_names[:4], start=2):
            alt = self._create_recommendation(
                name=alt_name,
                rank=i,
                face_shape=face_shape,
                shape_rule=shape_rule,
                texture=texture,
                thickness=thickness,
                tracker=tracker,
                evidence_ids=[shape_eid, hair_eid],
            )
            tracker.link_conclusion(f"alternative_{alt_name}", [shape_eid, hair_eid])
            alternatives.append(alt)

        # Cortes desaconselhados
        discouraged = []
        for disc_name in avoid[:5]:
            disc = DiscouragedCut(
                name=disc_name,
                reason=f"Incompativel com formato {face_shape.value}: {shape_rule['principle']}",
                alternative=compatible[0] if compatible else "layered_cut",
                confidence=0.7,
                evidence_ids=[shape_eid],
            )
            tracker.link_conclusion(f"discouraged_{disc_name}", [shape_eid])
            discouraged.append(disc)

        return primary, alternatives, discouraged

    def _analyze_proportions(self, proportions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analisa proporcoes faciais."""
        adjustments = []
        for prop_name, prop_data in proportions.items():
            value = prop_data.get("value", 0.5)
            classification = prop_data.get("classification", "unknown")

            if prop_name == "forehead_height_ratio":
                if classification == "high" or value > 0.55:
                    adjustments.append({
                        "description": "Testa alta: recomendar franja ou volume frontal",
                        "value": value,
                        "confidence": 0.7,
                    })
                elif classification == "low" or value < 0.35:
                    adjustments.append({
                        "description": "Testa baixa: evitar franja pesada, valorizar altura",
                        "value": value,
                        "confidence": 0.7,
                    })
            elif prop_name == "face_width_ratio":
                if classification == "wide" or value > 0.75:
                    adjustments.append({
                        "description": "Rosto largo: alongar visualmente",
                        "value": value,
                        "confidence": 0.7,
                    })
                elif classification == "narrow" or value < 0.65:
                    adjustments.append({
                        "description": "Rosto estreito: adicionar largura visual",
                        "value": value,
                        "confidence": 0.7,
                    })
            elif prop_name == "jaw_width_ratio":
                if classification == "strong" or value > 0.45:
                    adjustments.append({
                        "description": "Mandibula forte: suavizar com camadas",
                        "value": value,
                        "confidence": 0.7,
                    })
                elif classification == "delicate" or value < 0.35:
                    adjustments.append({
                        "description": "Mandibula delicada: estruturar com pontas definidas",
                        "value": value,
                        "confidence": 0.7,
                    })
        return adjustments

    def _create_recommendation(
        self,
        name: str,
        rank: int,
        face_shape: FaceShape,
        shape_rule: Dict[str, Any],
        texture: HairTexture,
        thickness: HairThickness,
        tracker: EvidenceTracker,
        evidence_ids: List[str],
    ) -> HaircutRecommendation:
        """Cria uma recomendacao completa."""
        base_confidence = 0.75 if face_shape != FaceShape.UNKNOWN else 0.45
        if texture == HairTexture.UNKNOWN:
            base_confidence -= 0.1
        if thickness == HairThickness.UNKNOWN:
            base_confidence -= 0.1
        confidence = max(0.2, min(0.95, base_confidence))

        change = ChangeLevel.MODERATE if rank <= 2 else ChangeLevel.SUBTLE
        maintenance = MaintenanceDifficulty.MEDIUM
        if "pixie" in name or "bangs" in name:
            maintenance = MaintenanceDifficulty.HIGH
        elif "long_layers" in name or "natural" in name:
            maintenance = MaintenanceDifficulty.LOW

        justification = (
            f"{shape_rule['principle']}. "
            f"Corte {name} compativel com formato {face_shape.value}. "
            f"Textura {texture.value}, espessura {thickness.value}."
        )

        return HaircutRecommendation(
            rank=rank,
            name=name,
            category="haircut",
            justification=justification,
            volume_distribution=shape_rule.get("volume", "Distribuicao natural"),
            texture_work=self._get_texture_work(texture, thickness),
            forehead_exposure_recommendation=shape_rule.get("forehead", ForeheadExposure.PARTIAL),
            side_treatment=shape_rule.get("side", SideTreatment.LAYERED),
            change_level=change,
            maintenance_difficulty=maintenance,
            maintenance_frequency=self._get_maintenance_frequency(name),
            technical_instructions=self._get_technical_instructions(name, face_shape, texture),
            styling_requirements=self._get_styling_requirements(name, texture),
            styling_products=self._get_styling_products(texture),
            styling_time_estimate=self._get_styling_time(name),
            confidence=confidence,
            confidence_explanation=f"Baseado em formato {face_shape.value} com confianca {confidence:.0%}",
            evidence_ids=evidence_ids,
        )

    def _create_fallback(
        self,
        face_shape: FaceShape,
        shape_rule: Dict[str, Any],
        tracker: EvidenceTracker,
        evidence_ids: List[str],
    ) -> HaircutRecommendation:
        """Cria recomendacao fallback."""
        return HaircutRecommendation(
            rank=1,
            name="layered_cut",
            category="haircut",
            justification=f"Dados insuficientes. {shape_rule['principle']}. Opcao segura e versatil.",
            volume_distribution="Distribuicao natural e equilibrada",
            texture_work="Trabalho minimo, respeitar textura natural",
            forehead_exposure_recommendation=ForeheadExposure.PARTIAL,
            side_treatment=SideTreatment.LAYERED,
            change_level=ChangeLevel.MODERATE,
            maintenance_difficulty=MaintenanceDifficulty.MEDIUM,
            maintenance_frequency="A cada 6-8 semanas",
            technical_instructions="Corte em camadas suaves. Consultar especialista para personalizacao.",
            styling_requirements="Finalizacao natural. Produtos leves.",
            styling_products=["Leave-in leve", "Protetor termico"],
            styling_time_estimate="10-15 minutos",
            confidence=0.3,
            confidence_explanation="Dados insuficientes — recomendacao generica",
            evidence_ids=evidence_ids,
        )

    def _create_alternative(
        self,
        name: str,
        face_shape: FaceShape,
        shape_rule: Dict[str, Any],
        tracker: EvidenceTracker,
        rank: int,
        evidence_ids: List[str],
    ) -> HaircutRecommendation:
        """Cria alternativa simplificada."""
        return HaircutRecommendation(
            rank=rank,
            name=name,
            category="haircut",
            justification=f"Alternativa {rank}: {shape_rule['principle']}",
            volume_distribution=shape_rule.get("volume", "Distribuicao natural"),
            texture_work="Respeitar textura natural",
            forehead_exposure_recommendation=shape_rule.get("forehead", ForeheadExposure.PARTIAL),
            side_treatment=shape_rule.get("side", SideTreatment.LAYERED),
            change_level=ChangeLevel.SUBTLE,
            maintenance_difficulty=MaintenanceDifficulty.MEDIUM,
            technical_instructions=f"Versao alternativa de {name}. Ajustar conforme formato {face_shape.value}.",
            styling_requirements="Finalizacao natural",
            confidence=0.5,
            evidence_ids=evidence_ids,
        )

    def _get_texture_work(self, texture: HairTexture, thickness: HairThickness) -> str:
        if texture == HairTexture.CURLY:
            return "Respeitar padrao de cacho. Corte a seco ou tecnica especializada."
        if texture == HairTexture.STRAIGHT:
            return "Corte preciso. Pontas retas ou leve graduacao."
        if texture == HairTexture.WAVY:
            return "Camadas para valorizar ondas. Evitar peso nas pontas."
        return "Avaliar textura no momento do corte. Adaptar tecnica."

    def _get_technical_instructions(self, name: str, face_shape: FaceShape, texture: HairTexture) -> str:
        instructions = {
            "layered_cut": f"Camadas suaves em todo o comprimento. Adaptar ao formato {face_shape.value}.",
            "long_bob": "Corte na altura dos ombros com leve camadas. Suavizar pontas.",
            "soft_layers": "Camadas suaves para movimento. Evitar peso nas pontas.",
            "side_swept_bangs": "Franja lateral leve, desconectada. Angulo suave.",
            "long_layers": "Camadas longas para criar comprimento visual. Pontas leves.",
            "volume_on_sides": "Volume nas laterais com camadas horizontais. Equilibrar formato.",
            "chin_length_bob": "Bob na altura do queixo. Leve textura nas pontas.",
            "bangs": "Franja reta ou lateral, acima das sobrancelhas. Suavizar testa.",
            "textured_ends": "Pontas texturizadas para movimento. Tecnica de desfiado leve.",
            "classic_bob": "Bob classico atemporal. Comprimento uniforme ou leve graduacao.",
            "medium_length": "Comprimento medio versatil. Camadas leves se necessario.",
            "natural_movement": "Corte que valoriza movimento natural. Minima intervencao.",
        }
        return instructions.get(name, f"Corte {name}. Adaptar ao formato {face_shape.value} e textura {texture.value}.")

    def _get_styling_requirements(self, name: str, texture: HairTexture) -> str:
        if texture == HairTexture.CURLY or texture == HairTexture.COILY:
            return "Usar tecnica de finalizacao para cachos. Difusor ou secagem natural."
        if "bangs" in name:
            return "Secar franja com escova redonda. Manter forma diariamente."
        if "pixie" in name:
            return "Modelar com pomada ou cera leve. Definir textura."
        return "Secagem natural ou com secador. Produtos leves para definicao."

    def _get_maintenance_frequency(self, name: str) -> str:
        if "bangs" in name or "pixie" in name:
            return "A cada 3-4 semanas"
        if "bob" in name:
            return "A cada 5-6 semanas"
        return "A cada 6-8 semanas"

    def _get_styling_products(self, texture: HairTexture) -> List[str]:
        base = ["Shampoo e condicionador adequados"]
        if texture == HairTexture.CURLY:
            base.extend(["Creme para pentear", "Gel leve", "Oleo finalizador"])
        elif texture == HairTexture.STRAIGHT:
            base.extend(["Protetor termico", "Spray de volume"])
        else:
            base.extend(["Leave-in", "Protetor termico"])
        return base

    def _get_styling_time(self, name: str) -> str:
        if "pixie" in name:
            return "5-10 minutos"
        if "bangs" in name:
            return "10-15 minutos"
        if "long" in name:
            return "15-25 minutos"
        return "10-20 minutos"
