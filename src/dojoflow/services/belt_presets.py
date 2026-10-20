from dojoflow.schemas.belt import BeltPayload
from dojoflow.shared.enums import DurationUnit

TAEKWONDO_NAME = 'Taekwondo'

WHITE = '#f8fafc'
GRAY = '#9ca3af'
YELLOW = '#facc15'
ORANGE = '#f97316'
GREEN = '#16a34a'
BLUE = '#1d4ed8'
RED = '#dc2626'
BLACK = '#111827'

# Tempo dos dans (1º ao 8º), em anos, pela regra do Kukkiwon; 9º Dan sem tempo
DAN_YEARS = (1, 2, 3, 4, 5, 6, 8, 9, None)


def _colored(
    name: str,
    primary: str,
    stripe: str | None = None,
    months: int = 3,
) -> BeltPayload:
    return BeltPayload(
        name=name,
        primary_color=primary,
        stripe_color=stripe,
        min_time_amount=months,
        min_time_unit=DurationUnit.MONTHS,
    )


def _dan(number: int, years: int | None) -> BeltPayload:
    return BeltPayload(
        name=f'Preta {number}º Dan',
        primary_color=BLACK,
        marks=number,
        min_time_amount=years,
        min_time_unit=DurationUnit.YEARS if years else None,
    )


# Sequência padrão sugerida (tudo editável depois)
TAEKWONDO_PRESET: tuple[BeltPayload, ...] = (
    _colored('Branca', WHITE),
    _colored('Cinza', GRAY),
    _colored('Amarela', YELLOW),
    _colored('Laranja', ORANGE),
    _colored('Verde', GREEN),
    _colored('Verde e azul', GREEN, BLUE),
    _colored('Azul', BLUE),
    _colored('Azul e vermelha', BLUE, RED),
    _colored('Vermelha', RED),
    _colored('Vermelha e preta', RED, BLACK, months=6),
    *(_dan(number, years) for number, years in enumerate(DAN_YEARS, 1)),
)
