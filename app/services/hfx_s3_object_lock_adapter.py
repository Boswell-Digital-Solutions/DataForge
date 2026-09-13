"""The real S3 Object Lock implementation of `hfx_objectstore_base.ObjectStoreAdapter`.

HFX-14F Section 7 item 5 ("implement cloud DataForge execution-authority
parity and the S3 Object Lock/checksum/quarantine path"), packet 1 of the
sequencing proposed in `hephaestus/docs/design/
HFX-14F_cloud_dataforge_object_lock_architecture.md`: the adapter alone,
proven against a mockable S3 client, with no real bucket, no mounting, and
no caller. It does not create, configure, or assume any specific bucket
exists — `bucket`, `kms_key_id`, `object_lock_mode`, and
`object_lock_retain_days` are all caller-supplied so this module carries no
opinion about real infrastructure (that stays HFX-14F Section 7 item 7's
declarative-IaC deliverable).

This is a **mockable client** in the same sense Section 7 item 6 requires for
the SageMaker adapter: the constructor takes any object exposing the small
slice of the boto3 S3 client surface this module calls
(`put_object`/`get_object`/`head_object`/`delete_object`/
`get_object_retention`), so tests exercise the real adapter logic against a
hand-built fake client and never touch AWS or need network access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from app.services.hfx_objectstore_base import (
    DigestMismatchError,
    ObjectImmutableError,
    ObjectInfo,
    ObjectNotFoundError,
    ObjectStoreAdapter,
    ObjectStoreError,
    content_digest,
    digests_match,
)

STAGING_PREFIX = "staging/"
_SHA256_METADATA_KEY = "hfx-sha256"


class S3ClientProtocol(Protocol):
    """The exact boto3 S3 client surface this adapter calls, and no more."""

    def put_object(self, **kwargs: Any) -> Any: ...
    def get_object(self, **kwargs: Any) -> Any: ...
    def head_object(self, **kwargs: Any) -> Any: ...
    def delete_object(self, **kwargs: Any) -> Any: ...
    def get_object_retention(self, **kwargs: Any) -> Any: ...


def _is_staging(key: str) -> bool:
    return key.startswith(STAGING_PREFIX)


def _client_error_code(exc: Exception) -> str | None:
    """The botocore error code from a `ClientError`-shaped exception, if any.

    Duck-typed rather than importing `botocore.exceptions.ClientError`
    directly so a test fake can raise a lightweight lookalike without
    depending on botocore's exact exception construction.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    error = response.get("Error")
    if not isinstance(error, dict):
        return None
    code = error.get("Code")
    return code if isinstance(code, str) else None


_NOT_FOUND_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
_NO_RETENTION_CODES = frozenset(
    {"ObjectLockConfigurationNotFoundError", "NoSuchObjectLockConfiguration"}
)


