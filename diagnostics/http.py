import re
import socket
from time import perf_counter
from urllib.parse import urljoin

import requests

from diagnostics.dns import resolve_addresses
from diagnostics.result import make_result
from diagnostics.target import TargetError, normalize_target, validate_public_addresses


TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
MAX_REDIRECTS = 5
MAX_BODY_BYTES = 128 * 1024


def _page_title(response):
    body = bytearray()

    for chunk in response.iter_content(chunk_size=8192):
        body.extend(chunk)
        if len(body) >= MAX_BODY_BYTES:
            break

    text = bytes(body[:MAX_BODY_BYTES]).decode(response.encoding or "utf-8", errors="replace")
    match = TITLE_PATTERN.search(text)

    if not match:
        return "Not found"

    return " ".join(match.group(1).split())[:200]


def _server_features(headers):
    features = []
    header_names = {name.lower() for name in headers}

    if "cf-ray" in header_names:
        features.append("Cloudflare")
    if "x-cache" in header_names or "x-served-by" in header_names:
        features.append("Caching/CDN headers")
    if "x-sucuri-id" in header_names:
        features.append("Sucuri")

    return features or ["No basic CDN/WAF signature detected"]


def check_http(target, timeout=6):
    started = perf_counter()
    session = requests.Session()
    session.trust_env = False
    current_url = target["url"]
    redirects = []

    try:
        for _ in range(MAX_REDIRECTS + 1):
            current_target = normalize_target(current_url)
            ipv4, ipv6 = resolve_addresses(current_target["hostname"])
            validate_public_addresses(ipv4 + ipv6)

            response = session.get(
                current_target["url"],
                allow_redirects=False,
                headers={"User-Agent": "ServicePath/1.0"},
                stream=True,
                timeout=timeout,
            )

            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise requests.RequestException(
                        "Redirect response did not include a Location header"
                    )
                current_url = urljoin(current_target["url"], location)
                redirects.append(current_url)
                continue

            title = _page_title(response)
            status_code = response.status_code
            final_url = current_target["url"]
            headers = response.headers
            response.close()

            details = {
                "Status code": status_code,
                "Final URL": final_url,
                "Redirects": redirects,
                "Page title": title,
                "Server": headers.get("Server", "Not reported"),
                "CDN/WAF": _server_features(headers),
            }

            if status_code >= 500:
                status = "error"
                summary = f"The website returned server error HTTP {status_code}."
            elif status_code >= 400:
                status = "warning"
                summary = f"The website is reachable but returned HTTP {status_code}."
            else:
                status = "passed"
                summary = f"The website responded with HTTP {status_code}."

            duration = round((perf_counter() - started) * 1000)
            return make_result("http", "HTTP", status, summary, duration, details)

        raise requests.TooManyRedirects(f"More than {MAX_REDIRECTS} redirects")
    except (requests.RequestException, socket.gaierror, TargetError) as error:
        duration = round((perf_counter() - started) * 1000)
        return make_result(
            "http",
            "HTTP",
            "error",
            f"HTTP request failed: {error}",
            duration,
        )
    finally:
        session.close()
