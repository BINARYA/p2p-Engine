from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import os
import re
import socket
import ssl
from typing import Mapping, Protocol
from urllib.parse import urlencode, urlsplit

from p2p_engine.adapters.credential_store import redact_secret
from p2p_engine.core.vertical_registry import ArtifactDownload


class VerticalRegistryTransport(Protocol):
    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        form: Mapping[str, str] | None = None,
        max_bytes: int = 1_048_576,
    ) -> object: ...

    def download(
        self,
        url: str,
        destination: Path,
        *,
        token: str = "",
        max_bytes: int,
    ) -> ArtifactDownload: ...

    def publish_artifact(
        self,
        url: str,
        artifact: Path,
        *,
        metadata: Mapping[str, object],
        token: str,
        idempotency_key: str,
        max_artifact_bytes: int,
        max_response_bytes: int,
    ) -> object: ...


class HTTPSVerticalRegistryTransport:
    def __init__(self, *, connect_timeout: float = 5.0, read_timeout: float = 30.0) -> None:
        if connect_timeout <= 0 or read_timeout <= 0:
            raise ValueError("P2P_REGISTRY_INVALID_TIMEOUT: timeouts must be positive")
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    def request_json(
        self,
        method: str,
        url: str,
        *,
        token: str = "",
        form: Mapping[str, str] | None = None,
        max_bytes: int = 1_048_576,
    ) -> object:
        headers = {"Accept": "application/json"}
        body: bytes | None = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if form is not None:
            body = urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        connection, path = self._connection(url)
        try:
            connection.request(method.upper(), path, body=body, headers=headers)
            response = connection.getresponse()
            self._set_read_timeout(connection)
            payload = self._read_bounded(response, max_bytes=max_bytes)
            if response.status == 400:
                try:
                    return json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
            self._raise_for_status(response.status, token=token)
            try:
                return json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("P2P_REGISTRY_RESPONSE_INVALID: expected a JSON response") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise ValueError("P2P_REGISTRY_TIMEOUT: registry request timed out") from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            raise ValueError(
                "P2P_REGISTRY_UNAVAILABLE: " + redact_secret(exc, token)
            ) from exc
        finally:
            connection.close()

    def download(
        self,
        url: str,
        destination: Path,
        *,
        token: str = "",
        max_bytes: int,
    ) -> ArtifactDownload:
        headers = {"Accept": "application/octet-stream"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection, path = self._connection(url)
        digest = hashlib.sha256()
        size = 0
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            self._set_read_timeout(connection)
            self._raise_for_status(response.status, token=token)
            declared = response.getheader("Content-Length")
            if declared is not None:
                try:
                    declared_size = int(declared)
                except ValueError as exc:
                    raise ValueError(
                        "P2P_REGISTRY_RESPONSE_INVALID: invalid Content-Length header"
                    ) from exc
                if declared_size > max_bytes:
                    raise ValueError(
                        f"P2P_REGISTRY_ARTIFACT_TOO_LARGE: artifact exceeds {max_bytes} bytes"
                    )
            with destination.open("xb") as handle:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError(
                            f"P2P_REGISTRY_ARTIFACT_TOO_LARGE: artifact exceeds {max_bytes} bytes"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            return ArtifactDownload(path=destination, sha256=digest.hexdigest(), size=size)
        except ValueError:
            destination.unlink(missing_ok=True)
            raise
        except (TimeoutError, socket.timeout) as exc:
            destination.unlink(missing_ok=True)
            raise ValueError("P2P_REGISTRY_TIMEOUT: registry download timed out") from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            destination.unlink(missing_ok=True)
            raise ValueError(
                "P2P_REGISTRY_UNAVAILABLE: " + redact_secret(exc, token)
            ) from exc
        finally:
            connection.close()

    def publish_artifact(
        self,
        url: str,
        artifact: Path,
        *,
        metadata: Mapping[str, object],
        token: str,
        idempotency_key: str,
        max_artifact_bytes: int,
        max_response_bytes: int,
    ) -> object:
        try:
            artifact_bytes = artifact.read_bytes()
        except OSError as exc:
            raise ValueError("P2P_REGISTRY_ARTIFACT_INVALID: artifact could not be read") from exc
        if len(artifact_bytes) > max_artifact_bytes:
            raise ValueError(
                f"P2P_REGISTRY_ARTIFACT_TOO_LARGE: artifact exceeds {max_artifact_bytes} bytes"
            )
        metadata_bytes = json.dumps(
            metadata,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        boundary = "p2p-vertical-" + hashlib.sha256(metadata_bytes).hexdigest()[:24]
        body = b"".join(
            (
                f"--{boundary}\r\n".encode("ascii"),
                b'Content-Disposition: form-data; name="metadata"\r\n',
                b"Content-Type: application/json\r\n\r\n",
                metadata_bytes,
                b"\r\n",
                f"--{boundary}\r\n".encode("ascii"),
                b'Content-Disposition: form-data; name="artifact"; filename="vertical.p2pv"\r\n',
                b"Content-Type: application/octet-stream\r\n\r\n",
                artifact_bytes,
                b"\r\n",
                f"--{boundary}--\r\n".encode("ascii"),
            )
        )
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Idempotency-Key": idempotency_key,
        }
        connection, path = self._connection(url)
        try:
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            self._set_read_timeout(connection)
            payload = self._read_bounded(response, max_bytes=max_response_bytes)
            if not 200 <= response.status < 300:
                self._raise_provider_error(response.status, payload, token=token)
            try:
                return json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(
                    "P2P_REGISTRY_RESPONSE_INVALID: expected a JSON response"
                ) from exc
        except ValueError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise ValueError("P2P_REGISTRY_TIMEOUT: registry request timed out") from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            raise ValueError(
                "P2P_REGISTRY_UNAVAILABLE: " + redact_secret(exc, token)
            ) from exc
        finally:
            connection.close()

    def _connection(self, url: str) -> tuple[http.client.HTTPConnection, str]:
        parsed = urlsplit(url)
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError("P2P_REGISTRY_INVALID_URL: unsafe request URL")
        if parsed.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                parsed.hostname,
                parsed.port,
                timeout=self.connect_timeout,
                context=ssl.create_default_context(),
            )
        elif parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            connection = http.client.HTTPConnection(
                parsed.hostname,
                parsed.port,
                timeout=self.connect_timeout,
            )
        else:
            raise ValueError("P2P_REGISTRY_INVALID_URL: HTTPS is required")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        return connection, path

    def _set_read_timeout(self, connection: http.client.HTTPConnection) -> None:
        if connection.sock is not None:
            connection.sock.settimeout(self.read_timeout)

    @staticmethod
    def _read_bounded(response: http.client.HTTPResponse, *, max_bytes: int) -> bytes:
        declared = response.getheader("Content-Length")
        if declared is not None:
            try:
                declared_size = int(declared)
            except ValueError as exc:
                raise ValueError(
                    "P2P_REGISTRY_RESPONSE_INVALID: invalid Content-Length header"
                ) from exc
            if declared_size > max_bytes:
                raise ValueError(
                    f"P2P_REGISTRY_RESPONSE_TOO_LARGE: response exceeds {max_bytes} bytes"
                )
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(
                f"P2P_REGISTRY_RESPONSE_TOO_LARGE: response exceeds {max_bytes} bytes"
            )
        return data

    @staticmethod
    def _raise_for_status(status: int, *, token: str) -> None:
        if 200 <= status < 300:
            return
        if status in {401, 403}:
            raise ValueError("P2P_REGISTRY_AUTH_REQUIRED: registry authentication is required")
        if status == 404:
            raise ValueError("P2P_REGISTRY_RELEASE_NOT_FOUND: exact release was not found")
        if status == 409:
            raise ValueError("P2P_REGISTRY_CONFLICT: registry rejected the request")
        raise ValueError(f"P2P_REGISTRY_UNAVAILABLE: registry returned HTTP {status}")

    @classmethod
    def _raise_provider_error(cls, status: int, payload: bytes, *, token: str) -> None:
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            cls._raise_for_status(status, token=token)
            return
        error = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(error, dict):
            code = str(error.get("code") or "")
            message = redact_secret(str(error.get("message") or "Registry request failed."), token)
            if re.fullmatch(r"P2P_[A-Z0-9_]+", code):
                raise ValueError(f"{code}: {message}")
        cls._raise_for_status(status, token=token)
