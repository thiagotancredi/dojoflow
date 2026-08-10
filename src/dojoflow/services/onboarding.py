from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.schemas.academy import AcademyCreate
from dojoflow.schemas.master import MasterCreate
from dojoflow.schemas.onboarding import (
    OnboardingRead,
    OnboardingTelegramCreate,
    OnboardingWebCreate,
)
from dojoflow.services.academy import AcademyService
from dojoflow.services.master import MasterService
from dojoflow.services.security import hash_password
from dojoflow.shared.exceptions import ConflictError


class OnboardingService:
    def __init__(
        self,
        academy_service: AcademyService,
        master_service: MasterService,
        db_session: AsyncSession,
    ) -> None:
        self.academy_service = academy_service
        self.master_service = master_service
        self.db_session = db_session

    async def register_onboarding(
        self,
        data: OnboardingTelegramCreate,
    ) -> OnboardingRead:
        return await self.register_telegram(data)

    @transactional
    async def register_telegram(
        self,
        data: OnboardingTelegramCreate,
    ) -> OnboardingRead:
        existing_master = await self.master_service.get_by_telegram_user_id(
            data.telegram_user_id
        )

        if existing_master is not None:
            raise ConflictError(
                'This Telegram user is already registered as a master.'
            )

        master_data = MasterCreate(
            academy_id=0,
            telegram_user_id=data.telegram_user_id,
            name=data.master_name,
            phone=data.phone,
        )

        return await self._create_academy_and_master(
            academy_name=data.academy_name,
            master_data=master_data,
        )

    @transactional
    async def register_web(
        self,
        data: OnboardingWebCreate,
    ) -> OnboardingRead:
        normalized_email = data.email.strip().lower()
        existing_master = await self.master_service.get_by_email(
            normalized_email
        )

        if existing_master is not None:
            raise ConflictError(
                'This email is already registered as a master.'
            )

        master_data = MasterCreate(
            academy_id=0,
            email=normalized_email,
            password_hash=hash_password(data.password),
            name=data.master_name,
            phone=data.phone,
        )

        return await self._create_academy_and_master(
            academy_name=data.academy_name,
            master_data=master_data,
        )

    async def _create_academy_and_master(
        self,
        academy_name: str,
        master_data: MasterCreate,
    ) -> OnboardingRead:
        academy_id = await self.academy_service.create(
            AcademyCreate(name=academy_name)
        )

        master_payload = master_data.model_copy(
            update={'academy_id': academy_id}
        )
        master_id = await self.master_service.create(master_payload)

        return OnboardingRead(
            academy_id=academy_id,
            master_id=master_id,
        )
