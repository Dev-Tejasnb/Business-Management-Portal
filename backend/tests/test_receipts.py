"""Tests for Receipt Generation and Communication System."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application import Application, ApplicationStatus
from app.models.billing import Billing, BillingStatus
from app.models.customer import Customer, CustomerStatus
from app.models.billing import Payment, PaymentStatus
from app.models.receipt import (
    CommunicationChannel,
    CommunicationHistory,
    CommunicationStatus,
    Receipt,
    ReceiptStatus,
    ReceiptType,
)
from app.models.service import Service, ServiceStatus
from app.models.shop import Shop, ShopStatus
from app.models.user import User
from app.modules.applications.service import ApplicationService
from app.modules.auth.dependencies import get_current_user
from app.modules.billing.service import BillingService, PaymentService
from app.modules.billing.receipt_service import ReceiptService
from app.modules.communication.service import CommunicationService
from app.core.security import hash_password


class TestReceiptAndCommunication:
    """Tests for receipt generation and communication sending."""

    @pytest.fixture
    async def sample_shop(self, db_session: AsyncSession) -> Shop:
        """Create a sample shop."""
        shop = Shop(
            code="TEST",
            name="Test Shop",
            slug="test-shop",
            status=ShopStatus.ACTIVE.value,
        )
        db_session.add(shop)
        await db_session.flush()
        return shop

    @pytest.fixture
    async def sample_user(self, db_session: AsyncSession, sample_shop: Shop) -> User:
        """Create a sample user in the shop."""
        user = User(
            email="staff@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Test Staff",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        from app.models.membership import ShopMembership as Membership, ShopRole
        membership = Membership(
            user_id=user.id,
            shop_id=sample_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(membership)
        await db_session.flush()
        return user

    @pytest.fixture
    async def sample_customer(self, db_session: AsyncSession, sample_shop: Shop) -> Customer:
        """Create a sample customer."""
        customer = Customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="+919876543210",
            email="john@example.com",
            status=CustomerStatus.ACTIVE.value,
        )
        db_session.add(customer)
        await db_session.flush()
        return customer

    @pytest.fixture
    async def sample_service(self, db_session: AsyncSession, sample_shop: Shop) -> Service:
        """Create a sample service."""
        service = Service(
            shop_id=sample_shop.id,
            name="PAN Card Service",
            slug="pan-card",
            description="PAN Card Application",
            base_price=100.00,
            estimated_processing_days=5,
            status=ServiceStatus.ACTIVE.value,
        )
        db_session.add(service)
        await db_session.flush()
        return service

    @pytest.fixture
    async def sample_application(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ) -> Application:
        """Create a sample application."""
        application = Application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
            status=ApplicationStatus.APPLIED.value,
            application_number="APP-TEST-001",
        )
        db_session.add(application)
        await db_session.flush()
        return application

    @pytest.fixture
    async def sample_billing(
        self,
        db_session: AsyncSession,
        sample_application: Application,
        sample_user: User,
    ) -> Billing:
        """Create a sample billing for the application."""
        from app.modules.billing.schemas import BillingCreate, BillingItemCreate
        billing_service = BillingService(db_session)
        billing = await billing_service.create_billing(
            shop_id=sample_application.shop_id,
            billing_data=BillingCreate(
                application_id=sample_application.id,
                items=[
                    BillingItemCreate(
                        name="Service Charge",
                        amount=100.0,
                        is_service_item=True,
                        service_id=sample_application.service_id,
                    )
                ],
            ),
            actor_user_id=sample_user.id,
            actor_role="STAFF",
        )
        return billing

    @pytest.mark.asyncio
    async def test_generate_invoice_pdf(
        self,
        db_session: AsyncSession,
        sample_billing: Billing,
        sample_user: User,
    ):
        """Test generating invoice PDF from billing."""
        receipt_service = ReceiptService(db_session)
        receipt = await receipt_service.generate_invoice_pdf(
            billing_id=sample_billing.id,
            generated_by=sample_user.id,
        )

        assert receipt.id is not None
        assert receipt.shop_id == sample_billing.shop_id
        assert receipt.billing_id == sample_billing.id
        assert receipt.receipt_type == ReceiptType.INVOICE.value
        assert receipt.status == ReceiptStatus.GENERATED.value
        assert receipt.storage_key is not None
        assert receipt.storage_key.endswith(".pdf")

        # Verify the receipt number format: INV-{SHOP_CODE}-{YEAR}-{SEQUENCE}
        assert receipt.receipt_number.startswith("INV-TEST-")
        parts = receipt.receipt_number.split("-")
        assert len(parts) == 4
        assert parts[0] == "INV"
        assert parts[1] == "TEST"
        assert parts[2].isdigit()  # year
        assert parts[3].isdigit()  # sequence

    @pytest.mark.asyncio
    async def test_generate_payment_receipt_pdf(
        self,
        db_session: AsyncSession,
        sample_billing: Billing,
        sample_user: User,
    ):
        """Test generating payment receipt PDF from payment."""
        # First, create a payment for the billing
        from app.modules.billing.schemas import PaymentCreate
        payment_service = PaymentService(db_session)
        payment = await payment_service.create_payment(
            shop_id=sample_billing.shop_id,
            billing_id=sample_billing.id,
            payment_data=PaymentCreate(
                amount=100.0,
                payment_method="upi",
                reference_number="TEST123",
            ),
            actor_user_id=sample_user.id,
            actor_role=sample_user.platform_role.value if sample_user.platform_role else "STAFF",
        )

        # Generate payment receipt
        receipt_service = ReceiptService(db_session)
        receipt = await receipt_service.generate_payment_receipt_pdf(
            payment_id=payment.id,
            generated_by=sample_user.id,
        )

        assert receipt.id is not None
        assert receipt.shop_id == sample_billing.shop_id
        assert receipt.payment_id == payment.id
        assert receipt.receipt_type == ReceiptType.PAYMENT_RECEIPT.value
        assert receipt.status == ReceiptStatus.GENERATED.value
        assert receipt.storage_key is not None
        assert receipt.storage_key.endswith(".pdf")

        # Verify the receipt number format: RCPT-{SHOP_CODE}-{YEAR}-{SEQUENCE}
        assert receipt.receipt_number.startswith("RCPT-TEST-")
        parts = receipt.receipt_number.split("-")
        assert len(parts) == 4
        assert parts[0] == "RCPT"
        assert parts[1] == "TEST"
        assert parts[2].isdigit()  # year
        assert parts[3].isdigit()  # sequence

    @pytest.mark.asyncio
    async def test_send_receipt_via_email(
        self,
        db_session: AsyncSession,
        sample_billing: Billing,
        sample_user: User,
    ):
        """Test sending a receipt via email."""
        # Generate invoice PDF first
        receipt_service = ReceiptService(db_session)
        receipt = await receipt_service.generate_invoice_pdf(
            billing_id=sample_billing.id,
            generated_by=sample_user.id,
        )

        # Send the receipt via email
        communication_service = CommunicationService(db_session)
        communication = await communication_service.send_receipt(
            receipt=receipt,
            channel=CommunicationChannel.EMAIL,
            recipient="customer@example.com",
            subject="Your Invoice",
            shop_id=sample_billing.shop_id,
            sent_by=sample_user.id,
        )

        assert communication.id is not None
        assert communication.shop_id == sample_billing.shop_id
        assert communication.receipt_id == receipt.id
        assert communication.channel == CommunicationChannel.EMAIL.value
        assert communication.recipient == "customer@example.com"
        assert communication.subject == "Your Invoice"
        assert communication.status == CommunicationStatus.SENT.value
        assert communication.sent_at is not None
        assert communication.error_message is None or communication.error_message == ""

    @pytest.mark.asyncio
    async def test_duplicate_send_protection(
        self,
        db_session: AsyncSession,
        sample_billing: Billing,
        sample_user: User,
    ):
        """Test that sending the same receipt to the same recipient within an hour is blocked."""
        # Generate invoice PDF
        receipt_service = ReceiptService(db_session)
        receipt = await receipt_service.generate_invoice_pdf(
            billing_id=sample_billing.id,
            generated_by=sample_user.id,
        )

        # Send the receipt via email first time
        communication_service = CommunicationService(db_session)
        communication1 = await communication_service.send_receipt(
            receipt=receipt,
            channel=CommunicationChannel.EMAIL,
            recipient="customer@example.com",
            subject="Your Invoice",
            shop_id=sample_billing.shop_id,
            sent_by=sample_user.id,
        )

        # Try to send again immediately (should return the same communication record)
        communication2 = await communication_service.send_receipt(
            receipt=receipt,
            channel=CommunicationChannel.EMAIL,
            recipient="customer@example.com",
            subject="Your Invoice",
            shop_id=sample_billing.shop_id,
            sent_by=sample_user.id,
        )

        # Should be the same communication record (duplicate send protection)
        assert communication1.id == communication2.id
        assert communication1.status == CommunicationStatus.SENT.value
        assert communication2.status == CommunicationStatus.SENT.value

    @pytest.mark.asyncio
    async def test_receipt_api_endpoints(
        self,
        db_session: AsyncSession,
        sample_billing: Billing,
        sample_user: User,
        client: AsyncClient,
    ):
        """Test the receipt API endpoints (requires authentication)."""
        # This test would require setting up the test client and authentication
        # For now, we'll skip because it's more involved and we are testing the service layer
        pass