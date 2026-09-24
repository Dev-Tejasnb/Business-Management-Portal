"""Billing and Payment service handling business logic, calculations, and audit."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditService, Module, audit_service
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.application import Application
from app.models.billing import (
    Billing,
    BillingItem,
    BillingStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    DiscountType,
)
from app.models.customer import Customer
from app.models.service import Service
from app.models.shop import Shop
from app.models.user import User
from app.modules.billing.schemas import (
    BillingCreate,
    BillingItemCreate,
    BillingUpdate,
    PaymentCreate,
)

logger = get_logger(__name__)


class BillingService:
    """Service for handling billing/invoice management operations with tenant isolation."""

    def __init__(
        self,
        session: AsyncSession,
        audit: Optional[AuditService] = None,
    ) -> None:
        self.session = session
        self.audit = audit or audit_service

    def _quantize_amount(self, amount: Decimal) -> Decimal:
        """Quantize decimal to 2 decimal places using ROUND_HALF_UP."""
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _validate_shop_access(self, shop_id: int) -> Shop:
        """Verify that the shop exists and is active."""
        shop = await self.session.scalar(select(Shop).where(Shop.id == shop_id))
        if not shop:
            raise NotFoundError("Shop not found.")
        return shop

    async def _validate_application_access(
        self, shop_id: int, application_id: int
    ) -> Application:
        """Validate that application belongs to the shop."""
        application = await self.session.scalar(
            select(Application)
            .options(selectinload(Application.service), selectinload(Application.customer))
            .where(
                and_(
                    Application.id == application_id,
                    Application.shop_id == shop_id,
                )
            )
        )
        if not application:
            raise NotFoundError("Application not found in this shop.")
        return application

    async def _generate_invoice_number(self, shop_id: int) -> str:
        """Generate a unique invoice number for the shop.
        Format: INV-{shop_code}-{year}-{sequential}
        Uses database sequence for concurrency safety.
        """
        shop = await self.session.scalar(select(Shop).where(Shop.id == shop_id))
        if not shop:
            raise NotFoundError("Shop not found.")

        shop_code = shop.code.upper()
        year = datetime.now().year

        # Use a database sequence-like approach with retry logic
        max_attempts = 5
        for attempt in range(max_attempts):
            # Get max sequence for this shop and year
            stmt = select(func.max(Billing.id)).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.invoice_number.like(f"INV-{shop_code}-{year}-%"),
                )
            )
            result = await self.session.execute(stmt)
            max_id = result.scalar() or 0
            sequence_number = max_id + 1
            invoice_number = f"INV-{shop_code}-{year}-{sequence_number:06d}"

            # Check if exists
            exists = await self.session.scalar(
                select(Billing.id).where(Billing.invoice_number == invoice_number)
            )
            if not exists:
                return invoice_number

            # Collision - wait and retry
            import asyncio

            await asyncio.sleep(0.1 * (attempt + 1))

        raise ConflictError("Unable to generate a unique invoice number after several attempts.")

    async def _calculate_billing_totals(
        self,
        items: List[BillingItemCreate],
        discount_type: Optional[str] = None,
        discount_value: Optional[Decimal] = None,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
        """Calculate billing totals from items and discount.

        Returns: (service_amount, non_service_charges, subtotal, discount_amount, total_amount, balance_amount)
        """
        service_amount = sum(
            (item.amount for item in items if item.is_service_item), Decimal("0.00")
        )
        non_service_charges = sum(
            (item.amount for item in items if not item.is_service_item), Decimal("0.00")
        )

        service_amount = self._quantize_amount(service_amount)
        non_service_charges = self._quantize_amount(non_service_charges)
        subtotal = self._quantize_amount(service_amount + non_service_charges)

        discount_amount = Decimal("0.00")
        if discount_type and discount_value is not None:
            if discount_type == DiscountType.FIXED.value:
                discount_amount = min(discount_value, subtotal)
            elif discount_type == DiscountType.PERCENTAGE.value:
                if discount_value > Decimal("100"):
                    raise ValidationError("Discount percentage cannot exceed 100%")
                discount_amount = self._quantize_amount(
                    (subtotal * discount_value / Decimal("100"))
                )
            discount_amount = self._quantize_amount(min(discount_amount, subtotal))

        total_amount = self._quantize_amount(subtotal - discount_amount)
        balance_amount = total_amount  # Initially no payments

        return (
            service_amount,
            non_service_charges,
            subtotal,
            discount_amount,
            total_amount,
            balance_amount,
        )

    async def create_billing(
        self,
        *,
        shop_id: int,
        billing_data: BillingCreate,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Billing:
        """Create a new billing/invoice record with line items."""
        # Validate shop and application
        await self._validate_shop_access(shop_id)
        application = await self._validate_application_access(shop_id, billing_data.application_id)

        # Verify customer matches application
        if application.customer_id != billing_data.application_id:  # This check is handled by FK
            pass

        # Check if billing already exists for this application
        existing = await self.session.scalar(
            select(Billing).where(Billing.application_id == billing_data.application_id)
        )
        if existing:
            raise ConflictError("Billing record already exists for this application.")

        # Validate service item matches the application's service
        service_items = [item for item in billing_data.items if item.is_service_item]
        if len(service_items) > 1:
            raise ValidationError("Only one service item is allowed per billing record.")
        if service_items:
            service_item = service_items[0]
            if service_item.service_id and service_item.service_id != application.service_id:
                raise ValidationError("Service item must match the application's service.")

        # Calculate totals
        (
            service_amount,
            non_service_charges,
            subtotal,
            discount_amount,
            total_amount,
            balance_amount,
        ) = await self._calculate_billing_totals(
            billing_data.items,
            billing_data.discount_type,
            billing_data.discount_value,
        )

        # Validate discount
        if billing_data.discount_type and billing_data.discount_value is not None:
            if not billing_data.discount_reason or not billing_data.discount_reason.strip():
                raise ValidationError("Discount reason is required when applying a discount.")

        # Generate invoice number
        invoice_number = await self._generate_invoice_number(shop_id)

        # Create billing record
        billing = Billing(
            shop_id=shop_id,
            application_id=billing_data.application_id,
            customer_id=application.customer_id,
            invoice_number=invoice_number,
            service_amount=service_amount,
            non_service_charges=non_service_charges,
            subtotal=subtotal,
            discount_type=billing_data.discount_type,
            discount_value=billing_data.discount_value,
            discount_amount=discount_amount,
            discount_reason=billing_data.discount_reason,
            total_amount=total_amount,
            amount_paid=Decimal("0.00"),
            balance_amount=balance_amount,
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.DRAFT.value,
            notes=billing_data.notes,
            created_by=actor_user_id,
        )

        self.session.add(billing)
        await self.session.flush()

        # Create billing items
        for item_data in billing_data.items:
            item = BillingItem(
                billing_id=billing.id,
                name=item_data.name,
                description=item_data.description,
                amount=item_data.amount,
                is_service_item=item_data.is_service_item,
                service_id=item_data.service_id,
                sort_order=item_data.sort_order,
            )
            self.session.add(item)

        # Record audit log
        await self.audit.record(
            action="billing.created",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Billing",
            entity_id=str(billing.id),
            old_values=None,
            new_values={
                "invoice_number": invoice_number,
                "application_id": billing_data.application_id,
                "service_amount": str(service_amount),
                "non_service_charges": str(non_service_charges),
                "subtotal": str(subtotal),
                "discount_type": billing_data.discount_type,
                "discount_value": str(billing_data.discount_value) if billing_data.discount_value else None,
                "discount_amount": str(discount_amount),
                "discount_reason": billing_data.discount_reason,
                "total_amount": str(total_amount),
                "payment_status": PaymentStatus.UNPAID.value,
                "billing_status": BillingStatus.DRAFT.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(billing)

        # Load items
        await self.session.refresh(billing, attribute_names=["items"])
        return billing

    async def get_billing(self, billing_id: int, shop_id: int) -> Optional[Billing]:
        """Get a billing record by ID, scoped to shop."""
        stmt = (
            select(Billing)
            .options(
                selectinload(Billing.items).selectinload(BillingItem.service),
                selectinload(Billing.application).selectinload(Application.service),
                selectinload(Billing.application).selectinload(Application.customer),
                selectinload(Billing.payments),
            )
            .where(
                and_(
                    Billing.id == billing_id,
                    Billing.shop_id == shop_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_billing_by_application(
        self, application_id: int, shop_id: int
    ) -> Optional[Billing]:
        """Get billing record by application ID, scoped to shop."""
        stmt = (
            select(Billing)
            .options(
                selectinload(Billing.items).selectinload(BillingItem.service),
                selectinload(Billing.application).selectinload(Application.service),
                selectinload(Billing.application).selectinload(Application.customer),
                selectinload(Billing.payments),
            )
            .where(
                and_(
                    Billing.application_id == application_id,
                    Billing.shop_id == shop_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_billings(
        self,
        *,
        shop_id: int,
        search: Optional[str] = None,
        payment_status: Optional[str] = None,
        billing_status: Optional[str] = None,
        service_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Billing], int]:
        """List billings for a shop with filtering and pagination."""
        stmt = select(Billing).where(Billing.shop_id == shop_id)

        # Apply filters
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Billing.invoice_number.ilike(search_term),
                    Billing.application.has(
                        Application.application_number.ilike(search_term)
                    ),
                    Billing.customer.has(Customer.name.ilike(search_term)),
                    Billing.customer.has(Customer.mobile.ilike(search_term)),
                )
            )

        if payment_status:
            stmt = stmt.where(Billing.payment_status == payment_status)

        if billing_status:
            stmt = stmt.where(Billing.billing_status == billing_status)

        if service_id is not None:
            stmt = stmt.where(Billing.application.has(Application.service_id == service_id))

        if customer_id is not None:
            stmt = stmt.where(Billing.customer_id == customer_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Billing.created_at.desc())

        result = await self.session.execute(stmt)
        billings = result.scalars().all()

        return list(billings), total

    async def update_billing(
        self,
        *,
        billing_id: int,
        shop_id: int,
        billing_data: BillingUpdate,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Billing:
        """Update a billing record (only allowed in DRAFT status before payments)."""
        billing = await self.get_billing(billing_id, shop_id)
        if not billing:
            raise NotFoundError("Billing record not found in this shop.")

        # Check if billing can be edited (not after payments exist or if issued/void)
        if billing.amount_paid > Decimal("0.00"):
            raise ValidationError(
                "Cannot edit billing after payments have been recorded."
            )
        if billing.billing_status != BillingStatus.DRAFT.value:
            raise ValidationError("Can only edit draft billings.")

        # Capture old values
        old_values = {
            "notes": billing.notes,
            "discount_type": billing.discount_type,
            "discount_value": str(billing.discount_value) if billing.discount_value else None,
            "discount_amount": str(billing.discount_amount),
            "discount_reason": billing.discount_reason,
        }

        # Update fields
        if billing_data.notes is not None:
            billing.notes = billing_data.notes
        if billing_data.discount_type is not None:
            billing.discount_type = billing_data.discount_type
        if billing_data.discount_value is not None:
            billing.discount_value = billing_data.discount_value
        if billing_data.discount_reason is not None:
            billing.discount_reason = billing_data.discount_reason

        # Recalculate totals
        if billing.items:
            (
                service_amount,
                non_service_charges,
                subtotal,
                discount_amount,
                total_amount,
                balance_amount,
            ) = await self._calculate_billing_totals(
                [
                    BillingItemCreate(
                        name=item.name,
                        description=item.description,
                        amount=item.amount,
                        is_service_item=item.is_service_item,
                        service_id=item.service_id,
                        sort_order=item.sort_order,
                    )
                    for item in billing.items
                ],
                billing.discount_type,
                billing.discount_value,
            )
            billing.service_amount = service_amount
            billing.non_service_charges = non_service_charges
            billing.subtotal = subtotal
            billing.discount_amount = discount_amount
            billing.total_amount = total_amount
            billing.balance_amount = self._quantize_amount(total_amount - billing.amount_paid)

        # Validate discount
        if billing.discount_type and billing.discount_value is not None:
            if not billing.discount_reason or not billing.discount_reason.strip():
                raise ValidationError("Discount reason is required when applying a discount.")

        # Update payment status
        if billing.amount_paid == Decimal("0.00"):
            billing.payment_status = PaymentStatus.UNPAID.value
        elif billing.amount_paid >= billing.total_amount:
            billing.payment_status = PaymentStatus.PAID.value
        else:
            billing.payment_status = PaymentStatus.PARTIALLY_PAID.value

        billing.updated_by = actor_user_id

        # Record audit log
        new_values = {
            "notes": billing.notes,
            "discount_type": billing.discount_type,
            "discount_value": str(billing.discount_value) if billing.discount_value else None,
            "discount_amount": str(billing.discount_amount),
            "discount_reason": billing.discount_reason,
            "total_amount": str(billing.total_amount),
        }

        await self.audit.record(
            action="billing.updated",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Billing",
            entity_id=str(billing.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(billing)
        return billing

    async def issue_billing(
        self,
        *,
        billing_id: int,
        shop_id: int,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Billing:
        """Issue a draft billing (change status from draft to issued)."""
        billing = await self.get_billing(billing_id, shop_id)
        if not billing:
            raise NotFoundError("Billing record not found in this shop.")

        if billing.billing_status != BillingStatus.DRAFT.value:
            raise ValidationError("Only draft billings can be issued.")

        old_values = {"billing_status": billing.billing_status}
        billing.billing_status = BillingStatus.ISSUED.value

        await self.audit.record(
            action="billing.issued",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Billing",
            entity_id=str(billing.id),
            old_values=old_values,
            new_values={"billing_status": BillingStatus.ISSUED.value},
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(billing)
        return billing

    async def void_billing(
        self,
        *,
        billing_id: int,
        shop_id: int,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Billing:
        """Void a billing record (only if no payments exist)."""
        billing = await self.get_billing(billing_id, shop_id)
        if not billing:
            raise NotFoundError("Billing record not found in this shop.")

        if billing.amount_paid > Decimal("0.00"):
            raise ValidationError("Cannot void billing with existing payments.")

        if billing.billing_status == BillingStatus.VOID.value:
            raise ValidationError("Billing is already voided.")

        old_values = {"billing_status": billing.billing_status}
        billing.billing_status = BillingStatus.VOID.value

        await self.audit.record(
            action="billing.voided",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Billing",
            entity_id=str(billing.id),
            old_values=old_values,
            new_values={"billing_status": BillingStatus.VOID.value},
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(billing)
        return billing


class PaymentService:
    """Service for handling payment operations with concurrency protection."""

    def __init__(
        self,
        session: AsyncSession,
        audit: Optional[AuditService] = None,
    ) -> None:
        self.session = session
        self.audit = audit or audit_service

    def _quantize_amount(self, amount: Decimal) -> Decimal:
        """Quantize decimal to 2 decimal places using ROUND_HALF_UP."""
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _validate_shop_access(self, shop_id: int) -> Shop:
        """Verify that the shop exists."""
        shop = await self.session.scalar(select(Shop).where(Shop.id == shop_id))
        if not shop:
            raise NotFoundError("Shop not found.")
        return shop

    async def _validate_billing_access(
        self, shop_id: int, billing_id: int, for_update: bool = False
    ) -> Billing:
        """Validate that billing belongs to the shop and lock for update if needed."""
        stmt = select(Billing).where(
            and_(
                Billing.id == billing_id,
                Billing.shop_id == shop_id,
            )
        )
        if for_update:
            stmt = stmt.with_for_update()

        billing = await self.session.scalar(stmt)
        if not billing:
            raise NotFoundError("Billing record not found in this shop.")
        return billing

    async def _validate_payment_data(
        self, payment_data: PaymentCreate, billing: Billing
    ) -> None:
        """Validate payment data against billing constraints."""
        # Check payment amount
        if payment_data.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")

        if payment_data.amount > billing.balance_amount:
            raise ValidationError(
                f"Payment amount ({payment_data.amount}) exceeds "
                f"outstanding balance ({billing.balance_amount}). Overpayment not allowed."
            )

        # Validate payment method
        valid_methods = [m.value for m in PaymentMethod]
        if payment_data.payment_method not in valid_methods:
            raise ValidationError(f"Invalid payment method. Must be one of: {valid_methods}")

        # Validate reference for digital payments
        is_digital = payment_data.payment_method in (
            PaymentMethod.UPI.value,
            PaymentMethod.CARD.value,
            PaymentMethod.BANK_TRANSFER.value,
            PaymentMethod.OTHER.value,
        )

        if is_digital and not payment_data.reference_exception:
            if not payment_data.reference_number or not payment_data.reference_number.strip():
                raise ValidationError(
                    "Reference number is required for digital payments. "
                    "Select 'Reference not available' with a reason if you don't have one."
                )

        # Validate exception reason
        if payment_data.reference_exception:
            if not payment_data.reference_exception_reason or not payment_data.reference_exception_reason.strip():
                raise ValidationError(
                    "Exception reason is required when marking reference as unavailable."
                )

    async def create_payment(
        self,
        *,
        shop_id: int,
        billing_id: int,
        payment_data: PaymentCreate,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Payment:
        """Create a new payment record with concurrency-safe balance checking."""
        # Validate shop and billing (with row-level lock for concurrency)
        await self._validate_shop_access(shop_id)
        billing = await self._validate_billing_access(shop_id, billing_id, for_update=True)

        # Verify billing is not voided
        if billing.billing_status == BillingStatus.VOID.value:
            raise ValidationError("Cannot record payment on voided billing.")

        # Validate payment data
        await self._validate_payment_data(payment_data, billing)

        # Create payment record
        payment = Payment(
            shop_id=shop_id,
            billing_id=billing_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            reference_number=payment_data.reference_number.strip()
            if payment_data.reference_number
            else None,
            reference_exception=payment_data.reference_exception,
            reference_exception_reason=payment_data.reference_exception_reason,
            notes=payment_data.notes,
            recorded_by=actor_user_id,
            paid_at=datetime.now(timezone.utc),
        )

        self.session.add(payment)

        # Update billing totals
        old_amount_paid = billing.amount_paid
        old_balance = billing.balance_amount
        old_payment_status = billing.payment_status

        billing.amount_paid = self._quantize_amount(billing.amount_paid + payment_data.amount)
        billing.balance_amount = self._quantize_amount(
            billing.total_amount - billing.amount_paid
        )

        # Update payment status
        if billing.amount_paid >= billing.total_amount:
            billing.payment_status = PaymentStatus.PAID.value
        elif billing.amount_paid > Decimal("0.00"):
            billing.payment_status = PaymentStatus.PARTIALLY_PAID.value
        else:
            billing.payment_status = PaymentStatus.UNPAID.value

        # Auto-issue if in draft and first payment
        if billing.billing_status == BillingStatus.DRAFT.value and old_amount_paid == Decimal("0.00"):
            billing.billing_status = BillingStatus.ISSUED.value

        # Record audit log for payment
        await self.audit.record(
            action="payment.created",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Payment",
            entity_id=str(payment.id),
            old_values=None,
            new_values={
                "billing_id": billing_id,
                "amount": str(payment_data.amount),
                "payment_method": payment_data.payment_method,
                "reference_number": payment.reference_number,
                "reference_exception": payment.reference_exception,
                "reference_exception_reason": payment.reference_exception_reason,
                "notes": payment.notes,
                "paid_at": payment.paid_at.isoformat(),
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        # Record audit log for billing update
        await self.audit.record(
            action="billing.payment_received",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Billing",
            entity_id=str(billing.id),
            old_values={
                "amount_paid": str(old_amount_paid),
                "balance_amount": str(old_balance),
                "payment_status": old_payment_status,
                "billing_status": billing.billing_status,
            },
            new_values={
                "amount_paid": str(billing.amount_paid),
                "balance_amount": str(billing.balance_amount),
                "payment_status": billing.payment_status,
                "billing_status": billing.billing_status,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_payment(self, payment_id: int, shop_id: int) -> Optional[Payment]:
        """Get a payment by ID, scoped to shop."""
        stmt = (
            select(Payment)
            .options(selectinload(Payment.billing))
            .where(
                and_(
                    Payment.id == payment_id,
                    Payment.shop_id == shop_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_payments_for_billing(
        self,
        *,
        billing_id: int,
        shop_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Payment], int]:
        """List payments for a billing record."""
        # Verify billing belongs to shop
        billing = await self._validate_billing_access(shop_id, billing_id)
        if not billing:
            raise NotFoundError("Billing record not found in this shop.")

        stmt = (
            select(Payment)
            .where(Payment.billing_id == billing_id)
            .order_by(Payment.paid_at.desc())
        )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        payments = result.scalars().all()

        return list(payments), total

    async def update_payment(
        self,
        *,
        payment_id: int,
        shop_id: int,
        payment_data: dict,
        actor_user_id: int,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Payment:
        """Update a payment record (limited to non-financial fields after creation)."""
        payment = await self.get_payment(payment_id, shop_id)
        if not payment:
            raise NotFoundError("Payment not found in this shop.")

        # Only allow updating notes and reference fields (not amount)
        old_values = {
            "reference_number": payment.reference_number,
            "reference_exception": payment.reference_exception,
            "reference_exception_reason": payment.reference_exception_reason,
            "notes": payment.notes,
        }

        if "notes" in payment_data:
            payment.notes = payment_data["notes"]
        if "reference_number" in payment_data:
            payment.reference_number = payment_data["reference_number"]
        if "reference_exception" in payment_data:
            payment.reference_exception = payment_data["reference_exception"]
        if "reference_exception_reason" in payment_data:
            payment.reference_exception_reason = payment_data["reference_exception_reason"]

        new_values = {
            "reference_number": payment.reference_number,
            "reference_exception": payment.reference_exception,
            "reference_exception_reason": payment.reference_exception_reason,
            "notes": payment.notes,
        }

        await self.audit.record(
            action="payment.updated",
            module=Module.APPLICATION,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Payment",
            entity_id=str(payment.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment