from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "runtime_mode.yaml"
SUPPORTED_MODES = {"shadow", "gate_only", "formal_list_default"}
SUPPORTED_GUARD_POLICIES = {"fail_open", "fail_close"}
DEFAULT_GUARD_POLICY_BY_MODE = {
    "shadow": "fail_open",
    "gate_only": "fail_close",
    "formal_list_default": "fail_close",
}


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


def _normalize_guard_policy(value: Any, default: str = "fail_close") -> str:
    policy = str(value or "").strip().lower()
    if policy in SUPPORTED_GUARD_POLICIES:
        return policy
    fallback = str(default or "").strip().lower()
    if fallback in SUPPORTED_GUARD_POLICIES:
        return fallback
    return "fail_close"


def _resolve_guard_policy_from_rule(rule: Any, mode: str) -> str:
    if isinstance(rule, str):
        return _normalize_guard_policy(rule)
    if not isinstance(rule, Mapping):
        return ""
    for key in (mode, "default", "policy"):
        value = rule.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, Mapping):
            nested = _resolve_guard_policy_from_rule(value, mode)
            if nested:
                return nested
            continue
        return _normalize_guard_policy(value)
    return ""


def get_provider_guard_policy(
    provider_name: str,
    *,
    runtime_mode: str | None = None,
    path: str | Path | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(runtime_mode or "").strip()
    if mode not in SUPPORTED_MODES:
        mode = get_runtime_mode(path)
    payload = dict(config) if config is not None else load_runtime_mode_config(path)
    guard_rails = payload.get("guard_rails", {})
    default_rule = {}
    provider_rule = {}
    if isinstance(guard_rails, Mapping):
        default_rule = guard_rails.get("default_provider_policy", guard_rails.get("default", {}))
        providers = guard_rails.get("providers", {})
        if isinstance(providers, Mapping):
            provider_rule = providers.get(str(provider_name), {}) or {}

    policy = _resolve_guard_policy_from_rule(provider_rule, mode)
    source = "provider"
    if not policy:
        policy = _resolve_guard_policy_from_rule(default_rule, mode)
        source = "default"
    if not policy:
        policy = DEFAULT_GUARD_POLICY_BY_MODE.get(mode, "fail_close")
        source = "fallback"
    policy = _normalize_guard_policy(policy)
    return {
        "provider_name": str(provider_name),
        "runtime_mode": mode,
        "policy": policy,
        "policy_source": source,
    }


def get_default_ui_filter(mode: str, *, has_formal_rows: bool) -> str:
    normalized = str(mode or "shadow").strip()
    if normalized == "formal_list_default" and has_formal_rows:
        return "正式建议"
    return "全部"


def is_release_gate_active(mode: str) -> bool:
    normalized = str(mode or "shadow").strip()
    return normalized in {"gate_only", "formal_list_default"}
