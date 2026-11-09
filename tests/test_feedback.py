"""Exercise private feedback submission, image safety, and administrator review."""

from io import BytesIO
from datetime import timedelta

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register complete metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.feedback import FeedbackAdminEvent, FeedbackSubmission
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password
from app.core.time import utc_now
from app.services.feedback_retention import purge_closed_feedback


ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "correct horse battery staple"


def setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = User(email="admin@example.com", display_name="Telaryn Admin", password_hash=hash_password(PASSWORD))
    member = User(email="member@example.com", display_name="Member", password_hash=hash_password(PASSWORD))
    db.add_all([admin, member])
    db.flush()
    admin_workspace = Workspace(name="Administration", created_by_user_id=admin.id)
    member_workspace = Workspace(name="Member Workspace", created_by_user_id=member.id)
    db.add_all([admin_workspace, member_workspace])
    db.flush()
    db.add_all([
        WorkspaceMembership(workspace_id=admin_workspace.id, user_id=admin.id, role="owner"),
        WorkspaceMembership(workspace_id=member_workspace.id, user_id=member.id, role="owner"),
    ])
    db.commit()
    monkeypatch.setattr(settings, "deployment_administrator_ids", [admin.id])
    monkeypatch.setattr(settings, "feedback_reviewer_ids", [admin.id])
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [])

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    return engine, db, admin, member, TestClient(app), TestClient(app)


def teardown(engine, db):
    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()


