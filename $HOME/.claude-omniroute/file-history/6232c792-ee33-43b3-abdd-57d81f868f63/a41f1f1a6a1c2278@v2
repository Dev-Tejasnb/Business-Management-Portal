"""Document management service handling business logic, validation, storage, and audit."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, BinaryIO, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditService, Module, audit_service
from app.core.exceptions import BadRequestError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.storage import (
    StorageService,
    generate_storage_key,
    get_storage_service,
    validate_file,
)
from app.models.application import Application
from app.models.document import Document, DocumentStatus
from app.models.service import Service
from app.models.service_field import ServiceRequiredDocument
from app.models.user import User
from app.modules.documents.schemas import (
    ApplicationDocumentChecklistResponse,
    DocumentChecklistRequirement,
    DocumentResponse,
)

logger = get_logger(__name__)


class DocumentService:
    """Service for handling document management operations with tenant isolation."""

    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[StorageService] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self.session = session
        self.storage = storage or get_storage_service()
        self.audit = audit or audit_service

    async def _format_document_response(
        self,
        doc: Document,
        include_download_url: bool = False,
    ) -> DocumentResponse:
        """Format Document entity to DocumentResponse schema with relations."""
        uploader_name = None
        verifier_name = None
        required_doc_name = None

        if doc.uploaded_by:
            uploader = await self.session.scalar(select(User).where(User.id == doc.uploaded_by))
            if uploader:
                uploader_name = uploader.full_name or uploader.email

        if doc.verified_by:
            verifier = await self.session.scalar(select(User).where(User.id == doc.verified_by))
            if verifier:
                verifier_name = verifier.full_name or verifier.email

        if doc.required_document_id:
            req_doc = await self.session.scalar(
                select(ServiceRequiredDocument).where(
                    ServiceRequiredDocument.id == doc.required_document_id
                )
            )
            if req_doc:
                required_doc_name = req_doc.name

        download_url = None
        if include_download_url:
            try:
                download_url = self.storage.generate_presigned_url(
                    storage_key=doc.storage_key,
                    expires_seconds=900,
                    download_filename=doc.original_filename,
                )
            except Exception as e:
                logger.warning("Failed to generate presigned URL for document %s: %s", doc.id, e)

        return DocumentResponse(
            id=doc.id,
            shop_id=doc.shop_id,
            application_id=doc.application_id,
            required_document_id=doc.required_document_id,
            uploaded_by=doc.uploaded_by,
            original_filename=doc.original_filename,
            storage_key=doc.storage_key,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            status=doc.status,
            rejection_reason=doc.rejection_reason,
            notes=doc.notes,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            verified_at=doc.verified_at,
            verified_by=doc.verified_by,
            uploader_name=uploader_name,
            verifier_name=verifier_name,
            required_document_name=required_doc_name,
            download_url=download_url,
        )

    async def upload_document(
        self,
        *,
        shop_id: int,
        application_id: int,
        filename: str,
        content: bytes,
        uploaded_by: int,
        required_document_id: Optional[int] = None,
        notes: Optional[str] = None,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DocumentResponse:
        """Upload and attach a document to an application with tenant validation."""
        # 1. Validate application exists in this shop
        application = await self.session.scalar(
            select(Application).where(
                and_(
                    Application.id == application_id,
                    Application.shop_id == shop_id,
                )
            )
        )
        if not application:
            raise NotFoundError("Application not found in this shop")

        # 2. Validate required_document_id if provided
        allowed_types = None
        max_size_mb = 10
        if required_document_id is not None:
            req_doc = await self.session.scalar(
                select(ServiceRequiredDocument).where(
                    and_(
                        ServiceRequiredDocument.id == required_document_id,
                        ServiceRequiredDocument.service_id == application.service_id,
                    )
                )
            )
            if not req_doc:
                raise BadRequestError("Required document definition not found for this service")
            allowed_types = req_doc.allowed_file_types
            if req_doc.max_file_size_mb:
                max_size_mb = req_doc.max_file_size_mb

        # 3. Validate file content, size, and MIME type
        safe_name, mime_type, file_size = validate_file(
            filename=filename,
            content=content,
            allowed_types=allowed_types,
            max_size_mb=max_size_mb,
        )

        # 4. Generate unique storage key
        storage_key = generate_storage_key(shop_id, application_id, safe_name)

        # 5. Handle document replacement if required_document_id is supplied
        # Archive previous active document for this required_doc requirement
        if required_document_id is not None:
            stmt = select(Document).where(
                and_(
                    Document.shop_id == shop_id,
                    Document.application_id == application_id,
                    Document.required_document_id == required_document_id,
                    Document.status != DocumentStatus.ARCHIVED.value,
                )
            )
            res = await self.session.execute(stmt)
            existing_docs = res.scalars().all()
            for prev_doc in existing_docs:
                prev_doc.status = DocumentStatus.ARCHIVED.value
                await self.audit.record(
                    action="document.replaced",
                    module=Module.DOCUMENT,
                    actor_user_id=actor_user_id or uploaded_by,
                    actor_role=actor_role,
                    shop_id=shop_id,
                    entity_type="Document",
                    entity_id=str(prev_doc.id),
                    old_values={"status": DocumentStatus.UPLOADED.value},
                    new_values={"status": DocumentStatus.ARCHIVED.value, "replaced_by_key": storage_key},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session=self.session,
                )

        # 6. Upload to MinIO object storage
        self.storage.upload_file(
            storage_key=storage_key,
            data=content,
            content_type=mime_type,
        )

        # 7. Create database record
        document = Document(
            shop_id=shop_id,
            application_id=application_id,
            required_document_id=required_document_id,
            uploaded_by=uploaded_by,
            original_filename=safe_name,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=file_size,
            status=DocumentStatus.UPLOADED.value,
            notes=notes,
        )
        self.session.add(document)

        try:
            await self.session.flush()

            # Record audit log
            await self.audit.record(
                action="document.upload",
                module=Module.DOCUMENT,
                actor_user_id=actor_user_id or uploaded_by,
                actor_role=actor_role,
                shop_id=shop_id,
                entity_type="Document",
                entity_id=str(document.id),
                old_values=None,
                new_values={
                    "application_id": application_id,
                    "required_document_id": required_document_id,
                    "original_filename": safe_name,
                    "mime_type": mime_type,
                    "file_size": file_size,
                    "status": DocumentStatus.UPLOADED.value,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                session=self.session,
            )

            await self.session.commit()
            await self.session.refresh(document)
        except Exception as e:
            await self.session.rollback()
            # Clean up uploaded storage object if database save fails
            self.storage.delete_file(storage_key)
            logger.error("Failed to save document record to DB, cleaned up storage: %s", e)
            raise

        return await self._format_document_response(document, include_download_url=True)

    async def get_document(
        self,
        *,
        shop_id: int,
        document_id: int,
        include_download_url: bool = False,
    ) -> DocumentResponse:
        """Fetch a single document with tenant check."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        return await self._format_document_response(document, include_download_url=include_download_url)

    async def list_documents_for_application(
        self,
        *,
        shop_id: int,
        application_id: int,
        status: Optional[str] = None,
        include_archived: bool = False,
        include_download_urls: bool = False,
    ) -> tuple[list[DocumentResponse], int]:
        """List documents attached to an application with filters."""
        # Ensure application belongs to this shop
        app_exists = await self.session.scalar(
            select(Application.id).where(
                and_(
                    Application.id == application_id,
                    Application.shop_id == shop_id,
                )
            )
        )
        if not app_exists:
            raise NotFoundError("Application not found in this shop")

        stmt = select(Document).where(
            and_(
                Document.shop_id == shop_id,
                Document.application_id == application_id,
            )
        )

        if not include_archived:
            stmt = stmt.where(Document.status != DocumentStatus.ARCHIVED.value)

        if status:
            stmt = stmt.where(Document.status == status)

        stmt = stmt.order_by(Document.created_at.desc())

        result = await self.session.execute(stmt)
        docs = result.scalars().all()

        formatted_items = []
        for d in docs:
            formatted_items.append(
                await self._format_document_response(d, include_download_url=include_download_urls)
            )

        return formatted_items, len(formatted_items)

    async def get_application_checklist(
        self,
        *,
        shop_id: int,
        application_id: int,
    ) -> ApplicationDocumentChecklistResponse:
        """Compute the required document checklist and verification state for an application."""
        # 1. Fetch application with service
        stmt = (
            select(Application)
            .options(selectinload(Application.service))
            .where(
                and_(
                    Application.id == application_id,
                    Application.shop_id == shop_id,
                )
            )
        )
        application = await self.session.scalar(stmt)
        if not application:
            raise NotFoundError("Application not found in this shop")

        service_id = application.service_id
        service_name = application.service.name if application.service else "Service"

        # 2. Fetch service requirements
        req_stmt = (
            select(ServiceRequiredDocument)
            .where(ServiceRequiredDocument.service_id == service_id)
            .order_by(ServiceRequiredDocument.id.asc())
        )
        req_res = await self.session.execute(req_stmt)
        required_defs = req_res.scalars().all()

        # 3. Fetch active documents uploaded for this application
        doc_stmt = (
            select(Document)
            .where(
                and_(
                    Document.shop_id == shop_id,
                    Document.application_id == application_id,
                    Document.status != DocumentStatus.ARCHIVED.value,
                )
            )
            .order_by(Document.created_at.desc())
        )
        doc_res = await self.session.execute(doc_stmt)
        active_docs = doc_res.scalars().all()

        # Group documents by required_document_id
        docs_by_req_id: dict[int, list[Document]] = {}
        additional_docs: list[Document] = []

        for d in active_docs:
            if d.required_document_id is not None:
                docs_by_req_id.setdefault(d.required_document_id, []).append(d)
            else:
                additional_docs.append(d)

        # Build requirement checklist items
        requirements: list[DocumentChecklistRequirement] = []
        mandatory_required_count = 0
        mandatory_uploaded_count = 0
        mandatory_verified_count = 0

        for req in required_defs:
            if req.is_mandatory:
                mandatory_required_count += 1

            matched_docs = docs_by_req_id.get(req.id, [])
            uploaded_doc_resp = None
            is_uploaded = False

            if matched_docs:
                is_uploaded = True
                # Pick verified document first if available, otherwise latest uploaded
                chosen_doc = next(
                    (d for d in matched_docs if d.status == DocumentStatus.VERIFIED.value),
                    matched_docs[0],
                )
                uploaded_doc_resp = await self._format_document_response(
                    chosen_doc, include_download_url=True
                )

                if req.is_mandatory:
                    mandatory_uploaded_count += 1
                    if chosen_doc.status == DocumentStatus.VERIFIED.value:
                        mandatory_verified_count += 1

            requirements.append(
                DocumentChecklistRequirement(
                    required_document_id=req.id,
                    name=req.name,
                    description=req.description,
                    is_mandatory=req.is_mandatory,
                    allowed_file_types=req.allowed_file_types,
                    max_file_size_mb=req.max_file_size_mb or 10,
                    is_uploaded=is_uploaded,
                    uploaded_document=uploaded_doc_resp,
                )
            )

        # Format additional documents
        formatted_additional: list[DocumentResponse] = []
        for add_doc in additional_docs:
            formatted_additional.append(
                await self._format_document_response(add_doc, include_download_url=True)
            )

        all_mandatory_verified = (
            mandatory_required_count > 0 and mandatory_verified_count >= mandatory_required_count
        ) or (mandatory_required_count == 0)

        return ApplicationDocumentChecklistResponse(
            application_id=application_id,
            service_id=service_id,
            service_name=service_name,
            total_requirements=len(required_defs),
            mandatory_required=mandatory_required_count,
            mandatory_uploaded=mandatory_uploaded_count,
            mandatory_verified=mandatory_verified_count,
            all_mandatory_verified=all_mandatory_verified,
            requirements=requirements,
            additional_documents=formatted_additional,
        )

    async def verify_document(
        self,
        *,
        shop_id: int,
        document_id: int,
        verifier_user_id: int,
        notes: Optional[str] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DocumentResponse:
        """Mark a document as verified with audit logging."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        old_values = {
            "status": document.status,
            "rejection_reason": document.rejection_reason,
            "notes": document.notes,
            "verified_at": str(document.verified_at) if document.verified_at else None,
            "verified_by": document.verified_by,
        }

        document.status = DocumentStatus.VERIFIED.value
        document.verified_at = datetime.now(timezone.utc)
        document.verified_by = verifier_user_id
        document.rejection_reason = None
        if notes is not None:
            document.notes = notes

        new_values = {
            "status": DocumentStatus.VERIFIED.value,
            "rejection_reason": None,
            "notes": document.notes,
            "verified_at": str(document.verified_at),
            "verified_by": verifier_user_id,
        }

        await self.audit.record(
            action="document.verify",
            module=Module.DOCUMENT,
            actor_user_id=verifier_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Document",
            entity_id=str(document.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(document)

        return await self._format_document_response(document, include_download_url=True)

    async def reject_document(
        self,
        *,
        shop_id: int,
        document_id: int,
        rejecter_user_id: int,
        rejection_reason: str,
        notes: Optional[str] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DocumentResponse:
        """Mark a document as rejected with a mandatory reason."""
        if not rejection_reason or not rejection_reason.strip():
            raise BadRequestError("Rejection reason is mandatory when rejecting a document")

        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        old_values = {
            "status": document.status,
            "rejection_reason": document.rejection_reason,
            "notes": document.notes,
            "verified_at": str(document.verified_at) if document.verified_at else None,
            "verified_by": document.verified_by,
        }

        document.status = DocumentStatus.REJECTED.value
        document.rejection_reason = rejection_reason.strip()
        document.verified_at = datetime.now(timezone.utc)
        document.verified_by = rejecter_user_id
        if notes is not None:
            document.notes = notes

        new_values = {
            "status": DocumentStatus.REJECTED.value,
            "rejection_reason": document.rejection_reason,
            "notes": document.notes,
            "verified_at": str(document.verified_at),
            "verified_by": rejecter_user_id,
        }

        await self.audit.record(
            action="document.reject",
            module=Module.DOCUMENT,
            actor_user_id=rejecter_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Document",
            entity_id=str(document.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(document)

        return await self._format_document_response(document, include_download_url=True)

    async def update_document(
        self,
        *,
        shop_id: int,
        document_id: int,
        notes: Optional[str] = None,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DocumentResponse:
        """Update document metadata/notes."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        old_values = {"notes": document.notes}
        document.notes = notes
        new_values = {"notes": document.notes}

        await self.audit.record(
            action="document.update",
            module=Module.DOCUMENT,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            shop_id=shop_id,
            entity_type="Document",
            entity_id=str(document.id),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            session=self.session,
        )

        await self.session.commit()
        await self.session.refresh(document)

        return await self._format_document_response(document, include_download_url=True)

    async def archive_or_delete_document(
        self,
        *,
        shop_id: int,
        document_id: int,
        hard_delete: bool = False,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Archive (soft-delete) or permanently delete a document."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        old_values = {
            "status": document.status,
            "storage_key": document.storage_key,
        }

        if hard_delete:
            storage_key = document.storage_key
            await self.session.delete(document)
            await self.audit.record(
                action="document.delete",
                module=Module.DOCUMENT,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                shop_id=shop_id,
                entity_type="Document",
                entity_id=str(document_id),
                old_values=old_values,
                new_values=None,
                ip_address=ip_address,
                user_agent=user_agent,
                session=self.session,
            )
            await self.session.commit()
            # Remove file from storage
            self.storage.delete_file(storage_key)
        else:
            document.status = DocumentStatus.ARCHIVED.value
            await self.audit.record(
                action="document.archive",
                module=Module.DOCUMENT,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                shop_id=shop_id,
                entity_type="Document",
                entity_id=str(document.id),
                old_values=old_values,
                new_values={"status": DocumentStatus.ARCHIVED.value},
                ip_address=ip_address,
                user_agent=user_agent,
                session=self.session,
            )
            await self.session.commit()

    async def get_presigned_url(
        self,
        *,
        shop_id: int,
        document_id: int,
        expires_seconds: int = 900,
    ) -> tuple[str, str, str]:
        """Generate a signed access URL for a shop-scoped document.

        Returns: (presigned_url, mime_type, original_filename)
        """
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        url = self.storage.generate_presigned_url(
            storage_key=document.storage_key,
            expires_seconds=expires_seconds,
            download_filename=document.original_filename,
        )
        return url, document.mime_type, document.original_filename

    async def get_document_stream(
        self,
        *,
        shop_id: int,
        document_id: int,
    ) -> tuple[Any, str, str, int]:
        """Retrieve raw file stream, mime type, filename, and file size for direct streaming."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.shop_id == shop_id,
                )
            )
        )
        document = await self.session.scalar(stmt)
        if not document:
            raise NotFoundError("Document not found in this shop")

        stream = self.storage.get_file_stream(document.storage_key)
        return stream, document.mime_type, document.original_filename, document.file_size
