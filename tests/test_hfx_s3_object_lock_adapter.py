"""Hermetic proof for the unmounted HFX S3 Object Lock adapter.

No AWS, no network, no credentials: `FakeS3Client` is a small in-memory
stand-in for the exact boto3 S3 surface `S3ObjectLockAdapter` calls, built to
mimic real S3 Object Lock semantics (a locked object refuses a direct
overwrite) closely enough to prove the adapter's own pre-checks are not the
only thing standing between it and data loss.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

import pytest

from app.services.hfx_objectstore_base import (
    DigestMismatchError,
    ObjectImmutableError,
    ObjectNotFoundError,
    ObjectStoreError,
    content_digest,
    digest_hex,
    digests_match,
    final_key,
    staging_key,
)
from app.services.hfx_s3_object_lock_adapter import S3ObjectLockAdapter


class _FakeClientError(Exception):
    def __init__(self, code: str) -> None:
        self.response: dict[str, Any] = {"Error": {"Code": code}}
        super().__init__(code)


class _FakeObject:
    def __init__(self, body: bytes, metadata: dict[str, str], lock_mode: str | None) -> None:
        self.body = body
        self.metadata = metadata
        self.lock_mode = lock_mode


class FakeS3Client:
    """An in-memory fake of the boto3 S3 client surface, nothing more."""

    def __init__(self) -> None:
        self._objects: dict[str, _FakeObject] = {}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        Metadata: dict[str, str] | None = None,
        ObjectLockMode: str | None = None,
        ObjectLockRetainUntilDate: datetime | None = None,
        ServerSideEncryption: str | None = None,
        SSEKMSKeyId: str | None = None,
    ) -> dict[str, Any]:
        existing = self._objects.get(Key)
        if existing is not None and existing.lock_mode is not None:
            # Real S3 Object Lock refuses this at the storage layer; the fake
            # mirrors that rather than trusting the adapter's own pre-check.
            raise _FakeClientError("AccessDenied")
        self._objects[Key] = _FakeObject(bytes(Body), dict(Metadata or {}), ObjectLockMode)
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        obj = self._objects.get(Key)
        if obj is None:
            raise _FakeClientError("NoSuchKey")
        return {"Body": io.BytesIO(obj.body)}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        obj = self._objects.get(Key)
        if obj is None:
            raise _FakeClientError("404")
        return {"ContentLength": len(obj.body), "Metadata": obj.metadata}

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._objects.pop(Key, None)
        return {}

    def get_object_retention(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        obj = self._objects.get(Key)
        if obj is None or obj.lock_mode is None:
            raise _FakeClientError("ObjectLockConfigurationNotFoundError")
        return {"Retention": {"Mode": obj.lock_mode, "RetainUntilDate": datetime.now(UTC)}}


@pytest.fixture
def client() -> FakeS3Client:
    return FakeS3Client()


@pytest.fixture
def store(client: FakeS3Client) -> S3ObjectLockAdapter:
    return S3ObjectLockAdapter(
        client,
        bucket="hfx-artifacts-test",
        object_lock_mode="COMPLIANCE",
        object_lock_retain_days=30,
    )


class TestDigests:
    def test_content_digest_is_sha256_of_the_bytes(self) -> None:
        assert content_digest(b"abc").startswith("sha256:")

    def test_digests_match_across_prefix_spellings(self) -> None:
        raw = content_digest(b"abc")
        assert digests_match(raw, "rfc8785-sha256:" + digest_hex(raw))

    def test_different_bytes_do_not_match(self) -> None:
        assert not digests_match(content_digest(b"abc"), content_digest(b"xyz"))

    def test_a_malformed_digest_never_matches(self) -> None:
        assert not digests_match(content_digest(b"abc"), "sha256:not-hex")


class TestKeyLayout:
    def test_staging_is_namespaced_per_run_and_attempt(self) -> None:
        assert staging_key("run-1", "attempt-1", "model.bin") == (
            "staging/runs/run-1/attempt-1/model.bin"
        )

    def test_final_keys_are_content_addressed_under_the_run(self) -> None:
        digest = content_digest(b"weights")
        assert final_key("run-1", digest) == f"runs/run-1/sha256/{digest_hex(digest)}"

    def test_identical_bytes_in_two_runs_get_two_keys(self) -> None:
        digest = content_digest(b"weights")
        assert final_key("run-1", digest) != final_key("run-2", digest)


class TestStaging:
    def test_staged_bytes_read_back(self, store: S3ObjectLockAdapter) -> None:
        key = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(key, b"weights")
        assert store.read(key) == b"weights"

    def test_a_staging_key_may_be_overwritten(self, store: S3ObjectLockAdapter) -> None:
        key = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(key, b"first")
        store.put_staged(key, b"second")
        assert store.read(key) == b"second"

    def test_writing_outside_staging_is_refused(self, store: S3ObjectLockAdapter) -> None:
        with pytest.raises(ObjectStoreError):
            store.put_staged("runs/run-1/sha256/deadbeef", b"weights")

    def test_stat_of_a_missing_key_is_none(self, store: S3ObjectLockAdapter) -> None:
        assert store.stat(staging_key("run-1", "attempt-1", "absent.bin")) is None

    def test_reading_a_missing_key_raises(self, store: S3ObjectLockAdapter) -> None:
        with pytest.raises(ObjectNotFoundError):
            store.read(staging_key("run-1", "attempt-1", "absent.bin"))


class TestPromotion:
    def test_promotion_verifies_and_moves(self, store: S3ObjectLockAdapter) -> None:
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        digest = content_digest(b"weights")
        destination = final_key("run-1", digest)

        info = store.promote(source, destination, digest)

        assert info.content_digest == digest
        assert store.read(destination) == b"weights"
        assert store.stat(source) is None  # staging purged on finalize

    def test_a_digest_mismatch_is_refused(self, store: S3ObjectLockAdapter) -> None:
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        with pytest.raises(DigestMismatchError):
            store.promote(source, final_key("run-1", content_digest(b"other")), content_digest(b"other"))

    def test_promoting_identical_bytes_twice_is_a_no_op(self, store: S3ObjectLockAdapter) -> None:
        source = staging_key("run-1", "attempt-1", "model.bin")
        digest = content_digest(b"weights")
        destination = final_key("run-1", digest)

        store.put_staged(source, b"weights")
        store.promote(source, destination, digest)

        store.put_staged(source, b"weights")
        info = store.promote(source, destination, digest)
        assert info.content_digest == digest

    def test_a_finalized_object_is_never_overwritten_with_different_content(
        self, store: S3ObjectLockAdapter
    ) -> None:
        # A caller-supplied final key that is not re-derived from the new
        # content's own digest — the scenario the immutability guard exists
        # for for content-addressed storage: strict re-derivation would give
        # different bytes a different key on its own, so this exercises what
        # happens when a caller (bug or misuse) reuses one anyway.
        destination = "runs/run-1/sha256/fixed-slot"

        first = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(first, b"weights")
        store.promote(first, destination, content_digest(b"weights"))

        second = staging_key("run-1", "attempt-2", "model.bin")
        store.put_staged(second, b"different-weights")
        with pytest.raises(ObjectImmutableError):
            store.promote(second, destination, content_digest(b"different-weights"))

    def test_the_fake_storage_layer_itself_refuses_a_direct_overwrite(
        self, client: FakeS3Client, store: S3ObjectLockAdapter
    ) -> None:
        """Real S3 Object Lock enforcement, not just the adapter's pre-check."""
        digest = content_digest(b"weights")
        destination = final_key("run-1", digest)
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        store.promote(source, destination, digest)

        with pytest.raises(_FakeClientError):
            client.put_object(Bucket="hfx-artifacts-test", Key=destination, Body=b"tampered")

    def test_promoting_a_missing_staging_object_raises(self, store: S3ObjectLockAdapter) -> None:
        with pytest.raises(ObjectNotFoundError):
            store.promote(
                staging_key("run-1", "attempt-1", "absent.bin"),
                final_key("run-1", content_digest(b"x")),
                content_digest(b"x"),
            )

    def test_promoting_from_a_non_staging_key_is_refused(self, store: S3ObjectLockAdapter) -> None:
        with pytest.raises(ObjectStoreError):
            store.promote(
                "runs/run-1/sha256/deadbeef",
                final_key("run-1", content_digest(b"x")),
                content_digest(b"x"),
            )

    def test_promoting_into_staging_is_refused(self, store: S3ObjectLockAdapter) -> None:
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        with pytest.raises(ObjectStoreError):
            store.promote(source, staging_key("run-1", "attempt-1", "other.bin"), content_digest(b"weights"))


