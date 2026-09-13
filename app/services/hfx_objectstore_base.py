"""The HFX object-store adapter boundary for cloud DataForge.

Structural mirror of `dataforge-Local/execution_authority/objectstore/base.py`
(HFX-14E ruling A2-a: S3 API vocabulary, per-run content-addressed keys,
object-lock/WORM immutability). Duplicated rather than imported across the
repo boundary — cloud DataForge and dataforge-Local are separate deployable
systems with separate dependency graphs, per the ecosystem's authority
hierarchy (this repo owns cloud durable truth; dataforge-Local owns the local
execution substrate). The two adapters are structurally identical on purpose
so a caller written against one reads unsurprisingly against the other.

Two invariants belong to the *adapter*, not to its callers:

- **A finalized object is immutable.** `promote` refuses to overwrite one
  with different content. The S3 implementation of this interface enforces
  this with real Object Lock, not an approximation.
- **The store verifies digests itself.** `promote` recomputes the digest from
  the bytes it actually holds rather than trusting what it was told they
  were (`D16`: staged, server-verified, immutable, content-addressed).
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

# Opaque artifact bytes are digested as `sha256:<hex>`, not `rfc8785-sha256:`
# (that prefix names a digest over canonical JSON, and a model checkpoint is
# not JSON). `digest_hex` compares on the hex body so a `training_run_receipt`
# artifact digest still matches.
CONTENT_DIGEST_PREFIX = "sha256:"


class ObjectStoreError(Exception):
    """Base class for object-store faults."""


class ObjectNotFoundError(ObjectStoreError):
    """The requested key does not exist."""


class ObjectImmutableError(ObjectStoreError):
    """A finalized object may not be overwritten or removed."""


class DigestMismatchError(ObjectStoreError):
    """The bytes the store holds do not have the digest they were declared to."""

    def __init__(self, key: str, declared: str, actual: str) -> None:
        super().__init__(
            f"{key}: declared {declared}, but the stored bytes digest to {actual}"
        )
        self.key = key
        self.declared = declared
        self.actual = actual


@dataclass(frozen=True)
class ObjectInfo:
    """What the store knows about one object."""

    key: str
    size_bytes: int
    content_digest: str
    immutable: bool
    created_at: datetime


def content_digest(data: bytes) -> str:
    """`sha256:<hex>` over opaque bytes."""
    return CONTENT_DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def digest_hex(digest: str) -> str:
    """The bare hex body of a digest, whatever prefix it carries."""
    return digest.rsplit(":", 1)[-1].lower()


def digests_match(left: str, right: str) -> bool:
    """Whether two digests name the same bytes, ignoring prefix spelling."""
    left_hex, right_hex = digest_hex(left), digest_hex(right)
    return len(left_hex) == 64 and left_hex == right_hex


def staging_key(run_id: str, attempt_id: str, artifact_name: str) -> str:
    """Where an artifact lands before it has been verified.

    Namespaced per run and per attempt so a reassigned attempt cannot collide
    with the attempt it replaced.
    """
    return f"staging/runs/{run_id}/{attempt_id}/{artifact_name}"


def final_key(run_id: str, digest: str) -> str:
    """The immutable, content-addressed home of a verified artifact.

    Per-run namespace (A2-a): identical bytes produced by two different runs
    are stored twice on purpose, so one run's retention/deletion decision
    cannot silently reach into another's.
    """
    return f"runs/{run_id}/sha256/{digest_hex(digest)}"


class ObjectStoreAdapter(ABC):
    """The storage operations the HFX artifact lifecycle needs, and no others."""

    @abstractmethod
    def put_staged(self, key: str, data: bytes) -> ObjectInfo:
        """Write bytes to a staging key. Overwriting a staging key is allowed —
        a retried upload of the same artifact is normal."""

    @abstractmethod
    def stat(self, key: str) -> ObjectInfo | None:
        """Object metadata, or None if the key does not exist."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """The object's bytes. Raises `ObjectNotFoundError` if absent."""

    @abstractmethod
    def promote(self, staging_key: str, final_key: str, declared_digest: str) -> ObjectInfo:
        """Verify and move a staged object into immutable storage.

        Must recompute the digest from the stored bytes and raise
        `DigestMismatchError` if it disagrees with `declared_digest`. Must
        raise `ObjectImmutableError` rather than overwrite an existing
        finalized object whose content differs. Promoting the identical
        bytes twice is a no-op, so a retried finalize is safe.
        """

    @abstractmethod
    def delete_staged(self, key: str) -> bool:
        """Purge a staging object. Returns False if it was already gone.

        Must refuse to delete anything outside the staging area — an
        immutable object is not deletable through this interface at all
        (`D18`: deletion is an evidence state, not a storage operation).
        """

    @abstractmethod
    def is_immutable(self, key: str) -> bool:
        """Whether the key is under the store's immutability guarantee."""

    def digest_of(self, data: bytes) -> str:
        """The digest this store would compute for these bytes."""
        return content_digest(data)
