from __future__ import annotations

import csv
import io
import json
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable, Mapping


_PERCENT_PATTERN = re.compile(r"([+-]?\d+(?:\.\d+)?)%")
_INT_PATTERN = re.compile(r"(-?\d+)")
_ALERT_MARK = "[ALERT]"


def list_ops_daily_reports(report_dir: Path, *, limit: int = 30) -> list[Path]:
    files = sorted(report_dir.glob("ops_daily_summary_*.md"), key=lambda path: path.name, reverse=True)
    return files[: max(1, int(limit))]


def read_latest_ops_daily_report(report_dir: Path) -> dict[str, Any]:
    files = list_ops_daily_reports(report_dir, limit=1)
    if not files:
        return {"ok": False, "reason": "no_report"}
    path = files[0]
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {"ok": False, "reason": f"read_failed:{exc}", "path": str(path)}
    return {"ok": True, "path": str(path), "text": text}


def load_ops_heartbeat(report_dir: Path) -> dict[str, Any]:
    heartbeat_path = report_dir / "ops_scheduler_heartbeat.json"
    if not heartbeat_path.exists():
        return {}
    try:
        payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_ops_heartbeat_summary_text(heartbeat: Mapping[str, Any]) -> str:
    if not heartbeat:
        return "心跳: 无"
    updated = str(heartbeat.get("updated_at", "-"))
    new_settled = int(heartbeat.get("new_settled", 0) or 0)
    bayes = heartbeat.get("bayes_calibration", {}) if isinstance(heartbeat, Mapping) else {}
    bucket = heartbeat.get("bucket_tuning", {}) if isinstance(heartbeat, Mapping) else {}
    guardrail = heartbeat.get("coverage_guardrail", {}) if isinstance(heartbeat, Mapping) else {}
    return (
        f"心跳更新时间: {updated} | 新结算: {new_settled} | "
        f"Bayes={bayes.get('reason', '-')} | Bucket={bucket.get('reason', '-')} | Guardrail={guardrail.get('reason', '-')}"
    )


def _parse_percent(text: str) -> float | None:
    match = _PERCENT_PATTERN.search(text)
    if not match:
        return None
    try:
        return float(match.group(1)) / 100.0
    except Exception:
        return None


