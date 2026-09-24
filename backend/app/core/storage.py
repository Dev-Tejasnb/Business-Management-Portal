"""Object storage abstraction and security helpers.

Handles secure file operations against MinIO / S3:
- Safe storage key generation
- Filename sanitization and path traversal prevention
- MIME type and magic header validation
- Presigned URL generation
- File upload, retrieval, and deletion with error handling
"""

from __future__ import annotations

import io
import mimetypes
import os
import re
import uuid
from datetime import timedelta
from typing import BinaryIO

from minio.error import S3Error

from app.core.config import get_settings
from app.core.exceptions import AppError, BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.core.minio import get_minio

logger = get_logger(__name__)

# Magic byte signatures for common document formats
MAGIC_NUMBERS: dict[bytes, str] = {
    b"%PDF": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WebP check requires sub-check
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    b"PK\x03\x04": "application/zip",  # Also docx, xlsx, pptx
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "application/x-ole-storage",  # Old doc, xls
}

EXTENSION_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "csv": "text/csv",
}

# Dangerous extensions that should NEVER be allowed
DISALLOWED_EXTENSIONS = frozenset({
    "exe", "bat", "cmd", "sh", "bash", "ps1", "vbs", "js", "mjs", "ts",
    "html", "htm", "php", "phtml", "py", "rb", "pl", "cgi", "jar", "war",
    "scr", "pif", "application", "gadget", "msi", "msp", "hta", "cpl",
    "msc", "reg", "dll", "so", "dylib", "bin", "elf", "com",
})


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename, preventing directory traversal and risky characters."""
    if not filename:
        return "document"

    # Strip directory components (both / and \)
    base = os.path.basename(filename.replace("\\", "/"))

    # Remove null bytes and control chars
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)

    # Split name and ext
    parts = base.rsplit(".", 1)
    name = parts[0]
    ext = ("." + parts[1].lower()) if len(parts) > 1 else ""

    # Keep only safe alphanumeric, dash, underscore, space, dot
    name = re.sub(r"[^a-zA-Z0-9_\-\.\s]", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")

    if not name:
        name = "document"

    # Enforce max filename length
    name = name[:100]
    return f"{name}{ext}"


def generate_storage_key(shop_id: int, application_id: int, filename: str) -> str:
    """Generate a deterministic and secure path in object storage.

    Format: shops/{shop_id}/applications/{application_id}/documents/{unique_uuid}_{safe_filename}
    """
    safe_name = sanitize_filename(filename)
    unique_id = uuid.uuid4().hex
    return f"shops/{shop_id}/applications/{application_id}/documents/{unique_id}_{safe_name}"


def detect_mime_type(content: bytes, filename: str) -> str:
    """Detect MIME type from file magic bytes and filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Check magic header
    detected = None
    for magic, mime in MAGIC_NUMBERS.items():
        if content.startswith(magic):
            if mime == "application/zip":
                if ext == "docx":
                    detected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ext == "xlsx":
                    detected = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    detected = "application/zip"
            elif mime == "image/webp":
                if len(content) >= 12 and content[8:12] == b"WEBP":
                    detected = "image/webp"
                else:
                    detected = "application/octet-stream"
            elif mime == "application/x-ole-storage":
                if ext == "doc":
                    detected = "application/msword"
                elif ext == "xls":
                    detected = "application/vnd.ms-excel"
                else:
                    detected = "application/x-ole-storage"
            else:
                detected = mime
            break

    if detected:
        return detected

    # Fallback to extension-based mime type
    if ext in EXTENSION_TO_MIME:
        return EXTENSION_TO_MIME[ext]

    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed

    return "application/octet-stream"


