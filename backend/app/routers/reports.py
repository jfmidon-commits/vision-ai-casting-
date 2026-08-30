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


async def _validate_report_resources(
    db: AsyncSession,
    tenant_id: UUID,
    profile_id: UUID,
    photoshoot_id: UUID,
):
    """Validate that report references stay inside the authenticated tenant.

    Foreign keys only validate that the referenced UUID exists; they do not
    guarantee that Profile/Photoshoot belong to the same tenant as the Report.
    This check prevents cross-tenant reference injection/IDOR and also ensures
    that the photoshoot actually belongs to the selected profile.
    """
    profile_result = await db.execute(
        select(Profile).where(
            and_(Profile.id == profile_id, Profile.tenant_id == tenant_id)
        )
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    photoshoot_result = await db.execute(
        select(Photoshoot).where(
            and_(
                Photoshoot.id == photoshoot_id,
                Photoshoot.tenant_id == tenant_id,
                Photoshoot.profile_id == profile_id,
            )
        )
    )
    photoshoot = photoshoot_result.scalar_one_or_none()
    if not photoshoot:
        raise HTTPException(status_code=404, detail="Photoshoot not found")

    return profile, photoshoot


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
    await _validate_report_resources(
        db=db,
        tenant_id=current_user.tenant_id,
        profile_id=report.profile_id,
        photoshoot_id=report.photoshoot_id,
    )

    # ReportCreate also carries generation options (sections/template/language)
    # that are not columns on the current Report model. Persist only mapped
    # Report fields instead of forwarding arbitrary schema fields to SQLAlchemy.
    db_report = Report(
        profile_id=report.profile_id,
        photoshoot_id=report.photoshoot_id,
        title=report.title,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
    )
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

    profile, _ = await _validate_report_resources(
        db=db,
        tenant_id=current_user.tenant_id,
        profile_id=report.profile_id,
        photoshoot_id=report.photoshoot_id,
    )
    # Avoid a lazy relationship fetch inside ReportService and ensure the profile
    # used in the PDF is exactly the tenant-scoped profile validated above.
    report.profile = profile

    pdf_url = await ReportService.generate_pdf(report)
    report.pdf_url = pdf_url
    await db.commit()
    return APIResponse(data={"pdf_url": pdf_url}, message="PDF generated")
