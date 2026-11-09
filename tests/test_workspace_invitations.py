"""Invitation foundations do not provision accounts or expose public endpoints."""

from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.base import Base
from app.models.access_request import AccessRequest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent
from app.schemas.access_request import AccessRequestCreate
from app.services.access_requests import build_access_request, purge_expired_requests
from app.services.workspace_invitations import (
    InvitationUnavailable, accept_existing_account, accept_new_account,
    digest_invitation_token, invitation_status, issue_invitation, revoke_invitation,
)
from app.services.auth import verify_password


@pytest.fixture
def setup(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'invitations.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(email="owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Private", created_by_user_id=owner.id)
        db.add(workspace)
        db.flush()
        db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=owner.id, role="owner"))
        request = build_access_request(AccessRequestCreate(first_name="New", last_name="Person", email="new@example.com", referral_source="github"))
        request.status = "approved"
        db.add(request)
        db.commit()
        monkeypatch.setattr(settings, "access_request_reviewer_ids", [owner.id])
        yield db, dict(actor_id=owner.id, request_id=request.id)
    engine.dispose()


def test_digest_only_expiry_and_no_provisioning(setup):
    db, args = setup
    issued = issue_invitation(db, **args)
    db.commit()
    invite = db.get(WorkspaceInvitation, issued.invitation_id)
    assert issued.token not in repr(issued)
    assert len(issued.token) >= 64
    assert invite.token_hash == digest_invitation_token(issued.token)
    assert invite.expires_at - invite.created_at == timedelta(hours=72)
    assert invite.role == "owner"
    assert invite.workspace_id is None
    assert db.scalar(select(func.count(User.id))) == 1
    assert db.scalar(select(func.count(WorkspaceMembership.id))) == 1
    assert invitation_status(invite, now=invite.expires_at) == "expired"
    assert invitation_status(invite, now=invite.expires_at-timedelta(seconds=1)) == "pending"


@pytest.mark.parametrize("reason", ["reviewer", "role", "request", "expired"])
def test_issuance_authority(setup, monkeypatch, reason):
    db, args = setup
    if reason == "reviewer":
        monkeypatch.setattr(settings, "access_request_reviewer_ids", [])
    elif reason == "role":
        db.scalar(select(WorkspaceMembership)).role = "member"
    elif reason == "request":
        db.get(AccessRequest, args["request_id"]).status = "reviewed"
    elif reason == "expired":
        db.get(AccessRequest, args["request_id"]).expires_at = utc_now()-timedelta(seconds=1)
    db.commit()
    with pytest.raises(InvitationUnavailable):
        issue_invitation(db, **args)
    db.rollback()
    assert db.scalar(select(func.count(WorkspaceInvitation.id))) == 0


def test_expiry_capped_by_intake_retention_and_cleanup(setup):
    db, args = setup
    request = db.get(AccessRequest, args["request_id"])
    request.expires_at = utc_now()+timedelta(hours=1)
    db.commit()
    issued = issue_invitation(db, **args)
    db.commit()
    assert db.get(WorkspaceInvitation, issued.invitation_id).expires_at == request.expires_at
    assert purge_expired_requests(db, now=request.expires_at) == 1
    db.commit()
    assert db.scalar(select(func.count(WorkspaceInvitation.id))) == 0
    assert db.scalar(select(func.count(WorkspaceInvitationEvent.id))) == 0
    assert db.scalar(select(func.count(User.id))) == 1


def test_reissue_requires_fresh_confirmation_and_invalidates_old_digest(setup):
    db, args = setup
    first = issue_invitation(db, **args)
    db.commit()
    with pytest.raises(InvitationUnavailable):
        issue_invitation(db, **args)
    db.rollback()
    second = issue_invitation(db, **args, expected_generation=first.generation)
    db.commit()
    assert first.token != second.token
    assert second.generation == 2
    assert db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == digest_invitation_token(first.token))) is None
    with pytest.raises(InvitationUnavailable):
        issue_invitation(db, **args, expected_generation=first.generation)
    db.rollback()
    assert db.scalar(select(func.count(WorkspaceInvitation.id))) == 1
    assert list(db.scalars(select(WorkspaceInvitationEvent.event).order_by(WorkspaceInvitationEvent.id))) == ["issued", "reissued"]


def test_revoke_checks_authority_generation_and_erases_digest(setup, monkeypatch):
    db, args = setup
    first = issue_invitation(db, **args)
    db.commit()
    revoke_args = dict(actor_id=args["actor_id"], invitation_id=first.invitation_id, expected_generation=1)
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [])
    with pytest.raises(InvitationUnavailable):
        revoke_invitation(db, **revoke_args)
    db.rollback()
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [args["actor_id"]])
    revoke_invitation(db, **revoke_args)
    db.commit()
    invitation = db.get(WorkspaceInvitation, first.invitation_id)
    assert invitation.token_hash is None
    assert invitation_status(invitation) == "revoked"
    third = issue_invitation(db, **args, expected_generation=1)
    db.commit()
    with pytest.raises(InvitationUnavailable):
        revoke_invitation(db, **revoke_args)
    db.rollback()
    assert db.get(WorkspaceInvitation, third.invitation_id).status == "pending"


