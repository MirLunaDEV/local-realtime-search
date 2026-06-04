from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


@dataclass(frozen=True)
class UrlSafetyResult:
    allowed: bool
    reason: str | None = None
    host: str | None = None
    resolved_ips: tuple[str, ...] = ()


_ALLOWED_SCHEMES = {"http", "https"}
_LOCAL_NAMES = {"localhost", "localhost.localdomain"}


def _is_private_or_special(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _normalize_host(host: str) -> str:
    return host.strip("[]").rstrip(".").lower()


def assess_url_safety(
    url: str,
    *,
    allow_private_network: bool = False,
    resolve_hostnames: bool = True,
    resolver=socket.getaddrinfo,
) -> UrlSafetyResult:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        return UrlSafetyResult(False, f"unsupported URL scheme: {parts.scheme or 'missing'}")
    if not parts.hostname:
        return UrlSafetyResult(False, "missing URL host")
    if parts.username or parts.password:
        return UrlSafetyResult(False, "URL userinfo is not allowed", host=parts.hostname)

    host = _normalize_host(parts.hostname)
    if not host:
        return UrlSafetyResult(False, "missing URL host")
    if allow_private_network:
        return UrlSafetyResult(True, host=host)
    if host in _LOCAL_NAMES or host.endswith(".localhost"):
        return UrlSafetyResult(False, "local hostnames are blocked", host=host)

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        if _is_private_or_special(ip):
            return UrlSafetyResult(False, f"private or special IP address is blocked: {ip}", host=host, resolved_ips=(str(ip),))
        return UrlSafetyResult(True, host=host, resolved_ips=(str(ip),))

    if not resolve_hostnames:
        return UrlSafetyResult(True, host=host)

    try:
        addr_infos = resolver(host, None)
    except Exception as exc:
        return UrlSafetyResult(False, f"hostname could not be resolved safely: {exc}", host=host)

    resolved: set[str] = set()
    for info in addr_infos:
        ip_text = str(info[4][0])
        try:
            resolved_ip = ipaddress.ip_address(ip_text)
        except ValueError:
            return UrlSafetyResult(False, f"unrecognized resolved address: {ip_text}", host=host)
        resolved.add(str(resolved_ip))
        if _is_private_or_special(resolved_ip):
            return UrlSafetyResult(
                False,
                f"hostname resolves to private or special IP address: {resolved_ip}",
                host=host,
                resolved_ips=tuple(sorted(resolved)),
            )

    return UrlSafetyResult(True, host=host, resolved_ips=tuple(sorted(resolved)))


def ensure_url_safe_for_fetch(
    url: str,
    *,
    allow_private_network: bool = False,
    resolve_hostnames: bool = True,
) -> UrlSafetyResult:
    result = assess_url_safety(
        url,
        allow_private_network=allow_private_network,
        resolve_hostnames=resolve_hostnames,
    )
    if not result.allowed:
        raise UnsafeUrlError(result.reason or "URL is not safe to fetch")
    return result