class TestDeletion:
    def test_staged_bytes_can_be_purged(self, store: S3ObjectLockAdapter) -> None:
        key = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(key, b"weights")
        assert store.delete_staged(key) is True
        assert store.stat(key) is None

    def test_purging_an_absent_staging_object_is_not_an_error(self, store: S3ObjectLockAdapter) -> None:
        assert store.delete_staged(staging_key("run-1", "attempt-1", "absent.bin")) is False

    def test_a_finalized_object_is_not_deletable_through_this_interface(
        self, store: S3ObjectLockAdapter
    ) -> None:
        digest = content_digest(b"weights")
        destination = final_key("run-1", digest)
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        store.promote(source, destination, digest)

        with pytest.raises(ObjectImmutableError):
            store.delete_staged(destination)


class TestImmutabilityIsReal:
    def test_staging_is_never_immutable(self, store: S3ObjectLockAdapter) -> None:
        key = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(key, b"weights")
        assert store.is_immutable(key) is False

    def test_a_missing_key_is_not_immutable(self, store: S3ObjectLockAdapter) -> None:
        assert store.is_immutable(final_key("run-1", content_digest(b"x"))) is False

    def test_a_finalized_object_reports_immutable_via_real_object_lock_retention(
        self, store: S3ObjectLockAdapter
    ) -> None:
        digest = content_digest(b"weights")
        destination = final_key("run-1", digest)
        source = staging_key("run-1", "attempt-1", "model.bin")
        store.put_staged(source, b"weights")
        store.promote(source, destination, digest)

        assert store.is_immutable(destination) is True


