from pydantic import BaseModel, Field

from dojoflow.schemas.base import ReadBase


class MasterCreate(BaseModel):
    academy_id: int = Field(gt=0)
    telegram_user_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class MasterRead(ReadBase):
    academy_id: int
    telegram_user_id: int
    name: str
    phone: str | None


class MasterRegistrationCreate(BaseModel):
    academy_name: str = Field(min_length=2, max_length=120)
    master_name: str = Field(min_length=2, max_length=120)
    telegram_user_id: int = Field(gt=0)
    phone: str | None = Field(default=None, max_length=20)


class MasterRegistrationRead(BaseModel):
    academy_id: int
    master_id: int
