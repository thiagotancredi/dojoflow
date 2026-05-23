import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PythonEnum
from typing import Any, TypeVar

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import MappedColumn, mapped_column

TEnum = TypeVar('TEnum', bound=PythonEnum)


def int_pk() -> MappedColumn[int]:
    return mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )


def uuid_public_id() -> MappedColumn[uuid.UUID]:
    return mapped_column(
        Uuid,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )


def int_fk(
    reference: str,
    nullable: bool = False,
) -> MappedColumn[int]:
    return mapped_column(
        ForeignKey(reference),
        nullable=nullable,
        index=True,
    )


def str_column(
    length: int = 120,
    nullable: bool = False,
) -> MappedColumn[str]:
    return mapped_column(
        String(length),
        nullable=nullable,
    )


def bool_column(
    default: bool = False,
    nullable: bool = False,
) -> MappedColumn[bool]:
    return mapped_column(
        Boolean,
        default=default,
        nullable=nullable,
    )


def money_column(
    nullable: bool = False,
) -> MappedColumn[Decimal]:
    return mapped_column(
        Numeric(10, 2),
        nullable=nullable,
    )


def int_column(
    nullable: bool = False,
    default: int | None = None,
) -> MappedColumn[int]:
    return mapped_column(
        Integer,
        nullable=nullable,
        default=default,
    )


def big_int_column(
    unique: bool = False,
    nullable: bool = False,
    index: bool = False,
) -> MappedColumn[int]:
    return mapped_column(
        BigInteger,
        unique=unique,
        nullable=nullable,
        index=index,
    )


def created_at_column() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


def updated_at_column() -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def date_column(
    nullable: bool = False,
) -> MappedColumn[date]:
    return mapped_column(
        Date,
        nullable=nullable,
    )


def datetime_column(
    nullable: bool = False,
) -> MappedColumn[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=nullable,
    )


def enum_column(
    enum_class: type[TEnum],
    default: TEnum | None = None,
    nullable: bool = False,
) -> MappedColumn[TEnum]:
    return mapped_column(
        SQLEnum(
            enum_class,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
            native_enum=False,
        ),
        default=default,
        nullable=nullable,
    )


def json_column(
    nullable: bool = False,
) -> MappedColumn[dict[str, Any]]:
    return mapped_column(
        JSON,
        default=dict,
        nullable=nullable,
    )
