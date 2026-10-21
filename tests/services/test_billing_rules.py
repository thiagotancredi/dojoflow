from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from dojoflow.services.billing_rules import (
    OpenCharge,
    allocate_oldest_first,
    billing_status,
    due_date_for,
    first_monthly_month,
    format_brl,
    months_label,
)

T0 = datetime(2026, 10, 1, tzinfo=UTC)
T1 = datetime(2026, 10, 2, tzinfo=UTC)


def test_first_monthly_month_is_next_month():
    assert first_monthly_month(date(2026, 10, 20)) == date(2026, 11, 1)
    assert first_monthly_month(date(2026, 12, 5)) == date(2027, 1, 1)


def test_due_date_for_uses_due_day():
    assert due_date_for(date(2027, 1, 1), 15) == date(2027, 1, 15)


def test_due_date_for_short_month_uses_last_day():
    assert due_date_for(date(2027, 2, 1), 31) == date(2027, 2, 28)


def test_allocate_oldest_first_example_from_spec():
    jan = OpenCharge(1, date(2027, 1, 15), T0, Decimal('50'))
    feb = OpenCharge(2, date(2027, 2, 15), T0, Decimal('100'))
    assert allocate_oldest_first([feb, jan], Decimal('150')) == [
        (1, Decimal('50')),
        (2, Decimal('100')),
    ]


def test_allocate_partial_stops_at_amount():
    jan = OpenCharge(1, date(2027, 1, 15), T0, Decimal('50'))
    feb = OpenCharge(2, date(2027, 2, 15), T0, Decimal('100'))
    assert allocate_oldest_first([jan, feb], Decimal('70')) == [
        (1, Decimal('50')),
        (2, Decimal('20')),
    ]


def test_allocate_same_due_date_uses_created_at():
    later = OpenCharge(1, date(2027, 1, 15), T1, Decimal('50'))
    earlier = OpenCharge(2, date(2027, 1, 15), T0, Decimal('50'))
    assert allocate_oldest_first([later, earlier], Decimal('50')) == [
        (2, Decimal('50')),
    ]


def test_allocate_rejects_more_than_open():
    with pytest.raises(ValueError, match='maior que o total'):
        allocate_oldest_first(
            [OpenCharge(1, date(2027, 1, 15), T0, Decimal('50'))],
            Decimal('51'),
        )


def test_allocate_rejects_zero_or_negative():
    charges = [OpenCharge(1, date(2027, 1, 15), T0, Decimal('50'))]
    with pytest.raises(ValueError, match='maior que zero'):
        allocate_oldest_first(charges, Decimal('0'))
    with pytest.raises(ValueError, match='maior que zero'):
        allocate_oldest_first(charges, Decimal('-1'))


def test_billing_status():
    today = date(2027, 2, 20)
    assert (
        billing_status(
            Decimal('100'), Decimal('50'), False, date(2027, 1, 15), today
        )
        == 'overdue'
    )
    assert (
        billing_status(
            Decimal('100'), Decimal('50'), False, date(2027, 3, 15), today
        )
        == 'partial'
    )
    assert (
        billing_status(
            Decimal('100'), Decimal('100'), False, date(2027, 1, 15), today
        )
        == 'paid'
    )
    assert (
        billing_status(
            Decimal('100'), Decimal('0'), True, date(2027, 1, 15), today
        )
        == 'waived'
    )
    assert (
        billing_status(
            Decimal('100'), Decimal('0'), False, date(2027, 3, 15), today
        )
        == 'upcoming'
    )


def test_billing_status_due_today_is_not_overdue():
    today = date(2027, 2, 15)
    assert (
        billing_status(Decimal('100'), Decimal('0'), False, today, today)
        == 'upcoming'
    )


def test_months_label():
    assert (
        months_label([date(2027, 1, 1), date(2027, 2, 1)], current_year=2027)
        == 'janeiro e fevereiro'
    )
    assert (
        months_label(
            [date(2027, 3, 1), date(2027, 1, 1), date(2027, 2, 1)],
            current_year=2027,
        )
        == 'janeiro, fevereiro e março'
    )
    assert (
        months_label([date(2026, 12, 1), date(2027, 1, 1)], current_year=2027)
        == 'dezembro de 2026 e janeiro'
    )


def test_months_label_single_and_empty():
    assert months_label([date(2027, 5, 1)], current_year=2027) == 'maio'
    assert not months_label([], current_year=2027)


def test_format_brl():
    assert format_brl(Decimal('150')) == 'R$ 150,00'
    assert format_brl(Decimal('1234.5')) == 'R$ 1.234,50'
    assert format_brl(Decimal('0.05')) == 'R$ 0,05'
