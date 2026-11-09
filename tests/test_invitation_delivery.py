"""Verify delivery configuration without contacting Azure or exposing tokens."""

import pytest

from app.core.config import settings
from app.services.invitation_delivery import (
    InvitationDeliveryUnavailable, activation_url, deliver_invitation,
    invitation_message,
)


def test_development_manual_delivery_returns_fragment_link(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "invitation_delivery_provider", "manual")
    monkeypatch.setattr(settings, "public_app_url", "http://localhost:5173")
    result, link = deliver_invitation(
        recipient_email="invitee@example.com", recipient_name="Test Invitee", token="secret / token"
    )
    assert result.provider == "manual"
    assert link == "http://localhost:5173/#/accept-invitation?token=secret%20%2F%20token"


def test_non_development_requires_https_and_azure(monkeypatch):
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "public_app_url", "http://example.com")
    monkeypatch.setattr(settings, "invitation_delivery_provider", "azure")
    with pytest.raises(InvitationDeliveryUnavailable):
        activation_url("never-return-this")
    monkeypatch.setattr(settings, "public_app_url", "https://example.com")
    monkeypatch.setattr(settings, "invitation_delivery_provider", "manual")
    with pytest.raises(InvitationDeliveryUnavailable):
        deliver_invitation(recipient_email="x@example.com", recipient_name="X", token="secret")


def test_azure_configuration_fails_closed_before_sdk_use(monkeypatch):
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "public_app_url", "https://example.com")
    monkeypatch.setattr(settings, "invitation_delivery_provider", "azure")
    monkeypatch.setattr(settings, "azure_communication_email_endpoint", None)
    monkeypatch.setattr(settings, "azure_communication_email_sender", None)
    with pytest.raises(InvitationDeliveryUnavailable):
        deliver_invitation(recipient_email="x@example.com", recipient_name="X", token="secret")


def test_invitation_message_is_branded_accessible_and_email_safe():
    message = invitation_message(
        recipient_name='Jay <script>alert("no")</script>',
        link="https://telaryn.app/#/accept-invitation?token=secret%20token&next=1",
    )

    assert message["subject"] == "Your Telaryn workspace is ready"
    assert "Create your private workspace" in message["plainText"]
    assert "expires in 72 hours" in message["plainText"]
    assert "can only be used once" in message["plainText"]
    assert "support@telaryn.app" in message["plainText"]
    assert "Every action has a purpose." in message["plainText"]
    assert "https://telaryn.app/#/getting-started" in message["plainText"]
    assert "Open https://telaryn.app in Safari" in message["plainText"]
    assert "Choose Add to Home Screen" in message["plainText"]
    assert "Open https://telaryn.app in Chrome" in message["plainText"]
    assert "Choose Install app or Add to Home screen" in message["plainText"]
    assert "Native iPhone and Android apps are planned" in message["plainText"]

    html = message["html"]
    assert "Your workspace is ready." in html
    assert ">Create your workspace</a>" in html
    assert "mailto:support@telaryn.app" in html
    assert "role=\"presentation\"" in html
    assert "<script>" not in html
    assert "Jay &lt;script&gt;" in html
    assert "token=secret%20token&amp;next=1" in html
    assert 'href="https://telaryn.app/#/getting-started"' in html
    assert "Add Telaryn to your Home Screen" in html
    assert "iPhone · Safari" in html
    assert "Android · Chrome" in html
    assert "<strong>Add to Home Screen</strong>" in html
    assert "<strong>Install app</strong>" in html
    assert 'href="https://telaryn.app"' in html
    assert "<img" not in html
