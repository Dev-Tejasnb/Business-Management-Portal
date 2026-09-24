"""Tests for Document Management Module."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.roles import ShopRole
from app.models.application import Application, ApplicationStatus
from app.models.audit_log import AuditLog
from app.models.customer import Customer, CustomerStatus
from app.models.document import Document, DocumentStatus
from app.models.service import Service, ServiceStatus
from app.models.service_field import ServiceRequiredDocument
from app.models.shop import Shop


@pytest.fixture
async def setup_env(create_user, create_shop, create_membership, login, client: AsyncClient):
    """Setup shop, staff user, customer, service with required docs, and application."""
    user = await create_user("staff@example.com", password="Password123!", full_name="Test Staff")
    shop = await create_shop("TEST-001", "Test Shop", "test-shop")
    await create_membership(user, shop, ShopRole.STAFF)
    await login("staff@example.com", "Password123!")

    factory = get_session_factory()
    async with factory() as session:
        customer = Customer(
            shop_id=shop.id,
            name="John Doe",
            mobile="+919876543210",
            email="john@example.com",
            status=CustomerStatus.ACTIVE.value,
        )
        session.add(customer)

        service = Service(
            shop_id=shop.id,
            name="PAN Card Service",
            slug="pan-card",
            description="PAN Card Application",
            base_price=100.00,
            estimated_processing_days=5,
            status=ServiceStatus.ACTIVE.value,
        )
        session.add(service)
        await session.flush()

        doc1 = ServiceRequiredDocument(
            service_id=service.id,
            name="Identity Proof",
            description="Government issued ID",
            is_mandatory=True,
            allowed_file_types=["pdf", "jpg", "png"],
            max_file_size_mb=5,
        )
        doc2 = ServiceRequiredDocument(
            service_id=service.id,
            name="Address Proof",
            description="Utility bill or bank statement",
            is_mandatory=True,
            allowed_file_types=["pdf"],
            max_file_size_mb=10,
        )
        doc3 = ServiceRequiredDocument(
            service_id=service.id,
            name="Photo",
            description="Passport size photo",
            is_mandatory=False,
            allowed_file_types=["jpg", "png"],
            max_file_size_mb=2,
        )
        session.add_all([doc1, doc2, doc3])
        await session.flush()

        application = Application(
            shop_id=shop.id,
            customer_id=customer.id,
            service_id=service.id,
            application_number="APP-TEST-001",
            status=ApplicationStatus.APPLIED.value,
        )
        session.add(application)
        await session.commit()

        await session.refresh(customer)
        await session.refresh(service)
        await session.refresh(doc1)
        await session.refresh(doc2)
        await session.refresh(doc3)
        await session.refresh(application)

        return {
            "user": user,
            "shop": shop,
            "customer": customer,
            "service": service,
            "req_doc1": doc1,
            "req_doc2": doc2,
            "req_doc3": doc3,
            "application": application,
        }


# ===== Test Upload Document =====

async def test_upload_document_success(client: AsyncClient, setup_env: dict):
    """Test successful document upload."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4\n%test\n%%EOF", "application/pdf")}
    data = {
        "required_document_id": str(req_doc1.id),
        "notes": "Test identity proof",
    }
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201, resp.text
    doc_data = resp.json()
    assert doc_data["original_filename"] == "identity.pdf"
    assert doc_data["mime_type"] == "application/pdf"
    assert doc_data["status"] == DocumentStatus.UPLOADED.value
    assert doc_data["notes"] == "Test identity proof"
    assert doc_data["required_document_id"] == req_doc1.id
    assert doc_data["shop_id"] == shop.id
    assert doc_data["application_id"] == app.id

    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Document).where(Document.id == doc_data["id"])
        db_doc = await session.scalar(stmt)
        assert db_doc is not None
        assert db_doc.status == DocumentStatus.UPLOADED.value


