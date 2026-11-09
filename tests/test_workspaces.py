"""Verify private workspace ownership is established before authentication is exposed."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.core.config import Settings, settings
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.workspaces import (
    get_or_create_bootstrap_workspace,
    get_workspace_project,
    get_workspace_ticket,
)


class WorkspaceFoundationTests(unittest.TestCase):
    """Exercise service-level boundaries without prematurely introducing login routes."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_bootstrap_workspace_creates_one_owner_membership(self) -> None:
        workspace = get_or_create_bootstrap_workspace(self.db)
        again = get_or_create_bootstrap_workspace(self.db)

        self.assertEqual(workspace.id, again.id)
        self.assertEqual(workspace.memberships[0].role, "owner")
        self.assertEqual(workspace.memberships[0].user.email, settings.bootstrap_user_email)

    def test_workspace_scoping_does_not_leak_projects_or_tickets(self) -> None:
        owner = User(email="owner@example.test", display_name="Owner")
        other_user = User(email="other@example.test", display_name="Other")
        self.db.add_all([owner, other_user])
        self.db.flush()
        owner_workspace = Workspace(name="Owner's Workspace", created_by_user_id=owner.id)
        other_workspace = Workspace(name="Other's Workspace", created_by_user_id=other_user.id)
        self.db.add_all([owner_workspace, other_workspace])
        self.db.flush()
        self.db.add_all(
            [
                WorkspaceMembership(workspace_id=owner_workspace.id, user_id=owner.id, role="owner"),
                WorkspaceMembership(workspace_id=other_workspace.id, user_id=other_user.id, role="owner"),
            ]
        )
        project = Project(name="Private project", workspace_id=owner_workspace.id)
        ticket = Ticket(title="Private ticket", workspace_id=owner_workspace.id, project=project)
        self.db.add_all([project, ticket])
        self.db.commit()

        self.assertIsNotNone(
            get_workspace_project(self.db, workspace_id=owner_workspace.id, project_id=project.id)
        )
        self.assertIsNone(
            get_workspace_project(self.db, workspace_id=other_workspace.id, project_id=project.id)
        )
        self.assertIsNotNone(
            get_workspace_ticket(self.db, workspace_id=owner_workspace.id, ticket_id=ticket.id)
        )
        self.assertIsNone(
            get_workspace_ticket(self.db, workspace_id=other_workspace.id, ticket_id=ticket.id)
        )

    def test_documented_bootstrap_environment_names_are_loaded(self) -> None:
        environment = {
            "ATLAS_BOOTSTRAP_USER_EMAIL": "jay@example.test",
            "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME": "Jay",
            "ATLAS_BOOTSTRAP_WORKSPACE_NAME": "Jay's Workspace",
            "ATLAS_SESSION_COOKIE_SECURE": "true",
            "ATLAS_SESSION_COOKIE_NAME": "atlas_staging_session",
        }
        with patch.dict(os.environ, environment, clear=False):
            configured = Settings(_env_file=None)

        self.assertEqual(configured.bootstrap_user_email, "jay@example.test")
        self.assertEqual(configured.bootstrap_user_display_name, "Jay")
        self.assertEqual(configured.bootstrap_workspace_name, "Jay's Workspace")
        self.assertTrue(configured.session_cookie_secure)
        self.assertEqual(configured.session_cookie_name, "atlas_staging_session")

    def test_bootstrap_mismatch_does_not_create_an_empty_workspace(self) -> None:
        existing = User(email="different-owner@example.test", display_name="Existing owner")
        self.db.add(existing)
        self.db.commit()

        with self.assertRaisesRegex(RuntimeError, "does not match"):
            get_or_create_bootstrap_workspace(self.db)

        self.assertEqual(self.db.query(User).count(), 1)
        self.assertEqual(self.db.query(Workspace).count(), 0)