class S3ObjectLockAdapter(ObjectStoreAdapter):
    """An S3 Object Lock-backed object store with the HFX adapter contract.

    Immutability is real, enforced by S3 Object Lock on the bucket and on
    every finalized object — not approximated, unlike dataforge-Local's
    filesystem fake adapter for the 14E phase.
    """

    def __init__(
        self,
        client: S3ClientProtocol,
        *,
        bucket: str,
        object_lock_mode: str,
        object_lock_retain_days: int,
        kms_key_id: str | None = None,
    ) -> None:
        if object_lock_mode not in ("GOVERNANCE", "COMPLIANCE"):
            raise ObjectStoreError(
                f"object_lock_mode must be GOVERNANCE or COMPLIANCE, got {object_lock_mode!r}"
            )
        if object_lock_retain_days < 1:
            raise ObjectStoreError("object_lock_retain_days must be at least 1")
        self._client = client
        self._bucket = bucket
        self._object_lock_mode = object_lock_mode
        self._object_lock_retain_days = object_lock_retain_days
        self._kms_key_id = kms_key_id

    # ── key handling ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_key(key: str) -> str:
        if not key or key.startswith("/"):
            raise ObjectStoreError(f"invalid object key {key!r}")
        return key

    def _put_kwargs(self, key: str, data: bytes) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": data,
            "Metadata": {_SHA256_METADATA_KEY: content_digest(data)[len("sha256:") :]},
        }
        if self._kms_key_id is not None:
            kwargs["ServerSideEncryption"] = "aws:kms"
            kwargs["SSEKMSKeyId"] = self._kms_key_id
        return kwargs

    def _head(self, key: str) -> dict[str, Any] | None:
        try:
            return self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 - re-raised narrowly below
            if _client_error_code(exc) in _NOT_FOUND_CODES:
                return None
            raise

    def _info_from_bytes(self, key: str, data: bytes) -> ObjectInfo:
        return ObjectInfo(
            key=key,
            size_bytes=len(data),
            content_digest=content_digest(data),
            immutable=self.is_immutable(key),
            created_at=datetime.now(UTC),
        )

    # ── adapter interface ────────────────────────────────────────────────

    def put_staged(self, key: str, data: bytes) -> ObjectInfo:
        self._validate_key(key)
        if not _is_staging(key):
            raise ObjectStoreError(
                f"{key!r} is not a staging key; only staged writes are accepted"
            )
        # No Object Lock on staging writes: a retried upload of the same
        # artifact must be able to overwrite its own staging copy.
        self._client.put_object(**self._put_kwargs(key, data))
        return self._info_from_bytes(key, data)

    def stat(self, key: str) -> ObjectInfo | None:
        self._validate_key(key)
        head = self._head(key)
        if head is None:
            return None
        data = self.read(key)
        return self._info_from_bytes(key, data)

    def read(self, key: str) -> bytes:
        self._validate_key(key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            if _client_error_code(exc) in _NOT_FOUND_CODES:
                raise ObjectNotFoundError(key) from exc
            raise
        body = response["Body"]
        return body.read() if hasattr(body, "read") else bytes(body)

    def promote(self, staging_key: str, final_key: str, declared_digest: str) -> ObjectInfo:
        self._validate_key(staging_key)
        self._validate_key(final_key)
        if not _is_staging(staging_key):
            raise ObjectStoreError(f"{staging_key!r} is not a staging key")
        if _is_staging(final_key):
            raise ObjectStoreError(f"{final_key!r} is a staging key, not a final one")

        # Server-side verification (D16): digest what we actually hold, not
        # what we were told we hold.
        try:
            staged_bytes = self.read(staging_key)
        except ObjectNotFoundError:
            raise

        actual = content_digest(staged_bytes)
        if not digests_match(actual, declared_digest):
            raise DigestMismatchError(staging_key, declared_digest, actual)

        existing_head = self._head(final_key)
        if existing_head is not None:
            existing_bytes = self.read(final_key)
            existing_digest = content_digest(existing_bytes)
            if digests_match(existing_digest, actual):
                # Content-addressed, so identical bytes at the same key. A
                # retried finalize is a no-op rather than an error.
                return self._info_from_bytes(final_key, existing_bytes)
            raise ObjectImmutableError(
                f"{final_key} already holds different content ({existing_digest}); "
                "a finalized object is never overwritten"
            )

        retain_until = datetime.now(UTC) + timedelta(days=self._object_lock_retain_days)
        put_kwargs = self._put_kwargs(final_key, staged_bytes)
        put_kwargs["ObjectLockMode"] = self._object_lock_mode
        put_kwargs["ObjectLockRetainUntilDate"] = retain_until
        self._client.put_object(**put_kwargs)

        self.delete_staged(staging_key)
        return self._info_from_bytes(final_key, staged_bytes)

    def delete_staged(self, key: str) -> bool:
        self._validate_key(key)
        if not _is_staging(key):
            raise ObjectImmutableError(
                f"{key!r} is not a staging key; a finalized object is not deletable "
                "through this interface"
            )
        if self._head(key) is None:
            return False
        self._client.delete_object(Bucket=self._bucket, Key=key)
        return True

    def is_immutable(self, key: str) -> bool:
        self._validate_key(key)
        if _is_staging(key):
            return False
        try:
            retention = self._client.get_object_retention(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            if _client_error_code(exc) in _NOT_FOUND_CODES | _NO_RETENTION_CODES:
                return False
            raise
        mode = retention.get("Retention", {}).get("Mode")
        return mode in ("GOVERNANCE", "COMPLIANCE")
