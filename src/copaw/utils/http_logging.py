# -*- coding: utf-8 -*-
"""HTTP request/response logging for debugging.

This module monkey-patches httpx to log full HTTP request and response messages.
"""
import json
import sys
from typing import Any

import httpx

# Flag to prevent double patching
_patched = False

# ANSI color codes
_COLOR_RESET = "\033[0m"
_COLOR_CYAN = "\033[36m"
_COLOR_GREEN = "\033[32m"
_COLOR_YELLOW = "\033[33m"
_COLOR_BOLD = "\033[1m"
_COLOR_RED = "\033[31m"

# Track streaming response bodies for logging
_streaming_bodies: dict[int, list[str]] = {}


def _format_headers(headers: httpx.Headers) -> str:
    """Format headers as HTTP header string."""
    lines = []
    for key, value in headers.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_body(body: Any, content_type: str = "") -> str:
    """Format request/response body for logging."""
    if body is None:
        return ""

    if isinstance(body, bytes):
        # Try to decode as UTF-8
        try:
            body_str = body.decode("utf-8")
            # Try to pretty-print JSON
            if "application/json" in content_type:
                try:
                    parsed = json.loads(body_str)
                    return json.dumps(parsed, indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    pass
            return body_str
        except UnicodeDecodeError:
            return f"<binary data: {len(body)} bytes>"
    elif isinstance(body, str):
        # Try to pretty-print JSON
        if "application/json" in content_type:
            try:
                parsed = json.loads(body)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
        return body
    elif isinstance(body, (dict, list)):
        return json.dumps(body, indent=2, ensure_ascii=False)
    else:
        return str(body)


def _classify_request(url: str) -> tuple[str, str, str]:
    """Classify request type based on URL.

    Returns:
        (type_name, color, description) - type name, ANSI color, Chinese description
    """
    url_lower = url.lower()
    if "/v1/chat/completions" in url_lower or "/chat/completions" in url_lower:
        return ("LLM", _COLOR_CYAN, "【发送给 LLM 的请求】")
    elif "/mcp" in url_lower or "mcp" in url_lower:
        return ("MCP", _COLOR_YELLOW, "【Agent 调用 MCP 工具的请求】")
    else:
        return ("HTTP", _COLOR_CYAN, "【HTTP 请求】")


def _classify_response(url: str) -> tuple[str, str, str]:
    """Classify response type based on URL.

    Returns:
        (type_name, color, Chinese description)
    """
    url_lower = url.lower()
    if "/v1/chat/completions" in url_lower or "/chat/completions" in url_lower:
        return ("LLM", _COLOR_GREEN, "【LLM 返回的响应】")
    elif "/mcp" in url_lower or "mcp" in url_lower:
        return ("MCP", _COLOR_GREEN, "【MCP 工具返回的响应】")
    else:
        return ("HTTP", _COLOR_GREEN, "【HTTP 响应】")


def _log_request(request: httpx.Request) -> None:
    """Log full HTTP request to console."""
    try:
        # Build request line
        method = request.method
        url = str(request.url)
        http_version = request.extensions.get(
            "http_version", b"HTTP/1.1"
        ).decode()

        # Classify request type
        type_name, color, description = _classify_request(url)

        output = [
            "",
            f"{_COLOR_BOLD}{color}{'█' * 80}{_COLOR_RESET}",
            f"{_COLOR_BOLD}{color}>>> {type_name} 请求 >>>  {description}{_COLOR_RESET}",
            f"{_COLOR_YELLOW}{method} {url} {http_version}{_COLOR_RESET}",
        ]

        # Add headers
        if request.headers:
            output.append(_format_headers(request.headers))

        output.append("")  # Empty line before body

        # Add body
        content_type = request.headers.get("content-type", "")
        if request.content:
            output.append(_format_body(request.content, content_type))
        elif hasattr(request, "_content") and request._content is not None:
            output.append(_format_body(request._content, content_type))

        output.append(f"{_COLOR_BOLD}{color}{'█' * 80}{_COLOR_RESET}")
        output.append("")  # Extra newline

        print("\n".join(output), file=sys.stderr, flush=True)
    except Exception as e:
        print(
            f"[HTTP LOG ERROR] Failed to log request: {e}",
            file=sys.stderr,
            flush=True,
        )


def _log_response(response: httpx.Response, request_url: str = "") -> None:
    """Log full HTTP response to console."""
    try:
        # Build response line
        http_version = getattr(response, "http_version", "HTTP/1.1")
        if isinstance(http_version, bytes):
            http_version = http_version.decode()

        # Classify response type
        type_name, color, description = _classify_response(
            request_url or str(response.url)
        )

        # Color code for status
        status_code = response.status_code
        if status_code < 300:
            status_color = _COLOR_GREEN
        elif status_code < 400:
            status_color = _COLOR_YELLOW
        else:
            status_color = _COLOR_RED

        output = [
            "",
            f"{_COLOR_BOLD}{color}{'░' * 80}{_COLOR_RESET}",
            f"{_COLOR_BOLD}{color}<<< {type_name} 响应 <<<  {description}{_COLOR_RESET}",
            f"{status_color}{http_version} {status_code} {response.reason_phrase}{_COLOR_RESET}",
        ]

        # Add headers
        if response.headers:
            output.append(_format_headers(response.headers))

        output.append("")  # Empty line before body

        # Add body (note: for streaming responses, this may be empty)
        content_type = response.headers.get("content-type", "")
        if response.content:
            body_text = _format_body(response.content, content_type)
            # Truncate very long streaming responses
            if len(body_text) > 5000 and "text/event-stream" in content_type:
                body_text = (
                    body_text[:5000]
                    + "\n... [响应内容过长，已截断，共 "
                    + str(len(body_text))
                    + " 字符]"
                )
            output.append(body_text)
        else:
            output.append("[流式响应 - 内容将在读取后显示]")

        output.append(f"{_COLOR_BOLD}{color}{'░' * 80}{_COLOR_RESET}")
        output.append("")  # Extra newline

        print("\n".join(output), file=sys.stderr, flush=True)
    except Exception as e:
        print(
            f"[HTTP LOG ERROR] Failed to log response: {e}",
            file=sys.stderr,
            flush=True,
        )


# Store original methods
_original_async_client_send = httpx.AsyncClient.send
_original_sync_client_send = httpx.Client.send


async def _patched_async_send(
    self, request: httpx.Request, **kwargs
) -> httpx.Response:
    """Patched AsyncClient.send that logs requests and responses."""
    request_url = str(request.url)
    _log_request(request)
    response = await _original_async_client_send(self, request, **kwargs)
    _log_response(response, request_url)
    return response


def _patched_sync_send(
    self, request: httpx.Request, **kwargs
) -> httpx.Response:
    """Patched Client.send that logs requests and responses."""
    request_url = str(request.url)
    _log_request(request)
    response = _original_sync_client_send(self, request, **kwargs)
    _log_response(response, request_url)
    return response


def enable_http_logging() -> None:
    """Enable full HTTP request/response logging by patching httpx.

    This function should be called once at application startup.
    """
    global _patched

    if _patched:
        print("[HTTP LOG] Already enabled, skipping", file=sys.stderr)
        return

    # Patch AsyncClient
    httpx.AsyncClient.send = _patched_async_send

    # Patch sync Client
    httpx.Client.send = _patched_sync_send

    _patched = True
    print(
        f"{_COLOR_GREEN}[HTTP LOG] Enabled - will print all HTTP traffic to console{_COLOR_RESET}",
        file=sys.stderr,
    )


def disable_http_logging() -> None:
    """Disable HTTP request/response logging by restoring original methods."""
    global _patched

    if not _patched:
        return

    # Restore original methods
    httpx.AsyncClient.send = _original_async_client_send
    httpx.Client.send = _original_sync_client_send

    _patched = False
    print("[HTTP LOG] Disabled", file=sys.stderr)
