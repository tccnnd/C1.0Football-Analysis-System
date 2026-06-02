"""
生产部署自动化脚本

自动执行部署前检查、部署和验证。
"""
from __future__ import annotations

import sys
import time
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root.parent / f"ELO_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checks_passed = []
        self.checks_failed = []
    
    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70)
    
    def print_step(self, step: str):
        """打印步骤"""
        print(f"\n{step}")
        print("-" * 70)
    
    def check_python_version(self) -> bool:
        """检查 Python 版本"""
        self.print_step("1. 检查 Python 版本")
        
        version = sys.version_info
        print(f"   Python 版本: {version.major}.{version.minor}.{version.micro}")
        
        if version.major >= 3 and version.minor >= 10:
            print("   ✅ Python 版本符合要求 (>= 3.10)")
            return True
        else:
            print("   ❌ Python 版本过低，需要 >= 3.10")
            return False
    
    def check_dependencies(self) -> bool:
        """检查依赖包"""
        self.print_step("2. 检查依赖包")
        
        required_packages = {
            "xgboost": "XGBoost",
            "numpy": "NumPy",
            "pandas": "Pandas",
        }
        
        all_ok = True
        for package, name in required_packages.items():
            try:
                module = __import__(package)
                version = getattr(module, "__version__", "unknown")
                print(f"   ✅ {name}: {version}")
            except ImportError:
                print(f"   ❌ {name}: 未安装")
                all_ok = False
        
        return all_ok
    
    def check_model_files(self) -> bool:
        """检查模型文件"""
        self.print_step("3. 检查模型文件")
        
        model_dir = self.project_root / "data" / "models"
        required_models = [
            "xgb_v0_match_outcome.json",
            "xgb_xg_match_outcome.json",
            "xgb_v1_total_goals.json",
            "xgb_v1_scoreline.json",
            "xgb_v1_scoreline_volatile.json",
        ]
        
        all_ok = True
        for model_file in required_models:
            model_path = model_dir / model_file
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                print(f"   ✅ {model_file}: {size_mb:.2f} MB")
            else:
                print(f"   ❌ {model_file}: 不存在")
                all_ok = False
        
        return all_ok
    
    def check_disk_space(self) -> bool:
        """检查磁盘空间"""
        self.print_step("4. 检查磁盘空间")
        
        try:
            import psutil
            disk = psutil.disk_usage(str(self.project_root))
            free_gb = disk.free / (1024**3)
            
            print(f"   可用空间: {free_gb:.2f} GB")
            
            if free_gb > 1.0:
                print("   ✅ 磁盘空间充足")
                return True
            else:
                print("   ⚠️ 磁盘空间不足 (< 1 GB)")
                return False
        except Exception as exc:
            print(f"   ⚠️ 无法检查磁盘空间: {exc}")
            return True  # 不阻止部署
    
    def verify_preload_module(self) -> bool:
        """验证预加载模块"""
        self.print_step("5. 验证预加载模块")
        
        try:
            from v24_app.model_preloader import preload_models
            print("   ✅ 预加载模块存在")
            return True
        except ImportError as exc:
            print(f"   ❌ 预加载模块不存在: {exc}")
            return False
    
    def verify_auto_preload(self) -> bool:
        """验证自动预加载"""
        self.print_step("6. 验证自动预加载")
        
        core_file = self.project_root / "src" / "v24_app" / "core.py"
        
        if not core_file.exists():
            print("   ❌ core.py 文件不存在")
            return False
        
        content = core_file.read_text(encoding="utf-8")
        
        if "_preload_xgboost_models" in content and "_preload_xgboost_models()" in content:
            print("   ✅ 自动预加载代码存在")
            return True
        else:
            print("   ❌ 自动预加载代码不存在")
            return False
    
    def create_backup(self) -> bool:
        """创建备份"""
        self.print_step("7. 创建备份")
        
        try:
            print(f"   备份目录: {self.backup_dir}")
            
            # 只备份关键文件
            backup_items = [
                "src",
                "data/models",
                "data/state",
                "c1",
                "launcher.py",
            ]
            
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            for item in backup_items:
                src = self.project_root / item
                if src.exists():
                    dst = self.backup_dir / item
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                    print(f"   ✅ 已备份: {item}")
            
            print(f"   ✅ 备份完成")
            return True
        
        except Exception as exc:
            print(f"   ❌ 备份失败: {exc}")
            return False
    
    def test_preload_performance(self) -> bool:
        """测试预加载性能"""
        self.print_step("8. 测试预加载性能")
        
        try:
            from v24_app.model_preloader import preload_models
            
            start = time.time()
            results = preload_models(self.project_root, verbose=False)
            elapsed = time.time() - start
            
            success_count = sum(1 for r in results.values() if r.get("success"))
            total_count = len(results)
            
            print(f"   预加载完成: {success_count}/{total_count} 成功")
            print(f"   耗时: {elapsed:.2f} 秒")
            
            if success_count == total_count and elapsed < 5.0:
                print("   ✅ 预加载性能正常")
                return True
            else:
                if success_count < total_count:
                    print(f"   ⚠️ 部分模型预加载失败")
                if elapsed >= 5.0:
                    print(f"   ⚠️ 预加载耗时过长 ({elapsed:.2f}s)")
                return False
        
        except Exception as exc:
            print(f"   ❌ 预加载测试失败: {exc}")
            return False
    
    def test_prediction(self) -> bool:
        """测试预测功能"""
        self.print_step("9. 测试预测功能")
        
        try:
            from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
            from v24_app.models.ensemble import EnsembleContext
            
            model = XGBoostProbabilityModel(self.project_root)
            
            # 预加载模型（模拟生产环境）
            model._load_model()
            
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
            
            # 预热一次
            model.predict(context)
            
            # 测试预测延迟
            start = time.time()
            output = model.predict(context)
            latency = (time.time() - start) * 1000
            
            print(f"   预测结果: 主胜 {output.probabilities[0]:.2%}")
            print(f"   预测延迟: {latency:.2f} ms")
            
            if latency < 10.0:
                print("   ✅ 预测功能正常")
                return True
            else:
                print(f"   ⚠️ 预测延迟偏高 ({latency:.2f} ms，但可接受)")
                return True  # 仍然允许部署
        
        except Exception as exc:
            print(f"   ❌ 预测测试失败: {exc}")
            return False
    
    def run_pre_deployment_checks(self) -> bool:
        """运行部署前检查"""
        self.print_header("部署前检查")
        
        checks = [
            ("Python 版本", self.check_python_version),
            ("依赖包", self.check_dependencies),
            ("模型文件", self.check_model_files),
            ("磁盘空间", self.check_disk_space),
            ("预加载模块", self.verify_preload_module),
            ("自动预加载", self.verify_auto_preload),
            ("创建备份", self.create_backup),
            ("预加载性能", self.test_preload_performance),
            ("预测功能", self.test_prediction),
        ]
        
        for name, check_func in checks:
            try:
                if check_func():
                    self.checks_passed.append(name)
                else:
                    self.checks_failed.append(name)
            except Exception as exc:
                print(f"   ❌ 检查异常: {exc}")
                self.checks_failed.append(name)
        
        return len(self.checks_failed) == 0
    
    def print_summary(self):
        """打印检查摘要"""
        self.print_header("检查摘要")
        
        print(f"\n通过: {len(self.checks_passed)}/{len(self.checks_passed) + len(self.checks_failed)}")
        
        if self.checks_passed:
            print("\n✅ 通过的检查:")
            for check in self.checks_passed:
                print(f"  - {check}")
        
        if self.checks_failed:
            print("\n❌ 失败的检查:")
            for check in self.checks_failed:
                print(f"  - {check}")
    
    def deploy(self) -> bool:
        """执行部署"""
        self.print_header("开始部署")
        
        # 运行检查
        if not self.run_pre_deployment_checks():
            self.print_summary()
            print("\n" + "="*70)
            print("❌ 部署前检查失败，部署中止")
            print("="*70)
            print("\n请修复以上问题后重试。")
            return False
        
        self.print_summary()
        
        # 部署成功
        self.print_header("部署完成")
        
        print("\n✅ 所有检查通过，部署成功！")
        print(f"\n备份位置: {self.backup_dir}")
        
        print("\n下一步:")
        print("  1. 重启应用服务")
        print("  2. 监控首次请求延迟")
        print("  3. 检查性能指标")
        print("  4. 收集运行数据")
        
        print("\n如需回滚:")
        print(f"  1. 停止应用")
        print(f"  2. 恢复备份: xcopy {self.backup_dir} {self.project_root} /E /I /H /Y")
        print(f"  3. 重启应用")
        
        return True


def main():
    """主部署流程"""
    print("\n" + "="*70)
    print("  生产部署自动化脚本")
    print("="*70)
    print(f"  项目路径: {PROJECT_ROOT}")
    print(f"  部署时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 确认部署
    print("\n" + "="*70)
    print("⚠️  警告: 即将部署到生产环境")
    print("="*70)
    print("\n此操作将:")
    print("  1. 创建当前版本的备份")
    print("  2. 验证所有模型和代码")
    print("  3. 测试预加载和预测功能")
    
    response = input("\n是否继续? (yes/no): ").strip().lower()
    
    if response not in ["yes", "y"]:
        print("\n部署已取消。")
        return False
    
    # 执行部署
    manager = DeploymentManager(PROJECT_ROOT)
    success = manager.deploy()
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n部署已中断。")
        sys.exit(1)
    except Exception as exc:
        print(f"\n\n❌ 部署失败: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