async def test_upload_document_invalid_extension(client: AsyncClient, setup_env: dict):
    """Test upload with disallowed extension."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("virus.exe", b"MZ...", "application/octet-stream")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 400, resp.text
    assert "not permitted" in resp.json()["error"]["message"]


async def test_upload_document_exceeds_size_limit(client: AsyncClient, setup_env: dict):
    """Test upload exceeding size limit."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    large_content = b"%PDF-1.4" + b"x" * (6 * 1024 * 1024)  # 6 MB (max allowed is 5 MB)
    files = {"file": ("identity.pdf", large_content, "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 400, resp.text
    assert "exceeds maximum allowed size" in resp.json()["error"]["message"]


async def test_upload_document_without_required_doc(client: AsyncClient, setup_env: dict):
    """Test upload without linking to a required document (additional document)."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]

    files = {"file": ("extra.txt", b"Some text content", "text/plain")}
    data = {"notes": "Additional document"}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201, resp.text
    doc_data = resp.json()
    assert doc_data["required_document_id"] is None
    assert doc_data["original_filename"] == "extra.txt"
    assert doc_data["mime_type"] == "text/plain"


async def test_upload_document_tenant_isolation(
    client: AsyncClient, setup_env: dict, create_shop
):
    """Test that users cannot upload documents to another shop's application."""
    env = setup_env
    app = env["application"]

    shop2 = await create_shop("TEST-002", "Test Shop 2", "test-shop-2")

    factory = get_session_factory()
    async with factory() as session:
        app2 = Application(
            shop_id=shop2.id,
            customer_id=env["customer"].id,
            service_id=env["service"].id,
            application_number="APP-TEST-002",
            status=ApplicationStatus.APPLIED.value,
        )
        session.add(app2)
        await session.commit()
        await session.refresh(app2)

    files = {"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    resp = await client.post(
        f"/api/v1/shops/{shop2.id}/applications/{app2.id}/documents",
        files=files,
        data={},
    )
    # Blocked by RBAC / membership check (403 Forbidden)
    assert resp.status_code == 403, resp.text


# ===== Test List Documents =====

async def test_list_documents_for_application(client: AsyncClient, setup_env: dict):
    """Test listing documents for an application."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]
    req_doc2 = env["req_doc2"]

    files1 = {"file": ("doc1.pdf", b"%PDF-1.4", "application/pdf")}
    data1 = {"required_document_id": str(req_doc1.id)}
    resp1 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files1,
        data=data1,
    )
    assert resp1.status_code == 201

    files2 = {"file": ("doc2.pdf", b"%PDF-1.4", "application/pdf")}
    data2 = {"required_document_id": str(req_doc2.id)}
    resp2 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files2,
        data=data2,
    )
    assert resp2.status_code == 201

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    filenames = {item["original_filename"] for item in data["items"]}
    assert filenames == {"doc1.pdf", "doc2.pdf"}


async def test_list_documents_with_status_filter(client: AsyncClient, setup_env: dict):
    """Test filtering documents by status."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/verify",
        json={"notes": "Looks good"},
    )
    assert resp.status_code == 200

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents?status=uploaded"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents?status=verified"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == DocumentStatus.VERIFIED.value


# ===== Test Document Checklist =====

async def test_get_application_checklist(client: AsyncClient, setup_env: dict):
    """Test getting document checklist for an application."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    service = env["service"]
    req_doc1 = env["req_doc1"]
    req_doc2 = env["req_doc2"]

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents/checklist"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["application_id"] == app.id
    assert data["service_id"] == service.id
    assert data["total_requirements"] == 3
    assert data["mandatory_required"] == 2
    assert data["mandatory_uploaded"] == 0
    assert data["mandatory_verified"] == 0
    assert data["all_mandatory_verified"] is False
    assert len(data["requirements"]) == 3

    req_names = {req["name"]: req for req in data["requirements"]}
    assert req_names["Identity Proof"]["is_mandatory"] is True
    assert req_names["Identity Proof"]["is_uploaded"] is False
    assert req_names["Address Proof"]["is_mandatory"] is True
    assert req_names["Address Proof"]["is_uploaded"] is False
    assert req_names["Photo"]["is_mandatory"] is False
    assert req_names["Photo"]["is_uploaded"] is False

    # Upload first mandatory document (Identity Proof)
    files1 = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data1 = {"required_document_id": str(req_doc1.id)}
    upload_resp1 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files1,
        data=data1,
    )
    assert upload_resp1.status_code == 201
    doc_id1 = upload_resp1.json()["id"]

    # Checklist after 1 upload
    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents/checklist"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mandatory_uploaded"] == 1
    assert data["mandatory_verified"] == 0
    assert data["all_mandatory_verified"] is False

    # Verify first document
    verify_resp1 = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id1}/verify",
        json={"notes": "Verified"},
    )
    assert verify_resp1.status_code == 200

    # Upload and verify second mandatory document (Address Proof)
    files2 = {"file": ("address.pdf", b"%PDF-1.4", "application/pdf")}
    data2 = {"required_document_id": str(req_doc2.id)}
    upload_resp2 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files2,
        data=data2,
    )
    assert upload_resp2.status_code == 201
    doc_id2 = upload_resp2.json()["id"]

    verify_resp2 = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id2}/verify",
        json={"notes": "Verified address"},
    )
    assert verify_resp2.status_code == 200

    # Checklist after both mandatory verified
    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents/checklist"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mandatory_uploaded"] == 2
    assert data["mandatory_verified"] == 2
    assert data["all_mandatory_verified"] is True


# ===== Test Get Document Details =====

async def test_get_document_details(client: AsyncClient, setup_env: dict):
    """Test getting document details."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id), "notes": "Test notes"}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_data = resp.json()
    doc_id = doc_data["id"]

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == doc_id
    assert data["original_filename"] == "identity.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["notes"] == "Test notes"
    assert data["status"] == DocumentStatus.UPLOADED.value
    assert data["uploader_name"] == "Test Staff"
    assert data["required_document_name"] == "Identity Proof"
    assert data["download_url"] is not None


# ===== Test Presigned URL =====

async def test_get_presigned_url(client: AsyncClient, setup_env: dict):
    """Test generating presigned URL for document."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/url?expires_seconds=1800"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["url"] is not None
    assert data["expires_in_seconds"] == 1800
    assert data["mime_type"] == "application/pdf"
    assert data["filename"] == "identity.pdf"


# ===== Test Download Document =====

async def test_download_document(client: AsyncClient, setup_env: dict):
    """Test downloading document binary."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    content = b"%PDF-1.4\n%test\n%%EOF"
    files = {"file": ("identity.pdf", content, "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/download"
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "inline; filename=\"identity.pdf\"" in resp.headers["content-disposition"]
    assert resp.content == content


# ===== Test Update Document =====

async def test_update_document_notes(client: AsyncClient, setup_env: dict):
    """Test updating document notes."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id), "notes": "Initial notes"}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}",
        json={"notes": "Updated notes"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["notes"] == "Updated notes"
    assert data["id"] == doc_id

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Updated notes"


# ===== Test Verify Document =====

async def test_verify_document(client: AsyncClient, setup_env: dict):
    """Test verifying a document."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/verify",
        json={"notes": "Verified successfully"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == DocumentStatus.VERIFIED.value
    assert data["verified_by"] is not None
    assert data["verified_at"] is not None
    assert data["rejection_reason"] is None
    assert data["notes"] == "Verified successfully"


# ===== Test Reject Document =====

async def test_reject_document_with_reason(client: AsyncClient, setup_env: dict):
    """Test rejecting a document with mandatory reason."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/reject",
        json={"rejection_reason": "Blurry image", "notes": "Please retake"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == DocumentStatus.REJECTED.value
    assert data["rejection_reason"] == "Blurry image"
    assert data["notes"] == "Please retake"
    assert data["verified_by"] is not None
    assert data["verified_at"] is not None


async def test_reject_document_without_reason_fails(client: AsyncClient, setup_env: dict):
    """Test that rejecting without reason fails."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Reject without reason (should fail)
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}/reject",
        json={"rejection_reason": "", "notes": "Missing reason"},
    )
    assert resp.status_code in (400, 422), resp.text


# ===== Test Archive/Delete Document =====

async def test_staff_cannot_delete_document(client: AsyncClient, setup_env: dict):
    """Test that staff without DOCUMENT_DELETE cannot delete/archive documents."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}"
    )
    assert resp.status_code == 403, resp.text


async def test_archive_document(
    client: AsyncClient, setup_env: dict, create_user, create_membership, login
):
    """Test archiving (soft deleting) a document by Shop Owner."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    # Upload document as staff
    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Login as shop owner who has DOCUMENT_DELETE
    owner = await create_user("owner@example.com", password="Password123!", full_name="Shop Owner")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner@example.com", "Password123!")

    resp = await client.delete(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}"
    )
    assert resp.status_code == 204, resp.text

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents?include_archived=true"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == DocumentStatus.ARCHIVED.value


async def test_hard_delete_document(
    client: AsyncClient, setup_env: dict, create_user, create_membership, login
):
    """Test hard deleting a document by Shop Owner."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Login as shop owner who has DOCUMENT_DELETE
    owner = await create_user("owner2@example.com", password="Password123!", full_name="Shop Owner 2")
    await create_membership(owner, shop, ShopRole.OWNER)
    await login("owner2@example.com", "Password123!")

    resp = await client.delete(
        f"/api/v1/shops/{shop.id}/documents/{doc_id}?hard_delete=true"
    )
    assert resp.status_code == 204, resp.text

    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Document).where(Document.id == doc_id)
        db_doc = await session.scalar(stmt)
        assert db_doc is None


# ===== Test Document Replacement =====

async def test_document_replacement_archives_previous(client: AsyncClient, setup_env: dict):
    """Test that uploading a new document for the same requirement archives the previous."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files1 = {"file": ("identity1.pdf", b"%PDF-1.4", "application/pdf")}
    data1 = {"required_document_id": str(req_doc1.id), "notes": "First upload"}
    resp1 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files1,
        data=data1,
    )
    assert resp1.status_code == 201
    doc1_id = resp1.json()["id"]

    files2 = {"file": ("identity2.pdf", b"%PDF-1.4", "application/pdf")}
    data2 = {"required_document_id": str(req_doc1.id), "notes": "Second upload"}
    resp2 = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files2,
        data=data2,
    )
    assert resp2.status_code == 201
    doc2_id = resp2.json()["id"]
    assert doc2_id != doc1_id

    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Document).where(Document.id == doc1_id)
        doc1 = await session.scalar(stmt)
        assert doc1 is not None
        assert doc1.status == DocumentStatus.ARCHIVED.value

        stmt = select(Document).where(Document.id == doc2_id)
        doc2 = await session.scalar(stmt)
        assert doc2 is not None
        assert doc2.status == DocumentStatus.UPLOADED.value

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents/checklist"
    )
    assert resp.status_code == 200
    data = resp.json()
    req_name = {req["name"]: req for req in data["requirements"]}
    assert req_name["Identity Proof"]["is_uploaded"] is True
    assert req_name["Identity Proof"]["uploaded_document"]["id"] == doc2_id


