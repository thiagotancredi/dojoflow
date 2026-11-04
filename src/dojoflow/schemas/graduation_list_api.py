from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from dojoflow.schemas.belt_api import BeltApiRead
from dojoflow.schemas.billing import ChargeStatus
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
    payment_due_date: date | None = None


class GraduationEntryApiCreate(BaseModel):
    enrollment_id: UUID
    target_belt_id: UUID | None = None


class GraduationEntryApiUpdate(BaseModel):
    target_belt_id: UUID


class ModalityRefApiRead(BaseModel):
    id: UUID
    name: str
    emoji: str


class GraduationListSummaryApiRead(BaseModel):
    id: UUID
    name: str
    modality: ModalityRefApiRead
    exam_date: date
    payment_due_date: date | None
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
            payment_due_date=summary.payment_due_date,
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


class GraduationChargeApiRead(BaseModel):
    """Cobrança da graduação de um aluno da lista."""

    id: UUID
    amount: Decimal
    paid: Decimal
    open_amount: Decimal
    status: ChargeStatus
    due_date: date
    paid_at: date | None
    days_late: int


class GraduationEntryApiRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    student_id: UUID
    student_name: str
    snapshot_belt: BeltApiRead | None
    snapshot_graduated_on: date | None
    eligibility: Eligibility
    target_belt: BeltApiRead
    charge: GraduationChargeApiRead | None
    whatsapp_url: str | None
    # Quem recebe a cobrança, quando é um responsável
    responsible_name: str | None

    @classmethod
    def from_internal(cls, entry: GraduationEntry) -> 'GraduationEntryApiRead':
        snapshot = entry.snapshot_belt
        billing = entry.billing
        charge = billing.charge if billing else None

        return cls(
            id=entry.public_id,
            enrollment_id=entry.enrollment_public_id,
            student_id=entry.student_public_id,
            student_name=entry.student_name,
            charge=GraduationChargeApiRead(
                id=charge.public_id,
                amount=charge.amount,
                paid=charge.paid,
                open_amount=charge.open_amount,
                status=charge.status,
                due_date=charge.due_date,
                paid_at=charge.paid_at,
                days_late=billing.days_late,
            )
            if billing and charge
            else None,
            whatsapp_url=billing.whatsapp_url if billing else None,
            responsible_name=billing.responsible_name if billing else None,
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
