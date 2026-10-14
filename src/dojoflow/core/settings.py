from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = 'change-me-in-production'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    PROJECT_NAME: str = 'DojoFlow'
    API_V1_PREFIX: str = '/api/v1'
    ENVIRONMENT: Literal['dev', 'prod'] = 'dev'
    WEB_APP_URL: str = 'http://localhost:5173'

    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_WEBHOOK_BASE_URL: str = ''
    TELEGRAM_WEBHOOK_SECRET: str = ''
    TELEGRAM_BOT_USERNAME: str = ''

    DATABASE_URL: str = (
        'postgresql+psycopg://postgres:password@localhost:5432/dojoflow'
    )

    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TTL_MINUTES: int = 30
    JWT_REFRESH_TTL_DAYS: int = 14
    JWT_TELEGRAM_LINK_TTL_MINUTES: int = 15
    JWT_TELEGRAM_SETUP_TTL_MINUTES: int = 15

    CORS_ORIGINS: str = 'http://localhost:5173,http://127.0.0.1:5173'

    # When set, POST /onboarding requires X-Internal-Api-Key header.
    INTERNAL_API_KEY: str = ''

    @model_validator(mode='after')
    def _refuse_default_secret_outside_dev(self) -> Self:
        if self.ENVIRONMENT != 'dev' and self.JWT_SECRET == DEFAULT_JWT_SECRET:
            raise ValueError(
                'JWT_SECRET must be set when ENVIRONMENT is not dev.'
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
