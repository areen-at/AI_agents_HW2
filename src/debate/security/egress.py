"""Outbound-request guard: domain allowlist + TLS + anti-SSRF (PRD §4.2 / NFR-6).

Every URL the web-search tool is about to fetch — including any redirect target —
must clear :func:`validate_url`: HTTPS only, host on the configured allowlist, and
never a private/loopback/link-local/reserved IP literal. On any failure it raises
:class:`EgressError`; the caller must not perform the request.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


class EgressError(ValueError):
    """Raised when a URL violates the egress policy (caller must not fetch it)."""


def _host_allowed(host: str, allowed_domains: list[str]) -> bool:
    """Exact or subdomain match of ``host`` against the allowlist (case-insensitive)."""
    host = host.lower().rstrip(".")
    for domain in allowed_domains:
        d = domain.lower().rstrip(".")
        if host == d or host.endswith("." + d):
            return True
    return False


def _ip_is_blocked(host: str) -> bool:
    """True if ``host`` is an IP literal in a non-routable/dangerous range.

    Non-IP hostnames return False here (the allowlist is the gate for those).
    """
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_url(url: str, *, allowed_domains: list[str]) -> str:
    """Return ``url`` unchanged if it satisfies the egress policy, else raise.

    Checks, in order: HTTPS scheme, a present hostname, no blocked IP literal,
    and host membership in ``allowed_domains``.
    """
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        raise EgressError(f"non-HTTPS URL rejected: {parts.scheme or '(none)'}")

    host = parts.hostname
    if not host:
        raise EgressError("URL has no host")

    if _ip_is_blocked(host):
        raise EgressError(f"private/loopback/link-local IP rejected: {host}")

    if not _host_allowed(host, allowed_domains):
        raise EgressError(f"host not on egress allowlist: {host}")

    return url
