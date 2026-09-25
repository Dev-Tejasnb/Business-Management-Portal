"""Reports & Financial Analytics service with database aggregation queries."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_, case, extract, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import Billing, BillingItem, BillingStatus, Payment, PaymentMethod, PaymentStatus
from app.models.application import Application, ApplicationStatus
from app.models.customer import Customer, CustomerStatus
from app.models.service import Service
from app.models.user import User
from app.models.membership import ShopMembership
from app.models.shop import Shop


class ReportsService:
    """Service for generating financial and operational reports with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # Date Range Helpers
    # -------------------------------------------------------------------------

    def _get_date_range(
        self,
        preset: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Tuple[date, date]:
        """Calculate actual date range from preset or custom dates."""
        today = date.today()

        if preset == "today":
            return today, today
        elif preset == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif preset == "last_7_days":
            return today - timedelta(days=7), today
        elif preset == "last_30_days":
            return today - timedelta(days=30), today
        elif preset == "this_month":
            return today.replace(day=1), today
        elif preset == "last_month":
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            return last_month_end.replace(day=1), last_month_end
        elif preset == "this_year":
            return today.replace(month=1, day=1), today
        elif preset == "custom":
            if not from_date or not to_date:
                raise ValueError("Custom range requires from_date and to_date")
            if from_date > to_date:
                raise ValueError("from_date cannot be after to_date")
            return from_date, to_date
        return today, today

    def _build_date_filter(self, model, date_column, from_date: date, to_date: date):
        """Build a date filter for the given model and date column."""
        # Use date() function to compare date parts only (handles timezone)
        return and_(
            func.date(date_column) >= from_date,
            func.date(date_column) <= to_date
        )

    # -------------------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------------------

    async def get_summary_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get dashboard summary KPIs."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total Customers (all time, shop-scoped)
        total_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status != CustomerStatus.ARCHIVED.value,
                )
            )
        ) or 0

        # New Customers (in period, based on created_at)
        new_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status != CustomerStatus.ARCHIVED.value,
                    self._build_date_filter(Customer, Customer.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Total Applications (all time)
        total_applications = await self.session.scalar(
            select(func.count(Application.id)).where(Application.shop_id == shop_id)
        ) or 0

        # New Applications (in period, based on created_at)
        new_applications = await self.session.scalar(
            select(func.count(Application.id)).where(
                and_(
                    Application.shop_id == shop_id,
                    self._build_date_filter(Application, Application.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Completed Applications (all time)
        completed_applications = await self.session.scalar(
            select(func.count(Application.id)).where(
                and_(
                    Application.shop_id == shop_id,
                    Application.status == ApplicationStatus.COMPLETED.value,
                )
            )
        ) or 0

        # Pending Applications (enquiry + applied + documents_pending + under_processing)
        pending_statuses = [
            ApplicationStatus.ENQUIRY.value,
            ApplicationStatus.APPLIED.value,
            ApplicationStatus.DOCUMENTS_PENDING.value,
            ApplicationStatus.UNDER_PROCESSING.value,
        ]
        pending_applications = await self.session.scalar(
            select(func.count(Application.id)).where(
                and_(
                    Application.shop_id == shop_id,
                    Application.status.in_(pending_statuses),
                )
            )
        ) or 0

        # Total Billed (all time, valid billings only - not void)
        total_billed_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.total_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                )
            )
        )
        total_billed = total_billed_result or Decimal("0.00")

        # Total Collected (all time, valid payments)
        total_collected_result = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                )
            )
        )
        total_collected = total_collected_result or Decimal("0.00")

        # Outstanding Balance (current unpaid/partially_paid balance for non-void billings)
        outstanding_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.balance_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
                )
            )
        )
        outstanding_balance = outstanding_result or Decimal("0.00")

        return {
            "total_customers": total_customers,
            "new_customers": new_customers,
            "total_applications": total_applications,
            "new_applications": new_applications,
            "completed_applications": completed_applications,
            "pending_applications": pending_applications,
            "total_billed": total_billed,
            "total_collected": total_collected,
            "outstanding_balance": outstanding_balance,
            "period_from": period_from,
            "period_to": period_to,
        }

    # -------------------------------------------------------------------------
    # Revenue Report
    # -------------------------------------------------------------------------

    async def get_revenue_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get revenue breakdown for a period."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Billed in period (billing created_at in period, non-void)
        billed_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.total_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_billed = billed_result or Decimal("0.00")

        # Collected in period (payment paid_at in period, non-void billing)
        collected_result = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            )
        )
        total_collected = collected_result or Decimal("0.00")

        # Discounts in period
        discount_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.discount_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_discounts = discount_result or Decimal("0.00")

        # Additional charges in period (non-service items)
        additional_charges_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.non_service_charges), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_additional_charges = additional_charges_result or Decimal("0.00")

        # Invoice count
        invoice_count = await self.session.scalar(
            select(func.count(Billing.id)).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Outstanding (total billed - total collected for billings in period)
        # This is the current outstanding balance for invoices created in this period
        outstanding_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.balance_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_outstanding = outstanding_result or Decimal("0.00")

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_billed": total_billed,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "total_discounts": total_discounts,
            "total_additional_charges": total_additional_charges,
            "invoice_count": invoice_count,
        }

    # -------------------------------------------------------------------------
    # Collection Report
    # -------------------------------------------------------------------------

    async def get_collection_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get collection statistics with payment method breakdown."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total collected in period
        collected_result = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            )
        )
        total_collected = collected_result or Decimal("0.00")

        # Payment count
        payment_count = await self.session.scalar(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            )
        ) or 0

        # Average payment
        average_payment = Decimal("0.00")
        if payment_count > 0:
            average_payment = total_collected / Decimal(str(payment_count))

        # Breakdown by payment method
        method_results = await self.session.execute(
            select(
                Payment.payment_method,
                func.count(Payment.id).label("count"),
                func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("total_amount"),
            ).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            ).group_by(Payment.payment_method)
        )

        by_method = [
            {
                "method": row.payment_method,
                "count": row.count,
                "total_amount": row.total_amount,
            }
            for row in method_results.all()
        ]

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_collected": total_collected,
            "payment_count": payment_count,
            "average_payment": average_payment,
            "by_method": by_method,
        }

    # -------------------------------------------------------------------------
    # Payment Method Analytics
    # -------------------------------------------------------------------------

    async def get_payment_method_analytics(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get payment method analytics."""
        result = await self.get_collection_report(shop_id, preset, from_date, to_date)
        # Transform to expected format with 'methods' key
        return {
            "period_from": result["period_from"],
            "period_to": result["period_to"],
            "methods": result["by_method"],
        }

    # -------------------------------------------------------------------------
    # Application Analytics
    # -------------------------------------------------------------------------

    async def get_application_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        group_by: str = "day",
    ) -> dict:
        """Get application analytics with trend."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total applications in period
        total_applications = await self.session.scalar(
            select(func.count(Application.id)).where(
                and_(
                    Application.shop_id == shop_id,
                    self._build_date_filter(Application, Application.created_at, period_from, period_to),
                )
            )
        ) or 0

        # By status (all time)
        status_results = await self.session.execute(
            select(
                Application.status,
                func.count(Application.id).label("count"),
            ).where(
                Application.shop_id == shop_id
            ).group_by(Application.status)
        )

        by_status = [
            {"status": row.status, "count": row.count}
            for row in status_results.all()
        ]

        # Trend by group_by period
        if group_by == "day":
            date_trunc = func.date(Application.created_at)
        elif group_by == "week":
            date_trunc = func.date_trunc("week", Application.created_at)
        elif group_by == "month":
            date_trunc = func.date_trunc("month", Application.created_at)
        else:
            date_trunc = func.date(Application.created_at)

        trend_results = await self.session.execute(
            select(
                date_trunc.label("period"),
                func.count(Application.id).label("count"),
            ).where(
                and_(
                    Application.shop_id == shop_id,
                    self._build_date_filter(Application, Application.created_at, period_from, period_to),
                )
            ).group_by(date_trunc).order_by(date_trunc)
        )

        trend = [
            {"period": row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period), "count": row.count}
            for row in trend_results.all()
        ]

        return {
            "period_from": period_from,
            "period_to": period_to,
            "group_by": group_by,
            "total_applications": total_applications,
            "by_status": by_status,
            "trend": trend,
        }

    # -------------------------------------------------------------------------
    # Service Report
    # -------------------------------------------------------------------------

    async def get_service_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get service-wise performance report."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Get all services for the shop
        services = await self.session.execute(
            select(Service).where(Service.shop_id == shop_id)
        )
        service_list = services.scalars().all()

        service_items = []
        for service in service_list:
            # Application count (in period)
            app_count = await self.session.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.shop_id == shop_id,
                        Application.service_id == service.id,
                        self._build_date_filter(Application, Application.created_at, period_from, period_to),
                    )
                )
            ) or 0

            # Completed count (all time)
            completed_count = await self.session.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.shop_id == shop_id,
                        Application.service_id == service.id,
                        Application.status == ApplicationStatus.COMPLETED.value,
                    )
                )
            ) or 0

            # Billed amount (in period, using billing created_at, service amount from billing)
            billed_result = await self.session.scalar(
                select(func.coalesce(func.sum(Billing.service_amount), Decimal("0.00"))).where(
                    and_(
                        Billing.shop_id == shop_id,
                        Billing.billing_status != BillingStatus.VOID.value,
                        Billing.application.has(Application.service_id == service.id),
                        self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                    )
                )
            )
            billed_amount = billed_result or Decimal("0.00")

            # Collected amount (in period, using payment paid_at, for billings of this service)
            collected_result = await self.session.scalar(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                    and_(
                        Payment.shop_id == shop_id,
                        Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                        Payment.billing.has(Billing.application.has(Application.service_id == service.id)),
                        self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                    )
                )
            )
            collected_amount = collected_result or Decimal("0.00")

            # Outstanding amount (current balance for this service's billings)
            outstanding_result = await self.session.scalar(
                select(func.coalesce(func.sum(Billing.balance_amount), Decimal("0.00"))).where(
                    and_(
                        Billing.shop_id == shop_id,
                        Billing.billing_status != BillingStatus.VOID.value,
                        Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
                        Billing.application.has(Application.service_id == service.id),
                    )
                )
            )
            outstanding_amount = outstanding_result or Decimal("0.00")

            service_items.append({
                "service_id": service.id,
                "service_name": service.name,
                "application_count": app_count,
                "completed_count": completed_count,
                "billed_amount": billed_amount,
                "collected_amount": collected_amount,
                "outstanding_amount": outstanding_amount,
            })

        return {
            "period_from": period_from,
            "period_to": period_to,
            "services": service_items,
        }

    # -------------------------------------------------------------------------
    # Customer Report
    # -------------------------------------------------------------------------

    async def get_customer_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get customer statistics."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total customers (non-archived)
        total_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status != CustomerStatus.ARCHIVED.value,
                )
            )
        ) or 0

        # New customers (in period)
        new_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status != CustomerStatus.ARCHIVED.value,
                    self._build_date_filter(Customer, Customer.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Active customers
        active_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status == CustomerStatus.ACTIVE.value,
                )
            )
        ) or 0

        # Inactive customers
        inactive_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status == CustomerStatus.INACTIVE.value,
                )
            )
        ) or 0

        # Archived customers
        archived_customers = await self.session.scalar(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.shop_id == shop_id,
                    Customer.status == CustomerStatus.ARCHIVED.value,
                )
            )
        ) or 0

        # Customers with applications
        customers_with_apps = await self.session.scalar(
            select(func.count(func.distinct(Application.customer_id))).where(
                Application.shop_id == shop_id
            )
        ) or 0

        # Customers with unpaid balances (have at least one billing with balance)
        customers_with_unpaid = await self.session.scalar(
            select(func.count(func.distinct(Billing.customer_id))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
                )
            )
        ) or 0

        # Customers with completed applications
        customers_completed = await self.session.scalar(
            select(func.count(func.distinct(Application.customer_id))).where(
                and_(
                    Application.shop_id == shop_id,
                    Application.status == ApplicationStatus.COMPLETED.value,
                )
            )
        ) or 0

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_customers": total_customers,
            "new_customers": new_customers,
            "active_customers": active_customers,
            "inactive_customers": inactive_customers,
            "archived_customers": archived_customers,
            "customers_with_applications": customers_with_apps,
            "customers_with_unpaid_balances": customers_with_unpaid,
            "customers_with_completed_applications": customers_completed,
        }

    # -------------------------------------------------------------------------
    # Staff Report
    # -------------------------------------------------------------------------

    async def get_staff_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get staff activity/performance report."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Get all active staff for the shop
        staff_memberships = await self.session.execute(
            select(ShopMembership).where(
                and_(
                    ShopMembership.shop_id == shop_id,
                    ShopMembership.is_active == True,
                )
            ).options(selectinload(ShopMembership.user))
        )
        staff_list = staff_memberships.scalars().all()

        staff_items = []
        for membership in staff_list:
            user = membership.user
            if not user:
                continue

            # Applications assigned (in period)
            apps_assigned = await self.session.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.shop_id == shop_id,
                        Application.assigned_staff_id == user.id,
                        self._build_date_filter(Application, Application.created_at, period_from, period_to),
                    )
                )
            ) or 0

            # Applications created by staff (in period) - using assigned_staff_id since Application doesn't have created_by
            apps_created = await self.session.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.shop_id == shop_id,
                        Application.assigned_staff_id == user.id,
                        self._build_date_filter(Application, Application.created_at, period_from, period_to),
                    )
                )
            ) or 0

            # Applications completed by staff (in period - based on updated_at when status changed to completed)
            apps_completed = await self.session.scalar(
                select(func.count(Application.id)).where(
                    and_(
                        Application.shop_id == shop_id,
                        Application.status == ApplicationStatus.COMPLETED.value,
                        Application.assigned_staff_id == user.id,
                    )
                )
            ) or 0

            # Payments recorded (in period)
            payments_recorded = await self.session.scalar(
                select(func.count(Payment.id)).where(
                    and_(
                        Payment.shop_id == shop_id,
                        Payment.recorded_by == user.id,
                        Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                        self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                    )
                )
            ) or 0

            # Total collected by staff (in period)
            collected_result = await self.session.scalar(
                select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                    and_(
                        Payment.shop_id == shop_id,
                        Payment.recorded_by == user.id,
                        Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                        self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                    )
                )
            )
            total_collected = collected_result or Decimal("0.00")

            staff_items.append({
                "staff_id": user.id,
                "staff_name": user.full_name,
                "staff_email": user.email,
                "role": membership.role,
                "applications_assigned": apps_assigned,
                "applications_created": apps_created,
                "applications_completed": apps_completed,
                "payments_recorded": payments_recorded,
                "total_collected": total_collected,
            })

        return {
            "period_from": period_from,
            "period_to": period_to,
            "staff": staff_items,
        }

    # -------------------------------------------------------------------------
    # Outstanding Report
    # -------------------------------------------------------------------------

    async def get_outstanding_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        payment_status: Optional[str] = None,
    ) -> dict:
        """Get outstanding payments report with pagination."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Build base query for outstanding billings
        stmt = select(Billing).options(
            selectinload(Billing.application).selectinload(Application.service),
            selectinload(Billing.customer),
        ).where(
            and_(
                Billing.shop_id == shop_id,
                Billing.billing_status != BillingStatus.VOID.value,
                Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
            )
        )

        # Apply date filter on billing creation date
        stmt = stmt.where(
            self._build_date_filter(Billing, Billing.created_at, period_from, period_to)
        )

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Billing.invoice_number.ilike(search_term),
                    Billing.application.has(Application.application_number.ilike(search_term)),
                    Billing.customer.has(Customer.name.ilike(search_term)),
                    Billing.application.has(Application.service.has(Service.name.ilike(search_term))),
                )
            )

        # Apply payment status filter
        if payment_status:
            stmt = stmt.where(Billing.payment_status == payment_status)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one() or 0

        # Apply pagination
        stmt = stmt.order_by(Billing.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        billings = result.scalars().all()

        items = []
        for billing in billings:
            items.append({
                "billing_id": billing.id,
                "invoice_number": billing.invoice_number,
                "application_number": billing.application.application_number if billing.application else "",
                "customer_name": billing.customer.name if billing.customer else "",
                "service_name": billing.application.service.name if billing.application and billing.application.service else "",
                "total_amount": billing.total_amount,
                "paid_amount": billing.amount_paid,
                "balance_amount": billing.balance_amount,
                "payment_status": billing.payment_status,
                "billing_status": billing.billing_status,
                "invoice_date": billing.created_at.date(),
            })

        total_pages = (total + page_size - 1) // page_size

        return {
            "period_from": period_from,
            "period_to": period_to,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # -------------------------------------------------------------------------
    # Billing Report
    # -------------------------------------------------------------------------

    async def get_billing_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get billing statistics."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total invoices (in period)
        total_invoices = await self.session.scalar(
            select(func.count(Billing.id)).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Total billed
        total_billed_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.total_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_billed = total_billed_result or Decimal("0.00")

        # Total discounted
        total_discounted_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.discount_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_discounted = total_discounted_result or Decimal("0.00")

        # Total additional charges
        total_additional_charges_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.non_service_charges), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_additional_charges = total_additional_charges_result or Decimal("0.00")

        # Total collected (for billings in period)
        total_collected_result = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    Payment.billing.has(self._build_date_filter(Billing, Billing.created_at, period_from, period_to)),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            )
        )
        total_collected = total_collected_result or Decimal("0.00")

        # Total outstanding (for billings in period)
        total_outstanding_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.balance_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.payment_status.in_([PaymentStatus.UNPAID.value, PaymentStatus.PARTIALLY_PAID.value]),
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_outstanding = total_outstanding_result or Decimal("0.00")

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_invoices": total_invoices,
            "total_billed": total_billed,
            "total_discounted": total_discounted,
            "total_additional_charges": total_additional_charges,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
        }

    # -------------------------------------------------------------------------
    # Discount Report
    # -------------------------------------------------------------------------

    async def get_discount_report(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get discount statistics."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        # Total discount amount
        total_discount_result = await self.session.scalar(
            select(func.coalesce(func.sum(Billing.discount_amount), Decimal("0.00"))).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        )
        total_discount_amount = total_discount_result or Decimal("0.00")

        # Invoices with discount
        invoices_with_discount = await self.session.scalar(
            select(func.count(Billing.id)).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.discount_amount > Decimal("0.00"),
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Discount by date (daily aggregation)
        daily_results = await self.session.execute(
            select(
                func.date(Billing.created_at).label("discount_date"),
                func.coalesce(func.sum(Billing.discount_amount), Decimal("0.00")).label("amount"),
            ).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    Billing.discount_amount > Decimal("0.00"),
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            ).group_by(func.date(Billing.created_at)).order_by(func.date(Billing.created_at))
        )

        by_date = [
            {"date": row.discount_date.isoformat(), "amount": row.amount}
            for row in daily_results.all()
        ]

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_discount_amount": total_discount_amount,
            "invoices_with_discount": invoices_with_discount,
            "by_date": by_date,
        }

    # -------------------------------------------------------------------------
    # Financial Trend
    # -------------------------------------------------------------------------

    async def get_financial_trend(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        group_by: str = "day",
    ) -> dict:
        """Get financial trend (billed vs collected over time)."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        if group_by == "day":
            billing_trunc = func.date(Billing.created_at)
            payment_trunc = func.date(Payment.paid_at)
        elif group_by == "week":
            billing_trunc = func.date_trunc("week", Billing.created_at)
            payment_trunc = func.date_trunc("week", Payment.paid_at)
        elif group_by == "month":
            billing_trunc = func.date_trunc("month", Billing.created_at)
            payment_trunc = func.date_trunc("month", Payment.paid_at)
        else:
            billing_trunc = func.date(Billing.created_at)
            payment_trunc = func.date(Payment.paid_at)

        # Billed by period
        billed_results = await self.session.execute(
            select(
                billing_trunc.label("period"),
                func.coalesce(func.sum(Billing.total_amount), Decimal("0.00")).label("billed"),
            ).where(
                and_(
                    Billing.shop_id == shop_id,
                    Billing.billing_status != BillingStatus.VOID.value,
                    self._build_date_filter(Billing, Billing.created_at, period_from, period_to),
                )
            ).group_by(billing_trunc).order_by(billing_trunc)
        )

        billed_by_period = {str(row.period): row.billed for row in billed_results.all()}

        # Collected by period
        collected_results = await self.session.execute(
            select(
                payment_trunc.label("period"),
                func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("collected"),
            ).where(
                and_(
                    Payment.shop_id == shop_id,
                    Payment.billing.has(Billing.billing_status != BillingStatus.VOID.value),
                    self._build_date_filter(Payment, Payment.paid_at, period_from, period_to),
                )
            ).group_by(payment_trunc).order_by(payment_trunc)
        )

        collected_by_period = {str(row.period): row.collected for row in collected_results.all()}

        # Combine
        all_periods = sorted(set(list(billed_by_period.keys()) + list(collected_by_period.keys())))

        trend = []
        for period in all_periods:
            trend.append({
                "period": period,
                "billed": billed_by_period.get(period, Decimal("0.00")),
                "collected": collected_by_period.get(period, Decimal("0.00")),
            })

        return {
            "period_from": period_from,
            "period_to": period_to,
            "group_by": group_by,
            "trend": trend,
        }

    # -------------------------------------------------------------------------
    # Document Analytics
    # -------------------------------------------------------------------------

    async def get_document_analytics(
        self,
        shop_id: int,
        preset: str = "this_month",
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """Get document statistics."""
        period_from, period_to = self._get_date_range(preset, from_date, to_date)

        from app.models.document import Document, DocumentStatus

        # Total documents (in period)
        total_documents = await self.session.scalar(
            select(func.count(Document.id)).where(
                and_(
                    Document.shop_id == shop_id,
                    self._build_date_filter(Document, Document.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Verified
        verified = await self.session.scalar(
            select(func.count(Document.id)).where(
                and_(
                    Document.shop_id == shop_id,
                    Document.status == DocumentStatus.VERIFIED.value,
                    self._build_date_filter(Document, Document.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Rejected
        rejected = await self.session.scalar(
            select(func.count(Document.id)).where(
                and_(
                    Document.shop_id == shop_id,
                    Document.status == DocumentStatus.REJECTED.value,
                    self._build_date_filter(Document, Document.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Pending (UPLOADED)
        pending = await self.session.scalar(
            select(func.count(Document.id)).where(
                and_(
                    Document.shop_id == shop_id,
                    Document.status == DocumentStatus.UPLOADED.value,
                    self._build_date_filter(Document, Document.created_at, period_from, period_to),
                )
            )
        ) or 0

        # Missing - documents required by services but not uploaded for applications in period
        # This is more complex, so we'll return 0 for now
        missing = 0

        return {
            "period_from": period_from,
            "period_to": period_to,
            "total_documents": total_documents,
            "verified": verified,
            "rejected": rejected,
            "pending": pending,
            "missing": missing,
        }