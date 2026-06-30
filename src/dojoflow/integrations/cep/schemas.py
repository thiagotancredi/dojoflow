from pydantic import BaseModel, Field


class CepAddress(BaseModel):
    zip_code: str = Field(min_length=8, max_length=8)
    street: str | None = None
    neighborhood: str | None = None
    city: str
    state: str = Field(min_length=2, max_length=2)
    provider: str
