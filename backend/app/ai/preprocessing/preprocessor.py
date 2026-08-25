import cv2
import numpy as np
from PIL import Image, ImageEnhance
from typing import Dict, List
import io
import asyncio
import logging

from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """Preprocessor otimizado para baixa memória (Render 512Mi)."""
    TARGET_SIZE = 1024  # Reduzido de 2048 para economizar ~75% de memória
    THUMBNAIL_SIZE = 512

    async def process_batch(self, photos: List[Dict]) -> List[Dict]:
        """Processa fotos sequencialmente em vez de simultaneamente para evitar OOM."""
        results = []
        for photo in photos:
            result = await self.process_single(photo)
            results.append(result)
        return results

    async def process_single(self, photo: Dict) -> Dict:
        photo_id = photo.get("id", "unknown")
        photo_url = photo.get("url", "")

        logger.info("Preprocessing photo %s", photo_id)

        # Download via S3 SDK com timeout via asyncio.wait_for
        try:
            image_bytes = await asyncio.wait_for(
                asyncio.to_thread(StorageService.read_object_from_url, photo_url),
                timeout=30,
            )
        except asyncio.TimeoutError as exc:
            logger.error("Timeout downloading photo %s after 30s", photo_id)
            raise RuntimeError(
                f"Timeout ao baixar foto {photo_id} do storage"
            ) from exc
        except Exception as exc:
            logger.error("Failed to download photo %s: %s", photo_id, exc)
            raise RuntimeError(
                f"Falha ao baixar foto {photo_id}: {exc}"
            ) from exc

        if not image_bytes or len(image_bytes) == 0:
            raise ValueError(f"Foto {photo_id} retornou corpo vazio")

        logger.info("Photo %s: %d bytes", photo_id, len(image_bytes))

        # Open with PIL
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:
            logger.error(
                "Photo %s invalid (hex: %s): %s",
                photo_id,
                image_bytes[:32].hex(),
                exc,
            )
            raise ValueError(f"Foto {photo_id} não é imagem válida") from exc

        if img.mode != "RGB":
            img = img.convert("RGB")

        img = self._resize_maintaining_ratio(img, self.TARGET_SIZE)
        img = self._normalize_colors(img)
        img = self._auto_enhance(img)

        return {
            "photo_id": photo_id,
            "image": img,
            "dimensions": f"{img.width}x{img.height}",
            "format": img.format or "JPEG",
            "mode": img.mode,
        }

    def _resize_maintaining_ratio(self, img: Image.Image, max_size: int) -> Image.Image:
        if max(img.width, img.height) > max_size:
            ratio = max_size / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        return img

    def _normalize_colors(self, img: Image.Image) -> Image.Image:
        img_array = np.array(img).astype(np.float32) / 255.0
        img_array = self._white_balance(img_array)
        img_array = np.power(img_array, 1.0 / 2.2)
        img_array = np.clip(img_array * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(img_array)

    def _white_balance(self, img: np.ndarray) -> np.ndarray:
        avg_r = np.mean(img[:, :, 0])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 2])
        avg_gray = (avg_r + avg_g + avg_b) / 3
        img[:, :, 0] *= avg_gray / avg_r
        img[:, :, 1] *= avg_gray / avg_g
        img[:, :, 2] *= avg_gray / avg_b
        return np.clip(img, 0, 1)

    def _auto_enhance(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        return img
