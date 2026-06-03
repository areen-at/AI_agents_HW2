"""Tests for the egress allowlist / anti-SSRF guard."""

from __future__ import annotations

import pytest

from debate.security.egress import EgressError, validate_url

ALLOWED = ["api.tavily.com"]


def test_allowlisted_https_url_accepted() -> None:
    url = "https://api.tavily.com/search?q=barcelona"
    assert validate_url(url, allowed_domains=ALLOWED) == url


def test_subdomain_of_allowlisted_host_accepted() -> None:
    url = "https://edge.api.tavily.com/v1"
    assert validate_url(url, allowed_domains=ALLOWED) == url


def test_off_allowlist_domain_rejected() -> None:
    with pytest.raises(EgressError, match="allowlist"):
        validate_url("https://evil.example.com/x", allowed_domains=ALLOWED)


def test_non_https_rejected() -> None:
    with pytest.raises(EgressError, match="non-HTTPS"):
        validate_url("http://api.tavily.com/search", allowed_domains=ALLOWED)


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "224.0.0.1"],
)
def test_private_or_loopback_ip_rejected(host: str) -> None:
    with pytest.raises(EgressError):
        validate_url(f"https://{host}/meta", allowed_domains=ALLOWED)


def test_url_without_host_rejected() -> None:
    with pytest.raises(EgressError, match="no host"):
        validate_url("https:///nohost", allowed_domains=ALLOWED)
