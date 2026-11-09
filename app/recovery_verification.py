"""Verify a restored database without printing user-authored data or credentials."""

from __future__ import annotations

import json
import traceback


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    """Migrate and prove the restored database while emitting bounded diagnostics."""
    stage = "module_import"
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import func, select

        from app.db.session import SessionLocal, engine
        from app.models.acceptance_criterion import AcceptanceCriterion
        from app.models.project import Project
        from app.models.subtask import Subtask
        from app.models.ticket import Ticket
        from app.models.ticket_activity_event import TicketActivityEvent
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.postgres_verification import main as verify_authenticated_workflow

        stage = "database_engine"
        require(
            engine.dialect.name == "postgresql",
            "Recovery verification requires PostgreSQL.",
        )

        stage = "schema_migration"
        alembic_config = Config("alembic.ini")
        command.upgrade(alembic_config, "head")

        stage = "schema_revision"
        expected_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
        with engine.connect() as connection:
            restored_revision = MigrationContext.configure(connection).get_current_revision()
        require(
            restored_revision == expected_revision,
            "The restored schema does not match the reviewed Telaryn revision.",
        )

        stage = "representative_records"
        model_counts: dict[str, int] = {}
        required_restored_records = {"users", "workspaces"}
        with SessionLocal() as db:
            for label, model in (
                ("users", User),
                ("workspaces", Workspace),
                ("projects", Project),
                ("tickets", Ticket),
                ("acceptance_criteria", AcceptanceCriterion),
                ("subtasks", Subtask),
                ("ticket_activity_events", TicketActivityEvent),
            ):
                count = db.scalar(select(func.count()).select_from(model)) or 0
                if label in required_restored_records:
                    require(
                        count > 0,
                        f"The restored database has no required {label} records.",
                    )
                model_counts[label] = count

            password_count = db.scalar(
                select(func.count()).select_from(User).where(User.password_hash.is_not(None))
            ) or 0
            require(
                password_count > 0,
                "The restored database has no local authentication credential.",
            )

        print(
            json.dumps(
                {
                    "event": "restored_database_verified",
                    "schema_revision": restored_revision,
                    "representative_record_counts": model_counts,
                    "local_credentials_present": True,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        stage = "authenticated_workflow"
        verify_authenticated_workflow()
        print(
            json.dumps({"event": "restored_authentication_workflow_verified"}),
            flush=True,
        )
    except Exception as error:
        final_frame = traceback.extract_tb(error.__traceback__)[-1]
        safe_message = (
            str(error)[:500]
            if isinstance(error, RuntimeError)
            else "The verifier raised an unexpected error; inspect its exception type and stage."
        )
        print(
            "RECOVERY_DIAGNOSTIC="
            + json.dumps(
                {
                    "event": "recovery_verification_failed",
                    "stage": stage,
                    "exception_type": type(error).__name__,
                    "failure_location": (
                        f"{final_frame.name}:{final_frame.lineno}"
                    ),
                    "message": safe_message,
                    "contains_secrets": False,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
