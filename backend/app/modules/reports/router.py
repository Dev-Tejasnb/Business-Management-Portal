"""Reports & Financial Analytics API routes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import REPORT_EXPORT, REPORT_VIEW
from app.modules.auth.dependencies import get_current_membership, require_permission
from app.modules.reports.schemas import (
    ApplicationReportResponse,
    BillingReportResponse,
    CollectionReportResponse,
    CustomerReportResponse,
    DateRangeRequest,
    DiscountReportResponse,
    DocumentAnalyticsResponse,
    FinancialTrendResponse,
    GroupByPeriod,
    OutstandingReportResponse,
    PaymentMethodAnalyticsResponse,
    RevenueReportResponse,
    ServiceReportResponse,
    StaffReportResponse,
    SummaryReportResponse,
)
from app.modules.reports.service import ReportsService
from app.db.session import get_db_session

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# Dependency for Reports Service
# ---------------------------------------------------------------------------

async def get_reports_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReportsService:
    """Get reports service instance."""
    return ReportsService(session)


# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=SummaryReportResponse,
    summary="Dashboard summary KPIs",
    description="Get dashboard summary with key performance indicators including customers, applications, billings, collections, and outstanding balance.",
)
async def get_summary_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> SummaryReportResponse:
    """Get dashboard summary report."""
    result = await service.get_summary_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return SummaryReportResponse(**result)


# ---------------------------------------------------------------------------
# Revenue Report
# ---------------------------------------------------------------------------

@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    summary="Revenue breakdown",
    description="Get revenue report with total billed, collected, outstanding, discounts, additional charges, and invoice count for the period.",
)
async def get_revenue_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> RevenueReportResponse:
    """Get revenue report."""
    result = await service.get_revenue_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return RevenueReportResponse(**result)


# ---------------------------------------------------------------------------
# Collection Report
# ---------------------------------------------------------------------------

@router.get(
    "/collection",
    response_model=CollectionReportResponse,
    summary="Collection statistics",
    description="Get collection report with total collected, payment count, average payment, and payment method breakdown.",
)
async def get_collection_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> CollectionReportResponse:
    """Get collection report."""
    result = await service.get_collection_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return CollectionReportResponse(**result)


# ---------------------------------------------------------------------------
# Payment Method Analytics
# ---------------------------------------------------------------------------

@router.get(
    "/payment-methods",
    response_model=PaymentMethodAnalyticsResponse,
    summary="Payment method analytics",
    description="Get payment method analytics with breakdown by method.",
)
async def get_payment_method_analytics(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> PaymentMethodAnalyticsResponse:
    """Get payment method analytics."""
    result = await service.get_payment_method_analytics(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return PaymentMethodAnalyticsResponse(**result)


# ---------------------------------------------------------------------------
# Application Analytics
# ---------------------------------------------------------------------------

@router.get(
    "/applications",
    response_model=ApplicationReportResponse,
    summary="Application analytics",
    description="Get application report with total applications, status breakdown, and trend data.",
)
async def get_application_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    group_by: GroupByPeriod = Query("day", description="Group trend by day/week/month"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> ApplicationReportResponse:
    """Get application analytics report."""
    result = await service.get_application_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,
    )
    return ApplicationReportResponse(**result)


# ---------------------------------------------------------------------------
# Service Report
# ---------------------------------------------------------------------------

@router.get(
    "/services",
    response_model=ServiceReportResponse,
    summary="Service-wise performance report",
    description="Get service-wise performance with application counts, billed/collected/outstanding amounts per service.",
)
async def get_service_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> ServiceReportResponse:
    """Get service-wise performance report."""
    result = await service.get_service_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return ServiceReportResponse(**result)


# ---------------------------------------------------------------------------
# Customer Report
# ---------------------------------------------------------------------------

@router.get(
    "/customers",
    response_model=CustomerReportResponse,
    summary="Customer statistics",
    description="Get customer report with total, new, active, inactive, archived counts, and customers with applications/unpaid balances/completed applications.",
)
async def get_customer_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> CustomerReportResponse:
    """Get customer statistics report."""
    result = await service.get_customer_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return CustomerReportResponse(**result)


# ---------------------------------------------------------------------------
# Staff Report
# ---------------------------------------------------------------------------

@router.get(
    "/staff",
    response_model=StaffReportResponse,
    summary="Staff activity/performance report",
    description="Get staff report with applications assigned/created/completed, payments recorded, and total collected per staff member.",
)
async def get_staff_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> StaffReportResponse:
    """Get staff performance report."""
    result = await service.get_staff_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return StaffReportResponse(**result)


# ---------------------------------------------------------------------------
# Outstanding Report
# ---------------------------------------------------------------------------

@router.get(
    "/outstanding",
    response_model=OutstandingReportResponse,
    summary="Outstanding payments report",
    description="Get paginated outstanding payments with search, status filter, and date range.",
)
async def get_outstanding_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by invoice number, application number, customer name, or service name"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status (unpaid, partially_paid)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> OutstandingReportResponse:
    """Get outstanding payments report."""
    result = await service.get_outstanding_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
        search=search,
        payment_status=payment_status,
    )
    return OutstandingReportResponse(**result)


# ---------------------------------------------------------------------------
# Billing Report
# ---------------------------------------------------------------------------

@router.get(
    "/billing",
    response_model=BillingReportResponse,
    summary="Billing statistics",
    description="Get billing report with total invoices, billed, discounted, additional charges, collected, and outstanding amounts.",
)
async def get_billing_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> BillingReportResponse:
    """Get billing statistics report."""
    result = await service.get_billing_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return BillingReportResponse(**result)


# ---------------------------------------------------------------------------
# Discount Report
# ---------------------------------------------------------------------------

@router.get(
    "/discounts",
    response_model=DiscountReportResponse,
    summary="Discount statistics",
    description="Get discount report with total discount amount, invoices with discount, and daily breakdown.",
)
async def get_discount_report(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> DiscountReportResponse:
    """Get discount statistics report."""
    result = await service.get_discount_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return DiscountReportResponse(**result)


# ---------------------------------------------------------------------------
# Financial Trend
# ---------------------------------------------------------------------------

@router.get(
    "/financial-trend",
    response_model=FinancialTrendResponse,
    summary="Financial trend (billed vs collected)",
    description="Get financial trend with billed and collected amounts grouped by day/week/month.",
)
async def get_financial_trend(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    group_by: GroupByPeriod = Query("day", description="Group by day/week/month"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> FinancialTrendResponse:
    """Get financial trend report."""
    result = await service.get_financial_trend(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,
    )
    return FinancialTrendResponse(**result)


# ---------------------------------------------------------------------------
# Document Analytics
# ---------------------------------------------------------------------------

@router.get(
    "/documents",
    response_model=DocumentAnalyticsResponse,
    summary="Document analytics",
    description="Get document statistics with total, verified, rejected, pending, and missing counts.",
)
async def get_document_analytics(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_VIEW)),
) -> DocumentAnalyticsResponse:
    """Get document analytics report."""
    result = await service.get_document_analytics(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )
    return DocumentAnalyticsResponse(**result)


# ---------------------------------------------------------------------------
# CSV Export Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/export/summary",
    summary="Export summary report as CSV",
    description="Export dashboard summary as CSV file.",
)
async def export_summary_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export summary report as CSV."""
    result = await service.get_summary_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    # Build CSV content
    csv_lines = [
        "Metric,Value",
        f"Total Customers,{result['total_customers']}",
        f"New Customers,{result['new_customers']}",
        f"Total Applications,{result['total_applications']}",
        f"New Applications,{result['new_applications']}",
        f"Completed Applications,{result['completed_applications']}",
        f"Pending Applications,{result['pending_applications']}",
        f"Total Billed,{result['total_billed']}",
        f"Total Collected,{result['total_collected']}",
        f"Outstanding Balance,{result['outstanding_balance']}",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
    ]
    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=summary_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/revenue",
    summary="Export revenue report as CSV",
    description="Export revenue report as CSV file.",
)
async def export_revenue_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export revenue report as CSV."""
    result = await service.get_revenue_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Billed,{result['total_billed']}",
        f"Total Collected,{result['total_collected']}",
        f"Total Outstanding,{result['total_outstanding']}",
        f"Total Discounts,{result['total_discounts']}",
        f"Total Additional Charges,{result['total_additional_charges']}",
        f"Invoice Count,{result['invoice_count']}",
    ]
    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=revenue_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/collection",
    summary="Export collection report as CSV",
    description="Export collection report as CSV file with payment method breakdown.",
)
async def export_collection_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export collection report as CSV."""
    result = await service.get_collection_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Collected,{result['total_collected']}",
        f"Payment Count,{result['payment_count']}",
        f"Average Payment,{result['average_payment']}",
        "",
        "Payment Method Breakdown",
        "Method,Count,Total Amount",
    ]
    for method in result["by_method"]:
        csv_lines.append(f"{method['method']},{method['count']},{method['total_amount']}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=collection_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/outstanding",
    summary="Export outstanding report as CSV",
    description="Export outstanding payments report as CSV file.",
)
async def export_outstanding_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search filter"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export outstanding report as CSV."""
    result = await service.get_outstanding_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        page=1,
        page_size=10000,  # Export all
        search=search,
        payment_status=payment_status,
    )

    csv_lines = [
        "Invoice Number,Application Number,Customer Name,Service Name,Total Amount,Paid Amount,Balance Amount,Payment Status,Billing Status,Invoice Date",
    ]
    for item in result["items"]:
        csv_lines.append(
            f"{item['invoice_number']},"
            f"{item['application_number']},"
            f"{item['customer_name']},"
            f"{item['service_name']},"
            f"{item['total_amount']},"
            f"{item['paid_amount']},"
            f"{item['balance_amount']},"
            f"{item['payment_status']},"
            f"{item['billing_status']},"
            f"{item['invoice_date']}"
        )

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=outstanding_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/billing",
    summary="Export billing report as CSV",
    description="Export billing statistics report as CSV file.",
)
async def export_billing_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export billing report as CSV."""
    result = await service.get_billing_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Invoices,{result['total_invoices']}",
        f"Total Billed,{result['total_billed']}",
        f"Total Discounted,{result['total_discounted']}",
        f"Total Additional Charges,{result['total_additional_charges']}",
        f"Total Collected,{result['total_collected']}",
        f"Total Outstanding,{result['total_outstanding']}",
    ]
    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=billing_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/discounts",
    summary="Export discount report as CSV",
    description="Export discount statistics report as CSV file.",
)
async def export_discounts_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export discount report as CSV."""
    result = await service.get_discount_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Discount Amount,{result['total_discount_amount']}",
        f"Invoices With Discount,{result['invoices_with_discount']}",
        "",
        "Discount by Date",
        "Date,Amount",
    ]
    for item in result["by_date"]:
        csv_lines.append(f"{item['date']},{item['amount']}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=discount_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/financial-trend",
    summary="Export financial trend as CSV",
    description="Export financial trend report as CSV file.",
)
async def export_financial_trend_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    group_by: GroupByPeriod = Query("day", description="Group by day/week/month"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export financial trend as CSV."""
    result = await service.get_financial_trend(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,
    )

    csv_lines = [
        f"Period,Billed,Collected",
    ]
    for item in result["trend"]:
        csv_lines.append(f"{item['period']},{item['billed']},{item['collected']}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=financial_trend_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/applications",
    summary="Export application report as CSV",
    description="Export application analytics report as CSV file.",
)
async def export_applications_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    group_by: GroupByPeriod = Query("day", description="Group by day/week/month"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export application report as CSV."""
    result = await service.get_application_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Applications,{result['total_applications']}",
        "",
        "By Status",
        "Status,Count",
    ]
    for item in result["by_status"]:
        csv_lines.append(f"{item['status']},{item['count']}")

    csv_lines.append("")
    csv_lines.append("Trend")
    csv_lines.append("Period,Count")
    for item in result["trend"]:
        csv_lines.append(f"{item['period']},{item['count']}")

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=application_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/services",
    summary="Export service report as CSV",
    description="Export service-wise performance report as CSV file.",
)
async def export_services_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export service report as CSV."""
    result = await service.get_service_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Service ID,Service Name,Application Count,Completed Count,Billed Amount,Collected Amount,Outstanding Amount",
    ]
    for item in result["services"]:
        csv_lines.append(
            f"{item['service_id']},"
            f"{item['service_name']},"
            f"{item['application_count']},"
            f"{item['completed_count']},"
            f"{item['billed_amount']},"
            f"{item['collected_amount']},"
            f"{item['outstanding_amount']}"
        )

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=service_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/customers",
    summary="Export customer report as CSV",
    description="Export customer statistics report as CSV file.",
)
async def export_customers_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export customer report as CSV."""
    result = await service.get_customer_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Customers,{result['total_customers']}",
        f"New Customers,{result['new_customers']}",
        f"Active Customers,{result['active_customers']}",
        f"Inactive Customers,{result['inactive_customers']}",
        f"Archived Customers,{result['archived_customers']}",
        f"Customers With Applications,{result['customers_with_applications']}",
        f"Customers With Unpaid Balances,{result['customers_with_unpaid_balances']}",
        f"Customers With Completed Applications,{result['customers_with_completed_applications']}",
    ]
    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=customer_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/staff",
    summary="Export staff report as CSV",
    description="Export staff performance report as CSV file.",
)
async def export_staff_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export staff report as CSV."""
    result = await service.get_staff_report(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Staff ID,Staff Name,Staff Email,Role,Applications Assigned,Applications Created,Applications Completed,Payments Recorded,Total Collected",
    ]
    for item in result["staff"]:
        csv_lines.append(
            f"{item['staff_id']},"
            f"{item['staff_name']},"
            f"{item['staff_email']},"
            f"{item['role']},"
            f"{item['applications_assigned']},"
            f"{item['applications_created']},"
            f"{item['applications_completed']},"
            f"{item['payments_recorded']},"
            f"{item['total_collected']}"
        )

    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=staff_report_{result['period_from']}_{result['period_to']}.csv"},
    )


@router.get(
    "/export/documents",
    summary="Export document analytics as CSV",
    description="Export document statistics report as CSV file.",
)
async def export_documents_csv(
    preset: str = Query("this_month", description="Date range preset"),
    from_date: Optional[date] = Query(None, description="Custom from date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Custom to date (YYYY-MM-DD)"),
    membership=Depends(get_current_membership),
    service: ReportsService = Depends(get_reports_service),
    _=Depends(require_permission(REPORT_EXPORT)),
):
    """Export document analytics as CSV."""
    result = await service.get_document_analytics(
        shop_id=membership.shop_id,
        preset=preset,
        from_date=from_date,
        to_date=to_date,
    )

    csv_lines = [
        "Metric,Value",
        f"Period From,{result['period_from']}",
        f"Period To,{result['period_to']}",
        f"Total Documents,{result['total_documents']}",
        f"Verified,{result['verified']}",
        f"Rejected,{result['rejected']}",
        f"Pending,{result['pending']}",
        f"Missing,{result['missing']}",
    ]
    csv_content = "\n".join(csv_lines)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=document_report_{result['period_from']}_{result['period_to']}.csv"},
    )