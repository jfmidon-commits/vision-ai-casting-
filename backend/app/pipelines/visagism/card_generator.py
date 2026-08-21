"""PNG barber-card generator for the reproducible visagism pipeline."""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps


class BarberCardGenerator:
    """Render a 1080x1920 technical barber card without synthetic imagery."""

    WIDTH = 1080
    HEIGHT = 1920

    def generate(
        self,
        evidence_image_path: str,
        recommendation: Mapping[str, Any],
        output_path: str,
        title: str = "VISION - Especificacao de Corte",
        simulation_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), "white")
        draw = ImageDraw.Draw(canvas)

        title_font = self._font(42)
        heading_font = self._font(32)
        body_font = self._font(25)
        small_font = self._font(21)

        draw.text((60, 48), title, fill="black", font=title_font)
        draw.text(
            (60, 110),
            "Foto real de referencia + especificacao tecnica",
            fill="black",
            font=small_font,
        )

        image_box = (60, 170, 1020, 900)
        if simulation_path and os.path.isfile(simulation_path):
            # Side by side: real photo left, simulation right
            left_box = (60, 170, 530, 900)
            right_box = (550, 170, 1020, 900)
            self._paste_reference(canvas, evidence_image_path, left_box)
            self._paste_reference(canvas, simulation_path, right_box)
            # Labels
            draw.text((60, 910), "Foto real", fill="black", font=small_font)
            draw.text((550, 910), "Simulacao", fill="black", font=small_font)
        else:
            self._paste_reference(canvas, evidence_image_path, image_box)

        y = 945
        name = str(recommendation.get("name", "Corte nao selecionado"))
        draw.text((60, y), name, fill="black", font=heading_font)
        y += 60

        score = recommendation.get("compatibility_score")
        if isinstance(score, (int, float)):
            draw.text(
                (60, y),
                f"Compatibilidade: {float(score) * 100:.0f}%",
                fill="black",
                font=body_font,
            )
            y += 46

        technical = self._technical_lines(recommendation)
        for label, value in technical:
            y = self._wrapped_line(
                draw,
                y,
                label,
                value,
                body_font,
                max_chars=62,
            )

        y += 16
        draw.text((60, y), "Motivos", fill="black", font=heading_font)
        y += 48
        for reason in recommendation.get("reasons", [])[:3]:
            y = self._wrapped_text(draw, y, f"- {reason}", small_font, 70)

        risks = recommendation.get("risks", [])
        if risks:
            y += 10
            draw.text((60, y), "Cuidados", fill="black", font=heading_font)
            y += 48
            for risk in risks[:3]:
                y = self._wrapped_text(draw, y, f"- {risk}", small_font, 70)

        footer_y = self.HEIGHT - 135
        draw.line((60, footer_y, 1020, footer_y), fill="black", width=2)
        if simulation_path and os.path.isfile(simulation_path):
            footer_text = "Simulacao gerada por IA. Resultado pode variar. Sempre consulte um profissional."
        else:
            footer_text = "Sem simulacao fotorealista: nenhuma imagem artificial foi apresentada como resultado real."
        draw.text(
            (60, footer_y + 20),
            footer_text,
            fill="black",
            font=small_font,
        )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        canvas.save(output_path, format="PNG")
        return {
            "path": output_path,
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "format": "PNG",
            "reference_image": evidence_image_path,
            "simulation_image": simulation_path if (simulation_path and os.path.isfile(simulation_path)) else None,
            "synthetic_simulation_used": bool(simulation_path and os.path.isfile(simulation_path)),
        }

    @staticmethod
    def _paste_reference(
        canvas: Image.Image,
        image_path: str,
        box: tuple[int, int, int, int],
    ) -> None:
        with Image.open(image_path).convert("RGB") as source:
            target_width = box[2] - box[0]
            target_height = box[3] - box[1]
            fitted = ImageOps.contain(source, (target_width, target_height))
            x = box[0] + (target_width - fitted.width) // 2
            y = box[1] + (target_height - fitted.height) // 2
            canvas.paste(fitted, (x, y))

    @staticmethod
    def _technical_lines(
        recommendation: Mapping[str, Any],
    ) -> list[tuple[str, str]]:
        top = recommendation.get("top_cm", ())
        sides = recommendation.get("sides_mm", ())
        top_text = BarberCardGenerator._range_text(top, "cm")
        sides_text = BarberCardGenerator._range_text(sides, "mm")
        return [
            ("Topo", top_text),
            ("Laterais", sides_text),
            ("Degrade", str(recommendation.get("fade", "nao determinado"))),
            ("Conexao", str(recommendation.get("connection", "nao determinada"))),
            ("Direcao", str(recommendation.get("direction", "nao determinada"))),
            ("Acabamento", str(recommendation.get("finish", "nao determinado"))),
            ("Manutencao", str(recommendation.get("maintenance", "nao determinada"))),
            ("Nao fazer", str(recommendation.get("avoid", "nao determinado"))),
        ]

    @staticmethod
    def _range_text(value: Any, unit: str) -> str:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return f"{value[0]}-{value[1]} {unit}"
        return "nao determinado"

    @staticmethod
    def _font(size: int) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except OSError:
            return ImageFont.load_default()

    @staticmethod
    def _wrapped_line(
        draw: ImageDraw.ImageDraw,
        y: int,
        label: str,
        value: str,
        font: ImageFont.ImageFont,
        max_chars: int,
    ) -> int:
        return BarberCardGenerator._wrapped_text(
            draw,
            y,
            f"{label}: {value}",
            font,
            max_chars,
        )

    @staticmethod
    def _wrapped_text(
        draw: ImageDraw.ImageDraw,
        y: int,
        text: str,
        font: ImageFont.ImageFont,
        max_chars: int,
    ) -> int:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for line in lines:
            draw.text((60, y), line, fill="black", font=font)
            y += 36
        return y
