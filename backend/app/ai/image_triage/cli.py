"""
backend/app/ai/image_triage/cli.py

Interface de linha de comando para triagem local de imagens.

Uso:
    python -m app.ai.image_triage --source-dir /caminho/imagens --output-dir /caminho/saida
    
Ou standalone:
    python cli.py --source-dir /caminho/imagens
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.ai.image_triage.engine import ImageTriageEngine
from app.ai.image_triage.schemas import TriageInput, TriageConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parseia argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Triagem inteligente de imagens para visagismo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Triagem basica
  python cli.py --source-dir ./fotos_raw
  
  # Com pasta de saida customizada
  python cli.py --source-dir ./fotos_raw --output-dir ./fotos_selecionadas
  
  # Com qualidade minima mais alta
  python cli.py --source-dir ./fotos_raw --min-quality 0.6
  
  # Apenas analisar, nao copiar
  python cli.py --source-dir ./fotos_raw --no-copy
        """,
    )
    
    parser.add_argument(
        "--source-dir", "-s",
        required=True,
        help="Pasta com as imagens originais (nao sera modificada)",
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Pasta de saida para imagens selecionadas (default: source-dir_triage)",
    )
    
    parser.add_argument(
        "--min-quality", "-q",
        type=float,
        default=0.4,
        help="Qualidade minima geral (0-1, default: 0.4)",
    )
    
    parser.add_argument(
        "--min-width",
        type=int,
        default=400,
        help="Largura minima em pixels (default: 400)",
    )
    
    parser.add_argument(
        "--min-height",
        type=int,
        default=400,
        help="Altura minima em pixels (default: 400)",
    )
    
    parser.add_argument(
        "--max-per-angle",
        type=int,
        default=2,
        help="Maximo de imagens por angulo (default: 2)",
    )
    
    parser.add_argument(
        "--max-total",
        type=int,
        default=15,
        help="Maximo total de imagens selecionadas (default: 15)",
    )
    
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Apenas analisar, nao copiar imagens selecionadas",
    )
    
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Nao gerar relatorio Markdown",
    )
    
    parser.add_argument(
        "--profile-id",
        default=None,
        help="ID do perfil (para organizacao da pasta de saida)",
    )
    
    parser.add_argument(
        "--formats",
        default=".jpg,.jpeg,.png,.webp",
        help="Formatos de imagem suportados, separados por virgula (default: .jpg,.jpeg,.png,.webp)",
    )
    
    return parser.parse_args()


async def main() -> int:
    """Entry point do CLI."""
    args = parse_args()
    
    # Validar pasta fonte
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        logger.error(f"Pasta fonte nao encontrada: {source_dir}")
        return 1
    
    if not source_dir.is_dir():
        logger.error(f"Caminho nao e uma pasta: {source_dir}")
        return 1
    
    # Configuracao
    config = TriageConfig(
        min_width=args.min_width,
        min_height=args.min_height,
        min_overall_quality=args.min_quality,
        max_per_angle=args.max_per_angle,
        max_total=args.max_total,
        output_dir=args.output_dir,
        copy_selected=not args.no_copy,
        generate_report=not args.no_report,
        supported_formats=args.formats.split(","),
    )
    
    input_data = TriageInput(
        source_dir=str(source_dir),
        config=config,
        profile_id=args.profile_id,
    )
    
    logger.info("=" * 60)
    logger.info("Triagem Inteligente de Imagens - Vision AI Casting")
    logger.info("=" * 60)
    logger.info(f"Pasta fonte: {source_dir}")
    logger.info(f"Qualidade minima: {config.min_overall_quality}")
    logger.info(f"Max por angulo: {config.max_per_angle}")
    logger.info(f"Max total: {config.max_total}")
    logger.info("=" * 60)
    
    # Executar triagem
    engine = ImageTriageEngine(config)
    result = await engine.triage(input_data)
    
    # Resumo
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTADO DA TRIAGEM")
    logger.info("=" * 60)
    logger.info(f"Total encontradas: {result.total_images_found}")
    logger.info(f"Total analisadas: {result.total_images_analyzed}")
    logger.info(f"Faces detectadas: {result.total_faces_detected}")
    logger.info(f"Selecionadas: {result.selected_count}")
    logger.info(f"Rejeitadas: {result.rejected_count}")
    logger.info(f"Tempo: {result.processing_time_seconds:.1f}s")
    logger.info("")
    
    # Cobertura do protocolo
    coverage = result.get_protocol_coverage()
    coverage_score = result.get_protocol_coverage_score()
    
    logger.info("Cobertura do Protocolo:")
    for angle, has in coverage.items():
        status = "✅" if has else "❌"
        logger.info(f"  {status} {angle}")
    logger.info(f"  Score: {coverage_score:.0%}")
    logger.info("")
    
    # Detalhes por ângulo
    if result.by_angle:
        logger.info("Imagens Selecionadas por Angulo:")
        for angle, candidates in sorted(result.by_angle.items()):
            logger.info(f"\n  [{angle}] — {len(candidates)} imagem(ns)")
            for c in candidates:
                logger.info(f"    #{c.rank_in_category} {c.filename} — qualidade: {c.overall_quality:.2f}")
    
    # Pasta de saída
    if result.output_dir:
        logger.info(f"\nPasta de saida: {result.output_dir}")
    if result.report_path:
        logger.info(f"Relatorio: {result.report_path}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Triagem concluida!")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
