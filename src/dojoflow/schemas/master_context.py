from uuid import UUID

from pydantic import BaseModel

from dojoflow.shared.enums import AcademyStatus


class MasterContextRead(BaseModel):
    master_id: int
    master_public_id: UUID
    master_name: str
    telegram_user_id: int | None
    email: str | None = None
    phone: str | None = None
    academy_id: int
    academy_public_id: UUID
    academy_name: str
    academy_status: AcademyStatus
    # Sessão de suporte: administrador vendo outra academia
    support_mode: bool = False


class AcademyApiRead(BaseModel):
    id: UUID
    name: str
    status: AcademyStatus


class MasterContextApiRead(BaseModel):
    id: UUID
    name: str
    email: str | None
    phone: str | None
    telegram_linked: bool
    academy: AcademyApiRead
    support_mode: bool

    @classmethod
    def from_context(
        cls, context: MasterContextRead
    ) -> 'MasterContextApiRead':
        return cls(
            id=context.master_public_id,
            name=context.master_name,
            email=context.email,
            phone=context.phone,
            telegram_linked=context.telegram_user_id is not None,
            support_mode=context.support_mode,
            academy=AcademyApiRead(
                id=context.academy_public_id,
                name=context.academy_name,
                status=context.academy_status,
            ),
        )
