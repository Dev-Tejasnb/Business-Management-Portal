/** Billing and Payment TypeScript types matching backend schemas. */

export type PaymentMethod = "cash" | "upi" | "card" | "bank_transfer" | "other";
export type PaymentStatus = "unpaid" | "partially_paid" | "paid";
export type BillingStatus = "draft" | "issued" | "void";
export type DiscountType = "fixed" | "percentage";

export interface BillingItemBase {
  name: string;
  description?: string;
  amount: number;
  is_service_item: boolean;
  service_id?: number;
  sort_order: number;
}

export interface BillingItemCreate extends BillingItemBase {}

export interface BillingItemUpdate {
  name?: string;
  description?: string;
  amount?: number;
  is_service_item?: boolean;
  service_id?: number;
  sort_order?: number;
}

export interface BillingItemResponse extends BillingItemBase {
  id: number;
  billing_id: number;
  created_at: string;
  updated_at?: string;
}

export interface BillingBase {
  notes?: string;
}

export interface BillingCreate extends BillingBase {
  application_id: number;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_reason?: string;
  items: BillingItemCreate[];
}

export interface BillingUpdate {
  notes?: string;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_reason?: string;
}

export interface BillingResponse extends BillingBase {
  id: number;
  shop_id: number;
  application_id: number;
  customer_id: number;
  invoice_number: string;
  service_amount: number;
  non_service_charges: number;
  subtotal: number;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_amount: number;
  discount_reason?: string;
  total_amount: number;
  amount_paid: number;
  balance_amount: number;
  payment_status: PaymentStatus;
  billing_status: BillingStatus;
  created_by: number;
  updated_by?: number;
  created_at: string;
  updated_at?: string;
  items: BillingItemResponse[];
  application_number?: string;
  customer_name?: string;
  service_name?: string;
}

export interface BillingListResponse {
  items: BillingResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaymentBase {
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  reference_exception: boolean;
  reference_exception_reason?: string;
  notes?: string;
}

export interface PaymentCreate extends PaymentBase {}

export interface PaymentUpdate {
  amount?: number;
  payment_method?: PaymentMethod;
  reference_number?: string;
  reference_exception?: boolean;
  reference_exception_reason?: string;
  notes?: string;
}

export interface PaymentResponse extends PaymentBase {
  id: number;
  shop_id: number;
  billing_id: number;
  recorded_by: number;
  paid_at: string;
  created_at: string;
  updated_at?: string;
  recorder_name?: string;
}

export interface PaymentListResponse {
  items: PaymentResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InvoiceNumberResponse {
  invoice_number: string;
}

export interface BillingCalculationPreview {
  service_amount: number;
  non_service_charges: number;
  subtotal: number;
  discount_type?: DiscountType;
  discount_value?: number;
  discount_amount: number;
  total_amount: number;
}

// For UI state
export interface BillingFormData {
  items: BillingItemCreate[];
  discount_type?: DiscountType;
  discount_value?: number;
  discount_reason?: string;
  notes?: string;
}

export interface PaymentFormData {
  amount: number;
  payment_method: PaymentMethod;
  reference_number?: string;
  reference_exception: boolean;
  reference_exception_reason?: string;
  notes?: string;
}

// Helper types for display
export type PaymentMethodLabel = {
  value: PaymentMethod;
  label: string;
};

export const PAYMENT_METHOD_LABELS: PaymentMethodLabel[] = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "card", label: "Card" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "other", label: "Other" },
];

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  unpaid: "Unpaid",
  partially_paid: "Partially Paid",
  paid: "Paid",
};

export const BILLING_STATUS_LABELS: Record<BillingStatus, string> = {
  draft: "Draft",
  issued: "Issued",
  void: "Void",
};

export const DISCOUNT_TYPE_LABELS: Record<DiscountType, string> = {
  fixed: "Fixed Amount",
  percentage: "Percentage",
};