import os
import tempfile
from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings
from app.services.storage_service import StorageService

class PDFService:
    @staticmethod
    async def generate_report_pdf(report_data: Dict, output_path: Optional[str] = None) -> str:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                Image, PageBreak, ListFlowable, ListItem, HRFlowable
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from io import BytesIO
            import requests
        except ImportError:
            # Fallback: create a simple HTML-based PDF
            return await PDFService._generate_html_pdf(report_data, output_path)

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#16213e"),
            spaceAfter=12,
            spaceBefore=12,
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
        )

        story = []

        # Header
        story.append(Paragraph("VISION AI CASTING", title_style))
        story.append(Paragraph("Relatório de Análise Profissional", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        # Metadata
        meta_data = [
            ["Perfil:", report_data.get("profile_name", "N/A")],
            ["Data:", datetime.now().strftime("%d/%m/%Y")],
            ["Versão:", f"{report_data.get('version', '1.0')}"],
            ["Confiança:", f"{(report_data.get('confidence_index', 0.5) * 100):.0f}%"],
        ]
        meta_table = Table(meta_data, colWidths=[2 * inch, 4 * inch])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.3 * inch))

        # Executive Summary
        if report_data.get("executive_summary"):
            story.append(Paragraph("Resumo Executivo", heading_style))
            story.append(Paragraph(report_data["executive_summary"], body_style))
            story.append(Spacer(1, 0.2 * inch))

        # Technical Analysis
        if report_data.get("technical_analysis"):
            story.append(Paragraph("Análise Técnica", heading_style))
            tech = report_data["technical_analysis"]

            if isinstance(tech, dict):
                for key, value in tech.items():
                    if isinstance(value, dict):
                        story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}</b>", body_style))
                        for k, v in value.items():
                            story.append(Paragraph(f"• {k.replace('_', ' ').title()}: {v}", body_style))
                    else:
                        story.append(Paragraph(f"• {key.replace('_', ' ').title()}: {value}", body_style))
            story.append(Spacer(1, 0.2 * inch))

        # Development Plan
        if report_data.get("development_plan"):
            story.append(Paragraph("Plano de Desenvolvimento", heading_style))
            plan = report_data["development_plan"]

            if isinstance(plan, dict):
                for timeframe, actions in plan.items():
                    story.append(Paragraph(f"<b>{timeframe.replace('_', ' ').title()}</b>", body_style))
                    if isinstance(actions, list):
                        for action in actions:
                            story.append(Paragraph(f"• {action}", body_style))
                    story.append(Spacer(1, 0.1 * inch))

        # Footer
        story.append(Spacer(1, 0.5 * inch))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Paragraph(
            "Este relatório foi gerado automaticamente pela plataforma Vision AI Casting. "
            "As recomendações são baseadas em análise de dados visuais e padrões de mercado.",
            ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.grey)
        ))

        doc.build(story)

        # Save to file or return bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            return output_path

        # Upload to S3
        filename = f"report_{report_data.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return await PDFService._upload_pdf(pdf_bytes, filename)

    @staticmethod
    async def _generate_html_pdf(report_data: Dict, output_path: Optional[str] = None) -> str:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Relatório Vision AI Casting</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
                .header {{ text-align: center; border-bottom: 3px solid #1a1a2e; padding-bottom: 20px; margin-bottom: 30px; }}
                .header h1 {{ color: #1a1a2e; font-size: 28px; margin: 0; }}
                .header h2 {{ color: #666; font-size: 16px; margin: 10px 0 0; font-weight: normal; }}
                .meta {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 30px; }}
                .meta table {{ width: 100%; }}
                .meta td {{ padding: 8px; }}
                .meta td:first-child {{ font-weight: bold; width: 30%; }}
                .section {{ margin-bottom: 30px; }}
                .section h3 {{ color: #16213e; font-size: 18px; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }}
                .section p {{ line-height: 1.6; text-align: justify; }}
                .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 11px; color: #999; text-align: center; }}
                .score {{ display: inline-block; background: #1a1a2e; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>VISION AI CASTING</h1>
                <h2>Relatório de Análise Profissional</h2>
            </div>

            <div class="meta">
                <table>
                    <tr><td>Perfil:</td><td>{report_data.get('profile_name', 'N/A')}</td></tr>
                    <tr><td>Data:</td><td>{datetime.now().strftime('%d/%m/%Y')}</td></tr>
                    <tr><td>Versão:</td><td>{report_data.get('version', '1.0')}</td></tr>
                    <tr><td>Índice de Confiança:</td><td><span class="score">{(report_data.get('confidence_index', 0.5) * 100):.0f}%</span></td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Resumo Executivo</h3>
                <p>{report_data.get('executive_summary', 'Análise completa disponível.')}</p>
            </div>

            <div class="section">
                <h3>Plano de Desenvolvimento</h3>
                <p>Recomendações personalizadas baseadas na análise de IA.</p>
            </div>

            <div class="footer">
                <p>Este relatório foi gerado automaticamente pela plataforma Vision AI Casting.<br>
                As recomendações são baseadas em análise de dados visuais e padrões de mercado.</p>
            </div>
        </body>
        </html>
        """

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return output_path

        # Convert HTML to PDF using weasyprint if available
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            filename = f"report_{report_data.get('id', 'unknown')}.pdf"
            return await PDFService._upload_pdf(pdf_bytes, filename)
        except ImportError:
            # Return HTML as fallback
            filename = f"report_{report_data.get('id', 'unknown')}.html"
            return await PDFService._upload_text(html_content, filename)

    @staticmethod
    async def _upload_pdf(pdf_bytes: bytes, filename: str) -> str:
        import boto3
        from io import BytesIO

        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=f"reports/{filename}",
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/reports/{filename}"

    @staticmethod
    async def _upload_text(content: str, filename: str) -> str:
        import boto3

        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=f"reports/{filename}",
            Body=content.encode("utf-8"),
            ContentType="text/html",
        )

        return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/reports/{filename}"
