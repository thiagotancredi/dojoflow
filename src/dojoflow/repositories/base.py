import types
from typing import Any, NoReturn, cast, get_args

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import delete, func, insert, inspect, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement

from dojoflow.database.base import Base
from dojoflow.database.transaction import transactional
from dojoflow.shared.exceptions import ConflictError, NotFoundError

type RecordId = int
type PkColumn = ColumnElement[RecordId]

type DataDict = dict[str, Any]
type DataInput = DataDict | PydanticBaseModel

type Field = InstrumentedAttribute[Any] | ColumnElement[Any]
type Fields = list[Field] | None

type Filter = ColumnElement[bool]
type Filters = list[Filter] | None

type OrderBy = Field
type OrderByList = list[OrderBy] | None

type Offset = int | None
type Limit = int | None


class BaseRepository[T: Base]:
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.model: type[T] = self._get_model()
        self.pk_column: PkColumn = self._get_pk_column()

    def _get_model(self) -> type[T]:
        original_classes = types.get_original_bases(self.__class__)

        for base in original_classes:
            args = get_args(base)

            if args:
                return args[0]

        raise TypeError(
            'You must declare the repository as BaseRepository[Model].'
        )

    def _get_pk_column(self) -> PkColumn:
        mapper = inspect(self.model)
        return cast(PkColumn, mapper.primary_key[0])

    @staticmethod
    def _get_data_dict(data: DataInput) -> DataDict:
        if isinstance(data, PydanticBaseModel):
            return data.model_dump()

        return data

    def _raise_not_found(self, record_id: RecordId) -> NoReturn:
        raise NotFoundError(
            f'Could not find {self.model.__name__} with id {record_id}.'
        )

    @transactional
    async def create(self, data: DataInput) -> RecordId:
        data_dict = self._get_data_dict(data)

        stmt = insert(self.model).values(**data_dict).returning(self.pk_column)
        stmt_result = await self.db_session.execute(stmt)

        return stmt_result.scalar_one()

    @transactional
    async def update_by_id(
        self,
        record_id: RecordId,
        data: DataInput,
    ) -> None:
        data_dict = self._get_data_dict(data)

        stmt = (
            update(self.model)
            .values(**data_dict)
            .where(self.pk_column == record_id)
            .returning(self.pk_column)
        )

        stmt_result = await self.db_session.execute(stmt)
        updated_id = stmt_result.scalar_one_or_none()

        if updated_id is None:
            self._raise_not_found(record_id)

    @transactional
    async def delete_by_id(self, record_id: RecordId) -> None:
        stmt = (
            delete(self.model)
            .where(self.pk_column == record_id)
            .returning(self.pk_column)
        )

        stmt_result = await self.db_session.execute(stmt)
        deleted_id = stmt_result.scalar_one_or_none()

        if deleted_id is None:
            self._raise_not_found(record_id)

    @transactional
    async def list(
        self,
        fields: Fields = None,
        filters: Filters = None,
        order_by: OrderByList = None,
        offset: Offset = None,
        limit: Limit = None,
    ) -> list[DataDict]:
        columns = fields if fields else list(self.model.__table__.columns)

        stmt = select(*columns).select_from(self.model)

        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        if order_by:
            stmt = stmt.order_by(*order_by)

        if offset is not None:
            stmt = stmt.offset(offset)

        if limit is not None:
            stmt = stmt.limit(limit)

        stmt_result = await self.db_session.execute(stmt)
        rows = stmt_result.mappings().all()

        return [dict(row) for row in rows]

    @transactional
    async def get_by_id(
        self,
        record_id: RecordId,
        fields: Fields = None,
    ) -> DataDict | None:
        records = await self.list(
            fields=fields,
            filters=[self.pk_column == record_id],
            order_by=None,
            offset=None,
            limit=1,
        )

        if not records:
            return None

        return records[0]

    @transactional
    async def get_by_id_or_fail(
        self,
        record_id: RecordId,
        fields: Fields = None,
    ) -> DataDict:
        record = await self.get_by_id(record_id=record_id, fields=fields)

        if record is None:
            self._raise_not_found(record_id)

        return record

    @transactional
    async def get_one(
        self,
        fields: Fields = None,
        filters: Filters = None,
    ) -> DataDict | None:
        records = await self.list(
            fields=fields,
            filters=filters,
            order_by=None,
            offset=None,
            limit=2,
        )

        if not records:
            return None

        if len(records) > 1:
            raise ConflictError(
                f'More than one {self.model.__name__} record was found.'
            )

        return records[0]

    @transactional
    async def get_one_or_fail(
        self,
        fields: Fields = None,
        filters: Filters = None,
    ) -> DataDict:
        record = await self.get_one(fields=fields, filters=filters)

        if record is None:
            raise NotFoundError(
                f'Could not find {self.model.__name__} with the given filters.'
            )

        return record

    @transactional
    async def exists(self, filters: Filters = None) -> bool:
        stmt = select(literal(1)).select_from(self.model).limit(1)

        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        stmt_result = await self.db_session.execute(stmt)

        return stmt_result.scalar_one_or_none() is not None

    @transactional
    async def count(self, filters: Filters = None) -> int:
        stmt = select(func.count()).select_from(self.model)

        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        stmt_result = await self.db_session.execute(stmt)

        return stmt_result.scalar_one()

    @transactional
    async def sum[V](
        self,
        field: InstrumentedAttribute[V] | ColumnElement[V],
        filters: Filters = None,
    ) -> V | None:
        stmt = select(func.sum(field)).select_from(self.model)

        if filters:
            for condition in filters:
                stmt = stmt.where(condition)

        stmt_result = await self.db_session.execute(stmt)

        return stmt_result.scalar_one_or_none()
