"""
训练所有 XGBoost 模型

执行全量模型训练并记录性能指标。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
from v24_app.models.xgboost_xg import XGBoostWithXGModel
from v24_app.models.play_xgboost import (
    TotalGoalsXGBoostModel,
    ScorelineXGBoostModel,
    VolatileScorelineXGBoostModel,
)


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.2f} 秒"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} 分 {secs:.2f} 秒"


def train_model(name: str, model, force_min_samples: int | None = None) -> dict:
    """训练单个模型并记录时间"""
    print(f"\n{'='*60}")
    print(f"开始训练: {name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = model.train_now(force_min_samples=force_min_samples)
        elapsed = time.time() - start_time
        
        if result.get("trained"):
            print(f"✅ 训练成功")
            print(f"   样本数: {result.get('sample_count', 0):,}")
            print(f"   可用样本: {result.get('usable_count', result.get('sample_count', 0)):,}")
            print(f"   标签分布: {result.get('label_counts', {})}")
            if 'class_names' in result:
                print(f"   类别数: {len(result.get('class_names', []))}")
            print(f"   训练时间: {format_time(elapsed)}")
            print(f"   模型文件: {result.get('model_file', 'N/A')}")
        else:
            print(f"⚠️ 训练失败")
            print(f"   原因: {result.get('reason', 'unknown')}")
            print(f"   样本数: {result.get('sample_count', 0):,}")
            print(f"   耗时: {format_time(elapsed)}")
        
        return {
            "name": name,
            "success": result.get("trained", False),
            "elapsed": elapsed,
            "sample_count": result.get("sample_count", 0),
            "usable_count": result.get("usable_count", result.get("sample_count", 0)),
            "result": result,
        }
    
    except Exception as exc:
        elapsed = time.time() - start_time
        print(f"❌ 训练异常: {exc}")
        print(f"   耗时: {format_time(elapsed)}")
        return {
            "name": name,
            "success": False,
            "elapsed": elapsed,
            "error": str(exc),
        }


def main():
    """主训练流程"""
    print("\n" + "="*60)
    print("XGBoost 模型全量训练")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目路径: {PROJECT_ROOT}")
    
    total_start = time.time()
    results = []
    
    # 1. XGBoost V0 - 基础 1X2 模型
    model_v0 = XGBoostProbabilityModel(
        project_dir=PROJECT_ROOT,
        min_train_samples=30,
        retrain_interval_minutes=30,
    )
    results.append(train_model("XGBoost V0 (1X2 基础模型)", model_v0, force_min_samples=1))
    
    # 2. XGBoost XG - 增强 xG 特征模型
    model_xg = XGBoostWithXGModel(
        project_dir=PROJECT_ROOT,
        min_train_samples=30,
        retrain_interval_minutes=30,
    )
    results.append(train_model("XGBoost XG (xG 增强模型)", model_xg, force_min_samples=1))
    
    # 3. Total Goals - 总进球数模型
    model_total_goals = TotalGoalsXGBoostModel(
        project_dir=PROJECT_ROOT,
        max_total_goals=10,
    )
    results.append(train_model("Total Goals (总进球数模型)", model_total_goals, force_min_samples=1))
    
    # 4. Scoreline - 比分预测模型
    model_scoreline = ScorelineXGBoostModel(
        project_dir=PROJECT_ROOT,
        top_k=18,
    )
    results.append(train_model("Scoreline (比分预测模型)", model_scoreline, force_min_samples=1))
    
    # 5. Volatile Scoreline - 大比分预测模型
    model_volatile = VolatileScorelineXGBoostModel(
        project_dir=PROJECT_ROOT,
        top_k=12,
    )
    results.append(train_model("Volatile Scoreline (大比分模型)", model_volatile, force_min_samples=1))
    
    total_elapsed = time.time() - total_start
    
    # 汇总报告
    print("\n" + "="*60)
    print("训练完成汇总")
    print("="*60)
    
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - success_count
    
    print(f"\n总训练时间: {format_time(total_elapsed)}")
    print(f"成功: {success_count}/{len(results)}")
    print(f"失败: {fail_count}/{len(results)}")
    
    print("\n详细结果:")
    print(f"{'模型':<30} {'状态':<8} {'样本数':<12} {'训练时间':<15}")
    print("-" * 70)
    
    for r in results:
        status = "✅ 成功" if r.get("success") else "❌ 失败"
        sample_count = f"{r.get('sample_count', 0):,}"
        elapsed = format_time(r.get("elapsed", 0))
        print(f"{r['name']:<30} {status:<8} {sample_count:<12} {elapsed:<15}")
    
    print("\n" + "="*60)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 保存训练日志
    log_file = PROJECT_ROOT / "data" / "models" / "training_log.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"训练时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总耗时: {format_time(total_elapsed)}\n")
        f.write(f"成功: {success_count}/{len(results)}\n")
        for r in results:
            status = "SUCCESS" if r.get("success") else "FAILED"
            f.write(f"  {r['name']}: {status} ({format_time(r.get('elapsed', 0))})\n")
    
    print(f"\n训练日志已保存: {log_file}")
    
    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
