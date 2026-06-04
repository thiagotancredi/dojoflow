from pydantic import BaseModel, ConfigDict, Field


class ModalityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    emoji: str = Field(min_length=1, max_length=10)
    is_active: bool = True


class ModalityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    emoji: str
    is_active: bool


class ModalityOptionRead(BaseModel):
    id: int
    name: str
    emoji: str
    is_selected: bool


class AcademyModalityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academy_id: int
    modality_id: int
