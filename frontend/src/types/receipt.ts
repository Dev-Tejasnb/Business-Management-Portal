/** Receipt and Communication TypeScript types matching backend schemas (Phase 10). */

export type ReceiptType = "invoice" | "payment_receipt";
export type ReceiptStatus = "generated" | "failed" | "regenerated";

export type CommunicationChannel = "email" | "whatsapp" | "sms";
export type CommunicationStatus = "pending" | "queued" | "sent" | "failed" | "cancelled";

export interface ReceiptBase {
  receipt_number: string;
  receipt_type: ReceiptType;
  storage_key?: string;
  status: ReceiptStatus;
}

export interface ReceiptCreate {
  // No additional fields needed for creation - PDF is generated from billing/payment
}

export interface ReceiptResponse extends ReceiptBase {
  id: number;
  shop_id: number;
  billing_id?: number;
  payment_id?: number;
  generated_at: string;
  generated_by: number;
  created_at: string;
  updated_at?: string;
}

export interface CommunicationHistoryBase {
  channel: CommunicationChannel;
  recipient: string;
  subject?: string;
  status: CommunicationStatus;
}

export interface CommunicationHistoryResponse extends CommunicationHistoryBase {
  id: number;
  shop_id: number;
  customer_id?: number;
  application_id?: number;
  payment_id?: number;
  billing_id?: number;
  receipt_id?: number;
  provider?: string;
  provider_message_id?: string;
  error_message?: string;
  sent_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface SendReceiptRequest {
  channel: CommunicationChannel;
  recipient: string;
  subject?: string;
}

export interface SendReceiptResponse {
  id: number;
  channel: CommunicationChannel;
  recipient: string;
  status: CommunicationStatus;
  sent_at?: string;
  created_at: string;
  error_message?: string;
}

export interface CommunicationListParams {
  receipt_id?: number;
  channel?: CommunicationChannel;
  status?: CommunicationStatus;
  limit?: number;
  offset?: number;
}

export interface CommunicationListResponse {
  items: CommunicationHistoryResponse[];
  total: number;
  limit: number;
  offset: number;
}

// For UI state
export interface ReceiptViewerProps {
  receiptId: number;
  shopId: number;
  onClose: () => void;
}

export interface SendReceiptDialogProps {
  receiptId: number;
  shopId: number;
  receiptType: ReceiptType;
  defaultRecipient?: string;
  onClose: () => void;
  onSent: () => void;
}

// Helper types for display
export const RECEIPT_TYPE_LABELS: Record<ReceiptType, string> = {
  invoice: "Invoice",
  payment_receipt: "Payment Receipt",
};

export const RECEIPT_STATUS_LABELS: Record<ReceiptStatus, string> = {
  generated: "Generated",
  failed: "Failed",
  regenerated: "Regenerated",
};

export const COMMUNICATION_CHANNEL_LABELS: Record<CommunicationChannel, string> = {
  email: "Email",
  whatsapp: "WhatsApp",
  sms: "SMS",
};

export const COMMUNICATION_STATUS_LABELS: Record<CommunicationStatus, string> = {
  pending: "Pending",
  queued: "Queued",
  sent: "Sent",
  failed: "Failed",
  cancelled: "Cancelled",
};