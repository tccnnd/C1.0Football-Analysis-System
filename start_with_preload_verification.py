"""
启动应用并验证预加载

在启动应用前验证预加载功能正常。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def print_header(title: str):
    """打印标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def verify_preload():
    """验证预加载"""
    print_header("验证模型预加载")
    
    print("\n正在导入 core 模块（会触发自动预加载）...")
    start = time.time()
    
    try:
        from v24_app import core
        elapsed = time.time() - start
        
        print(f"✅ Core 模块导入成功（耗时 {elapsed:.2f} 秒）")
        
        # 检查模型是否已加载
        print("\n检查模型加载状态:")
        
        models = {
            "XGBoost V0": core.XGBOOST_MODEL,
            "Total Goals": core.TOTAL_GOALS_MODEL,
            "Scoreline": core.SCORELINE_MODEL,
            "Volatile Scoreline": core.VOLATILE_SCORELINE_MODEL,
        }
        
        all_loaded = True
        for name, model in models.items():
            with model._model_lock:
                loaded = model._model is not None
            
            status = "✅ 已加载" if loaded else "❌ 未加载"
            print(f"  {name}: {status}")
            
            if not loaded:
                all_loaded = False
        
        if all_loaded:
            print("\n✅ 所有模型已成功预加载")
            return True
        else:
            print("\n⚠️ 部分模型未预加载（将在首次使用时加载）")
            return True  # 仍然允许启动
    
    except Exception as exc:
        print(f"\n❌ 预加载验证失败: {exc}")
        return False


def test_quick_prediction():
    """快速预测测试"""
    print_header("快速预测测试")
    
    try:
        from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
        from v24_app.models.ensemble import EnsembleContext
        
        model = XGBoostProbabilityModel(PROJECT_ROOT)
        
        context = EnsembleContext(
            home_rating=1600.0,
            away_rating=1600.0,
            league_strength=0.70,
            market_probs=(0.40, 0.30, 0.30),
            market_draw_prob=0.30,
            metadata={
                "odds_home": 2.40,
                "odds_draw": 3.20,
                "odds_away": 2.80,
            }
        )
        
        print("\n执行测试预测...")
        start = time.time()
        output = model.predict(context)
        latency = (time.time() - start) * 1000
        
        print(f"✅ 预测成功")
        print(f"   结果: 主胜 {output.probabilities[0]:.2%} | "
              f"平局 {output.probabilities[1]:.2%} | "
              f"客胜 {output.probabilities[2]:.2%}")
        print(f"   延迟: {latency:.2f} ms")
        
        if latency < 10.0:
            print(f"   ⚡ 延迟优秀 (< 10ms)")
        elif latency < 50.0:
            print(f"   ✅ 延迟良好 (< 50ms)")
        else:
            print(f"   ⚠️ 延迟偏高 ({latency:.2f} ms)")
        
        return True
    
    except Exception as exc:
        print(f"\n❌ 预测测试失败: {exc}")
        return False


def start_application():
    """启动应用"""
    print_header("启动应用")
    
    print("\n正在启动 V24 / C1 应用...")
    print("时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        from v24_app.ai_dashboard import main as run_app
        
        print("\n✅ 应用模块导入成功")
        print("\n" + "="*70)
        print("  应用启动中...")
        print("="*70)
        print("\n提示:")
        print("  - 模型已预加载，首次预测将非常快")
        print("  - 如需监控，运行: python monitor_production.py --continuous")
        print("  - 如需停止，按 Ctrl+C")
        print("\n" + "="*70 + "\n")
        
        # 启动应用
        run_app()
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n应用已停止。")
        return 0
    
    except Exception as exc:
        print(f"\n❌ 应用启动失败: {exc}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """主启动流程"""
    print("\n" + "="*70)
    print("  V24 / C1 应用启动器（带预加载验证）")
    print("="*70)
    print(f"  项目路径: {PROJECT_ROOT}")
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 验证预加载
    if not verify_preload():
        print("\n⚠️ 预加载验证失败，但仍将尝试启动应用...")
    
    # 快速预测测试
    if not test_quick_prediction():
        print("\n⚠️ 预测测试失败，但仍将尝试启动应用...")
    
    # 启动应用
    return start_application()


if __name__ == "__main__":
    sys.exit(main())
