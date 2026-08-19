import asyncio
import io
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import aiohttp
import numpy as np
from PIL import Image, ImageEnhance


class PreprocessedPhoto(dict):
    """Dictionary compatible with legacy analyzers and attribute-based pipeline code."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class ImagePreprocessor:
    TARGET_SIZE = 2048
    THUMBNAIL_SIZE = 512

    async def process_batch(self, photos: List[Dict]) -> List[PreprocessedPhoto]:
        tasks = [self.process_single(photo) for photo in photos]
        return await asyncio.gather(*tasks)

    async def process_single(self, photo: Dict) -> PreprocessedPhoto:
        image_bytes = await self._read_image_bytes(photo["url"])
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode != "RGB":
            img = img.convert("RGB")

        original_format = img.format or "JPEG"
        img = self._resize_maintaining_ratio(img, self.TARGET_SIZE)
        img = self._normalize_colors(img)
        img = self._auto_enhance(img)

        photo_id = photo.get("id") or photo.get("photo_id")
        return PreprocessedPhoto(
            id=photo_id,
            photo_id=photo_id,
            url=photo.get("url", ""),
            angle=photo.get("angle", "front"),
            quality_score=photo.get("quality_score"),
            is_usable=photo.get("is_usable", True),
            image=img,
            dimensions=f"{img.width}x{img.height}",
            format=original_format,
            mode=img.mode,
        )

    async def _read_image_bytes(self, source: str) -> bytes:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            async with aiohttp.ClientSession() as session:
                async with session.get(source) as response:
                    response.raise_for_status()
                    return await response.read()

        local_path = Path(source.removeprefix("file://"))
        if not local_path.exists():
            raise FileNotFoundError(f"Imagem nao encontrada: {source}")
        return local_path.read_bytes()

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
        img[:, :, 0] *= avg_gray / max(avg_r, 1e-6)
        img[:, :, 1] *= avg_gray / max(avg_g, 1e-6)
        img[:, :, 2] *= avg_gray / max(avg_b, 1e-6)
        return np.clip(img, 0, 1)

    def _auto_enhance(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(1.2)
