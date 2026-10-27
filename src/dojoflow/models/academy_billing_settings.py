from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column

from dojoflow.database.helper_mapped_columns import (
    datetime_column,
    enum_column,
    str_column,
)
from dojoflow.models.base_model import BaseModel
from dojoflow.shared.enums import PixKeyType


class AcademyBillingSettings(BaseModel):
    __tablename__ = 'academy_billing_settings'

    # Uma linha por academia
    academy_id: Mapped[int] = mapped_column(
        ForeignKey('academy.id'),
        nullable=False,
        unique=True,
    )

    pix_key: Mapped[str | None] = str_column(length=140, nullable=True)
    # Obrigatório quando há chave: define o formato dela no código Pix
    pix_key_type: Mapped[PixKeyType | None] = enum_column(
        PixKeyType, nullable=True
    )
    # Cidade de quem recebe (o código Pix exige)
    pix_city: Mapped[str | None] = str_column(length=60, nullable=True)
    recipient_name: Mapped[str | None] = str_column(length=120, nullable=True)
    bank_details: Mapped[str | None] = str_column(length=500, nullable=True)
    # Nulo = usa o texto padrão
    message_template: Mapped[str | None] = str_column(
        length=1000,
        nullable=True,
    )

    # Baixa automática pela InfinitePay (opcional)
    infinitepay_handle: Mapped[str | None] = str_column(
        length=60, nullable=True
    )
    # Cifrada (core.crypto); nunca volta pela API
    infinitepay_api_key: Mapped[str | None] = str_column(
        length=500, nullable=True
    )
    infinitepay_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    infinitepay_tested_at: Mapped[datetime | None] = datetime_column(
        nullable=True
    )

    # Cobrança do mês por e-mail (desligada por padrão)
    email_billing_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
