"""Cifra segredos guardados no banco (hoje: a chave de API da InfinitePay).

A chave de cifra fica fora do banco, em INFINITEPAY_SECRET_KEY.
"""

from cryptography.fernet import Fernet

from dojoflow.core.settings import settings


def _fernet() -> Fernet:
    return Fernet(settings.INFINITEPAY_SECRET_KEY.encode())


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
