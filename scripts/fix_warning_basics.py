from datetime import datetime, UTC
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

INCLUDE_EXTENSIONS = {".py"}
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "htmlcov",
    ".pytest_cache",
    "dist",
    "build",
}

UTCNOW_PATTERN = re.compile(r"\bdatetime\.utcnow\(\)")
DECLARATIVE_IMPORT_PATTERN = re.compile(
    r"^from sqlalchemy\.ext\.declarative import declarative_base\s*$",
    re.MULTILINE,
)

DATETIME_IMPORT_RE = re.compile(
    r"^from datetime import (?P<imports>.+)$",
    re.MULTILINE,
)

CLASS_CONFIG_PATTERN = re.compile(r"^\s*class\s+Config\s*:", re.MULTILINE)
MIN_ITEMS_PATTERN = re.compile(r"\bmin_items\s*=")


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if should_skip(path):
            continue
        yield path


def ensure_utc_import(text: str) -> str:
    """
    Ensure `UTC` is imported when datetime.now(UTC) is used.
    Handles:
      - from datetime import datetime
      - from datetime import datetime, timezone
      - no datetime import at all
    """
    if "datetime.now(UTC)" not in text:
        return text

    match = DATETIME_IMPORT_RE.search(text)
    if match:
        imports_raw = match.group("imports")
        imports = [part.strip() for part in imports_raw.split(",")]
        if "UTC" not in imports:
            imports.append("UTC")
            new_line = f"from datetime import {', '.join(imports)}"
            text = (
                text[: match.start()]
                + new_line
                + text[match.end() :]
            )
        return text

    lines = text.splitlines()
    insert_at = 0

    if lines and lines[0].startswith("#!"):
        insert_at = 1

    while insert_at < len(lines) and (
        lines[insert_at].startswith("#")
        or lines[insert_at].strip() == ""
        or lines[insert_at].startswith('"""')
        or lines[insert_at].startswith("'''")
    ):
        insert_at += 1

    lines.insert(insert_at, "from datetime import datetime, UTC")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def fix_declarative_base_import(text: str) -> tuple[str, bool]:
    new_text, count = DECLARATIVE_IMPORT_PATTERN.subn(
        "from sqlalchemy.orm import declarative_base", text
    )
    return new_text, count > 0


def fix_datetime_utcnow(text: str) -> tuple[str, bool]:
    if "datetime.now(UTC)" not in text:
        return text, False

    new_text, count = UTCNOW_PATTERN.subn("datetime.now(UTC)", text)
    if count == 0:
        return text, False

    new_text = ensure_utc_import(new_text)
    return new_text, True


def analyze_pydantic_debt(text: str) -> dict[str, int]:
    return {
        "config_classes": len(CLASS_CONFIG_PATTERN.findall(text)),
        "min_items": len(MIN_ITEMS_PATTERN.findall(text)),
    }


def process_file(path: Path) -> dict[str, object]:
    original = path.read_text(encoding="utf-8")
    updated = original

    changed_rules: list[str] = []

    updated, declarative_changed = fix_declarative_base_import(updated)
    if declarative_changed:
        changed_rules.append("sqlalchemy_declarative_base")

    updated, utcnow_changed = fix_datetime_utcnow(updated)
    if utcnow_changed:
        changed_rules.append("datetime_utcnow")

    pydantic_debt = analyze_pydantic_debt(updated)

    changed = updated != original
    if changed:
        path.write_text(updated, encoding="utf-8")

    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "changed": changed,
        "changed_rules": changed_rules,
        "pydantic_config_classes": pydantic_debt["config_classes"],
        "pydantic_min_items": pydantic_debt["min_items"],
    }


def main() -> None:
    results = [process_file(path) for path in iter_python_files(REPO_ROOT)]

    changed = [r for r in results if r["changed"]]
    pydantic_flagged = [
        r
        for r in results
        if r["pydantic_config_classes"] or r["pydantic_min_items"]
    ]

    print("=== Warning Basics Worker Report ===")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Files scanned: {len(results)}")
    print(f"Files changed: {len(changed)}")
    print()

    if changed:
        print("Changed files:")
        for item in changed:
            rules = ", ".join(item["changed_rules"]) if item["changed_rules"] else "unknown"
            print(f"  - {item['path']} [{rules}]")
        print()
    else:
        print("No low-risk changes were needed.")
        print()

    if pydantic_flagged:
        print("Files still needing likely manual Pydantic cleanup:")
        for item in pydantic_flagged:
            parts = []
            if item["pydantic_config_classes"]:
                parts.append(f"Config classes={item['pydantic_config_classes']}")
            if item["pydantic_min_items"]:
                parts.append(f"min_length={item['pydantic_min_items']}")
            print(f"  - {item['path']} ({', '.join(parts)})")
        print()
    else:
        print("No obvious Pydantic cleanup targets found.")
        print()

    print("Done.")


if __name__ == "__main__":
    main()