/** Reports & Financial Analytics TypeScript types matching backend schemas. */

// Date range presets
export type DateRangePreset = "today" | "yesterday" | "last_7_days" | "last_30_days" | "this_month" | "last_month" | "this_year" | "custom";
export type GroupByPeriod = "day" | "week" | "month";

// Common request
export interface DateRangeRequest {
  preset: DateRangePreset;
  from_date?: string;
  to_date?: string;
}

// ---------------------------------------------------------------------------
// Summary Report
// ---------------------------------------------------------------------------

export interface SummaryReportResponse {
  total_customers: number;
  new_customers: number;
  total_applications: number;
  new_applications: number;
  completed_applications: number;
  pending_applications: number;
  total_billed: string; // Decimal as string
  total_collected: string;
  outstanding_balance: string;
  period_from: string;
  period_to: string;
}

// ---------------------------------------------------------------------------
// Revenue Report
// ---------------------------------------------------------------------------

export interface RevenueReportResponse {
  period_from: string;
  period_to: string;
  total_billed: string;
  total_collected: string;
  total_outstanding: string;
  total_discounts: string;
  total_additional_charges: string;
  invoice_count: number;
}

// ---------------------------------------------------------------------------
// Collection Report
// ---------------------------------------------------------------------------

export interface CollectionMethodBreakdown {
  method: string;
  count: number;
  total_amount: string;
}

export interface CollectionReportResponse {
  period_from: string;
  period_to: string;
  total_collected: string;
  payment_count: number;
  average_payment: string;
  by_method: CollectionMethodBreakdown[];
}

// ---------------------------------------------------------------------------
// Payment Method Analytics
// ---------------------------------------------------------------------------

export interface PaymentMethodAnalyticsResponse {
  period_from: string;
  period_to: string;
  methods: CollectionMethodBreakdown[];
}

// ---------------------------------------------------------------------------
// Application Analytics
// ---------------------------------------------------------------------------

export interface ApplicationStatusBreakdown {
  status: string;
  count: number;
}

export interface ApplicationTrendPoint {
  period: string;
  count: number;
}

export interface ApplicationReportResponse {
  period_from: string;
  period_to: string;
  total_applications: number;
  by_status: ApplicationStatusBreakdown[];
  trend: ApplicationTrendPoint[];
}

// ---------------------------------------------------------------------------
// Service Report
// ---------------------------------------------------------------------------

export interface ServiceReportItem {
  service_id: number;
  service_name: string;
  application_count: number;
  completed_count: number;
  billed_amount: string;
  collected_amount: string;
  outstanding_amount: string;
}

export interface ServiceReportResponse {
  period_from: string;
  period_to: string;
  services: ServiceReportItem[];
}

// ---------------------------------------------------------------------------
// Customer Report
// ---------------------------------------------------------------------------

export interface CustomerReportResponse {
  period_from: string;
  period_to: string;
  total_customers: number;
  new_customers: number;
  active_customers: number;
  inactive_customers: number;
  archived_customers: number;
  customers_with_applications: number;
  customers_with_unpaid_balances: number;
  customers_with_completed_applications: number;
}

// ---------------------------------------------------------------------------
// Staff Report
// ---------------------------------------------------------------------------

export interface StaffReportItem {
  staff_id: number;
  staff_name: string;
  staff_email: string;
  role: string;
  applications_assigned: number;
  applications_created: number;
  applications_completed: number;
  payments_recorded: number;
  total_collected: string;
}

export interface StaffReportResponse {
  period_from: string;
  period_to: string;
  staff: StaffReportItem[];
}

// ---------------------------------------------------------------------------
// Outstanding Report
// ---------------------------------------------------------------------------

export interface OutstandingItem {
  billing_id: number;
  invoice_number: string;
  application_number: string;
  customer_name: string;
  service_name: string;
  total_amount: string;
  paid_amount: string;
  balance_amount: string;
  payment_status: string;
  billing_status: string;
  invoice_date: string;
}

export interface OutstandingReportResponse {
  period_from: string;
  period_to: string;
  items: OutstandingItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ---------------------------------------------------------------------------
// Billing Report
// ---------------------------------------------------------------------------

export interface BillingReportResponse {
  period_from: string;
  period_to: string;
  total_invoices: number;
  total_billed: string;
  total_discounted: string;
  total_additional_charges: string;
  total_collected: string;
  total_outstanding: string;
}

// ---------------------------------------------------------------------------
// Discount Report
// ---------------------------------------------------------------------------

export interface DiscountReportResponse {
  period_from: string;
  period_to: string;
  total_discount_amount: string;
  invoices_with_discount: number;
  by_date: { date: string; amount: string }[];
}

// ---------------------------------------------------------------------------
// Financial Trend
// ---------------------------------------------------------------------------

export interface FinancialTrendPoint {
  period: string;
  billed: string;
  collected: string;
}

export interface FinancialTrendResponse {
  period_from: string;
  period_to: string;
  group_by: GroupByPeriod;
  trend: FinancialTrendPoint[];
}

// ---------------------------------------------------------------------------
// Document Analytics
// ---------------------------------------------------------------------------

export interface DocumentAnalyticsResponse {
  period_from: string;
  period_to: string;
  total_documents: number;
  verified: number;
  rejected: number;
  pending: number;
  missing: number;
}

// ---------------------------------------------------------------------------
// UI Helper Types
// ---------------------------------------------------------------------------

export interface ReportTab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
}

export interface DateRangePickerProps {
  value: DateRangeRequest;
  onChange: (value: DateRangeRequest) => void;
  className?: string;
}