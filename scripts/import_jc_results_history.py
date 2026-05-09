from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = Path.home() / "Desktop" / "tools" / "赛果.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "history" / "jc_matches_2022_2026.jsonl"
DEFAULT_AUDIT_OUTPUT = PROJECT_ROOT / "reports" / "jc_results_import_audit.json"

HEADER_ROWS = 3


COL_ID = 0
COL_YEAR = 1
COL_ISSUE = 3
COL_LEAGUE = 4
COL_ROUND = 5
COL_MATCH_TIME = 6
COL_STATUS = 7
COL_HOME_TEAM = 9
COL_AWAY_TEAM = 10
COL_HALF_SCORE = 12
COL_FULL_SCORE = 13
COL_RESULT = 14
COL_SPF_OPEN_HOME = 15
COL_SPF_OPEN_DRAW = 16
COL_SPF_OPEN_AWAY = 17
COL_SPF_CLOSE_HOME = 18
COL_SPF_CLOSE_DRAW = 19
COL_SPF_CLOSE_AWAY = 20
COL_HANDICAP = 341
COL_HANDICAP_RESULT = 344
COL_HANDICAP_BONUS = 345
COL_SPF_RESULT = 346
COL_SPF_BONUS = 347


def bootstrap_project() -> None:
    os.chdir(PROJECT_ROOT)
    src_dir = PROJECT_ROOT / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _cell(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    return str(row[index] or "").strip()


def safe_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def safe_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "").replace("↑", "").replace("↓", "").strip()
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def parse_score(value: Any) -> tuple[int, int] | None:
    text = str(value or "").strip()
    if not text or text in {"-", "--", "VS"}:
        return None
    normalized = text.replace("：", ":").replace("-", ":").replace(" ", "")
    parts = normalized.split(":")
    if len(parts) != 2:
        return None
    left = safe_int(parts[0])
    right = safe_int(parts[1])
    if left is None or right is None:
        return None
    return left, right


def parse_match_datetime(year: int, raw_value: str) -> tuple[str, str, str]:
    raw = str(raw_value or "").strip()
    if not raw:
        return "", "", ""
    for pattern in ("%m-%d %H:%M", "%m/%d %H:%M", "%m.%d %H:%M"):
        try:
            dt = datetime.strptime(f"{year}-{raw}", f"%Y-{pattern}")
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except Exception:
            continue
    for pattern in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y.%m.%d %H:%M"):
        try:
            dt = datetime.strptime(raw, pattern)
            return dt.strftime("%Y-%m-%d %H:%M:%S"), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except Exception:
            continue
    return "", "", ""


