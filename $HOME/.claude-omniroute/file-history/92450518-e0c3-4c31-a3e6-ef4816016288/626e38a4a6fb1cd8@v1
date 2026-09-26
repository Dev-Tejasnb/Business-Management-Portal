"""Billing and Payment router endpoints."""

from __future__ import annotations

from typing import Optional, List

from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_service
from app.core.database import get_db_session as get_session
from app.core.exceptions import BadRequestError, NotFoundError, ValidationError
from app.modules.auth.dependencies import get_current_membership, require_permission
from app.modules.billing.schemas import (
    BillingCalculationPreview,
    BillingCreate,
    BillingItemCreate,
    BillingItemResponse,
    BillingItemUpdate,
    BillingListResponse,
    BillingResponse,
    BillingUpdate,
    InvoiceNumberResponse,
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentUpdate,
)
from app.modules.billing.service import BillingService, PaymentService
from app.models.billing import Billing, BillingItem, BillingStatus, Payment, PaymentStatus
from app.models.shop import Shop

router = APIRouter(prefix="/shops/{shop_id}/applications", tags=["billing"])


# Dependency providers
def get_billing_service(
    session: AsyncSession = Depends(get_session),
    audit_service=Depends(get_audit_service),
) -> BillingService:
    return BillingService(session, audit_service)


def get_payment_service(
    session: AsyncSession = Depends(get_session),
    audit_service=Depends(get_audit_service),
) -> PaymentService:
    return PaymentService(session, audit_service)


