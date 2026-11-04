from email.utils import parseaddr

import boto3
import pytest
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ParamValidationError,
    ReadTimeoutError,
)
from botocore.stub import Stubber

from dojoflow.core.settings import settings
from dojoflow.integrations.email import sender as sender_module
from dojoflow.integrations.email.sender import (
    ConsoleEmailSender,
    EmailMessage,
    EmailUnavailable,
    SesEmailSender,
    get_email_sender,
)


def make_message(**overrides) -> EmailMessage:
    data = {
        'to': 'aluno@x.com',
        'subject': 'Mensalidade',
        'html': '<p>Oi</p>',
        'text': 'Oi',
        'from_name': 'Sparta Kombat',
        'from_address': 'cobranca@katsuflow.com.br',
        'reply_to': 'mestre@x.com',
    }
    data.update(overrides)
    return EmailMessage(**data)


@pytest.fixture
def ses():
    client = boto3.client(
        'sesv2',
        region_name='sa-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test',  # noqa: S106
    )
    with Stubber(client) as stubber:
        yield client, stubber


def test_ses_sends_html_text_and_reply_to(ses):
    client, stubber = ses
    stubber.add_response(
        'send_email',
        {'MessageId': 'abc-123'},
        {
            'FromEmailAddress': 'Sparta Kombat <cobranca@katsuflow.com.br>',
            'Destination': {'ToAddresses': ['aluno@x.com']},
            'ReplyToAddresses': ['mestre@x.com'],
            'Content': {
                'Simple': {
                    'Subject': {'Data': 'Mensalidade', 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': '<p>Oi</p>', 'Charset': 'UTF-8'},
                        'Text': {'Data': 'Oi', 'Charset': 'UTF-8'},
                    },
                }
            },
        },
    )

    assert SesEmailSender(client).send(make_message()) == 'abc-123'
    stubber.assert_no_pending_responses()


def test_ses_from_name_with_quotes_and_accents_is_encoded(ses):
    client, stubber = ses
    sent = {}

    def capture(params, **kwargs):
        sent.update(params)

    client.meta.events.register(
        'provide-client-params.sesv2.SendEmail', capture
    )
    stubber.add_response('send_email', {'MessageId': 'x'})

    SesEmailSender(client).send(
        make_message(from_name='Dojo "Tigre" São José')
    )

    address = parseaddr(sent['FromEmailAddress'])[1]
    assert address == 'cobranca@katsuflow.com.br'
    assert sent['FromEmailAddress'].isascii()


def test_ses_without_reply_to_omits_field(ses):
    client, stubber = ses
    sent = {}
    client.meta.events.register(
        'provide-client-params.sesv2.SendEmail',
        lambda params, **kwargs: sent.update(params),
    )
    stubber.add_response('send_email', {'MessageId': 'x'})

    SesEmailSender(client).send(make_message(reply_to=None))

    assert 'ReplyToAddresses' not in sent


def test_ses_throttling_raises_email_unavailable(ses):
    client, stubber = ses
    stubber.add_client_error('send_email', 'TooManyRequestsException')

    with pytest.raises(EmailUnavailable):
        SesEmailSender(client).send(make_message())


def test_ses_rejected_address_raises_client_error(ses):
    client, stubber = ses
    stubber.add_client_error('send_email', 'BadRequestException')

    with pytest.raises(ClientError) as error:
        SesEmailSender(client).send(make_message())

    assert not isinstance(error.value, EmailUnavailable)


def test_ses_server_error_raises_email_unavailable(ses):
    client, stubber = ses
    stubber.add_client_error(
        'send_email', 'InternalFailure', http_status_code=500
    )

    with pytest.raises(EmailUnavailable):
        SesEmailSender(client).send(make_message())


class _RaisingClient:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def send_email(self, **kwargs):
        raise self.error


@pytest.mark.parametrize(
    'error',
    [
        EndpointConnectionError(endpoint_url='https://email.aws'),
        ConnectTimeoutError(endpoint_url='https://email.aws'),
        ReadTimeoutError(endpoint_url='https://email.aws'),
        ConnectionClosedError(endpoint_url='https://email.aws'),
    ],
)
def test_ses_network_errors_raise_email_unavailable(error):
    with pytest.raises(EmailUnavailable):
        SesEmailSender(_RaisingClient(error)).send(make_message())


@pytest.mark.parametrize(
    'error',
    [NoCredentialsError(), ParamValidationError(report='campo errado')],
)
def test_ses_setup_errors_are_not_retried(error):
    with pytest.raises(type(error)):
        SesEmailSender(_RaisingClient(error)).send(make_message())


def test_default_ses_client_has_timeouts_and_retries(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sender_module.boto3,
        'client',
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(settings, 'AWS_REGION', 'sa-east-1')

    SesEmailSender()

    ((args, kwargs),) = calls
    assert args == ('sesv2',)
    assert kwargs['region_name'] == 'sa-east-1'
    config = kwargs['config']
    assert config.connect_timeout == 5  # noqa: PLR2004
    assert config.read_timeout == 15  # noqa: PLR2004
    assert config.retries == {'max_attempts': 3, 'mode': 'standard'}


def test_console_sender_records_message():
    sender = ConsoleEmailSender()
    message = make_message()

    assert sender.send(message) == 'console-1'
    assert sender.send(message) == 'console-2'
    assert sender.sent == [message, message]


def test_get_email_sender_by_setting(monkeypatch):
    monkeypatch.setattr(settings, 'EMAIL_BACKEND', 'console')
    assert isinstance(get_email_sender(), ConsoleEmailSender)

    monkeypatch.setattr(settings, 'EMAIL_BACKEND', 'ses')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test')
    assert isinstance(get_email_sender(), SesEmailSender)
