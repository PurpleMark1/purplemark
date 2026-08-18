#!/usr/bin/env python3
"""Call the local PurpleMark API and print its JSON response."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://127.0.0.1:39520"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call the PurpleMark local API.")
    parser.add_argument("path", help="API path, including an optional query string")
    parser.add_argument("--method", default="GET", choices=("GET", "POST"))
    parser.add_argument("--data", help="JSON request body")
    parser.add_argument("--data-file", type=Path, help="UTF-8 JSON request body file")
    parser.add_argument("--endpoint", help="Override PURPLEMARK_LOCAL_API_URL")
    parser.add_argument("--api-key", help="Override PURPLEMARK_API_KEY")
    return parser.parse_args()


def read_body(arguments: argparse.Namespace) -> bytes | None:
    if arguments.data and arguments.data_file:
        raise ValueError("Use only one of --data and --data-file.")

    value = arguments.data
    if arguments.data_file:
        value = arguments.data_file.read_text(encoding="utf-8")
    if value is None:
        return None

    parsed = json.loads(value)
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


def print_response(payload: bytes) -> None:
    try:
        print(json.dumps(json.loads(payload.decode("utf-8")), ensure_ascii=False, indent=2))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(payload.decode("utf-8", errors="replace"))


def main() -> int:
    arguments = parse_arguments()
    try:
        body = read_body(arguments)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Request body error: {error}", file=sys.stderr)
        return 2

    endpoint = (arguments.endpoint or os.getenv("PURPLEMARK_LOCAL_API_URL") or DEFAULT_ENDPOINT).rstrip("/")
    path = arguments.path if arguments.path.startswith("/") else f"/{arguments.path}"
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"

    api_key = arguments.api_key or os.getenv("PURPLEMARK_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(f"{endpoint}{path}", data=body, headers=headers, method=arguments.method)
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
            status = response.status
    except HTTPError as error:
        print_response(error.read())
        return 1
    except URLError as error:
        print(f"Connection error: {error.reason}", file=sys.stderr)
        return 1

    print_response(payload)
    try:
        api_response = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 0 if 200 <= status < 300 else 1
    return 0 if 200 <= status < 300 and api_response.get("code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
