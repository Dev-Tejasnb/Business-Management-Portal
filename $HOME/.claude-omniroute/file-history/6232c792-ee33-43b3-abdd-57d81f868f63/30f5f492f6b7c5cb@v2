"""Pydantic schemas for Document Management."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Schema representing an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    application_id: int
    required_document_id: int | None = None
    uploaded_by: int
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    status: str
    rejection_reason: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    verified_at: datetime | None = None
    verified_by: int | None = None
    uploader_name: str | None = None
    verifier_name: str | None = None
    required_document_name: str | None = None
    download_url: str | None = None


class DocumentUpdate(BaseModel):
    """Schema for updating document notes or metadata."""

    notes: str | None = None


class DocumentVerify(BaseModel):
    """Schema for approving / verifying a document."""

    notes: str | None = None


class DocumentReject(BaseModel):
    """Schema for rejecting a document with a mandatory reason."""

    rejection_reason: str = Field(..., min_length=1, description="Mandatory reason explaining why the document was rejected")
    notes: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentResponse]
    total: int


class DocumentChecklistRequirement(BaseModel):
    """Checklist item for a required document configuration of a service."""

    required_document_id: int
    name: str
    description: str | None = None
    is_mandatory: bool = True
    allowed_file_types: list[str] | None = None
    max_file_size_mb: int | None = 10
    is_uploaded: bool = False
    uploaded_document: DocumentResponse | None = None


class ApplicationDocumentChecklistResponse(BaseModel):
    """Overall document completion and checklist summary for an application."""

    application_id: int
    service_id: int
    service_name: str
    total_requirements: int
    mandatory_required: int
    mandatory_uploaded: int
    mandatory_verified: int
    all_mandatory_verified: bool
    requirements: list[DocumentChecklistRequirement]
    additional_documents: list[DocumentResponse]


class PresignedUrlResponse(BaseModel):
    """Presigned download / preview URL."""

    url: str
    expires_in_seconds: int = 900
    mime_type: str
    filename: str
