from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ExamBillingRead(BaseModel):
    """Uma lista de graduação que cobra no mês (ou que ainda tem dívida)."""

    list_id: UUID
    name: str
    modality_name: str
    exam_date: date
    payment_due_date: date
    total: Decimal
    received: Decimal
    # Alunos que ainda devem
    owing: int
    # Dias depois da data limite (alguém deve e o prazo passou)
    days_late: int | None
    # Dias até a data limite (alguém deve e o prazo não passou)
    days_to_due: int | None


class GraduationOverviewRead(BaseModel):
    # Cobranças com data limite no mês (sem as dispensadas)
    expected: Decimal
    # Baixas de graduação feitas no mês
    received: Decimal
    # O que falta do mês e o atrasado de antes dele
    open_total: Decimal
    unpaid_students: int
    exams: list[ExamBillingRead]
