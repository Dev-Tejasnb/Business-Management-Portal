"""Tests for Reports & Financial Analytics Module."""

from __future__ import annotations

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.application import Application, ApplicationStatus
from app.models.billing import Billing, BillingItem, BillingStatus, Payment, PaymentMethod, PaymentStatus
from app.models.customer import Customer, CustomerStatus
from app.models.document import Document, DocumentStatus
from app.models.service import Service, ServiceStatus
from app.models.shop import Shop, ShopStatus
from app.models.user import User
from app.models.membership import ShopMembership, ShopRole
from app.modules.reports.service import ReportsService
from app.core.security import hash_password


class TestReportsService:
    """Tests for ReportsService business logic."""

    @pytest.fixture
    async def sample_shop(self, db_session: AsyncSession) -> Shop:
        """Create a sample shop."""
        shop = Shop(code="TEST", name="Test Shop", slug="test-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(shop)
        await db_session.flush()
        return shop

    @pytest.fixture
    async def sample_user_owner(self, db_session: AsyncSession, sample_shop: Shop) -> User:
        """Create a sample owner user in the shop."""
        user = User(
            email="owner@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Test Owner",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        membership = ShopMembership(
            user_id=user.id,
            shop_id=sample_shop.id,
            role=ShopRole.OWNER,
            is_active=True,
        )
        db_session.add(membership)
        await db_session.flush()
        return user

    @pytest.fixture
    async def sample_user_staff(self, db_session: AsyncSession, sample_shop: Shop) -> User:
        """Create a sample staff user in the shop."""
        user = User(
            email="staff@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Test Staff",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        membership = ShopMembership(
            user_id=user.id,
            shop_id=sample_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(membership)
        await db_session.flush()
        return user

    @pytest.fixture
    async def sample_user_financial(self, db_session: AsyncSession, sample_shop: Shop) -> User:
        """Create a sample financial staff user in the shop."""
        user = User(
            email="financial@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Test Financial Staff",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        membership = ShopMembership(
            user_id=user.id,
            shop_id=sample_shop.id,
            role=ShopRole.FINANCIAL_STAFF,
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
    async def sample_customer2(self, db_session: AsyncSession, sample_shop: Shop) -> Customer:
        """Create a second sample customer."""
        customer = Customer(
            shop_id=sample_shop.id,
            name="Jane Smith",
            mobile="+919876543211",
            email="jane@example.com",
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
    async def sample_service2(self, db_session: AsyncSession, sample_shop: Shop) -> Service:
        """Create a second sample service."""
        service = Service(
            shop_id=sample_shop.id,
            name="Passport Service",
            slug="passport",
            description="Passport Application",
            base_price=200.00,
            estimated_processing_days=10,
            status=ServiceStatus.ACTIVE.value,
        )
        db_session.add(service)
        await db_session.flush()
        return service

    @pytest.fixture
    async def sample_application(
        self, db_session: AsyncSession, sample_shop: Shop, sample_customer: Customer, sample_service: Service
    ) -> Application:
        """Create a sample application."""
        application = Application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
            status=ApplicationStatus.COMPLETED.value,
            application_number="APP-TEST-2024-0001",
        )
        db_session.add(application)
        await db_session.flush()
        return application

    @pytest.fixture
    async def sample_billing(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ) -> Billing:
        """Create a sample billing."""
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("100.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("100.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("100.00"),
            amount_paid=Decimal("100.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0001",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()
        return billing

    @pytest.fixture
    async def sample_payment(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_billing: Billing,
        sample_user_financial: User,
    ) -> Payment:
        """Create a sample payment."""
        payment = Payment(
            shop_id=sample_shop.id,
            billing_id=sample_billing.id,
            recorded_by=sample_user_financial.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH.value,
            reference_number="REF001",
            paid_at=date.today(),
        )
        db_session.add(payment)
        await db_session.flush()
        return payment

    @pytest.fixture
    async def sample_document(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_application: Application,
        sample_user_owner: User,
    ) -> Document:
        """Create a sample document."""
        document = Document(
            shop_id=sample_shop.id,
            application_id=sample_application.id,
            storage_key="test/document.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            status=DocumentStatus.VERIFIED.value,
            uploaded_by=sample_user_owner.id,
        )
        db_session.add(document)
        await db_session.flush()
        return document

    # -------------------------------------------------------------------------
    # Summary Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_summary_report(
        self, db_session: AsyncSession, sample_shop: Shop, sample_customer: Customer, sample_application: Application, sample_billing: Billing, sample_payment: Payment, sample_user_owner: User
    ):
        """Test summary report returns correct KPIs."""
        service = ReportsService(db_session)

        result = await service.get_summary_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["total_customers"] == 1
        assert result["new_customers"] >= 0  # Created in this period
        assert result["total_applications"] == 1
        assert result["new_applications"] >= 0
        assert result["completed_applications"] == 1
        assert result["pending_applications"] == 0
        assert result["total_billed"] == Decimal("100.00")
        assert result["total_collected"] == Decimal("100.00")
        assert result["outstanding_balance"] == Decimal("0.00")
        assert "period_from" in result
        assert "period_to" in result

    @pytest.mark.asyncio
    async def test_get_summary_report_with_unpaid_billing(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test summary report with unpaid billing."""
        # Create unpaid billing (sample_billing fixture already has paid billing of 100)
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("200.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("200.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("200.00"),
            amount_paid=Decimal("0.00"),
            balance_amount=Decimal("200.00"),
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0002",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_summary_report(shop_id=sample_shop.id, preset="this_month")

        assert result["total_billed"] == Decimal("300.00")  # 100 + 200
        assert result["total_collected"] == Decimal("100.00")  # Only first billing paid
        assert result["outstanding_balance"] == Decimal("200.00")

    # -------------------------------------------------------------------------
    # Revenue Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_revenue_report(
        self, db_session: AsyncSession, sample_shop: Shop, sample_billing: Billing, sample_payment: Payment, sample_user_owner: User
    ):
        """Test revenue report returns correct breakdown."""
        service = ReportsService(db_session)

        result = await service.get_revenue_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_billed"] == Decimal("100.00")
        assert result["total_collected"] == Decimal("100.00")
        assert result["total_outstanding"] == Decimal("0.00")
        assert result["invoice_count"] == 1

    @pytest.mark.asyncio
    async def test_get_revenue_report_with_discount(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test revenue report with discount."""
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("200.00"),
            non_service_charges=Decimal("50.00"),
            subtotal=Decimal("250.00"),
            discount_type="fixed",
            discount_value=Decimal("25.00"),
            discount_amount=Decimal("25.00"),
            total_amount=Decimal("225.00"),
            amount_paid=Decimal("225.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0003",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()

        payment = Payment(
            shop_id=sample_shop.id,
            billing_id=billing.id,
            recorded_by=sample_application.customer_id,  # Using customer_id as recorded_by for simplicity
            amount=Decimal("225.00"),
            payment_method=PaymentMethod.CASH.value,
            paid_at=date.today(),
        )
        db_session.add(payment)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_revenue_report(shop_id=sample_shop.id, preset="this_month")

        # Only this billing is created in this test
        assert result["total_billed"] == Decimal("225.00")
        assert result["total_discounts"] == Decimal("25.00")
        assert result["total_additional_charges"] == Decimal("50.00")
        assert result["invoice_count"] == 1

    # -------------------------------------------------------------------------
    # Collection Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_collection_report(
        self, db_session: AsyncSession, sample_shop: Shop, sample_billing: Billing, sample_payment: Payment
    ):
        """Test collection report returns correct statistics."""
        service = ReportsService(db_session)

        result = await service.get_collection_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_collected"] == Decimal("100.00")
        assert result["payment_count"] == 1
        assert result["average_payment"] == Decimal("100.00")
        assert len(result["by_method"]) == 1
        assert result["by_method"][0]["method"] == "cash"
        assert result["by_method"][0]["count"] == 1
        assert result["by_method"][0]["total_amount"] == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_collection_report_multiple_methods(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_financial: User,
        sample_user_owner: User,
    ):
        """Test collection report with multiple payment methods."""
        # Create two billings with different payment methods
        billing1 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("50.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("50.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("50.00"),
            amount_paid=Decimal("50.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0004",
            created_by=sample_user_owner.id,
        )
        billing2 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("50.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("50.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("50.00"),
            amount_paid=Decimal("50.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0005",
            created_by=sample_user_owner.id,
        )
        db_session.add_all([billing1, billing2])
        await db_session.flush()

        payment_cash = Payment(
            shop_id=sample_shop.id,
            billing_id=billing1.id,
            recorded_by=sample_user_financial.id,
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.CASH.value,
            reference_number="CASH123",
            paid_at=date.today(),
        )
        payment_upi = Payment(
            shop_id=sample_shop.id,
            billing_id=billing2.id,
            recorded_by=sample_user_financial.id,
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.UPI.value,
            reference_number="UPI123",
            paid_at=date.today(),
        )
        db_session.add_all([payment_cash, payment_upi])
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_collection_report(shop_id=sample_shop.id, preset="this_month")

        assert result["total_collected"] == Decimal("100.00")
        assert result["payment_count"] == 2
        assert result["average_payment"] == Decimal("50.00")
        assert len(result["by_method"]) == 2

        methods = {m["method"]: m for m in result["by_method"]}
        assert "cash" in methods
        assert "upi" in methods

    # -------------------------------------------------------------------------
    # Payment Method Analytics Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_payment_method_analytics(
        self, db_session: AsyncSession, sample_shop: Shop, sample_billing: Billing, sample_payment: Payment, sample_user_financial: User, sample_user_owner: User
    ):
        """Test payment method analytics."""
        service = ReportsService(db_session)

        result = await service.get_payment_method_analytics(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert len(result["methods"]) == 1
        assert result["methods"][0]["method"] == "cash"

    # -------------------------------------------------------------------------
    # Application Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_application_report(
        self, db_session: AsyncSession, sample_shop: Shop, sample_application: Application
    ):
        """Test application report returns correct analytics."""
        service = ReportsService(db_session)

        result = await service.get_application_report(
            shop_id=sample_shop.id,
            preset="this_month",
            group_by="day",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_applications"] == 1
        assert len(result["by_status"]) >= 1
        assert len(result["trend"]) >= 1

    @pytest.mark.asyncio
    async def test_get_application_report_group_by_month(
        self, db_session: AsyncSession, sample_shop: Shop, sample_application: Application
    ):
        """Test application report grouped by month."""
        service = ReportsService(db_session)

        result = await service.get_application_report(
            shop_id=sample_shop.id,
            preset="this_year",
            group_by="month",
        )

        assert result["group_by"] == "month"
        assert len(result["trend"]) >= 1

    # -------------------------------------------------------------------------
    # Service Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_service_report(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_service: Service,
        sample_application: Application,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test service-wise performance report."""
        service = ReportsService(db_session)

        result = await service.get_service_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert len(result["services"]) == 1

        svc = result["services"][0]
        assert svc["service_id"] == sample_service.id
        assert svc["service_name"] == "PAN Card Service"
        assert svc["application_count"] == 1
        assert svc["completed_count"] == 1
        assert svc["billed_amount"] == Decimal("100.00")
        assert svc["collected_amount"] == Decimal("100.00")
        assert svc["outstanding_amount"] == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_get_service_report_multiple_services(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_service: Service,
        sample_service2: Service,
        sample_customer: Customer,
        sample_customer2: Customer,
        sample_user_staff: User,
        sample_user_owner: User,
        sample_application: Application,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test service report with multiple services."""
        # Create application for service2
        app2 = Application(
            shop_id=sample_shop.id,
            customer_id=sample_customer2.id,
            service_id=sample_service2.id,
            status=ApplicationStatus.COMPLETED.value,
            application_number="APP-TEST-2024-0002",
        )
        db_session.add(app2)
        await db_session.flush()

        # Create billing for app2
        billing2 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer2.id,
            application_id=app2.id,
            service_amount=Decimal("200.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("200.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("200.00"),
            amount_paid=Decimal("100.00"),
            balance_amount=Decimal("100.00"),
            payment_status=PaymentStatus.PARTIALLY_PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0005",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing2)
        await db_session.flush()

        payment2 = Payment(
            shop_id=sample_shop.id,
            billing_id=billing2.id,
            recorded_by=sample_user_staff.id,
            amount=Decimal("100.00"),
            payment_method=PaymentMethod.CARD.value,
            reference_number="CARD123",
            paid_at=date.today(),
        )
        db_session.add(payment2)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_service_report(shop_id=sample_shop.id, preset="this_month")

        assert len(result["services"]) == 2

        svc1 = next(s for s in result["services"] if s["service_id"] == sample_service.id)
        assert svc1["billed_amount"] == Decimal("100.00")
        assert svc1["collected_amount"] == Decimal("100.00")
        assert svc1["outstanding_amount"] == Decimal("0.00")

        svc2 = next(s for s in result["services"] if s["service_id"] == sample_service2.id)
        assert svc2["billed_amount"] == Decimal("200.00")
        assert svc2["collected_amount"] == Decimal("100.00")
        assert svc2["outstanding_amount"] == Decimal("100.00")

    # -------------------------------------------------------------------------
    # Customer Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_customer_report(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test customer statistics report."""
        service = ReportsService(db_session)

        result = await service.get_customer_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_customers"] == 1
        assert result["active_customers"] == 1
        assert result["inactive_customers"] == 0
        assert result["archived_customers"] == 0
        assert result["customers_with_applications"] == 1
        assert result["customers_with_unpaid_balances"] == 0  # Billing is paid
        assert result["customers_with_completed_applications"] == 1

    @pytest.mark.asyncio
    async def test_get_customer_report_with_unpaid(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test customer report with unpaid balances."""
        # Create unpaid billing
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("500.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("500.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("500.00"),
            amount_paid=Decimal("0.00"),
            balance_amount=Decimal("500.00"),
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0006",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_customer_report(shop_id=sample_shop.id, preset="this_month")

        assert result["customers_with_unpaid_balances"] == 1

    # -------------------------------------------------------------------------
    # Staff Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_staff_report(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_user_staff: User,
        sample_application: Application,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test staff performance report."""
        service = ReportsService(db_session)

        result = await service.get_staff_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert len(result["staff"]) >= 1

        staff = next(s for s in result["staff"] if s["staff_id"] == sample_user_staff.id)
        assert staff["staff_name"] == "Test Staff"
        assert staff["staff_email"] == "staff@test.com"
        assert staff["role"] == "staff"

    # -------------------------------------------------------------------------
    # Outstanding Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_outstanding_report(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_billing: Billing,
        sample_user_owner: User,
    ):
        """Test outstanding payments report."""
        # Create another billing with unpaid balance
        billing2 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("300.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("300.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("300.00"),
            amount_paid=Decimal("100.00"),
            balance_amount=Decimal("200.00"),
            payment_status=PaymentStatus.PARTIALLY_PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-TEST-2024-0007",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing2)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month")

        # First billing is paid, second is partially paid
        assert result["total"] == 1  # Only the partially paid one
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["items"]) == 1
        assert result["items"][0]["balance_amount"] == Decimal("200.00")
        assert result["items"][0]["payment_status"] == "partially_paid"

    @pytest.mark.asyncio
    async def test_get_outstanding_report_pagination(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test outstanding report pagination."""
        # Create multiple unpaid billings
        for i in range(15):
            billing = Billing(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                application_id=sample_application.id,
                service_amount=Decimal("100.00"),
                non_service_charges=Decimal("0.00"),
                subtotal=Decimal("100.00"),
                discount_type="fixed",
                discount_value=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
                total_amount=Decimal("100.00"),
                amount_paid=Decimal("0.00"),
                balance_amount=Decimal("100.00"),
                payment_status=PaymentStatus.UNPAID.value,
                billing_status=BillingStatus.ISSUED.value,
                invoice_number=f"INV-TEST-2024-{i+10:04d}",
                created_by=sample_user_owner.id,
            )
            db_session.add(billing)
        await db_session.flush()

        service = ReportsService(db_session)

        # Page 1
        result1 = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month", page=1, page_size=10)
        assert result1["total"] == 15
        assert result1["page"] == 1
        assert result1["page_size"] == 10
        assert len(result1["items"]) == 10
        assert result1["total_pages"] == 2

        # Page 2
        result2 = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month", page=2, page_size=10)
        assert result2["page"] == 2
        assert len(result2["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_outstanding_report_search(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test outstanding report search filter."""
        # Create billing with specific invoice number
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("100.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("100.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("100.00"),
            amount_paid=Decimal("0.00"),
            balance_amount=Decimal("100.00"),
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-SEARCH-TEST-001",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month", search="SEARCH")

        assert result["total"] == 1
        assert result["items"][0]["invoice_number"] == "INV-SEARCH-TEST-001"

    @pytest.mark.asyncio
    async def test_get_outstanding_report_payment_status_filter(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test outstanding report payment status filter."""
        # Create one unpaid and one partially paid
        billing1 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("100.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("100.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("100.00"),
            amount_paid=Decimal("0.00"),
            balance_amount=Decimal("100.00"),
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-UNPAID-001",
            created_by=sample_user_owner.id,
        )
        billing2 = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("200.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("200.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("200.00"),
            amount_paid=Decimal("100.00"),
            balance_amount=Decimal("100.00"),
            payment_status=PaymentStatus.PARTIALLY_PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-PARTIAL-001",
            created_by=sample_user_owner.id,
        )
        db_session.add_all([billing1, billing2])
        await db_session.flush()

        service = ReportsService(db_session)

        result_unpaid = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month", payment_status="unpaid")
        assert result_unpaid["total"] == 1
        assert result_unpaid["items"][0]["payment_status"] == "unpaid"

        result_partial = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month", payment_status="partially_paid")
        assert result_partial["total"] == 1
        assert result_partial["items"][0]["payment_status"] == "partially_paid"

    # -------------------------------------------------------------------------
    # Billing Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_billing_report(
        self, db_session: AsyncSession, sample_shop: Shop, sample_billing: Billing, sample_payment: Payment
    ):
        """Test billing statistics report."""
        service = ReportsService(db_session)

        result = await service.get_billing_report(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_invoices"] == 1
        assert result["total_billed"] == Decimal("100.00")
        assert result["total_discounted"] == Decimal("0.00")
        assert result["total_additional_charges"] == Decimal("0.00")
        assert result["total_collected"] == Decimal("100.00")
        assert result["total_outstanding"] == Decimal("0.00")

    # -------------------------------------------------------------------------
    # Discount Report Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_discount_report(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
    ):
        """Test discount statistics report."""
        # Create billing with discount
        billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("500.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("500.00"),
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            discount_amount=Decimal("50.00"),
            total_amount=Decimal("450.00"),
            amount_paid=Decimal("450.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-DISC-001",
            created_by=sample_user_owner.id,
        )
        db_session.add(billing)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_discount_report(shop_id=sample_shop.id, preset="this_month")

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_discount_amount"] == Decimal("50.00")
        assert result["invoices_with_discount"] == 1
        assert len(result["by_date"]) == 1

    # -------------------------------------------------------------------------
    # Financial Trend Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_financial_trend(
        self, db_session: AsyncSession, sample_shop: Shop, sample_billing: Billing, sample_payment: Payment
    ):
        """Test financial trend report."""
        service = ReportsService(db_session)

        result = await service.get_financial_trend(
            shop_id=sample_shop.id,
            preset="this_month",
            group_by="day",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["group_by"] == "day"
        assert len(result["trend"]) >= 1

        trend_point = result["trend"][0]
        assert "period" in trend_point
        assert "billed" in trend_point
        assert "collected" in trend_point

    # -------------------------------------------------------------------------
    # Document Analytics Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_document_analytics(
        self, db_session: AsyncSession, sample_shop: Shop, sample_document: Document
    ):
        """Test document analytics report."""
        service = ReportsService(db_session)

        result = await service.get_document_analytics(
            shop_id=sample_shop.id,
            preset="this_month",
        )

        assert result["period_from"] is not None
        assert result["period_to"] is not None
        assert result["total_documents"] == 1
        assert result["verified"] == 1
        assert result["rejected"] == 0
        assert result["pending"] == 0
        assert result["missing"] == 0

    @pytest.mark.asyncio
    async def test_get_document_analytics_with_rejected(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_application: Application,
        sample_user_owner: User,
        sample_document: Document,
    ):
        """Test document analytics with rejected document."""
        document = Document(
            shop_id=sample_shop.id,
            application_id=sample_application.id,
            storage_key="test/rejected.pdf",
            original_filename="rejected.pdf",
            mime_type="application/pdf",
            file_size=1024,
            status=DocumentStatus.REJECTED.value,
            rejection_reason="Invalid document",
            uploaded_by=sample_user_owner.id,
        )
        db_session.add(document)
        await db_session.flush()

        service = ReportsService(db_session)
        result = await service.get_document_analytics(shop_id=sample_shop.id, preset="this_month")

        assert result["total_documents"] == 2
        assert result["verified"] == 1
        assert result["rejected"] == 1

    # -------------------------------------------------------------------------
    # Cross-shop isolation tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cross_shop_isolation(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test reports don't leak data across shops."""
        # Create another shop with data
        other_shop = Shop(code="OTHER", name="Other Shop", slug="other-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(other_shop)
        await db_session.flush()

        other_user = User(
            email="other@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Other Owner",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        other_membership = ShopMembership(
            user_id=other_user.id,
            shop_id=other_shop.id,
            role=ShopRole.OWNER,
            is_active=True,
        )
        db_session.add(other_membership)
        await db_session.flush()

        other_customer = Customer(
            shop_id=other_shop.id,
            name="Other Customer",
            mobile="+919876543220",
            email="other@example.com",
            status=CustomerStatus.ACTIVE.value,
        )
        db_session.add(other_customer)
        await db_session.flush()

        other_service = Service(
            shop_id=other_shop.id,
            name="Other Service",
            slug="other-service",
            base_price=100.00,
            status=ServiceStatus.ACTIVE.value,
        )
        db_session.add(other_service)
        await db_session.flush()

        other_application = Application(
            shop_id=other_shop.id,
            customer_id=other_customer.id,
            service_id=other_service.id,
            status=ApplicationStatus.COMPLETED.value,
            application_number="APP-OTHER-2024-0001",
        )
        db_session.add(other_application)
        await db_session.flush()

        other_billing = Billing(
            shop_id=other_shop.id,
            customer_id=other_customer.id,
            application_id=other_application.id,
            service_amount=Decimal("500.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("500.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("500.00"),
            amount_paid=Decimal("500.00"),
            balance_amount=Decimal("0.00"),
            payment_status=PaymentStatus.PAID.value,
            billing_status=BillingStatus.ISSUED.value,
            invoice_number="INV-OTHER-2024-0001",
            created_by=other_user.id,
        )
        db_session.add(other_billing)
        await db_session.flush()

        other_payment = Payment(
            shop_id=other_shop.id,
            billing_id=other_billing.id,
            recorded_by=other_user.id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.CASH.value,
            paid_at=date.today(),
        )
        db_session.add(other_payment)
        await db_session.flush()

        service = ReportsService(db_session)

        # Get reports for sample_shop - should NOT include other_shop data
        summary = await service.get_summary_report(shop_id=sample_shop.id, preset="this_month")
        assert summary["total_customers"] == 1
        assert summary["total_applications"] == 1
        assert summary["total_billed"] == Decimal("100.00")
        assert summary["total_collected"] == Decimal("100.00")

        # Get reports for other_shop - should NOT include sample_shop data
        summary_other = await service.get_summary_report(shop_id=other_shop.id, preset="this_month")
        assert summary_other["total_customers"] == 1
        assert summary_other["total_applications"] == 1
        assert summary_other["total_billed"] == Decimal("500.00")
        assert summary_other["total_collected"] == Decimal("500.00")

    # -------------------------------------------------------------------------
    # Date range preset tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_date_range_presets(
        self, db_session: AsyncSession, sample_shop: Shop, sample_customer: Customer
    ):
        """Test all date range presets work correctly."""
        service = ReportsService(db_session)

        # Test all presets don't raise errors
        presets = ["today", "yesterday", "last_7_days", "last_30_days", "this_month", "last_month", "this_year"]
        for preset in presets:
            result = await service.get_summary_report(shop_id=sample_shop.id, preset=preset)
            assert "period_from" in result
            assert "period_to" in result
            assert result["period_from"] <= result["period_to"]

    @pytest.mark.asyncio
    async def test_custom_date_range(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test custom date range works correctly."""
        service = ReportsService(db_session)

        from_date = date(2024, 1, 1)
        to_date = date(2024, 1, 31)

        result = await service.get_summary_report(
            shop_id=sample_shop.id,
            preset="custom",
            from_date=from_date,
            to_date=to_date,
        )

        assert result["period_from"] == from_date
        assert result["period_to"] == to_date

    @pytest.mark.asyncio
    async def test_custom_date_range_validation(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test custom date range validation."""
        service = ReportsService(db_session)

        # from_date after to_date should raise
        with pytest.raises(ValueError):
            await service.get_summary_report(
                shop_id=sample_shop.id,
                preset="custom",
                from_date=date(2024, 2, 1),
                to_date=date(2024, 1, 1),
            )

        # Missing from_date or to_date should raise
        with pytest.raises(ValueError):
            await service.get_summary_report(
                shop_id=sample_shop.id,
                preset="custom",
                from_date=date(2024, 1, 1),
                to_date=None,
            )

    # -------------------------------------------------------------------------
    # Voided billing exclusion tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_voided_billing_excluded_from_reports(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_application: Application,
        sample_user_owner: User,
        sample_billing: Billing,
        sample_payment: Payment,
    ):
        """Test voided billings are excluded from all reports."""
        # Create voided billing
        voided_billing = Billing(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            application_id=sample_application.id,
            service_amount=Decimal("1000.00"),
            non_service_charges=Decimal("0.00"),
            subtotal=Decimal("1000.00"),
            discount_type="fixed",
            discount_value=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            balance_amount=Decimal("1000.00"),
            payment_status=PaymentStatus.UNPAID.value,
            billing_status=BillingStatus.VOID.value,  # VOID status
            invoice_number="INV-VOID-001",
            created_by=sample_user_owner.id,
        )
        db_session.add(voided_billing)
        await db_session.flush()

        service = ReportsService(db_session)

        # Summary should exclude voided billing
        summary = await service.get_summary_report(shop_id=sample_shop.id, preset="this_month")
        assert summary["total_billed"] == Decimal("100.00")  # Only non-voided
        assert summary["outstanding_balance"] == Decimal("0.00")  # Voided not counted

        # Revenue should exclude voided billing
        revenue = await service.get_revenue_report(shop_id=sample_shop.id, preset="this_month")
        assert revenue["total_billed"] == Decimal("100.00")
        assert revenue["total_outstanding"] == Decimal("0.00")
        assert revenue["invoice_count"] == 1

        # Outstanding should exclude voided billing
        outstanding = await service.get_outstanding_report(shop_id=sample_shop.id, preset="this_month")
        assert outstanding["total"] == 0  # No outstanding since only voided has balance

        # Billing report should exclude voided billing
        billing_report = await service.get_billing_report(shop_id=sample_shop.id, preset="this_month")
        assert billing_report["total_invoices"] == 1
        assert billing_report["total_billed"] == Decimal("100.00")