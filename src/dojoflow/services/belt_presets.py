from dojoflow.schemas.belt import BeltPayload
from dojoflow.shared.enums import DurationUnit

WHITE = '#f8fafc'
GRAY = '#9ca3af'
YELLOW = '#facc15'
ORANGE = '#f97316'
GREEN = '#16a34a'
BLUE = '#1d4ed8'
RED = '#dc2626'
BROWN = '#372822'
PURPLE = '#7c3aed'
BLACK = '#111827'

# Tempo dos dans (1º ao 8º), em anos, pela regra do Kukkiwon; 9º Dan sem tempo
DAN_YEARS = (1, 2, 3, 4, 5, 6, 8, 9, None)


def _months(
    name: str,
    primary: str,
    months: int,
    stripe: str | None = None,
) -> BeltPayload:
    return BeltPayload(
        name=name,
        primary_color=primary,
        stripe_color=stripe,
        min_time_amount=months,
        min_time_unit=DurationUnit.MONTHS,
    )


def _years(
    name: str,
    primary: str,
    years: int,
    stripe: str | None = None,
) -> BeltPayload:
    return BeltPayload(
        name=name,
        primary_color=primary,
        stripe_color=stripe,
        min_time_amount=years,
        min_time_unit=DurationUnit.YEARS,
    )


def _dan(number: int, years: int | None) -> BeltPayload:
    return BeltPayload(
        name=f'Preta {number}º Dan',
        primary_color=BLACK,
        marks=number,
        min_time_amount=years,
        min_time_unit=DurationUnit.YEARS if years else None,
    )


# Pretas iguais nas duas modalidades: 1º ao 9º Dan
BLACK_BELTS = tuple(
    _dan(number, years) for number, years in enumerate(DAN_YEARS, 1)
)

TAEKWONDO_PRESET: tuple[BeltPayload, ...] = (
    _months('Branca', WHITE, 3),
    _months('Cinza', GRAY, 2),
    _months('Amarela', YELLOW, 4),
    _months('Laranja', ORANGE, 4),
    _months('Verde', GREEN, 4),
    _months('Verde e azul', GREEN, 5, stripe=BLUE),
    _months('Azul', BLUE, 8),
    _months('Azul e vermelha', BLUE, 6, stripe=RED),
    _months('Vermelha', RED, 8),
    _years('Vermelha e preta', RED, 1, stripe=BLACK),
    *BLACK_BELTS,
)

KICKBOXING_PRESET: tuple[BeltPayload, ...] = (
    _months('Branca', WHITE, 4),
    _months('Amarela', YELLOW, 6),
    _months('Laranja', ORANGE, 6),
    _months('Verde', GREEN, 8),
    _months('Azul', BLUE, 10),
    _years('Marrom', BROWN, 1),
    *BLACK_BELTS,
)

# Tabela de carências enviada pelo Thiago (23/10/2026); a preta não tem tempo
KARATE_PRESET: tuple[BeltPayload, ...] = (
    _months('Branca', WHITE, 3),
    _months('Cinza', GRAY, 3),
    _months('Azul', BLUE, 3),
    _months('Amarela', YELLOW, 6),
    _months('Vermelha', RED, 12),
    _months('Laranja', ORANGE, 12),
    _months('Verde', GREEN, 18),
    _months('Roxa', PURPLE, 18),
    _months('Marrom', BROWN, 24),
    BeltPayload(name='Preta', primary_color=BLACK),
)

# Sequências padrão sugeridas, pelo nome da modalidade (tudo editável depois)
BELT_PRESETS: dict[str, tuple[BeltPayload, ...]] = {
    'Taekwondo': TAEKWONDO_PRESET,
    'Kickboxing': KICKBOXING_PRESET,
    'Karatê': KARATE_PRESET,
}
