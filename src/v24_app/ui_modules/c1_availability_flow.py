from __future__ import annotations

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
        item["last_sync_at"] = str(sync_summary.get("last_sync_at") or sync_summary.get("updated_at") or "-")

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
    lines = [
        "同步完成\n"
        + f"导入行数: {int(result.get('total_rows', 0) or 0)}\n"
        + f"写入键数: {int(result.get('total_keys', 0) or 0)}\n"
        + f"存储: {result.get('snapshot_file', '-')}\n"
        + f"失败源: {int(result.get('failed_providers', 0) or 0)}\n"
        + f"同步时间: {result.get('last_sync_at', '-')}"
    ]
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
