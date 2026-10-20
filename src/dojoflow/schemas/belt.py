from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from dojoflow.models.belt import DEFAULT_MARKS_COLOR
from dojoflow.shared.enums import DurationUnit

MAX_MARKS = 10

HexColor = Annotated[
    str,
    StringConstraints(pattern=r'^#[0-9a-fA-F]{6}$', to_lower=True),
]
BeltName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]


class BeltPayload(BaseModel):
    name: BeltName
    primary_color: HexColor
    stripe_color: HexColor | None = None
    marks: int = Field(default=0, ge=0, le=MAX_MARKS)
    marks_color: HexColor = DEFAULT_MARKS_COLOR
    tip_color: HexColor | None = None
    min_time_amount: int | None = Field(default=None, gt=0)
    min_time_unit: DurationUnit | None = None

    @model_validator(mode='after')
    def _min_time_needs_amount_and_unit(self) -> Self:
        if (self.min_time_amount is None) != (self.min_time_unit is None):
            raise ValueError(
                'min_time_amount and min_time_unit must be set together.'
            )

        return self


class BeltRead(BeltPayload):
    id: int
    public_id: UUID
    modality_id: int
    position: int
