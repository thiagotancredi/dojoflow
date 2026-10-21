from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.repositories.master import MasterRepository
from dojoflow.schemas.master import MasterCreate
from dojoflow.schemas.master_context import MasterContextRead
from dojoflow.shared.exceptions import ConflictError, NotFoundError


class MasterService:
    def __init__(
        self,
        master_repository: MasterRepository,
        db_session: AsyncSession,
    ) -> None:
        self.master_repository = master_repository
        self.db_session = db_session

    @transactional
    async def create(self, data: MasterCreate) -> int:
        return await self.master_repository.create(data.model_dump())

    async def get_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> dict[str, Any] | None:
        return await self.master_repository.get_by_telegram_user_id(
            telegram_user_id
        )

    async def get_by_email(
        self,
        email: str,
    ) -> dict[str, Any] | None:
        return await self.master_repository.get_by_email(email)

    async def get_by_id(
        self,
        master_id: int,
    ) -> dict[str, Any] | None:
        return await self.master_repository.get_by_id(master_id)

    async def get_context_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> MasterContextRead | None:
        context = await self.master_repository.get_context_by_telegram_user_id(
            telegram_user_id
        )

        if context is None:
            return None

        return MasterContextRead(**context)

    async def get_context_by_id(
        self,
        master_id: int,
    ) -> MasterContextRead | None:
        context = await self.master_repository.get_context_by_id(master_id)

        if context is None:
            return None

        return MasterContextRead(**context)

    async def get_support_context(
        self,
        master_id: int,
        academy_id: int,
    ) -> MasterContextRead | None:
        """O administrador (master_id) vendo os dados de academy_id."""
        context = await self.master_repository.get_context_by_id(
            master_id, academy_id=academy_id
        )

        if context is None:
            return None

        return MasterContextRead(**context, support_mode=True)

    @transactional
    async def link_telegram_user(
        self,
        master_id: int,
        telegram_user_id: int,
    ) -> MasterContextRead:
        existing = await self.get_by_telegram_user_id(telegram_user_id)

        if existing is not None and int(existing['id']) != master_id:
            raise ConflictError(
                'This Telegram user is already linked to another master.'
            )

        master = await self.get_by_id(master_id)

        if master is None:
            raise NotFoundError(f'Could not find Master with id {master_id}.')

        current_telegram_id = master.get('telegram_user_id')

        if (
            current_telegram_id is not None
            and int(current_telegram_id) != telegram_user_id
        ):
            raise ConflictError(
                'This master is already linked to another Telegram user.'
            )

        await self.master_repository.update_by_id(
            record_id=master_id,
            data={'telegram_user_id': telegram_user_id},
        )

        context = await self.get_context_by_id(master_id)

        if context is None:
            raise NotFoundError(f'Could not find Master with id {master_id}.')

        return context

    @transactional
    async def set_credentials(
        self,
        master_id: int,
        email: str,
        password_hash: str,
    ) -> MasterContextRead:
        normalized_email = email.strip().lower()
        existing = await self.get_by_email(normalized_email)

        if existing is not None and int(existing['id']) != master_id:
            raise ConflictError(
                'This email is already registered as a master.',
                code='EMAIL_ALREADY_REGISTERED',
            )

        master = await self.get_by_id(master_id)

        if master is None:
            raise NotFoundError(f'Could not find Master with id {master_id}.')

        await self.master_repository.update_by_id(
            record_id=master_id,
            data={
                'email': normalized_email,
                'password_hash': password_hash,
            },
        )

        context = await self.get_context_by_id(master_id)

        if context is None:
            raise NotFoundError(f'Could not find Master with id {master_id}.')

        return context
