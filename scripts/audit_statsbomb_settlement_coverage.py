from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
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


def items_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def norm(value: object) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[\s\-_.,:;|/\\()\[\]{}]+", " ", text)
    text = re.sub(r"\b(fc|cf|club|the|afc|sc)\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def match_key(item: dict[str, Any], *, include_league: bool = False) -> str:
    parts = [norm(item.get("match_date"))]
    if include_league:
        parts.append(norm(item.get("league")))
    parts.extend([norm(item.get("home_team")), norm(item.get("away_team"))])
    return "|".join(part for part in parts if part)


def exact_match_keys(item: dict[str, Any]) -> set[str]:
    keys = {
        norm(item.get("match_id")),
        norm(item.get("source_match_id")),
        match_key(item),
        match_key(item, include_league=True),
    }
    return {key for key in keys if key}


def date_values(items: list[dict[str, Any]], *, date_key: str = "match_date") -> list[str]:
    dates = {
        str(item.get(date_key) or "").strip()
        for item in items
        if isinstance(item, dict) and str(item.get(date_key) or "").strip()
    }
    return sorted(dates)


def similarity(left: object, right: object) -> float:
    left_text = norm(left)
    right_text = norm(right)
    if not left_text or not right_text:
        return 0.0
    ratio = SequenceMatcher(None, left_text, right_text).ratio()
    left_tokens = set(left_text.split())
    right_tokens = set(right_text.split())
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    return max(ratio, overlap)


def candidate_score(settlement: dict[str, Any], statsbomb: dict[str, Any]) -> float:
    direct = (
        similarity(settlement.get("home_team"), statsbomb.get("home_team"))
        + similarity(settlement.get("away_team"), statsbomb.get("away_team"))
    ) / 2.0
    swapped = (
        similarity(settlement.get("home_team"), statsbomb.get("away_team"))
        + similarity(settlement.get("away_team"), statsbomb.get("home_team"))
    ) / 2.0
    return round(max(direct, swapped), 4)


def build_coverage_audit(
    settlements: list[dict[str, Any]],
    statsbomb_items: list[dict[str, Any]],
    *,
    candidate_limit: int = 30,
    min_candidate_score: float = 0.55,
) -> dict[str, Any]:
    statsbomb_index: dict[str, dict[str, Any]] = {}
    statsbomb_by_date: dict[str, list[dict[str, Any]]] = {}
    for item in statsbomb_items:
        for key in exact_match_keys(item):
            statsbomb_index.setdefault(key, item)
        date_key = norm(item.get("match_date"))
        if date_key:
            statsbomb_by_date.setdefault(date_key, []).append(item)

    exact_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    no_same_date = 0
    settlement_dates = date_values(settlements)
    statsbomb_dates = date_values(statsbomb_items)
    overlap_dates = sorted(set(settlement_dates) & set(statsbomb_dates))
    for settlement in settlements:
        matched = None
        for key in exact_match_keys(settlement):
            if key in statsbomb_index:
                matched = statsbomb_index[key]
                break
        if matched is not None:
            exact_rows.append(
                {
                    "match_id": settlement.get("match_id"),
                    "statsbomb_source_match_id": matched.get("source_match_id"),
                    "match_date": settlement.get("match_date"),
                    "home_team": settlement.get("home_team"),
                    "away_team": settlement.get("away_team"),
                }
            )
            continue

        same_date = statsbomb_by_date.get(norm(settlement.get("match_date")), [])
        if not same_date:
            no_same_date += 1
            continue
        scored = [
            (candidate_score(settlement, item), item)
            for item in same_date
        ]
        scored.sort(key=lambda item: (-item[0], str(item[1].get("home_team") or "")))
        for score, item in scored[:3]:
            if score < min_candidate_score:
                continue
            candidates.append(
                {
                    "score": score,
                    "settlement": {
                        "match_id": settlement.get("match_id"),
                        "match_date": settlement.get("match_date"),
                        "league": settlement.get("league"),
                        "home_team": settlement.get("home_team"),
                        "away_team": settlement.get("away_team"),
                    },
                    "statsbomb": {
                        "source_match_id": item.get("source_match_id"),
                        "match_date": item.get("match_date"),
                        "league": item.get("league"),
                        "home_team": item.get("home_team"),
                        "away_team": item.get("away_team"),
                    },
                }
            )

    candidates.sort(key=lambda item: (-float(item.get("score") or 0.0), str(item.get("settlement", {}).get("match_id") or "")))
    exact_count = len(exact_rows)
    candidate_count = len(candidates)
    settlement_count = len(settlements)
    coverage_blocker = (
        "no_settlement_dates"
        if not settlement_dates
        else "no_statsbomb_dates"
        if not statsbomb_dates
        else "no_date_overlap"
        if not overlap_dates
        else None
    )
    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "settlement_count": settlement_count,
        "statsbomb_match_count": len(statsbomb_items),
        "settlement_date_count": len(settlement_dates),
        "settlement_date_start": settlement_dates[0] if settlement_dates else None,
        "settlement_date_end": settlement_dates[-1] if settlement_dates else None,
        "statsbomb_date_count": len(statsbomb_dates),
        "statsbomb_date_start": statsbomb_dates[0] if statsbomb_dates else None,
        "statsbomb_date_end": statsbomb_dates[-1] if statsbomb_dates else None,
        "date_overlap_count": len(overlap_dates),
        "date_overlap_start": overlap_dates[0] if overlap_dates else None,
        "date_overlap_end": overlap_dates[-1] if overlap_dates else None,
        "date_overlap_ratio": round(len(overlap_dates) / settlement_count, 4) if settlement_count else 0.0,
        "coverage_blocker": coverage_blocker,
        "exact_match_count": exact_count,
        "exact_match_rate": round(exact_count / settlement_count, 4) if settlement_count else 0.0,
        "candidate_count": candidate_count,
        "no_same_date_count": no_same_date,
        "same_date_unmatched_count": max(0, settlement_count - exact_count - no_same_date),
        "exact_rows": exact_rows[:candidate_limit],
        "candidate_rows": candidates[:candidate_limit],
        "recommendation": (
            "import_statsbomb_for_settlement_date_range"
            if coverage_blocker == "no_date_overlap"
            else "expand_statsbomb_import"
            if no_same_date >= max(1, settlement_count - exact_count)
            else "review_team_aliases"
            if candidate_count
            else "collect_more_overlap"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit overlap between app settlements and StatsBomb event summaries.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--candidate-limit", type=int, default=30)
    parser.add_argument("--min-candidate-score", type=float, default=0.55)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    state_dir = args.project_root / "data" / "state"
    settlements = items_from_payload(read_json(state_dir / "settlements.json"))
    statsbomb_items = items_from_payload(read_json(state_dir / "statsbomb_event_summaries.json"))
    audit = build_coverage_audit(
        settlements,
        statsbomb_items,
        candidate_limit=max(0, int(args.candidate_limit)),
        min_candidate_score=max(0.0, min(1.0, float(args.min_candidate_score))),
    )
    output_path = args.output or state_dir / "statsbomb_settlement_coverage_audit.json"
    write_json(output_path, audit)
    print(json.dumps({**audit, "output_path": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
