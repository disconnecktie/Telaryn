"""Portable release identity and AI failure-contract tests, without private infrastructure."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.ai.factory import AIProviderUnavailableError, get_ai_provider
from app.core.config import settings
from app.main import ai_provider_unavailable


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("provider", "api_key"),
    [("none", None), ("openai", None)],
)
def test_unavailable_ai_configuration_fails_closed(monkeypatch, provider, api_key):
    """Never start an AI request without a configured provider and credentials."""
    monkeypatch.setattr(settings, "ai_provider", provider)
    monkeypatch.setattr(settings, "openai_api_key", api_key)

    with pytest.raises(AIProviderUnavailableError) as error:
        get_ai_provider()

    assert str(error.value) == "Telaryn AI is not configured for this deployment."


def test_ai_unavailable_response_omits_internal_details():
    """A failed provider configuration must not disclose the exception contents."""
    response = asyncio.run(
        ai_provider_unavailable(None, AIProviderUnavailableError("private exception"))
    )

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "detail": "Telaryn AI is not configured for this deployment."
    }
    assert b"private exception" not in response.body


def test_release_version_and_proprietary_license_are_consistent():
    """Keep the source release identity aligned across the npm manifest and lock."""
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert package["version"] == "1.0.0-rc.1"
    assert lock["version"] == package["version"]
    assert lock["packages"][""]["version"] == package["version"]
    assert "Proprietary Source-Available Notice" in license_text
    assert "All rights reserved" in license_text


def test_public_browser_and_install_metadata_identify_telaryn():
    """Prevent reintroduction of the starter-template brand or old icon paths."""
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    manifest = json.loads(
        (ROOT / "frontend/public/manifest.webmanifest").read_text(encoding="utf-8")
    )
    icons = {item["src"] for item in manifest["icons"]}

    assert "<title>Telaryn · Every action has a purpose.</title>" in html
    assert 'name="application-name" content="Telaryn"' in html
    assert 'href="/telaryn-apple-touch-icon.png"' in html
    assert manifest["name"] == manifest["short_name"] == "Telaryn"
    assert {"/telaryn-icon-192.png", "/telaryn-icon-512.png", "/telaryn-mark.svg"} <= icons
    assert "Atlas Waypoint" not in html
    assert all("atlas-icon" not in icon for icon in icons)


def test_public_brand_preserves_compatible_export_schema():
    """Brand as Telaryn without silently breaking existing ticket-export consumers."""
    source = (ROOT / "app/services/ticket_export.py").read_text(encoding="utf-8")
    brand = (ROOT / "frontend/src/components/AtlasBrand.jsx").read_text(
        encoding="utf-8"
    )
    landing = (ROOT / "frontend/src/views/PublicLandingView.jsx").read_text(
        encoding="utf-8"
    )

    assert '"schema": "atlas.ticket-export"' in source
    assert 'author="Telaryn"' in source
    assert "TELARYN" in brand
    assert "Every action has a purpose." in landing
    assert "AI proposes. Humans approve. Telaryn records." in landing
