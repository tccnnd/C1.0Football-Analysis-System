"""
2串1策略回测与优化

用历史数据模拟 2串1 投注，找出最优条件组合。

计算：
1. 不同置信度门槛下的 2串1 胜率和 ROI
2. 最优赔率范围
3. 联赛组合关联性分析
4. 模拟资金曲线
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def fetch_data(since_year: int = 2019, limit: int = 8000) -> list[dict]:
    import pymysql, pymysql.cursors
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root",
        password=os.environ.get("FOOT_MYSQL_PASSWORD", "Meta.123"),
        database="foot", charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT mh.Id, mh.MainTeamId, mh.GuestTeamId,
               mh.MainTeamGoals, mh.GuestTeamGoals,
               DATE(mh.MatchDate) AS match_date,
               l.Name AS league_name,
               eh.Ep3 AS odds_home, eh.Ep1 AS odds_draw, eh.Ep0 AS odds_away
        FROM t_match_his mh
        INNER JOIN t_league l ON l.Id = mh.LeagueId
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id AND eh.CompId IN ('81','281')
        WHERE mh.MainTeamGoals >= 0 AND YEAR(mh.MatchDate) >= %s
          AND eh.Ep3 > 1.0 AND eh.Ep0 > 1.0
        ORDER BY mh.MatchDate ASC LIMIT %s
    """, (since_year, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def predict_batch(rows: list[dict], elo_ratings: dict) -> list[dict]:
    """批量预测，返回每场的预测结果"""
    from c1.inference.baseline import BaselineInferenceEngine
    from c1.inference.schema import InferenceInput

    engine = BaselineInferenceEngine()
    weights = {"market": 0.278, "elo": 0.333, "poisson": 0.167, "dixon_coles": 0.222}
    results = []

    for row in rows:
        oh = float(row.get("odds_home") or 2.5)
        od = float(row.get("odds_draw") or 3.2)
        oa = float(row.get("odds_away") or 2.8)
        home = str(row.get("MainTeamId", ""))
        away = str(row.get("GuestTeamId", ""))
        hg = int(row.get("MainTeamGoals", -1))
        ag = int(row.get("GuestTeamGoals", -1))

        actual = "home" if hg > ag else "away" if hg < ag else "draw"

        inp = InferenceInput(
            match_id=str(row.get("Id", "")),
            odds_home=oh, odds_draw=od, odds_away=oa,
            home_rating=elo_ratings.get(home, 1500.0),
            away_rating=elo_ratings.get(away, 1500.0),
            league_strength=0.95, feature_fields={}, metadata={},
        )
        r = engine.infer(inp, weights=weights)
        probs = r.fused_probabilities
        predicted = max(probs, key=probs.get)
        conf = probs[predicted]

        # 预测方向对应的赔率
        odds_map = {"home": oh, "draw": od, "away": oa}
        pred_odds = odds_map.get(predicted, 2.0)

        results.append({
            "match_id": row.get("Id"),
            "match_date": str(row.get("match_date", "")),
            "league": row.get("league_name", ""),
            "predicted": predicted,
            "actual": actual,
            "confidence": conf,
            "correct": predicted == actual,
            "pred_odds": pred_odds,
            "odds_home": oh,
            "odds_draw": od,
            "odds_away": oa,
        })
    return results


def simulate_parlay(
    predictions: list[dict],
    min_confidence: float = 0.55,
    max_odds: float = 2.50,
    min_odds: float = 1.20,
    stake: float = 100.0,
    same_day_only: bool = True,
) -> dict:
    """
    模拟 2串1 投注策略

    筛选条件：
    - 置信度 >= min_confidence
    - 预测方向赔率在 [min_odds, max_odds] 范围内
    - 同一天的比赛配对（same_day_only=True）
    """
    # 筛选合格的单场
    eligible = [
        p for p in predictions
        if p["confidence"] >= min_confidence
        and min_odds <= p["pred_odds"] <= max_odds
        and p["predicted"] != "draw"  # 2串1 通常不选平局
    ]

    if len(eligible) < 2:
        return {"parlays": 0, "profit": 0, "roi": 0, "win_rate": 0}

    # 按日期分组
    by_date = defaultdict(list)
    for p in eligible:
        by_date[p["match_date"]].append(p)

    # 生成 2串1 组合
    parlays = []
    for date, matches in by_date.items():
        if len(matches) < 2:
            continue
        # 每天最多取 3 个 2串1（避免过度投注）
        pairs = list(combinations(matches, 2))[:3]
        for m1, m2 in pairs:
            parlay_odds = m1["pred_odds"] * m2["pred_odds"]
            both_correct = m1["correct"] and m2["correct"]
            pnl = stake * (parlay_odds - 1) if both_correct else -stake
            parlays.append({
                "date": date,
                "leg1": f"{m1['league']} conf={m1['confidence']:.2f} odds={m1['pred_odds']:.2f}",
                "leg2": f"{m2['league']} conf={m2['confidence']:.2f} odds={m2['pred_odds']:.2f}",
                "parlay_odds": round(parlay_odds, 2),
                "leg1_correct": m1["correct"],
                "leg2_correct": m2["correct"],
                "both_correct": both_correct,
                "pnl": round(pnl, 2),
            })

    if not parlays:
        return {"parlays": 0, "profit": 0, "roi": 0, "win_rate": 0}

    total_stake = stake * len(parlays)
    total_pnl = sum(p["pnl"] for p in parlays)
    wins = sum(1 for p in parlays if p["both_correct"])
    win_rate = wins / len(parlays)
    roi = total_pnl / total_stake

    return {
        "parlays": len(parlays),
        "wins": wins,
        "losses": len(parlays) - wins,
        "win_rate": round(win_rate, 4),
        "total_stake": round(total_stake, 2),
        "total_pnl": round(total_pnl, 2),
        "roi": round(roi, 4),
        "avg_parlay_odds": round(np.mean([p["parlay_odds"] for p in parlays]), 2),
        "best_streak": _best_streak(parlays),
        "worst_streak": _worst_streak(parlays),
    }


def _best_streak(parlays):
    best = current = 0
    for p in parlays:
        if p["both_correct"]:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _worst_streak(parlays):
    worst = current = 0
    for p in parlays:
        if not p["both_correct"]:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


def main():
    print(f"\n{'='*60}")
    print(f"  2串1 策略回测与优化")
    print(f"{'='*60}\n")

    # 1. 加载数据
    print("1. 加载数据...")
    rows = fetch_data(since_year=2019, limit=8000)
    print(f"   {len(rows)} 场比赛")

    elo_file = PROJECT_ROOT / "data" / "state" / "foot_elo_ratings.json"
    elo_ratings = {}
    if elo_file.exists():
        elo_ratings = json.loads(elo_file.read_text(encoding="utf-8")).get("ratings", {})

    # 2. 批量预测
    print("2. 批量预测...")
    t0 = time.time()
    predictions = predict_batch(rows, elo_ratings)
    print(f"   完成 {len(predictions)} 场  耗时 {time.time()-t0:.0f}s")

    # 单场基线
    single_acc = sum(1 for p in predictions if p["correct"]) / len(predictions)
    print(f"   单场准确率: {single_acc:.1%}")

    # 3. 搜索最优 2串1 参数
    print("\n3. 搜索最优 2串1 参数...")
    print(f"   {'置信度':<8} {'赔率范围':<14} {'串数':<6} {'胜率':<8} {'ROI':<8} {'盈亏'}")
    print(f"   {'-'*60}")

    best_roi = -999
    best_params = {}
    all_results = []

    for min_conf in [0.50, 0.55, 0.58, 0.60, 0.63, 0.65]:
        for max_odds in [1.80, 2.00, 2.20, 2.50]:
            result = simulate_parlay(
                predictions,
                min_confidence=min_conf,
                max_odds=max_odds,
                min_odds=1.20,
                stake=100,
            )
            if result["parlays"] < 10:
                continue
            all_results.append({
                "min_confidence": min_conf,
                "max_odds": max_odds,
                **result,
            })
            roi_pct = result["roi"] * 100
            print(f"   {min_conf:.2f}    [1.20-{max_odds:.2f}]    {result['parlays']:<6} {result['win_rate']:.1%}   {roi_pct:+.1f}%   {result['total_pnl']:+.0f}")
            if result["roi"] > best_roi:
                best_roi = result["roi"]
                best_params = {"min_confidence": min_conf, "max_odds": max_odds}

    # 4. 最优策略详情
    print(f"\n4. 最优 2串1 策略:")
    if best_params:
        best_result = simulate_parlay(
            predictions,
            min_confidence=best_params["min_confidence"],
            max_odds=best_params["max_odds"],
        )
        print(f"   条件: 置信度 >= {best_params['min_confidence']:.2f}, 赔率 <= {best_params['max_odds']:.2f}")
        print(f"   总串数: {best_result['parlays']}")
        print(f"   胜率: {best_result['win_rate']:.1%}")
        print(f"   ROI: {best_result['roi']*100:+.1f}%")
        print(f"   总盈亏: {best_result['total_pnl']:+.0f} (投入 {best_result['total_stake']:.0f})")
        print(f"   平均串赔率: {best_result['avg_parlay_odds']:.2f}")
        print(f"   最长连赢: {best_result['best_streak']}")
        print(f"   最长连输: {best_result['worst_streak']}")

    # 5. 盈亏平衡分析
    print(f"\n5. 盈亏平衡分析:")
    for r in sorted(all_results, key=lambda x: -x["roi"])[:5]:
        avg_odds = r["avg_parlay_odds"]
        breakeven = 1.0 / avg_odds
        margin = r["win_rate"] - breakeven
        status = "✅ 盈利" if margin > 0 else "❌ 亏损"
        print(f"   conf>={r['min_confidence']:.2f} odds<={r['max_odds']:.2f}: "
              f"胜率{r['win_rate']:.1%} 平衡点{breakeven:.1%} 边际{margin:+.1%} {status}")

    # 6. 保存
    output = {
        "calibrated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "single_accuracy": round(single_acc, 4),
        "best_parlay_params": best_params,
        "best_parlay_roi": round(best_roi, 4),
        "all_results": sorted(all_results, key=lambda x: -x["roi"])[:10],
    }
    out_file = PROJECT_ROOT / "data" / "models" / "parlay_strategy_c1.json"
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n6. 保存到: {out_file}")

    print(f"\n{'='*60}")
    print(f"  回测完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
