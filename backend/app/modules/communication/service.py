"""Communication Service.

Provides abstraction layer for sending communications via email, WhatsApp, and SMS.
Includes mock implementations for development and testing.
"""

from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.receipt import (
    CommunicationChannel,
    CommunicationHistory,
    CommunicationStatus,
)
from app.models.receipt import Receipt
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send an email.

        Returns:
            True if email was sent successfully, False otherwise
        """
        pass


class WhatsAppProvider(ABC):
    """Abstract base class for WhatsApp providers."""

    @abstractmethod
    async def send_whatsapp(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """Send a WhatsApp message.

        Returns:
            True if message was sent successfully, False otherwise
        """
        pass


class SMSProvider(ABC):
    """Abstract base class for SMS providers."""

    @abstractmethod
    async def send_sms(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """Send an SMS.

        Returns:
            True if SMS was sent successfully, False otherwise
        """
        pass


class MockEmailProvider(EmailProvider):
    """Mock email provider for development and testing.

    Logs email details instead of actually sending.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Mock sending an email by logging details."""
        logger.info(
            "MOCK EMAIL SENT",
            extra={
                "to": to_email,
                "subject": subject,
                "body_preview": body[:100] + "..." if len(body) > 100 else body,
                "has_html": html_body is not None,
            }
        )
        # Simulate success
        return True


class MockWhatsAppProvider(WhatsAppProvider):
    """Mock WhatsApp provider for development and testing."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_whatsapp(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """Mock sending a WhatsApp message by logging details."""
        logger.info(
            "MOCK WHATSAPP SENT",
            extra={
                "to": to_phone,
                "message_preview": message[:100] + "..." if len(message) > 100 else message,
            }
        )
        # Simulate success
        return True


class MockSMSProvider(SMSProvider):
    """Mock SMS provider for development and testing."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_sms(
        self,
        to_phone: str,
        message: str,
    ) -> bool:
        """Mock sending an SMS by logging details."""
        logger.info(
            "MOCK SMS SENT",
            extra={
                "to": to_phone,
                "message": message,
            }
        )
        # Simulate success
        return True


