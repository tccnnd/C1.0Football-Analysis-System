from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "runtime_mode.yaml"
SUPPORTED_MODES = {"shadow", "gate_only", "formal_list_default", "c1_primary"}
SUPPORTED_GUARD_POLICIES = {"fail_open", "fail_close"}
DEFAULT_GUARD_POLICY_BY_MODE = {
    "shadow": "fail_open",
    "gate_only": "fail_close",
    "formal_list_default": "fail_close",
    "c1_primary": "fail_close",
}

# c1_primary 验收门槛：未达标时运行时拒绝以 c1_primary 运行。
# 这是防回归的硬约束——即使有人手动把 YAML 改回 c1_primary，
# 只要 switch_log.validation 不满足这些条件，运行时也会降级到 formal_list_default。
C1_PRIMARY_MIN_GOVERNANCE_SEPARATION = 0.05
C1_PRIMARY_DOWNGRADE_FALLBACK = "formal_list_default"


def load_runtime_mode_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid runtime mode config: {config_path}")
    return payload


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def evaluate_c1_primary_acceptance(config: Mapping[str, Any]) -> dict[str, Any]:
    """检查 c1_primary 验收条件是否满足。

    依据 switch_log.validation 中记录的 shadow run 指标：
    - accuracy_c1 >= accuracy_v24
    - governance_separation >= 0.05

    返回 {'accepted': bool, 'unmet': [...], 'validation': {...}}。
    缺少 validation 数据时视为未达标（保守 fail-close）。
    """
    switch_log = config.get("switch_log") if isinstance(config, Mapping) else None
    validation = switch_log.get("validation") if isinstance(switch_log, Mapping) else None
    if not isinstance(validation, Mapping):
        return {"accepted": False, "unmet": ["missing_validation_data"], "validation": {}}

    acc_c1 = _safe_float(validation.get("accuracy_c1"), -1.0)
    acc_v24 = _safe_float(validation.get("accuracy_v24"), 0.0)
    separation = _safe_float(validation.get("governance_separation"), -1.0)

    unmet: list[str] = []
    if acc_c1 < acc_v24:
        unmet.append(f"accuracy_c1({acc_c1:.3f}) < accuracy_v24({acc_v24:.3f})")
    if separation < C1_PRIMARY_MIN_GOVERNANCE_SEPARATION:
        unmet.append(
            f"governance_separation({separation:.3f}) < {C1_PRIMARY_MIN_GOVERNANCE_SEPARATION}"
        )
    return {"accepted": not unmet, "unmet": unmet, "validation": dict(validation)}


def get_runtime_mode(path: str | Path | None = None) -> str:
    config = load_runtime_mode_config(path)
    mode = str(config.get("mode", "shadow")).strip()
    if mode not in SUPPORTED_MODES:
        return "shadow"
    # 防回归门槛：c1_primary 必须通过验收条件，否则降级。
    if mode == "c1_primary":
        acceptance = evaluate_c1_primary_acceptance(config)
        if not acceptance["accepted"]:
            return C1_PRIMARY_DOWNGRADE_FALLBACK
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

    # 防回归 guard：即使显式传入 runtime_mode='c1_primary'，
    # 也必须通过验收条件，否则降级（与 get_runtime_mode 行为一致）。
    mode_downgraded_from: str | None = None
    if mode == "c1_primary":
        acceptance = evaluate_c1_primary_acceptance(payload)
        if not acceptance["accepted"]:
            mode_downgraded_from = "c1_primary"
            mode = C1_PRIMARY_DOWNGRADE_FALLBACK

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
    result = {
        "provider_name": str(provider_name),
        "runtime_mode": mode,
        "policy": policy,
        "policy_source": source,
    }
    if mode_downgraded_from is not None:
        result["mode_downgraded_from"] = mode_downgraded_from
    return result


def get_default_ui_filter(mode: str, *, has_formal_rows: bool) -> str:
    normalized = str(mode or "shadow").strip()
    if normalized in {"formal_list_default", "c1_primary"} and has_formal_rows:
        return "正式建议"
    return "全部"


def is_release_gate_active(mode: str) -> bool:
    normalized = str(mode or "shadow").strip()
    return normalized in {"gate_only", "formal_list_default", "c1_primary"}


def is_c1_primary(mode: str) -> bool:
    """C1.0 是否作为主决策引擎"""
    return str(mode or "").strip() == "c1_primary"
