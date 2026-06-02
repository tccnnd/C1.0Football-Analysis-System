"""
测试 foot (Go) 集成

检查 foot 项目是否正确安装和运行
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def check_foot_installation():
    """检查 foot 是否安装"""
    foot_dir = Path("E:/APP/foot")
    foot_exe = foot_dir / "foot.exe"
    
    print("=== foot Installation Check ===\n")
    
    if not foot_dir.exists():
        print("✗ foot directory not found: E:/APP/foot")
        print("  Run: powershell -ExecutionPolicy Bypass -File scripts/setup_foot.ps1")
        return False
    
    print(f"✓ foot directory exists: {foot_dir}")
    
    if not foot_exe.exists():
        print("✗ foot.exe not found")
        print("  Run: cd E:/APP/foot && go build -o foot.exe")
        return False
    
    print(f"✓ foot.exe exists: {foot_exe}")
    
    # 检查文件大小
    size = foot_exe.stat().st_size
    print(f"  Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    
    return True


def test_foot_execution():
    """测试 foot 是否可以执行"""
    foot_exe = Path("E:/APP/foot/foot.exe")
    
    print("\n=== foot Execution Test ===\n")
    
    try:
        # 尝试运行 --help
        result = subprocess.run(
            [str(foot_exe), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=foot_exe.parent,
        )
        
        if result.returncode == 0:
            print("✓ foot.exe is executable")
            print("\nHelp output:")
            print("-" * 60)
            print(result.stdout[:500])  # 只显示前 500 字符
            if len(result.stdout) > 500:
                print("... (truncated)")
            print("-" * 60)
            return True
        else:
            print(f"✗ foot.exe returned error code: {result.returncode}")
            print(f"  stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ foot.exe timed out")
        return False
    except Exception as e:
        print(f"✗ Failed to run foot.exe: {e}")
        return False


def check_foot_config():
    """检查 foot 配置文件"""
    foot_dir = Path("E:/APP/foot")
    
    print("\n=== foot Configuration Check ===\n")
    
    # 常见配置文件名
    config_files = [
        "config.yaml",
        "config.yml",
        "config.json",
        "config.toml",
        "app.yaml",
        "app.yml",
    ]
    
    found_configs = []
    for config_name in config_files:
        config_path = foot_dir / config_name
        if config_path.exists():
            found_configs.append(config_path)
            print(f"✓ Found config: {config_name}")
            
            # 显示文件大小
            size = config_path.stat().st_size
            print(f"  Size: {size} bytes")
    
    if not found_configs:
        print("⚠ No standard config files found")
        print("  Listing all files in foot directory:")
        for item in foot_dir.iterdir():
            if item.is_file():
                print(f"  - {item.name}")
    
    return len(found_configs) > 0


def check_foot_output():
    """检查 foot 是否有输出文件"""
    foot_dir = Path("E:/APP/foot")
    
    print("\n=== foot Output Check ===\n")
    
    # 常见输出目录
    output_dirs = [
        foot_dir / "output",
        foot_dir / "data",
        foot_dir / "results",
        foot_dir / "export",
    ]
    
    found_outputs = []
    for output_dir in output_dirs:
        if output_dir.exists() and output_dir.is_dir():
            files = list(output_dir.glob("*"))
            if files:
                found_outputs.append(output_dir)
                print(f"✓ Found output directory: {output_dir.name}")
                print(f"  Files: {len(files)}")
                
                # 显示最近的几个文件
                recent_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]
                for f in recent_files:
                    print(f"  - {f.name} ({f.stat().st_size} bytes)")
    
    if not found_outputs:
        print("⚠ No output files found")
        print("  foot may not have run yet")
    
    return len(found_outputs) > 0


def test_http_api():
    """测试 foot HTTP API（如果有）"""
    print("\n=== foot HTTP API Test ===\n")
    
    try:
        import requests
    except ImportError:
        print("⚠ requests library not installed, skipping HTTP test")
        return False
    
    # 尝试常见端口
    ports = [8080, 8081, 8082, 9000]
    
    for port in ports:
        url = f"http://localhost:{port}/health"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"✓ foot HTTP API found on port {port}")
                print(f"  Response: {response.text[:200]}")
                return True
        except:
            pass
    
    print("⚠ No HTTP API found on common ports")
    print("  foot may not be running as HTTP server")
    return False


def suggest_next_steps():
    """建议下一步操作"""
    print("\n=== Next Steps ===\n")
    
    print("1. 了解 foot 的功能:")
    print("   cd E:/APP/foot")
    print("   ./foot.exe --help")
    print("")
    
    print("2. 查看 foot 的配置:")
    print("   - 检查 config.yaml 或 config.json")
    print("   - 了解数据源配置")
    print("   - 了解输出格式")
    print("")
    
    print("3. 运行 foot 采集数据:")
    print("   cd E:/APP/foot")
    print("   ./foot.exe")
    print("")
    
    print("4. 集成到 ELO 系统:")
    print("   - 查看 docs/FOOT_GITEE_INTEGRATION.md")
    print("   - 选择集成方式（HTTP/文件/数据库）")
    print("   - 配置 c1/configs/availability_sources.yaml")
    print("")


def main():
    """主函数"""
    print("=" * 70)
    print("foot (Go) Integration Test")
    print("=" * 70)
    print("")
    
    results = {
        "installation": check_foot_installation(),
        "execution": False,
        "config": False,
        "output": False,
        "http_api": False,
    }
    
    if results["installation"]:
        results["execution"] = test_foot_execution()
        results["config"] = check_foot_config()
        results["output"] = check_foot_output()
        results["http_api"] = test_http_api()
    
    # 总结
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("")
    
    for key, value in results.items():
        status = "✓" if value else "✗"
        print(f"{status} {key.replace('_', ' ').title()}: {'PASS' if value else 'FAIL'}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if results["installation"] and results["execution"]:
        print("\n✓ foot is ready for integration!")
    else:
        print("\n⚠ foot needs setup. Run:")
        print("  powershell -ExecutionPolicy Bypass -File scripts/setup_foot.ps1")
    
    suggest_next_steps()


if __name__ == "__main__":
    main()
