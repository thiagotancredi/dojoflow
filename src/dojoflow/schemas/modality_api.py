from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.modality import ModalityOptionRead, ModalityRead


class ModalityApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str

    @classmethod
    def from_internal(cls, modality: ModalityRead) -> 'ModalityApiRead':
        return cls(
            id=modality.public_id,
            name=modality.name,
            emoji=modality.emoji,
        )


class ModalityOptionApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str
    is_selected: bool
    has_belts: bool

    @classmethod
    def from_internal(
        cls,
        option: ModalityOptionRead,
    ) -> 'ModalityOptionApiRead':
        return cls(
            id=option.public_id,
            name=option.name,
            emoji=option.emoji,
            is_selected=option.is_selected,
            has_belts=option.has_belts,
        )


class ModalityToggleRead(BaseModel):
    is_selected: bool
