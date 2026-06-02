"""
验证模型预加载优化

确认优化已正确实施并生效。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def verify_preload_module_exists():
    """验证预加载模块存在"""
    print("\n1. 验证预加载模块...")
    try:
        from v24_app.model_preloader import preload_models
        print("   ✅ 预加载模块存在")
        return True
    except ImportError as exc:
        print(f"   ❌ 预加载模块不存在: {exc}")
        return False


def verify_auto_preload_in_core():
    """验证 core.py 中的自动预加载"""
    print("\n2. 验证自动预加载代码...")
    core_file = PROJECT_ROOT / "src" / "v24_app" / "core.py"
    
    if not core_file.exists():
        print("   ❌ core.py 文件不存在")
        return False
    
    content = core_file.read_text(encoding="utf-8")
    
    if "_preload_xgboost_models" in content:
        print("   ✅ 自动预加载函数存在")
    else:
        print("   ❌ 自动预加载函数不存在")
        return False
    
    if "_preload_xgboost_models()" in content:
        print("   ✅ 自动预加载调用存在")
    else:
        print("   ❌ 自动预加载调用不存在")
        return False
    
    return True


def verify_preload_works():
    """验证预加载功能正常工作"""
    print("\n3. 验证预加载功能...")
    
    try:
        from v24_app.model_preloader import preload_models
        
        start = time.time()
        results = preload_models(PROJECT_ROOT, verbose=False)
        elapsed = time.time() - start
        
        success_count = sum(1 for r in results.values() if r.get("success"))
        total_count = len(results)
        
        print(f"   预加载完成: {success_count}/{total_count} 成功")
        print(f"   耗时: {elapsed:.2f} 秒")
        
        if success_count == total_count:
            print("   ✅ 所有模型预加载成功")
            return True
        else:
            print(f"   ⚠️ 部分模型预加载失败")
            for name, result in results.items():
                if not result.get("success"):
                    print(f"      - {name}: {result.get('error', result.get('reason'))}")
            return False
    
    except Exception as exc:
        print(f"   ❌ 预加载功能异常: {exc}")
        return False


def verify_latency_improvement():
    """验证延迟改善"""
    print("\n4. 验证延迟改善...")
    
    try:
        from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
        from v24_app.models.ensemble import EnsembleContext
        
        # 创建模型并预加载
        model = XGBoostProbabilityModel(PROJECT_ROOT)
        model._load_model()
        
        # 创建测试上下文
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
        
        # 测试预测延迟
        latencies = []
        for _ in range(10):
            start = time.time()
            model.predict(context)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"   平均预测延迟: {avg_latency:.2f} ms")
        
        if avg_latency < 5.0:
            print("   ✅ 预测延迟优秀 (< 5ms)")
            return True
        elif avg_latency < 20.0:
            print("   ✅ 预测延迟良好 (< 20ms)")
            return True
        else:
            print(f"   ⚠️ 预测延迟偏高 ({avg_latency:.2f} ms)")
            return False
    
    except Exception as exc:
        print(f"   ❌ 延迟测试异常: {exc}")
        return False


def verify_skip_preload_flag():
    """验证跳过预加载标志"""
    print("\n5. 验证跳过预加载标志...")
    
    import os
    
    # 设置跳过标志
    os.environ["SKIP_MODEL_PRELOAD"] = "1"
    
    try:
        # 重新导入 core 模块
        import importlib
        if "v24_app.core" in sys.modules:
            del sys.modules["v24_app.core"]
        
        from v24_app import core
        
        # 检查模型是否未预加载
        with core.XGBOOST_MODEL._model_lock:
            model_loaded = core.XGBOOST_MODEL._model is not None
        
        if not model_loaded:
            print("   ✅ 跳过预加载标志生效")
            result = True
        else:
            print("   ⚠️ 跳过预加载标志未生效（模型已加载）")
            result = False
    
    except Exception as exc:
        print(f"   ❌ 测试异常: {exc}")
        result = False
    
    finally:
        # 清理环境变量
        if "SKIP_MODEL_PRELOAD" in os.environ:
            del os.environ["SKIP_MODEL_PRELOAD"]
    
    return result


def main():
    """主验证流程"""
    print("\n" + "="*70)
    print("模型预加载优化验证")
    print("="*70)
    
    results = []
    
    # 执行验证
    results.append(("预加载模块存在", verify_preload_module_exists()))
    results.append(("自动预加载代码", verify_auto_preload_in_core()))
    results.append(("预加载功能正常", verify_preload_works()))
    results.append(("延迟改善验证", verify_latency_improvement()))
    results.append(("跳过标志验证", verify_skip_preload_flag()))
    
    # 汇总结果
    print("\n" + "="*70)
    print("验证结果汇总")
    print("="*70)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n通过: {success_count}/{total_count}")
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    if success_count == total_count:
        print("\n" + "="*70)
        print("✅ 所有验证通过！优化已成功实施。")
        print("="*70)
        print("\n下一步:")
        print("  1. 部署到生产环境")
        print("  2. 监控首次请求延迟")
        print("  3. 收集性能数据")
        return True
    else:
        print("\n" + "="*70)
        print("⚠️ 部分验证失败，请检查实施情况。")
        print("="*70)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
