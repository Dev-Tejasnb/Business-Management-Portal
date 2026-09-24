/**
 * Document types for the Business Management Portal
 * Matches backend schemas from app/modules/documents/schemas.py
 */

export type DocumentStatus = 'uploaded' | 'verified' | 'rejected' | 'archived';

export interface DocumentResponse {
  id: number;
  shop_id: number;
  application_id: number;
  required_document_id?: number | null;
  uploaded_by: number;
  original_filename: string;
  storage_key: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  rejection_reason?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at?: string | null;
  verified_at?: string | null;
  verified_by?: number | null;
  uploader_name?: string | null;
  verifier_name?: string | null;
  required_document_name?: string | null;
  download_url?: string | null;
}

export interface DocumentChecklistRequirement {
  required_document_id: number;
  name: string;
  description?: string | null;
  is_mandatory: boolean;
  allowed_file_types?: string[] | null;
  max_file_size_mb?: number | null;
  is_uploaded: boolean;
  uploaded_document?: DocumentResponse | null;
}

export interface ApplicationDocumentChecklistResponse {
  application_id: number;
  service_id: number;
  service_name: string;
  total_requirements: number;
  mandatory_required: number;
  mandatory_uploaded: number;
  mandatory_verified: number;
  all_mandatory_verified: boolean;
  requirements: DocumentChecklistRequirement[];
  additional_documents: DocumentResponse[];
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
}

export interface PresignedUrlResponse {
  url: string;
  expires_in_seconds: number;
  mime_type: string;
  filename: string;
}
