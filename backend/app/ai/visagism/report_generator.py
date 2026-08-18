"""
backend/app/ai/visagism/report_generator.py

Gerador de relatorio humano do VisagismAgent.

Transforma o JSON canonico em linguagem profissional, compreensivel
e justificada. Cada recomendacao e explicada em termos de:
- O QUE foi observado
- COMO isso afeta a percepcao visual
- POR QUE a recomendacao funciona
- O QUE o profissional deve fazer
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from app.ai.visagism.schemas import VisagismAnalysisResult, FaceShape


class VisagismReportGenerator:
    """
    Gerador de relatorios humanos a partir do JSON canonico.
    
    Produz texto profissional, nao generico. Cada paragrafo
    justifica uma conclusao com referencia as evidencias.
    """
    
    # Templates de descricao de formato facial
    FACE_SHAPE_DESCRIPTIONS = {
        FaceShape.OVAL: (
            "Formato oval — considerado o mais equilibrado proporcionalmente. "
            "A altura e aproximadamente 1.3 a 1.5 vezes a largura, com curvas suaves "
            "e mandibula levemente mais estreita que a testa."
        ),
        FaceShape.ROUND: (
            "Formato redondo — largura e altura aproximadamente iguais, com curvas "
            "predominantes e angulos suaves. A mandibula e arredondada, sem arestas marcantes."
        ),
        FaceShape.SQUARE: (
            "Formato quadrado — largura da mandibula aproximadamente igual a largura "
            "da testa, com angulos pronunciados na mandibula e queixo. A estrutura ossea "
            "e visualmente forte."
        ),
        FaceShape.HEART: (
            "Formato coracao — testa mais larga que a mandibula, com queixo pontiagudo "
            "ou estreito. A atencao visual converge naturalmente para a regiao inferior do rosto."
        ),
        FaceShape.DIAMOND: (
            "Formato diamante — zigomas (bochechas) como ponto mais largo do rosto, "
            "com testa e queixo mais estreitos. Estrutura angular com pontos de interesse "
            "nas laterais."
        ),
        FaceShape.OBLONG: (
            "Formato oblongo — altura facial significativamente maior que a largura, "
            "gerando percepcao de alongamento. Mandibula e testa com larguras similares."
        ),
        FaceShape.TRIANGULAR: (
            "Formato triangular — mandibula mais larga que a testa, com queixo "
            "pronunciado. A base do rosto e visualmente mais pesada que o topo."
        ),
        FaceShape.MIXED: (
            "Formato misto — caracteristicas de multiplos formatos sem predominancia "
            "clara. Requer analise mais granular das proporcoes individuais."
        ),
        FaceShape.UNKNOWN: (
            "Formato nao determinado com confianca suficiente — dados insuficientes "
            "ou inconsistencia entre fontes de analise."
        ),
    }
    
    def generate(self, result: VisagismAnalysisResult) -> str:
        """
        Gera relatorio humano completo a partir do resultado JSON.
        
        Args:
            result: VisagismAnalysisResult com todos os campos preenchidos
            
        Returns:
            String com relatorio formatado
        """
        sections = []
        
        # Cabecalho
        sections.append(self._generate_header(result))
        
        # Resumo executivo
        sections.append(self._generate_executive_summary(result))
        
        # Analise facial detalhada
        sections.append(self._generate_facial_analysis(result))
        
        # Analise de cabelo
        if result.hair:
            sections.append(self._generate_hair_analysis(result))
        
        # Recomendacoes
        if result.primary_recommendation:
            sections.append(self._generate_recommendations(result))
        
        # Manutencao
        if result.general_maintenance_schedule:
            sections.append(self._generate_maintenance(result))
        
        # Limitacoes
        if result.analysis_limitations:
            sections.append(self._generate_limitations(result))
        
        # Rodape
        sections.append(self._generate_footer(result))
        
        return "\n\n".join(sections)
    
    def _generate_header(self, result: VisagismAnalysisResult) -> str:
        """Gera cabecalho do relatorio."""
        confidence_pct = result.overall_confidence * 100
        
        header = f"""RELATORIO DE ANALISE DE VISAGISMO CAPILAR
Vision AI Casting — v{result.version}
Gerado em: {result.generated_at.strftime('%d/%m/%Y %H:%M')}
ID de correlacao: {result.correlation_id or 'N/A'}

NIVEL DE CONFIANCA GLOBAL: {confidence_pct:.0f}%
{result.overall_confidence_explanation}

FOTOS ANALISADAS: {result.photos_analyzed} | USAVEIS: {result.photos_usable} | REJEITADAS: {result.photos_rejected}"""
        
        return header
    
    def _generate_executive_summary(self, result: VisagismAnalysisResult) -> str:
        """Gera resumo executivo."""
        
        shape_desc = self.FACE_SHAPE_DESCRIPTIONS.get(
            result.face_shape_category,
            "Formato nao classificado."
        )
        
        summary = f"""RESUMO EXECUTIVO

Formato Facial: {result.face_shape_category.value.upper()}
{shape_desc}

