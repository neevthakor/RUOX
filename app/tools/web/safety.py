import os
import socket
import ipaddress
from urllib.parse import urlparse
from app.security.redaction import redact_text

class SecurityError(Exception):
    pass

def is_local_only() -> bool:
    return os.getenv("LOCAL_ONLY", "true").lower() == "true"

def validate_url_safety(url: str) -> str:
    """
    Validates URL safety for SSRF. Returns the URL if safe.
    Raises SecurityError if blocked.
    """
    if is_local_only():
        raise SecurityError("Web access is disabled because LOCAL_ONLY mode is enabled.")

    # Redact check: if the URL changes after redaction, it contained a secret
    redacted = redact_text(url)
    if redacted != url:
        raise SecurityError("URL rejected: contains sensitive information/secrets.")

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise SecurityError(f"Protocol '{parsed.scheme}' not allowed. Only http/https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SecurityError("Invalid URL: missing hostname.")

    try:
        # getaddrinfo returns a list of 5-tuples
        ip_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise SecurityError(f"Could not resolve hostname: {hostname}")

    for result in ip_info:
        ip_str = result[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                raise SecurityError(f"SSRF Protection: Resolution to private/loopback IP blocked ({ip_str})")
            if str(ip) == "169.254.169.254":
                raise SecurityError("SSRF Protection: Cloud metadata endpoint blocked.")
        except ValueError:
            raise SecurityError(f"SSRF Protection: Invalid IP structure ({ip_str})")

    return url

def validate_search_query(query: str) -> str:
    """
    Validates search query. Returns the query if safe.
    Raises SecurityError if blocked.
    """
    if is_local_only():
        raise SecurityError("Web access is disabled because LOCAL_ONLY mode is enabled.")

    redacted = redact_text(query)
    if redacted != query:
        raise SecurityError("Search query rejected: contains sensitive information/secrets.")
        
    return query
