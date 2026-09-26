# Phase 10: Receipt Generation & Communication System Implementation Plan

## Context
This plan outlines the implementation of Phase 10: Receipt Generation & Communication System for the Business Management Portal SaaS application. The phase builds upon the existing Phase 8 Billing & Payments implementation to add professional invoice and payment receipt generation, secure PDF access, communication capabilities, and integration with the existing frontend.

## Approach Overview
The implementation will follow the existing architectural patterns and reuse established services where possible:
- Extend billing/payment models to support receipt generation
- Create PDF generation service using existing report generation approach if available, otherwise implement lightweight PDF solution
- Leverage existing storage service for secure PDF handling
- Implement communication abstraction layer with mock email provider
- Add communication history tracking
- Implement duplicate-send protection
- Extend RBAC permissions appropriately
- Integrate with existing frontend billing manager component
- Maintain tenant isolation and audit logging throughout

## Files to be Created

### Backend
1. `backend/app/modules/billing/receipt_service.py` - Core receipt generation logic
2. `backend/app/modules/billing/pdf_service.py` - PDF generation utilities
3. `backend/app/modules/communication/` - New module for communication services
   - `__init__.py`
   - `service.py` - CommunicationService abstraction
   - `providers/` - Provider implementations
     - `__init__.py`
     - `email_provider.py` - EmailProvider abstraction
     - `mock_email_provider.py` - Mock EmailProvider for development
     - `whatsapp_provider.py` - WhatsAppProvider abstraction (interface only)
     - `sms_provider.py` - SMSProvider abstraction (interface only)
4. `backend/app/modules/communication/models.py` - Communication history models
5. `backend/app/modules/communication/router.py` - Communication API endpoints
6. `backend/app/modules/billing/router.py` - Extension for receipt endpoints
7. `backend/alembic/versions/` - New migration for receipt/communication tables
8. `backend/app/core/exceptions.py` - Extension for new exception types if needed

### Frontend
1. `frontend/src/types/receipt.ts` - TypeScript types for receipts
2. `frontend/lib/api.ts` - Extension for receipt API endpoints
3. `frontend/components/billing/billing-manager.tsx` - Enhancement for receipt actions
4. `frontend/components/receipt/` - New receipt viewer component
5. `frontend/app/dashboard/applications/[id]/page.tsx` - Integration of receipt actions

## Database Changes
New tables required:
1. `receipts` - Store generated receipt metadata
   - id (PK)
   - shop_id (FK)
   - payment_id (FK) - for payment receipts
   - billing_id (FK) - for invoices (nullable)
   - receipt_number (unique, tenant-aware)
   - receipt_type (invoice/payment_receipt)
   - generated_at
   - generated_by (FK)
   - storage_key (for persisted PDFs)
   - status
   - created_at
   - updated_at

2. `communication_history` - Track sent communications
   - id (PK)
   - shop_id (FK)
   - customer_id (FK)
   - application_id (FK)
   - payment_id (FK)
   - billing_id (FK)
   - receipt_id (FK)
   - channel (email/whatsapp/sms)
   - recipient
   - subject (for email)
   - status (pending/queued/sent/failed)
   - provider
   - provider_message_id
   - error_message
   - sent_at
   - created_at
   - updated_at

## API Endpoints
### Receipt Generation
- `GET /shops/{shop_id}/billings/{billing_id}/invoice` - Generate/view invoice PDF
- `GET /shops/{shop_id}/payments/{payment_id}/receipt` - Generate/view payment receipt PDF
- `POST /shops/{shop_id}/receipts/{receipt_id}/send` - Send receipt via communication channel

### Communication
- `POST /shops/{shop_id}/communications` - Create communication record
- `GET /shops/{shop_id}/communications` - List communication history
- `GET /shops/{shop_id}/communications/{communication_id}` - Get communication details

## Permissions to Add
- `RECEIPT_VIEW` - View/download receipts
- `RECEIPT_GENERATE` - Generate receipts
- `RECEIPT_SEND` - Send receipts
- `COMMUNICATION_VIEW` - View communication history

## Implementation Order
1. Design database schema and create migration
2. Implement receipt model and service layer
3. Implement PDF generation service
4. Implement storage integration for secure PDF access
5. Implement communication abstraction and mock email provider
6. Implement communication history model and service
7. Implement duplicate-send protection mechanisms
8. Extend billing router with receipt endpoints
9. Extend RBAC roles with new permissions
10. Implement audit logging for receipt operations
11. Create frontend types and API client extensions
12. Enhance billing manager component with receipt actions
13. Create receipt viewer component
14. Implement frontend communication integration
15. Write comprehensive tests
16. Run verification and validation

## Verification Checklist
- [ ] Invoice PDF generation works correctly with historical billing data
- [ ] Payment receipt PDF generation shows correct payment details
- [ ] Receipt numbering is unique and concurrency-safe
- [ ] PDFs are securely stored and accessed via signed URLs
- [ ] Tenant isolation is enforced (Shop A cannot access Shop B receipts)
- [ ] RBAC permissions work correctly for all operations
- [ ] Audit logging captures receipt generation and sending events
- [ ] Communication abstraction works with mock email provider
- [ ] Communication history tracks all sent communications
- [ ] Duplicate-send protection prevents accidental resends
- [ ] Frontend integration provides View/Download/Send actions
- [ ] All existing backend tests continue to pass (regression)
- [ ] Frontend build passes without errors
- [ ] Docker services remain healthy
- [ ] Environment variables documented in .env.example

## Known Limitations & Future Work
- WhatsApp/SMS providers are architected but not implemented with real credentials (mock interfaces only)
- Advanced shop branding (GST/tax fields) left for future phases if not already supported
- Async job processing for communications reuse existing Redis/job architecture if present
- Template customization for receipts left for future enhancement

## Stop Condition
Phase 10 is complete when all verification checklist items pass and the implementation has been thoroughly tested without breaking existing functionality.