Pontos Fortes Visuais:"""
        
        for strength in result.visual_strengths:
            summary += f"\n  • {strength}"
        
        if result.visual_strengths:
            summary += "\n"
        
        summary += "\nAspectos que Podem Ser Modificados:"
        for aspect in result.modifiable_aspects:
            summary += f"\n  • {aspect}"
        
        if result.modifiable_aspects:
            summary += "\n"
        
        summary += "\nAspectos que Devem Ser Preservados:"
        for aspect in result.preserve_aspects:
            summary += f"\n  • {aspect}"
        
        return summary
    
    def _generate_facial_analysis(self, result: VisagismAnalysisResult) -> str:
        """Gera analise facial detalhada por regiao."""
        
        analysis = "ANALISE FACIAL DETALHADA\n"
        
        # Proporcoes
        if result.facial_proportions:
            analysis += "\nProporcoes Faciais Medidas:\n"
            for prop in result.facial_proportions:
                ideal = prop.ideal_range
                ideal_str = f"(ideal: {ideal[0]:.2f}-{ideal[1]:.2f})" if ideal else ""
                analysis += (
                    f"  • {prop.name}: {prop.value:.3f} {ideal_str} — "
                    f"{prop.classification}\n"
                )
        
        # Regioes
        regions_map = {
            'Testa': result.forehead,
            'Sobrancelhas': result.eyebrows,
            'Regiao Ocular': result.eyes,
            'Nariz': result.nose,
            'Zigomas': result.cheekbones,
            'Boca': result.mouth,
            'Mandibula': result.jaw,
            'Queixo': result.chin,
            'Pescoco': result.neck,
        }
        
        for region_name, region in regions_map.items():
            if region and region.observations:
                analysis += f"\n{region_name}:\n"
                for obs in region.observations:
                    analysis += f"  • {obs}\n"
                analysis += f"  [confianca: {region.confidence:.0%}]\n"
        
        # Assimetrias
        if result.asymmetries and result.asymmetries.is_detectable:
            analysis += f"\nAssimetrias Detectadas:\n"
            analysis += f"  • {result.asymmetries.description}\n"
            analysis += f"  • Regioes afetadas: {', '.join(result.asymmetries.affected_regions)}\n"
            analysis += f"  • Severidade: {result.asymmetries.severity}\n"
            if result.asymmetries.compensatory_design:
                analysis += f"  • Design compensatorio: {result.asymmetries.compensatory_design}\n"
        
        # Relacao cabeca/pescoco/ombros
        if result.head_neck_shoulder:
            hns = result.head_neck_shoulder
            analysis += f"\nRelacao Cabeca/Pescoco/Ombros:\n"
            if hns.neck_length:
                analysis += f"  • Pescoco: {hns.neck_length.value}\n"
            if hns.shoulder_width_relative:
                analysis += f"  • Ombros: {hns.shoulder_width_relative.value}\n"
            if hns.head_to_body_ratio:
                analysis += f"  • Proporcao cabeca/corpo: {hns.head_to_body_ratio:.2f}\n"
            if hns.posture_observation:
                analysis += f"  • Observacao postural: {hns.posture_observation}\n"
        
        return analysis
    
    def _generate_hair_analysis(self, result: VisagismAnalysisResult) -> str:
        """Gera analise do cabelo."""
        
        hair = result.hair
        if not hair:
            return ""
        
        analysis = "ANALISE DO CABELO\n"
        
        if hair.hairline_shape:
            analysis += f"\nImplantacao Capilar:\n"
            analysis += f"  • Forma: {hair.hairline_shape}\n"
            if hair.hairline_height:
                analysis += f"  • Altura: {hair.hairline_height}\n"
            if hair.forehead_exposure is not None:
                analysis += f"  • Exposicao da testa: {hair.forehead_exposure:.0%}\n"
        
        if hair.texture and hair.texture != "unknown":
            analysis += f"\nTextura: {hair.texture.value}\n"
        
        if hair.thickness and hair.thickness != "unknown":
            analysis += f"Espessura do fio: {hair.thickness.value}\n"
        
        if hair.volume and hair.volume != "unknown":
            analysis += f"Volume geral: {hair.volume.value}\n"
        
        if any([hair.crown_volume, hair.side_volume, hair.nape_volume]):
            analysis += "\nDistribuicao de Volume:\n"
            if hair.crown_volume:
                analysis += f"  • Coroa: {hair.crown_volume.value}\n"
            if hair.side_volume:
                analysis += f"  • Laterais: {hair.side_volume.value}\n"
            if hair.nape_volume:
                analysis += f"  • Nuca: {hair.nape_volume.value}\n"
            if hair.occipital_volume:
                analysis += f"  • Occipital: {hair.occipital_volume.value}\n"
        
        if hair.posterior_assessment:
            analysis += f"\nAvaliacao Posterior: {hair.posterior_assessment}\n"
        
        return analysis
    
    def _generate_recommendations(self, result: VisagismAnalysisResult) -> str:
        """Gera secao de recomendacoes."""
        
        recs = "RECOMENDACOES DE CORTE\n"
        
        # Recomendacao principal
        if result.primary_recommendation:
            primary = result.primary_recommendation
            recs += f"\n{'='*60}\n"
            recs += f"RECOMENDACAO PRINCIPAL (#{primary.rank})\n"
            recs += f"{'='*60}\n"
            recs += f"Corte: {primary.name}\n"
            recs += f"Categoria: {primary.category}\n"
            recs += f"Confianca: {primary.confidence:.0%}\n"
            recs += f"\nJUSTIFICATIVA TECNICA:\n{primary.justification}\n"
            
            recs += f"\nPARAMETROS TECNICOS:\n"
            if primary.recommended_length_top:
                recs += f"  • Topo: {primary.recommended_length_top}\n"
            if primary.recommended_length_sides:
                recs += f"  • Laterais: {primary.recommended_length_sides}\n"
            if primary.recommended_length_nape:
                recs += f"  • Nuca: {primary.recommended_length_nape}\n"
            if primary.recommended_length_occipital:
                recs += f"  • Occipital: {primary.recommended_length_occipital}\n"
            
            recs += f"  • Distribuicao de volume: {primary.volume_distribution}\n"
            recs += f"  • Exposicao da testa: {primary.forehead_exposure_recommendation.value}\n"
            recs += f"  • Tratamento lateral: {primary.side_treatment.value}\n"
            
            if primary.advantages:
                recs += f"\nVANTAGENS PARA ESTE ROSTO:\n"
                for adv in primary.advantages:
                    recs += f"  + {adv}\n"
            
            if primary.disadvantages:
                recs += f"\nPOSSIVEIS DESVANTAGENS:\n"
                for dis in primary.disadvantages:
                    recs += f"  - {dis}\n"
            
            recs += f"\nNIVEL DE MUDANCA: {primary.change_level.value}\n"
            recs += f"DIFICULDADE DE MANUTENCAO: {primary.maintenance_difficulty.value}\n"
            if primary.maintenance_frequency:
                recs += f"FREQUENCIA: {primary.maintenance_frequency}\n"
            
            recs += f"\nINSTRUCOES TECNICAS AO PROFISSIONAL:\n{primary.technical_instructions}\n"
            
            recs += f"\nSTYLING DIARIO:\n{primary.styling_requirements}\n"
            if primary.styling_products:
                recs += f"Produtos recomendados: {', '.join(primary.styling_products)}\n"
            if primary.styling_time_estimate:
                recs += f"Tempo estimado: {primary.styling_time_estimate}\n"
        
        # Alternativas
        for alt in result.alternative_recommendations:
            recs += f"\n{'='*60}\n"
            recs += f"ALTERNATIVA #{alt.rank}: {alt.name}\n"
            recs += f"{'='*60}\n"
            recs += f"Confianca: {alt.confidence:.0%}\n"
            recs += f"\n{alt.justification}\n"
            recs += f"\nNivel de mudanca: {alt.change_level.value}\n"
            recs += f"Manutencao: {alt.maintenance_difficulty.value}\n"
            recs += f"\nInstrucoes tecnicas: {alt.technical_instructions}\n"
        
        # Cortes desaconselhados
        if result.discouraged_cuts:
            recs += f"\n{'='*60}\n"
            recs += "CORTES DESACONSELHADOS\n"
            recs += f"{'='*60}\n"
            for disc in result.discouraged_cuts:
                recs += f"\n  ✗ {disc.name}\n"
                recs += f"    Motivo: {disc.reason}\n"
                if disc.alternative:
                    recs += f"    Alternativa: {disc.alternative}\n"
        
        return recs
    
    def _generate_maintenance(self, result: VisagismAnalysisResult) -> str:
        """Gera secao de manutencao."""
        return f"""MANUTENCAO