def login(client, email):
    response = client.post("/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def image_bytes(*, image_format="PNG", exif=False):
    output = BytesIO()
    image = Image.new("RGB", (24, 18), "#3974b8")
    metadata = Image.Exif()
    if exif:
        metadata[0x010E] = "private screenshot note"
    image.save(output, format=image_format, exif=metadata)
    return output.getvalue()


def submit(client, screenshot=None):
    files = {"screenshot": ("screen.fake", screenshot, "application/octet-stream")} if screenshot else None
    return client.post(
        "/feedback/",
        headers={**ORIGIN, "User-Agent": "Telaryn Test Browser/1.0"},
        data={
            "category": "problem",
            "description": "The ticket drawer did not close after saving.",
            "route": "/tickets/42?secret=hidden#drawer",
            "viewport_width": "390",
            "viewport_height": "844",
        },
        files=files,
    )


def test_submission_is_private_and_records_bounded_context(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        response = submit(member_client)
        assert response.status_code == 201
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["reference"].startswith("FBK-")
        feedback = db.query(FeedbackSubmission).one()
        assert feedback.submitted_by_user_id == member.id
        assert feedback.workspace.name == "Member Workspace"
        assert feedback.route == "/tickets/42"
        assert feedback.browser_context == "Telaryn Test Browser/1.0"
        assert feedback.app_version == settings.app_version

        assert member_client.get("/feedback/admin").status_code == 403
        assert member_client.get(f"/feedback/admin/{feedback.public_id}").status_code == 403
        assert member_client.get(f"/feedback/admin/{feedback.public_id}/screenshot").status_code == 403
        assert member_client.get("/feedback/reviewer-access").json() == {"allowed": False}

        listed = admin_client.get("/feedback/admin?state=all")
        assert listed.status_code == 200
        access = admin_client.get("/feedback/reviewer-access")
        assert access.json() == {"allowed": True}
        assert access.headers["cache-control"] == "no-store"
        assert listed.json()["items"][0]["submitter"] == {
            "display_name": "Member", "email": "member@example.com", "workspace_name": "Member Workspace"
        }
    finally:
        teardown(engine, db)


def test_feedback_reviewer_authority_is_independent(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        reference = submit(member_client).json()["reference"]

        # Deployment administration alone discloses neither records nor their existence.
        monkeypatch.setattr(settings, "feedback_reviewer_ids", [])
        assert admin_client.get("/feedback/reviewer-access").json() == {"allowed": False}
        assert admin_client.get("/feedback/admin?state=all").status_code == 403
        assert admin_client.get(f"/feedback/admin/{reference}").status_code == 403
        assert admin_client.get(f"/feedback/admin/{reference}/screenshot").status_code == 403
        assert admin_client.patch(
            f"/feedback/admin/{reference}",
            headers=ORIGIN,
            json={"status": "reviewing", "admin_notes": "Must remain private."},
        ).status_code == 403

        # Feedback review alone grants the private queue, not either other role.
        monkeypatch.setattr(settings, "feedback_reviewer_ids", [member.id])
        monkeypatch.setattr(settings, "deployment_administrator_ids", [admin.id])
        assert member_client.get("/feedback/reviewer-access").json() == {"allowed": True}
        assert member_client.get("/feedback/admin?state=all").status_code == 200
        assert member_client.get("/user-management/access").json() == {"allowed": False}
        assert member_client.get("/user-management/users").status_code == 403
        assert member_client.get("/access-requests/reviewer-access").json()["allowed"] is False
    finally:
        teardown(engine, db)


def test_screenshot_is_decoded_reencoded_and_admin_only(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        response = submit(member_client, image_bytes(exif=True))
        assert response.status_code == 201
        feedback = db.query(FeedbackSubmission).one()
        assert feedback.screenshot_content_type == "image/png"
        assert feedback.screenshot_filename == "screen.png"
        with Image.open(BytesIO(feedback.screenshot_data)) as sanitized:
            assert sanitized.format == "PNG"
            assert not sanitized.getexif()

        screenshot = admin_client.get(f"/feedback/admin/{feedback.public_id}/screenshot")
        assert screenshot.status_code == 200
        assert screenshot.headers["content-type"] == "image/png"
        assert screenshot.headers["cache-control"] == "no-store"
        assert screenshot.headers["x-content-type-options"] == "nosniff"
        assert screenshot.content == feedback.screenshot_data
    finally:
        teardown(engine, db)


def test_malformed_and_oversized_screenshots_are_rejected(monkeypatch):
    engine, db, _admin, member, _admin_client, member_client = setup(monkeypatch)
    try:
        login(member_client, member.email)
        invalid = submit(member_client, b"<svg onload='alert(1)'></svg>")
        assert invalid.status_code == 422
        assert "PNG, JPEG, or WebP" in invalid.json()["detail"]
        oversized = submit(member_client, b"x" * (5 * 1024 * 1024 + 1))
        assert oversized.status_code == 413
        assert db.query(FeedbackSubmission).count() == 0
    finally:
        teardown(engine, db)


def test_administrator_review_preserves_original_and_records_history(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        reference = submit(member_client).json()["reference"]
        original = db.query(FeedbackSubmission).one()
        original_description = original.description
        reviewed = admin_client.patch(
            f"/feedback/admin/{reference}",
            headers=ORIGIN,
            json={"status": "reviewing", "admin_notes": "Reproduced on mobile."},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "reviewing"
        assert reviewed.json()["events"] == [{
            "actor_display_name": "Telaryn Admin",
            "actor_email": "admin@example.com",
            "previous_status": "new",
            "new_status": "reviewing",
            "notes_changed": True,
            "created_at": reviewed.json()["events"][0]["created_at"],
        }]
        db.refresh(original)
        assert original.description == original_description
        assert original.reviewed_by_user_id == admin.id
        assert original.closed_at is None
        assert db.query(FeedbackAdminEvent).count() == 1

        event = db.query(FeedbackAdminEvent).one()
        event.new_status = "closed"
        try:
            with db.begin_nested():
                db.flush()
        except ValueError as error:
            assert "append-only and immutable" in str(error)
        else:
            raise AssertionError("Feedback administrator events must be immutable.")
        db.rollback()

        guessed = admin_client.get("/feedback/admin/FBK-2222-2222-2222")
        assert guessed.status_code == 404
    finally:
        teardown(engine, db)


def test_closed_feedback_and_screenshots_follow_approved_retention(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        screenshot_reference = submit(member_client, image_bytes()).json()["reference"]
        expired_reference = submit(member_client, image_bytes()).json()["reference"]
        active_reference = submit(member_client, image_bytes()).json()["reference"]

        for reference in (screenshot_reference, expired_reference):
            response = admin_client.patch(
                f"/feedback/admin/{reference}",
                headers=ORIGIN,
                json={"status": "closed", "admin_notes": "Retention test."},
            )
            assert response.status_code == 200

        now = utc_now()
        screenshot_record = db.query(FeedbackSubmission).filter_by(
            public_id=screenshot_reference
        ).one()
        expired_record = db.query(FeedbackSubmission).filter_by(
            public_id=expired_reference
        ).one()
        expired_record_id = expired_record.id
        active_record = db.query(FeedbackSubmission).filter_by(
            public_id=active_reference
        ).one()
        screenshot_record.closed_at = now - timedelta(days=91)
        expired_record.closed_at = now - timedelta(days=366)
        db.commit()

        result = purge_closed_feedback(db, now=now)
        db.commit()

        assert result.screenshots_purged == 2
        assert result.feedback_records_purged == 1
        db.refresh(screenshot_record)
        assert screenshot_record.screenshot_data is None
        assert screenshot_record.screenshot_filename is None
        assert db.query(FeedbackSubmission).filter_by(public_id=expired_reference).one_or_none() is None
        db.refresh(active_record)
        assert active_record.screenshot_data is not None
        assert db.query(FeedbackAdminEvent).filter_by(feedback_id=expired_record_id).count() == 0

        reopened = admin_client.patch(
            f"/feedback/admin/{screenshot_reference}",
            headers=ORIGIN,
            json={"status": "reviewing", "admin_notes": "Reopened."},
        )
        assert reopened.status_code == 200
        db.refresh(screenshot_record)
        assert screenshot_record.closed_at is None
    finally:
        teardown(engine, db)
