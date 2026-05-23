from sqlalchemy.orm import Mapped

from dojoflow.database.helper_mapped_columns import (
    enum_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.models.enums import AcademyStatus


class Academy(BaseModel):
    __tablename__ = 'academy'

    name: Mapped[str] = str_column(120)

    status: Mapped[AcademyStatus] = enum_column(
        AcademyStatus, default=AcademyStatus.ACTIVE
    )
