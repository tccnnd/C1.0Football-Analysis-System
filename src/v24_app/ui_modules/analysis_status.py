from __future__ import annotations


def build_analysis_status_text(
    *,
    base_status: str,
    gate_active: bool,
    allowed_count: int,
    active_allowed_count: int,
    parlay_count: int,
) -> str:
    if gate_active:
        status = f"{base_status} | C1放行 {active_allowed_count} 场"
    else:
        status = f"{base_status} | C1候选 {allowed_count} 场"
    if parlay_count > 0:
        status = f"{status} | 二串一 {parlay_count} 组"
    return status
