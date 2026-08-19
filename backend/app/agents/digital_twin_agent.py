"""
DigitalTwinAgent v0.2 - Gerenciamento do gemeo digital com upload multi-angulo.

Responsabilidades:
- Receber uploads de fotos de multiplos angulos (frontal, perfil, 3/4, etc.)
- Processar e alinhar imagens para criacao do gemeo digital
- Gerar mesh 3D a partir das imagens
- Versionar o gemeo digital (v0.1, v0.2, etc.)
- Simular personagens e expressoes
- Exportar assets para diferentes plataformas
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.base import VisionAgent, AgentContext, AgentResult, AgentCapability


class DigitalTwinAgent(VisionAgent):
    """Agente especializado em criacao e gestao do gemeo digital v0.2."""

    # Angulos necessarios para um gemeo digital completo
    REQUIRED_ANGLES = [
        {
            "id": "frontal",
            "name": "Frontal",
            "description": "Rosto de frente, neutro",
            "required": True,
        },
        {
            "id": "profile_left",
            "name": "Perfil Esquerdo",
            "description": "Vista lateral esquerda",
            "required": True,
        },
        {
            "id": "profile_right",
            "name": "Perfil Direito",
            "description": "Vista lateral direita",
            "required": True,
        },
        {
            "id": "three_quarter_left",
            "name": "3/4 Esquerdo",
            "description": "Angulo tres quartos esquerdo",
            "required": True,
        },
        {
            "id": "three_quarter_right",
            "name": "3/4 Direito",
            "description": "Angulo tres quartos direito",
            "required": True,
        },
        {
            "id": "top",
            "name": "Superior",
            "description": "Vista de cima",
            "required": False,
        },
        {
            "id": "bottom",
            "name": "Inferior",
            "description": "Vista de baixo (queixo)",
            "required": False,
        },
        {
            "id": "smile",
            "name": "Sorrindo",
            "description": "Expressao de sorriso",
            "required": False,
        },
        {
            "id": "eyes_closed",
            "name": "Olhos Fechados",
            "description": "Olhos fechados para captura de palpebras",
            "required": False,
        },
        {
            "id": "full_body_front",
            "name": "Corpo Inteiro Frente",
            "description": "Corpo inteiro de frente",
            "required": False,
        },
    ]

    # Formatos de exportacao suportados
    EXPORT_FORMATS = [
        {
            "id": "obj",
            "name": "Wavefront OBJ",
            "extension": ".obj",
            "supports_texture": True,
        },
        {
            "id": "fbx",
            "name": "Autodesk FBX",
            "extension": ".fbx",
            "supports_texture": True,
        },
        {
            "id": "gltf",
            "name": "glTF 2.0",
            "extension": ".gltf",
            "supports_texture": True,
        },
        {
            "id": "usdz",
            "name": "USDZ (Apple)",
            "extension": ".usdz",
            "supports_texture": True,
        },
        {
            "id": "vrm",
            "name": "VRM (VR/VTuber)",
            "extension": ".vrm",
            "supports_texture": True,
        },
    ]

    # Estilos de gemeo digital
    TWIN_STYLES = [
        {
            "id": "realistic",
            "name": "Realista",
            "description": "Reproducao fiel da aparencia real",
        },
        {
            "id": "stylized",
            "name": "Estilizado",
            "description": "Levemente estilizado, tipo jogo AAA",
        },
        {"id": "anime", "name": "Anime", "description": "Estilo anime/manga"},
        {
            "id": "low_poly",
            "name": "Low Poly",
            "description": "Estilo geometrico simplificado",
        },
        {"id": "voxel", "name": "Voxel", "description": "Estilo Minecraft/voxel art"},
    ]

    def __init__(self):
        super().__init__(
            name="DigitalTwinAgent",
            description="Gerenciamento do gemeo digital v0.2 com upload multi-angulo",
            capabilities=[
                AgentCapability.DIGITAL_TWIN_CREATION,
                AgentCapability.DIGITAL_TWIN_UPDATE,
                AgentCapability.CHARACTER_SIMULATION,
            ],
        )

    def can_handle(self, context: AgentContext) -> bool:
        return context.intent in [
            "GENERATE_CHARACTER",
            "UPDATE_DIGITAL_TWIN",
            "SIMULATE_CHARACTER",
            "UPLOAD_MULTI_ANGLE",
            "CHECK_ANGLES_COMPLETENESS",
            "GENERATE_MESH",
            "EXPORT_DIGITAL_TWIN",
            "VERSION_DIGITAL_TWIN",
            "COMPARE_VERSIONS",
        ]

    async def execute(self, context: AgentContext) -> AgentResult:
        self._increment_execution()

        intent = context.intent
        input_data = context.input_data

        try:
            if intent == "UPLOAD_MULTI_ANGLE":
                result = await self._upload_multi_angle(input_data)
            elif intent == "CHECK_ANGLES_COMPLETENESS":
                result = await self._check_angles_completeness(input_data)
            elif intent == "GENERATE_MESH":
                result = await self._generate_mesh(input_data)
            elif intent == "UPDATE_DIGITAL_TWIN":
                result = await self._update_digital_twin(input_data)
            elif intent == "SIMULATE_CHARACTER":
                result = await self._simulate_character(input_data)
            elif intent == "EXPORT_DIGITAL_TWIN":
                result = await self._export_digital_twin(input_data)
            elif intent == "VERSION_DIGITAL_TWIN":
                result = await self._version_digital_twin(input_data)
            elif intent == "COMPARE_VERSIONS":
                result = await self._compare_versions(input_data)
            else:
                return AgentResult(
                    success=False,
                    error=f"Intencao '{intent}' nao suportada pelo DigitalTwinAgent",
                )

            return AgentResult(
                success=True,
                data=result,
                message=f"DigitalTwinAgent executou '{intent}' com sucesso",
            )

        except Exception as e:
            self._increment_error()
            return AgentResult(
                success=False,
                error=f"Erro no DigitalTwinAgent: {str(e)}",
            )

    def validate(self, result: AgentResult) -> bool:
        if not result.success:
            return False
        data = result.data or {}
        if "mesh_quality" in data and not (0 <= data["mesh_quality"] <= 100):
            return False
        return True

    # ========== IMPLEMENTACOES v0.2 ==========

    async def _upload_multi_angle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa upload de fotos de multiplos angulos."""
        uploads = data.get("uploads", [])
        profile_id = data.get("profile_id", "")

        processed = []
        errors = []

        for upload in uploads:
            angle_id = upload.get("angle_id", "")
            image_data = upload.get("image_data", None)

            # Validar angulo
            angle_info = next(
                (a for a in self.REQUIRED_ANGLES if a["id"] == angle_id), None
            )
            if not angle_info:
                errors.append(
                    {
                        "angle_id": angle_id,
                        "error": "Angulo nao reconhecido",
                    }
                )
                continue

            # Validar imagem
            if not image_data:
                errors.append(
                    {
                        "angle_id": angle_id,
                        "error": "Dados da imagem ausentes",
                    }
                )
                continue

            # Processar imagem (em producao: validacao de qualidade, deteccao de face, etc.)
            processed.append(
                {
                    "angle_id": angle_id,
                    "angle_name": angle_info["name"],
                    "status": "processed",
                    "quality_score": random.randint(70, 98),
                    "face_detected": True,
                    "resolution": "2048x2048",
                    "file_size_mb": round(random.uniform(1.5, 5.0), 2),
                    "processed_at": datetime.utcnow().isoformat(),
                }
            )

        # Verificar completude
        completeness = self._calculate_completeness(processed)

        return {
            "profile_id": profile_id,
            "uploaded_angles": len(processed),
            "total_errors": len(errors),
            "errors": errors,
            "processed_angles": processed,
            "completeness": completeness,
            "can_generate_mesh": completeness["percentage"] >= 80,
        }

    async def _check_angles_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica quais angulos estao faltando para gerar o gemeo digital."""
        existing_angles = data.get("existing_angles", [])

        required_ids = {a["id"] for a in self.REQUIRED_ANGLES if a["required"]}
        existing_ids = {
            a["angle_id"] if isinstance(a, dict) else a for a in existing_angles
        }

        missing_required = [
            a
            for a in self.REQUIRED_ANGLES
            if a["required"] and a["id"] not in existing_ids
        ]
        missing_optional = [
            a
            for a in self.REQUIRED_ANGLES
            if not a["required"] and a["id"] not in existing_ids
        ]
        present = [a for a in self.REQUIRED_ANGLES if a["id"] in existing_ids]

        completeness_pct = (len(present) / len(self.REQUIRED_ANGLES)) * 100
        required_pct = (
            (len([p for p in present if p["required"]]) / len(required_ids)) * 100
            if required_ids
            else 100
        )

        return {
            "total_angles": len(self.REQUIRED_ANGLES),
            "required_angles": len(required_ids),
            "present_angles": len(present),
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "completeness_percentage": round(completeness_pct, 1),
            "required_completeness": round(required_pct, 1),
            "can_generate_basic": required_pct >= 100,
            "can_generate_full": completeness_pct >= 80,
            "recommendations": self._angle_recommendations(
                missing_required, missing_optional
            ),
        }

    async def _generate_mesh(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Gera mesh 3D a partir das imagens multi-angulo."""
        angles = data.get("angles", [])
        style = data.get("style", "realistic")
        quality = data.get("quality", "high")

        # Verificar se ha angulos suficientes
        if len(angles) < 5:
            return {
                "success": False,
                "error": "Minimo de 5 angulos necessarios para gerar mesh",
                "provided_angles": len(angles),
            }

        # Simular geracao de mesh (em producao: pipeline de photogrammetry/NeRF)
        mesh_stats = {
            "vertex_count": (
                random.randint(50000, 200000)
                if quality == "high"
                else random.randint(20000, 50000)
            ),
            "face_count": (
                random.randint(100000, 400000)
                if quality == "high"
                else random.randint(40000, 100000)
            ),
            "texture_resolution": "4096x4096" if quality == "high" else "2048x2048",
            "has_uv_map": True,
            "has_normals": True,
            "has_vertex_colors": False,
        }

        # Qualidade do mesh baseada nos angulos fornecidos
        angle_quality = sum(a.get("quality_score", 80) for a in angles) / len(angles)
        mesh_quality = min(100, int(angle_quality * 0.9 + random.randint(5, 15)))

        # Estimativa de tempo (em producao seria real)
        generation_time = len(angles) * random.uniform(30, 120)  # segundos

        return {
            "mesh_id": f"mesh_{random.randint(10000, 99999)}",
            "style": style,
            "quality": quality,
            "mesh_stats": mesh_stats,
            "mesh_quality_score": mesh_quality,
            "generation_time_seconds": round(generation_time, 1),
            "angles_used": len(angles),
            "texture_maps": [
                {"type": "diffuse", "resolution": mesh_stats["texture_resolution"]},
                {"type": "normal", "resolution": mesh_stats["texture_resolution"]},
                {"type": "roughness", "resolution": "1024x1024"},
                {"type": "ambient_occlusion", "resolution": "1024x1024"},
            ],
            "blendshapes_count": (
                random.randint(20, 52)
                if style == "realistic"
                else random.randint(10, 30)
            ),
            "bone_rig": style in ["realistic", "stylized"],
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _update_digital_twin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza o gemeo digital existente com novas imagens."""
        twin_id = data.get("twin_id", "")
        new_angles = data.get("new_angles", [])
        update_type = data.get("update_type", "incremental")  # incremental ou full

        # Em producao: mesclar novo mesh com existente ou regenerar
        if update_type == "incremental":
            # Atualizar apenas partes modificadas
            updated_regions = [a["angle_id"] for a in new_angles]
            return {
                "twin_id": twin_id,
                "update_type": "incremental",
                "updated_regions": updated_regions,
                "mesh_quality_change": random.uniform(-5, 10),
                "processing_time": random.uniform(60, 300),
                "version_bump": "patch",  # v0.2.1
            }
        else:
            # Regeneracao completa
            return {
                "twin_id": twin_id,
                "update_type": "full",
                "mesh_quality_change": random.uniform(5, 20),
                "processing_time": random.uniform(300, 900),
                "version_bump": "minor",  # v0.3
            }

    async def _simulate_character(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simula personagem com o gemeo digital."""
        twin_id = data.get("twin_id", "")
        simulation_type = data.get("simulation_type", "expression")
        parameters = data.get("parameters", {})

        simulations = {
            "expression": self._simulate_expression(parameters),
            "pose": self._simulate_pose(parameters),
            "lighting": self._simulate_lighting(parameters),
            "aging": self._simulate_aging(parameters),
            "makeup": self._simulate_makeup(parameters),
            "hairstyle": self._simulate_hairstyle(parameters),
        }

        result = simulations.get(
            simulation_type, {"error": "Tipo de simulacao desconhecido"}
        )

        return {
            "twin_id": twin_id,
            "simulation_type": simulation_type,
            "result": result,
            "render_time": random.uniform(5, 30),
            "output_resolution": "2048x2048",
        }

    async def _export_digital_twin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Exporta o gemeo digital para um formato especifico."""
        twin_id = data.get("twin_id", "")
        format_id = data.get("format", "gltf")
        include_textures = data.get("include_textures", True)
        lod_level = data.get("lod_level", 0)  # 0 = full, 1 = medium, 2 = low

        format_info = next(
            (f for f in self.EXPORT_FORMATS if f["id"] == format_id), None
        )
        if not format_info:
            return {
                "success": False,
                "error": f"Formato '{format_id}' nao suportado",
                "supported_formats": [f["id"] for f in self.EXPORT_FORMATS],
            }

        # Ajustar qualidade baseado no LOD
        lod_multipliers = {0: 1.0, 1: 0.5, 2: 0.25}
        multiplier = lod_multipliers.get(lod_level, 1.0)

        estimated_size = random.uniform(50, 200) * multiplier  # MB
        if include_textures:
            estimated_size *= 1.5

        return {
            "twin_id": twin_id,
            "format": format_id,
            "format_name": format_info["name"],
            "extension": format_info["extension"],
            "include_textures": include_textures,
            "lod_level": lod_level,
            "estimated_file_size_mb": round(estimated_size, 1),
            "download_url": f"/api/digital-twin/{twin_id}/download?format={format_id}&lod={lod_level}",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    async def _version_digital_twin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria uma nova versao do gemeo digital."""
        twin_id = data.get("twin_id", "")
        version_type = data.get("version_type", "minor")  # major, minor, patch
        changes_description = data.get("changes_description", "")

        # Calcular nova versao
        current_version = data.get("current_version", "0.1.0")
        new_version = self._bump_version(current_version, version_type)

        return {
            "twin_id": twin_id,
            "previous_version": current_version,
            "new_version": new_version,
            "version_type": version_type,
            "changes": changes_description,
            "created_at": datetime.utcnow().isoformat(),
            "is_latest": True,
            "can_rollback": True,
        }

    async def _compare_versions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compara duas versoes do gemeo digital."""
        version_a = data.get("version_a", "")
        version_b = data.get("version_b", "")

        # Simular comparacao
        improvements = random.sample(
            [
                "Melhor qualidade de textura",
                "Mais blendshapes",
                "Mesh mais limpo",
                "Melhor rigging",
                "Menor tamanho de arquivo",
                "Mais detalhes faciais",
            ],
            random.randint(1, 4),
        )

        return {
            "version_a": version_a,
            "version_b": version_b,
            "improvements_in_b": improvements,
            "quality_delta": random.uniform(5, 25),
            "file_size_delta": random.uniform(-20, 10),
            "recommendation": (
                f"Versao {version_b} e superior"
                if random.random() > 0.3
                else "Ambas sao equivalentes"
            ),
        }

    # ========== HELPERS ==========

    def _calculate_completeness(self, processed: List[Dict]) -> Dict[str, Any]:
        """Calcula percentual de completude dos angulos."""
        required_count = len([a for a in self.REQUIRED_ANGLES if a["required"]])
        optional_count = len([a for a in self.REQUIRED_ANGLES if not a["required"]])

        present_required = len(
            [
                p
                for p in processed
                if any(
                    a["id"] == p["angle_id"] and a["required"]
                    for a in self.REQUIRED_ANGLES
                )
            ]
        )
        present_optional = len(
            [
                p
                for p in processed
                if any(
                    a["id"] == p["angle_id"] and not a["required"]
                    for a in self.REQUIRED_ANGLES
                )
            ]
        )

        required_pct = (
            (present_required / required_count * 100) if required_count else 100
        )
        optional_pct = (
            (present_optional / optional_count * 100) if optional_count else 100
        )
        overall_pct = required_pct * 0.7 + optional_pct * 0.3

        return {
            "percentage": round(overall_pct, 1),
            "required_percentage": round(required_pct, 1),
            "optional_percentage": round(optional_pct, 1),
            "required_present": present_required,
            "optional_present": present_optional,
            "total_required": required_count,
            "total_optional": optional_count,
        }

    def _angle_recommendations(
        self, missing_required: List[Dict], missing_optional: List[Dict]
    ) -> List[str]:
        """Gera recomendacoes para completar angulos."""
        recs = []

        if missing_required:
            angles_names = ", ".join([a["name"] for a in missing_required[:3]])
            recs.append(f"Priorizar captura dos angulos obrigatorios: {angles_names}")

        if missing_optional:
            recs.append(
                f"Adicionar angulos opcionais para melhor qualidade: {missing_optional[0]['name']}"
            )

        if not missing_required and not missing_optional:
            recs.append("Todos os angulos capturados! Pronto para gerar mesh.")

        recs.append("Usar iluminacao uniforme e fundo neutro para todos os angulos")
        recs.append("Manter distancia consistente da camera entre as fotos")

        return recs

    def _simulate_expression(self, parameters: Dict) -> Dict:
        expressions = [
            "neutral",
            "smile",
            "surprise",
            "sad",
            "angry",
            "fear",
            "disgust",
        ]
        expression = parameters.get("expression", "smile")
        intensity = parameters.get("intensity", 0.7)

        return {
            "expression": expression if expression in expressions else "neutral",
            "intensity": min(1.0, max(0.0, intensity)),
            "blendshapes_activated": random.randint(8, 25),
            "render_quality": "high",
        }

    def _simulate_pose(self, parameters: Dict) -> Dict:
        poses = ["standing", "sitting", "walking", "running", "idle"]
        pose = parameters.get("pose", "standing")

        return {
            "pose": pose if pose in poses else "standing",
            "bone_rotations": random.randint(15, 45),
            "physics_simulated": pose in ["walking", "running"],
        }

    def _simulate_lighting(self, parameters: Dict) -> Dict:
        setups = ["studio", "outdoor", "dramatic", "soft", "neon"]
        setup = parameters.get("setup", "studio")

        return {
            "setup": setup if setup in setups else "studio",
            "light_sources": random.randint(2, 5),
            "shadow_quality": "high",
        }

    def _simulate_aging(self, parameters: Dict) -> Dict:
        years = parameters.get("years", 10)
        return {
            "years_ahead": years,
            "wrinkles_intensity": min(1.0, years / 50),
            "hair_graying": min(1.0, years / 40),
            "skin_texture_change": min(1.0, years / 30),
        }

    def _simulate_makeup(self, parameters: Dict) -> Dict:
        styles = ["natural", "glam", "editorial", "avant_garde", "no_makeup"]
        style = parameters.get("style", "natural")

        return {
            "style": style if style in styles else "natural",
            "layers": random.randint(3, 8),
            "texture_resolution": "4096x4096",
        }

    def _simulate_hairstyle(self, parameters: Dict) -> Dict:
        styles = ["current", "short", "long", "curly", "straight", "updo", "bald"]
        style = parameters.get("style", "current")
        color = parameters.get("color", None)

        return {
            "style": style if style in styles else "current",
            "color_change": color is not None,
            "new_color": color,
            "hair_strands_simulated": random.randint(50000, 150000),
        }

    def _bump_version(self, current: str, version_type: str) -> str:
        """Incrementa versao semantica."""
        parts = current.split(".")
        if len(parts) != 3:
            parts = ["0", "1", "0"]

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1

        return f"{major}.{minor}.{patch}"
