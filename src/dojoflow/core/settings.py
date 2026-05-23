from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    PROJECT_NAME: str = 'DojoFlow'
    API_V1_PREFIX: str = '/api/v1'
    DATABASE_URL: str = (
        'postgresql+asyncpg://postgres:password@localhost:5432/dojoflow'
    )


settings = Settings()
