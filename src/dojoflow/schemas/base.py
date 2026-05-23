from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReadBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: UUID
    created_at: datetime
    updated_at: datetime
