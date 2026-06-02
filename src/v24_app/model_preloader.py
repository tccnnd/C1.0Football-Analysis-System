"""
模型预加载模块

在应用启动时预加载所有模型，消除首次预测延迟。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .models.xgboost_v0 import XGBoostProbabilityModel
from .models.xgboost_xg import XGBoostWithXGModel
from .models.play_xgboost import (
    TotalGoalsXGBoostModel,
    ScorelineXGBoostModel,
    VolatileScorelineXGBoostModel,
)


class ModelPreloader:
    """模型预加载器"""
    
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.preload_results: dict[str, dict[str, Any]] = {}
    
    def preload_all(self, verbose: bool = True) -> dict[str, dict[str, Any]]:
        """
        预加载所有模型
        
        Args:
            verbose: 是否打印详细信息
            
        Returns:
            预加载结果字典
        """
        if verbose:
            print("\n" + "="*60)
            print("模型预加载")
            print("="*60)
        
        total_start = time.time()
        
        # 预加载 1X2 模型
        self._preload_xgboost_v0(verbose)
        self._preload_xgboost_xg(verbose)
        
        # 预加载玩法模型
        self._preload_total_goals(verbose)
        self._preload_scoreline(verbose)
        self._preload_volatile_scoreline(verbose)
        
        total_elapsed = time.time() - total_start
        
        if verbose:
            print("\n" + "="*60)
            print(f"预加载完成，总耗时: {total_elapsed:.2f} 秒")
            print("="*60)
            
            # 统计
            success_count = sum(1 for r in self.preload_results.values() if r.get("success"))
            print(f"\n✅ 成功: {success_count}/{len(self.preload_results)}")
            
            for name, result in self.preload_results.items():
                status = "✅" if result.get("success") else "❌"
                elapsed = result.get("elapsed", 0)
                print(f"  {status} {name}: {elapsed:.3f} 秒")
        
        return self.preload_results
    
    def _preload_xgboost_v0(self, verbose: bool) -> None:
        """预加载 XGBoost V0 模型"""
        name = "XGBoost V0"
        if verbose:
            print(f"\n预加载 {name}...")
        
        start = time.time()
        try:
            model = XGBoostProbabilityModel(self.project_dir)
            model._load_model()
            
            # 验证模型已加载
            with model._model_lock:
                model_loaded = model._model is not None
            
            elapsed = time.time() - start
            
            if model_loaded:
                if verbose:
                    print(f"  ✅ 成功 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": True,
                    "elapsed": elapsed,
                    "model_ready": model._model_ready,
                }
            else:
                if verbose:
                    print(f"  ⚠️ 模型未加载 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": False,
                    "elapsed": elapsed,
                    "reason": "model_not_loaded",
                }
        
        except Exception as exc:
            elapsed = time.time() - start
            if verbose:
                print(f"  ❌ 失败: {exc} ({elapsed:.3f} 秒)")
            self.preload_results[name] = {
                "success": False,
                "elapsed": elapsed,
                "error": str(exc),
            }
    
    def _preload_xgboost_xg(self, verbose: bool) -> None:
        """预加载 XGBoost XG 模型"""
        name = "XGBoost XG"
        if verbose:
            print(f"\n预加载 {name}...")
        
        start = time.time()
        try:
            model = XGBoostWithXGModel(self.project_dir)
            model._load_model()
            
            # 验证模型已加载
            with model._model_lock:
                model_loaded = model._model is not None
            
            elapsed = time.time() - start
            
            if model_loaded:
                if verbose:
                    print(f"  ✅ 成功 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": True,
                    "elapsed": elapsed,
                    "model_ready": model._model_ready,
                }
            else:
                if verbose:
                    print(f"  ⚠️ 模型未加载 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": False,
                    "elapsed": elapsed,
                    "reason": "model_not_loaded",
                }
        
        except Exception as exc:
            elapsed = time.time() - start
            if verbose:
                print(f"  ❌ 失败: {exc} ({elapsed:.3f} 秒)")
            self.preload_results[name] = {
                "success": False,
                "elapsed": elapsed,
                "error": str(exc),
            }
    
    def _preload_total_goals(self, verbose: bool) -> None:
        """预加载 Total Goals 模型"""
        name = "Total Goals"
        if verbose:
            print(f"\n预加载 {name}...")
        
        start = time.time()
        try:
            model = TotalGoalsXGBoostModel(self.project_dir)
            model._load_model()
            
            # 验证模型已加载
            with model._model_lock:
                model_loaded = model._model is not None
            
            elapsed = time.time() - start
            
            if model_loaded:
                if verbose:
                    print(f"  ✅ 成功 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": True,
                    "elapsed": elapsed,
                    "model_ready": model._model_ready,
                }
            else:
                if verbose:
                    print(f"  ⚠️ 模型未加载 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": False,
                    "elapsed": elapsed,
                    "reason": "model_not_loaded",
                }
        
        except Exception as exc:
            elapsed = time.time() - start
            if verbose:
                print(f"  ❌ 失败: {exc} ({elapsed:.3f} 秒)")
            self.preload_results[name] = {
                "success": False,
                "elapsed": elapsed,
                "error": str(exc),
            }
    
    def _preload_scoreline(self, verbose: bool) -> None:
        """预加载 Scoreline 模型"""
        name = "Scoreline"
        if verbose:
            print(f"\n预加载 {name}...")
        
        start = time.time()
        try:
            model = ScorelineXGBoostModel(self.project_dir)
            model._load_model()
            
            # 验证模型已加载
            with model._model_lock:
                model_loaded = model._model is not None
            
            elapsed = time.time() - start
            
            if model_loaded:
                if verbose:
                    print(f"  ✅ 成功 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": True,
                    "elapsed": elapsed,
                    "model_ready": model._model_ready,
                }
            else:
                if verbose:
                    print(f"  ⚠️ 模型未加载 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": False,
                    "elapsed": elapsed,
                    "reason": "model_not_loaded",
                }
        
        except Exception as exc:
            elapsed = time.time() - start
            if verbose:
                print(f"  ❌ 失败: {exc} ({elapsed:.3f} 秒)")
            self.preload_results[name] = {
                "success": False,
                "elapsed": elapsed,
                "error": str(exc),
            }
    
    def _preload_volatile_scoreline(self, verbose: bool) -> None:
        """预加载 Volatile Scoreline 模型"""
        name = "Volatile Scoreline"
        if verbose:
            print(f"\n预加载 {name}...")
        
        start = time.time()
        try:
            model = VolatileScorelineXGBoostModel(self.project_dir)
            model._load_model()
            
            # 验证模型已加载
            with model._model_lock:
                model_loaded = model._model is not None
            
            elapsed = time.time() - start
            
            if model_loaded:
                if verbose:
                    print(f"  ✅ 成功 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": True,
                    "elapsed": elapsed,
                    "model_ready": model._model_ready,
                }
            else:
                if verbose:
                    print(f"  ⚠️ 模型未加载 ({elapsed:.3f} 秒)")
                self.preload_results[name] = {
                    "success": False,
                    "elapsed": elapsed,
                    "reason": "model_not_loaded",
                }
        
        except Exception as exc:
            elapsed = time.time() - start
            if verbose:
                print(f"  ❌ 失败: {exc} ({elapsed:.3f} 秒)")
            self.preload_results[name] = {
                "success": False,
                "elapsed": elapsed,
                "error": str(exc),
            }


def preload_models(project_dir: Path, verbose: bool = True) -> dict[str, dict[str, Any]]:
    """
    预加载所有模型的便捷函数
    
    Args:
        project_dir: 项目根目录
        verbose: 是否打印详细信息
        
    Returns:
        预加载结果字典
    """
    preloader = ModelPreloader(project_dir)
    return preloader.preload_all(verbose=verbose)
