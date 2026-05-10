from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def payload_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def pct(hits: int, total: int) -> str:
    if total <= 0:
        return "-"
    return f"{hits / total:.1%}"


def winner_from_margin(value: float, *, threshold: float = 0.0) -> str:
    if value > threshold:
        return "home"
    if value < -threshold:
        return "away"
    return "draw"


def team_stats(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = record.get("event_summary") if isinstance(record.get("event_summary"), dict) else {}
    stats = summary.get("team_stats") if isinstance(summary.get("team_stats"), dict) else {}
    home = str(record.get("home_team") or "")
    away = str(record.get("away_team") or "")
    home_stats = stats.get(home) if home else None
    away_stats = stats.get(away) if away else None
    if not isinstance(home_stats, dict) or not isinstance(away_stats, dict):
        values = [item for item in stats.values() if isinstance(item, dict)]
        if len(values) >= 2:
            home_stats = values[0] if not isinstance(home_stats, dict) else home_stats
            away_stats = values[1] if not isinstance(away_stats, dict) else away_stats
    return home_stats if isinstance(home_stats, dict) else {}, away_stats if isinstance(away_stats, dict) else {}


def baseline_row(record: dict[str, Any], *, xg_threshold: float = 0.25) -> dict[str, Any] | None:
    home_stats, away_stats = team_stats(record)
    if not home_stats or not away_stats:
        return None
    home_goals = safe_int(record.get("home_goals"))
    away_goals = safe_int(record.get("away_goals"))
    home_xg = safe_float(home_stats.get("xg"))
    away_xg = safe_float(away_stats.get("xg"))
    home_shots = safe_int(home_stats.get("shots"))
    away_shots = safe_int(away_stats.get("shots"))
    home_sot = safe_int(home_stats.get("shots_on_target"))
    away_sot = safe_int(away_stats.get("shots_on_target"))
    score_winner = winner_from_margin(float(home_goals - away_goals))
    xg_winner = winner_from_margin(home_xg - away_xg, threshold=xg_threshold)
    shot_winner = winner_from_margin(float(home_shots - away_shots), threshold=2.0)
    xg_margin = round(home_xg - away_xg, 4)
    goal_margin = home_goals - away_goals
    finishing_delta_home = round(home_goals - home_xg, 4)
    finishing_delta_away = round(away_goals - away_xg, 4)
    return {
        "match_id": record.get("match_id"),
        "source_match_id": record.get("source_match_id"),
        "match_date": record.get("match_date"),
        "league": record.get("league"),
        "season": record.get("season"),
        "home_team": record.get("home_team"),
        "away_team": record.get("away_team"),
        "score": f"{home_goals}-{away_goals}",
        "score_winner": score_winner,
        "xg_winner": xg_winner,
        "shot_winner": shot_winner,
        "xg_aligned_with_score": bool(xg_winner == score_winner),
        "shot_aligned_with_score": bool(shot_winner == score_winner),
        "finishing_variance": bool(xg_winner != "draw" and xg_winner != score_winner),
        "home_xg": round(home_xg, 4),
        "away_xg": round(away_xg, 4),
        "xg_margin": xg_margin,
        "xg_total": round(home_xg + away_xg, 4),
        "home_shots": home_shots,
        "away_shots": away_shots,
        "shot_margin": home_shots - away_shots,
        "home_shots_on_target": home_sot,
        "away_shots_on_target": away_sot,
        "shots_on_target_margin": home_sot - away_sot,
        "goal_margin": goal_margin,
        "finishing_delta_home": finishing_delta_home,
        "finishing_delta_away": finishing_delta_away,
        "event_count": safe_int((record.get("event_summary") or {}).get("event_count") if isinstance(record.get("event_summary"), dict) else 0),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "match_count": 0,
            "xg_alignment_rate": "-",
            "shot_alignment_rate": "-",
            "finishing_variance_rate": "-",
            "avg_xg_total": 0.0,
            "avg_event_count": 0.0,
        }
    xg_aligned = sum(1 for item in rows if item.get("xg_aligned_with_score"))
    shot_aligned = sum(1 for item in rows if item.get("shot_aligned_with_score"))
    finishing_variance = sum(1 for item in rows if item.get("finishing_variance"))
    return {
        "match_count": len(rows),
        "xg_alignment_rate": pct(xg_aligned, len(rows)),
        "shot_alignment_rate": pct(shot_aligned, len(rows)),
        "finishing_variance_rate": pct(finishing_variance, len(rows)),
        "avg_xg_total": round(sum(safe_float(item.get("xg_total")) for item in rows) / len(rows), 4),
        "avg_event_count": round(sum(safe_int(item.get("event_count")) for item in rows) / len(rows), 2),
    }


def bucket_label(value: float) -> str:
    absolute = abs(value)
    if absolute < 0.25:
        return "balanced"
    if absolute < 0.75:
        return "small_edge"
    if absolute < 1.25:
        return "clear_edge"
    return "dominant_edge"


def build_statsbomb_event_baseline(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in (baseline_row(record) for record in records) if isinstance(row, dict)]
    by_competition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    result_counts: Counter[str] = Counter()
    for row in rows:
        key = f"{row.get('league') or '-'} | {row.get('season') or '-'}"
        by_competition[key].append(row)
        by_bucket[bucket_label(safe_float(row.get("xg_margin")))].append(row)
        result_counts[str(row.get("score_winner") or "-")] += 1
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "StatsBomb Open Data",
        "purpose": "historical_post_match_event_baseline",
        "leakage_note": "This baseline uses post-match event data and must not be used as pre-match prediction input.",
        "summary": {
            **summarize_rows(rows),
            "result_counts": dict(result_counts),
            "competition_count": len(by_competition),
        },
        "competition_profiles": {
            key: summarize_rows(value)
            for key, value in sorted(by_competition.items())
        },
        "xg_margin_buckets": {
            key: summarize_rows(value)
            for key, value in sorted(by_bucket.items())
        },
        "variance_rows": [
            item
            for item in sorted(
                rows,
                key=lambda row: (
                    not bool(row.get("finishing_variance")),
                    -abs(safe_float(row.get("xg_margin"))),
                    str(row.get("match_date") or ""),
                ),
            )
            if item.get("finishing_variance")
        ][:30],
        "items": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a historical StatsBomb event baseline for post-match review.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    state_dir = args.project_root / "data" / "state"
    input_path = args.input or state_dir / "statsbomb_event_summaries.json"
    output_path = args.output or state_dir / "statsbomb_event_baseline.json"
    baseline = build_statsbomb_event_baseline(payload_items(read_json(input_path)))
    write_json(output_path, baseline)
    result = {
        "match_count": baseline.get("summary", {}).get("match_count", 0),
        "competition_count": baseline.get("summary", {}).get("competition_count", 0),
        "variance_count": len(baseline.get("variance_rows", [])),
        "output_path": str(output_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
