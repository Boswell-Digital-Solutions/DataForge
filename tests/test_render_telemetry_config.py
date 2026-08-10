"""Render blueprint coverage for canonical telemetry rollout controls."""

from pathlib import Path


def _web_service_block() -> str:
    text = Path("render.yaml").read_text(encoding="utf-8")
    return text.split("\n  # Scheduled pull", 1)[0]


def _setting_lines(key: str) -> list[str]:
    lines = _web_service_block().splitlines()
    marker = f"      - key: {key}"
    index = lines.index(marker)
    setting = [lines[index]]
    for line in lines[index + 1 :]:
        if line.startswith("      - key:"):
            break
        setting.append(line)
    return setting


def test_render_declares_telemetry_storage_and_rollout_controls_without_values() -> (
    None
):
    keys = (
        "DATAFORGE_TELEMETRY_DATABASE_URL",
        "DATAFORGE_FORGE_EVENT_V1_WRITE_ENABLED",
        "DATAFORGE_TELEMETRY_CORRELATION_READ_ENABLED",
    )

    for key in keys:
        setting = _setting_lines(key)
        assert any("sync: false" in line for line in setting)
        assert not any("value:" in line or "generateValue:" in line for line in setting)
