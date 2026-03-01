"""
Tests for corpus version governance.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import models
from app.utils.corpus_versioning import bump_corpus_version_sync, get_current_corpus_version_sync


def _build_corpus_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.CorpusState.__table__.create(bind=engine)
    models.CorpusVersion.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    session.add(models.CorpusState(id=1, current_version=1))
    session.add(models.CorpusVersion(version=1, trigger_event="initial", trigger_entity_id=None))
    session.commit()
    return session


def test_bump_corpus_version_sync_is_monotonic() -> None:
    session = _build_corpus_session()
    try:
        first = bump_corpus_version_sync(session, "doc_insert", 101)
        second = bump_corpus_version_sync(session, "chunk_insert", 101)
        session.commit()

        assert first == 2
        assert second == 3
        assert get_current_corpus_version_sync(session) == 3
    finally:
        session.close()


def test_corpus_version_audit_rows_are_appended() -> None:
    session = _build_corpus_session()
    try:
        bump_corpus_version_sync(session, "doc_delete", 7)
        session.commit()

        versions = (
            session.query(models.CorpusVersion)
            .order_by(models.CorpusVersion.version.asc())
            .all()
        )

        assert versions[0].version == 1
        assert versions[-1].version == 2
        assert versions[-1].trigger_event == "doc_delete"
        assert versions[-1].trigger_entity_id == 7
    finally:
        session.close()
