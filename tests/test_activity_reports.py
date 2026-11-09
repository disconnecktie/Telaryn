"""Protect Activity Report classification, authorization, and AI privacy boundaries."""

from datetime import date, datetime, timedelta, timezone

from app.models.project import Project
from app.models.ticket import Ticket
from app.schemas.activity_report import ActivityReportRequest, ActivityReportResult
from app.services.activity_reports import report_dates

from tests.test_workspace_authorization import (
    ORIGIN,
    build_authorization_client,
    close_authorization_client,
)


def test_annual_report_period_is_an_inclusive_rolling_year():
    assert report_dates("annual", None, date(2026, 9, 25)) == (
        date(2025, 9, 26),
        date(2026, 9, 25),
    )
    assert report_dates("annual", None, date(2024, 2, 29)) == (
        date(2023, 3, 1),
        date(2024, 2, 29),
    )
    assert ActivityReportRequest(
        period="annual", output_format="narrative"
    ).period == "annual"


def test_project_life_context_and_report_generation_are_workspace_scoped():
    engine, db, client, records = build_authorization_client()
    try:
        period_end = date.today()
        period_start = period_end - timedelta(days=6)
        project = records["jay_project"]
        updated = client.patch(
            f"/projects/{project.id}",
            headers=ORIGIN,
            json={"life_context": "work"},
        )
        assert updated.status_code == 200
        assert updated.json()["life_context"] == "work"
        history = client.get(f"/projects/{project.id}/lifecycle-events").json()
        assert history[0]["action"] == "life_context_changed"
        assert history[0]["previous_life_context"] == "unclassified"
        assert history[0]["new_life_context"] == "work"

        options = client.get("/activity-reports/projects")
        assert options.status_code == 200
        assert [item["id"] for item in options.json()] == [project.id]

        generated = client.post(
            "/activity-reports/generate",
            headers=ORIGIN,
            json={
                "period": "weekly",
                "output_format": "action_result_impact",
                "scope": "work",
                "project_ids": [project.id],
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            },
        )
        assert generated.status_code == 200
        payload = generated.json()
        assert payload["included_project_ids"] == [project.id]
        assert payload["output_format"] == "action_result_impact"
        assert payload["period_start"] == period_start.isoformat()
        assert payload["period_end"] == period_end.isoformat()
        assert payload["items"]
        assert "Jay" in payload["items"][0]
        assert "the user" not in payload["items"][0].lower()

        foreign = client.post(
            "/activity-reports/generate",
            headers=ORIGIN,
            json={
                "period": "weekly",
                "output_format": "narrative",
                "project_ids": [records["other_project"].id],
            },
        )
        assert foreign.status_code == 404
    finally:
        close_authorization_client(engine, db)


def test_non_completed_archives_are_excluded_by_default_but_remain_explicit_options():
    engine, db, client, records = build_authorization_client()
    try:
        workspace_id = records["jay_project"].workspace_id
        completed = Project(
            workspace_id=workspace_id,
            name="Completed Project",
            life_context="work",
            archived_at=datetime.now(timezone.utc),
            archive_reason="completed",
        )
        developmental = Project(
            workspace_id=workspace_id,
            name="Development Test",
            life_context="work",
            archived_at=datetime.now(timezone.utc),
            archive_reason="test_development",
        )
        other = Project(
            workspace_id=workspace_id,
            name="Other Archive",
            life_context="work",
            archived_at=datetime.now(timezone.utc),
            archive_reason="other",
            archive_reason_note="Administrative cleanup.",
        )
        db.add_all([completed, developmental, other])
        db.commit()

        options = {item["name"]: item for item in client.get("/activity-reports/projects").json()}
        assert options["Completed Project"]["included_by_default"] is True
        assert options["Development Test"]["included_by_default"] is False
        assert options["Development Test"]["archive_reason"] == "test_development"
        assert options["Other Archive"]["included_by_default"] is False
    finally:
        close_authorization_client(engine, db)


def test_activity_report_result_exposes_a_strict_openai_schema():
    schema = ActivityReportResult.model_json_schema()
    assert schema["additionalProperties"] is False


def test_private_projects_and_tickets_never_enter_report_context():
    engine, db, client, records = build_authorization_client()
    try:
        workspace_id = records["jay_project"].workspace_id
        private_project = Project(
            workspace_id=workspace_id,
            name="Private Project",
            life_context="work",
            ai_context_enabled=False,
        )
        visible_project = Project(
            workspace_id=workspace_id,
            name="Visible Project",
            life_context="work",
        )
        db.add_all([private_project, visible_project])
        db.flush()
        db.add(Ticket(
            workspace_id=workspace_id,
            project_id=visible_project.id,
            title="Private Ticket",
            ai_context_enabled=False,
        ))
        db.commit()

        option_ids = {item["id"] for item in client.get("/activity-reports/projects").json()}
        assert private_project.id not in option_ids
        assert visible_project.id in option_ids

        unavailable = client.post(
            "/activity-reports/generate",
            headers=ORIGIN,
            json={
                "period": "weekly",
                "output_format": "narrative",
                "project_ids": [private_project.id],
            },
        )
        assert unavailable.status_code == 404

        no_activity = client.post(
            "/activity-reports/generate",
            headers=ORIGIN,
            json={
                "period": "weekly",
                "output_format": "narrative",
                "project_ids": [visible_project.id],
            },
        )
        assert no_activity.status_code == 422
    finally:
        close_authorization_client(engine, db)


def test_project_life_context_rejects_invalid_or_null_values():
    engine, db, client, records = build_authorization_client()
    try:
        project_id = records["jay_project"].id
        for value in ("career", None):
            response = client.patch(
                f"/projects/{project_id}",
                headers=ORIGIN,
                json={"life_context": value},
            )
            assert response.status_code == 422
    finally:
        close_authorization_client(engine, db)
