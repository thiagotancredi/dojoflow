from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.belt_api import BeltApiRead
from dojoflow.schemas.enrollment_belt_api import BeltRecordApiRead
from dojoflow.schemas.graduation_list import (
    GraduationCandidate,
    GraduationEntry,
    GraduationListDetail,
    GraduationListSummary,
    ListName,
)
from dojoflow.shared.enums import Eligibility


class GraduationListApiCreate(BaseModel):
    name: ListName
    modality_id: UUID
    exam_date: date


class ModalityRefApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str


class GraduationListSummaryApiRead(BaseModel):
    id: UUID
    name: str
    modality: ModalityRefApiRead
    exam_date: date
    created_at: datetime
    entry_count: int

    @classmethod
    def from_internal(
        cls, summary: GraduationListSummary
    ) -> 'GraduationListSummaryApiRead':
        return cls(
            id=summary.public_id,
            name=summary.name,
            modality=ModalityRefApiRead(
                id=summary.modality_public_id,
                name=summary.modality_name,
                emoji=summary.modality_emoji,
            ),
            exam_date=summary.exam_date,
            created_at=summary.created_at,
            entry_count=summary.entry_count,
        )


class GraduationCandidateApiRead(BaseModel):
    enrollment_id: UUID
    student_name: str
    current: BeltRecordApiRead | None
    eligibility: Eligibility
    suggested_target: BeltApiRead | None

    @classmethod
    def from_internal(
        cls, candidate: GraduationCandidate
    ) -> 'GraduationCandidateApiRead':
        current = candidate.current
        target = candidate.suggested_target

        return cls(
            enrollment_id=candidate.enrollment_public_id,
            student_name=candidate.student_name,
            current=BeltRecordApiRead.from_internal(current)
            if current
            else None,
            eligibility=candidate.eligibility,
            suggested_target=BeltApiRead.from_internal(target)
            if target
            else None,
        )


class GraduationEntryApiRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    student_name: str
    snapshot_belt: BeltApiRead | None
    snapshot_graduated_on: date | None
    eligibility: Eligibility
    target_belt: BeltApiRead

    @classmethod
    def from_internal(cls, entry: GraduationEntry) -> 'GraduationEntryApiRead':
        snapshot = entry.snapshot_belt

        return cls(
            id=entry.public_id,
            enrollment_id=entry.enrollment_public_id,
            student_name=entry.student_name,
            snapshot_belt=BeltApiRead.from_internal(snapshot)
            if snapshot
            else None,
            snapshot_graduated_on=entry.snapshot_graduated_on,
            eligibility=entry.eligibility,
            target_belt=BeltApiRead.from_internal(entry.target_belt),
        )


class GraduationListDetailApiRead(BaseModel):
    summary: GraduationListSummaryApiRead
    belts: list[BeltApiRead]
    entries: list[GraduationEntryApiRead]
    candidates: list[GraduationCandidateApiRead]

    @classmethod
    def from_internal(
        cls, detail: GraduationListDetail
    ) -> 'GraduationListDetailApiRead':
        return cls(
            summary=GraduationListSummaryApiRead.from_internal(detail.summary),
            belts=[BeltApiRead.from_internal(belt) for belt in detail.belts],
            entries=[
                GraduationEntryApiRead.from_internal(entry)
                for entry in detail.entries
            ],
            candidates=[
                GraduationCandidateApiRead.from_internal(candidate)
                for candidate in detail.candidates
            ],
        )
