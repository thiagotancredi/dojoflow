"""Código Pix copia e cola (BR Code estático) e formato das chaves Pix.

Segue o padrão EMV do Banco Central: cada campo é ID + tamanho (2 dígitos)
+ valor, e os 4 últimos caracteres são um CRC16 de tudo o que vem antes.
"""

import re
import unicodedata
import uuid
from decimal import Decimal

from dojoflow.shared.enums import PixKeyType

MAX_NAME = 25
MAX_CITY = 15
MAX_EMAIL = 77
CPF_LENGTH = 11
CNPJ_LENGTH = 14
BR_PREFIX = '55'


def crc16(payload: str) -> str:
    """CRC16/CCITT-FALSE (poly 0x1021, início 0xFFFF), 4 hex maiúsculos."""
    crc = 0xFFFF
    for byte in payload.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f'{crc:04X}'


def _field(field_id: str, value: str) -> str:
    return f'{field_id}{len(value):02d}{value}'


def _plain(text: str, limit: int) -> str:
    """Maiúsculas, sem acento nem pontuação, cortado no limite do campo."""
    decomposed = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = re.sub(r'[^A-Z0-9 ]', '', ascii_text.upper())
    return ' '.join(cleaned.split())[:limit].rstrip()


def pix_copy_paste(
    key: str, recipient_name: str, city: str, amount: Decimal
) -> str:
    """Código Pix copia e cola com valor; `key` já no formato do BR Code."""
    account = _field('00', 'br.gov.bcb.pix') + _field('01', key)
    payload = (
        _field('00', '01')
        + _field('26', account)
        + _field('52', '0000')
        + _field('53', '986')
        + _field('54', f'{amount.quantize(Decimal("0.01"))}')
        + _field('58', 'BR')
        + _field('59', _plain(recipient_name, MAX_NAME))
        + _field('60', _plain(city, MAX_CITY))
        + _field('62', _field('05', '***'))
        + '6304'
    )
    return payload + crc16(payload)


def _check_digit(digits: str, weights: list[int]) -> str:
    rest = sum(int(d) * w for d, w in zip(digits, weights, strict=True)) % 11
    return '0' if rest < 2 else str(11 - rest)  # noqa: PLR2004


def _valid_cpf(digits: str) -> bool:
    if len(digits) != CPF_LENGTH or len(set(digits)) == 1:
        return False
    first = _check_digit(digits[:9], list(range(10, 1, -1)))
    second = _check_digit(digits[:9] + first, list(range(11, 1, -1)))
    return digits[9:] == first + second


def _valid_cnpj(digits: str) -> bool:
    if len(digits) != CNPJ_LENGTH or len(set(digits)) == 1:
        return False
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    first = _check_digit(digits[:12], weights)
    second = _check_digit(digits[:12] + first, [6, *weights])
    return digits[12:] == first + second


def _phone(raw: str) -> str:
    digits = re.sub(r'\D', '', raw)
    if len(digits) in {10, 11}:
        digits = BR_PREFIX + digits
    if len(digits) not in {12, 13} or not digits.startswith(BR_PREFIX):
        raise ValueError('Celular inválido: use DDD + número.')
    return f'+{digits}'


def _email(raw: str) -> str:
    email = raw.strip().lower()
    user, at, domain = email.partition('@')
    if (
        not at
        or not user
        or '@' in domain
        or '.' not in domain.strip('.')
        or len(email) > MAX_EMAIL
    ):
        raise ValueError('E-mail inválido.')
    return email


def _random(raw: str) -> str:
    try:
        return str(uuid.UUID(raw.strip()))
    except ValueError:
        raise ValueError('Chave aleatória inválida.') from None


def normalize_pix_key(key: str, key_type: PixKeyType) -> str:
    """Chave no formato do BR Code; ValueError se não combina com o tipo."""
    if key_type is PixKeyType.CPF:
        digits = re.sub(r'[.\-\s]', '', key)
        if not _valid_cpf(digits):
            raise ValueError('CPF inválido.')
        return digits
    if key_type is PixKeyType.CNPJ:
        digits = re.sub(r'[.\-/\s]', '', key)
        if not _valid_cnpj(digits):
            raise ValueError('CNPJ inválido.')
        return digits
    if key_type is PixKeyType.PHONE:
        return _phone(key)
    if key_type is PixKeyType.EMAIL:
        return _email(key)
    return _random(key)
