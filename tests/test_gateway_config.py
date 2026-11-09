"""Protect the Azure Container Apps gateway's internal host routing."""

from pathlib import Path


def test_gateway_proxies_with_the_internal_backend_host() -> None:
    config = Path("frontend/nginx.conf").read_text(encoding="utf-8")

    assert "proxy_pass ${ATLAS_BACKEND_ORIGIN}/;" in config
    assert "proxy_set_header Host $proxy_host;" in config
    assert "proxy_set_header Host $host;" not in config


def test_gateway_buffers_standard_api_responses() -> None:
    """Do not stream unbounded chunks of small JSON replies through the gateway."""
    config = Path("frontend/nginx.conf").read_text(encoding="utf-8")
    api_location = config.split("location /api/ {", 1)[1].split("    }", 1)[0]
    assert "proxy_buffering on;" in api_location
    assert "proxy_buffering off;" not in api_location
    assert "proxy_buffers 16 16k;" in api_location
    assert "proxy_max_temp_file_size 0;" not in api_location


def test_gateway_omits_connection_close_for_aca_internal_ingress() -> None:
    """Do not trigger ACA's reported internal-ingress response truncation."""
    config = Path("frontend/nginx.conf").read_text(encoding="utf-8")
    api_location = config.split("location /api/ {", 1)[1].split("    }", 1)[0]

    assert "proxy_http_version 1.1;" in api_location
    assert 'proxy_set_header Connection "";' in api_location
    assert 'proxy_set_header Connection "close";' not in api_location
    assert "proxy_set_header Host $proxy_host;" in api_location