{result.general_maintenance_schedule}

Recomendacoes gerais:
  • Ajustar o corte nas primeiras 48h se necessario
  • Fotografar o resultado para comparacao futura
  • Registrar feedback do cliente no sistema
  • Reavaliar visagismo a cada 3-6 meses ou apos mudancas significativas"""
    
    def _generate_limitations(self, result: VisagismAnalysisResult) -> str:
        """Gera secao de limitacoes."""
        
        limitations = "LIMITACOES DA ANALISE\n\n"
        limitations += "Esta analise foi conduzida com base em imagens e possui as seguintes limitacoes:\n"
        
        for lim in result.analysis_limitations:
            limitations += f"  • {lim}\n"
        
        limitations += "\nRecomenda-se validacao por profissional de visagismo para decisoes finais."
        
        return limitations
    
    def _generate_footer(self, result: VisagismAnalysisResult) -> str:
        """Gera rodape do relatorio."""
        return f"""---

Este relatorio foi gerado automaticamente pelo Vision AI Casting.
Todas as recomendacoes sao baseadas em analise computacional e devem
ser validadas por profissional qualificado.

Para auditoria das evidencias, consulte o JSON canonico associado
(correlation_id: {result.correlation_id or 'N/A'}).

© Vision AI Casting — {result.generated_at.year}"""