# ---------------------------------------------------------------------------
# Billing endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{application_id}/billing",
    response_model=BillingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("BILLING_CREATE"))],
)
async def create_billing(
    shop_id: int,
    application_id: int,
    billing_data: BillingCreate,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Create a new billing/invoice for an application."""
    # Verify application_id matches path parameter
    if billing_data.application_id != application_id:
        raise BadRequestError("Application ID in body must match path parameter.")

    return await billing_service.create_billing(
        shop_id=shop_id,
        billing_data=billing_data,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


@router.get(
    "/{application_id}/billing",
    response_model=BillingResponse,
    dependencies=[Depends(require_permission("BILLING_VIEW"))],
)
async def get_billing_by_application(
    shop_id: int,
    application_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Get billing record for an application."""
    billing = await billing_service.get_billing_by_application(application_id, shop_id)
    if not billing:
        raise NotFoundError("Billing record not found for this application.")

    # Enrich with related names
    await billing_service.session.refresh(billing, attribute_names=["application", "customer"])
    return billing


@router.get(
    "/billing/list",
    response_model=BillingListResponse,
    dependencies=[Depends(require_permission("BILLING_VIEW"))],
)
async def list_billings(
    shop_id: int,
    search: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    billing_status: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """List billing records for a shop with filters and pagination."""
    billings, total = await billing_service.list_billings(
        shop_id=shop_id,
        search=search,
        payment_status=payment_status,
        billing_status=billing_status,
        service_id=service_id,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return BillingListResponse(
        items=billings,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/billing/{billing_id}",
    response_model=BillingResponse,
    dependencies=[Depends(require_permission("BILLING_VIEW"))],
)
async def get_billing(
    shop_id: int,
    billing_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Get a billing record by ID."""
    billing = await billing_service.get_billing(billing_id, shop_id)
    if not billing:
        raise NotFoundError("Billing record not found.")
    return billing


@router.patch(
    "/billing/{billing_id}",
    response_model=BillingResponse,
    dependencies=[Depends(require_permission("BILLING_UPDATE"))],
)
async def update_billing(
    shop_id: int,
    billing_id: int,
    billing_data: BillingUpdate,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Update a billing record (only draft billings before payments)."""
    return await billing_service.update_billing(
        billing_id=billing_id,
        shop_id=shop_id,
        billing_data=billing_data,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


@router.post(
    "/billing/{billing_id}/issue",
    response_model=BillingResponse,
    dependencies=[Depends(require_permission("BILLING_UPDATE"))],
)
async def issue_billing(
    shop_id: int,
    billing_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Issue a draft billing."""
    return await billing_service.issue_billing(
        billing_id=billing_id,
        shop_id=shop_id,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


@router.post(
    "/billing/{billing_id}/void",
    response_model=BillingResponse,
    dependencies=[Depends(require_permission("BILLING_VOID"))],
)
async def void_billing(
    shop_id: int,
    billing_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Void a billing record (only if no payments exist)."""
    return await billing_service.void_billing(
        billing_id=billing_id,
        shop_id=shop_id,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


# ---------------------------------------------------------------------------
# Billing Items endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/billing/{billing_id}/items",
    response_model=BillingItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("BILLING_CHARGE"))],
)
async def add_billing_item(
    shop_id: int,
    billing_id: int,
    item_data: BillingItemCreate,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Add a line item to a billing record (only for draft billings)."""
    billing = await billing_service.get_billing(billing_id, shop_id)
    if not billing:
        raise NotFoundError("Billing record not found.")

    if billing.billing_status != BillingStatus.DRAFT.value:
        raise ValidationError("Can only add items to draft billings.")

    if billing.amount_paid > Decimal("0.00"):
        raise ValidationError("Cannot add items after payments have been recorded.")

    item = BillingItem(
        billing_id=billing_id,
        name=item_data.name,
        description=item_data.description,
        amount=item_data.amount,
        is_service_item=item_data.is_service_item,
        service_id=item_data.service_id,
        sort_order=item_data.sort_order,
    )

    billing_service.session.add(item)
    await billing_service.session.flush()

    # Recalculate totals
    from app.modules.billing.service import BillingService as BS
    bs = BS(billing_service.session)
    items_list = [
        BillingItemCreate(
            name=i.name,
            description=i.description,
            amount=i.amount,
            is_service_item=i.is_service_item,
            service_id=i.service_id,
            sort_order=i.sort_order,
        )
        for i in billing.items
    ]
    (
        service_amount,
        non_service_charges,
        subtotal,
        discount_amount,
        total_amount,
        balance_amount,
    ) = await bs._calculate_billing_totals(
        items_list,
        billing.discount_type,
        billing.discount_value,
    )

    billing.service_amount = service_amount
    billing.non_service_charges = non_service_charges
    billing.subtotal = subtotal
    billing.discount_amount = discount_amount
    billing.total_amount = total_amount
    billing.balance_amount = balance_amount

    # Update payment status
    if billing.amount_paid == Decimal("0.00"):
        billing.payment_status = PaymentStatus.UNPAID.value
    elif billing.amount_paid >= billing.total_amount:
        billing.payment_status = PaymentStatus.PAID.value
    else:
        billing.payment_status = PaymentStatus.PARTIALLY_PAID.value

    await billing_service.audit.record(
        action="billing.item_added",
        module="application",
        actor_user_id=membership.user_id,
        actor_role=membership.role,
        shop_id=shop_id,
        entity_type="BillingItem",
        entity_id=str(item.id),
        old_values=None,
        new_values={
            "billing_id": billing_id,
            "name": item.name,
            "amount": str(item.amount),
            "is_service_item": item.is_service_item,
        },
        session=billing_service.session,
    )

    await billing_service.session.commit()
    await billing_service.session.refresh(item)
    return item


@router.patch(
    "/billing/{billing_id}/items/{item_id}",
    response_model=BillingItemResponse,
    dependencies=[Depends(require_permission("BILLING_CHARGE"))],
)
async def update_billing_item(
    shop_id: int,
    billing_id: int,
    item_id: int,
    item_data: BillingItemUpdate,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Update a billing item (only for draft billings)."""
    billing = await billing_service.get_billing(billing_id, shop_id)
    if not billing:
        raise NotFoundError("Billing record not found.")

    if billing.billing_status != BillingStatus.DRAFT.value:
        raise ValidationError("Can only update items in draft billings.")

    if billing.amount_paid > Decimal("0.00"):
        raise ValidationError("Cannot update items after payments have been recorded.")

    item = await billing_service.session.scalar(
        select(BillingItem).where(
            BillingItem.id == item_id,
            BillingItem.billing_id == billing_id,
        )
    )
    if not item:
        raise NotFoundError("Billing item not found.")

    old_values = {
        "name": item.name,
        "description": item.description,
        "amount": str(item.amount),
        "is_service_item": item.is_service_item,
        "service_id": item.service_id,
        "sort_order": item.sort_order,
    }

    if item_data.name is not None:
        item.name = item_data.name
    if item_data.description is not None:
        item.description = item_data.description
    if item_data.amount is not None:
        item.amount = item_data.amount
    if item_data.is_service_item is not None:
        item.is_service_item = item_data.is_service_item
    if item_data.service_id is not None:
        item.service_id = item_data.service_id
    if item_data.sort_order is not None:
        item.sort_order = item_data.sort_order

    # Recalculate totals
    from app.modules.billing.service import BillingService as BS
    bs = BS(billing_service.session)
    items_list = [
        BillingItemCreate(
            name=i.name,
            description=i.description,
            amount=i.amount,
            is_service_item=i.is_service_item,
            service_id=i.service_id,
            sort_order=i.sort_order,
        )
        for i in billing.items
    ]
    (
        service_amount,
        non_service_charges,
        subtotal,
        discount_amount,
        total_amount,
        balance_amount,
    ) = await bs._calculate_billing_totals(
        items_list,
        billing.discount_type,
        billing.discount_value,
    )

    billing.service_amount = service_amount
    billing.non_service_charges = non_service_charges
    billing.subtotal = subtotal
    billing.discount_amount = discount_amount
    billing.total_amount = total_amount
    billing.balance_amount = balance_amount

    if billing.amount_paid == Decimal("0.00"):
        billing.payment_status = PaymentStatus.UNPAID.value
    elif billing.amount_paid >= billing.total_amount:
        billing.payment_status = PaymentStatus.PAID.value
    else:
        billing.payment_status = PaymentStatus.PARTIALLY_PAID.value

    await billing_service.audit.record(
        action="billing.item_updated",
        module="application",
        actor_user_id=membership.user_id,
        actor_role=membership.role,
        shop_id=shop_id,
        entity_type="BillingItem",
        entity_id=str(item.id),
        old_values=old_values,
        new_values={
            "name": item.name,
            "description": item.description,
            "amount": str(item.amount),
            "is_service_item": item.is_service_item,
            "service_id": item.service_id,
            "sort_order": item.sort_order,
        },
        session=billing_service.session,
    )

    await billing_service.session.commit()
    await billing_service.session.refresh(item)
    return item


@router.delete(
    "/billing/{billing_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("BILLING_CHARGE"))],
)
async def delete_billing_item(
    shop_id: int,
    billing_id: int,
    item_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Delete a billing item (only for draft billings)."""
    billing = await billing_service.get_billing(billing_id, shop_id)
    if not billing:
        raise NotFoundError("Billing record not found.")

    if billing.billing_status != BillingStatus.DRAFT.value:
        raise ValidationError("Can only delete items from draft billings.")

    if billing.amount_paid > Decimal("0.00"):
        raise ValidationError("Cannot delete items after payments have been recorded.")

    item = await billing_service.session.scalar(
        select(BillingItem).where(
            BillingItem.id == item_id,
            BillingItem.billing_id == billing_id,
        )
    )
    if not item:
        raise NotFoundError("Billing item not found.")

    await billing_service.session.delete(item)
    await billing_service.session.flush()

    # Recalculate totals
    from app.modules.billing.service import BillingService as BS
    bs = BS(billing_service.session)
    items_list = [
        BillingItemCreate(
            name=i.name,
            description=i.description,
            amount=i.amount,
            is_service_item=i.is_service_item,
            service_id=i.service_id,
            sort_order=i.sort_order,
        )
        for i in billing.items
    ]
    (
        service_amount,
        non_service_charges,
        subtotal,
        discount_amount,
        total_amount,
        balance_amount,
    ) = await bs._calculate_billing_totals(
        items_list,
        billing.discount_type,
        billing.discount_value,
    )

    billing.service_amount = service_amount
    billing.non_service_charges = non_service_charges
    billing.subtotal = subtotal
    billing.discount_amount = discount_amount
    billing.total_amount = total_amount
    billing.balance_amount = balance_amount

    if billing.amount_paid == Decimal("0.00"):
        billing.payment_status = PaymentStatus.UNPAID.value
    elif billing.amount_paid >= billing.total_amount:
        billing.payment_status = PaymentStatus.PAID.value
    else:
        billing.payment_status = PaymentStatus.PARTIALLY_PAID.value

    await billing_service.audit.record(
        action="billing.item_deleted",
        module="application",
        actor_user_id=membership.user_id,
        actor_role=membership.role,
        shop_id=shop_id,
        entity_type="BillingItem",
        entity_id=str(item_id),
        old_values={
            "name": item.name,
            "amount": str(item.amount),
            "is_service_item": item.is_service_item,
        },
        new_values=None,
        session=billing_service.session,
    )

    await billing_service.session.commit()
    return None


# ---------------------------------------------------------------------------
# Payment endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/billing/{billing_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("PAYMENT_CREATE"))],
)
async def create_payment(
    shop_id: int,
    billing_id: int,
    payment_data: PaymentCreate,
    payment_service: PaymentService = Depends(get_payment_service),
    membership=Depends(get_current_membership),
):
    """Record a payment for a billing."""
    return await payment_service.create_payment(
        shop_id=shop_id,
        billing_id=billing_id,
        payment_data=payment_data,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


@router.get(
    "/billing/{billing_id}/payments",
    response_model=PaymentListResponse,
    dependencies=[Depends(require_permission("PAYMENT_VIEW"))],
)
async def list_payments(
    shop_id: int,
    billing_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    payment_service: PaymentService = Depends(get_payment_service),
    membership=Depends(get_current_membership),
):
    """List payments for a billing record."""
    payments, total = await payment_service.list_payments_for_billing(
        billing_id=billing_id,
        shop_id=shop_id,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return PaymentListResponse(
        items=payments,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/billing/{billing_id}/payments/{payment_id}",
    response_model=PaymentResponse,
    dependencies=[Depends(require_permission("PAYMENT_VIEW"))],
)
async def get_payment(
    shop_id: int,
    billing_id: int,
    payment_id: int,
    payment_service: PaymentService = Depends(get_payment_service),
    membership=Depends(get_current_membership),
):
    """Get a payment by ID."""
    payment = await payment_service.get_payment(payment_id, shop_id)
    if not payment:
        raise NotFoundError("Payment not found.")
    if payment.billing_id != billing_id:
        raise NotFoundError("Payment not found for this billing.")
    return payment


@router.patch(
    "/billing/{billing_id}/payments/{payment_id}",
    response_model=PaymentResponse,
    dependencies=[Depends(require_permission("PAYMENT_UPDATE"))],
)
async def update_payment(
    shop_id: int,
    billing_id: int,
    payment_id: int,
    payment_data: PaymentUpdate,
    payment_service: PaymentService = Depends(get_payment_service),
    membership=Depends(get_current_membership),
):
    """Update payment metadata (notes, reference). Amount cannot be changed."""
    # Only allow updating non-financial fields
    update_data = payment_data.model_dump(exclude_unset=True)
    if "amount" in update_data:
        raise ValidationError("Payment amount cannot be modified after creation.")

    return await payment_service.update_payment(
        payment_id=payment_id,
        shop_id=shop_id,
        payment_data=update_data,
        actor_user_id=membership.user_id,
        actor_role=membership.role,
    )


# ---------------------------------------------------------------------------
# Billing calculation preview
# ---------------------------------------------------------------------------

@router.post(
    "/billing/preview",
    response_model=BillingCalculationPreview,
    dependencies=[Depends(require_permission("BILLING_VIEW"))],
)
async def preview_billing_calculation(
    shop_id: int,
    items: List[BillingItemCreate],
    discount_type: Optional[str] = None,
    discount_value: Optional[Decimal] = None,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Preview billing calculation without creating a record."""
    if not items:
        raise BadRequestError("At least one item is required.")

    (
        service_amount,
        non_service_charges,
        subtotal,
        discount_amount,
        total_amount,
        balance_amount,
    ) = await billing_service._calculate_billing_totals(
        items,
        discount_type,
        discount_value,
    )

    return BillingCalculationPreview(
        service_amount=service_amount,
        non_service_charges=non_service_charges,
        subtotal=subtotal,
        discount_type=discount_type,
        discount_value=discount_value,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )


@router.get(
    "/billing/next-invoice-number",
    response_model=InvoiceNumberResponse,
    dependencies=[Depends(require_permission("BILLING_VIEW"))],
)
async def get_next_invoice_number(
    shop_id: int,
    billing_service: BillingService = Depends(get_billing_service),
    membership=Depends(get_current_membership),
):
    """Get the next invoice number that would be generated."""
    invoice_number = await billing_service._generate_invoice_number(shop_id)
    return InvoiceNumberResponse(invoice_number=invoice_number)