from pydantic import BaseModel

from dojoflow.shared.enums import AcademyStatus


class MasterContextRead(BaseModel):
    master_id: int
    master_name: str
    telegram_user_id: int
    academy_id: int
    academy_name: str
    academy_status: AcademyStatus
