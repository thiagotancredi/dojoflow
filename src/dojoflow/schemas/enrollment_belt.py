from datetime import date
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.belt import BeltRead


class EnrollmentBeltPayload(BaseModel):
    belt_id: int
    graduated_on: date


class BeltRecord(BaseModel):
    """Um registro do histórico de faixas, com a faixa completa."""

    id: int
    public_id: UUID
    enrollment_id: int
    graduated_on: date
    belt: BeltRead
