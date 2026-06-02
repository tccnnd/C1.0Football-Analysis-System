"""
策略校准：用历史数据优化 ensemble 权重和高准策略筛选

1. Ensemble 权重优化（grid search）
2. 高准策略条件筛选（找出 >60% 准确率的组合）
3. 输出最优配置到 data/models/

用法：
    python calibrate_strategy.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

MODELS_DIR = PROJECT_ROOT / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ── 数据获取 ──────────────────────────────────────────────────────────────────

def fetch_calibration_data(since_year: int = 2021, limit: int = 10000) -> list[dict]:
    """获取有欧赔的历史比赛"""
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
               eh.Sp3 AS euro_sp3, eh.Sp1 AS euro_sp1, eh.Sp0 AS euro_sp0,
               eh.Ep3 AS euro_ep3, eh.Ep1 AS euro_ep1, eh.Ep0 AS euro_ep0
        FROM t_match_his mh
        INNER JOIN t_league l ON l.Id = mh.LeagueId
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id AND eh.CompId IN ('81', '281')
        WHERE mh.MainTeamGoals >= 0
          AND YEAR(mh.MatchDate) >= %s
          AND eh.Ep3 > 1.0 AND eh.Ep0 > 1.0
        ORDER BY mh.MatchDate ASC
        LIMIT %s
    """, (since_year, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def actual_result(row: dict) -> str:
    hg = int(row.get("MainTeamGoals", -1))
    ag = int(row.get("GuestTeamGoals", -1))
    if hg > ag: return "home"
    if hg < ag: return "away"
    return "draw"


# ── 模型预测 ──────────────────────────────────────────────────────────────────

def predict_with_weights(row: dict, weights: dict[str, float], elo_ratings: dict) -> dict:
    """用指定权重预测单场比赛"""
    from c1.inference.baseline import BaselineInferenceEngine
    from c1.inference.schema import InferenceInput

    odds_home = float(row.get("euro_ep3") or 2.5)
    odds_draw = float(row.get("euro_ep1") or 3.2)
    odds_away = float(row.get("euro_ep0") or 2.8)

    home_team = str(row.get("MainTeamId", ""))
    away_team = str(row.get("GuestTeamId", ""))
    home_elo = elo_ratings.get(home_team, 1500.0)
    away_elo = elo_ratings.get(away_team, 1500.0)

    inp = InferenceInput(
        match_id=str(row.get("Id", "")),
        odds_home=odds_home, odds_draw=odds_draw, odds_away=odds_away,
        home_rating=home_elo, away_rating=away_elo,
        league_strength=0.95,
        feature_fields={},
        metadata={},
    )

    engine = _get_engine()
    result = engine.infer(inp, weights=weights)
    return {
        "predicted_side": result.fused_probabilities,
        "confidence": max(result.fused_probabilities.values()),
        "predicted": max(result.fused_probabilities, key=result.fused_probabilities.get),
    }


_ENGINE_CACHE = None
def _get_engine():
    global _ENGINE_CACHE
    if _ENGINE_CACHE is None:
        from c1.inference.baseline import BaselineInferenceEngine
        _ENGINE_CACHE = BaselineInferenceEngine()
    return _ENGINE_CACHE


def batch_predict(rows: list[dict], weights: dict[str, float], elo_ratings: dict) -> list[dict]:
    """批量预测"""
    from c1.inference.baseline import BaselineInferenceEngine
    from c1.inference.schema import InferenceInput

    engine = _get_engine()
    results = []
    for row in rows:
        odds_home = float(row.get("euro_ep3") or 2.5)
        odds_draw = float(row.get("euro_ep1") or 3.2)
        odds_away = float(row.get("euro_ep0") or 2.8)
        home_team = str(row.get("MainTeamId", ""))
        away_team = str(row.get("GuestTeamId", ""))

        inp = InferenceInput(
            match_id=str(row.get("Id", "")),
            odds_home=odds_home, odds_draw=odds_draw, odds_away=odds_away,
            home_rating=elo_ratings.get(home_team, 1500.0),
            away_rating=elo_ratings.get(away_team, 1500.0),
            league_strength=0.95,
            feature_fields={}, metadata={},
        )
        r = engine.infer(inp, weights=weights)
        probs = r.fused_probabilities
        predicted = max(probs, key=probs.get)
        conf = probs[predicted]
        actual = actual_result(row)
        results.append({
            "predicted": predicted,
            "actual": actual,
            "confidence": conf,
            "correct": predicted == actual,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
            "probs": probs,
        })
    return results


# ── 权重优化 ──────────────────────────────────────────────────────────────────

def grid_search_weights(train_rows: list[dict], elo_ratings: dict) -> dict:
    """预计算各模型输出，然后纯数学搜索最优权重（极快）"""
    from c1.inference.baseline import BaselineInferenceEngine
    from c1.inference.schema import InferenceInput

    engine = _get_engine()
    print("  预计算各模型输出...")

    # 预计算每场比赛每个模型的概率
    model_outputs = []  # [{model_name: {home, draw, away}}, ...]
    actuals = []

    for row in train_rows:
        odds_home = float(row.get("euro_ep3") or 2.5)
        odds_draw = float(row.get("euro_ep1") or 3.2)
        odds_away = float(row.get("euro_ep0") or 2.8)
        home_team = str(row.get("MainTeamId", ""))
        away_team = str(row.get("GuestTeamId", ""))

        inp = InferenceInput(
            match_id="cal", odds_home=odds_home, odds_draw=odds_draw, odds_away=odds_away,
            home_rating=elo_ratings.get(home_team, 1500.0),
            away_rating=elo_ratings.get(away_team, 1500.0),
            league_strength=0.95, feature_fields={}, metadata={},
        )
        r = engine.infer(inp, weights={"market": 0.25, "elo": 0.25, "poisson": 0.25, "dixon_coles": 0.25})
        components = {c.name: c.probabilities for c in r.components}
        model_outputs.append(components)
        actuals.append(actual_result(row))

    print(f"  预计算完成: {len(model_outputs)} 场")

    # 纯数学搜索（极快，不需要再调用推理引擎）
    print("  搜索最优权重...")
    model_names = ["market", "elo", "poisson", "dixon_coles"]
    best_acc = 0.0
    best_weights = {}
    tested = 0

    for market in np.arange(0.25, 0.55, 0.05):
        for elo in np.arange(0.10, 0.35, 0.05):
            for poisson in np.arange(0.05, 0.25, 0.05):
                for dc in np.arange(0.05, 0.25, 0.05):
                    total = market + elo + poisson + dc
                    if total < 0.8 or total > 1.05:
                        continue
                    # 归一化
                    w = {"market": market/total, "elo": elo/total, "poisson": poisson/total, "dixon_coles": dc/total}

                    correct = 0
                    for i, components in enumerate(model_outputs):
                        # 加权融合
                        h = sum(components.get(m, {}).get("home", 0.33) * w[m] for m in model_names)
                        d = sum(components.get(m, {}).get("draw", 0.33) * w[m] for m in model_names)
                        a = sum(components.get(m, {}).get("away", 0.33) * w[m] for m in model_names)
                        predicted = "home" if h >= d and h >= a else "draw" if d >= a else "away"
                        if predicted == actuals[i]:
                            correct += 1

                    acc = correct / len(actuals)
                    tested += 1
                    if acc > best_acc:
                        best_acc = acc
                        best_weights = {k: round(v, 3) for k, v in w.items()}

    print(f"  测试了 {tested} 种组合")
    return {"weights": best_weights, "accuracy": best_acc}


# ── 高准策略筛选 ──────────────────────────────────────────────────────────────

def find_high_accuracy_conditions(results: list[dict]) -> list[dict]:
    """找出准确率 > 55% 的条件组合"""
    strategies = []

    # 条件 1：高置信度
    for conf_threshold in [0.45, 0.50, 0.55, 0.60, 0.65]:
        filtered = [r for r in results if r["confidence"] >= conf_threshold]
        if len(filtered) < 20:
            continue
        acc = sum(1 for r in filtered if r["correct"]) / len(filtered)
        if acc >= 0.55:
            strategies.append({
                "condition": f"confidence >= {conf_threshold:.2f}",
                "accuracy": round(acc, 4),
                "sample_size": len(filtered),
                "coverage": round(len(filtered) / len(results), 4),
            })

    # 条件 2：高置信度 + 非平局预测
    for conf_threshold in [0.40, 0.45, 0.50]:
        filtered = [r for r in results if r["confidence"] >= conf_threshold and r["predicted"] != "draw"]
        if len(filtered) < 20:
            continue
        acc = sum(1 for r in filtered if r["correct"]) / len(filtered)
        if acc >= 0.55:
            strategies.append({
                "condition": f"confidence >= {conf_threshold:.2f} AND predicted != draw",
                "accuracy": round(acc, 4),
                "sample_size": len(filtered),
                "coverage": round(len(filtered) / len(results), 4),
            })

    # 条件 3：赔率范围（热门比赛）
    for max_odds in [1.60, 1.80, 2.00]:
        filtered = [r for r in results if min(r["odds_home"], r["odds_away"]) <= max_odds]
        if len(filtered) < 20:
            continue
        acc = sum(1 for r in filtered if r["correct"]) / len(filtered)
        if acc >= 0.55:
            strategies.append({
                "condition": f"min_odds <= {max_odds:.2f} (热门)",
                "accuracy": round(acc, 4),
                "sample_size": len(filtered),
                "coverage": round(len(filtered) / len(results), 4),
            })

    # 条件 4：高置信度 + 热门
    for conf in [0.45, 0.50]:
        for max_odds in [1.80, 2.00]:
            filtered = [r for r in results
                       if r["confidence"] >= conf
                       and min(r["odds_home"], r["odds_away"]) <= max_odds]
            if len(filtered) < 15:
                continue
            acc = sum(1 for r in filtered if r["correct"]) / len(filtered)
            if acc >= 0.58:
                strategies.append({
                    "condition": f"confidence >= {conf:.2f} AND min_odds <= {max_odds:.2f}",
                    "accuracy": round(acc, 4),
                    "sample_size": len(filtered),
                    "coverage": round(len(filtered) / len(results), 4),
                })

    return sorted(strategies, key=lambda x: -x["accuracy"])


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  策略校准")
    print(f"{'='*60}\n")

    # 1. 加载数据
    print("1. 加载校准数据...")
    rows = fetch_calibration_data(since_year=2019, limit=8000)
    print(f"   取到 {len(rows)} 场比赛")

    # 加载 ELO
    elo_file = PROJECT_ROOT / "data" / "state" / "foot_elo_ratings.json"
    elo_ratings = {}
    if elo_file.exists():
        data = json.loads(elo_file.read_text(encoding="utf-8"))
        elo_ratings = data.get("ratings", {})
    print(f"   ELO 评分: {len(elo_ratings)} 支球队")

    # 划分训练/验证（80/20 按时间）
    split = int(len(rows) * 0.8)
    train_rows = rows[:split]
    val_rows = rows[split:]
    print(f"   训练集: {len(train_rows)}  验证集: {len(val_rows)}")

    # 2. 当前权重基线
    print("\n2. 当前权重基线...")
    current_weights = {"market": 0.35, "elo": 0.25, "poisson": 0.15, "dixon_coles": 0.10}
    baseline_results = batch_predict(val_rows, current_weights, elo_ratings)
    baseline_acc = sum(1 for r in baseline_results if r["correct"]) / len(baseline_results)
    print(f"   当前权重: {current_weights}")
    print(f"   验证集准确率: {baseline_acc:.1%}")

    # 3. Grid search 最优权重
    print("\n3. Grid search 最优权重...")
    t0 = time.time()
    best = grid_search_weights(train_rows, elo_ratings)
    elapsed = time.time() - t0
    print(f"   最优权重: {best['weights']}")
    print(f"   训练集准确率: {best['accuracy']:.1%}")
    print(f"   搜索耗时: {elapsed:.0f}s")

    # 用最优权重在验证集上评估
    opt_results = batch_predict(val_rows, best["weights"], elo_ratings)
    opt_acc = sum(1 for r in opt_results if r["correct"]) / len(opt_results)
    print(f"   验证集准确率: {opt_acc:.1%} (基线: {baseline_acc:.1%}, 提升: {opt_acc-baseline_acc:+.1%})")

    # 4. 高准策略筛选
    print("\n4. 高准策略筛选...")
    strategies = find_high_accuracy_conditions(opt_results)
    if strategies:
        print(f"   找到 {len(strategies)} 个高准策略:")
        print(f"   {'条件':<50} {'准确率':<8} {'样本':<6} {'覆盖率'}")
        print(f"   {'-'*75}")
        for s in strategies[:10]:
            print(f"   {s['condition']:<50} {s['accuracy']:.1%}   {s['sample_size']:<6} {s['coverage']:.1%}")
    else:
        print("   未找到准确率 > 55% 的策略")

    # 5. 保存结果
    print("\n5. 保存校准结果...")
    output = {
        "calibrated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "foot_mysql + football-data.co.uk",
        "train_size": len(train_rows),
        "val_size": len(val_rows),
        "baseline_weights": current_weights,
        "baseline_accuracy": round(baseline_acc, 4),
        "optimized_weights": best["weights"],
        "optimized_train_accuracy": round(best["accuracy"], 4),
        "optimized_val_accuracy": round(opt_acc, 4),
        "improvement": round(opt_acc - baseline_acc, 4),
        "high_accuracy_strategies": strategies[:10],
    }
    output_file = MODELS_DIR / "ensemble_calibration_c1.json"
    output_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   保存到: {output_file}")

    # 总结
    print(f"\n{'='*60}")
    print(f"  校准完成")
    print(f"  基线准确率: {baseline_acc:.1%}")
    print(f"  优化准确率: {opt_acc:.1%} ({opt_acc-baseline_acc:+.1%})")
    print(f"  最优权重: {best['weights']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
