"""Customer management service handling business logic."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerStatus
from app.models.shop import Shop
from app.models.user import User
from app.models.membership import ShopMembership
from app.utils.phone import normalize_phone
from app.core.audit import audit_service, Module, AuditAction
from app.core.logging import get_logger

logger = get_logger(__name__)


class CustomerService:
    """Service for customer management operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_customer(
        self,
        *,
        shop_id: int,
        name: str,
        mobile: str,
        email: Optional[str] = None,
        address: Optional[str] = None,
        notes: Optional[str] = None,
        primary_staff_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Customer:
        """Create a new customer with shop scoping and mobile normalization."""
        # Normalize mobile number
        normalized_mobile = normalize_phone(mobile)
        if not normalized_mobile:
            raise ValueError("Invalid mobile number")

        # Check for duplicate mobile within the same shop
        stmt = select(Customer).where(
            and_(
                Customer.shop_id == shop_id,
                Customer.mobile == normalized_mobile,
                Customer.status != CustomerStatus.ARCHIVED.value
            )
        )
        result = await self.session.execute(stmt)
        existing_customer = result.scalar_one_or_none()

        if existing_customer:
            raise ValueError(f"Customer with mobile {normalized_mobile} already exists in this shop")

        # Validate primary staff belongs to same shop if provided
        if primary_staff_id is not None:
            # Check if user has an active membership in this shop
            staff_membership = await self.session.scalar(
                select(ShopMembership).where(
                    and_(
                        ShopMembership.user_id == primary_staff_id,
                        ShopMembership.shop_id == shop_id,
                        ShopMembership.is_active.is_(True),
                    )
                )
            )
            if not staff_membership:
                raise ValueError("Primary staff must belong to the same shop")

        # Create customer instance
        customer = Customer(
            shop_id=shop_id,
            name=name,
            mobile=normalized_mobile,
            email=email,
            address=address,
            notes=notes,
            primary_staff_id=primary_staff_id,
            status=CustomerStatus.ACTIVE.value,
        )

        self.session.add(customer)
        await self.session.flush()  # Get the ID without committing

        # Prepare audit data
        new_values = {
            "id": customer.id,
            "shop_id": customer.shop_id,
            "name": customer.name,
            "mobile": customer.mobile,
            "email": customer.email,
            "address": customer.address,
            "notes": customer.notes,
            "status": customer.status,
            "primary_staff_id": customer.primary_staff_id,
        }

        # Record audit log
        await audit_service.record(
            action=AuditAction.LOGIN_SUCCESS,  # Using generic success action for creation
            module=Module.CUSTOMER,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="customer",
            entity_id=str(customer.id),
            old_values=None,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(customer)

        logger.info("Customer created", customer_id=customer.id, shop_id=shop_id)
        return customer

    async def get_customer(self, customer_id: int, shop_id: int) -> Optional[Customer]:
        """Get a customer by ID, scoped to shop."""
        stmt = select(Customer).where(
            and_(
                Customer.id == customer_id,
                Customer.shop_id == shop_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_customers(
        self,
        *,
        shop_id: int,
        search: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        primary_staff_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Customer], int]:
        """List customers for a shop with filtering and pagination."""
        # Base query
        stmt = select(Customer).where(Customer.shop_id == shop_id)

        # Apply filters
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(search_term),
                    Customer.mobile.ilike(search_term),
                    Customer.email.ilike(search_term)
                )
            )

        if status:
            stmt = stmt.where(Customer.status == status.value)

        if primary_staff_id is not None:
            stmt = stmt.where(Customer.primary_staff_id == primary_staff_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(Customer.created_at.desc())

        result = await self.session.execute(stmt)
        customers = result.scalars().all()

        return list(customers), total

    async def update_customer(
        self,
        *,
        customer_id: int,
        shop_id: int,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        notes: Optional[str] = None,
        primary_staff_id: Optional[int] = None,
        status: Optional[CustomerStatus] = None,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Customer:
        """Update a customer with validation."""
        # Get existing customer
        customer = await self.get_customer(customer_id, shop_id)
        if not customer:
            raise ValueError("Customer not found")

        # Capture old values for audit
        old_values = {
            "name": customer.name,
            "mobile": customer.mobile,
            "email": customer.email,
            "address": customer.address,
            "notes": customer.notes,
            "status": customer.status,
            "primary_staff_id": customer.primary_staff_id,
        }

        # Update fields if provided
        if name is not None:
            customer.name = name
        if mobile is not None:
            normalized_mobile = normalize_phone(mobile)
            if not normalized_mobile:
                raise ValueError("Invalid mobile number")

            # Check for duplicate mobile within same shop (excluding current customer)
            stmt = select(Customer).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.mobile == normalized_mobile,
                    Customer.id != customer_id,
                    Customer.status != CustomerStatus.ARCHIVED.value
                )
            )
            result = await self.session.execute(stmt)
            existing_customer = result.scalar_one_or_none()

            if existing_customer:
                raise ValueError(f"Customer with mobile {normalized_mobile} already exists in this shop")

            customer.mobile = normalized_mobile
        if email is not None:
            customer.email = email
        if address is not None:
            customer.address = address
        if notes is not None:
            customer.notes = notes
        if primary_staff_id is not None:
            # Validate primary staff belongs to same shop
            staff_membership = await self.session.scalar(
                select(ShopMembership).where(
                    and_(
                        ShopMembership.user_id == primary_staff_id,
                        ShopMembership.shop_id == shop_id,
                        ShopMembership.is_active.is_(True),
                    )
                )
            )
            if not staff_membership:
                raise ValueError("Primary staff must belong to the same shop")
            customer.primary_staff_id = primary_staff_id
        elif primary_staff_id is None and "primary_staff_id" in old_values:
            # Handle explicit unset (set to None)
            customer.primary_staff_id = None
        if status is not None:
            customer.status = status.value

        # Prepare new values for audit
        new_values = {
            "name": customer.name,
            "mobile": customer.mobile,
            "email": customer.email,
            "address": customer.address,
            "notes": customer.notes,
            "status": customer.status,
            "primary_staff_id": customer.primary_staff_id,
        }

        # Record audit log
        await audit_service.record(
            action="customer.updated",  # Custom action for updates
            module=Module.CUSTOMER,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="customer",
            entity_id=str(customer.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()
        await self.session.refresh(customer)

        logger.info("Customer updated", customer_id=customer.id, shop_id=shop_id)
        return customer

    async def archive_customer(
        self,
        *,
        customer_id: int,
        shop_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Customer:
        """Archive (soft delete) a customer."""
        customer = await self.get_customer(customer_id, shop_id)
        if not customer:
            raise ValueError("Customer not found")

        if customer.status == CustomerStatus.ARCHIVED.value:
            raise ValueError("Customer is already archived")

        # Capture old values for audit
        old_values = {
            "status": customer.status,
        }

        # Archive the customer
        customer.status = CustomerStatus.ARCHIVED.value

        # Prepare new values for audit
        new_values = {
            "status": customer.status,
        }

        # Record audit log
        await audit_service.record(
            action="customer.archived",
            module=Module.CUSTOMER,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="customer",
            entity_id=str(customer.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()
        await self.session.refresh(customer)

        logger.info("Customer archived", customer_id=customer.id, shop_id=shop_id)
        return customer

    async def restore_customer(
        self,
        *,
        customer_id: int,
        shop_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Customer:
        """Restore an archived customer."""
        customer = await self.get_customer(customer_id, shop_id)
        if not customer:
            raise ValueError("Customer not found")

        if customer.status != CustomerStatus.ARCHIVED.value:
            raise ValueError("Customer is not archived")

        # Capture old values for audit
        old_values = {
            "status": customer.status,
        }

        # Restore the customer
        customer.status = CustomerStatus.ACTIVE.value

        # Prepare new values for audit
        new_values = {
            "status": customer.status,
        }

        # Record audit log
        await audit_service.record(
            action="customer.restored",
            module=Module.CUSTOMER,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="customer",
            entity_id=str(customer.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.session.commit()
        await self.session.refresh(customer)

        logger.info("Customer restored", customer_id=customer.id, shop_id=shop_id)
        return customer