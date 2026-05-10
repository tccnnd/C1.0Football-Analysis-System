from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from c1.data import (
    AvailabilityProviderChain,
    C1AvailabilityStore,
    build_availability_template_rows,
    export_availability_template_csv,
    load_rows_from_file,
)


def _build_provider_error_hint(item: Mapping[str, object]) -> str:
    status = str(item.get("status", "")).strip().lower()
    error = str(item.get("error", "")).strip()
    fixtures_errors = item.get("fixtures_errors")
    fixture_error_text = ""
    if isinstance(fixtures_errors, list):
        fixture_error_text = " | ".join(str(x) for x in fixtures_errors if str(x).strip())
    suspended_text = f"{error} {fixture_error_text}".lower()
    if "suspended" in suspended_text or "account is suspended" in suspended_text:
        return "API-Football 账号已被暂停，请到 dashboard 恢复账号或更换可用 key。"
    if status in {"ready", "ok", "imported", "empty"}:
        return ""
    if "winerror 10013" in error.lower() or "访问权限不允许" in error:
        return "网络权限拦截（WinError 10013），请放通目标域名 443 出站连接。"
    if "timed out" in error.lower():
        return "请求超时，建议检查网络质量或增大超时阈值。"
    if "name or service not known" in error.lower() or "nodename nor servname provided" in error.lower():
        return "DNS 解析失败，请检查本机 DNS 或代理配置。"
    if status == "sync_skipped":
        return "该源仅用于本地兜底，不参与上游同步。"
    if status == "error":
        return "源异常，已自动降级到后续可用数据源。"
    return ""


def export_c1_availability_template(matches: list[Any], target: Path) -> dict:
    rows = build_availability_template_rows(matches)
    path = export_availability_template_csv(target, rows)
    return {"rows": len(rows), "path": str(path)}


def import_c1_availability_snapshots(project_root: Path, source: Path, *, replace: bool = False) -> dict:
    rows = load_rows_from_file(source)
    store = C1AvailabilityStore(project_root)
    result = store.import_rows(rows, replace=replace)
    result["source"] = str(source)
    return result


def sync_c1_availability_sources(project_root: Path, *, replace: bool = False) -> dict:
    chain = AvailabilityProviderChain.from_project_root(project_root)
    return chain.sync_to_store(project_root, replace=replace)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_allowed_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"false", "0", "no", "off"}:
        return False
    return True


def build_c1_release_review_availability_guard(sync_summary: Mapping[str, object] | None) -> dict:
    summary = sync_summary if isinstance(sync_summary, Mapping) else {}
    smoke = summary.get("smoke_check") if isinstance(summary.get("smoke_check"), Mapping) else {}
    smoke_status = str(smoke.get("status") or ("missing" if not smoke else "-")).strip().lower()
    release_review_allowed = _safe_allowed_flag(smoke.get("release_review_allowed", True))
    quality_failures = _safe_int(summary.get("quality_failures", 0))
    quality_warnings = _safe_int(summary.get("quality_warnings", 0))

    blocked = not release_review_allowed or smoke_status == "fail" or quality_failures > 0
    issues: list[str] = []
    smoke_issues = smoke.get("issues") if isinstance(smoke.get("issues"), list) else []
    provider_reasons = (
        summary.get("provider_failure_reasons") if isinstance(summary.get("provider_failure_reasons"), list) else []
    )
    for value in [*smoke_issues, *provider_reasons]:
        text = str(value).strip()
        if text and text not in issues:
            issues.append(text)
    if blocked and not issues:
        issues.append("availability quality gate failed")

    status_text = "C1 放行评估已阻止 | 阵容源质量门控失败" if blocked else "C1 放行评估门控通过"
    if not blocked and smoke_status in {"warn", "missing"}:
        status_text = f"C1 放行评估门控可运行 | smoke={smoke_status}"

    message_lines = [
        "C1 阵容源质量门控未通过，已跳过本次放行评估。"
        if blocked
        else "C1 阵容源质量门控允许本次放行评估。",
        f"Smoke: {smoke_status or '-'}",
        f"Quality fail/warn: {quality_failures}/{quality_warnings}",
    ]
    if issues:
        message_lines.append("原因:")
        message_lines.extend(f"- {item}" for item in issues[:8])
    if blocked:
        message_lines.append("请先重新同步 C1 阵容源，或修复失败数据源后再运行放行评估。")

    return {
        "allowed": not blocked,
        "status": smoke_status or "-",
        "quality_failures": quality_failures,
        "quality_warnings": quality_warnings,
        "issues": issues,
        "status_text": status_text,
        "message": "\n".join(message_lines),
    }


