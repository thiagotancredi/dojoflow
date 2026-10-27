"""Peça de envio de e-mail.

Em produção usa o Amazon SES (v2); em dev e testes, o "console", que só
registra a mensagem. As credenciais da AWS ficam nas variáveis padrão do
boto3 (``AWS_ACCESS_KEY_ID`` e ``AWS_SECRET_ACCESS_KEY``).
"""

import logging
from dataclasses import dataclass
from email.utils import formataddr
from http import HTTPStatus
from typing import Any, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from dojoflow.core.settings import settings

logger = logging.getLogger(__name__)

CHARSET = 'UTF-8'

# Erros do SES que passam com o tempo: vale tentar de novo depois
RETRYABLE_ERROR_CODES = frozenset({
    'TooManyRequestsException',
    'LimitExceededException',
    'SendingPausedException',
})


class EmailUnavailable(Exception):
    """SES fora do ar, limite de envio ou rede: tentar de novo depois."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str
    from_name: str
    from_address: str
    reply_to: str | None = None


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> str:
        """Envia a mensagem e devolve o id dela."""
        ...


class ConsoleEmailSender:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> str:
        self.sent.append(message)
        logger.info('E-mail to=%s subject=%s', message.to, message.subject)
        return f'console-{len(self.sent)}'


class SesEmailSender:
    def __init__(self, client: Any = None) -> None:
        self._client = client or boto3.client(
            'sesv2', region_name=settings.AWS_REGION
        )

    def send(self, message: EmailMessage) -> str:
        request: dict[str, Any] = {
            # formataddr codifica acentos e aspas do nome da academia
            'FromEmailAddress': formataddr((
                message.from_name,
                message.from_address,
            )),
            'Destination': {'ToAddresses': [message.to]},
            'Content': {
                'Simple': {
                    'Subject': {'Data': message.subject, 'Charset': CHARSET},
                    'Body': {
                        'Html': {'Data': message.html, 'Charset': CHARSET},
                        'Text': {'Data': message.text, 'Charset': CHARSET},
                    },
                }
            },
        }
        if message.reply_to:
            request['ReplyToAddresses'] = [message.reply_to]

        try:
            response = self._client.send_email(**request)
        except ClientError as error:
            if _is_retryable(error):
                raise EmailUnavailable(
                    f'SES unavailable ({error.response["Error"]["Code"]}).'
                ) from error
            raise
        except BotoCoreError as error:
            # Rede, tempo esgotado, endpoint inalcançável
            raise EmailUnavailable(
                f'SES unreachable ({type(error).__name__}).'
            ) from error

        return response['MessageId']


def _is_retryable(error: ClientError) -> bool:
    code = error.response.get('Error', {}).get('Code')
    status = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    return code in RETRYABLE_ERROR_CODES or (
        status is not None and status >= HTTPStatus.INTERNAL_SERVER_ERROR
    )


def get_email_sender() -> EmailSender:
    if settings.EMAIL_BACKEND == 'ses':
        return SesEmailSender()
    return ConsoleEmailSender()
