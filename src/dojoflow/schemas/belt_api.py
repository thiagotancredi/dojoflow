from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.belt import BeltRead
from dojoflow.shared.enums import DurationUnit


class BeltApiRead(BaseModel):
    id: UUID
    name: str
    primary_color: str
    stripe_color: str | None
    marks: int
    marks_color: str
    tip_color: str | None
    min_time_amount: int | None
    min_time_unit: DurationUnit | None
    position: int

    @classmethod
    def from_internal(cls, belt: BeltRead) -> 'BeltApiRead':
        return cls(
            id=belt.public_id,
            **belt.model_dump(exclude={'id', 'public_id', 'modality_id'}),
        )


class BeltOrderRequest(BaseModel):
    belt_ids: list[UUID]