class CommunicationService:
    """Service for handling communications via multiple channels."""

    def __init__(
        self,
        session: AsyncSession,
        email_provider: EmailProvider | None = None,
        whatsapp_provider: WhatsAppProvider | None = None,
        sms_provider: SMSProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()

        # Use mock providers by default for development
        self.email_provider = email_provider or MockEmailProvider()
        self.whatsapp_provider = whatsapp_provider or MockWhatsAppProvider()
        self.sms_provider = sms_provider or MockSMSProvider()

    async def send_receipt(
        self,
        receipt: Receipt,
        channel: CommunicationChannel,
        recipient: str,
        subject: Optional[str] = None,
        shop_id: int | None = None,
        customer_id: int | None = None,
        application_id: int | None = None,
        payment_id: int | None = None,
        billing_id: int | None = None,
        sent_by: int | None = None,
    ) -> CommunicationHistory:
        """Send a receipt via the specified communication channel.

        Args:
            receipt: The receipt to send
            channel: Communication channel (email, whatsapp, sms)
            recipient: Email address or phone number
            subject: Optional subject (for email)
            shop_id: Shop ID for tenant isolation
            customer_id: Optional customer ID
            application_id: Optional application ID
            payment_id: Optional payment ID
            billing_id: Optional billing ID
            sent_by: User ID sending the communication

        Returns:
            Created CommunicationHistory record

        Raises:
            ValueError: If receipt not found or channel not supported
        """
        from sqlalchemy import and_

        # Validate receipt exists and belongs to shop
        if shop_id is not None and receipt.shop_id != shop_id:
            raise ValueError("Receipt does not belong to specified shop")

        # Check for duplicate-send protection
        # Prevent sending the same receipt via same channel to same recipient within 1 hour
        recent_comm = await self._check_duplicate_send(
            receipt_id=receipt.id,
            channel=channel,
            recipient=recipient,
            shop_id=shop_id or receipt.shop_id,
        )

        if recent_comm:
            logger.warning(
                "Duplicate send blocked",
                extra={
                    "receipt_id": receipt.id,
                    "channel": channel.value,
                    "recipient": recipient,
                    "previous_communication_id": recent_comm.id,
                }
            )
            # Return the existing communication record instead of creating duplicate
            return recent_comm

        # Create communication history record
        communication = CommunicationHistory(
            shop_id=shop_id or receipt.shop_id,
            customer_id=customer_id,
            application_id=application_id,
            payment_id=payment_id,
            billing_id=billing_id,
            receipt_id=receipt.id,
            channel=channel.value,
            recipient=recipient,
            subject=subject,
            status=CommunicationStatus.PENDING.value,
        )

        self.session.add(communication)
        await self.session.flush()

        # Attempt to send via appropriate provider
        try:
            success = await self._send_via_provider(
                communication=communication,
                channel=channel,
                recipient=recipient,
                subject=subject or "",
            )

            if success:
                communication.status = CommunicationStatus.SENT.value
                communication.sent_at = datetime.now()
                logger.info(
                    "Communication sent successfully",
                    extra={
                        "communication_id": communication.id,
                        "channel": channel.value,
                        "recipient": recipient,
                    }
                )
            else:
                communication.status = CommunicationStatus.FAILED.value
                communication.error_message = "Provider returned failure"
                logger.warning(
                    "Communication failed to send",
                    extra={
                        "communication_id": communication.id,
                        "channel": channel.value,
                        "recipient": recipient,
                    }
                )

        except Exception as e:
            communication.status = CommunicationStatus.FAILED.value
            communication.error_message = str(e)[:500]  # Limit error message length
            logger.error(
                "Communication error",
                extra={
                    "communication_id": communication.id,
                    "channel": channel.value,
                    "recipient": recipient,
                    "error": str(e),
                },
                exc_info=True
            )

        await self.session.flush()
        return communication

    async def _send_via_provider(
        self,
        communication: CommunicationHistory,
        channel: CommunicationChannel,
        recipient: str,
        subject: str,
    ) -> bool:
        """Send communication via the appropriate provider."""
        # Get receipt for content
        receipt = communication.receipt
        if not receipt:
            raise ValueError("Communication missing receipt reference")

        # Prepare message content based on channel and receipt type
        if channel == CommunicationChannel.EMAIL:
            # For email, we need both plain text and HTML versions
            # For now, we'll use a simple text version
            body = self._generate_email_body(receipt, communication)
            return await self.email_provider.send_email(
                to_email=recipient,
                subject=subject or f"Receipt {receipt.receipt_number}",
                body=body,
            )

        elif channel == CommunicationChannel.WHATSAPP:
            message = self._generate_whatsapp_message(receipt, communication)
            return await self.whatsapp_provider.send_whatsapp(
                to_phone=recipient,
                message=message,
            )

        elif channel == CommunicationChannel.SMS:
            message = self._generate_sms_message(receipt, communication)
            return await self.sms_provider.send_sms(
                to_phone=recipient,
                message=message,
            )

        else:
            raise ValueError(f"Unsupported communication channel: {channel}")

    def _generate_email_body(self, receipt: Receipt, communication: CommunicationHistory) -> str:
        """Generate email body for receipt."""
        if receipt.receipt_type == "invoice":
            return f"""
Dear Customer,

Please find attached your invoice {receipt.receipt_number} for your recent service.

Invoice Details:
- Invoice Number: {receipt.receipt_number}
- Date: {receipt.generated_at.strftime('%d/%m/%Y')}
- Amount Due: Please refer to the attached invoice for details

This is an automated message. Please do not reply to this email.

Best regards,
{receipt.shop.name if receipt.shop else 'Business Management Portal'}
            """.strip()
        else:  # payment_receipt
            return f"""
Dear Customer,

Thank you for your payment! Please find attached your payment receipt {receipt.receipt_number}.

Payment Details:
- Receipt Number: {receipt.receipt_number}
- Date: {receipt.generated_at.strftime('%d/%m/%Y')}
- Amount Paid: Please refer to the attached receipt for details

This is an automated message. Please do not reply to this email.

Best regards,
{receipt.shop.name if receipt.shop else 'Business Management Portal'}
            """.strip()

    def _generate_whatsapp_message(self, receipt: Receipt, communication: CommunicationHistory) -> str:
        """Generate WhatsApp message for receipt."""
        if receipt.receipt_type == "invoice":
            return f"""
Hello! Your invoice {receipt.receipt_number} is ready.

Invoice #{receipt.receipt_number}
Date: {receipt.generated_at.strftime('%d/%m/%Y')}
Please check the attached PDF for details.

Thank you for your business!
{receipt.shop.name if receipt.shop else 'Business Management Portal'}
            """.strip()
        else:  # payment_receipt
            return f"""
Hello! Thank you for your payment.

Receipt #{receipt.receipt_number}
Date: {receipt.generated_at.strftime('%d/%m/%Y')}
Please check the attached PDF for details.

Have a great day!
{receipt.shop.name if receipt.shop else 'Business Management Portal'}
            """.strip()

    def _generate_sms_message(self, receipt: Receipt, communication: CommunicationHistory) -> str:
        """Generate SMS message for receipt (limited to 160 characters)."""
        if receipt.receipt_type == "invoice":
            return f"Invoice {receipt.receipt_number} ready. Please check attached PDF. -{receipt.shop.name if receipt.shop else 'BMP'}"
        else:  # payment_receipt
            return f"Payment received. Receipt {receipt.receipt_number}. Thank you! -{receipt.shop.name if receipt.shop else 'BMP'}"

    async def _check_duplicate_send(
        self,
        receipt_id: int,
        channel: CommunicationChannel,
        recipient: str,
        shop_id: int,
    ) -> Optional[CommunicationHistory]:
        """Check for recent duplicate sends to prevent spam.

        Looks for communications sent in the last hour to the same recipient
        via the same channel for the same receipt.
        """
        from datetime import datetime, timedelta

        one_hour_ago = datetime.now() - timedelta(hours=1)

        stmt = (
            select(CommunicationHistory)
            .where(
                and_(
                    CommunicationHistory.receipt_id == receipt_id,
                    CommunicationHistory.channel == channel.value,
                    CommunicationHistory.recipient == recipient,
                    CommunicationHistory.shop_id == shop_id,
                    CommunicationHistory.created_at >= one_hour_ago,
                    CommunicationHistory.status.in_([
                        CommunicationStatus.SENT.value,
                        CommunicationStatus.QUEUED.value,
                    ]),
                )
            )
            .order_by(CommunicationHistory.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# Import needed for datetime
from datetime import datetime