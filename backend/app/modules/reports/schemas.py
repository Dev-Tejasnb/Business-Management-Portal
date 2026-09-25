"""Pydantic schemas for Reports & Financial Analytics module."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator

# Date range presets
DateRangePreset = Literal[
    "today", "yesterday", "last_7_days", "last_30_days",
    "this_month", "last_month", "this_year", "custom"
]

GroupByPeriod = Literal["day", "week", "month"]

# ---------------------------------------------------------------------------
# Common Schemas
# ---------------------------------------------------------------------------

class DateRangeRequest(BaseModel):
    """Date range filter for reports."""
    preset: DateRangePreset = "this_month"
    from_date: Optional[date] = None
    to_date: Optional[date] = None

    @field_validator("from_date", "to_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v

    def get_date_range(self) -> tuple[date, date]:
        """Calculate actual from_date and to_date based on preset."""
        today = date.today()
        if self.preset == "today":
            return today, today
        elif self.preset == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif self.preset == "last_7_days":
            return today - timedelta(days=7), today
        elif self.preset == "last_30_days":
            return today - timedelta(days=30), today
        elif self.preset == "this_month":
            return today.replace(day=1), today
        elif self.preset == "last_month":
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            return last_month_end.replace(day=1), last_month_end
        elif self.preset == "this_year":
            return today.replace(month=1, day=1), today
        elif self.preset == "custom":
            if not self.from_date or not self.to_date:
                raise ValueError("Custom range requires from_date and to_date")
            if self.from_date > self.to_date:
                raise ValueError("from_date cannot be after to_date")
            return self.from_date, self.to_date
        return today, today


# Need to import timedelta
from datetime import timedelta


# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------

class SummaryReportResponse(BaseModel):
    """Dashboard summary KPIs."""
    total_customers: int = 0
    new_customers: int = 0
    total_applications: int = 0
    new_applications: int = 0
    completed_applications: int = 0
    pending_applications: int = 0
    total_billed: Decimal = Decimal("0.00")
    total_collected: Decimal = Decimal("0.00")
    outstanding_balance: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Revenue Report
# ---------------------------------------------------------------------------

class RevenueReportResponse(BaseModel):
    """Revenue breakdown report."""
    period_from: date
    period_to: date
    total_billed: Decimal = Decimal("0.00")
    total_collected: Decimal = Decimal("0.00")
    total_outstanding: Decimal = Decimal("0.00")
    total_discounts: Decimal = Decimal("0.00")
    total_additional_charges: Decimal = Decimal("0.00")
    invoice_count: int = 0

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Collection Report
# ---------------------------------------------------------------------------

class CollectionMethodBreakdown(BaseModel):
    """Payment method breakdown."""
    method: str
    count: int
    total_amount: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class CollectionReportResponse(BaseModel):
    """Collection statistics report."""
    period_from: date
    period_to: date
    total_collected: Decimal = Decimal("0.00")
    payment_count: int = 0
    average_payment: Decimal = Decimal("0.00")
    by_method: List[CollectionMethodBreakdown] = []

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Payment Method Analytics
# ---------------------------------------------------------------------------

class PaymentMethodAnalyticsResponse(BaseModel):
    """Payment method analytics."""
    period_from: date
    period_to: date
    methods: List[CollectionMethodBreakdown] = []

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Application Analytics
# ---------------------------------------------------------------------------

class ApplicationStatusBreakdown(BaseModel):
    """Application count by status."""
    status: str
    count: int


class ApplicationTrendPoint(BaseModel):
    """Single point in application trend."""
    period: str  # ISO date string for day/week/month
    count: int


class ApplicationReportResponse(BaseModel):
    """Application analytics report."""
    period_from: date
    period_to: date
    total_applications: int = 0
    by_status: List[ApplicationStatusBreakdown] = []
    trend: List[ApplicationTrendPoint] = []


# ---------------------------------------------------------------------------
# Service Report
# ---------------------------------------------------------------------------

class ServiceReportItem(BaseModel):
    """Service performance metrics."""
    service_id: int
    service_name: str
    application_count: int = 0
    completed_count: int = 0
    billed_amount: Decimal = Decimal("0.00")
    collected_amount: Decimal = Decimal("0.00")
    outstanding_amount: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class ServiceReportResponse(BaseModel):
    """Service-wise performance report."""
    period_from: date
    period_to: date
    services: List[ServiceReportItem] = []

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Customer Report
# ---------------------------------------------------------------------------

class CustomerReportResponse(BaseModel):
    """Customer statistics report."""
    period_from: date
    period_to: date
    total_customers: int = 0
    new_customers: int = 0
    active_customers: int = 0
    inactive_customers: int = 0
    archived_customers: int = 0
    customers_with_applications: int = 0
    customers_with_unpaid_balances: int = 0
    customers_with_completed_applications: int = 0


# ---------------------------------------------------------------------------
# Staff Report
# ---------------------------------------------------------------------------

class StaffReportItem(BaseModel):
    """Staff activity metrics."""
    staff_id: int
    staff_name: str
    staff_email: str
    role: str
    applications_assigned: int = 0
    applications_created: int = 0
    applications_completed: int = 0
    payments_recorded: int = 0
    total_collected: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class StaffReportResponse(BaseModel):
    """Staff performance report."""
    period_from: date
    period_to: date
    staff: List[StaffReportItem] = []

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Outstanding Report
# ---------------------------------------------------------------------------

class OutstandingItem(BaseModel):
    """Outstanding payment item."""
    billing_id: int
    invoice_number: str
    application_number: str
    customer_name: str
    service_name: str
    total_amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    balance_amount: Decimal = Decimal("0.00")
    payment_status: str
    billing_status: str
    invoice_date: date

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class OutstandingReportResponse(BaseModel):
    """Outstanding payments report with pagination."""
    period_from: date
    period_to: date
    items: List[OutstandingItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Billing Report
# ---------------------------------------------------------------------------

class BillingReportResponse(BaseModel):
    """Billing statistics report."""
    period_from: date
    period_to: date
    total_invoices: int = 0
    total_billed: Decimal = Decimal("0.00")
    total_discounted: Decimal = Decimal("0.00")
    total_additional_charges: Decimal = Decimal("0.00")
    total_collected: Decimal = Decimal("0.00")
    total_outstanding: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Discount Report
# ---------------------------------------------------------------------------

class DiscountReportResponse(BaseModel):
    """Discount statistics report."""
    period_from: date
    period_to: date
    total_discount_amount: Decimal = Decimal("0.00")
    invoices_with_discount: int = 0
    by_date: List[dict] = []  # date -> amount

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Financial Trend
# ---------------------------------------------------------------------------

class FinancialTrendPoint(BaseModel):
    """Single point in financial trend."""
    period: str  # ISO date string
    billed: Decimal = Decimal("0.00")
    collected: Decimal = Decimal("0.00")

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class FinancialTrendResponse(BaseModel):
    """Revenue/Collection trend data."""
    period_from: date
    period_to: date
    group_by: GroupByPeriod
    trend: List[FinancialTrendPoint] = []

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# ---------------------------------------------------------------------------
# Document Analytics
# ---------------------------------------------------------------------------

class DocumentAnalyticsResponse(BaseModel):
    """Document statistics report."""
    period_from: date
    period_to: date
    total_documents: int = 0
    verified: int = 0
    rejected: int = 0
    pending: int = 0
    missing: int = 0