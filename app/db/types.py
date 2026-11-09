"""Provide database types that preserve Telaryn's UTC timestamp contract."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.core.time import as_utc


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC instants compatibly and always return timezone-aware values.

    SQLite historically stored Telaryn timestamps as naive text. Binding UTC as
    naive values on SQLite preserves that representation, while result
    normalization interprets both legacy and new SQLite values as UTC.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name != "sqlite"))

    def process_bind_param(self, value: datetime | None, dialect: Dialect):
        normalized = as_utc(value)
        if normalized is not None and dialect.name == "sqlite":
            return normalized.replace(tzinfo=None)
        return normalized

    def process_result_value(self, value: datetime | None, _dialect: Dialect):
        return as_utc(value)

