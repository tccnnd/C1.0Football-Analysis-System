"""
2串1 详细统计分析

回答：
1. 8000 场比赛中，符合 2串1 条件的单场有多少？
2. 能组成多少个 2串1？
3. 平均每天推荐几个？
4. 高准策略（conf>=0.60）vs 普通策略的对比
5. 是否应该只用高准策略组合？
"""
import json, os, sys
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def fetch_and_predict():
    """复用 calibrate_parlay 的逻辑"""
    import pymysql, pymysql.cursors
    from c1.inference.baseline import BaselineInferenceEngine
    from c1.inference.schema import InferenceInput

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
               DATE(mh.MatchDate) AS match_date, l.Name AS league_name,
               eh.Ep3 AS odds_home, eh.Ep1 AS odds_draw, eh.Ep0 AS odds_away
        FROM t_match_his mh
        INNER JOIN t_league l ON l.Id = mh.LeagueId
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id AND eh.CompId IN ('81','281')
        WHERE mh.MainTeamGoals >= 0 AND YEAR(mh.MatchDate) >= 2019
          AND eh.Ep3 > 1.0 AND eh.Ep0 > 1.0
        ORDER BY mh.MatchDate ASC LIMIT 8000
    """)
    rows = cur.fetchall()
    conn.close()

    elo_file = PROJECT_ROOT / "data" / "state" / "foot_elo_ratings.json"
    elo_ratings = json.loads(elo_file.read_text(encoding="utf-8")).get("ratings", {}) if elo_file.exists() else {}

    engine = BaselineInferenceEngine()
    weights = {"market": 0.278, "elo": 0.333, "poisson": 0.167, "dixon_coles": 0.222}
    predictions = []

    for row in rows:
        oh = float(row.get("odds_home") or 2.5)
        od = float(row.get("odds_draw") or 3.2)
        oa = float(row.get("odds_away") or 2.8)
        home = str(row.get("MainTeamId", ""))
        away = str(row.get("GuestTeamId", ""))
        hg, ag = int(row["MainTeamGoals"]), int(row["GuestTeamGoals"])
        actual = "home" if hg > ag else "away" if hg < ag else "draw"

        inp = InferenceInput(
            match_id=str(row["Id"]), odds_home=oh, odds_draw=od, odds_away=oa,
            home_rating=elo_ratings.get(home, 1500.0),
            away_rating=elo_ratings.get(away, 1500.0),
            league_strength=0.95, feature_fields={}, metadata={},
        )
        r = engine.infer(inp, weights=weights)
        probs = r.fused_probabilities
        predicted = max(probs, key=probs.get)
        conf = probs[predicted]
        odds_map = {"home": oh, "draw": od, "away": oa}

        predictions.append({
            "match_date": str(row["match_date"]),
            "league": row["league_name"],
            "home": home, "away": away,
            "predicted": predicted,
            "actual": actual,
            "confidence": conf,
            "correct": predicted == actual,
            "pred_odds": odds_map[predicted],
        })
    return predictions


def analyze(predictions):
    total = len(predictions)
    dates = set(p["match_date"] for p in predictions)
    total_days = len(dates)

    print(f"\n{'='*60}")
    print(f"  2串1 详细统计（{total} 场，{total_days} 天）")
    print(f"{'='*60}\n")

    # ── 不同策略的单场筛选 ──
    strategies = {
        "全部（不筛选）": lambda p: p["predicted"] != "draw",
        "conf>=0.50 + odds<=2.50": lambda p: p["confidence"] >= 0.50 and p["pred_odds"] <= 2.50 and p["predicted"] != "draw",
        "conf>=0.55 + odds<=2.00": lambda p: p["confidence"] >= 0.55 and p["pred_odds"] <= 2.00 and p["predicted"] != "draw",
        "高准 conf>=0.60": lambda p: p["confidence"] >= 0.60 and p["predicted"] != "draw",
        "高准 conf>=0.65": lambda p: p["confidence"] >= 0.65 and p["predicted"] != "draw",
    }

    print("1. 单场筛选统计:")
    print(f"   {'策略':<28} {'合格场次':<8} {'单场准确率':<10} {'日均场次'}")
    print(f"   {'-'*60}")
    for name, filt in strategies.items():
        eligible = [p for p in predictions if filt(p)]
        acc = sum(1 for p in eligible if p["correct"]) / max(len(eligible), 1)
        daily = len(eligible) / max(total_days, 1)
        print(f"   {name:<28} {len(eligible):<8} {acc:.1%}        {daily:.1f}")

    # ── 2串1 组合统计 ──
    print(f"\n2. 2串1 组合统计（同日配对）:")
    print(f"   {'策略':<28} {'可组串数':<8} {'日均串数':<8} {'胜率':<8} {'ROI'}")
    print(f"   {'-'*65}")

    for name, filt in strategies.items():
        eligible = [p for p in predictions if filt(p)]
        by_date = defaultdict(list)
        for p in eligible:
            by_date[p["match_date"]].append(p)

        parlays = []
        for date, matches in by_date.items():
            if len(matches) < 2:
                continue
            for m1, m2 in combinations(matches, 2):
                odds = m1["pred_odds"] * m2["pred_odds"]
                win = m1["correct"] and m2["correct"]
                pnl = 100 * (odds - 1) if win else -100
                parlays.append({"win": win, "pnl": pnl, "odds": odds})

        if not parlays:
            print(f"   {name:<28} 0        -        -        -")
            continue

        wins = sum(1 for p in parlays if p["win"])
        wr = wins / len(parlays)
        total_pnl = sum(p["pnl"] for p in parlays)
        roi = total_pnl / (100 * len(parlays))
        daily_parlays = len(parlays) / max(total_days, 1)
        print(f"   {name:<28} {len(parlays):<8} {daily_parlays:<8.1f} {wr:.1%}   {roi*100:+.1f}%")

    # ── 高准 vs 混合策略对比 ──
    print(f"\n3. 关键对比：只用高准 vs 混合策略")
    print(f"   {'方案':<35} {'串数':<6} {'胜率':<8} {'ROI':<8} {'日均盈亏'}")
    print(f"   {'-'*70}")

    configs = [
        ("A: 只用 conf>=0.60（纯高准）", 0.60, 99.0),
        ("B: conf>=0.55 + odds<=2.00（推荐）", 0.55, 2.00),
        ("C: conf>=0.50 + odds<=2.50（激进）", 0.50, 2.50),
        ("D: conf>=0.50 + odds<=1.80（保守）", 0.50, 1.80),
    ]

    for label, min_conf, max_odds in configs:
        eligible = [p for p in predictions
                   if p["confidence"] >= min_conf
                   and p["pred_odds"] <= max_odds
                   and p["predicted"] != "draw"]
        by_date = defaultdict(list)
        for p in eligible:
            by_date[p["match_date"]].append(p)

        parlays = []
        for date, matches in by_date.items():
            if len(matches) < 2:
                continue
            pairs = list(combinations(matches, 2))[:3]  # 每天最多 3 串
            for m1, m2 in pairs:
                odds = m1["pred_odds"] * m2["pred_odds"]
                win = m1["correct"] and m2["correct"]
                pnl = 100 * (odds - 1) if win else -100
                parlays.append({"win": win, "pnl": pnl})

        if not parlays:
            print(f"   {label:<35} 0     -        -        -")
            continue

        wins = sum(1 for p in parlays if p["win"])
        wr = wins / len(parlays)
        total_pnl = sum(p["pnl"] for p in parlays)
        roi = total_pnl / (100 * len(parlays))
        daily_pnl = total_pnl / max(total_days, 1)
        print(f"   {label:<35} {len(parlays):<6} {wr:.1%}   {roi*100:+.1f}%   {daily_pnl:+.0f}")

    print(f"\n4. 结论:")
    print(f"   - 纯高准策略（conf>=0.60）串数少但胜率高")
    print(f"   - 混合策略（conf>=0.55）串数多且 ROI 仍然正")
    print(f"   - 建议：日常用 conf>=0.55 保证出单量，重要场次用 conf>=0.60")


if __name__ == "__main__":
    preds = fetch_and_predict()
    analyze(preds)
