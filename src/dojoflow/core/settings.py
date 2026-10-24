from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = 'change-me-in-production'
# Só para desenvolvimento e testes. Em produção, gere outra (ver
# deploy/env.prod.example)
DEFAULT_INFINITEPAY_SECRET_KEY = 'cw-73PkU28RMAdbrer-rsS8UYKezoxp-zirg9U9SPyM='


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        # Variáveis que sobraram de versões antigas (ex.: TELEGRAM_*) no .env
        # não impedem a API de subir
        extra='ignore',
    )

    PROJECT_NAME: str = 'DojoFlow'
    API_V1_PREFIX: str = '/api/v1'
    ENVIRONMENT: Literal['dev', 'prod'] = 'dev'
    WEB_APP_URL: str = 'http://localhost:5173'

    DATABASE_URL: str = (
        'postgresql+psycopg://postgres:password@localhost:5432/dojoflow'
    )

    # Fila do worker (Celery). Local: o Redis do compose.yml (porta 6380)
    REDIS_URL: str = 'redis://localhost:6380/0'

    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TTL_MINUTES: int = 30
    JWT_REFRESH_TTL_DAYS: int = 14

    # Cifra as chaves de API da InfinitePay guardadas no banco (Fernet)
    INFINITEPAY_SECRET_KEY: str = DEFAULT_INFINITEPAY_SECRET_KEY

    CORS_ORIGINS: str = 'http://localhost:5173,http://127.0.0.1:5173'

    # E-mail do único administrador da plataforma (painel admin.*).
    # Vazio = ninguém é administrador.
    ADMIN_EMAIL: str = ''

    @model_validator(mode='after')
    def _refuse_default_secret_outside_dev(self) -> Self:
        if self.ENVIRONMENT != 'dev' and self.JWT_SECRET == DEFAULT_JWT_SECRET:
            raise ValueError(
                'JWT_SECRET must be set when ENVIRONMENT is not dev.'
            )
        if (
            self.ENVIRONMENT != 'dev'
            and self.INFINITEPAY_SECRET_KEY == DEFAULT_INFINITEPAY_SECRET_KEY
        ):
            raise ValueError(
                'INFINITEPAY_SECRET_KEY must be set when ENVIRONMENT is not '
                'dev.'
            )

        return self

    @property
    def cookie_secure(self) -> bool:
        return self.ENVIRONMENT != 'dev'

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(',')
            if origin.strip()
        ]


settings = Settings()
