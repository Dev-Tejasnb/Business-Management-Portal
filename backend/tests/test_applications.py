"""Tests for Application Management Module."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.application import Application, ApplicationStatus
from app.models.customer import Customer, CustomerStatus
from app.models.service import Service, ServiceStatus
from app.models.service_field import ServiceField, FieldType
from app.models.shop import Shop, ShopStatus
from app.models.user import User
from app.modules.applications.service import ApplicationService
from app.modules.applications.schemas import ApplicationCreate, ApplicationUpdate
from app.core.security import hash_password


class TestApplicationService:
    """Tests for ApplicationService business logic."""

    @pytest.fixture
    async def sample_shop(self, db_session: AsyncSession) -> Shop:
        """Create a sample shop."""
        shop = Shop(code="TEST", name="Test Shop", slug="test-shop", status=ShopStatus.ACTIVE.value)
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
    async def sample_service_with_fields(
        self, db_session: AsyncSession, sample_shop: Shop
    ) -> Service:
        """Create a service with custom fields."""
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

        # Add custom fields
        fields = [
            ServiceField(
                service_id=service.id,
                name="applicant_name",
                label="Applicant Name",
                field_type=FieldType.TEXT.value,
                is_required=True,
                sort_order=1,
            ),
            ServiceField(
                service_id=service.id,
                name="date_of_birth",
                label="Date of Birth",
                field_type=FieldType.DATE.value,
                is_required=True,
                sort_order=2,
            ),
            ServiceField(
                service_id=service.id,
                name="father_name",
                label="Father's Name",
                field_type=FieldType.TEXT.value,
                is_required=False,
                sort_order=3,
            ),
            ServiceField(
                service_id=service.id,
                name="category",
                label="Category",
                field_type=FieldType.SELECT.value,
                is_required=True,
                options=["General", "OBC", "SC", "ST"],
                sort_order=4,
            ),
        ]
        for field in fields:
            db_session.add(field)
        await db_session.flush()

        return service

    @pytest.mark.asyncio
    async def test_create_application(
        self, db_session: AsyncSession, sample_shop: Shop, sample_customer: Customer, sample_service: Service
    ):
        """Test creating an application."""
        service = ApplicationService(db_session)
        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        assert application.id is not None
        assert application.shop_id == sample_shop.id
        assert application.customer_id == sample_customer.id
        assert application.service_id == sample_service.id
        assert application.application_number is not None
        assert application.status == ApplicationStatus.ENQUIRY.value
        assert application.assigned_staff_id is None
        assert application.application_data is None
        assert application.notes is None

    @pytest.mark.asyncio
    async def test_create_application_with_data(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service_with_fields: Service,
    ):
        """Test creating an application with application data."""
        service = ApplicationService(db_session)
        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service_with_fields.id,
            application_data={
                "applicant_name": "John Doe",
                "date_of_birth": "1990-01-01",
                "father_name": "Robert Doe",
                "category": "General",
            },
            notes="Test application",
        )

        assert application.application_data is not None
        assert application.application_data["applicant_name"] == "John Doe"
        assert application.application_data["date_of_birth"] == "1990-01-01"
        assert application.application_data["father_name"] == "Robert Doe"
        assert application.application_data["category"] == "General"
        assert application.notes == "Test application"

    @pytest.mark.asyncio
    async def test_create_application_cross_shop_customer_fails(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test creating application with customer from different shop fails."""
        # Create another shop
        other_shop = Shop(code="OTHER", name="Other Shop", slug="other-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(other_shop)
        await db_session.flush()

        # Create service in other shop
        other_service = Service(
            shop_id=other_shop.id,
            name="Other Service",
            slug="other-service",
            base_price=50.00,
            status=ServiceStatus.ACTIVE.value,
        )
        db_session.add(other_service)
        await db_session.flush()

        service = ApplicationService(db_session)

        # Try to create application in other_shop using customer from sample_shop
        with pytest.raises(Exception):  # Should raise NotFoundError
            await service.create_application(
                shop_id=other_shop.id,
                customer_id=sample_customer.id,
                service_id=other_service.id,
            )

    @pytest.mark.asyncio
    async def test_create_application_cross_shop_service_fails(
        self, db_session: AsyncSession, sample_shop: Shop, sample_customer: Customer
    ):
        """Test creating application with service from different shop fails."""
        # Create another shop
        other_shop = Shop(code="OTHER", name="Other Shop", slug="other-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(other_shop)
        await db_session.flush()

        # Create service in other shop
        other_service = Service(
            shop_id=other_shop.id,
            name="Other Service",
            slug="other-service",
            base_price=50.00,
            status=ServiceStatus.ACTIVE.value,
        )
        db_session.add(other_service)
        await db_session.flush()

        service = ApplicationService(db_session)

        # Try to create application in sample_shop using service from other_shop
        with pytest.raises(Exception):  # Should raise NotFoundError
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=other_service.id,
            )

    @pytest.mark.asyncio
    async def test_create_application_cross_shop_staff_fails(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test creating application with staff from different shop fails."""
        # Create another shop with user
        other_shop = Shop(code="OTHER", name="Other Shop", slug="other-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(other_shop)
        await db_session.flush()

        other_user = User(
            email="other@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Other Staff",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        from app.models.membership import ShopMembership as Membership, ShopRole
        other_membership = Membership(
            user_id=other_user.id,
            shop_id=other_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(other_membership)
        await db_session.flush()

        service = ApplicationService(db_session)

        # Try to create application with staff from different shop
        with pytest.raises(Exception):  # Should raise NotFoundError
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service.id,
                assigned_staff_id=other_user.id,
            )

    @pytest.mark.asyncio
    async def test_create_application_validation_required_fields(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service_with_fields: Service,
    ):
        """Test validation fails for missing required fields."""
        service = ApplicationService(db_session)

        # Missing required fields
        with pytest.raises(Exception):  # Should raise ValidationError
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service_with_fields.id,
                application_data={
                    # Missing applicant_name (required)
                    # Missing date_of_birth (required)
                    "father_name": "Robert Doe",
                    "category": "General",
                },
            )

    @pytest.mark.asyncio
    async def test_create_application_validation_field_types(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service_with_fields: Service,
    ):
        """Test validation fails for invalid field types."""
        service = ApplicationService(db_session)

        # Invalid date format
        with pytest.raises(Exception):
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service_with_fields.id,
                application_data={
                    "applicant_name": "John Doe",
                    "date_of_birth": "invalid-date",  # Invalid date format
                    "category": "General",
                },
            )

        # Invalid select option
        with pytest.raises(Exception):
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service_with_fields.id,
                application_data={
                    "applicant_name": "John Doe",
                    "date_of_birth": "1990-01-01",
                    "category": "InvalidCategory",  # Not in options
                },
            )

    @pytest.mark.asyncio
    async def test_get_application(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test getting an application by ID."""
        service = ApplicationService(db_session)

        # Create application
        created = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Get application
        application = await service.get_application(created.id, sample_shop.id)

        assert application is not None
        assert application.id == created.id
        assert application.application_number == created.application_number

    @pytest.mark.asyncio
    async def test_get_application_not_found(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test getting non-existent application returns None."""
        service = ApplicationService(db_session)

        application = await service.get_application(99999, sample_shop.id)

        assert application is None

    @pytest.mark.asyncio
    async def test_list_applications(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
        sample_user: User,
    ):
        """Test listing applications with filters."""
        service = ApplicationService(db_session)

        # Create multiple applications
        for i in range(3):
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service.id,
                assigned_staff_id=sample_user.id if i < 2 else None,
            )

        # Test list all
        applications, total = await service.list_applications(shop_id=sample_shop.id)
        assert total == 3
        assert len(applications) == 3

        # Test filter by assigned staff
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            assigned_staff_id=sample_user.id,
        )
        assert total == 2

        # Test filter by status
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            status=ApplicationStatus.ENQUIRY,
        )
        assert total == 3

        # Test pagination
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            page=1,
            page_size=2,
        )
        assert total == 3
        assert len(applications) == 2

    @pytest.mark.asyncio
    async def test_list_applications_search(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test searching applications."""
        service = ApplicationService(db_session)

        # Create applications
        app1 = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Search by application number
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            search=app1.application_number,
        )
        assert total == 1
        assert applications[0].id == app1.id

    @pytest.mark.asyncio
    async def test_update_application(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
        sample_user: User,
    ):
        """Test updating an application."""
        service = ApplicationService(db_session)

        # Create application
        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Update application
        updated = await service.update_application(
            application_id=application.id,
            shop_id=sample_shop.id,
            notes="Updated notes",
            assigned_staff_id=sample_user.id,
        )

        assert updated.notes == "Updated notes"
        assert updated.assigned_staff_id == sample_user.id
        assert updated.application_number == application.application_number  # Unchanged
        assert updated.customer_id == application.customer_id  # Unchanged
        assert updated.service_id == application.service_id  # Unchanged

    @pytest.mark.asyncio
    async def test_update_application_data(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service_with_fields: Service,
    ):
        """Test updating application data."""
        service = ApplicationService(db_session)

        # Create application with initial data
        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service_with_fields.id,
            application_data={
                "applicant_name": "John Doe",
                "date_of_birth": "1990-01-01",
                "category": "General",
            },
        )

        # Update application data
        updated = await service.update_application(
            application_id=application.id,
            shop_id=sample_shop.id,
            application_data={
                "applicant_name": "John Updated",
                "date_of_birth": "1990-01-01",
                "father_name": "Robert Doe",
                "category": "OBC",
            },
        )

        assert updated.application_data["applicant_name"] == "John Updated"
        assert updated.application_data["father_name"] == "Robert Doe"
        assert updated.application_data["category"] == "OBC"

    @pytest.mark.asyncio
    async def test_update_application_invalid_data(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service_with_fields: Service,
    ):
        """Test updating application with invalid data fails."""
        service = ApplicationService(db_session)

        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service_with_fields.id,
            application_data={
                "applicant_name": "John Doe",
                "date_of_birth": "1990-01-01",
                "category": "General",
            },
        )

        # Try to update with invalid data
        with pytest.raises(Exception):
            await service.update_application(
                application_id=application.id,
                shop_id=sample_shop.id,
                application_data={
                    "applicant_name": "John Doe",
                    "date_of_birth": "invalid-date",
                    "category": "General",
                },
            )

    @pytest.mark.asyncio
    async def test_assign_staff(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
        sample_user: User,
    ):
        """Test assigning staff to application."""
        service = ApplicationService(db_session)

        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Assign staff
        updated = await service.assign_staff(
            application_id=application.id,
            shop_id=sample_shop.id,
            assigned_staff_id=sample_user.id,
        )

        assert updated.assigned_staff_id == sample_user.id

        # Reassign to None (unassign)
        updated = await service.assign_staff(
            application_id=application.id,
            shop_id=sample_shop.id,
            assigned_staff_id=None,
        )

        assert updated.assigned_staff_id is None

    @pytest.mark.asyncio
    async def test_assign_staff_cross_shop_fails(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test assigning staff from different shop fails."""
        # Create another shop with user
        other_shop = Shop(code="OTHER", name="Other Shop", slug="other-shop", status=ShopStatus.ACTIVE.value)
        db_session.add(other_shop)
        await db_session.flush()

        other_user = User(
            email="other@test.com",
            hashed_password=hash_password("Password123!"),
            full_name="Other Staff",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        from app.models.membership import ShopMembership as Membership, ShopRole
        other_membership = Membership(
            user_id=other_user.id,
            shop_id=other_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(other_membership)
        await db_session.flush()

        service = ApplicationService(db_session)

        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Try to assign staff from different shop
        with pytest.raises(Exception):
            await service.assign_staff(
                application_id=application.id,
                shop_id=sample_shop.id,
                assigned_staff_id=other_user.id,
            )

    @pytest.mark.asyncio
    async def test_update_status(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test updating application status."""
        service = ApplicationService(db_session)

        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        assert application.status == ApplicationStatus.ENQUIRY.value

        # Update status
        updated = await service.update_status(
            application_id=application.id,
            shop_id=sample_shop.id,
            status=ApplicationStatus.APPLIED,
        )

        assert updated.status == ApplicationStatus.APPLIED.value

        # Update to completed
        updated = await service.update_status(
            application_id=application.id,
            shop_id=sample_shop.id,
            status=ApplicationStatus.COMPLETED,
        )

        assert updated.status == ApplicationStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_application_number_unique(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test that application numbers are unique."""
        service = ApplicationService(db_session)

        # Create multiple applications
        apps = []
        for i in range(5):
            app = await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=sample_service.id,
            )
            apps.append(app)

        # Check all have unique application numbers
        numbers = [app.application_number for app in apps]
        assert len(numbers) == len(set(numbers))

    @pytest.mark.asyncio
    async def test_application_number_format(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test application number format."""
        service = ApplicationService(db_session)

        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # Format: {SHOP_CODE}-{YEAR}-{SEQUENTIAL}
        parts = application.application_number.split('-')
        assert len(parts) == 3
        assert parts[0] == sample_shop.code.upper()
        assert parts[1] == str(datetime.now().year)
        assert parts[2].isdigit()

    @pytest.mark.asyncio
    async def test_multiple_applications_same_customer(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test a customer can have multiple applications."""
        service = ApplicationService(db_session)

        app1 = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )
        app2 = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        assert app1.id != app2.id
        assert app1.application_number != app2.application_number

        # List customer's applications
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
        )
        assert total == 2

    @pytest.mark.asyncio
    async def test_multiple_applications_same_service(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
        sample_service: Service,
    ):
        """Test a service can have multiple applications."""
        service = ApplicationService(db_session)

        app1 = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )
        app2 = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=sample_service.id,
        )

        # List service's applications
        applications, total = await service.list_applications(
            shop_id=sample_shop.id,
            service_id=sample_service.id,
        )
        assert total == 2

    @pytest.mark.asyncio
    async def test_archived_service_not_usable_for_new_application(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
    ):
        """Test that archived services cannot be used for new applications."""
        # Create archived service
        archived_service = Service(
            shop_id=sample_shop.id,
            name="Archived Service",
            slug="archived-service",
            base_price=50.00,
            status=ServiceStatus.ARCHIVED.value,
        )
        db_session.add(archived_service)
        await db_session.flush()

        service = ApplicationService(db_session)

        # Try to create application with archived service
        with pytest.raises(Exception):
            await service.create_application(
                shop_id=sample_shop.id,
                customer_id=sample_customer.id,
                service_id=archived_service.id,
            )

    @pytest.mark.asyncio
    async def test_inactive_service_usable(
        self,
        db_session: AsyncSession,
        sample_shop: Shop,
        sample_customer: Customer,
    ):
        """Test that inactive services can be used (business decision)."""
        # Create inactive service
        inactive_service = Service(
            shop_id=sample_shop.id,
            name="Inactive Service",
            slug="inactive-service",
            base_price=50.00,
            status=ServiceStatus.INACTIVE.value,
        )
        db_session.add(inactive_service)
        await db_session.flush()

        service = ApplicationService(db_session)

        # Should be able to create (or not, depending on business logic)
        # The current implementation allows it - we'll test current behavior
        application = await service.create_application(
            shop_id=sample_shop.id,
            customer_id=sample_customer.id,
            service_id=inactive_service.id,
        )
        assert application.service_id == inactive_service.id


# Import datetime for the format test
from datetime import datetime