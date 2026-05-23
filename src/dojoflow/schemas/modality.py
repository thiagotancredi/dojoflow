from pydantic import BaseModel, ConfigDict, Field


class ModalityCreate(BaseModel):
    academy_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=80)


class ModalityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academy_id: int
    name: str
