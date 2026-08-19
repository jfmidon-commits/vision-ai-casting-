"""Visual hairstyle simulation for the visagism pipeline.

Uses OpenAI image editing to preserve the subject's identity while changing
only the hairstyle according to the structured visagism recommendation.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.config import settings


@dataclass
class VisualSimulationResult:
    status: str
    image_data_url: Optional[str] = None
    model: Optional[str] = None
    source_photo_url: Optional[str] = None
    error: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "image_data_url": self.image_data_url,
            "model": self.model,
            "source_photo_url": self.source_photo_url,
            "error": self.error,
        }


class VisagismImageSimulator:
    """Generate a realistic hairstyle edit from a source portrait."""

    API_URL = "https://api.openai.com/v1/images/edits"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate(
        self,
        *,
        source_photo_url: str,
        recommendation: Dict[str, Any],
        face_shape: Optional[str] = None,
    ) -> VisualSimulationResult:
        if not self.enabled:
            return VisualSimulationResult(
                status="unavailable",
                source_photo_url=source_photo_url,
                error="OPENAI_API_KEY nao configurada",
            )

        if not source_photo_url:
            return VisualSimulationResult(
                status="failed",
                error="Foto fonte nao informada",
            )

        try:
            image_bytes, filename, content_type = await self._load_source_image(
                source_photo_url
            )
            prompt = self._build_prompt(recommendation, face_shape)
            payload = await self._request_edit(
                image_bytes=image_bytes,
                filename=filename,
                content_type=content_type,
                prompt=prompt,
            )
            image_b64 = self._extract_image_base64(payload)
            if not image_b64:
                raise ValueError("Resposta da API sem imagem gerada")

            return VisualSimulationResult(
                status="completed",
                image_data_url=f"data:image/png;base64,{image_b64}",
                model=settings.OPENAI_IMAGE_MODEL,
                source_photo_url=source_photo_url,
            )
        except Exception as exc:
            return VisualSimulationResult(
                status="failed",
                model=settings.OPENAI_IMAGE_MODEL,
                source_photo_url=source_photo_url,
                error=str(exc),
            )

    async def _load_source_image(self, source: str) -> Tuple[bytes, str, str]:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            owns_client = self._client is None
            client = self._client or httpx.AsyncClient(timeout=30.0)
            try:
                response = await client.get(source)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/jpeg").split(
                    ";", 1
                )[0]
                filename = Path(parsed.path).name or "portrait.jpg"
                return response.content, filename, content_type
            finally:
                if owns_client:
                    await client.aclose()

        local_path = Path(source.removeprefix("file://"))
        if not local_path.exists():
            raise FileNotFoundError(f"Foto fonte nao encontrada: {source}")
        content_type = mimetypes.guess_type(local_path.name)[0] or "image/jpeg"
        return local_path.read_bytes(), local_path.name, content_type

    async def _request_edit(
        self,
        *,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        prompt: str,
    ) -> Dict[str, Any]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=120.0)
        try:
            response = await client.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                data={
                    "model": settings.OPENAI_IMAGE_MODEL,
                    "prompt": prompt,
                    "size": settings.OPENAI_IMAGE_SIZE,
                    "quality": settings.OPENAI_IMAGE_QUALITY,
                    "input_fidelity": "high",
                    "output_format": "png",
                },
                files={"image": (filename, image_bytes, content_type)},
            )
            response.raise_for_status()
            return response.json()
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _extract_image_base64(payload: Dict[str, Any]) -> Optional[str]:
        data = payload.get("data") or []
        if data and isinstance(data[0], dict):
            value = data[0].get("b64_json")
            if value:
                return value
        value = payload.get("b64_json")
        if value:
            return value
        return None

    @staticmethod
    def _build_prompt(
        recommendation: Dict[str, Any], face_shape: Optional[str]
    ) -> str:
        display_name = recommendation.get("display_name") or recommendation.get(
            "name", "corte recomendado"
        )
        barber = recommendation.get("barber_instructions") or ""
        if isinstance(barber, dict):
            top = barber.get("top") or recommendation.get("volume_distribution", "")
            sides = barber.get("sides_and_nape") or recommendation.get(
                "side_treatment", ""
            )
            fringe = barber.get("fringe") or recommendation.get(
                "forehead_exposure", ""
            )
            finish = barber.get("finish") or recommendation.get("styling", "")
            instructions = (
                f"Topo: {top}. Laterais e nuca: {sides}. "
                f"Franja/frontal: {fringe}. Acabamento: {finish}."
            )
        else:
            instructions = str(barber)
            styling = recommendation.get("styling")
            if styling:
                instructions = f"{instructions} Finalizacao: {styling}."

        return (
            "Edite SOMENTE o cabelo da pessoa desta fotografia. Preserve com alta "
            "fidelidade a identidade, formato do rosto, olhos, nariz, boca, pele, "
            "orelhas, idade aparente, expressao, pose, roupa, iluminacao e fundo. "
            "Nao embeleze nem altere tracos faciais. Gere um resultado fotografico "
            "realista de barbearia/cabeleireiro. "
            f"Corte recomendado: {display_name}. "
            f"Formato facial considerado: {face_shape or 'nao informado'}. "
            f"Instrucoes tecnicas: {instructions} "
            "A implantacao capilar deve permanecer plausivel para a pessoa da foto."
        )
