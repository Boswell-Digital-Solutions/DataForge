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


def _all_setting_lines(key: str) -> list[list[str]]:
    lines = Path("render.yaml").read_text(encoding="utf-8").splitlines()
    marker = f"      - key: {key}"
    settings: list[list[str]] = []
    for index, line in enumerate(lines):
        if line != marker:
            continue
        setting = [line]
        for following in lines[index + 1 :]:
            if following.startswith("      - key:"):
                break
            setting.append(following)
        settings.append(setting)
    return settings


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


def test_render_declares_github_app_pair_for_each_private_dependency_build() -> None:
    for key in (
        "FORGE_PRIVATE_DEPS_APP_CLIENT_ID",
        "FORGE_PRIVATE_DEPS_APP_PRIVATE_KEY",
    ):
        settings = _all_setting_lines(key)
        assert len(settings) == 2
        for setting in settings:
            assert any("sync: false" in line for line in setting)
            assert not any(
                "value:" in line or "generateValue:" in line for line in setting
            )

    legacy_settings = _all_setting_lines("FORGE_TELEMETRY_TOKEN")
    assert len(legacy_settings) == 2
    assert all(
        any("Legacy" in line and "build-only" in line for line in setting)
        for setting in legacy_settings
    )
