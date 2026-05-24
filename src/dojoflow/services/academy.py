from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.database.transaction import transactional
from dojoflow.repositories.academy import AcademyRepository
from dojoflow.schemas.academy import AcademyCreate


class AcademyService:
    def __init__(
        self,
        academy_repository: AcademyRepository,
        db_session: AsyncSession,
    ) -> None:
        self.academy_repository = academy_repository
        self.db_session = db_session

    @transactional
    async def create(self, data: AcademyCreate) -> int:
        return await self.academy_repository.create(data)
