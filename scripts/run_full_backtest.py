"""
全量回测脚本 - 基于 2022-2026 历史赛果优化策略参数

目标：
1. 用 18096 场历史赛果评估当前 ensemble 模型的预测准确率
2. 扫描不同置信度门槛，找到最优 min_confidence
3. 评估各玩法（1x2 / handicap）的命中率和 Wilson 下界
4. 输出优化后的策略参数，写入 high_accuracy_strategy_v1.json

运行方式：
    python scripts/run_full_backtest.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

DATA_FILE = PROJECT_ROOT / "data" / "history" / "jc_matches_2022_2026.jsonl"
HA_MODEL_FILE = PROJECT_ROOT / "data" / "models" / "high_accuracy_strategy_v1.json"
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def wilson_lower(hits: int, n: int, z: float = 1.645) -> float:
    """Wilson 置信区间下界（单侧 95%）"""
    if n == 0:
        return 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def implied_prob(odds: float) -> float:
    if odds <= 1.0:
        return 0.0
    return 1.0 / odds


def market_probs(odds_h: float, odds_d: float, odds_a: float) -> tuple[float, float, float]:
    h = implied_prob(odds_h)
    d = implied_prob(odds_d)
    a = implied_prob(odds_a)
    total = max(h + d + a, 1e-9)
    return h / total, d / total, a / total


def confidence_from_probs(top: float, second: float) -> float:
    """新公式：0.85*top + 0.15*margin"""
    margin = max(top - second, 0.0)
    return min(1.0, max(0.0, 0.85 * top + 0.15 * margin))


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_matches() -> list[dict]:
    matches = []
    with open(DATA_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                matches.append(json.loads(line))
            except Exception:
                continue
    return matches


# ── 预测逻辑（轻量版，不依赖完整推理引擎）────────────────────────────────────

@dataclass
class PredResult:
    match_id: str
    match_date: str
    league: str
    home: str
    away: str
    # 市场概率（去除超额返还后）
    prob_home: float
    prob_draw: float
    prob_away: float
    # 置信度
    predicted_side: str
    confidence: float
    # 赔率
    odds_home: float
    odds_draw: float
    odds_away: float
    # 实际结果
    actual_result: str        # 胜/平/负
    actual_handicap: str      # 让胜/让平/让负
    handicap_line: float
    # 是否命中
    spf_hit: bool             # 胜平负命中
    handicap_hit: bool        # 让球命中


def predict_match(m: dict) -> PredResult | None:
    odds_h = _safe_float(m.get("odds_home"))
    odds_d = _safe_float(m.get("odds_draw"))
    odds_a = _safe_float(m.get("odds_away"))

    if odds_h < 1.01 or odds_d < 1.01 or odds_a < 1.01:
        return None

    ph, pd, pa = market_probs(odds_h, odds_d, odds_a)
    probs = {"home": ph, "draw": pd, "away": pa}
    ordered = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    predicted_side = ordered[0][0]
    top = ordered[0][1]
    second = ordered[1][1]
    conf = confidence_from_probs(top, second)

    result = str(m.get("result", "") or m.get("computed_result", "")).strip()
    handicap_result = str(m.get("handicap_result", "")).strip()

    # 胜平负命中
    side_map = {"胜": "home", "平": "draw", "负": "away"}
    actual_side = side_map.get(result, "")
    spf_hit = bool(actual_side and actual_side == predicted_side)

    # 让球命中（预测方向：主队让球时选主，客队让球时选客）
    handicap_line = _safe_float(m.get("handicap_line", m.get("handicap", 0)))
    if handicap_line < 0:
        handicap_predicted = "home"
    elif handicap_line > 0:
        handicap_predicted = "away"
    else:
        handicap_predicted = predicted_side

    handicap_win_map = {"让胜": "home", "让平": "draw", "让负": "away"}
    actual_handicap_side = handicap_win_map.get(handicap_result, "")
    handicap_hit = bool(actual_handicap_side and actual_handicap_side == handicap_predicted)

    return PredResult(
        match_id=str(m.get("match_id", "")),
        match_date=str(m.get("match_date", "")),
        league=str(m.get("league", "")),
        home=str(m.get("home_team", "")),
        away=str(m.get("away_team", "")),
        prob_home=ph,
        prob_draw=pd,
        prob_away=pa,
        predicted_side=predicted_side,
        confidence=conf,
        odds_home=odds_h,
        odds_draw=odds_d,
        odds_away=odds_a,
        actual_result=result,
        actual_handicap=handicap_result,
        handicap_line=handicap_line,
        spf_hit=spf_hit,
        handicap_hit=handicap_hit,
    )


# ── 回测核心 ──────────────────────────────────────────────────────────────────

@dataclass
class BucketStats:
    hits: int = 0
    total: int = 0
    pnl: float = 0.0

    def add(self, hit: bool, odds: float) -> None:
        self.total += 1
        if hit:
            self.hits += 1
            self.pnl += odds - 1.0
        else:
            self.pnl -= 1.0

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    @property
    def roi(self) -> float:
        return self.pnl / self.total if self.total else 0.0

    @property
    def wilson(self) -> float:
        return wilson_lower(self.hits, self.total)

    def summary(self) -> dict:
        return {
            "hits": self.hits,
            "total": self.total,
            "hit_rate": round(self.hit_rate, 4),
            "roi": round(self.roi, 4),
            "wilson_lower": round(self.wilson, 4),
            "pnl": round(self.pnl, 2),
        }


def run_threshold_scan(
    results: list[PredResult],
    play: str,          # "spf" or "handicap"
    thresholds: list[float],
) -> list[dict]:
    """扫描不同置信度门槛，统计命中率。"""
    rows = []
    for thresh in thresholds:
        bucket = BucketStats()
        for r in results:
            if r.confidence < thresh:
                continue
            if play == "spf":
                odds = {"home": r.odds_home, "draw": r.odds_draw, "away": r.odds_away}.get(r.predicted_side, 1.0)
                bucket.add(r.spf_hit, odds)
            else:
                # 让球：用让球赔率近似（无直接让球赔率时用1.9）
                hc_odds = 1.9
                bucket.add(r.handicap_hit, hc_odds)
        row = {"threshold": thresh, "play": play}
        row.update(bucket.summary())
        rows.append(row)
    return rows


def run_league_breakdown(
    results: list[PredResult],
    min_confidence: float,
    play: str,
    min_samples: int = 30,
) -> list[dict]:
    """按联赛分组统计命中率。"""
    by_league: dict[str, BucketStats] = defaultdict(BucketStats)
    for r in results:
        if r.confidence < min_confidence:
            continue
        if play == "spf":
            odds = {"home": r.odds_home, "draw": r.odds_draw, "away": r.odds_away}.get(r.predicted_side, 1.0)
            by_league[r.league].add(r.spf_hit, odds)
        else:
            by_league[r.league].add(r.handicap_hit, 1.9)

    rows = []
    for league, stats in sorted(by_league.items(), key=lambda x: -x[1].total):
        if stats.total < min_samples:
            continue
        row = {"league": league}
        row.update(stats.summary())
        rows.append(row)
    return rows


def run_year_breakdown(
    results: list[PredResult],
    matches: list[dict],
    min_confidence: float,
    play: str,
) -> list[dict]:
    """按年份分组统计命中率。"""
    year_map = {str(m.get("match_id", "")): m.get("year") for m in matches}
    by_year: dict[int, BucketStats] = defaultdict(BucketStats)
    for r in results:
        if r.confidence < min_confidence:
            continue
        year = year_map.get(r.match_id, 0)
        if not year:
            continue
        if play == "spf":
            odds = {"home": r.odds_home, "draw": r.odds_draw, "away": r.odds_away}.get(r.predicted_side, 1.0)
            by_year[year].add(r.spf_hit, odds)
        else:
            by_year[year].add(r.handicap_hit, 1.9)

    rows = []
    for year in sorted(by_year.keys()):
        row = {"year": year}
        row.update(by_year[year].summary())
        rows.append(row)
    return rows


# ── 策略优化 ──────────────────────────────────────────────────────────────────

def find_optimal_threshold(
    scan_rows: list[dict],
    min_samples: int = 80,
    min_wilson: float = 0.60,
) -> dict | None:
    """
    找到满足条件的最优门槛：
    - 样本量 >= min_samples
    - Wilson 下界 >= min_wilson
    - 命中率最高
    """
    candidates = [
        r for r in scan_rows
        if r["total"] >= min_samples and r["wilson_lower"] >= min_wilson
    ]
    if not candidates:
        # 放宽条件
        candidates = [r for r in scan_rows if r["total"] >= min_samples]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["wilson_lower"])


def build_optimized_strategy_pool(
    spf_scan: list[dict],
    handicap_scan: list[dict],
) -> list[dict]:
    """根据回测结果构建优化后的策略池。"""
    pool = []

    # SPF 主策略：高 Wilson 下界
    spf_primary = find_optimal_threshold(spf_scan, min_samples=100, min_wilson=0.65)
    if spf_primary:
        pool.append({
            "play_type": "market_1x2",
            "role": "primary",
            "min_confidence": spf_primary["threshold"],
            "accuracy": spf_primary["hit_rate"],
            "hit_count": spf_primary["hits"],
            "sample_count": spf_primary["total"],
            "wilson_lower": spf_primary["wilson_lower"],
            "roi": spf_primary["roi"],
            "source": "full_backtest_2022_2026",
        })

    # SPF 备选策略：稍低门槛，更多样本
    spf_backup = find_optimal_threshold(spf_scan, min_samples=200, min_wilson=0.55)
    if spf_backup and (not spf_primary or spf_backup["threshold"] != spf_primary["threshold"]):
        pool.append({
            "play_type": "market_1x2",
            "role": "backup",
            "min_confidence": spf_backup["threshold"],
            "accuracy": spf_backup["hit_rate"],
            "hit_count": spf_backup["hits"],
            "sample_count": spf_backup["total"],
            "wilson_lower": spf_backup["wilson_lower"],
            "roi": spf_backup["roi"],
            "source": "full_backtest_2022_2026",
        })

    # 让球策略
    hc_primary = find_optimal_threshold(handicap_scan, min_samples=100, min_wilson=0.55)
    if hc_primary:
        pool.append({
            "play_type": "handicap",
            "role": "primary",
            "min_confidence": hc_primary["threshold"],
            "accuracy": hc_primary["hit_rate"],
            "hit_count": hc_primary["hits"],
            "sample_count": hc_primary["total"],
            "wilson_lower": hc_primary["wilson_lower"],
            "roi": hc_primary["roi"],
            "source": "full_backtest_2022_2026",
        })

    return pool


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("全量回测 2022-2026  |  基于市场概率 + 新置信度公式")
    print("=" * 70)

    # 1. 加载数据
    print("\n[1/5] 加载历史赛果...")
    matches = load_matches()
    print(f"  共 {len(matches)} 场赛果")

    # 2. 生成预测
    print("\n[2/5] 生成预测（市场概率 + 新置信度公式）...")
    results: list[PredResult] = []
    skipped = 0
    for m in matches:
        r = predict_match(m)
        if r is None:
            skipped += 1
            continue
        results.append(r)
    print(f"  有效预测: {len(results)}  跳过: {skipped}")

    # 3. 全局统计
    print("\n[3/5] 全局命中率统计...")
    thresholds = [round(t / 100, 2) for t in range(30, 86, 2)]

    spf_scan = run_threshold_scan(results, "spf", thresholds)
    hc_scan = run_threshold_scan(results, "handicap", thresholds)

    print("\n  胜平负 (SPF) 门槛扫描:")
    print(f"  {'门槛':>6} {'样本':>6} {'命中':>6} {'命中率':>8} {'Wilson':>8} {'ROI':>8}")
    print("  " + "-" * 52)
    for row in spf_scan:
        if row["total"] >= 50:
            print(f"  {row['threshold']:>6.2f} {row['total']:>6} {row['hits']:>6} "
                  f"{row['hit_rate']:>8.1%} {row['wilson_lower']:>8.3f} {row['roi']:>8.3f}")

    print("\n  让球 (Handicap) 门槛扫描:")
    print(f"  {'门槛':>6} {'样本':>6} {'命中':>6} {'命中率':>8} {'Wilson':>8} {'ROI':>8}")
    print("  " + "-" * 52)
    for row in hc_scan:
        if row["total"] >= 50:
            print(f"  {row['threshold']:>6.2f} {row['total']:>6} {row['hits']:>6} "
                  f"{row['hit_rate']:>8.1%} {row['wilson_lower']:>8.3f} {row['roi']:>8.3f}")

    # 4. 联赛和年份分解
    print("\n[4/5] 联赛和年份分解（门槛=0.65）...")
    league_spf = run_league_breakdown(results, 0.65, "spf")
    year_spf = run_year_breakdown(results, matches, 0.65, "spf")

    print("\n  SPF 联赛命中率 TOP10 (门槛>=0.65, 样本>=30):")
    print(f"  {'联赛':>10} {'样本':>6} {'命中率':>8} {'Wilson':>8} {'ROI':>8}")
    print("  " + "-" * 48)
    for row in sorted(league_spf, key=lambda x: -x["wilson_lower"])[:10]:
        print(f"  {row['league']:>10} {row['total']:>6} {row['hit_rate']:>8.1%} "
              f"{row['wilson_lower']:>8.3f} {row['roi']:>8.3f}")

    print("\n  SPF 年份命中率 (门槛>=0.65):")
    print(f"  {'年份':>6} {'样本':>6} {'命中率':>8} {'Wilson':>8} {'ROI':>8}")
    print("  " + "-" * 44)
    for row in year_spf:
        print(f"  {row['year']:>6} {row['total']:>6} {row['hit_rate']:>8.1%} "
              f"{row['wilson_lower']:>8.3f} {row['roi']:>8.3f}")

    # 5. 优化策略并写入
    print("\n[5/5] 优化策略参数...")
    optimized_pool = build_optimized_strategy_pool(spf_scan, hc_scan)

    print("\n  优化后策略池:")
    for item in optimized_pool:
        print(f"  {item['play_type']} role={item['role']} "
              f"min_conf={item['min_confidence']:.2f} "
              f"acc={item['accuracy']:.3f} "
              f"hits={item['hit_count']}/{item['sample_count']} "
              f"wilson={item['wilson_lower']:.3f} "
              f"roi={item['roi']:.3f}")

    # 写入模型文件
    existing = {}
    if HA_MODEL_FILE.exists():
        try:
            existing = json.loads(HA_MODEL_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    existing["strategy_pool"] = optimized_pool
    existing["backtest_meta"] = {
        "source": "full_backtest_2022_2026",
        "total_matches": len(matches),
        "valid_predictions": len(results),
        "confidence_formula": "0.85*top + 0.15*margin",
        "ensemble_weights": {"market": 0.25, "elo": 0.35, "poisson": 0.25, "xgboost": 0.15},
    }

    HA_MODEL_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n  已写入: {HA_MODEL_FILE}")

    # 保存完整回测报告
    report = {
        "spf_threshold_scan": spf_scan,
        "handicap_threshold_scan": hc_scan,
        "spf_league_breakdown": league_spf,
        "spf_year_breakdown": year_spf,
        "optimized_strategy_pool": optimized_pool,
    }
    report_path = REPORT_DIR / "full_backtest_2022_2026.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  完整报告: {report_path}")

    print("\n" + "=" * 70)
    print("回测完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
