from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


def _bootstrap(project_root: Path) -> None:
    root = project_root.resolve()
    src = root / "src"
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text)


def _load_cfg(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_api_header(project_root: Path) -> dict[str, str]:
    cfg_path = project_root / "c1" / "configs" / "availability_sources.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    key = ""
    for line in text.splitlines():
        if "x-apisports-key:" in line:
            key = line.split(":", 1)[1].strip()
            break
    if not key:
        raise RuntimeError("x-apisports-key not found in availability_sources.yaml")
    return {
        "x-apisports-key": key,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }


def _fixture_time(date_text: str) -> str:
    try:
        return datetime.fromisoformat(str(date_text).replace("Z", "+00:00")).strftime("%H:%M")
    except Exception:
        return ""


def _fetch_api_fixtures(headers: dict[str, str], date_text: str) -> list[dict]:
    url = f"https://v3.football.api-sports.io/fixtures?date={date_text}&timezone=Asia/Shanghai"
    response = requests.get(url, headers=headers, timeout=25)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("response", [])
    return rows if isinstance(rows, list) else []


def _build_candidate_index(fixtures: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    index: dict[tuple[str, str, str], list[dict]] = {}
    for item in fixtures:
        if not isinstance(item, dict):
            continue
        fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
        league = item.get("league") if isinstance(item.get("league"), dict) else {}
        teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
        date_text = str((fixture or {}).get("date", "")).split("T", 1)[0]
        match_time = _fixture_time((fixture or {}).get("date", ""))
        league_name = str((league or {}).get("name", "")).strip()
        if not date_text or not match_time or not league_name:
            continue
        key = (date_text, match_time, league_name)
        index.setdefault(key, []).append(item)
    return index


def _team_match(candidate: dict, home_alias: str, away_alias: str) -> bool:
    teams = candidate.get("teams") if isinstance(candidate.get("teams"), dict) else {}
    home_name = str((teams.get("home") or {}).get("name", "")).strip()
    away_name = str((teams.get("away") or {}).get("name", "")).strip()
    if not home_alias or not away_alias:
        return False
    home_alias_norm = _norm(home_alias)
    away_alias_norm = _norm(away_alias)
    home_norm = _norm(home_name)
    away_norm = _norm(away_name)
    home_ok = home_alias_norm in home_norm or home_norm in home_alias_norm
    away_ok = away_alias_norm in away_norm or away_norm in away_alias_norm
    return home_ok and away_ok


def _to_fixture_id(candidate: dict) -> str:
    fixture = candidate.get("fixture") if isinstance(candidate.get("fixture"), dict) else {}
    return str((fixture or {}).get("id", "")).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build C1 bridge map from V24 source_id to API-Football fixture_id.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default="data/c1_state/source_id_bridge.json")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    _bootstrap(project_root)

    from v24_app.core import fetch_matches_v24

    cfg = _load_cfg(project_root / "c1" / "configs" / "source_bridge_cfg.json")
    league_alias = cfg.get("league_alias_zh_to_en", {}) if isinstance(cfg.get("league_alias_zh_to_en"), dict) else {}
    team_alias = cfg.get("team_alias_zh_to_en", {}) if isinstance(cfg.get("team_alias_zh_to_en"), dict) else {}
    headers = _load_api_header(project_root)

    fetch_result = fetch_matches_v24(strict_today=True)
    matches = list(fetch_result.matches)
    dates = sorted({str(m.match_date) for m in matches})
    all_fixtures: list[dict] = []
    for date_text in dates:
        all_fixtures.extend(_fetch_api_fixtures(headers=headers, date_text=date_text))
    candidate_index = _build_candidate_index(all_fixtures)

    mappings: list[dict] = []
    unresolved: list[dict] = []
    mapping_dict: dict[str, str] = {}

    for match in matches:
        date_text = str(match.match_date)
        match_time = str(match.match_time)
        league_name = str(league_alias.get(str(match.league), str(match.league)))
        key = (date_text, match_time, league_name)
        candidates = list(candidate_index.get(key, []))
        reason = ""
        if len(candidates) == 1:
            reason = "unique_league_time"
        elif len(candidates) > 1:
            home_alias = str(team_alias.get(str(match.home_team), ""))
            away_alias = str(team_alias.get(str(match.away_team), ""))
            narrowed = [item for item in candidates if _team_match(item, home_alias=home_alias, away_alias=away_alias)]
            if len(narrowed) == 1:
                candidates = narrowed
                reason = "team_alias_disambiguated"
            else:
                candidates = narrowed if narrowed else candidates

        if len(candidates) == 1:
            fixture_id = _to_fixture_id(candidates[0])
            if fixture_id and str(match.source_id):
                mapping_dict[str(match.source_id)] = fixture_id
                mappings.append(
                    {
                        "v24_source_id": str(match.source_id),
                        "api_source_id": fixture_id,
                        "match_id": str(match.match_id),
                        "match_date": date_text,
                        "match_time": match_time,
                        "league": str(match.league),
                        "home_team": str(match.home_team),
                        "away_team": str(match.away_team),
                        "reason": reason or "single_candidate",
                    }
                )
                continue

        unresolved.append(
            {
                "v24_source_id": str(match.source_id),
                "match_id": str(match.match_id),
                "match_date": date_text,
                "match_time": match_time,
                "league": str(match.league),
                "home_team": str(match.home_team),
                "away_team": str(match.away_team),
                "candidate_count": len(candidates),
                "league_key": league_name,
            }
        )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_matches": len(matches),
        "mapped_count": len(mappings),
        "unresolved_count": len(unresolved),
        "source_id_map": mapping_dict,
        "mappings": mappings,
        "unresolved": unresolved,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
