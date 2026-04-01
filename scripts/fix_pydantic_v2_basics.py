from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

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

PYDANTIC_IMPORT_RE = re.compile(
    r"^from pydantic import (?P<imports>.+)$",
    re.MULTILINE,
)

FIELD_MIN_ITEMS_RE = re.compile(r"\bmin_items\s*=")
FIELD_MAX_ITEMS_RE = re.compile(r"\bmax_items\s*=")


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        if should_skip(path):
            continue
        yield path


def ensure_configdict_import(text: str) -> str:
    match = PYDANTIC_IMPORT_RE.search(text)
    if match:
        imports = [part.strip() for part in match.group("imports").split(",")]
        if "ConfigDict" not in imports:
            imports.append("ConfigDict")
            new_line = f"from pydantic import {', '.join(imports)}"
            text = text[: match.start()] + new_line + text[match.end() :]
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

    lines.insert(insert_at, "from pydantic import ConfigDict")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def replace_field_item_lengths(text: str) -> tuple[str, bool]:
    updated = FIELD_MIN_ITEMS_RE.sub("min_length=", text)
    updated = FIELD_MAX_ITEMS_RE.sub("max_length=", updated)
    return updated, updated != text


def extract_simple_config_mapping(config_node: ast.ClassDef) -> dict[str, str] | None:
    config: dict[str, str] = {}

    for stmt in config_node.body:
        if not isinstance(stmt, ast.Assign):
            return None
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            return None

        key = stmt.targets[0].id

        value = stmt.value
        if isinstance(value, ast.Constant):
            config[key] = repr(value.value)
        elif isinstance(value, ast.Name):
            config[key] = value.id
        elif isinstance(value, ast.Attribute):
            try:
                config[key] = ast.unparse(value)
            except Exception:
                return None
        elif isinstance(value, (ast.Dict, ast.List, ast.Tuple)):
            try:
                config[key] = ast.unparse(value)
            except Exception:
                return None
        else:
            try:
                config[key] = ast.unparse(value)
            except Exception:
                return None

    return config


def get_line_start_offsets(text: str) -> list[int]:
    offsets = [0]
    running = 0
    for line in text.splitlines(keepends=True):
        running += len(line)
        offsets.append(running)
    return offsets


def line_col_to_offset(offsets: list[int], lineno: int, col: int) -> int:
    return offsets[lineno - 1] + col


def replace_class_config_blocks(text: str) -> tuple[str, bool, list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text, False, []

    offsets = get_line_start_offsets(text)
    replacements: list[tuple[int, int, str]] = []
    manual_review: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        config_node = None
        insert_after_node = None

        for stmt in node.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
                config_node = stmt
            if not isinstance(stmt, ast.ClassDef):
                insert_after_node = stmt

        if config_node is None:
            continue

        config_map = extract_simple_config_mapping(config_node)
        if config_map is None:
            manual_review.append(node.name)
            continue

        kwargs = ", ".join(f"{key}={value}" for key, value in config_map.items())
        indent = " " * 4
        replacement_line = f"{indent}model_config = ConfigDict({kwargs})\n"

        config_start = line_col_to_offset(offsets, config_node.lineno, config_node.col_offset)
        config_end = line_col_to_offset(offsets, config_node.end_lineno, config_node.end_col_offset)

        original_block = text[config_start:config_end]
        trailing = ""
        if not original_block.endswith("\n"):
            trailing = "\n"

        replacements.append((config_start, config_end, replacement_line.rstrip("\n") + trailing))

    if not replacements:
        return text, False, manual_review

    updated = text
    for start, end, replacement in sorted(replacements, reverse=True):
        updated = updated[:start] + replacement + updated[end:]

    return updated, updated != text, manual_review


def process_file(path: Path) -> dict[str, object]:
    original = path.read_text(encoding="utf-8")
    updated = original

    changed_rules: list[str] = []
    manual_review: list[str] = []

    updated, field_changed = replace_field_item_lengths(updated)
    if field_changed:
        changed_rules.append("field_items_to_lengths")

    updated, config_changed, flagged_classes = replace_class_config_blocks(updated)
    if flagged_classes:
        manual_review.extend(flagged_classes)

    if config_changed:
        updated = ensure_configdict_import(updated)
        changed_rules.append("class_config_to_configdict")

    changed = updated != original
    if changed:
        path.write_text(updated, encoding="utf-8")

    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "changed": changed,
        "changed_rules": changed_rules,
        "manual_review": manual_review,
    }


def main() -> None:
    results = [process_file(path) for path in iter_python_files(REPO_ROOT)]

    changed = [r for r in results if r["changed"]]
    flagged = [r for r in results if r["manual_review"]]

    print("=== Pydantic V2 Basics Worker Report ===")
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
        print("No automatic Pydantic V2 basic changes were needed.")
        print()

    if flagged:
        print("Files/classes needing manual review:")
        for item in flagged:
            classes = ", ".join(item["manual_review"])
            print(f"  - {item['path']} :: {classes}")
        print()
    else:
        print("No manual-review Config blocks were detected.")
        print()

    print("Done.")


if __name__ == "__main__":
    main()