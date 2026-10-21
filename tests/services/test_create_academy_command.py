import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dojoflow.commands.create_academy import create_academy
from dojoflow.models.master import Master
from dojoflow.schemas.admin_api import AdminAcademyCreate
from dojoflow.services.security import verify_password


@pytest.mark.asyncio
async def test_create_academy_command_creates_master_with_password(
    db_session: AsyncSession,
) -> None:
    result = await create_academy(
        db_session,
        AdminAcademyCreate(
            academy_name='Katsuflow',
            master_name='Thiago',
            email='Admin@Katsuflow.TEST',
        ),
    )

    assert result.academy.name == 'Katsuflow'
    master = await db_session.scalar(
        select(Master).where(Master.email == 'admin@katsuflow.test')
    )
    assert master is not None
    assert verify_password(result.password, master.password_hash or '')
