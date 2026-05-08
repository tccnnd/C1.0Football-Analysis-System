from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _bootstrap_paths() -> tuple[Path, Path]:
    base_dir = _project_root()
    src_dir = base_dir / "src"
    os.chdir(base_dir)
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return base_dir, src_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V24 / C1 APP launcher")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify launcher environment and print resolved paths.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base_dir, src_dir = _bootstrap_paths()
    venv_python = base_dir / "venv" / "Scripts" / "python.exe"

    if args.check:
        print(f"project_root={base_dir}")
        print(f"src_dir={src_dir}")
        print(f"venv_python_exists={venv_python.exists()}")
        print(f"python_executable={sys.executable}")
        return 0

    try:
        from v24_app.ai_dashboard import main as run_app
    except Exception as exc:
        print("Launcher failed to import v24_app.ui.main", file=sys.stderr)
        print(f"project_root={base_dir}", file=sys.stderr)
        print(f"src_dir={src_dir}", file=sys.stderr)
        print(f"python_executable={sys.executable}", file=sys.stderr)
        print(f"error={exc}", file=sys.stderr)
        return 1

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