class TestConstruction:
    def test_an_invalid_object_lock_mode_is_refused(self, client: FakeS3Client) -> None:
        with pytest.raises(ObjectStoreError):
            S3ObjectLockAdapter(
                client, bucket="b", object_lock_mode="NONE", object_lock_retain_days=30
            )

    def test_a_non_positive_retention_period_is_refused(self, client: FakeS3Client) -> None:
        with pytest.raises(ObjectStoreError):
            S3ObjectLockAdapter(
                client, bucket="b", object_lock_mode="COMPLIANCE", object_lock_retain_days=0
            )


class TestKeyValidation:
    @pytest.mark.parametrize("bad_key", ["", "/leading-slash"])
    def test_read_refuses_an_invalid_key(self, store: S3ObjectLockAdapter, bad_key: str) -> None:
        with pytest.raises(ObjectStoreError):
            store.read(bad_key)

    @pytest.mark.parametrize("bad_key", ["", "/leading-slash"])
    def test_stat_refuses_an_invalid_key(self, store: S3ObjectLockAdapter, bad_key: str) -> None:
        with pytest.raises(ObjectStoreError):
            store.stat(bad_key)

    @pytest.mark.parametrize("bad_key", ["", "/leading-slash"])
    def test_is_immutable_refuses_an_invalid_key(
        self, store: S3ObjectLockAdapter, bad_key: str
    ) -> None:
        with pytest.raises(ObjectStoreError):
            store.is_immutable(bad_key)


class TestKmsAndErrorPropagation:
    def test_kms_key_id_is_forwarded_on_put(self, client: FakeS3Client) -> None:
        calls: list[dict[str, Any]] = []
        original_put = client.put_object

        def _spy_put(**kwargs: Any) -> Any:
            calls.append(kwargs)
            return original_put(**kwargs)

        client.put_object = _spy_put  # type: ignore[method-assign]
        store = S3ObjectLockAdapter(
            client,
            bucket="b",
            object_lock_mode="COMPLIANCE",
            object_lock_retain_days=30,
            kms_key_id="arn:aws:kms:us-east-2:000000000000:key/fake",
        )
        store.put_staged(staging_key("run-1", "attempt-1", "model.bin"), b"weights")

        assert calls[0]["ServerSideEncryption"] == "aws:kms"
        assert calls[0]["SSEKMSKeyId"] == "arn:aws:kms:us-east-2:000000000000:key/fake"

    def test_an_unexpected_head_error_is_not_swallowed(self, store: S3ObjectLockAdapter) -> None:
        def _boom(**kwargs: Any) -> Any:
            raise _FakeClientError("InternalError")

        store._client.head_object = _boom  # type: ignore[method-assign]
        with pytest.raises(_FakeClientError):
            store.stat(staging_key("run-1", "attempt-1", "model.bin"))

    def test_an_unexpected_get_error_is_not_swallowed(self, store: S3ObjectLockAdapter) -> None:
        def _boom(**kwargs: Any) -> Any:
            raise _FakeClientError("InternalError")

        store._client.get_object = _boom  # type: ignore[method-assign]
        with pytest.raises(_FakeClientError):
            store.read(staging_key("run-1", "attempt-1", "model.bin"))

    def test_an_unexpected_retention_error_is_not_swallowed(
        self, store: S3ObjectLockAdapter
    ) -> None:
        def _boom(**kwargs: Any) -> Any:
            raise _FakeClientError("InternalError")

        store._client.get_object_retention = _boom  # type: ignore[method-assign]
        with pytest.raises(_FakeClientError):
            store.is_immutable(final_key("run-1", content_digest(b"x")))
