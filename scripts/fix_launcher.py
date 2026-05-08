import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    base_dir = scripts_dir.parent
    os.chdir(base_dir)

    launcher = base_dir / "launcher.py"
    venv_python = base_dir / "venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python if venv_python.exists() else Path(sys.executable))

    print(f"工作目录: {base_dir}")
    print(f"Python: {python_exe}")
    print(f"启动器: {launcher}")

    if not launcher.exists():
        print("错误: 未找到 launcher.py")
        input("按回车键退出...")
        return

    result = subprocess.run([python_exe, str(launcher)], check=False)
    if result.returncode != 0:
        print(f"启动失败，退出码: {result.returncode}")

    input("按回车键退出...")


if __name__ == "__main__":
    main()
