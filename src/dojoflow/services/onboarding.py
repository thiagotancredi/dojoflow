from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.schemas.academy import AcademyCreate
from dojoflow.schemas.master import (
    MasterCreate,
    MasterRegistrationCreate,
    MasterRegistrationRead,
)
from dojoflow.services.academy import AcademyService
from dojoflow.services.master import MasterService
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

    @transactional
    async def register_master(
        self,
        data: MasterRegistrationCreate,
    ) -> MasterRegistrationRead:
        existing_master = await self.master_service.get_by_telegram_user_id(
            data.telegram_user_id
        )

        if existing_master is not None:
            raise ConflictError(
                'This Telegram user is already registered as a master.'
            )

        academy_id = await self.academy_service.create(
            AcademyCreate(name=data.academy_name)
        )

        master_id = await self.master_service.create(
            MasterCreate(
                academy_id=academy_id,
                telegram_user_id=data.telegram_user_id,
                name=data.master_name,
                phone=data.phone,
            )
        )

        return MasterRegistrationRead(
            academy_id=academy_id,
            master_id=master_id,
        )
