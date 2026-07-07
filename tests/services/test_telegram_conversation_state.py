from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from dojoflow.services.telegram_conversation_state import (
    TelegramConversationStateService,
)
from dojoflow.shared.telegram_enums import TelegramStep


@pytest.mark.asyncio
async def test_update_student_edit_context_serializes_context_data() -> None:
    repository = AsyncMock()
    db_session = AsyncMock()
    service = TelegramConversationStateService(
        telegram_conversation_state_repository=repository,
        db_session=db_session,
    )
    public_id = uuid4()
    updated_at = datetime(2026, 7, 7, 10, 30, 0)

    await service.update_student_edit_context(
        state_id=12,
        next_step=TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU,
        context_data={
            'student_id': public_id,
            'birth_date': date(2026, 7, 7),
            'updated_at': updated_at,
            'monthly_fee': Decimal('180.00'),
            'address': {
                'reference_id': public_id,
            },
            'responsibles': [
                {
                    'document_id': public_id,
                },
            ],
        },
    )

    repository.update_by_id.assert_awaited_once_with(
        record_id=12,
        data={
            'current_flow': 'student_edit',
            'current_step': TelegramStep.WAITING_STUDENT_EDIT_ADDRESS_MENU,
            'context_data': {
                'student_id': str(public_id),
                'birth_date': '2026-07-07',
                'updated_at': '2026-07-07T10:30:00',
                'monthly_fee': '180.00',
                'address': {
                    'reference_id': str(public_id),
                },
                'responsibles': [
                    {
                        'document_id': str(public_id),
                    },
                ],
            },
        },
    )
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()


def test_serialize_context_data_handles_recursive_values() -> None:
    public_id = uuid4()
    payload = {
        'student_id': public_id,
        'dates': [date(2026, 7, 7), datetime(2026, 7, 7, 10, 30, 0)],
        'amounts': (Decimal('150.00'),),
    }

    serialized = TelegramConversationStateService._serialize_context_data(
        payload
    )

    assert serialized == {
        'student_id': str(public_id),
        'dates': ['2026-07-07', '2026-07-07T10:30:00'],
        'amounts': ['150.00'],
    }
