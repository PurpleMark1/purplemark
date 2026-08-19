#!/usr/bin/env python3
"""Small standard-library client for the PurpleMark Local API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "http://127.0.0.1:39520"
API_KEY_ENV = "PURPLEMARK_API_KEY"
ENDPOINT_ENV = "PURPLEMARK_LOCAL_API_URL"


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def positive_number(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call the PurpleMark desktop Local API")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get(ENDPOINT_ENV, DEFAULT_ENDPOINT),
        help=f"loopback Local API URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--timeout",
        type=positive_number,
        default=30.0,
        help="request timeout in seconds",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="check Local API health")

    request_parser = subparsers.add_parser("request", help="call a Local API endpoint")
    request_parser.add_argument("method", choices=("GET", "POST"))
    request_parser.add_argument("path", help="API path beginning with /api/v1/")
    request_parser.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="query parameter; repeat for multiple values",
    )
    json_group = request_parser.add_mutually_exclusive_group()
    json_group.add_argument("--json", dest="json_text", help="inline JSON request body")
    json_group.add_argument("--json-file", type=Path, help="UTF-8 JSON request body file")

    for command, help_text in (
        ("profile-start", "start a browser profile"),
        ("profile-stop", "stop a browser profile"),
        ("profile-status", "query browser profile status"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        add_profile_identifier_arguments(command_parser)

    return parser


def add_profile_identifier_arguments(parser: argparse.ArgumentParser) -> None:
    identifiers = parser.add_mutually_exclusive_group(required=True)
    identifiers.add_argument("--profile-id", help="profile string identifier")
    identifiers.add_argument(
        "--profile-no",
        type=positive_integer,
        help="positive profile number",
    )


def validate_endpoint(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("the Local API endpoint must use HTTP on a loopback address")
    if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("the Local API endpoint must not include a path, credentials, query, or fragment")
    return normalized


def validate_api_path(path: str) -> str:
    if not path.startswith("/api/v1/"):
        raise ValueError("request path must begin with /api/v1/")
    if ".." in path or "?" in path or "#" in path:
        raise ValueError("request path must not contain traversal, query, or fragment text")
    return path


def parse_query(items: Sequence[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key:
            raise ValueError(f"invalid query parameter: {item!r}; expected KEY=VALUE")
        pairs.append((key, value))
    return pairs


def load_json_body(json_text: str | None, json_file: Path | None) -> Any | None:
    if json_file is not None:
        json_text = json_file.read_text(encoding="utf-8")
    if json_text is None:
        return None
    return json.loads(json_text)


def profile_identifiers(args: argparse.Namespace) -> dict[str, str | int]:
    if args.profile_id is not None:
        profile_id = args.profile_id.strip()
        if not profile_id:
            raise ValueError("profile ID must not be empty")
        return {"profile_id": profile_id}
    return {"profile_no": args.profile_no}


def resolve_operation(
    args: argparse.Namespace,
) -> tuple[str, str, list[tuple[str, str]], Any | None, bool]:
    if args.command == "health":
        return "GET", "/api/v1/healthz", [], None, False
    if args.command == "request":
        return (
            args.method,
            validate_api_path(args.path),
            parse_query(args.query),
            load_json_body(args.json_text, args.json_file),
            True,
        )

    identifiers = profile_identifiers(args)
    if args.command == "profile-start":
        return "POST", "/api/v1/profile/start", [], identifiers, True
    if args.command == "profile-stop":
        return "POST", "/api/v1/profile/stop", [], identifiers, True
    if args.command == "profile-status":
        return (
            "GET",
            "/api/v1/profile/status",
            [(key, str(value)) for key, value in identifiers.items()],
            None,
            True,
        )
    raise ValueError(f"unsupported command: {args.command}")


def resolve_api_key() -> str:
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise ValueError(f"set {API_KEY_ENV} before calling an authenticated endpoint")
    return api_key


def decode_response(payload: bytes) -> Any:
    text = payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"code": -1, "msg": "Local API returned a non-JSON response", "data": text}


def call_api(
    endpoint: str,
    method: str,
    path: str,
    query: Sequence[tuple[str, str]],
    body: Any | None,
    authenticated: bool,
    timeout: float,
) -> tuple[int, Any]:
    url = f"{endpoint}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    headers = {"Accept": "application/json"}
    if authenticated:
        headers["Authorization"] = f"Bearer {resolve_api_key()}"

    request_body = None
    if body is not None:
        request_body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(url, data=request_body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, decode_response(response.read())
    except HTTPError as error:
        return error.code, decode_response(error.read())


def print_result(result: Any, stream: Any = sys.stdout) -> None:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        endpoint = validate_endpoint(args.endpoint)
        method, path, query, body, authenticated = resolve_operation(args)
        status, result = call_api(
            endpoint,
            method,
            path,
            query,
            body,
            authenticated,
            args.timeout,
        )
    except (OSError, URLError, ValueError, json.JSONDecodeError) as error:
        print(f"PurpleMark Local API error: {error}", file=sys.stderr)
        return 2

    response_code = result.get("code") if isinstance(result, dict) else None
    succeeded = 200 <= status < 300 and response_code == 0
    print_result(result, sys.stdout if succeeded else sys.stderr)
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
