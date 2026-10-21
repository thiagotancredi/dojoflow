from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import str_column
from dojoflow.models.base_model import BaseModel


class AcademyBillingSettings(BaseModel):
    __tablename__ = 'academy_billing_settings'

    # Uma linha por academia
    academy_id: Mapped[int] = mapped_column(
        ForeignKey('academy.id'),
        nullable=False,
        unique=True,
    )

    pix_key: Mapped[str | None] = str_column(length=140, nullable=True)
    recipient_name: Mapped[str | None] = str_column(length=120, nullable=True)
    bank_details: Mapped[str | None] = str_column(length=500, nullable=True)
    # Nulo = usa o texto padrão
    message_template: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )
