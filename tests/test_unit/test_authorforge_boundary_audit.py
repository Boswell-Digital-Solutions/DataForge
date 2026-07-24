"""The legacy-data audit reads identifiers and counts, never content columns."""

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from scripts.audit_authorforge_boundary import audit_authorforge_metadata


def test_metadata_audit_never_outputs_synthetic_content():
    audit_engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    projects = Table(
        "projects",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String),
        Column("description", String),
    )
    manuscripts = Table(
        "manuscripts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("content", String),
    )
    pressforge_campaigns = Table(
        "pf_campaigns",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String),
        Column("news_angle", String),
    )
    metadata.create_all(audit_engine)
    with audit_engine.begin() as connection:
        connection.execute(
            projects.insert(),
            {"id": 7, "name": "PRIVATE-PROJECT-NAME", "description": "PRIVATE-NOTES"},
        )
        connection.execute(
            manuscripts.insert(),
            {"id": 11, "content": "PRIVATE-MANUSCRIPT-CONTENT"},
        )
        connection.execute(
            pressforge_campaigns.insert(),
            {"id": 13, "title": "PRIVATE-BOOK-TITLE", "news_angle": "PRIVATE-ANGLE"},
        )

    report = audit_authorforge_metadata(audit_engine)
    rendered = str(report)

    assert report["read_only"] is True
    assert report["content_columns_read"] is False
    assert {item["category"] for item in report["potential_legacy_categories"]} == {
        "projects",
        "manuscripts",
        "pressforge_linked/campaigns",
    }
    assert "'record_count': 1" in rendered
    assert "'record_ids': ['7']" in rendered
    assert "'record_ids': ['11']" in rendered
    assert "'record_ids': ['13']" in rendered
    assert "PRIVATE-PROJECT-NAME" not in rendered
    assert "PRIVATE-NOTES" not in rendered
    assert "PRIVATE-MANUSCRIPT-CONTENT" not in rendered
    assert "PRIVATE-BOOK-TITLE" not in rendered
    assert "PRIVATE-ANGLE" not in rendered