def _parse_int(text: str) -> int | None:
    match = _INT_PATTERN.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _parse_threshold_snapshot_line(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    pattern = re.compile(r"(1x2|handicap|total_goals|score|htft)\s*=\s*([+-]?\d+(?:\.\d+)?)", re.IGNORECASE)
    for key, raw_value in pattern.findall(str(text or "")):
        try:
            values[f"threshold_{key.lower()}"] = float(raw_value)
        except Exception:
            continue
    return values


def parse_ops_daily_summary_text(text: str, filename: str) -> dict[str, Any]:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    row: dict[str, Any] = {
        "file": filename,
        "date": filename.replace("ops_daily_summary_", "").replace(".md", ""),
        "overall_hit_rate": None,
        "overall_ev_bias": None,
        "losing_streak": None,
        "breaker_on": None,
        "bayes_reason": "",
        "bucket_reason": "",
        "guardrail_reason": "",
        "parlay_ticket_count": None,
        "parlay_unique_match_count": None,
        "parlay_max_exposure": None,
        "parlay_avg_exposure": None,
        "parlay_mixed_ratio": None,
        "parlay_avg_expected_hit": None,
        "parlay_max_expected_hit": None,
        "parlay_high_expected_hit_count": None,
        "parlay_low_discount_count": None,
        "parlay_high_upset_leg_count": None,
        "parlay_avg_pair_quality_factor": None,
        "parlay_avg_play_reliability_factor": None,
        "threshold_mode": "",
        "threshold_updated_at": "",
        "threshold_1x2": None,
        "threshold_handicap": None,
        "threshold_total_goals": None,
        "threshold_score": None,
        "threshold_htft": None,
        "is_alert": False,
        "alert_reasons": [],
    }
    for line in lines:
        if line.startswith("- Overall:"):
            parts = line.split("|")
            if len(parts) >= 3:
                row["overall_hit_rate"] = _parse_percent(parts[0])
                row["overall_ev_bias"] = _parse_percent(parts[2])
            if len(parts) >= 4:
                row["losing_streak"] = _parse_int(parts[3])
            breaker_match = re.search(r"\bbreaker\s+(true|false)\b", line, flags=re.IGNORECASE)
            if breaker_match is not None:
                row["breaker_on"] = breaker_match.group(1).lower() == "true"
        elif line.startswith("- Bayes:"):
            row["bayes_reason"] = line
        elif line.startswith("- Bucket Tuning:"):
            row["bucket_reason"] = line
        elif line.startswith("- Coverage Guardrail:"):
            row["guardrail_reason"] = line
        elif line.startswith("- tickets="):
            row["parlay_ticket_count"] = _parse_int(re.search(r"tickets=(\d+)", line).group(1)) if re.search(r"tickets=(\d+)", line) else None
            row["parlay_unique_match_count"] = (
                _parse_int(re.search(r"unique_matches=(\d+)", line).group(1))
                if re.search(r"unique_matches=(\d+)", line)
                else None
            )
            row["parlay_max_exposure"] = (
                _parse_int(re.search(r"max_exposure=(\d+)", line).group(1))
                if re.search(r"max_exposure=(\d+)", line)
                else None
            )
            avg_exposure_match = re.search(r"avg_exposure=([+-]?\d+(?:\.\d+)?)", line)
            row["parlay_avg_exposure"] = float(avg_exposure_match.group(1)) if avg_exposure_match else None
        elif line.startswith("- mixed_ratio="):
            row["parlay_mixed_ratio"] = _parse_percent(line)
            avg_expected_match = re.search(r"avg_expected_hit=([+-]?\d+(?:\.\d+)?)%", line)
            max_expected_match = re.search(r"max_expected_hit=([+-]?\d+(?:\.\d+)?)%", line)
            row["parlay_avg_expected_hit"] = (
                (float(avg_expected_match.group(1)) / 100.0) if avg_expected_match else None
            )
            row["parlay_max_expected_hit"] = (
                (float(max_expected_match.group(1)) / 100.0) if max_expected_match else None
            )
        elif line.startswith("- risk_flags:"):
            row["parlay_high_expected_hit_count"] = (
                _parse_int(re.search(r"high_expected_hit=(\d+)", line).group(1))
                if re.search(r"high_expected_hit=(\d+)", line)
                else None
            )
            row["parlay_low_discount_count"] = (
                _parse_int(re.search(r"low_discount=(\d+)", line).group(1))
                if re.search(r"low_discount=(\d+)", line)
                else None
            )
            row["parlay_high_upset_leg_count"] = (
                _parse_int(re.search(r"high_upset_leg=(\d+)", line).group(1))
                if re.search(r"high_upset_leg=(\d+)", line)
                else None
            )
        elif line.startswith("- factors:"):
            pair_quality_match = re.search(r"pair_quality=([+-]?\d+(?:\.\d+)?)", line)
            reliability_match = re.search(r"play_reliability=([+-]?\d+(?:\.\d+)?)", line)
            row["parlay_avg_pair_quality_factor"] = float(pair_quality_match.group(1)) if pair_quality_match else None
            row["parlay_avg_play_reliability_factor"] = float(reliability_match.group(1)) if reliability_match else None
        elif line.startswith("- mode:"):
            row["threshold_mode"] = line.replace("- mode:", "", 1).strip()
        elif line.startswith("- updated_at:"):
            row["threshold_updated_at"] = line.replace("- updated_at:", "", 1).strip()
        elif line.startswith("- 1x2="):
            row.update(_parse_threshold_snapshot_line(line))

    reasons: list[str] = []
    if bool(row.get("breaker_on")):
        reasons.append("breaker_on")
    ev_bias = row.get("overall_ev_bias")
    if isinstance(ev_bias, float) and ev_bias <= -0.08:
        reasons.append("ev_bias_low")
    max_exposure = row.get("parlay_max_exposure")
    if isinstance(max_exposure, int) and max_exposure >= 3:
        reasons.append("parlay_exposure_high")
    low_discount_count = row.get("parlay_low_discount_count")
    if isinstance(low_discount_count, int) and low_discount_count >= 2:
        reasons.append("parlay_correlation_risk")
    high_upset_count = row.get("parlay_high_upset_leg_count")
    if isinstance(high_upset_count, int) and high_upset_count >= 2:
        reasons.append("parlay_upset_risk")
    play_reliability = row.get("parlay_avg_play_reliability_factor")
    if isinstance(play_reliability, float) and play_reliability < 0.90:
        reasons.append("parlay_reliability_low")
    row["alert_reasons"] = reasons
    row["is_alert"] = len(reasons) > 0
    return row


def _build_threshold_delta_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    previous: dict[str, float] = {}
    keys = [
        "threshold_1x2",
        "threshold_handicap",
        "threshold_total_goals",
        "threshold_score",
        "threshold_htft",
    ]
    for row in rows:
        item = dict(row)
        for key in keys:
            current = item.get(key)
            delta_key = f"delta_{key}"
            if isinstance(current, (float, int)):
                previous_value = previous.get(key)
                item[delta_key] = round(float(current) - float(previous_value), 4) if previous_value is not None else None
                previous[key] = float(current)
            else:
                item[delta_key] = None
        deltas.append(item)
    return deltas


def build_threshold_change_table_text(rows: list[Mapping[str, Any]]) -> str:
    resolved_rows = _build_threshold_delta_rows(list(rows))
    if not resolved_rows:
        return ""
    lines = [
        "Threshold Change Table",
        "",
        "| Date | Mode | 1x2 | d | Handicap | d | Total Goals | d | Score | d | HTFT | d |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def _fmt_value(value: Any) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):.2f}"
        return "-"

    def _fmt_delta(value: Any) -> str:
        if isinstance(value, (float, int)):
            return f"{float(value):+.2f}"
        return "-"

    for row in resolved_rows:
        lines.append(
            f"| {row.get('date', '-')} | {row.get('threshold_mode', '-') or '-'} | "
            f"{_fmt_value(row.get('threshold_1x2'))} | {_fmt_delta(row.get('delta_threshold_1x2'))} | "
            f"{_fmt_value(row.get('threshold_handicap'))} | {_fmt_delta(row.get('delta_threshold_handicap'))} | "
            f"{_fmt_value(row.get('threshold_total_goals'))} | {_fmt_delta(row.get('delta_threshold_total_goals'))} | "
            f"{_fmt_value(row.get('threshold_score'))} | {_fmt_delta(row.get('delta_threshold_score'))} | "
            f"{_fmt_value(row.get('threshold_htft'))} | {_fmt_delta(row.get('delta_threshold_htft'))} |"
        )
    return "\n".join(lines)


def build_ops_trend_rows(report_dir: Path, *, days: int = 7) -> list[dict[str, Any]]:
    files = list_ops_daily_reports(report_dir, limit=max(1, int(days)))
    rows: list[dict[str, Any]] = []
    for path in reversed(files):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        rows.append(parse_ops_daily_summary_text(text, path.name))
    return rows


def build_ops_trend_text(report_dir: Path, *, days: int = 7) -> str:
    parsed = build_ops_trend_rows(report_dir, days=days)
    if not parsed:
        return ""

    hit_values = [float(item["overall_hit_rate"]) for item in parsed if isinstance(item.get("overall_hit_rate"), float)]
    bias_values = [float(item["overall_ev_bias"]) for item in parsed if isinstance(item.get("overall_ev_bias"), float)]
    breaker_count = sum(1 for item in parsed if item.get("breaker_on") is True)
    max_exposure_values = [int(item["parlay_max_exposure"]) for item in parsed if isinstance(item.get("parlay_max_exposure"), int)]
    avg_expected_hit_values = [
        float(item["parlay_avg_expected_hit"])
        for item in parsed
        if isinstance(item.get("parlay_avg_expected_hit"), float)
    ]
    anomaly_count = sum(1 for item in parsed if bool(item.get("is_alert")))
    avg_hit = (sum(hit_values) / len(hit_values)) if hit_values else 0.0
    avg_bias = (sum(bias_values) / len(bias_values)) if bias_values else 0.0
    avg_parlay_expected_hit = (sum(avg_expected_hit_values) / len(avg_expected_hit_values)) if avg_expected_hit_values else 0.0

    horizon_days = max(1, int(days))
    lines = [
        f"运营{horizon_days}天趋势 ({len(parsed)} 天)",
        f"- 平均命中率: {avg_hit:.1%}",
        f"- 平均EV偏差: {avg_bias:+.1%}",
        f"- Breaker触发天数: {breaker_count}",
        f"- 二串一平均组合命中率: {avg_parlay_expected_hit:.1%}",
        f"- 二串一最大场次暴露: {max(max_exposure_values) if max_exposure_values else 0}",
        f"- 异常日数: {anomaly_count}",
        "",
        "| 日期 | 命中率 | EV偏差 | 连败 | Breaker | 二串一健康 | Alert | Bayes | Bucket | Guardrail |",
        "|---|---:|---:|---:|---|---|---|---|---|---|",
    ]
    for item in parsed:
        hit = item.get("overall_hit_rate")
        bias = item.get("overall_ev_bias")
        streak = item.get("losing_streak")
        bayes = "ok" if "reason=ok" in str(item.get("bayes_reason", "")) else "-"
        bucket = "ok" if "reason=ok" in str(item.get("bucket_reason", "")) else "-"
        guardrail = "ok" if "reason=ok" in str(item.get("guardrail_reason", "")) else "-"
        alert = "-"
        if bool(item.get("is_alert")):
            reasons = item.get("alert_reasons", [])
            reason_text = ",".join(str(r) for r in reasons) if isinstance(reasons, list) and reasons else "anomaly"
            alert = f"{_ALERT_MARK} {reason_text}"
        exposure = item.get("parlay_max_exposure")
        parlay_expected = item.get("parlay_avg_expected_hit")
        parlay_health = (
            f"exp={(f'{float(parlay_expected):.1%}' if isinstance(parlay_expected, float) else '-')}"
            f"|expo={(str(exposure) if isinstance(exposure, int) else '-')}"
            f"|risk={int(item.get('parlay_low_discount_count', 0) or 0)}/{int(item.get('parlay_high_upset_leg_count', 0) or 0)}"
        )
        lines.append(
            f"| {item.get('date', '-')} | "
            f"{(f'{float(hit):.1%}' if isinstance(hit, float) else '-')} | "
            f"{(f'{float(bias):+.1%}' if isinstance(bias, float) else '-')} | "
            f"{(str(streak) if isinstance(streak, int) else '-')} | "
            f"{'ON' if item.get('breaker_on') else 'OFF'} | {parlay_health} | {alert} | {bayes} | {bucket} | {guardrail} |"
        )
    threshold_table_text = build_threshold_change_table_text(parsed)
    return "\n".join(lines) + ("\n\n" + threshold_table_text if threshold_table_text else "")


def build_ops_trend_csv_text(rows: list[Mapping[str, Any]]) -> str:
    resolved_rows = _build_threshold_delta_rows(list(rows))
    fieldnames = [
        "date",
        "overall_hit_rate",
        "overall_ev_bias",
        "losing_streak",
        "breaker_on",
        "is_alert",
        "alert_reasons",
        "bayes_reason",
        "bucket_reason",
        "guardrail_reason",
        "parlay_ticket_count",
        "parlay_unique_match_count",
        "parlay_max_exposure",
        "parlay_avg_exposure",
        "parlay_mixed_ratio",
        "parlay_avg_expected_hit",
        "parlay_max_expected_hit",
        "parlay_high_expected_hit_count",
        "parlay_low_discount_count",
        "parlay_high_upset_leg_count",
        "parlay_avg_pair_quality_factor",
        "parlay_avg_play_reliability_factor",
        "threshold_mode",
        "threshold_updated_at",
        "threshold_1x2",
        "threshold_handicap",
        "threshold_total_goals",
        "threshold_score",
        "threshold_htft",
        "delta_threshold_1x2",
        "delta_threshold_handicap",
        "delta_threshold_total_goals",
        "delta_threshold_score",
        "delta_threshold_htft",
        "file",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in resolved_rows:
        reasons = row.get("alert_reasons", [])
        reason_text = ",".join(str(item) for item in reasons) if isinstance(reasons, list) else str(reasons or "")
        writer.writerow(
            {
                "date": row.get("date", ""),
                "overall_hit_rate": row.get("overall_hit_rate", ""),
                "overall_ev_bias": row.get("overall_ev_bias", ""),
                "losing_streak": row.get("losing_streak", ""),
                "breaker_on": row.get("breaker_on", ""),
                "is_alert": row.get("is_alert", ""),
                "alert_reasons": reason_text,
                "bayes_reason": row.get("bayes_reason", ""),
                "bucket_reason": row.get("bucket_reason", ""),
                "guardrail_reason": row.get("guardrail_reason", ""),
                "parlay_ticket_count": row.get("parlay_ticket_count", ""),
                "parlay_unique_match_count": row.get("parlay_unique_match_count", ""),
                "parlay_max_exposure": row.get("parlay_max_exposure", ""),
                "parlay_avg_exposure": row.get("parlay_avg_exposure", ""),
                "parlay_mixed_ratio": row.get("parlay_mixed_ratio", ""),
                "parlay_avg_expected_hit": row.get("parlay_avg_expected_hit", ""),
                "parlay_max_expected_hit": row.get("parlay_max_expected_hit", ""),
                "parlay_high_expected_hit_count": row.get("parlay_high_expected_hit_count", ""),
                "parlay_low_discount_count": row.get("parlay_low_discount_count", ""),
                "parlay_high_upset_leg_count": row.get("parlay_high_upset_leg_count", ""),
                "parlay_avg_pair_quality_factor": row.get("parlay_avg_pair_quality_factor", ""),
                "parlay_avg_play_reliability_factor": row.get("parlay_avg_play_reliability_factor", ""),
                "threshold_mode": row.get("threshold_mode", ""),
                "threshold_updated_at": row.get("threshold_updated_at", ""),
                "threshold_1x2": row.get("threshold_1x2", ""),
                "threshold_handicap": row.get("threshold_handicap", ""),
                "threshold_total_goals": row.get("threshold_total_goals", ""),
                "threshold_score": row.get("threshold_score", ""),
                "threshold_htft": row.get("threshold_htft", ""),
                "delta_threshold_1x2": row.get("delta_threshold_1x2", ""),
                "delta_threshold_handicap": row.get("delta_threshold_handicap", ""),
                "delta_threshold_total_goals": row.get("delta_threshold_total_goals", ""),
                "delta_threshold_score": row.get("delta_threshold_score", ""),
                "delta_threshold_htft": row.get("delta_threshold_htft", ""),
                "file": row.get("file", ""),
            }
        )
    return buf.getvalue()


def build_ops_trend_csv_filename(*, days: int = 7, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"ops_trend_{max(1, int(days))}d_{stamp}.csv"


def build_threshold_trend_csv_filename(*, days: int = 7, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"threshold_trend_{max(1, int(days))}d_{stamp}.csv"


def build_threshold_trend_csv_text(rows: list[Mapping[str, Any]]) -> str:
    resolved_rows = _build_threshold_delta_rows(list(rows))
    fieldnames = [
        "date",
        "threshold_mode",
        "threshold_updated_at",
        "threshold_1x2",
        "delta_threshold_1x2",
        "threshold_handicap",
        "delta_threshold_handicap",
        "threshold_total_goals",
        "delta_threshold_total_goals",
        "threshold_score",
        "delta_threshold_score",
        "threshold_htft",
        "delta_threshold_htft",
        "file",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in resolved_rows:
        writer.writerow(
            {
                "date": row.get("date", ""),
                "threshold_mode": row.get("threshold_mode", ""),
                "threshold_updated_at": row.get("threshold_updated_at", ""),
                "threshold_1x2": row.get("threshold_1x2", ""),
                "delta_threshold_1x2": row.get("delta_threshold_1x2", ""),
                "threshold_handicap": row.get("threshold_handicap", ""),
                "delta_threshold_handicap": row.get("delta_threshold_handicap", ""),
                "threshold_total_goals": row.get("threshold_total_goals", ""),
                "delta_threshold_total_goals": row.get("delta_threshold_total_goals", ""),
                "threshold_score": row.get("threshold_score", ""),
                "delta_threshold_score": row.get("delta_threshold_score", ""),
                "threshold_htft": row.get("threshold_htft", ""),
                "delta_threshold_htft": row.get("delta_threshold_htft", ""),
                "file": row.get("file", ""),
            }
        )
    return buf.getvalue()


def export_ops_trend_csv(
    report_dir: Path,
    *,
    rows: list[Mapping[str, Any]] | None = None,
    days: int = 7,
    now: datetime | None = None,
) -> Path | None:
    resolved_rows: list[Mapping[str, Any]] = rows if isinstance(rows, list) else build_ops_trend_rows(report_dir, days=days)
    if not resolved_rows:
        return None
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / build_ops_trend_csv_filename(days=days, now=now)
    path.write_text(build_ops_trend_csv_text(resolved_rows), encoding="utf-8")
    return path


def export_threshold_trend_csv(
    report_dir: Path,
    *,
    rows: list[Mapping[str, Any]] | None = None,
    days: int = 7,
    now: datetime | None = None,
) -> Path | None:
    resolved_rows: list[Mapping[str, Any]] = rows if isinstance(rows, list) else build_ops_trend_rows(report_dir, days=days)
    if not resolved_rows:
        return None
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / build_threshold_trend_csv_filename(days=days, now=now)
    path.write_text(build_threshold_trend_csv_text(resolved_rows), encoding="utf-8")
    return path


def open_text_view_window(
    *,
    root: tk.Tk,
    existing_window: tk.Toplevel | None,
    title: str,
    header: str,
    content: str,
    on_close: Callable[[], None],
    actions: list[tuple[str, Callable[[], None]]] | None = None,
    highlight_alerts: bool = True,
    width: int = 980,
    height: int = 660,
) -> tk.Toplevel:
    if existing_window is not None and existing_window.winfo_exists():
        existing_window.lift()
        existing_window.focus_force()
        return existing_window

    window = tk.Toplevel(root)
    window.title(title)
    window.geometry(f"{max(780, int(width))}x{max(520, int(height))}")
    window.minsize(760, 500)
    window.transient(root)
    window.protocol("WM_DELETE_WINDOW", on_close)

    frame = ttk.Frame(window, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frame, text=title, font=("Microsoft YaHei UI", 13, "bold")).pack(anchor=tk.W)
    ttk.Label(frame, text=header, style="Sub.TLabel").pack(anchor=tk.W, pady=(4, 10))

    text_frame = ttk.Frame(frame)
    text_frame.pack(fill=tk.BOTH, expand=True)
    text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10), background="#fbfdff")
    y_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    x_scroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
    text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    text_widget.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)
    text_widget.insert("1.0", content or "")
    if highlight_alerts and content:
        text_widget.tag_configure("alert_line", foreground="#b91c1c", background="#fff1f2")
        cursor = "1.0"
        while True:
            found = text_widget.search(_ALERT_MARK, cursor, stopindex=tk.END)
            if not found:
                break
            text_widget.tag_add("alert_line", f"{found} linestart", f"{found} lineend")
            cursor = f"{found}+1c"
    text_widget.configure(state=tk.DISABLED)

    footer = ttk.Frame(frame)
    footer.pack(fill=tk.X, pady=(8, 0))
    if actions:
        for idx, (label, callback) in enumerate(actions):
            ttk.Button(footer, text=label, command=callback).pack(side=tk.LEFT, padx=(0, 8) if idx < len(actions) - 1 else 0)
    ttk.Button(footer, text="关闭", command=on_close).pack(side=tk.RIGHT)
    return window
