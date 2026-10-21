"""Cria uma academia com o mestre e imprime a senha gerada.

Uso (no servidor, uma vez, para a academia do administrador):
    docker compose -f compose.prod.yml run --rm api \\
        python -m dojoflow.commands.create_academy \\
        --academy-name "Katsuflow" --master-name "Thiago" \\
        --email thiagotancredii@gmail.com

Local:
    poetry run python -m dojoflow.commands.create_academy ...
"""

import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.session import AsyncSessionLocal, engine
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.repositories.master import MasterRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.schemas.admin_api import AdminAcademyCreate, AdminCredentialsRead
from dojoflow.services.academy import AcademyService
from dojoflow.services.admin import AdminService
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService


async def create_academy(
    session: AsyncSession,
    data: AdminAcademyCreate,
) -> AdminCredentialsRead:
    academy_repository = AcademyRepository(db_session=session)
    master_repository = MasterRepository(db_session=session)
    onboarding_service = OnboardingService(
        academy_service=AcademyService(
            academy_repository=academy_repository, db_session=session
        ),
        master_service=MasterService(
            master_repository=master_repository,
            db_session=session,
        ),
        db_session=session,
    )
    admin_service = AdminService(
        academy_repository=academy_repository,
        onboarding_service=onboarding_service,
        master_repository=master_repository,
        refresh_session_repository=RefreshSessionRepository(
            db_session=session
        ),
        db_session=session,
    )

    return await admin_service.create_academy(data)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--academy-name', required=True)
    parser.add_argument('--master-name', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--phone')
    args = parser.parse_args()

    data = AdminAcademyCreate(
        academy_name=args.academy_name,
        master_name=args.master_name,
        email=args.email,
        phone=args.phone,
    )

    try:
        async with AsyncSessionLocal() as session:
            result = await create_academy(session, data)
    finally:
        await engine.dispose()

    print('Academia criada.')
    print(f'E-mail: {data.email}')
    print(f'Senha: {result.password}')


if __name__ == '__main__':
    asyncio.run(main())
