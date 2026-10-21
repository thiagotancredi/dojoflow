"""Painel do administrador da plataforma (admin.*): academias e mestres."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.models.master import Master
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.repositories.master import MasterRepository
from dojoflow.repositories.refresh_session import RefreshSessionRepository
from dojoflow.schemas.admin_api import (
    AdminAcademyCreate,
    AdminAcademyRead,
    AdminAcademyUpdate,
    AdminCredentialsRead,
    AdminMasterRead,
    AdminPasswordRead,
)
from dojoflow.schemas.onboarding import OnboardingWebCreate
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.security import generate_password, hash_password
from dojoflow.shared.enums import AcademyStatus
from dojoflow.shared.exceptions import ConflictError, NotFoundError


class AdminService:
    def __init__(  # noqa: PLR0913
        self,
        academy_repository: AcademyRepository,
        onboarding_service: OnboardingService,
        master_repository: MasterRepository,
        refresh_session_repository: RefreshSessionRepository,
        db_session: AsyncSession,
        *,
        own_academy_id: int | None = None,
    ) -> None:
        self.academy_repository = academy_repository
        self.onboarding_service = onboarding_service
        self.master_repository = master_repository
        self.refresh_session_repository = refresh_session_repository
        self.db_session = db_session
        # Academia do administrador logado (para marcar "Sua academia")
        self.own_academy_id = own_academy_id

    def _to_read(self, row: dict[str, Any]) -> AdminAcademyRead:
        master = None

        if row['master_id'] is not None:
            master = AdminMasterRead(
                id=row['master_public_id'],
                name=row['master_name'],
                email=row['master_email'],
                phone=row['master_phone'],
            )

        return AdminAcademyRead(
            id=row['academy_public_id'],
            name=row['academy_name'],
            status=row['academy_status'],
            created_at=row['academy_created_at'],
            master=master,
            is_own=row['academy_id'] == self.own_academy_id,
        )

    async def get_academy(self, academy_id: int) -> AdminAcademyRead:
        row = await self.academy_repository.get_with_master(academy_id)

        if row is None:
            raise NotFoundError('Academy not found.', code='ACADEMY_NOT_FOUND')

        return self._to_read(row)

    async def list_academies(
        self,
        search: str | None = None,
    ) -> list[AdminAcademyRead]:
        rows = await self.academy_repository.list_with_master(search)

        return [self._to_read(row) for row in rows]

    async def create_academy(
        self,
        data: AdminAcademyCreate,
    ) -> AdminCredentialsRead:
        password = generate_password()
        onboarding = await self.onboarding_service.register_web(
            OnboardingWebCreate(
                academy_name=data.academy_name,
                master_name=data.master_name,
                email=data.email,
                password=password,
                phone=data.phone,
            )
        )

        return AdminCredentialsRead(
            academy=await self.get_academy(onboarding.academy_id),
            password=password,
        )

    async def _first_master_id(self, academy_id: int) -> int | None:
        row = await self.academy_repository.get_with_master(academy_id)

        if row is None:
            raise NotFoundError('Academy not found.', code='ACADEMY_NOT_FOUND')

        return row['master_id']

    async def _revoke_academy_sessions(self, academy_id: int) -> None:
        master_ids = await self.db_session.scalars(
            select(Master.id).where(Master.academy_id == academy_id)
        )
        now = datetime.now(UTC)

        for master_id in master_ids.all():
            await self.refresh_session_repository.revoke_all_for_master(
                master_id=master_id, revoked_at=now
            )

    @transactional
    async def update_academy(
        self,
        academy_id: int,
        data: AdminAcademyUpdate,
    ) -> AdminAcademyRead:
        master_id = await self._first_master_id(academy_id)
        fields = data.model_fields_set

        if data.academy_name is not None:
            await self.academy_repository.update_by_id(
                academy_id, {'name': data.academy_name}
            )

        master_data: dict[str, Any] = {}

        if data.master_name is not None:
            master_data['name'] = data.master_name

        if 'phone' in fields:
            master_data['phone'] = data.phone

        if data.email is not None and master_id is not None:
            await self._check_new_email(academy_id, master_id, data.email)
            master_data['email'] = data.email

        if master_data and master_id is not None:
            await self.master_repository.update_by_id(master_id, master_data)

        return await self.get_academy(academy_id)

    async def _check_new_email(
        self,
        academy_id: int,
        master_id: int,
        email: str,
    ) -> None:
        current = await self.master_repository.get_by_id(master_id)
        current_email = (current or {}).get('email')

        if email == current_email:
            return

        if academy_id == self.own_academy_id:
            # Trocar o e-mail do administrador o trancaria fora do painel
            raise ConflictError(
                'The admin email cannot be changed here.',
                code='ADMIN_EMAIL_LOCKED',
            )

        if await self.master_repository.get_by_email(email) is not None:
            raise ConflictError(
                'This email is already registered as a master.',
                code='EMAIL_ALREADY_REGISTERED',
            )

    @transactional
    async def reset_password(self, academy_id: int) -> AdminPasswordRead:
        master_id = await self._first_master_id(academy_id)

        if master_id is None:
            raise NotFoundError('Master not found.', code='MASTER_NOT_FOUND')

        password = generate_password()
        await self.master_repository.update_by_id(
            master_id, {'password_hash': hash_password(password)}
        )
        await self._revoke_academy_sessions(academy_id)

        return AdminPasswordRead(password=password)

    @transactional
    async def set_status(
        self,
        academy_id: int,
        status: AcademyStatus,
    ) -> AdminAcademyRead:
        await self._first_master_id(academy_id)

        if (
            status == AcademyStatus.BLOCKED
            and academy_id == self.own_academy_id
        ):
            raise ConflictError(
                'You cannot block your own academy.',
                code='CANNOT_BLOCK_OWN_ACADEMY',
            )

        await self.academy_repository.update_by_id(
            academy_id, {'status': status}
        )

        if status == AcademyStatus.BLOCKED:
            await self._revoke_academy_sessions(academy_id)

        return await self.get_academy(academy_id)
