from decimal import Decimal

import pytest

from dojoflow.services.pix import crc16, normalize_pix_key, pix_copy_paste
from dojoflow.shared.enums import PixKeyType


def test_crc16_matches_central_bank_example():
    payload = (
        '00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-'
        '4266554400005204000053039865802BR5913Fulano de Tal6008BRASILIA'
        '62070503***6304'
    )

    assert crc16(payload) == '1D3D'


def test_pix_copy_paste_with_amount():
    code = pix_copy_paste(
        '+5511912345678', 'Thiago T. Trajano', 'São Paulo', Decimal('300')
    )

    assert code == (
        '00020126360014br.gov.bcb.pix0114+5511912345678520400005303986'
        '5406300.005802BR5916THIAGO T TRAJANO6009SAO PAULO62070503***'
        '63047BFD'
    )


def test_pix_copy_paste_truncates_name_and_city():
    code = pix_copy_paste(
        'dojo@exemplo.com',
        'Associação Desportiva São João Batista',
        'São José dos Campos',
        Decimal('150.5'),
    )

    assert '5925ASSOCIACAO DESPORTIVA SAO' in code
    assert '6015SAO JOSE DOS CA' in code
    assert '5406150.50' in code
    assert code[-4:] == crc16(code[:-4])


@pytest.mark.parametrize(
    ('raw', 'key_type', 'expected'),
    [
        ('529.982.247-25', PixKeyType.CPF, '52998224725'),
        ('11.222.333/0001-81', PixKeyType.CNPJ, '11222333000181'),
        ('(11) 91234-5678', PixKeyType.PHONE, '+5511912345678'),
        ('+55 11 91234-5678', PixKeyType.PHONE, '+5511912345678'),
        ('5511912345678', PixKeyType.PHONE, '+5511912345678'),
        (' Dojo@Exemplo.COM ', PixKeyType.EMAIL, 'dojo@exemplo.com'),
        (
            '123E4567-E12B-12D1-A456-426655440000',
            PixKeyType.RANDOM,
            '123e4567-e12b-12d1-a456-426655440000',
        ),
    ],
)
def test_normalize_pix_key(raw, key_type, expected):
    assert normalize_pix_key(raw, key_type) == expected


@pytest.mark.parametrize(
    ('raw', 'key_type'),
    [
        ('52998224726', PixKeyType.CPF),  # dígito errado
        ('11111111111', PixKeyType.CPF),  # todos iguais
        ('11222333000180', PixKeyType.CNPJ),
        ('1234', PixKeyType.PHONE),
        ('dojo.exemplo.com', PixKeyType.EMAIL),
        ('nao-e-uuid', PixKeyType.RANDOM),
        ('dojo@exemplo.com', PixKeyType.CPF),  # tipo trocado
    ],
)
def test_normalize_pix_key_rejects(raw, key_type):
    with pytest.raises(ValueError):  # noqa: PT011
        normalize_pix_key(raw, key_type)
