from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class AddressCreate(BaseModel):
    academy_id: int = Field(gt=0)
    zip_code: str | None = Field(default=None, min_length=8, max_length=8)
    street: str | None = Field(default=None, max_length=160)
    neighborhood: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=120)


class AddressRead(ReadBase):
    academy_id: int
    zip_code: str | None
    street: str | None
    neighborhood: str | None
    city: str | None
    state: str | None
    number: str | None
    complement: str | None
