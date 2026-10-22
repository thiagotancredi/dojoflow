from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class MasterCreate(BaseModel):
    academy_id: int = Field(ge=0)
    email: str | None = Field(default=None, max_length=255)
    password_hash: str | None = Field(default=None, max_length=255)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class MasterRead(ReadBase):
    academy_id: int
    email: str | None
    name: str
    phone: str | None
