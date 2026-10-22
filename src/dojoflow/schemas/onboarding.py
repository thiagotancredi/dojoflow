from pydantic import BaseModel, Field


class OnboardingWebCreate(BaseModel):
    academy_name: str = Field(min_length=2, max_length=120)
    master_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)


class OnboardingRead(BaseModel):
    academy_id: int
    master_id: int
