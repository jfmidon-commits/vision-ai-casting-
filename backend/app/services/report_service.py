from app.config import settings
from app.services.storage_service import StorageService
from app.services.pdf_service import PDFService

class ReportService:
    @staticmethod
    async def generate_pdf(report):
        report_data = {
            "id": str(report.id),
            "profile_name": report.profile.full_name if hasattr(report, "profile") else "Unknown",
            "version": report.version,
            "confidence_index": float(report.confidence_index) if report.confidence_index else 0.5,
            "executive_summary": report.executive_summary,
            "technical_analysis": report.technical_analysis,
            "artistic_analysis": report.artistic_analysis,
            "commercial_analysis": report.commercial_analysis,
            "development_plan": report.development_plan,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }

        pdf_url = await PDFService.generate_report_pdf(report_data)
        return pdf_url

    @staticmethod
    async def generate_executive_summary(analysis_results):
        summary_parts = []

        if analysis_results.get("casting"):
            casting = analysis_results["casting"]
            summary_parts.append(f"Tipos de personagem: {', '.join(casting.get('character_types', [])[:3])}")

        if analysis_results.get("facial_structure"):
            facial = analysis_results["facial_structure"]
            summary_parts.append(f"Forma do rosto: {facial.get('face_shape', 'N/A')}")

        return " | ".join(summary_parts) if summary_parts else "Análise completa disponível no relatório detalhado."
