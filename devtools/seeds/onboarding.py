import asyncio
from argparse import ArgumentParser
from time import time

from devtools.factories.onboarding import OnboardingPayloadFactory
from dojoflow.database.session import AsyncSessionLocal
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.repositories.master import MasterRepository
from dojoflow.schemas.onboarding import OnboardingCreate
from dojoflow.services.academy import AcademyService
from dojoflow.services.master import MasterService
from dojoflow.services.onboarding import OnboardingService


def parse_args() -> int:
    parser = ArgumentParser()
    parser.add_argument(
        '-q',
        '--quantity',
        type=int,
        default=3,
        help='Number of onboarding records to create.',
    )

    args = parser.parse_args()

    return args.quantity


async def seed_onboarding(quantity: int) -> None:
    base_telegram_user_id = int(time() * 1000)

    async with AsyncSessionLocal() as session:
        academy_repository = AcademyRepository(session)
        master_repository = MasterRepository(session)

        academy_service = AcademyService(
            academy_repository=academy_repository,
            db_session=session,
        )
        master_service = MasterService(
            master_repository=master_repository,
            db_session=session,
        )

        onboarding_service = OnboardingService(
            academy_service=academy_service,
            master_service=master_service,
            db_session=session,
        )

        for index in range(quantity):
            payload = OnboardingPayloadFactory(
                telegram_user_id=base_telegram_user_id + index,
            )

            onboarding = await onboarding_service.register_onboarding(
                OnboardingCreate(**payload)
            )

            print(
                'Created onboarding: '
                f'academy_id={onboarding.academy_id}, '
                f'master_id={onboarding.master_id}'
            )


async def main() -> None:
    quantity = parse_args()
    await seed_onboarding(quantity)


if __name__ == '__main__':
    asyncio.run(main())
