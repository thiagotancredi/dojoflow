from dojoflow.schemas.belt import BeltRead


def belts_to_award(
    belts: list[BeltRead],
    current_belt_id: int | None,
    target_belt_id: int,
) -> list[BeltRead]:
    """Faixas que a aprovação grava: as puladas e a alvo, na ordem.

    `belts` vem na ordem da modalidade. Sem faixa atual, faixa atual de
    fora da modalidade ou alvo que não está acima da atual: só a alvo.
    """
    by_id = {belt.id: belt for belt in belts}
    target = by_id[target_belt_id]
    current = by_id.get(current_belt_id) if current_belt_id else None

    if current is None or target.position <= current.position:
        return [target]

    return [
        belt
        for belt in belts
        if current.position < belt.position <= target.position
    ]
