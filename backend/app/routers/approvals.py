"""
Approvals Router - API REST para workflow de aprovação.

Gerencia o ciclo de vida das aprovações humanas no sistema.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import User, ContentApproval
from app.schemas import APIResponse
from app.core.event_bus import emit_event, VisionEventType

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.get("", response_model=APIResponse)
async def list_approvals(
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista aprovações do tenant do usuário."""
    query = select(ContentApproval).where(
        ContentApproval.tenant_id == current_user.tenant_id
    )
    if status:
        query = query.where(ContentApproval.status == status)

    result = await db.execute(query)
    approvals = result.scalars().all()
    return APIResponse(data=[{
        "id": str(a.id),
        "content_item_id": str(a.content_item_id),
        "approval_type": a.approval_type,
        "status": a.status,
        "requested_at": a.requested_at.isoformat() if a.requested_at else None,
        "responded_at": a.responded_at.isoformat() if a.responded_at else None,
    } for a in approvals])


@router.post("/{approval_id}/approve", response_model=APIResponse)
async def approve(
    approval_id: UUID,
    notes: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aprova um item."""
    result = await db.execute(
        select(ContentApproval).where(
            and_(ContentApproval.id == approval_id, ContentApproval.tenant_id == current_user.tenant_id)
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "approved"
    approval.approved_by = current_user.id
    approval.responded_at = datetime.utcnow()
    approval.response_notes = notes

    await db.commit()

    await emit_event(
        event_type=VisionEventType.APPROVAL_APPROVED,
        payload={"approval_id": str(approval_id), "approved_by": str(current_user.id)},
    )

    return APIResponse(message="Approved successfully")


@router.post("/{approval_id}/reject", response_model=APIResponse)
async def reject(
    approval_id: UUID,
    notes: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rejeita um item."""
    result = await db.execute(
        select(ContentApproval).where(
            and_(ContentApproval.id == approval_id, ContentApproval.tenant_id == current_user.tenant_id)
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "rejected"
    approval.approved_by = current_user.id
    approval.responded_at = datetime.utcnow()
    approval.response_notes = notes

    await db.commit()

    await emit_event(
        event_type=VisionEventType.APPROVAL_REJECTED,
        payload={"approval_id": str(approval_id)},
    )

    return APIResponse(message="Rejected successfully")


@router.post("/{approval_id}/revision", response_model=APIResponse)
async def request_revision(
    approval_id: UUID,
    notes: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Solicita revisão de um item."""
    result = await db.execute(
        select(ContentApproval).where(
            and_(ContentApproval.id == approval_id, ContentApproval.tenant_id == current_user.tenant_id)
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    approval.status = "revision_requested"
    approval.revision_notes = notes
    approval.responded_at = datetime.utcnow()

    await db.commit()

    await emit_event(
        event_type=VisionEventType.APPROVAL_REVISION_REQUESTED,
        payload={"approval_id": str(approval_id), "revision_notes": notes},
    )

    return APIResponse(message="Revision requested")
