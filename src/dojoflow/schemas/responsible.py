from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class ResponsibleCreate(BaseModel):
    academy_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    phone_is_whatsapp: bool = False
    email: str | None = Field(default=None, max_length=255)


class ResponsibleRead(ReadBase):
    academy_id: int
    name: str
    phone: str
    phone_is_whatsapp: bool
    email: str | None
