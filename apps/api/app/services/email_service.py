from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailMessage:
    to_email: str
    subject: str
    body: str


class EmailService:
    def send(self, message: EmailMessage) -> None:
        raise NotImplementedError


class LoggingEmailService(EmailService):
    def send(self, message: EmailMessage) -> None:
        logger.info(
            "EMAIL OUTBOUND | to=%s | subject=%s | body=%s",
            message.to_email,
            message.subject,
            message.body,
        )
