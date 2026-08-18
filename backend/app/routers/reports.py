from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.database import get_db
from app.models import Report, Profile, Photoshoot
from app.schemas import ReportCreate, ReportResponse, APIResponse
from app.middleware.auth import get_current_user
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

@router.get("", response_model=APIResponse)
async def list_reports(
    profile_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Report).where(Report.tenant_id == current_user.tenant_id)
    if profile_id:
        query = query.where(Report.profile_id == profile_id)

    result = await db.execute(query)
    reports = result.scalars().all()
    return APIResponse(data=[ReportResponse.model_validate(r) for r in reports])

@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report: ReportCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_report = Report(**report.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return APIResponse(data=ReportResponse.model_validate(db_report), message="Report created")

@router.get("/{report_id}", response_model=APIResponse)
async def get_report(
    report_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Report).where(
            and_(Report.id == report_id, Report.tenant_id == current_user.tenant_id)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return APIResponse(data=ReportResponse.model_validate(report))

@router.post("/{report_id}/generate-pdf", response_model=APIResponse)
async def generate_pdf(
    report_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Report).where(
            and_(Report.id == report_id, Report.tenant_id == current_user.tenant_id)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_url = await ReportService.generate_pdf(report)
    report.pdf_url = pdf_url
    await db.commit()
    return APIResponse(data={"pdf_url": pdf_url}, message="PDF generated")