def result_label(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "胜"
    if home_goals < away_goals:
        return "负"
    return "平"


def build_match_id(record: dict[str, Any]) -> str:
    base = "|".join(
        str(record.get(key) or "")
        for key in ("year", "issue", "league", "match_time_raw", "home_team", "away_team")
    )
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"jc:{record.get('year')}:{record.get('issue')}:{digest}"


def convert_row(row: list[str], source_row: int, source_file: Path) -> dict[str, Any] | None:
    year = safe_int(_cell(row, COL_YEAR))
    if year is None:
        return None

    full_score = _cell(row, COL_FULL_SCORE)
    parsed_full_score = parse_score(full_score)
    if parsed_full_score is None:
        return None
    home_goals, away_goals = parsed_full_score

    parsed_half_score = parse_score(_cell(row, COL_HALF_SCORE))
    match_datetime, match_date, match_time = parse_match_datetime(year, _cell(row, COL_MATCH_TIME))

    open_home = safe_float(_cell(row, COL_SPF_OPEN_HOME))
    open_draw = safe_float(_cell(row, COL_SPF_OPEN_DRAW))
    open_away = safe_float(_cell(row, COL_SPF_OPEN_AWAY))
    close_home = safe_float(_cell(row, COL_SPF_CLOSE_HOME))
    close_draw = safe_float(_cell(row, COL_SPF_CLOSE_DRAW))
    close_away = safe_float(_cell(row, COL_SPF_CLOSE_AWAY))

    record: dict[str, Any] = {
        "source": "jc_results_csv",
        "source_file": str(source_file),
        "source_row": source_row,
        "source_id": _cell(row, COL_ID),
        "year": year,
        "issue": _cell(row, COL_ISSUE),
        "league": _cell(row, COL_LEAGUE),
        "round": _cell(row, COL_ROUND),
        "match_time_raw": _cell(row, COL_MATCH_TIME),
        "match_datetime": match_datetime,
        "match_date": match_date,
        "match_time": match_time,
        "status": _cell(row, COL_STATUS),
        "home_team": _cell(row, COL_HOME_TEAM),
        "away_team": _cell(row, COL_AWAY_TEAM),
        "half_score": _cell(row, COL_HALF_SCORE),
        "full_score": full_score,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": _cell(row, COL_RESULT) or result_label(home_goals, away_goals),
        "computed_result": result_label(home_goals, away_goals),
        "official_spf_open": {"home": open_home, "draw": open_draw, "away": open_away},
        "official_spf_close": {"home": close_home, "draw": close_draw, "away": close_away},
        "odds_home": close_home,
        "odds_draw": close_draw,
        "odds_away": close_away,
        "opening_odds_home": open_home,
        "opening_odds_draw": open_draw,
        "opening_odds_away": open_away,
        "handicap": safe_float(_cell(row, COL_HANDICAP)),
        "handicap_line": safe_float(_cell(row, COL_HANDICAP)) or 0.0,
        "handicap_result": _cell(row, COL_HANDICAP_RESULT),
        "handicap_bonus": safe_float(_cell(row, COL_HANDICAP_BONUS)),
        "spf_result": _cell(row, COL_SPF_RESULT),
        "spf_bonus": safe_float(_cell(row, COL_SPF_BONUS)),
    }
    if parsed_half_score is not None:
        record["home_ht_goals"] = parsed_half_score[0]
        record["away_ht_goals"] = parsed_half_score[1]
    record["match_id"] = build_match_id(record)
    return record


def _has_complete_close_odds(record: dict[str, Any]) -> bool:
    return all(record.get(key) is not None for key in ("odds_home", "odds_draw", "odds_away"))


def _has_complete_open_odds(record: dict[str, Any]) -> bool:
    return all(record.get(key) is not None for key in ("opening_odds_home", "opening_odds_draw", "opening_odds_away"))


def read_source_rows(input_path: Path) -> list[tuple[int, list[str]]]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    source_rows: list[tuple[int, list[str]]] = []
    for offset, row in enumerate(rows[HEADER_ROWS:], start=HEADER_ROWS + 1):
        if any(str(value or "").strip() for value in row):
            source_rows.append((offset, row))
    return source_rows


def import_jc_results_history(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    audit_output_path: Path = DEFAULT_AUDIT_OUTPUT,
    start_year: int = 2022,
    end_year: int | None = None,
    include_unfinished: bool = False,
    require_close_odds: bool = True,
) -> dict[str, Any]:
    if end_year is None:
        end_year = datetime.now().year
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    raw_rows = read_source_rows(input_path)
    status_counts: Counter[str] = Counter()
    raw_year_counts: Counter[str] = Counter()
    raw_league_counts: Counter[str] = Counter()
    imported_year_counts: Counter[str] = Counter()
    imported_league_counts: Counter[str] = Counter()
    skipped = Counter()
    missing_spf_open = 0
    missing_spf_close = 0
    imported: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    date_values: list[str] = []

    for source_row, row in raw_rows:
        year = safe_int(_cell(row, COL_YEAR))
        status = _cell(row, COL_STATUS)
        league = _cell(row, COL_LEAGUE)
        status_counts[status or "-"] += 1
        if year is not None:
            raw_year_counts[str(year)] += 1
        raw_league_counts[league or "-"] += 1

        raw_open_complete = all(
            safe_float(_cell(row, index)) is not None
            for index in (COL_SPF_OPEN_HOME, COL_SPF_OPEN_DRAW, COL_SPF_OPEN_AWAY)
        )
        raw_close_complete = all(
            safe_float(_cell(row, index)) is not None
            for index in (COL_SPF_CLOSE_HOME, COL_SPF_CLOSE_DRAW, COL_SPF_CLOSE_AWAY)
        )
        if not raw_open_complete:
            missing_spf_open += 1
        if not raw_close_complete:
            missing_spf_close += 1

        if year is None:
            skipped["missing_year"] += 1
            continue
        if year < start_year or year > end_year:
            skipped["by_year"] += 1
            continue
        if not include_unfinished and status != "完":
            skipped["by_status"] += 1
            continue
        if parse_score(_cell(row, COL_FULL_SCORE)) is None:
            skipped["missing_score"] += 1
            continue

        record = convert_row(row, source_row, input_path)
        if record is None:
            skipped["invalid_row"] += 1
            continue
        if not record.get("league") or not record.get("home_team") or not record.get("away_team"):
            skipped["missing_required"] += 1
            continue
        if require_close_odds and not _has_complete_close_odds(record):
            skipped["missing_close_odds"] += 1
            continue

        match_id = str(record["match_id"])
        if match_id in seen_ids:
            skipped["duplicate"] += 1
            continue
        seen_ids.add(match_id)
        if not _has_complete_open_odds(record):
            record["open_odds_missing"] = True
        imported.append(record)
        imported_year_counts[str(year)] += 1
        imported_league_counts[str(record.get("league") or "-")] += 1
        if record.get("match_date"):
            date_values.append(str(record["match_date"]))

    imported.sort(key=lambda item: (str(item.get("match_datetime") or ""), str(item.get("match_id") or "")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in imported:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    audit = {
        "source_file": str(input_path),
        "output_file": str(output_path),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filters": {
            "start_year": start_year,
            "end_year": end_year,
            "include_unfinished": include_unfinished,
            "require_close_odds": require_close_odds,
        },
        "raw_rows": len(raw_rows),
        "imported": len(imported),
        "skipped": dict(sorted(skipped.items())),
        "skipped_total": sum(skipped.values()),
        "missing_spf_open": missing_spf_open,
        "missing_spf_close": missing_spf_close,
        "duplicate_count": int(skipped.get("duplicate", 0)),
        "status_counts": dict(sorted(status_counts.items())),
        "rows_by_year": dict(sorted(raw_year_counts.items())),
        "imported_by_year": dict(sorted(imported_year_counts.items())),
        "top_leagues": dict(imported_league_counts.most_common(30)),
        "raw_top_leagues": dict(raw_league_counts.most_common(30)),
        "date_start": min(date_values) if date_values else None,
        "date_end": max(date_values) if date_values else None,
    }
    audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def import_to_xgb_samples(
    output_path: Path,
    *,
    replace: bool = False,
    sync_ratings: bool = False,
) -> dict[str, Any]:
    bootstrap_project()
    from v24_app.training_samples import import_historical_xgb_samples

    return import_historical_xgb_samples(
        project_dir=PROJECT_ROOT,
        input_path=output_path,
        replace=replace,
        sync_ratings=sync_ratings,
    )


def train_xgb_model(force_min_samples: int | None = None) -> dict[str, Any]:
    bootstrap_project()
    from v24_app.core import train_xgb_v0_now

    return train_xgb_v0_now(force_min_samples=force_min_samples)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import JC results CSV into normalized local history JSONL.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=datetime.now().year)
    parser.add_argument("--include-unfinished", action="store_true")
    parser.add_argument(
        "--allow-missing-close-odds",
        action="store_true",
        help="Keep rows without complete official closing SPF odds.",
    )
    parser.add_argument("--import-xgb", action="store_true", help="Import normalized JC history into XGB samples.")
    parser.add_argument("--replace-xgb", action="store_true", help="Replace existing XGB samples during --import-xgb.")
    parser.add_argument("--sync-ratings", action="store_true", help="Sync reconstructed Elo ratings during --import-xgb.")
    parser.add_argument("--train", action="store_true", help="Train XGB v0 after --import-xgb.")
    parser.add_argument(
        "--force-min-samples",
        type=int,
        default=None,
        help="Override XGB minimum sample threshold during --train.",
    )
    args = parser.parse_args()

    audit = import_jc_results_history(
        input_path=args.input,
        output_path=args.output,
        audit_output_path=args.audit_output,
        start_year=args.start_year,
        end_year=args.end_year,
        include_unfinished=args.include_unfinished,
        require_close_odds=not args.allow_missing_close_odds,
    )
    result: dict[str, Any] = {"history_import": audit}
    if args.import_xgb:
        result["xgb_import"] = import_to_xgb_samples(
            output_path=args.output,
            replace=args.replace_xgb,
            sync_ratings=args.sync_ratings,
        )
    if args.train:
        if not args.import_xgb:
            result["warning"] = "--train was requested without --import-xgb; training existing samples."
        result["xgb_train"] = train_xgb_model(force_min_samples=args.force_min_samples)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
