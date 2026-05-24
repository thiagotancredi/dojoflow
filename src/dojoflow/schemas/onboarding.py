from pydantic import BaseModel, Field


class OnboardingCreate(BaseModel):
    academy_name: str = Field(min_length=2, max_length=120)
    master_name: str = Field(min_length=2, max_length=120)
    telegram_user_id: int = Field(gt=0)
    phone: str | None = Field(default=None, max_length=20)


class OnboardingRead(BaseModel):
    academy_id: int
    master_id: int
