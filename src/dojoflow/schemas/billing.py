from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from dojoflow.shared.enums import (
    ChargeCategory,
    PaymentKind,
    PaymentMethod,
    PaymentSource,
)

ChargeStatus = Literal['paid', 'partial', 'overdue', 'upcoming', 'waived']


class BeltLookApiRead(BaseModel):
    """O que é preciso para desenhar a faixa."""

    name: str
    primary_color: str
    stripe_color: str | None
    marks: int
    marks_color: str
    tip_color: str | None


class ChargeGraduationApiRead(BaseModel):
    """Cobrança de graduação: o exame, a faixa-alvo e como cobrar."""

    list_id: UUID
    list_name: str
    exam_date: date
    belt: BeltLookApiRead
    whatsapp_url: str | None
    pay_url: str


class ChargeRead(BaseModel):
    """Cobrança (mensalidade ou taxa) como a ficha do aluno mostra."""

    id: int
    public_id: UUID
    kind: PaymentKind
    student_id: int
    enrollment_public_id: UUID
    modality_name: str
    reference_month: date
    due_date: date
    amount: Decimal
    paid: Decimal
    status: ChargeStatus
    created_at: datetime
    # Graduação: o nome da faixa-alvo (ex.: "Verde"); avulsa "Outros": o
    # que está sendo cobrado
    description: str | None = None
    # Avulsa: a categoria (uniforme, campeonato...)
    category: ChargeCategory | None = None
    graduation_entry_id: int | None = None
    paid_at: date | None = None
    # Só na ficha do aluno, em cobranças de graduação ligadas a uma lista
    graduation: ChargeGraduationApiRead | None = None

    @property
    def open_amount(self) -> Decimal:
        return self.amount - self.paid


class GraduationEntryBilling(BaseModel):
    """A cobrança de graduação de um aluno da lista e como cobrá-la."""

    charge: ChargeRead
    days_late: int
    whatsapp_url: str | None
    responsible_name: str | None


class AllocationRead(BaseModel):
    charge_public_id: UUID
    label: str
    amount: Decimal


class AllocationPreview(AllocationRead):
    settles: bool


class PaymentRead(BaseModel):
    """Uma baixa e para onde o dinheiro foi."""

    id: int
    public_id: UUID
    amount: Decimal
    paid_on: date
    method: PaymentMethod | None
    notes: str | None
    allocations: list[AllocationRead]
    # Manual ou automática (InfinitePay, com o recibo dela)
    source: PaymentSource = PaymentSource.MANUAL
    receipt_url: str | None = None


class CheckoutReviewRead(BaseModel):
    """Pago pela InfinitePay, mas o valor em aberto mudou: o mestre
    confere."""

    public_id: UUID
    amount: Decimal
    paid_at: date
    receipt_url: str | None


class PayLinkRead(BaseModel):
    """Link novo do "Cobrar": o endereço, a mensagem e o valor."""

    pay_url: str
    whatsapp_url: str | None
    amount: Decimal


class StudentBillingRead(BaseModel):
    open_total: Decimal
    open_months: str
    whatsapp_url: str | None
    pay_url: str
    charges: list[ChargeRead]
    payments: list[PaymentRead]
    reviews: list[CheckoutReviewRead] = []


OverviewFilter = Literal['overdue', 'upcoming', 'paid', 'all']


class OverdueStudentRead(BaseModel):
    student_id: UUID
    name: str
    modality: str
    amount: Decimal
    days_late: int


class MethodTotalRead(BaseModel):
    """Quanto entrou no mês por forma de pagamento."""

    method: PaymentMethod | None
    amount: Decimal


class ModalityTotalRead(BaseModel):
    """Recebido de previsto, nas cobranças do mês de uma modalidade."""

    modality_name: str
    expected: Decimal
    received: Decimal


class BillingOverviewItemRead(BaseModel):
    student_id: UUID
    name: str
    # Preenchido quando a cobrança vai para o responsável (aluno menor)
    responsible_name: str | None
    modalities: list[str]
    open_amount: Decimal
    days_late: int | None
    whatsapp_url: str | None
    # O vencimento mais antigo em aberto do aluno no filtro
    due_date: date | None = None


class BillingOverviewRead(BaseModel):
    month_expected: Decimal
    month_received: Decimal
    overdue_total: Decimal
    overdue_students: int
    due_soon_total: Decimal
    due_soon_students: int
    # "Falta receber": o que falta do mês e o atrasado de meses anteriores
    month_open_total: Decimal
    # "Ainda não pagaram": alunos com algo no total acima
    unpaid_students: int
    by_method: list[MethodTotalRead]
    by_modality: list[ModalityTotalRead]
    # Quem deve há mais tempo (os 5 primeiros)
    longest_overdue: list[OverdueStudentRead]
    # Alunos em cada filtro, antes da busca
    filter_counts: dict[OverviewFilter, int]
    items: list[BillingOverviewItemRead]
    total: int
    page: int
    page_size: int
