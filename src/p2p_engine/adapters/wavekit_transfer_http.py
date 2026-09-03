from __future__ import annotations

import http.client
import json
import socket
import ssl
import time
from collections.abc import Iterator
from typing import Mapping, Protocol
from urllib.parse import urlencode, urlsplit

from p2p_engine.adapters.credential_store import redact_secret


class WaveKitTransferTransport(Protocol):
    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        json_body: Mapping[str, object] | None = None,
        form: Mapping[str, str] | None = None,
        idempotency_key: str = "",
        max_bytes: int = 1_048_576,
    ) -> object: ...

    def upload_bytes(
        self,
        url: str,
        content: bytes,
        *,
        token: str,
        digest: str,
        idempotency_key: str,
        max_bytes: int,
        max_response_bytes: int = 1_048_576,
    ) -> object: ...

    def download_bytes(
        self,
        url: str,
        *,
        token: str,
        max_bytes: int,
    ) -> bytes: ...

    def iter_sse(
        self,
        url: str,
        *,
        token: str,
        last_event_id: str = "",
        heartbeat_seconds: int = 30,
    ) -> Iterator[Mapping[str, object]]: ...


class HTTPSWaveKitTransferTransport:
    def __init__(self, *, connect_timeout: float = 5.0, read_timeout: float = 60.0) -> None:
        if connect_timeout <= 0 or read_timeout <= 0:
            raise ValueError("P2P_WAVEKIT_INVALID_TIMEOUT: timeouts must be positive")
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        json_body: Mapping[str, object] | None = None,
        form: Mapping[str, str] | None = None,
        idempotency_key: str = "",
        max_bytes: int = 1_048_576,
    ) -> object:
        if json_body is not None and form is not None:
            raise ValueError("P2P_WAVEKIT_REQUEST_INVALID: JSON and form bodies are exclusive")
        headers = {"Accept": "application/json"}
        body: bytes | None = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if json_body is not None:
            body = json.dumps(
                json_body, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("ascii")
            headers["Content-Type"] = "application/json"
        elif form is not None:
            body = urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return self._request(method, url, body=body, headers=headers, token=token, max_bytes=max_bytes)

    def upload_bytes(
        self,
        url: str,
        content: bytes,
        *,
        token: str,
        digest: str,
        idempotency_key: str,
        max_bytes: int,
        max_response_bytes: int = 1_048_576,
    ) -> object:
        if len(content) > max_bytes:
            raise ValueError("P2P_AUTHORITY_TRANSFER_PAYLOAD_TOO_LARGE: upload exceeds limit")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "Content-Digest": f"sha-256=:{digest}:",
            "Idempotency-Key": idempotency_key,
        }
        return self._request(
            "PUT",
            url,
            body=content,
            headers=headers,
            token=token,
            max_bytes=max_response_bytes,
        )

    def download_bytes(
        self,
        url: str,
        *,
        token: str,
        max_bytes: int,
    ) -> bytes:
        headers = {
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
        }
        connection, path = self._connection(url)
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            if connection.sock is not None:
                connection.sock.settimeout(self.read_timeout)
            payload = self._read_bounded(response, max_bytes=max_bytes)
            if not 200 <= response.status < 300:
                self._raise_provider_error(response.status, payload, token=token)
            return payload
        except ValueError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise ValueError(
                "P2P_WAVEKIT_RESPONSE_UNKNOWN: download timed out; retry the same session"
            ) from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            raise ValueError("P2P_WAVEKIT_UNAVAILABLE: " + redact_secret(exc, token)) from exc
        finally:
            connection.close()

    def iter_sse(
        self,
        url: str,
        *,
        token: str,
        last_event_id: str = "",
        heartbeat_seconds: int = 30,
    ) -> Iterator[Mapping[str, object]]:
        """Yield bounded JSON SSE notifications and reconnect after clean/lost streams."""
        if not 1 <= heartbeat_seconds <= 300:
            raise ValueError("P2P_REPLICATION_INVALID: heartbeat interval is unsafe")
        event_id = last_event_id
        reconnect_attempt = 0
        while True:
            connection, path = self._connection(url)
            headers = {
                "Accept": "text/event-stream",
                "Authorization": f"Bearer {token}",
                "Cache-Control": "no-cache",
            }
            if event_id:
                headers["Last-Event-ID"] = event_id
            try:
                connection.request("GET", path, headers=headers)
                response = connection.getresponse()
                if not 200 <= response.status < 300:
                    payload = self._read_bounded(response, max_bytes=1_048_576)
                    self._raise_provider_error(response.status, payload, token=token)
                if connection.sock is not None:
                    connection.sock.settimeout(float(heartbeat_seconds * 2))
                content_type = str(response.getheader("Content-Type") or "")
                if "text/event-stream" not in content_type.lower():
                    raise ValueError("P2P_REPLICATION_RESPONSE_INVALID: expected event stream")
                data_lines: list[str] = []
                wire_bytes = 0
                while True:
                    line = response.readline(65_537)
                    if not line:
                        break
                    wire_bytes += len(line)
                    if len(line) > 65_536 or wire_bytes > 16_777_216:
                        raise ValueError(
                            "P2P_REPLICATION_PAYLOAD_TOO_LARGE: SSE event exceeds its limit"
                        )
                    try:
                        text = line.decode("utf-8").rstrip("\r\n")
                    except UnicodeDecodeError as exc:
                        raise ValueError(
                            "P2P_REPLICATION_RESPONSE_INVALID: SSE is not UTF-8"
                        ) from exc
                    if not text:
                        if data_lines:
                            try:
                                payload = json.loads("\n".join(data_lines))
                            except json.JSONDecodeError as exc:
                                raise ValueError(
                                    "P2P_REPLICATION_RESPONSE_INVALID: SSE data is not JSON"
                                ) from exc
                            if not isinstance(payload, Mapping):
                                raise ValueError(
                                    "P2P_REPLICATION_RESPONSE_INVALID: SSE data must be a mapping"
                                )
                            received_id = payload.get("event_id")
                            if isinstance(received_id, str) and received_id:
                                event_id = received_id
                            reconnect_attempt = 0
                            yield payload
                        data_lines = []
                        wire_bytes = 0
                        continue
                    if text.startswith(":"):
                        # A heartbeat is a complete comment frame, not part of
                        # the following JSON event's byte budget.
                        wire_bytes = 0
                        continue
                    field, _, value = text.partition(":")
                    value = value[1:] if value.startswith(" ") else value
                    if field == "id" and value:
                        event_id = value
                    elif field == "data":
                        data_lines.append(value)
            except ValueError as exc:
                if "P2P_WAVEKIT_THROTTLED" not in str(exc):
                    raise
                # A throttled event stream is transient.  Reuse the same
                # bounded reconnect path and Last-Event-ID cursor.
            except (TimeoutError, socket.timeout, ssl.SSLError, OSError, http.client.HTTPException):
                # SSE is only a wake-up channel.  Reconnection is bounded by
                # exponential backoff; the caller confirms all state via HTTP.
                pass
            finally:
                connection.close()
            reconnect_attempt += 1
            time.sleep(min(30.0, 0.25 * (2 ** min(reconnect_attempt, 7))))

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None,
        headers: Mapping[str, str],
        token: str,
        max_bytes: int,
    ) -> object:
        connection, path = self._connection(url)
        try:
            connection.request(method.upper(), path, body=body, headers=dict(headers))
            response = connection.getresponse()
            if connection.sock is not None:
                connection.sock.settimeout(self.read_timeout)
            payload = self._read_bounded(response, max_bytes=max_bytes)
            if not 200 <= response.status < 300:
                self._raise_provider_error(response.status, payload, token=token)
            if not payload:
                return {}
            try:
                return json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: expected JSON") from exc
        except ValueError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise ValueError(
                "P2P_WAVEKIT_RESPONSE_UNKNOWN: request timed out; query the same transfer session"
            ) from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            raise ValueError(
                "P2P_WAVEKIT_UNAVAILABLE: " + redact_secret(exc, token)
            ) from exc
        finally:
            connection.close()

    def _connection(self, url: str) -> tuple[http.client.HTTPConnection, str]:
        parsed = urlsplit(url)
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.hostname is None
        ):
            raise ValueError("P2P_WAVEKIT_INVALID_URL: unsafe request URL")
        hostname = parsed.hostname
        if parsed.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                hostname,
                parsed.port,
                timeout=self.connect_timeout,
                context=ssl.create_default_context(),
            )
        elif parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            connection = http.client.HTTPConnection(
                hostname, parsed.port, timeout=self.connect_timeout
            )
        else:
            raise ValueError("P2P_WAVEKIT_INVALID_URL: HTTPS is required outside loopback")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        return connection, path

    @staticmethod
    def _read_bounded(response: http.client.HTTPResponse, *, max_bytes: int) -> bytes:
        declared = response.getheader("Content-Length")
        if declared is not None:
            try:
                if int(declared) > max_bytes:
                    raise ValueError(
                        "P2P_WAVEKIT_RESPONSE_TOO_LARGE: response exceeds negotiated limit"
                    )
            except ValueError as exc:
                if str(exc).startswith("P2P_"):
                    raise
                raise ValueError("P2P_WAVEKIT_RESPONSE_INVALID: invalid Content-Length") from exc
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("P2P_WAVEKIT_RESPONSE_TOO_LARGE: response exceeds negotiated limit")
        return payload

    @staticmethod
    def _raise_provider_error(status: int, payload: bytes, *, token: str) -> None:
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raw = None
        error = raw.get("error") if isinstance(raw, dict) else None
        if isinstance(error, dict):
            code = str(error.get("code") or "")
            message = redact_secret(error.get("message") or "WaveKit rejected the request.", token)
            if code.startswith("P2P_") and code.replace("_", "").isalnum():
                raise ValueError(f"{code}: {message}")
        if status in {401, 403}:
            raise ValueError("P2P_WAVEKIT_AUTH_REQUIRED: authentication or capability is missing")
        if status == 404:
            raise ValueError("P2P_AUTHORITY_TRANSFER_NOT_FOUND: transfer session was not found")
        if status == 409:
            raise ValueError("P2P_AUTHORITY_TRANSFER_CONFLICT: WaveKit rejected conflicting state")
        if status == 413:
            raise ValueError("P2P_AUTHORITY_TRANSFER_PAYLOAD_TOO_LARGE: server quota was exceeded")
        if status == 429:
            raise ValueError("P2P_WAVEKIT_THROTTLED: request was throttled")
        raise ValueError(f"P2P_WAVEKIT_UNAVAILABLE: WaveKit returned HTTP {status}")
