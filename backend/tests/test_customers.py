"""Tests for Customer Management Module."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.customer import Customer, CustomerStatus
from app.models.shop import Shop, ShopStatus
from app.models.user import User
from app.modules.customers.service import CustomerService
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.utils.phone import normalize_phone
from app.core.security import hash_password


class TestPhoneNormalization:
    """Tests for phone normalization utility."""

    def test_normalize_10_digit_indian(self):
        """Test 10-digit Indian number normalization."""
        assert normalize_phone("9876543210") == "+919876543210"
        assert normalize_phone("9876543210") == "+919876543210"

    def test_normalize_with_country_code_91(self):
        """Test Indian number with 91 prefix."""
        assert normalize_phone("919876543210") == "+919876543210"
        assert normalize_phone("+919876543210") == "+919876543210"

    def test_normalize_with_formatting(self):
        """Test numbers with various formatting."""
        assert normalize_phone("98765 43210") == "+919876543210"
        assert normalize_phone("98765-43210") == "+919876543210"
        assert normalize_phone("(987) 654-3210") == "+919876543210"

    def test_normalize_invalid(self):
        """Test invalid numbers return empty."""
        assert normalize_phone("") == ""
        assert normalize_phone("123") == "123"
        assert normalize_phone("abcdefghij") == ""  # Non-numeric returns empty


class TestCustomerService:
    """Tests for CustomerService business logic."""

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

        # Add membership
        from app.models.membership import ShopMembership, ShopRole
        membership = ShopMembership(
            user_id=user.id,
            shop_id=sample_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(membership)
        await db_session.flush()
        return user

    @pytest.mark.asyncio
    async def test_create_customer(self, db_session: AsyncSession, sample_shop: Shop):
        """Test creating a customer."""
        service = CustomerService(db_session)
        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
            email="john@example.com",
            address="123 Test St",
            notes="Test customer",
        )

        assert customer.id is not None
        assert customer.name == "John Doe"
        assert customer.mobile == "+919876543210"
        assert customer.email == "john@example.com"
        assert customer.shop_id == sample_shop.id
        assert customer.status == CustomerStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_mobile_fails(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test creating a customer with duplicate mobile fails."""
        service = CustomerService(db_session)

        # Create first customer
        await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )

        # Try to create second with same mobile
        with pytest.raises(ValueError, match="already exists"):
            await service.create_customer(
                shop_id=sample_shop.id,
                name="Jane Smith",
                mobile="9876543210",  # Same mobile
            )

    @pytest.mark.asyncio
    async def test_create_customer_different_shop_same_mobile_ok(
        self, db_session: AsyncSession
    ):
        """Test same mobile allowed in different shops."""
        service = CustomerService(db_session)

        shop1 = Shop(code="SHOP1", name="Shop 1", slug="shop-1", status=ShopStatus.ACTIVE.value)
        shop2 = Shop(code="SHOP2", name="Shop 2", slug="shop-2", status=ShopStatus.ACTIVE.value)
        db_session.add_all([shop1, shop2])
        await db_session.flush()

        # Create in shop 1
        await service.create_customer(
            shop_id=shop1.id,
            name="John Doe",
            mobile="9876543210",
        )

        # Create in shop 2 with same mobile - should succeed
        customer = await service.create_customer(
            shop_id=shop2.id,
            name="Jane Smith",
            mobile="9876543210",
        )

        assert customer.mobile == "+919876543210"
        assert customer.shop_id == shop2.id

    @pytest.mark.asyncio
    async def test_list_customers_with_filters(
        self, db_session: AsyncSession, sample_shop: Shop, sample_user: User
    ):
        """Test listing customers with search and filters."""
        service = CustomerService(db_session)

        # Create multiple customers
        await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
            primary_staff_id=sample_user.id,
        )
        await service.create_customer(
            shop_id=sample_shop.id,
            name="Jane Smith",
            mobile="9876543211",
            primary_staff_id=sample_user.id,
        )
        await service.create_customer(
            shop_id=sample_shop.id,
            name="Bob Wilson",
            mobile="9876543212",
        )

        # Test search by name
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            search="John",
        )
        assert total == 1
        assert customers[0].name == "John Doe"

        # Test search by mobile
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            search="9876543211",
        )
        assert total == 1
        assert customers[0].name == "Jane Smith"

        # Test filter by staff
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            primary_staff_id=sample_user.id,
        )
        assert total == 2

        # Test filter by status
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            status=CustomerStatus.ACTIVE,
        )
        assert total == 3

        # Test pagination
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            page=1,
            page_size=2,
        )
        assert total == 3
        assert len(customers) == 2

    @pytest.mark.asyncio
    async def test_update_customer(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test updating a customer."""
        service = CustomerService(db_session)

        # Create customer
        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
            email="john@example.com",
        )

        # Update customer
        updated = await service.update_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
            name="John Updated",
            email="john.updated@example.com",
        )

        assert updated.name == "John Updated"
        assert updated.email == "john.updated@example.com"
        assert updated.mobile == "+919876543210"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_customer_mobile_duplicate_fails(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test updating customer to existing mobile fails."""
        service = CustomerService(db_session)

        # Create two customers
        customer1 = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )
        customer2 = await service.create_customer(
            shop_id=sample_shop.id,
            name="Jane Smith",
            mobile="9876543211",
        )

        # Try to update customer2 to customer1's mobile
        with pytest.raises(ValueError, match="already exists"):
            await service.update_customer(
                shop_id=sample_shop.id,
                customer_id=customer2.id,
                mobile="9876543210",
            )

    @pytest.mark.asyncio
    async def test_archive_customer(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test archiving a customer."""
        service = CustomerService(db_session)

        # Create customer
        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )
        assert customer.status == CustomerStatus.ACTIVE.value

        # Archive customer
        archived = await service.archive_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
        )

        assert archived.status == CustomerStatus.ARCHIVED.value

        # Verify it's not in active list
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            status=CustomerStatus.ACTIVE,
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_restore_customer(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test restoring an archived customer."""
        service = CustomerService(db_session)

        # Create and archive customer
        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )
        await service.archive_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
        )

        # Restore customer
        restored = await service.restore_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
        )

        assert restored.status == CustomerStatus.ACTIVE.value

        # Verify it's back in active list
        customers, total = await service.list_customers(
            shop_id=sample_shop.id,
            status=CustomerStatus.ACTIVE,
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_archive_already_archived_fails(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test archiving already archived customer fails."""
        service = CustomerService(db_session)

        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )
        await service.archive_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
        )

        with pytest.raises(ValueError, match="already archived"):
            await service.archive_customer(
                shop_id=sample_shop.id,
                customer_id=customer.id,
            )

    @pytest.mark.asyncio
    async def test_restore_not_archived_fails(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test restoring non-archived customer fails."""
        service = CustomerService(db_session)

        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )

        with pytest.raises(ValueError, match="not archived"):
            await service.restore_customer(
                shop_id=sample_shop.id,
                customer_id=customer.id,
            )

    @pytest.mark.asyncio
    async def test_primary_staff_same_shop_validation(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test that primary staff must belong to same shop."""
        service = CustomerService(db_session)

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

        from app.models.membership import ShopMembership, ShopRole
        other_membership = ShopMembership(
            user_id=other_user.id,
            shop_id=other_shop.id,
            role=ShopRole.STAFF,
            is_active=True,
        )
        db_session.add(other_membership)
        await db_session.flush()

        # Try to create customer with primary staff from different shop
        with pytest.raises(ValueError, match="same shop"):
            await service.create_customer(
                shop_id=sample_shop.id,
                name="John Doe",
                mobile="9876543210",
                primary_staff_id=other_user.id,
            )

    @pytest.mark.asyncio
    async def test_archived_customers_excluded_from_duplicate_check(
        self, db_session: AsyncSession, sample_shop: Shop
    ):
        """Test archived customers don't block mobile reuse."""
        service = CustomerService(db_session)

        # Create and archive a customer
        customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="John Doe",
            mobile="9876543210",
        )
        await service.archive_customer(
            shop_id=sample_shop.id,
            customer_id=customer.id,
        )

        # Should be able to create new customer with same mobile
        new_customer = await service.create_customer(
            shop_id=sample_shop.id,
            name="Jane Smith",
            mobile="9876543210",
        )

        assert new_customer.id != customer.id
        assert new_customer.mobile == "+919876543210"