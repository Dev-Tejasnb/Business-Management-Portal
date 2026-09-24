"""Document Management API endpoints.

Provides shop-scoped document management:
- Upload documents attached to an application
- List documents for an application
- Get application document checklist summary
- Download/stream document files and generate presigned URLs
- Verify and reject documents with mandatory reason tracking
- Update notes and soft-delete/archive documents
"""

from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService, get_audit_service
from app.core.database import get_db_session
from app.core.roles import (
    DOCUMENT_DELETE,
    DOCUMENT_REJECT,
    DOCUMENT_UPDATE,
    DOCUMENT_UPLOAD,
    DOCUMENT_VERIFY,
    DOCUMENT_VIEW,
)
from app.models.user import User
from app.modules.auth.dependencies import get_current_user, require_permission
from app.modules.documents.schemas import (
    ApplicationDocumentChecklistResponse,
    DocumentListResponse,
    DocumentReject,
    DocumentResponse,
    DocumentUpdate,
    DocumentVerify,
    PresignedUrlResponse,
)
from app.modules.documents.service import DocumentService

router = APIRouter()


@router.post(
    "/shops/{shop_id}/applications/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and attach document to application",
    dependencies=[Depends(require_permission(DOCUMENT_UPLOAD))],
)
async def upload_document(
    shop_id: int,
    application_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    file: UploadFile = File(..., description="Document file to upload"),
    required_document_id: Optional[int] = Form(None, description="Optional ServiceRequiredDocument ID"),
    notes: Optional[str] = Form(None, description="Optional notes"),
) -> DocumentResponse:
    """Upload a file to MinIO and attach it to an application within a shop."""
    content = await file.read()
    filename = file.filename or "uploaded_document"

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_role = getattr(user.platform_role, "value", str(user.platform_role)) if user.platform_role else "staff"

    service = DocumentService(db, audit=audit)
    return await service.upload_document(
        shop_id=shop_id,
        application_id=application_id,
        filename=filename,
        content=content,
        uploaded_by=user.id,
        required_document_id=required_document_id,
        notes=notes,
        actor_user_id=user.id,
        actor_role=actor_role,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/shops/{shop_id}/applications/{application_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents for an application",
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def list_application_documents(
    shop_id: int,
    application_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status: Optional[str] = Query(None, description="Filter by status (uploaded, verified, rejected, archived)"),
    include_archived: bool = Query(False, description="Whether to include archived documents"),
) -> DocumentListResponse:
    """List documents uploaded for a specific application in a shop."""
    service = DocumentService(db)
    items, total = await service.list_documents_for_application(
        shop_id=shop_id,
        application_id=application_id,
        status=status,
        include_archived=include_archived,
        include_download_urls=True,
    )
    return DocumentListResponse(items=items, total=total)


@router.get(
    "/shops/{shop_id}/applications/{application_id}/documents/checklist",
    response_model=ApplicationDocumentChecklistResponse,
    summary="Get application required documents checklist",
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def get_application_checklist(
    shop_id: int,
    application_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationDocumentChecklistResponse:
    """Calculate and return the document requirement checklist status for an application."""
    service = DocumentService(db)
    return await service.get_application_checklist(
        shop_id=shop_id,
        application_id=application_id,
    )


@router.get(
    "/shops/{shop_id}/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def get_document(
    shop_id: int,
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentResponse:
    """Get metadata for a single document."""
    service = DocumentService(db)
    return await service.get_document(
        shop_id=shop_id,
        document_id=document_id,
        include_download_url=True,
    )


@router.get(
    "/shops/{shop_id}/documents/{document_id}/url",
    response_model=PresignedUrlResponse,
    summary="Get presigned download/view URL",
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def get_document_url(
    shop_id: int,
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    expires_seconds: int = Query(900, ge=60, le=86400, description="Expiration time in seconds"),
) -> PresignedUrlResponse:
    """Generate a short-lived presigned URL for document preview or direct download."""
    service = DocumentService(db)
    url, mime_type, filename = await service.get_presigned_url(
        shop_id=shop_id,
        document_id=document_id,
        expires_seconds=expires_seconds,
    )
    return PresignedUrlResponse(
        url=url,
        expires_in_seconds=expires_seconds,
        mime_type=mime_type,
        filename=filename,
    )


@router.get(
    "/shops/{shop_id}/documents/{document_id}/download",
    summary="Download or stream document binary directly",
    dependencies=[Depends(require_permission(DOCUMENT_VIEW))],
)
async def download_document(
    shop_id: int,
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Stream document binary directly from storage with tenant check."""
    service = DocumentService(db)
    stream, mime_type, filename, file_size = await service.get_document_stream(
        shop_id=shop_id,
        document_id=document_id,
    )

    def iterfile():
        try:
            for chunk in stream.stream(32 * 1024):
                yield chunk
        finally:
            stream.close()
            stream.release_conn()

    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Content-Length": str(file_size),
    }
    return StreamingResponse(
        iterfile(),
        media_type=mime_type,
        headers=headers,
    )


@router.patch(
    "/shops/{shop_id}/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Update document notes",
    dependencies=[Depends(require_permission(DOCUMENT_UPDATE))],
)
async def update_document(
    shop_id: int,
    document_id: int,
    payload: DocumentUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> DocumentResponse:
    """Update notes for a document."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_role = getattr(user.platform_role, "value", str(user.platform_role)) if user.platform_role else "staff"

    service = DocumentService(db, audit=audit)
    return await service.update_document(
        shop_id=shop_id,
        document_id=document_id,
        notes=payload.notes,
        actor_user_id=user.id,
        actor_role=actor_role,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/shops/{shop_id}/documents/{document_id}/verify",
    response_model=DocumentResponse,
    summary="Approve / verify a document",
    dependencies=[Depends(require_permission(DOCUMENT_VERIFY))],
)
async def verify_document(
    shop_id: int,
    document_id: int,
    payload: DocumentVerify,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> DocumentResponse:
    """Mark a document as verified."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_role = getattr(user.platform_role, "value", str(user.platform_role)) if user.platform_role else "staff"

    service = DocumentService(db, audit=audit)
    return await service.verify_document(
        shop_id=shop_id,
        document_id=document_id,
        verifier_user_id=user.id,
        notes=payload.notes,
        actor_role=actor_role,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/shops/{shop_id}/documents/{document_id}/reject",
    response_model=DocumentResponse,
    summary="Reject a document with mandatory reason",
    dependencies=[Depends(require_permission(DOCUMENT_REJECT))],
)
async def reject_document(
    shop_id: int,
    document_id: int,
    payload: DocumentReject,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> DocumentResponse:
    """Reject a document with a mandatory reason."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_role = getattr(user.platform_role, "value", str(user.platform_role)) if user.platform_role else "staff"

    service = DocumentService(db, audit=audit)
    return await service.reject_document(
        shop_id=shop_id,
        document_id=document_id,
        rejecter_user_id=user.id,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes,
        actor_role=actor_role,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.delete(
    "/shops/{shop_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive or permanently delete document",
    dependencies=[Depends(require_permission(DOCUMENT_DELETE))],
)
async def delete_document(
    shop_id: int,
    document_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
    hard_delete: bool = Query(False, description="Permanently delete from database and storage if True"),
) -> None:
    """Archive (soft delete) or permanently delete a document."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_role = getattr(user.platform_role, "value", str(user.platform_role)) if user.platform_role else "staff"

    service = DocumentService(db, audit=audit)
    await service.archive_or_delete_document(
        shop_id=shop_id,
        document_id=document_id,
        hard_delete=hard_delete,
        actor_user_id=user.id,
        actor_role=actor_role,
        ip_address=ip,
        user_agent=user_agent,
    )