def test_rollback_restores_previous_invitation_and_history(setup):
    db, args = setup
    first = issue_invitation(db, **args)
    db.commit()
    issue_invitation(db, **args, expected_generation=1)
    db.rollback()
    invite = db.get(WorkspaceInvitation, first.invitation_id)
    assert invite.generation == 1
    assert invite.token_hash == digest_invitation_token(first.token)
    assert db.scalar(select(func.count(WorkspaceInvitationEvent.id))) == 1


def test_accepted_cannot_be_reissued_or_revoked(setup):
    db, args = setup
    first = issue_invitation(db, **args)
    db.get(WorkspaceInvitation, first.invitation_id).status = "accepted"
    db.commit()
    with pytest.raises(InvitationUnavailable):
        issue_invitation(db, **args, expected_generation=1)
    db.rollback()
    with pytest.raises(InvitationUnavailable):
        revoke_invitation(db, actor_id=args["actor_id"], invitation_id=first.invitation_id, expected_generation=1)
    db.rollback()


@pytest.mark.parametrize("reissue", [False, True])
def test_two_connections_cannot_issue_duplicate_or_replace_fresh_generation(setup, reissue):
    db, args = setup
    if reissue:
        issue_invitation(db, **args)
        db.commit()
        args = {**args, "expected_generation": 1}
    barrier = Barrier(2)
    def attempt():
        with Session(db.get_bind()) as connection:
            barrier.wait(timeout=5)
            try:
                result = issue_invitation(connection, **args)
                connection.commit()
                return result.generation
            except InvitationUnavailable:
                connection.rollback()
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(value is not None for value in results) == 1
    assert db.scalar(select(func.count(WorkspaceInvitation.id))) == 1
    assert db.scalar(select(WorkspaceInvitation.generation)) == (2 if reissue else 1)


def test_new_account_activation_is_atomic_and_single_use(setup):
    db, args = setup
    issued = issue_invitation(db, **args)
    db.commit()
    user = accept_new_account(db, token=issued.token, password="correct horse battery staple",
                              password_confirmation="correct horse battery staple")
    db.commit()
    invitation = db.get(WorkspaceInvitation, issued.invitation_id)
    assert invitation.status == "accepted"
    assert invitation.token_hash is None
    assert user.email == "new@example.com"
    assert verify_password("correct horse battery staple", user.password_hash)
    membership = db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id))
    workspace = db.get(Workspace, membership.workspace_id)
    assert workspace.name == "New's Workspace"
    assert workspace.created_by_user_id == user.id
    assert membership.role == "owner"
    assert invitation.workspace_id == workspace.id
    with pytest.raises(InvitationUnavailable):
        accept_new_account(db, token=issued.token, password="correct horse battery staple",
                           password_confirmation="correct horse battery staple")
    db.rollback()


def test_new_account_existing_identity_and_failed_confirmation_change_nothing(setup):
    db, args = setup
    existing = User(email="new@example.com", display_name="Existing", password_hash="unchanged")
    db.add(existing)
    issued = issue_invitation(db, **args)
    db.commit()
    with pytest.raises(InvitationUnavailable):
        accept_new_account(db, token=issued.token, password="one long password", password_confirmation="different long password")
    db.rollback()
    with pytest.raises(InvitationUnavailable):
        accept_new_account(db, token=issued.token, password="one long password", password_confirmation="one long password")
    db.rollback()
    assert db.get(User, existing.id).password_hash == "unchanged"
    assert db.get(WorkspaceInvitation, issued.invitation_id).status == "pending"


def test_existing_account_must_match_and_password_is_unchanged(setup):
    db, args = setup
    existing = User(email="new@example.com", display_name="Existing", password_hash="unchanged")
    wrong = User(email="wrong@example.com", display_name="Wrong", password_hash="wrong-hash")
    db.add_all([existing, wrong])
    db.flush()
    # Existing users need an existing workspace in order to authenticate normally.
    other = Workspace(name="Other", created_by_user_id=existing.id)
    db.add(other); db.flush()
    db.add_all([
        WorkspaceMembership(workspace_id=other.id, user_id=existing.id, role="owner"),
        WorkspaceMembership(workspace_id=other.id, user_id=wrong.id, role="member"),
    ])
    issued = issue_invitation(db, **args)
    db.commit()
    with pytest.raises(InvitationUnavailable):
        accept_existing_account(db, token=issued.token, user=wrong)
    db.rollback()
    accepted_user = accept_existing_account(db, token=issued.token, user=existing)
    db.commit()
    assert accepted_user.id == existing.id
    assert existing.password_hash == "unchanged"
    assert db.scalar(select(func.count(WorkspaceMembership.id)).where(
        WorkspaceMembership.user_id == existing.id
    )) == 1
    assert db.get(WorkspaceInvitation, issued.invitation_id).workspace_id is None