def build_c1_release_review_guard_status_text(guard: Mapping[str, object] | None) -> str:
    item = guard if isinstance(guard, Mapping) else {}
    status = str(item.get("status") or "-").strip().lower()
    fail = _safe_int(item.get("quality_failures", 0))
    warn = _safe_int(item.get("quality_warnings", 0))
    if not bool(item.get("allowed", True)):
        return f"放行门控: 阻止 | smoke={status} | fail/warn={fail}/{warn}"
    if status == "pass":
        return "放行门控: 通过"
    if status in {"warn", "missing"}:
        return f"放行门控: 可运行 | smoke={status}"
    return f"放行门控: 可运行 | smoke={status or '-'}"


def build_c1_release_guard_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"c1_release_guard_block_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_c1_release_guard_report_lines(
    guard: Mapping[str, object] | None,
    *,
    matches_count: int,
    generated_at: datetime | None = None,
) -> list[str]:
    item = guard if isinstance(guard, Mapping) else {}
    issues = item.get("issues") if isinstance(item.get("issues"), list) else []
    now = generated_at or datetime.now()
    lines = [
        "# C1 Release Review Guard Block",
        "",
        f"- Generated At: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Matches Requested: {int(matches_count)}",
        f"- Allowed: {bool(item.get('allowed', True))}",
        f"- Smoke: {item.get('status', '-')}",
        f"- Quality Fail/Warn: {_safe_int(item.get('quality_failures', 0))}/{_safe_int(item.get('quality_warnings', 0))}",
        f"- Status Text: {item.get('status_text', '-')}",
        "",
        "## Issues",
    ]
    if issues:
        lines.extend(f"- {issue}" for issue in issues)
    else:
        lines.append("- none")
    message = str(item.get("message") or "").strip()
    if message:
        lines.extend(["", "## Message", "```text", message, "```"])
    return lines


def get_c1_release_review_availability_guard(project_root: Path) -> dict:
    store = C1AvailabilityStore(project_root)
    return build_c1_release_review_availability_guard(store.load_sync_status())


def get_c1_availability_provider_statuses(project_root: Path) -> list[dict]:
    chain = AvailabilityProviderChain.from_project_root(project_root)
    statuses = [item for item in chain.provider_statuses() if isinstance(item, dict)]

    store = C1AvailabilityStore(project_root)
    sync_summary = store.load_sync_status()
    if not sync_summary:
        return statuses

    reports = sync_summary.get("provider_reports")
    report_map: dict[str, Mapping[str, object]] = {}
    if isinstance(reports, list):
        for item in reports:
            if not isinstance(item, Mapping):
                continue
            provider_name = str(item.get("provider_name", "")).strip()
            if provider_name:
                report_map[provider_name] = item

    for item in statuses:
        provider_name = str(item.get("provider_name", "")).strip()
        report = report_map.get(provider_name)
        if isinstance(report, Mapping):
            item["last_sync_status"] = str(report.get("status", "-"))
            item["last_imported_rows"] = int(report.get("rows", 0) or 0)
            item["last_written_keys"] = int(report.get("written_keys", 0) or 0)
            if "fixture_total" in report:
                item["fixture_total"] = int(report.get("fixture_total", 0) or 0)
            if "fixture_issue_count" in report:
                item["fixture_issue_count"] = int(report.get("fixture_issue_count", 0) or 0)
            if "fixture_limit" in report:
                item["fixture_limit"] = int(report.get("fixture_limit", 0) or 0)
            item["quality_gate"] = str(report.get("quality_gate") or "-")
            item["quality_score"] = float(report.get("quality_score", 0) or 0)
            item["quality_issues"] = report.get("quality_issues") if isinstance(report.get("quality_issues"), list) else []
            item["keyable_rate"] = float(report.get("keyable_rate", 0) or 0)
            item["availability_known_rate"] = float(report.get("availability_known_rate", 0) or 0)
        item["last_sync_at"] = str(sync_summary.get("last_sync_at") or sync_summary.get("updated_at") or "-")

    smoke = sync_summary.get("smoke_check") if isinstance(sync_summary.get("smoke_check"), Mapping) else {}
    statuses.append(
        {
            "provider_name": "__sync_summary__",
            "status": "ready",
            "is_sync_summary": True,
            "last_sync_at": str(sync_summary.get("last_sync_at") or sync_summary.get("updated_at") or "-"),
            "total_rows": int(sync_summary.get("total_rows", 0) or 0),
            "total_keys": int(sync_summary.get("total_keys", 0) or 0),
            "failed_providers": int(sync_summary.get("failed_providers", 0) or 0),
            "imported_providers": int(sync_summary.get("imported_providers", 0) or 0),
            "quality_failures": int(sync_summary.get("quality_failures", 0) or 0),
            "quality_warnings": int(sync_summary.get("quality_warnings", 0) or 0),
            "smoke_status": str(smoke.get("status") or "-"),
            "smoke_issues": smoke.get("issues") if isinstance(smoke.get("issues"), list) else [],
            "release_review_allowed": bool(smoke.get("release_review_allowed", True)),
        }
    )
    return statuses


