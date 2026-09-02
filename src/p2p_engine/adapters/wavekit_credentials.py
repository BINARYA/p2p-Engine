from __future__ import annotations

import json
from typing import Protocol

from p2p_engine.adapters.credential_store import redact_secret
from p2p_engine.core.authority_transfer import WaveKitCredential


class WaveKitCredentialStore(Protocol):
    def get(self, server_key: str) -> WaveKitCredential | None: ...

    def set(self, server_key: str, credential: WaveKitCredential) -> None: ...

    def delete(self, server_key: str) -> bool: ...


class MemoryWaveKitCredentialStore:
    def __init__(self) -> None:
        self._credentials: dict[str, WaveKitCredential] = {}

    def get(self, server_key: str) -> WaveKitCredential | None:
        return self._credentials.get(server_key)

    def set(self, server_key: str, credential: WaveKitCredential) -> None:
        self._credentials[server_key] = credential

    def delete(self, server_key: str) -> bool:
        return self._credentials.pop(server_key, None) is not None


class KeyringWaveKitCredentialStore:
    """Personal credential storage; no secret is written below a project root."""

    def __init__(self, *, service_name: str = "p2p-engine.wavekit") -> None:
        self.service_name = service_name

    def get(self, server_key: str) -> WaveKitCredential | None:
        keyring = self._keyring()
        try:
            payload = keyring.get_password(self.service_name, server_key)
        except Exception as exc:  # noqa: BLE001 - provider-specific backend errors.
            raise _unavailable(exc) from exc
        if payload is None:
            return None
        try:
            raw = json.loads(payload)
            if not isinstance(raw, dict):
                raise ValueError("credential payload is not a mapping")
            return WaveKitCredential(
                access_token=str(raw.get("access_token") or ""),
                refresh_token=str(raw.get("refresh_token") or ""),
                token_type=str(raw.get("token_type") or "Bearer"),
                expires_at=int(raw.get("expires_at") or 0),
                scopes=tuple(str(item) for item in raw.get("scopes", []) if str(item)),
                account_profile_ref=str(raw.get("account_profile_ref") or ""),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                "P2P_WAVEKIT_CREDENTIAL_INVALID: secure credential data is malformed"
            ) from exc

    def set(self, server_key: str, credential: WaveKitCredential) -> None:
        payload = json.dumps(
            {
                "access_token": credential.access_token,
                "refresh_token": credential.refresh_token,
                "token_type": credential.token_type,
                "expires_at": credential.expires_at,
                "scopes": list(credential.scopes),
                "account_profile_ref": credential.account_profile_ref,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            self._keyring().set_password(self.service_name, server_key, payload)
        except Exception as exc:  # noqa: BLE001 - provider-specific backend errors.
            raise _unavailable(exc) from exc

    def delete(self, server_key: str) -> bool:
        keyring = self._keyring()
        try:
            if keyring.get_password(self.service_name, server_key) is None:
                return False
            keyring.delete_password(self.service_name, server_key)
        except Exception as exc:  # noqa: BLE001 - provider-specific backend errors.
            raise _unavailable(exc) from exc
        return True

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:
            raise ValueError(
                "P2P_WAVEKIT_CREDENTIAL_STORE_UNAVAILABLE: install a supported OS keyring backend"
            ) from exc
        return keyring


def _unavailable(exc: Exception) -> ValueError:
    return ValueError(
        "P2P_WAVEKIT_CREDENTIAL_STORE_UNAVAILABLE: operating-system credential provider failed "
        f"({redact_secret(exc)})"
    )
