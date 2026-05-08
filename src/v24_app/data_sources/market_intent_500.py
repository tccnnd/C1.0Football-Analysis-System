from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


COMPANY_NAME_MAP = {
    2: "立博",
    3: "Bet365",
    5: "澳门",
    6: "韦德",
    8: "SNAI",
    9: "易胜博",
    280: "皇冠",
    293: "威廉",
}
TARGET_COMPANY_IDS = (3, 293, 2, 280, 5)


@dataclass
class FixtureIndex500:
    fixture_id: str
    match_date: str
    league: str
    home_team: str
    away_team: str


@dataclass
class MarketIntentSnapshot:
    opening_odds_home: float = 0.0
    opening_odds_draw: float = 0.0
    opening_odds_away: float = 0.0
    instant_odds_home: float = 0.0
    instant_odds_draw: float = 0.0
    instant_odds_away: float = 0.0
    return_rate: float = 0.0
    kelly_home: float = 0.0
    kelly_draw: float = 0.0
    kelly_away: float = 0.0
    companies: list[str] | None = None
    fixture_id: str = ""


class MarketIntentFetcher500:
    def __init__(self, project_dir: Path, debug: bool = False) -> None:
        self.project_dir = Path(project_dir)
        self.debug = debug
        self.cache_dir = self.project_dir / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            text = str(value).strip().replace("%", "")
            return float(text) if text else default
        except Exception:
            return default

    @staticmethod
    def _looks_suspect_text(text: str) -> bool:
        content = str(text or "")
        return not content or "\ufffd" in content

    @staticmethod
    def _decode_content(content: bytes, preferred: str) -> str:
        encodings: list[str] = []
        for item in (preferred, "gb18030", "gbk", "gb2312", "utf-8"):
            if item and item not in encodings:
                encodings.append(item)
        for encoding in encodings:
            try:
                decoded = content.decode(encoding)
            except Exception:
                continue
            if not MarketIntentFetcher500._looks_suspect_text(decoded):
                return decoded
        for encoding in encodings:
            try:
                return content.decode(encoding, errors="ignore")
            except Exception:
                continue
        return ""

    @staticmethod
    def _normalize_team_name(name: str) -> str:
        text = str(name or "").strip().lower()
        text = re.sub(r"\(.*?\)|（.*?）", "", text)
        for token in ("fc", "u23", "u21", "u20", "队", "国家队", "女足", "男足"):
            text = text.replace(token, "")
        text = text.replace(" ", "")
        text = re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", text)
        return text

    @staticmethod
    def _team_score(left: str, right: str) -> int:
        if not left or not right:
            return 0
        if left == right:
            return 4
        if left in right or right in left:
            return 2
        return 0

    def _cache_read(self, path: Path, max_age_seconds: int) -> str | None:
        if not path.exists():
            return None
        age = datetime.now().timestamp() - path.stat().st_mtime
        if age > max_age_seconds:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None
        return None if self._looks_suspect_text(text) else text

    def _cache_write(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def _fetch_text(self, url: str, cache_name: str, encoding: str, max_age_seconds: int) -> str | None:
        cache_path = self.cache_dir / cache_name
        cached = self._cache_read(cache_path, max_age_seconds=max_age_seconds)
        if cached is not None:
            return cached
        try:
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            text = self._decode_content(response.content, preferred=encoding)
            if text:
                self._cache_write(cache_path, text)
                return text
        except Exception as exc:
            if self.debug:
                logger.warning("500 fetch failed %s: %s", url, exc)
        try:
            text = cache_path.read_text(encoding="utf-8")
        except Exception:
            return None
        return None if self._looks_suspect_text(text) else text

    def get_index_matches(self, match_date: str) -> list[FixtureIndex500]:
        url = f"https://m.500.com/info/odds/index_jczq_{match_date}.shtml"
        text = self._fetch_text(
            url=url,
            cache_name=f"m500_odds_index_{match_date}.html",
            encoding="gb18030",
            max_age_seconds=900,
        )
        if not text:
            return []
        soup = BeautifulSoup(text, "html.parser")
        fixtures: list[FixtureIndex500] = []
        for node in soup.select("div.zhis-col[fixture]"):
            fixture_id = str(node.get("fixture", "")).strip()
            if not fixture_id:
                continue
            league_node = node.select_one(".zhis-time em")
            team_nodes = node.select(".zhis-team span span")
            if len(team_nodes) < 2:
                continue
            home_team = team_nodes[0].get_text(strip=True)
            away_team = team_nodes[1].get_text(strip=True)
            if self._looks_suspect_text(home_team) or self._looks_suspect_text(away_team):
                continue
            fixtures.append(
                FixtureIndex500(
                    fixture_id=fixture_id,
                    match_date=match_date,
                    league=(league_node.get_text(strip=True) if league_node else ""),
                    home_team=home_team,
                    away_team=away_team,
                )
            )
        return fixtures

    @staticmethod
    def _parse_nested_triplets(cell) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        rows = cell.select("tr")
        parsed: list[tuple[float, float, float]] = []
        for row in rows[:2]:
            values = [MarketIntentFetcher500._safe_float(td.get_text(strip=True)) for td in row.find_all("td")]
            while len(values) < 3:
                values.append(0.0)
            parsed.append((values[0], values[1], values[2]))
        while len(parsed) < 2:
            parsed.append((0.0, 0.0, 0.0))
        return parsed[0], parsed[1]

    @staticmethod
    def _parse_nested_single(cell) -> tuple[float, float]:
        rows = cell.select("tr")
        values: list[float] = []
        for row in rows[:2]:
            td = row.find("td")
            values.append(MarketIntentFetcher500._safe_float(td.get_text(strip=True) if td else 0.0))
        while len(values) < 2:
            values.append(0.0)
        current = values[1] if len(values) > 1 and values[1] > 0 else values[0]
        return values[0], current

    def get_market_snapshot(self, fixture_id: str) -> MarketIntentSnapshot | None:
        text = self._fetch_text(
            url=f"https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml",
            cache_name=f"500_ouzhi_{fixture_id}.html",
            encoding="gb18030",
            max_age_seconds=1800,
        )
        if not text:
            return None
        soup = BeautifulSoup(text, "html.parser")
        rows = soup.select("tr.tr1[ttl='zy'], tr.tr2[ttl='zy']")
        company_rows: list[dict] = []
        for row in rows:
            company_id = int(self._safe_float(row.get("id"), default=0))
            if company_id not in TARGET_COMPANY_IDS:
                continue
            cells = row.find_all("td", recursive=False)
            if len(cells) < 5:
                continue
            opening_odds, instant_odds = self._parse_nested_triplets(cells[2])
            detail_tables = cells[4].select("table.pl_table_data")
            if len(detail_tables) < 2:
                continue
            _, current_return = self._parse_nested_single(detail_tables[0])
            _, current_kelly = self._parse_nested_triplets(detail_tables[1])
            company_rows.append(
                {
                    "company_id": company_id,
                    "company_name": COMPANY_NAME_MAP.get(company_id, str(company_id)),
                    "opening_odds": opening_odds,
                    "instant_odds": instant_odds,
                    "return_rate": current_return / 100.0 if current_return > 1.0 else current_return,
                    "kelly": current_kelly,
                }
            )
        if not company_rows:
            return None
        count = float(len(company_rows))
        return MarketIntentSnapshot(
            opening_odds_home=round(sum(item["opening_odds"][0] for item in company_rows) / count, 4),
            opening_odds_draw=round(sum(item["opening_odds"][1] for item in company_rows) / count, 4),
            opening_odds_away=round(sum(item["opening_odds"][2] for item in company_rows) / count, 4),
            instant_odds_home=round(sum(item["instant_odds"][0] for item in company_rows) / count, 4),
            instant_odds_draw=round(sum(item["instant_odds"][1] for item in company_rows) / count, 4),
            instant_odds_away=round(sum(item["instant_odds"][2] for item in company_rows) / count, 4),
            return_rate=round(sum(item["return_rate"] for item in company_rows) / count, 4),
            kelly_home=round(sum(item["kelly"][0] for item in company_rows) / count, 4),
            kelly_draw=round(sum(item["kelly"][1] for item in company_rows) / count, 4),
            kelly_away=round(sum(item["kelly"][2] for item in company_rows) / count, 4),
            companies=[str(item["company_name"]) for item in company_rows],
            fixture_id=str(fixture_id),
        )

    def _match_fixture(
        self,
        match_date: str,
        home_team: str,
        away_team: str,
        candidates: list[FixtureIndex500],
    ) -> FixtureIndex500 | None:
        home_key = self._normalize_team_name(home_team)
        away_key = self._normalize_team_name(away_team)
        ranked: list[tuple[int, FixtureIndex500]] = []
        for item in candidates:
            if item.match_date != match_date:
                continue
            score = self._team_score(home_key, self._normalize_team_name(item.home_team))
            score += self._team_score(away_key, self._normalize_team_name(item.away_team))
            if score <= 0:
                continue
            ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].fixture_id))
        return ranked[0][1] if ranked and ranked[0][0] >= 4 else None

    def enrich_matches(self, matches: list[object]) -> int:
        if not matches:
            return 0
        dates = sorted(
            {
                str(getattr(match, "match_date", "")).strip()
                for match in matches
                if getattr(match, "match_date", "")
            }
        )
        index_map: dict[str, list[FixtureIndex500]] = {date: self.get_index_matches(date) for date in dates}
        enriched = 0
        for match in matches:
            match_date = str(getattr(match, "match_date", "")).strip()
            if not match_date:
                continue
            fixture = self._match_fixture(
                match_date=match_date,
                home_team=str(getattr(match, "home_team", "")),
                away_team=str(getattr(match, "away_team", "")),
                candidates=index_map.get(match_date, []),
            )
            if fixture is None:
                continue
            snapshot = self.get_market_snapshot(fixture.fixture_id)
            if snapshot is None:
                continue
            setattr(match, "opening_odds_home", snapshot.opening_odds_home)
            setattr(match, "opening_odds_draw", snapshot.opening_odds_draw)
            setattr(match, "opening_odds_away", snapshot.opening_odds_away)
            setattr(match, "return_rate", snapshot.return_rate)
            setattr(match, "kelly_home", snapshot.kelly_home)
            setattr(match, "kelly_draw", snapshot.kelly_draw)
            setattr(match, "kelly_away", snapshot.kelly_away)
            enriched += 1
        return enriched