def build_c1_availability_provider_status_lines(statuses: list[dict]) -> list[str]:
    lines = ["C1 阵容源状态"]

    summary_item: dict | None = None
    provider_items: list[dict] = []
    for item in statuses:
        if not isinstance(item, dict):
            continue
        if bool(item.get("is_sync_summary")):
            summary_item = item
            continue
        provider_items.append(item)

    if isinstance(summary_item, dict):
        lines.append(
            "最近同步: {time} | 导入行数 {rows} | 写入键数 {keys} | 失败源 {failed}".format(
                time=str(summary_item.get("last_sync_at", "-")),
                rows=int(summary_item.get("total_rows", 0) or 0),
                keys=int(summary_item.get("total_keys", 0) or 0),
                failed=int(summary_item.get("failed_providers", 0) or 0),
            )
        )

    if isinstance(summary_item, dict):
        lines.append(
            "  Smoke: {status} | quality fail/warn={fail}/{warn} | release_review={allowed}".format(
                status=str(summary_item.get("smoke_status", "-")),
                fail=int(summary_item.get("quality_failures", 0) or 0),
                warn=int(summary_item.get("quality_warnings", 0) or 0),
                allowed="on" if bool(summary_item.get("release_review_allowed", True)) else "off",
            )
        )

    ready_count = 0
    error_count = 0
    disabled_count = 0
    for item in provider_items:
        provider_name = str(item.get("provider_name", "-"))
        status = str(item.get("status", "-"))
        rows = item.get("rows", "-")
        resolve_enabled = bool(item.get("resolve_enabled", True))
        if status.lower() == "ready":
            ready_count += 1
        if status.lower() == "error":
            error_count += 1
        if not resolve_enabled:
            disabled_count += 1
        path_or_url = item.get("source_path") or item.get("url") or item.get("snapshot_file") or "-"
        extra = f" | resolve={'on' if resolve_enabled else 'off'}"
        lines.append(f"- {provider_name}: {status} | rows={rows} | source={path_or_url}{extra}")

        last_sync = str(item.get("last_sync_status", "")).strip()
        if last_sync:
            lines.append(
                "  上次同步: status={status} | rows={rows} | keys={keys} | at={at}".format(
                    status=last_sync,
                    rows=int(item.get("last_imported_rows", 0) or 0),
                    keys=int(item.get("last_written_keys", 0) or 0),
                    at=str(item.get("last_sync_at", "-")),
                )
            )
        if "fixture_total" in item:
            lines.append(
                "  API样本: total={total} | issue={issue} | limit={limit}".format(
                    total=int(item.get("fixture_total", 0) or 0),
                    issue=int(item.get("fixture_issue_count", 0) or 0),
                    limit=int(item.get("fixture_limit", 0) or 0),
                )
            )

        quality_gate = str(item.get("quality_gate", "")).strip()
        if quality_gate:
            issues = item.get("quality_issues") if isinstance(item.get("quality_issues"), list) else []
            lines.append(
                "  璐ㄩ噺闂ㄦ帶: gate={gate} | score={score:.2f} | keyable={keyable:.0%} | known={known:.0%} | issues={issues}".format(
                    gate=quality_gate,
                    score=float(item.get("quality_score", 0) or 0),
                    keyable=float(item.get("keyable_rate", 0) or 0),
                    known=float(item.get("availability_known_rate", 0) or 0),
                    issues=", ".join(str(issue) for issue in issues) if issues else "-",
                )
            )

        hint = _build_provider_error_hint(item)
        if hint:
            lines.append(f"  建议: {hint}")
    lines.append(f"汇总: ready={ready_count} | error={error_count} | resolve_off={disabled_count}")
    return lines


