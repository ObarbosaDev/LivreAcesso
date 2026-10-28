"""Verifica endpoints públicos após um deploy Oracle sem enviar dados."""

from __future__ import annotations

import argparse
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check(url: str, expected: set[int]) -> tuple[bool, str]:
    request = Request(url, headers={"User-Agent": "livre-acesso-smoke-check/1"})
    try:
        with urlopen(request, timeout=10) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    except (URLError, TimeoutError) as error:
        return False, f"{url}: indisponível ({error})"
    if status not in expected:
        return False, f"{url}: status inesperado {status}"
    return True, f"{url}: {status}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test do deploy Oracle")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--frontend-url", required=True)
    args = parser.parse_args()
    api = args.api_url.rstrip("/")
    frontend = args.frontend_url.rstrip("/")
    checks = [
        check(f"{api}/health/live", {200}),
        check(f"{api}/health/ready", {200}),
        check(f"{api}/api/v1/students", {401}),
        check(f"{frontend}/health", {200}),
    ]
    for passed, message in checks:
        print(("PASS" if passed else "FAIL") + " " + message)
    return 0 if all(passed for passed, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
