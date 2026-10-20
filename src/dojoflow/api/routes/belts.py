from fastapi import APIRouter, status
from sqlalchemy import select

from dojoflow.api.dependencies.auth import CurrentMasterDep
from dojoflow.api.dependencies.belt import BeltServiceDep
from dojoflow.api.dependencies.db_session import DbSessionDep
from dojoflow.api.dependencies.enrollment_belt import EnrollmentBeltServiceDep
from dojoflow.api.dependencies.public_ids import (
    BeltIdDep,
    EnabledModalityIdDep,
    resolve_academy_enrollment_id,
    resolve_belt_id,
)
from dojoflow.models.belt import Belt
from dojoflow.schemas.belt import BeltPayload
from dojoflow.schemas.belt_api import BeltApiRead, BeltOrderRequest
from dojoflow.schemas.enrollment_belt import EnrollmentBeltPayload
from dojoflow.schemas.enrollment_belt_api import (
    BulkBeltRequest,
    BulkBeltResultApiRead,
    PendingBeltEnrollmentApiRead,
)
from dojoflow.shared.exceptions import ConflictError

router = APIRouter(prefix='/academy', tags=['Belts'])


@router.get(
    path='/modalities/{modality_id}/belts',
    status_code=status.HTTP_200_OK,
)
async def list_belts(
    modality_id: EnabledModalityIdDep,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
) -> list[BeltApiRead]:
    belts = await belt_service_dep.list_by_modality(
        current_master.academy_id, modality_id
    )

    return [BeltApiRead.from_internal(belt) for belt in belts]


@router.post(
    path='/modalities/{modality_id}/belts',
    status_code=status.HTTP_201_CREATED,
)
async def create_belt(
    modality_id: EnabledModalityIdDep,
    data: BeltPayload,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
) -> BeltApiRead:
    belt = await belt_service_dep.create(
        current_master.academy_id, modality_id, data
    )

    return BeltApiRead.from_internal(belt)


@router.post(
    path='/modalities/{modality_id}/belts/taekwondo-preset',
    status_code=status.HTTP_201_CREATED,
)
async def apply_taekwondo_preset(
    modality_id: EnabledModalityIdDep,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
) -> list[BeltApiRead]:
    belts = await belt_service_dep.apply_taekwondo_preset(
        current_master.academy_id, modality_id
    )

    return [BeltApiRead.from_internal(belt) for belt in belts]


@router.get(
    path='/modalities/{modality_id}/belts/pending-enrollments',
    status_code=status.HTTP_200_OK,
)
async def list_enrollments_without_belt(
    modality_id: EnabledModalityIdDep,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
) -> list[PendingBeltEnrollmentApiRead]:
    pending = await enrollment_belt_service_dep.list_pending(
        current_master.academy_id, modality_id
    )

    return [PendingBeltEnrollmentApiRead.from_internal(p) for p in pending]


@router.post(
    path='/modalities/{modality_id}/belts/bulk',
    status_code=status.HTTP_200_OK,
)
async def register_belts_in_bulk(
    modality_id: EnabledModalityIdDep,
    data: BulkBeltRequest,
    current_master: CurrentMasterDep,
    enrollment_belt_service_dep: EnrollmentBeltServiceDep,
    db_session_dep: DbSessionDep,
) -> BulkBeltResultApiRead:
    academy_id = current_master.academy_id
    items = [
        (
            await resolve_academy_enrollment_id(
                db_session_dep, item.enrollment_id, academy_id
            ),
            EnrollmentBeltPayload(
                belt_id=await resolve_belt_id(
                    db_session_dep, item.belt_id, academy_id
                ),
                graduated_on=item.graduated_on,
            ),
        )
        for item in data.items
    ]

    saved = await enrollment_belt_service_dep.bulk_add(
        academy_id, modality_id, items
    )

    return BulkBeltResultApiRead(saved=saved)


@router.put(
    path='/modalities/{modality_id}/belts/order',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reorder_belts(
    modality_id: EnabledModalityIdDep,
    data: BeltOrderRequest,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
    db_session_dep: DbSessionDep,
) -> None:
    rows = await db_session_dep.execute(
        select(Belt.public_id, Belt.id).where(
            Belt.academy_id == current_master.academy_id,
            Belt.modality_id == modality_id,
            Belt.public_id.in_(data.belt_ids),
        )
    )
    ids_by_public_id = dict(rows.tuples().all())

    if any(public_id not in ids_by_public_id for public_id in data.belt_ids):
        raise ConflictError(
            'The new order must list every belt of this modality once.',
            code='BELT_ORDER_MISMATCH',
        )

    await belt_service_dep.reorder(
        current_master.academy_id,
        modality_id,
        [ids_by_public_id[public_id] for public_id in data.belt_ids],
    )


@router.put(
    path='/belts/{belt_id}',
    status_code=status.HTTP_200_OK,
)
async def update_belt(
    belt_id: BeltIdDep,
    data: BeltPayload,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
) -> BeltApiRead:
    belt = await belt_service_dep.update(
        current_master.academy_id, belt_id, data
    )

    return BeltApiRead.from_internal(belt)


@router.delete(
    path='/belts/{belt_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_belt(
    belt_id: BeltIdDep,
    current_master: CurrentMasterDep,
    belt_service_dep: BeltServiceDep,
) -> None:
    await belt_service_dep.delete(current_master.academy_id, belt_id)