def build_c1_template_export_status_text(rows: int) -> str:
    return f"C1 阵容模板已导出 | {int(rows)} 行"


def build_c1_template_export_message_text(rows: int, path: str) -> str:
    return f"模板已导出\n行数: {int(rows)}\n路径: {path}"


def build_c1_snapshot_import_status_text(imported_rows: int, written_keys: int) -> str:
    return f"C1 阵容快照已导入 | 行 {int(imported_rows)} | 键 {int(written_keys)}"


def build_c1_snapshot_import_message_text(result: Mapping[str, object]) -> str:
    return (
        "导入完成\n"
        + f"来源: {result.get('source', '-')}\n"
        + f"导入行数: {int(result.get('imported_rows', 0) or 0)}\n"
        + f"写入键数: {int(result.get('written_keys', 0) or 0)}\n"
        + f"存储: {result.get('snapshot_file', '-')}"
    )


def build_c1_sync_status_text(total_rows: int, total_keys: int, *, failed_providers: int = 0) -> str:
    text = f"C1 阵容源已同步 | 行 {int(total_rows)} | 键 {int(total_keys)}"
    if int(failed_providers) > 0:
        text += f" | 失败源 {int(failed_providers)}"
    return text


def build_c1_sync_message_text(result: Mapping[str, object]) -> str:
    smoke = result.get("smoke_check") if isinstance(result.get("smoke_check"), Mapping) else {}
    lines = [
        "同步完成\n"
        + f"导入行数: {int(result.get('total_rows', 0) or 0)}\n"
        + f"写入键数: {int(result.get('total_keys', 0) or 0)}\n"
        + f"存储: {result.get('snapshot_file', '-')}\n"
        + f"失败源: {int(result.get('failed_providers', 0) or 0)}\n"
        + f"同步时间: {result.get('last_sync_at', '-')}"
    ]
    lines.append(
        "Quality gate: fail/warn={fail}/{warn} | smoke={smoke}".format(
            fail=int(result.get("quality_failures", 0) or 0),
            warn=int(result.get("quality_warnings", 0) or 0),
            smoke=smoke.get("status", "-"),
        )
    )
    provider_reports = result.get("provider_reports")
    if isinstance(provider_reports, list) and provider_reports:
        lines.append("源明细:")
        for item in provider_reports:
            if not isinstance(item, Mapping):
                continue
            provider_name = str(item.get("provider_name", "-"))
            status = str(item.get("status", "-"))
            rows = int(item.get("rows", 0) or 0)
            written_keys = int(item.get("written_keys", 0) or 0)
            line = f"- {provider_name}: status={status} | rows={rows} | keys={written_keys}"
            if "fixture_total" in item:
                line += (
                    f" | total={int(item.get('fixture_total', 0) or 0)}"
                    f" issue={int(item.get('fixture_issue_count', 0) or 0)}"
                    f" limit={int(item.get('fixture_limit', 0) or 0)}"
                )
            if "quality_gate" in item:
                issues = item.get("quality_issues") if isinstance(item.get("quality_issues"), list) else []
                line += (
                    f" | quality={item.get('quality_gate', '-')}"
                    f" score={float(item.get('quality_score', 0) or 0):.2f}"
                    f" issues={','.join(str(issue) for issue in issues) if issues else '-'}"
                )
            error = str(item.get("error", "")).strip()
            if error:
                line += f" | error={error}"
            lines.append(line)
            hint = _build_provider_error_hint(item)
            if hint:
                lines.append(f"  建议: {hint}")
    return "\n".join(lines)


def should_auto_rerun_shadow_after_import(*, has_matches: bool, imported_rows: int) -> bool:
    return bool(has_matches and int(imported_rows) > 0)


def should_auto_rerun_shadow_after_sync(*, has_matches: bool) -> bool:
    return bool(has_matches)
