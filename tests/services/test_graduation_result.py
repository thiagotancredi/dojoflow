"""Faixas que a aprovação grava na ficha: a alvo e as puladas."""

from dojoflow.schemas.belt import BeltRead
from dojoflow.services.graduation_result import belts_to_award

BELTS = [
    BeltRead.model_construct(id=10 + position, position=position, name=name)
    for position, name in enumerate(
        ('Branca', 'Amarela', 'Laranja', 'Verde'), start=1
    )
]
ID = {belt.name: belt.id for belt in BELTS}


def _names(current: str | None, target: str) -> list[str]:
    current_id = ID[current] if current else None
    return [b.name for b in belts_to_award(BELTS, current_id, ID[target])]


def test_next_belt_only() -> None:
    assert _names('Amarela', 'Laranja') == ['Laranja']


def test_skip_awards_every_belt_in_between() -> None:
    assert _names('Amarela', 'Verde') == ['Laranja', 'Verde']


def test_no_current_belt_awards_only_target() -> None:
    assert _names(None, 'Laranja') == ['Laranja']


def test_target_not_above_current_awards_only_target() -> None:
    assert _names('Verde', 'Amarela') == ['Amarela']
    assert _names('Laranja', 'Laranja') == ['Laranja']


def test_current_belt_not_in_modality_awards_only_target() -> None:
    assert [b.name for b in belts_to_award(BELTS, 999, ID['Verde'])] == [
        'Verde'
    ]