# ===== Test Audit Logging =====

async def test_audit_logs_created_on_upload(client: AsyncClient, setup_env: dict):
    """Test that audit logs are created for document upload."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]
    req_doc1 = env["req_doc1"]

    files = {"file": ("identity.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc1.id), "notes": "Test notes"}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    factory = get_session_factory()
    async with factory() as session:
        stmt = select(AuditLog).where(
            AuditLog.entity_type == "Document",
            AuditLog.entity_id == str(doc_id),
            AuditLog.action == "document.upload",
        )
        result = await session.execute(stmt)
        audit_logs = result.scalars().all()
        assert len(audit_logs) == 1
        assert audit_logs[0].shop_id == shop.id


# ===== Additional Edge Cases =====

async def test_upload_document_invalid_required_doc_id(client: AsyncClient, setup_env: dict):
    """Test upload with non-existent required document ID."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]

    files = {"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": "99999"}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 400, resp.text
    assert "Required document definition not found" in resp.json()["error"]["message"]


async def test_upload_document_wrong_service_required_doc(
    client: AsyncClient, setup_env: dict
):
    """Test upload with required document from another service."""
    env = setup_env
    shop = env["shop"]
    app = env["application"]

    factory = get_session_factory()
    async with factory() as session:
        service2 = Service(
            shop_id=shop.id,
            name="Another Service",
            slug="another-service",
            description="Another Service",
            base_price=50.00,
            estimated_processing_days=2,
            status=ServiceStatus.ACTIVE.value,
        )
        session.add(service2)
        await session.flush()

        req_doc_service2 = ServiceRequiredDocument(
            service_id=service2.id,
            name="Service2 Doc",
            description="Doc for service 2",
            is_mandatory=True,
            allowed_file_types=["pdf"],
            max_file_size_mb=5,
        )
        session.add(req_doc_service2)
        await session.commit()
        await session.refresh(req_doc_service2)

    files = {"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"required_document_id": str(req_doc_service2.id)}
    resp = await client.post(
        f"/api/v1/shops/{shop.id}/applications/{app.id}/documents",
        files=files,
        data=data,
    )
    assert resp.status_code == 400, resp.text
    assert "Required document definition not found for this service" in resp.json()["error"]["message"]


async def test_get_nonexistent_document(client: AsyncClient, setup_env: dict):
    """Test getting a document that doesn't exist."""
    env = setup_env
    shop = env["shop"]

    resp = await client.get(
        f"/api/v1/shops/{shop.id}/documents/99999"
    )
    assert resp.status_code == 404, resp.text
