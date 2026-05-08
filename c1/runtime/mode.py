from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "runtime_mode.yaml"
SUPPORTED_MODES = {"shadow", "gate_only", "formal_list_default"}


def load_runtime_mode_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid runtime mode config: {config_path}")
    return payload


def get_runtime_mode(path: str | Path | None = None) -> str:
    config = load_runtime_mode_config(path)
    mode = str(config.get("mode", "shadow")).strip()
    if mode not in SUPPORTED_MODES:
        return "shadow"
    return mode


def get_default_ui_filter(mode: str, *, has_formal_rows: bool) -> str:
    normalized = str(mode or "shadow").strip()
    if normalized == "formal_list_default" and has_formal_rows:
        return "正式建议"
    return "全部"


def is_release_gate_active(mode: str) -> bool:
    normalized = str(mode or "shadow").strip()
    return normalized in {"gate_only", "formal_list_default"}
