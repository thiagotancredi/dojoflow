from dataclasses import dataclass

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.models.academy import Academy
from dojoflow.models.master import Master
from dojoflow.models.modality import Modality
from dojoflow.services.security import create_access_token


@dataclass
class SeedMaster:
    """Academia e mestre fixos, criados uma vez por execução (conftest)."""

    academy_name: str = 'Academia Web Teste'
    master_name: str = 'Mestre Web'
    # E-mail próprio: os testes de cadastro usam mestre@dojoflow.test
    email: str = 'seed@dojoflow.test'
    phone: str = '62999990000'
    password: str = 'senha-segura'
    password_hash: str = ''
    academy_id: int = 0
    master_id: int = 0


SEED = SeedMaster()


def _bearer(master_id: int) -> dict[str, str]:
    return {'Authorization': f'Bearer {create_access_token(master_id)}'}


async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Token do mestre fixo, sem cadastro nem hash de senha."""
    return _bearer(SEED.master_id)


async def other_academy_headers(
    db_session: AsyncSession,
    email: str = 'outro@dojoflow.test',
    academy_name: str = 'Outra Academia',
) -> dict[str, str]:
    """Segunda academia, para testar que uma não vê os dados da outra."""
    academy = Academy(name=academy_name)
    db_session.add(academy)
    await db_session.flush()

    master = Master(
        academy_id=academy.id,
        name='Outro Mestre',
        email=email,
    )
    db_session.add(master)
    await db_session.commit()

    return _bearer(master.id)


async def create_modality(
    db_session: AsyncSession,
    name: str,
    emoji: str = '🥋',
) -> Modality:
    modality = Modality(name=name, emoji=emoji, is_active=True)
    db_session.add(modality)
    await db_session.commit()
    await db_session.refresh(modality)

    return modality