def validate_file(
    filename: str,
    content: bytes,
    allowed_types: list[str] | None = None,
    max_size_mb: int | None = None,
) -> tuple[str, str, int]:
    """Validate a file before upload.

    Returns:
        tuple[safe_filename, detected_mime_type, file_size_bytes]
    Raises:
        BadRequestError: if file validation fails
    """
    if not content:
        raise BadRequestError("File content is empty")

    file_size = len(content)

    # Max size validation (default 25 MB if unspecified)
    effective_max_mb = max_size_mb if (max_size_mb and max_size_mb > 0) else 25
    max_bytes = effective_max_mb * 1024 * 1024
    if file_size > max_bytes:
        raise BadRequestError(
            f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed size of {effective_max_mb} MB"
        )

    safe_name = sanitize_filename(filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if not ext:
        raise BadRequestError("File must have a valid extension")

    if ext in DISALLOWED_EXTENSIONS:
        raise BadRequestError(f"File type '.{ext}' is not permitted")

    mime_type = detect_mime_type(content, safe_name)

    # Allowed types validation if specified
    if allowed_types:
        normalized_allowed: list[str] = []
        for t in allowed_types:
            clean_t = t.lower().strip().lstrip(".")
            normalized_allowed.append(clean_t)

        # Check if extension matches or mime type matches
        ext_match = ext in normalized_allowed
        mime_match = any(
            mime_type.lower() == t or mime_type.lower().startswith(t)
            for t in normalized_allowed
        )

        if not (ext_match or mime_match):
            allowed_str = ", ".join(f".{t}" for t in normalized_allowed)
            raise BadRequestError(
                f"File format '.{ext}' ({mime_type}) is not allowed for this document. Allowed formats: {allowed_str}"
            )

    return safe_name, mime_type, file_size


class StorageService:
    """Service for interacting with MinIO object storage."""

    def __init__(self) -> None:
        self.client = get_minio()
        self.settings = get_settings()

    def ensure_bucket_exists(self) -> None:
        """Ensure the target bucket exists."""
        bucket = self.settings.MINIO_BUCKET
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created MinIO bucket '%s'", bucket)
        except Exception as e:
            logger.error("Failed to check/create MinIO bucket '%s': %s", bucket, e)
            raise AppError(f"Storage service unavailable: {e}")

    def upload_file(
        self,
        storage_key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload a file to object storage."""
        self.ensure_bucket_exists()
        bucket = self.settings.MINIO_BUCKET

        if isinstance(data, bytes):
            length = len(data)
            stream = io.BytesIO(data)
        else:
            data.seek(0, os.SEEK_END)
            length = data.tell()
            data.seek(0)
            stream = data

        try:
            self.client.put_object(
                bucket_name=bucket,
                object_name=storage_key,
                data=stream,
                length=length,
                content_type=content_type,
            )
            logger.info("Successfully uploaded object to '%s/%s'", bucket, storage_key)
        except Exception as e:
            logger.error("Failed to upload object '%s' to bucket '%s': %s", storage_key, bucket, e)
            raise AppError(f"Failed to upload file to storage: {e}")

    def get_file_stream(self, storage_key: str):
        """Retrieve a file stream from object storage."""
        bucket = self.settings.MINIO_BUCKET
        try:
            response = self.client.get_object(bucket, storage_key)
            return response
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchBucket"):
                raise NotFoundError("Document file not found in storage")
            logger.error("S3 error getting object '%s': %s", storage_key, e)
            raise AppError(f"Storage error: {e}")
        except Exception as e:
            logger.error("Failed to get object '%s': %s", storage_key, e)
            raise AppError(f"Failed to retrieve file from storage: {e}")

    def delete_file(self, storage_key: str) -> None:
        """Delete a file from object storage."""
        bucket = self.settings.MINIO_BUCKET
        try:
            self.client.remove_object(bucket, storage_key)
            logger.info("Removed object '%s/%s'", bucket, storage_key)
        except Exception as e:
            logger.warning("Failed to remove object '%s' from bucket '%s': %s", storage_key, bucket, e)

    def generate_presigned_url(
        self,
        storage_key: str,
        expires_seconds: int = 900,
        download_filename: str | None = None,
    ) -> str:
        """Generate a short-lived presigned GET URL for viewing or downloading."""
        bucket = self.settings.MINIO_BUCKET
        headers = {}
        if download_filename:
            safe_dl_name = sanitize_filename(download_filename)
            headers["response-content-disposition"] = f'attachment; filename="{safe_dl_name}"'
        else:
            headers["response-content-disposition"] = "inline"

        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=storage_key,
                expires=timedelta(seconds=expires_seconds),
                response_headers=headers,
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL for '%s': %s", storage_key, e)
            raise AppError(f"Failed to generate secure document URL: {e}")


storage_service = StorageService()


def get_storage_service() -> StorageService:
    """Dependency for obtaining the storage service."""
    return storage_service
