from __future__ import annotations

import json
from typing import Protocol

from p2p_engine.core.vertical_registry import RegistryCredential


_SERVICE_NAME = "p2p-engine.vertical-registry"


class CredentialStore(Protocol):
    def get(self, registry: str) -> RegistryCredential | None: ...

    def set(self, registry: str, credential: RegistryCredential) -> None: ...

    def delete(self, registry: str) -> bool: ...


class MemoryCredentialStore:
    def __init__(self) -> None:
        self._credentials: dict[str, RegistryCredential] = {}

    def get(self, registry: str) -> RegistryCredential | None:
        return self._credentials.get(registry)

    def set(self, registry: str, credential: RegistryCredential) -> None:
        self._credentials[registry] = credential

    def delete(self, registry: str) -> bool:
        return self._credentials.pop(registry, None) is not None


class KeyringCredentialStore:
    def __init__(self, *, service_name: str = _SERVICE_NAME) -> None:
        self.service_name = service_name

    def get(self, registry: str) -> RegistryCredential | None:
        keyring = self._keyring()
        try:
            payload = keyring.get_password(self.service_name, registry)
        except Exception as exc:  # noqa: BLE001 - keyring backends expose provider errors.
            raise _unavailable(exc) from exc
        if payload is None:
            return None
        try:
            raw = json.loads(payload)
            if not isinstance(raw, dict) or not str(raw.get("access_token") or ""):
                raise ValueError("credential payload is incomplete")
            return RegistryCredential(
                access_token=str(raw["access_token"]),
                refresh_token=str(raw.get("refresh_token") or ""),
                token_type=str(raw.get("token_type") or "Bearer"),
                expires_at=int(raw.get("expires_at") or 0),
                scopes=tuple(str(item) for item in raw.get("scopes", []) if str(item)),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                "P2P_REGISTRY_CREDENTIAL_INVALID: secure credential data is malformed"
            ) from exc

    def set(self, registry: str, credential: RegistryCredential) -> None:
        keyring = self._keyring()
        payload = json.dumps(
            {
                "access_token": credential.access_token,
                "refresh_token": credential.refresh_token,
                "token_type": credential.token_type,
                "expires_at": credential.expires_at,
                "scopes": list(credential.scopes),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            keyring.set_password(self.service_name, registry, payload)
        except Exception as exc:  # noqa: BLE001 - keyring backends expose provider errors.
            raise _unavailable(exc) from exc

    def delete(self, registry: str) -> bool:
        keyring = self._keyring()
        try:
            if keyring.get_password(self.service_name, registry) is None:
                return False
            keyring.delete_password(self.service_name, registry)
        except Exception as exc:  # noqa: BLE001 - keyring backends expose provider errors.
            raise _unavailable(exc) from exc
        return True

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:
            raise ValueError(
                "P2P_REGISTRY_CREDENTIAL_STORE_UNAVAILABLE: install a supported OS keyring backend"
            ) from exc
        return keyring


def redact_secret(message: object, *secrets: str) -> str:
    result = str(message)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def _unavailable(exc: Exception) -> ValueError:
    message = redact_secret(exc)
    return ValueError(
        "P2P_REGISTRY_CREDENTIAL_STORE_UNAVAILABLE: "
        f"the operating-system credential provider failed ({message})"
    )
