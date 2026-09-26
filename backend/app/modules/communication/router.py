"""Communication API endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_service
from app.modules.auth.dependencies import get_current_user
from app.core.permissions import require_permission
from app.db.session import get_db_session
from app.models.receipt import CommunicationHistory, CommunicationStatus
from app.modules.communication.service import CommunicationService
from app.modules.billing.receipt_service import ReceiptService
from app.models.receipt import Receipt
from app.models.billing import Billing, Payment
from app.models.shop import Shop

router = APIRouter(
    prefix="/shops/{shop_id}/communications",
    tags=["communications"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_communication(
    shop_id: int,
    channel: str,
    recipient: str,
    receipt_id: Optional[int] = None,
    subject: Optional[str] = None,
    request: Request = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_permission("COMMUNICATION_SEND")),
) -> dict:
    """Create and send a communication for a receipt."""
    # Verify shop access
    shop_result = await session.execute(
        select(Shop).where(Shop.id == shop_id)
    )
    shop = shop_result.scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    # Verify receipt exists and belongs to shop
    receipt = None
    if receipt_id:
        receipt_result = await session.execute(
            select(Receipt).where(
                and_(Receipt.id == receipt_id, Receipt.shop_id == shop_id)
            )
        )
        receipt = receipt_result.scalar_one_or_none()
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt not found or does not belong to this shop"
            )

    # Initialize services
    communication_service = CommunicationService(session)

    # Send communication
    communication = await communication_service.send_receipt(
        receipt=receipt,
        channel=channel,
        recipient=recipient,
        subject=subject,
        shop_id=shop_id,
        sent_by=current_user["id"],
    )

    # Record audit log
    audit_service = get_audit_service()
    await audit_service.record_from_request(
        request,
        action="communication.send",
        module="communication",
        actor_user_id=current_user["id"],
        actor_role=current_user.get("role"),
        shop_id=shop_id,
        entity_type="communication",
        entity_id=communication.id,
        extra={
            "channel": channel,
            "recipient": recipient,
            "receipt_id": receipt_id,
        }
    )

    return {
        "id": communication.id,
        "channel": communication.channel,
        "recipient": communication.recipient,
        "status": communication.status,
        "sent_at": communication.sent_at,
        "created_at": communication.created_at,
    }


@router.get("/", response_model=List[dict])
async def list_communications(
    shop_id: int,
    receipt_id: Optional[int] = Query(None, description="Filter by receipt ID"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, lte=100),
    offset: int = Query(0, gte=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_permission("COMMUNICATION_VIEW")),
) -> List[dict]:
    """List communication history for a shop."""
    # Verify shop access
    shop_result = await session.execute(
        select(Shop).where(Shop.id == shop_id)
    )
    shop = shop_result.scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    # Build query
    stmt = select(CommunicationHistory).where(
        CommunicationHistory.shop_id == shop_id
    )

    if receipt_id:
        stmt = stmt.where(CommunicationHistory.receipt_id == receipt_id)
    if channel:
        stmt = stmt.where(CommunicationHistory.channel == channel)
    if status:
        stmt = stmt.where(CommunicationHistory.status == status)

    stmt = (
        stmt.order_by(CommunicationHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(stmt)
    communications = result.scalars().all()

    return [
        {
            "id": comm.id,
            "channel": comm.channel,
            "recipient": comm.recipient,
            "subject": comm.subject,
            "status": comm.status,
            "provider": comm.provider,
            "sent_at": comm.sent_at,
            "created_at": comm.created_at,
            "receipt_id": comm.receipt_id,
        }
        for comm in communications
    ]


@router.get("/{communication_id}", response_model=dict)
async def get_communication(
    shop_id: int,
    communication_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_permission("COMMUNICATION_VIEW")),
) -> dict:
    """Get communication details."""
    # Verify shop access
    shop_result = await session.execute(
        select(Shop).where(Shop.id == shop_id)
    )
    shop = shop_result.scalar_one_or_none()
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )

    # Get communication
    result = await session.execute(
        select(CommunicationHistory).where(
            and_(
                CommunicationHistory.id == communication_id,
                CommunicationHistory.shop_id == shop_id,
            )
        )
    )
    communication = result.scalar_one_or_none()

    if not communication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Communication not found"
        )

    return {
        "id": communication.id,
        "channel": communication.channel,
        "recipient": communication.recipient,
        "subject": communication.subject,
        "status": communication.status,
        "provider": communication.provider,
        "provider_message_id": communication.provider_message_id,
        "error_message": communication.error_message,
        "sent_at": communication.sent_at,
        "created_at": communication.created_at,
        "updated_at": communication.updated_at,
        "receipt_id": communication.receipt_id,
        "billing_id": communication.billing_id,
        "payment_id": communication.payment_id,
    }


# Import needed for and_
from sqlalchemy import and_