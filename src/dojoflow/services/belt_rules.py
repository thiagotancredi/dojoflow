import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from dojoflow.shared.enums import DurationUnit, Eligibility

ACADEMY_TIMEZONE = ZoneInfo('America/Sao_Paulo')
MONTHS_PER_YEAR = 12


def local_today() -> date:
    return datetime.now(ACADEMY_TIMEZONE).date()


def add_duration(start: date, amount: int, unit: DurationUnit) -> date:
    if unit is DurationUnit.DAYS:
        return start + timedelta(days=amount)

    months = amount * MONTHS_PER_YEAR if unit is DurationUnit.YEARS else amount
    # Soma pelo calendário; dia inexistente cai no último dia do mês
    year, month_index = divmod(
        start.year * MONTHS_PER_YEAR + start.month - 1 + months,
        MONTHS_PER_YEAR,
    )
    month = month_index + 1
    last_day = calendar.monthrange(year, month)[1]

    return date(year, month, min(start.day, last_day))


def eligible_on(
    graduated_on: date,
    amount: int | None,
    unit: DurationUnit | None,
) -> date | None:
    if amount is None or unit is None:
        return None

    return add_duration(graduated_on, amount, unit)


def evaluate_eligibility(
    graduated_on: date | None,
    amount: int | None,
    unit: DurationUnit | None,
    reference: date,
) -> Eligibility:
    if graduated_on is None:
        return Eligibility.NO_BELT

    target = eligible_on(graduated_on, amount, unit)

    if target is None:
        return Eligibility.NO_REQUIREMENT

    if target <= reference:
        return Eligibility.ELIGIBLE

    return Eligibility.NOT_YET
