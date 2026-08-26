import asyncio
import io
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageEnhance

from app.services.storage_service import StorageService
from app.utils.logger import get_logger
from app.utils.memory import log_rss

logger = get_logger(__name__)


class ImagePreprocessor:
    """Preprocessor optimized for low-memory Render instances."""

    TARGET_SIZE = 1024
    THUMBNAIL_SIZE = 512
    MAX_IMAGE_BYTES = 20 * 1024 * 1024

    async def process_batch(
        self,
        photos: List[Dict],
        analysis_id: Optional[str] = None,
    ) -> List[Dict]:
        """Process photos sequentially to avoid concurrent memory spikes."""
        results = []
        for photo in photos:
            result = await self.process_single(photo, analysis_id=analysis_id)
            results.append(result)
        return results

    async def process_single(
        self,
        photo: Dict,
        analysis_id: Optional[str] = None,
    ) -> Dict:
        photo_id = photo.get("id", "unknown")
        photo_url = photo.get("url", "")
        rss_analysis_id = analysis_id or "unknown"

        logger.info("[PREPROCESS] photo=%s stage=start analysis_id=%s", photo_id, rss_analysis_id)

        logger.info(
            "[PREPROCESS] photo=%s stage=download_start analysis_id=%s",
            photo_id,
            rss_analysis_id,
        )
        log_rss(f"preprocess_{photo_id}_download_start", rss_analysis_id)
        try:
            image_bytes = await asyncio.wait_for(
                asyncio.to_thread(
                    StorageService.read_object_from_url,
                    photo_url,
                    self.MAX_IMAGE_BYTES,
                ),
                timeout=30,
            )
        except asyncio.TimeoutError as exc:
            logger.error(
                "[PREPROCESS] photo=%s stage=download_timeout analysis_id=%s",
                photo_id,
                rss_analysis_id,
            )
            raise RuntimeError(
                f"Timeout ao baixar foto {photo_id} do storage"
            ) from exc
        except Exception as exc:
            logger.error(
                "[PREPROCESS] photo=%s stage=download_error analysis_id=%s error=%s",
                photo_id,
                rss_analysis_id,
                exc,
            )
            raise RuntimeError(
                f"Falha ao baixar foto {photo_id}: {exc}"
            ) from exc

        if not image_bytes:
            raise ValueError(f"Foto {photo_id} retornou corpo vazio")

        logger.info(
            "[PREPROCESS] photo=%s stage=download_end analysis_id=%s bytes=%d",
            photo_id,
            rss_analysis_id,
            len(image_bytes),
        )
        log_rss(f"preprocess_{photo_id}_download_end", rss_analysis_id)

        logger.info(
            "[PREPROCESS] photo=%s stage=decode_start analysis_id=%s",
            photo_id,
            rss_analysis_id,
        )
        log_rss(f"preprocess_{photo_id}_decode_start", rss_analysis_id)
        try:
            img = await asyncio.to_thread(self._decode_image, image_bytes)
        except Exception as exc:
            logger.error(
                "[PREPROCESS] photo=%s stage=decode_error analysis_id=%s error=%s",
                photo_id,
                rss_analysis_id,
                exc,
            )
            raise ValueError(f"Foto {photo_id} não é imagem válida") from exc

        logger.info(
            "[PREPROCESS] photo=%s stage=decode_end analysis_id=%s dims=%dx%d",
            photo_id,
            rss_analysis_id,
            img.width,
            img.height,
        )
        log_rss(f"preprocess_{photo_id}_decode_end", rss_analysis_id)

        logger.info(
            "[PREPROCESS] photo=%s stage=resize_start analysis_id=%s",
            photo_id,
            rss_analysis_id,
        )
        img = await asyncio.to_thread(
            self._resize_maintaining_ratio,
            img,
            self.TARGET_SIZE,
        )
        logger.info(
            "[PREPROCESS] photo=%s stage=resize_end analysis_id=%s dims=%dx%d",
            photo_id,
            rss_analysis_id,
            img.width,
            img.height,
        )
        log_rss(f"preprocess_{photo_id}_resize_end", rss_analysis_id)

        logger.info(
            "[PREPROCESS] photo=%s stage=normalize_start analysis_id=%s",
            photo_id,
            rss_analysis_id,
        )
        img = await asyncio.to_thread(self._normalize_and_enhance, img)
        logger.info(
            "[PREPROCESS] photo=%s stage=normalize_end analysis_id=%s",
            photo_id,
            rss_analysis_id,
        )
        log_rss(f"preprocess_{photo_id}_normalize_end", rss_analysis_id)

        logger.info("[PREPROCESS] photo=%s stage=end analysis_id=%s", photo_id, rss_analysis_id)
        return {
            "photo_id": photo_id,
            "image": img,
            "dimensions": f"{img.width}x{img.height}",
            "format": img.format or "JPEG",
            "mode": img.mode,
        }

    def _decode_image(self, image_bytes: bytes) -> Image.Image:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    def _normalize_and_enhance(self, img: Image.Image) -> Image.Image:
        img = self._normalize_colors(img)
        return self._auto_enhance(img)

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
