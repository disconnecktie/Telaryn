"""Protect Telaryn's aware-UTC storage, serialization, and source conventions."""

from datetime import datetime, timezone
from pathlib import Path
import unittest

from fastapi.encoders import jsonable_encoder
from sqlalchemy import Column, DateTime, Integer, MetaData, Table, create_engine, insert, select

import app.models  # noqa: F401 - registers every ORM model with Base metadata
from app.core.time import as_utc, utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class UTCTimestampTests(unittest.TestCase):
    def test_canonical_clock_returns_aware_utc(self):
        value = utc_now()

        self.assertIs(value.tzinfo, timezone.utc)
        self.assertEqual(value.utcoffset().total_seconds(), 0)

    def test_naive_legacy_values_are_interpreted_as_utc(self):
        legacy = datetime(2026, 8, 30, 7, 15, 0)

        normalized = as_utc(legacy)

        self.assertEqual(normalized.isoformat(), "2026-08-30T07:15:00+00:00")

    def test_sqlite_legacy_rows_load_as_aware_utc_without_rewriting(self):
        engine = create_engine("sqlite://")
        metadata = MetaData()
        events = Table(
            "events",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("occurred_at", UTCDateTime(), nullable=False),
        )
        metadata.create_all(engine)

        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO events (id, occurred_at) VALUES (?, ?)",
                (1, "2026-08-30 07:15:00.000000"),
            )
            connection.execute(
                insert(events).values(
                    id=2,
                    occurred_at=datetime(
                        2026, 8, 30, 8, 15, 0, tzinfo=timezone.utc
                    ),
                )
            )
            rows = connection.execute(
                select(events.c.occurred_at).order_by(events.c.occurred_at)
            ).scalars().all()
            raw_legacy = connection.exec_driver_sql(
                "SELECT occurred_at FROM events WHERE id = 1"
            ).scalar_one()

        self.assertEqual(
            [value.isoformat() for value in rows],
            [
                "2026-08-30T07:15:00+00:00",
                "2026-08-30T08:15:00+00:00",
            ],
        )
        self.assertEqual(raw_legacy, "2026-08-30 07:15:00.000000")

    def test_json_serialization_communicates_utc_explicitly(self):
        encoded = jsonable_encoder(
            {"occurred_at": datetime(2026, 8, 30, 7, 15, tzinfo=timezone.utc)}
        )

        self.assertEqual(encoded["occurred_at"], "2026-08-30T07:15:00+00:00")

    def test_every_orm_datetime_column_uses_the_utc_boundary(self):
        timestamp_columns = []
        bypasses = []
        for table in Base.metadata.tables.values():
            for column in table.columns:
                label = f"{table.name}.{column.name}"
                if isinstance(column.type, UTCDateTime):
                    timestamp_columns.append(label)
                elif isinstance(column.type, DateTime):
                    bypasses.append(label)

        self.assertTrue(timestamp_columns)
        self.assertEqual(bypasses, [])

    def test_application_source_does_not_use_deprecated_utcnow(self):
        violations = []
        for path in Path("app").rglob("*.py"):
            if "datetime.utcnow" in path.read_text(encoding="utf-8"):
                violations.append(str(path))

        self.assertEqual(violations, [])

