"""
用 foot 历史数据训练 LightGBM 1X2 分类模型

特征来源：
- 欧赔（伟德 CompId=81）：Sp3/Sp1/Sp0/Ep3/Ep1/Ep0
- 亚赔（Crown）：SLetBall/ELetBall/Sp3/Sp0/Ep3/Ep0
- 赔率衍生特征：return_rate, overround, odds_move, kelly 近似
- ELO 评分（从 foot_elo_ratings.json）

输出：
- data/models/lgbm_c1_match_outcome.txt（模型文件）
- data/models/lgbm_c1_match_outcome.meta.json（元数据）
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

MODELS_DIR = PROJECT_ROOT / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_FILE = MODELS_DIR / "lgbm_c1_match_outcome.txt"
META_FILE = MODELS_DIR / "lgbm_c1_match_outcome.meta.json"


# ── 特征工程 ──────────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    # 欧赔原始
    "euro_sp3", "euro_sp1", "euro_sp0",
    "euro_ep3", "euro_ep1", "euro_ep0",
    # 欧赔衍生
    "euro_home_prob", "euro_draw_prob", "euro_away_prob",
    "euro_overround", "euro_return_rate",
    "euro_home_move", "euro_draw_move", "euro_away_move",
    # 亚赔
    "asia_s_let_ball", "asia_e_let_ball", "asia_let_ball_move",
    "asia_sp3", "asia_sp0", "asia_ep3", "asia_ep0",
    "asia_home_move", "asia_away_move",
    # ELO
    "home_elo", "away_elo", "elo_diff", "elo_diff_abs",
    # 综合
    "home_implied_prob", "away_implied_prob",
    "market_balance",  # |home_prob - away_prob|
]


def build_features(row: dict, elo_ratings: dict) -> list[float]:
    """从一行数据构建特征向量"""
    def sf(v, d=0.0):
        try:
            return float(v) if v not in (None, "") else d
        except Exception:
            return d

    # 欧赔
    esp3 = sf(row.get("euro_sp3"), 2.5)
    esp1 = sf(row.get("euro_sp1"), 3.2)
    esp0 = sf(row.get("euro_sp0"), 3.0)
    eep3 = sf(row.get("euro_ep3"), esp3)
    eep1 = sf(row.get("euro_ep1"), esp1)
    eep0 = sf(row.get("euro_ep0"), esp0)

    # 欧赔隐含概率
    eh = 1.0 / max(eep3, 1.01)
    ed = 1.0 / max(eep1, 1.01)
    ea = 1.0 / max(eep0, 1.01)
    total = eh + ed + ea
    euro_home_prob = eh / total
    euro_draw_prob = ed / total
    euro_away_prob = ea / total
    euro_overround = total
    euro_return_rate = 1.0 / max(total, 0.01)

    # 欧赔变动
    euro_home_move = (eep3 - esp3) / max(esp3, 1.01)
    euro_draw_move = (eep1 - esp1) / max(esp1, 1.01)
    euro_away_move = (eep0 - esp0) / max(esp0, 1.01)

    # 亚赔
    aslb = sf(row.get("asia_s_let_ball"), 0.0)
    aelb = sf(row.get("asia_e_let_ball"), 0.0)
    asp3 = sf(row.get("asia_sp3"), 0.9)
    asp0 = sf(row.get("asia_sp0"), 0.9)
    aep3 = sf(row.get("asia_ep3"), asp3)
    aep0 = sf(row.get("asia_ep0"), asp0)
    asia_let_ball_move = aelb - aslb
    asia_home_move = (aep3 - asp3) / max(asp3, 0.01)
    asia_away_move = (aep0 - asp0) / max(asp0, 0.01)

    # ELO
    home_team = str(row.get("MainTeamId", ""))
    away_team = str(row.get("GuestTeamId", ""))
    home_elo = elo_ratings.get(home_team, 1500.0)
    away_elo = elo_ratings.get(away_team, 1500.0)
    elo_diff = home_elo - away_elo
    elo_diff_abs = abs(elo_diff)

    # 综合
    home_implied = euro_home_prob
    away_implied = euro_away_prob
    market_balance = abs(euro_home_prob - euro_away_prob)

    return [
        esp3, esp1, esp0, eep3, eep1, eep0,
        euro_home_prob, euro_draw_prob, euro_away_prob,
        euro_overround, euro_return_rate,
        euro_home_move, euro_draw_move, euro_away_move,
        aslb, aelb, asia_let_ball_move,
        asp3, asp0, aep3, aep0,
        asia_home_move, asia_away_move,
        home_elo, away_elo, elo_diff, elo_diff_abs,
        home_implied, away_implied, market_balance,
    ]


def build_label(row: dict) -> int:
    """0=主胜 1=平 2=客胜"""
    hg = int(row.get("MainTeamGoals", -1))
    ag = int(row.get("GuestTeamGoals", -1))
    if hg > ag:
        return 0
    if hg < ag:
        return 2
    return 1


# ── 数据获取 ──────────────────────────────────────────────────────────────────

def fetch_training_data(limit: int = 100000, since_year: int = 2010) -> list[dict]:
    import pymysql, pymysql.cursors
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root",
        password=os.environ.get("FOOT_MYSQL_PASSWORD", "Meta.123"),
        database="foot", charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT
            mh.MainTeamId, mh.GuestTeamId,
            mh.MainTeamGoals, mh.GuestTeamGoals,
            ah.SLetBall AS asia_s_let_ball, ah.ELetBall AS asia_e_let_ball,
            ah.Sp3 AS asia_sp3, ah.Sp0 AS asia_sp0,
            ah.Ep3 AS asia_ep3, ah.Ep0 AS asia_ep0,
            eh.Sp3 AS euro_sp3, eh.Sp1 AS euro_sp1, eh.Sp0 AS euro_sp0,
            eh.Ep3 AS euro_ep3, eh.Ep1 AS euro_ep1, eh.Ep0 AS euro_ep0
        FROM t_match_his mh
        INNER JOIN t_asia_his ah ON ah.MatchId = mh.Id AND ah.CompId = 'Crown'
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id AND eh.CompId = '81'
        WHERE mh.MainTeamGoals >= 0
          AND YEAR(mh.MatchDate) >= %s
          AND eh.Ep3 > 1.0 AND eh.Ep0 > 1.0
        ORDER BY mh.MatchDate ASC
        LIMIT %s
    """, (since_year, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_elo_ratings() -> dict[str, float]:
    path = PROJECT_ROOT / "data" / "state" / "foot_elo_ratings.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("ratings", {})


# ── 训练 ──────────────────────────────────────────────────────────────────────

def main():
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    from datetime import datetime

    print(f"\n{'='*60}")
    print(f"  LightGBM 1X2 模型训练")
    print(f"{'='*60}\n")

    # 1. 加载数据
    print("1. 加载训练数据...")
    t0 = time.time()
    rows = fetch_training_data(limit=200000, since_year=2010)
    print(f"   取到 {len(rows):,} 条样本  耗时 {time.time()-t0:.1f}s")

    elo_ratings = load_elo_ratings()
    print(f"   ELO 评分: {len(elo_ratings):,} 支球队")

    # 2. 构建特征矩阵
    print("2. 构建特征矩阵...")
    X = []
    y = []
    for row in rows:
        features = build_features(row, elo_ratings)
        label = build_label(row)
        X.append(features)
        y.append(label)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)
    print(f"   特征矩阵: {X.shape}  标签分布: 主胜={sum(y==0)} 平={sum(y==1)} 客胜={sum(y==2)}")

    # 3. 划分训练/测试集（按时间顺序，后 20% 为测试）
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    print(f"   训练集: {len(X_train):,}  测试集: {len(X_test):,}")

    # 4. 训练
    print("3. 训练 LightGBM...")
    t0 = time.time()

    train_data = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_NAMES)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    params = {
        "objective": "multiclass",
        "num_class": 3,
        "metric": "multi_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "learning_rate": 0.05,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": 42,
    }

    callbacks = [lgb.log_evaluation(period=50)]
    model = lgb.train(
        params,
        train_data,
        num_boost_round=300,
        valid_sets=[test_data],
        callbacks=callbacks,
    )
    train_time = time.time() - t0
    print(f"   训练完成  耗时 {train_time:.1f}s")

    # 5. 评估
    print("4. 评估...")
    y_pred_proba = model.predict(X_test)
    y_pred = np.argmax(y_pred_proba, axis=1)
    acc = accuracy_score(y_test, y_pred)
    print(f"   测试集准确率: {acc:.4f} ({acc:.1%})")
    print()
    label_names = ["主胜(0)", "平局(1)", "客胜(2)"]
    print(classification_report(y_test, y_pred, target_names=label_names))

    # 6. 特征重要性
    print("5. Top 10 特征重要性:")
    importance = model.feature_importance(importance_type="gain")
    sorted_idx = np.argsort(importance)[::-1]
    for i in range(min(10, len(FEATURE_NAMES))):
        idx = sorted_idx[i]
        print(f"   {i+1:2}. {FEATURE_NAMES[idx]:<25} {importance[idx]:.0f}")

    # 7. 保存模型
    print("\n6. 保存模型...")
    model.save_model(str(MODEL_FILE))

    meta = {
        "model": "lgbm_c1_match_outcome",
        "version": "v1",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "test_accuracy": round(acc, 4),
        "train_time_seconds": round(train_time, 1),
        "num_boost_round": 300,
        "params": params,
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "label_map": {"0": "home", "1": "draw", "2": "away"},
        "feature_importance_top10": [
            {"name": FEATURE_NAMES[sorted_idx[i]], "gain": float(importance[sorted_idx[i]])}
            for i in range(min(10, len(FEATURE_NAMES)))
        ],
    }
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   模型: {MODEL_FILE}")
    print(f"   元数据: {META_FILE}")

    print(f"\n{'='*60}")
    print(f"  训练完成  准确率: {acc:.1%}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
