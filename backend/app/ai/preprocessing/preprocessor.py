import cv2
import numpy as np
from PIM import Image, ImageEnhance
from typing import Dict, List
import aiohttp
import asyncio
import io

class ImagePreprocessor:
    TARGET_SIZE = 2048
    THUMBNAIL_SIZE = 512

    async def process_batch(self, photos: List[Dict]) -> List[Dict]:
        tasks = [self.process_single(photo) for photo in photos]
        return await asyncio.gather(*tasks)

    async def process_single(self, photo: Dict) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(photo["url"]) as response:
                image_bytes = await response.read()

    img = Image.open(io.BytesIO(image_bytes))

    if img.mode != "RGB":
        img = img.convert("RGB")

    img = self._resize_maintaining_ratio(img, self.TARGET_SIZE)
    img = self._normalize_colors(img)
    img = self._auto_enhance(img)

    return {
        "photo_id": photo["id"],
        "image": img,
        "dimensions": f"{img.width}x{img.height}",
        "format": img.format or "PEG",
        "mode": img.mode,
    }

    def _resize_maintaining_ratio(self, img: Image.Image, max_size: int) -> Image.Image:
        if max(img.width, img.height) > max_size:
            ratio = max_size / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCOZ)
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
