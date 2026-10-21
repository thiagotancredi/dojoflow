import calendar
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from dojoflow.services.belt_rules import local_today

DECEMBER = 12

MONTH_NAMES = (
    'janeiro',
    'fevereiro',
    'março',
    'abril',
    'maio',
    'junho',
    'julho',
    'agosto',
    'setembro',
    'outubro',
    'novembro',
    'dezembro',
)


def first_monthly_month(enrolled_on: date) -> date:
    # A primeira mensalidade é sempre a do mês seguinte à matrícula
    if enrolled_on.month == DECEMBER:
        return date(enrolled_on.year + 1, 1, 1)
    return date(enrolled_on.year, enrolled_on.month + 1, 1)


def due_date_for(reference_month: date, due_day: int) -> date:
    # Dia que não existe no mês (ex.: 31 em fevereiro) cai no último dia
    last_day = calendar.monthrange(
        reference_month.year, reference_month.month
    )[1]
    return reference_month.replace(day=min(due_day, last_day))


def billing_status(
    amount: Decimal,
    paid: Decimal,
    waived: bool,
    due_date: date,
    today: date,
) -> str:
    if waived:
        return 'waived'
    if paid >= amount:
        return 'paid'
    # Vencida (mesmo com parte paga) é atrasada; vence hoje ainda não
    if due_date < today:
        return 'overdue'
    if paid > 0:
        return 'partial'
    return 'upcoming'


@dataclass(frozen=True)
class OpenCharge:
    id: int
    due_date: date
    created_at: datetime
    open_amount: Decimal


def allocate_oldest_first(
    charges: list[OpenCharge],
    amount: Decimal,
) -> list[tuple[int, Decimal]]:
    """Distribui a baixa pelas cobranças, da mais antiga para a mais nova."""
    open_charges = [charge for charge in charges if charge.open_amount > 0]
    open_total = sum(
        (charge.open_amount for charge in open_charges), Decimal(0)
    )

    if amount <= 0:
        raise ValueError('O valor da baixa precisa ser maior que zero.')
    if amount > open_total:
        raise ValueError('O valor da baixa é maior que o total em aberto.')

    allocations: list[tuple[int, Decimal]] = []
    remaining = amount

    for charge in sorted(
        open_charges, key=lambda c: (c.due_date, c.created_at)
    ):
        if remaining <= 0:
            break
        part = min(charge.open_amount, remaining)
        allocations.append((charge.id, part))
        remaining -= part

    return allocations


def join_names(names: list[str]) -> str:
    """Ex.: ["a", "b", "c"] → "a, b e c"."""
    if len(names) <= 1:
        return ''.join(names)
    return f'{", ".join(names[:-1])} e {names[-1]}'


def month_name(month: date, current_year: int) -> str:
    name = MONTH_NAMES[month.month - 1]
    return name if month.year == current_year else f'{name} de {month.year}'


def months_label(months: list[date], current_year: int | None = None) -> str:
    """Ex.: "janeiro e fevereiro"; meses de outro ano levam o ano."""
    year = current_year if current_year is not None else local_today().year
    return join_names([
        month_name(month, year) for month in sorted(set(months))
    ])


def format_brl(value: Decimal) -> str:
    """Ex.: Decimal('1234.5') → "R$ 1.234,50"."""
    text = f'{value.quantize(Decimal("0.01")):,.2f}'
    return 'R$ ' + text.replace(',', '_').replace('.', ',').replace('_', '.')


# Telefone brasileiro sem o país: DDD + 8 ou 9 dígitos
LOCAL_PHONE_LENGTHS = (10, 11)
# Com o país (55) na frente
FULL_PHONE_LENGTHS = (12, 13)
BRAZIL_CODE = '55'


def whatsapp_phone(phone: str | None) -> str | None:
    """Número para o wa.me: só dígitos, com 55; inválido → None."""
    digits = ''.join(ch for ch in phone or '' if ch.isdigit())

    if len(digits) in LOCAL_PHONE_LENGTHS:
        return BRAZIL_CODE + digits
    if len(digits) in FULL_PHONE_LENGTHS and digits.startswith(BRAZIL_CODE):
        return digits
    return None


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (
        birth_date.month,
        birth_date.day,
    )
    return today.year - birth_date.year - (0 if had_birthday else 1)
