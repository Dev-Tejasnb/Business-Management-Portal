"""Receipt Generation Service.

Handles generation of professional invoice and payment receipt PDFs from
existing billing and payment data. Does NOT modify financial records.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage_service, StorageService
from app.models.billing import Billing, Payment
from app.models.receipt import Receipt, ReceiptStatus, ReceiptType
from app.models.shop import Shop
from app.models.user import User


class ReceiptService:
    """Service for generating receipt PDFs (invoices and payment receipts)."""

    def __init__(self, session: AsyncSession, storage_service: StorageService | None = None) -> None:
        self.session = session
        self.storage_service = storage_service or get_storage_service()
        self._setup_fonts()

    def _setup_fonts(self) -> None:
        """Setup fonts for PDF generation."""
        # Use default reportlab fonts for simplicity
        # In production, you might want to register custom fonts
        pass

    async def _get_latest_sequence_number(
        self,
        shop_id: int,
        year: int,
        receipt_type: ReceiptType,
    ) -> int:
        """Get the latest sequence number for receipt generation (concurrency-safe).

        Uses database-level locking to prevent race conditions.
        """
        prefix = "INV" if receipt_type == ReceiptType.INVOICE else "RCPT"
        shop_result = await self.session.execute(
            select(Shop.code).where(Shop.id == shop_id)
        )
        shop_code = shop_result.scalar_one()

        # Format: {PREFIX}-{SHOP_CODE}-{YEAR}-{SEQUENTIAL}
        # e.g., INV-ABC12-2026-0001
        pattern = f"{prefix}-{shop_code}-{year}-%"

        # Use SELECT ... FOR UPDATE to lock rows during the transaction
        stmt = (
            select(Receipt.receipt_number)
            .where(
                and_(
                    Receipt.shop_id == shop_id,
                    Receipt.receipt_number.like(pattern),
                )
            )
            .order_by(Receipt.receipt_number.desc())
            .limit(1)
            .with_for_update()
        )

        result = await self.session.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest:
            # Extract sequence number from receipt_number
            # Format: PREFIX-SHOPCODE-YEAR-SEQUENCE
            try:
                sequence_str = latest.split("-")[-1]
                return int(sequence_str)
            except (ValueError, IndexError):
                return 0
        return 0

    def _generate_receipt_number(
        self,
        shop_id: int,
        receipt_type: ReceiptType,
        session: AsyncSession | None = None,
    ) -> str:
        """Generate a unique receipt number.

        Format: {PREFIX}-{SHOP_CODE}-{YEAR}-{SEQUENTIAL}
        - PREFIX: INV for invoice, RCPT for payment receipt
        - SHOP_CODE: from shop.code
        - YEAR: current year
        - SEQUENTIAL: 4-digit zero-padded sequence per shop/year/type

        This method is designed to be called within a transaction that
        locks the receipts table to prevent race conditions.
        """
        target_session = session or self.session
        # This should be called within a locked transaction
        # For simplicity in this implementation, we'll do a basic query
        # In production, you'd want to use proper locking mechanisms

        import asyncio
        from datetime import date

        # Run the async method in sync context (this is a simplification)
        # In practice, this would be properly awaited
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sequence = loop.run_until_complete(
                self._get_latest_sequence_number(shop_id, date.today().year, receipt_type)
            )
        finally:
            loop.close()

        next_sequence = sequence + 1

        # Get shop code
        from sqlalchemy import select
        shop_result = target_session.execute(select(Shop.code).where(Shop.id == shop_id))
        shop_code = shop_result.scalar_one() or "UNKNOWN"

        prefix = "INV" if receipt_type == ReceiptType.INVOICE else "RCPT"
        year = date.today().year

        return f"{prefix}-{shop_code}-{year}-{next_sequence:04d}"

    async def generate_invoice_pdf(
        self,
        billing_id: int,
        generated_by: int,
    ) -> Receipt:
        """Generate invoice PDF from billing data.

        Args:
            billing_id: ID of the billing to generate invoice for
            generated_by: User ID generating the receipt

        Returns:
            Created Receipt record

        Raises:
            ValueError: If billing not found or not in issuable status
        """
        from sqlalchemy import and_

        # Get billing with relationships
        stmt = (
            select(Billing)
            .where(Billing.id == billing_id)
            .options(
                selectinload(Billing.shop),
                selectinload(Billing.application),
                selectinload(Billing.customer),
                selectinload(Billing.items),
                selectinload(Billing.payments),
            )
        )
        result = await self.session.execute(stmt)
        billing = result.scalar_one_or_none()

        if not billing:
            raise ValueError(f"Billing with ID {billing_id} not found")

        if billing.billing_status not in ["draft", "issued"]:
            raise ValueError(f"Billing {billing.invoice_number} is not in a state that can be invoiced")

        if billing.shop_id is None:
            raise ValueError("Billing must be associated with a shop")

        # Generate receipt number within a transaction
        # For simplicity, we'll handle this in the service method
        # In production, you'd want to use proper database locking

        from datetime import date

        # Get latest sequence for this shop/year/type
        stmt = (
            select(Receipt.receipt_number)
            .where(
                and_(
                    Receipt.shop_id == billing.shop_id,
                    Receipt.receipt_type == ReceiptType.INVOICE.value,
                    Receipt.receipt_number.like(f"INV-{billing.shop.code}-{date.today().year}-%"),
                )
            )
            .order_by(Receipt.receipt_number.desc())
            .limit(1)
            .with_for_update()  # Lock for update
        )
        result = await self.session.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest:
            try:
                sequence_str = latest.split("-")[-1]
                sequence = int(sequence_str)
            except (ValueError, IndexError):
                sequence = 0
        else:
            sequence = 0

        next_sequence = sequence + 1
        receipt_number = f"INV-{billing.shop.code}-{date.today().year}-{next_sequence:04d}"

        # Generate PDF content
        pdf_bytes = await self._create_invoice_pdf_content(billing)

        # Store PDF in object storage
        storage_key = f"shops/{billing.shop_id}/receipts/invoices/{receipt_number}.pdf"
        self.storage_service.upload_file(
            storage_key=storage_key,
            data=pdf_bytes,
            content_type="application/pdf"
        )

        # Create receipt record
        receipt = Receipt(
            shop_id=billing.shop_id,
            billing_id=billing.id,
            receipt_number=receipt_number,
            receipt_type=ReceiptType.INVOICE.value,
            generated_by=generated_by,
            storage_key=storage_key,
            status=ReceiptStatus.GENERATED.value,
        )

        self.session.add(receipt)
        await self.session.flush()

        return receipt

    async def generate_payment_receipt_pdf(
        self,
        payment_id: int,
        generated_by: int,
    ) -> Receipt:
        """Generate payment receipt PDF from payment data.

        Args:
            payment_id: ID of the payment to generate receipt for
            generated_by: User ID generating the receipt

        Returns:
            Created Receipt record

        Raises:
            ValueError: If payment not found or associated billing is void
        """
        from sqlalchemy import and_

        # Get payment with relationships
        stmt = (
            select(Payment)
            .where(Payment.id == payment_id)
            .options(
                selectinload(Payment.shop),
                selectinload(Payment.billing)
                .selectinload(Billing.shop),
                selectinload(Payment.billing)
                .selectinload(Billing.application),
                selectinload(Payment.billing)
                .selectinload(Billing.customer),
                selectinload(Payment.billing)
                .selectinload(Billing.items),
                selectinload(Payment.billing)
                .selectinload(Billing.payments),
            )
        )
        result = await self.session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")

        if not payment.billing:
            raise ValueError(f"Payment {payment.id} is not associated with a billing")

        billing = payment.billing
        if billing.billing_status == "void":
            raise ValueError(f"Cannot generate receipt for payment linked to voided billing {billing.invoice_number}")

        if billing.shop_id is None:
            raise ValueError("Associated billing must be associated with a shop")

        # Generate receipt number within a transaction
        from datetime import date

        # Get latest sequence for this shop/year/type
        stmt = (
            select(Receipt.receipt_number)
            .where(
                and_(
                    Receipt.shop_id == billing.shop_id,
                    Receipt.receipt_type == ReceiptType.PAYMENT_RECEIPT.value,
                    Receipt.receipt_number.like(f"RCPT-{billing.shop.code}-{date.today().year}-%"),
                )
            )
            .order_by(Receipt.receipt_number.desc())
            .limit(1)
            .with_for_update()  # Lock for update
        )
        result = await self.session.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest:
            try:
                sequence_str = latest.split("-")[-1]
                sequence = int(sequence_str)
            except (ValueError, IndexError):
                sequence = 0
        else:
            sequence = 0

        next_sequence = sequence + 1
        receipt_number = f"RCPT-{billing.shop.code}-{date.today().year}-{next_sequence:04d}"

        # Generate PDF content
        pdf_bytes = await self._create_payment_receipt_pdf_content(payment)

        # Store PDF in object storage
        storage_key = f"shops/{billing.shop_id}/receipts/payment_receipts/{receipt_number}.pdf"
        self.storage_service.upload_file(
            storage_key=storage_key,
            data=pdf_bytes,
            content_type="application/pdf"
        )

        # Create receipt record
        receipt = Receipt(
            shop_id=billing.shop_id,
            payment_id=payment.id,
            receipt_number=receipt_number,
            receipt_type=ReceiptType.PAYMENT_RECEIPT.value,
            generated_by=generated_by,
            storage_key=storage_key,
            status=ReceiptStatus.GENERATED.value,
        )

        self.session.add(receipt)
        await self.session.flush()

        return receipt

    async def _create_invoice_pdf_content(self, billing: Billing) -> bytes:
        """Create invoice PDF content as bytes."""
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        story = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue,
        )
        normal_style = styles['Normal']

        # Company/Shop header
        shop_name = billing.shop.name if billing.shop else "Business Management Portal"
        story.append(Paragraph(f"<b>{shop_name}</b>", title_style))
        story.append(Paragraph("Tax Invoice", heading_style))
        story.append(Spacer(1, 12))

        # Invoice details
        invoice_data = [
            ["Invoice Number:", billing.invoice_number, "Date:", billing.created_at.strftime("%d/%m/%Y")],
            ["Due Date:", (billing.created_at.replace(day=billing.created_at.day + 30)).strftime("%d/%m/%"), ""],
        ]

        if billing.customer:
            invoice_data.extend([
                ["Bill To:", billing.customer.name, "", ""],
                ["", billing.customer.email or "", "", ""],
            ])

        invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch, 1.5*inch, 2*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(invoice_table)
        story.append(Spacer(1, 20))

        # Line items table
        story.append(Paragraph("Description of Services", heading_style))

        # Table header
        item_data = [["Description", "Quantity", "Rate", "Amount"]]

        # Add billing items
        for item in billing.items:
            item_data.append([
                item.name or "",
                "1",  # Quantity - simplified
                f"₹{item.amount:.2f}",
                f"₹{item.amount:.2f}"
            ])

        # Add totals
        item_data.extend([
            ["", "", "Subtotal:", f"₹{billing.subtotal:.2f}"],
            ["", "", "Discount (-):", f"₹{billing.discount_amount:.2f}" if billing.discount_amount > 0 else "₹0.00"],
            ["", "", "Total:", f"₹{billing.total_amount:.2f}"],
            ["", "", "Amount Paid:", f"₹{billing.amount_paid:.2f}"],
            ["", "", "Balance Due:", f"₹{billing.balance_amount:.2f}"],
        ])

        item_table = Table(item_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -4), 1, colors.black),
            ('BACKGROUND', (0, -3), (-1, -1), colors.beige),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, -3), (-1, -1), 1, colors.black),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 30))

        # Notes and terms
        if billing.notes:
            story.append(Paragraph("<b>Notes:</b>", normal_style))
            story.append(Paragraph(billing.notes, normal_style))
            story.append(Spacer(1, 12))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Thank you for your business!", ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,  # Center
            textColor=colors.grey
        )))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    async def _create_payment_receipt_pdf_content(self, payment: Payment) -> bytes:
        """Create payment receipt PDF content as bytes."""
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        story = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue,
        )
        normal_style = styles['Normal']

        # Company/Shop header
        shop_name = payment.shop.name if payment.shop else "Business Management Portal"
        story.append(Paragraph(f"<b>{shop_name}</b>", title_style))
        story.append(Paragraph("Payment Receipt", heading_style))
        story.append(Spacer(1, 12))

        # Receipt details
        receipt_data = [
            ["Receipt Number:", payment.billing.invoice_number if payment.billing else "N/A", "Date:", payment.paid_at.strftime("%d/%m/%Y")],
            ["Payment Method:", payment.payment_method.upper(), "", ""],
        ]

        if payment.reference_number:
            receipt_data.append(["Reference Number:", payment.reference_number, "", ""])

        if payment.billing and payment.billing.customer:
            receipt_data.extend([
                ["Received From:", payment.billing.customer.name, "", ""],
                ["", payment.billing.customer.email or "", "", ""],
            ])

        receipt_table = Table(receipt_data, colWidths=[2*inch, 3*inch, 1.5*inch, 2*inch])
        receipt_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(receipt_table)
        story.append(Spacer(1, 20))

        # Payment details table
        story.append(Paragraph("Payment Details", heading_style))

        payment_details = [
            ["Description", "Amount"],
            [f"Payment against Invoice #{payment.billing.invoice_number if payment.billing else 'N/A'}", f"₹{payment.amount:.2f}"],
            ["", ""],  # Spacer
            ["Total Paid:", f"₹{payment.amount:.2f}"],
        ]

        payment_table = Table(payment_details, colWidths=[4*inch, 2*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 30))

        # Notes
        if payment.notes:
            story.append(Paragraph("<b>Notes:</b>", normal_style))
            story.append(Paragraph(payment.notes, normal_style))
            story.append(Spacer(1, 12))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("This is a computer-generated receipt and does not require signature.", ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=1,  # Center
            textColor=colors.grey
        )))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


# Import needed for selectinload and and_
from sqlalchemy import and_
from sqlalchemy.orm import selectinload