from pydantic import BaseModel


class EmailBillingStatusApi(BaseModel):
    """Situação da cobrança por e-mail da academia."""

    enabled: bool
    # Só liga com chave Pix ou InfinitePay configurada
    can_enable: bool
    students_without_email: int


class EmailBillingUpdateApi(BaseModel):
    enabled: bool


class EmailPreviewApi(BaseModel):
    subject: str
    html: str
