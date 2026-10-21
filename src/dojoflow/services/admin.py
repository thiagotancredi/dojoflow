"""Painel do administrador da plataforma (admin.*): academias e mestres."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.repositories.academy import AcademyRepository
from dojoflow.schemas.admin_api import (
    AdminAcademyCreate,
    AdminAcademyRead,
    AdminCredentialsRead,
    AdminMasterRead,
)
from dojoflow.schemas.onboarding import OnboardingWebCreate
from dojoflow.services.onboarding import OnboardingService
from dojoflow.services.security import generate_password
from dojoflow.shared.exceptions import NotFoundError


class AdminService:
    def __init__(
        self,
        academy_repository: AcademyRepository,
        onboarding_service: OnboardingService,
        db_session: AsyncSession,
        own_academy_id: int | None = None,
    ) -> None:
        self.academy_repository = academy_repository
        self.onboarding_service = onboarding_service
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
