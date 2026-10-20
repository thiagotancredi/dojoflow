from datetime import date

import pytest

from dojoflow.services.belt_rules import (
    add_duration,
    eligible_on,
    evaluate_eligibility,
)
from dojoflow.shared.enums import DurationUnit, Eligibility


@pytest.mark.parametrize(
    ('start', 'amount', 'unit', 'expected'),
    [
        (date(2026, 1, 15), 1, DurationUnit.MONTHS, date(2026, 2, 15)),
        (date(2026, 1, 31), 1, DurationUnit.MONTHS, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, DurationUnit.MONTHS, date(2028, 2, 29)),
        (date(2026, 11, 30), 3, DurationUnit.MONTHS, date(2027, 2, 28)),
        (date(2024, 2, 29), 1, DurationUnit.YEARS, date(2025, 2, 28)),
        (date(2026, 1, 1), 90, DurationUnit.DAYS, date(2026, 4, 1)),
    ],
)
def test_add_duration_uses_calendar(
    start: date,
    amount: int,
    unit: DurationUnit,
    expected: date,
) -> None:
    assert add_duration(start, amount, unit) == expected


def test_eligible_exactly_on_exam_day() -> None:
    graduated_on = date(2026, 8, 1)

    assert (
        evaluate_eligibility(
            graduated_on, 3, DurationUnit.MONTHS, date(2026, 11, 1)
        )
        == Eligibility.ELIGIBLE
    )
    assert (
        evaluate_eligibility(
            graduated_on, 3, DurationUnit.MONTHS, date(2026, 10, 31)
        )
        == Eligibility.NOT_YET
    )


def test_eligibility_is_measured_on_exam_date() -> None:
    # 2 meses hoje (20/10), precisa de 3, exame em 20/11
    assert (
        evaluate_eligibility(
            date(2026, 8, 20), 3, DurationUnit.MONTHS, date(2026, 11, 20)
        )
        == Eligibility.ELIGIBLE
    )


def test_no_belt_and_no_requirement() -> None:
    assert (
        evaluate_eligibility(None, 3, DurationUnit.MONTHS, date(2026, 1, 1))
        == Eligibility.NO_BELT
    )
    assert (
        evaluate_eligibility(date(2020, 1, 1), None, None, date(2026, 1, 1))
        == Eligibility.NO_REQUIREMENT
    )


def test_eligible_on() -> None:
    assert eligible_on(date(2026, 8, 1), 3, DurationUnit.MONTHS) == date(
        2026, 11, 1
    )
    assert eligible_on(date(2026, 8, 1), None, None) is None
