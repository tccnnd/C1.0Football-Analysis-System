from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap(project_root: Path) -> None:
    root = project_root.resolve()
    src = root / "src"
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync configured C1 availability providers into local snapshot store.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    _bootstrap(project_root)

    from c1.data import AvailabilityProviderChain

    chain = AvailabilityProviderChain.from_project_root(project_root)
    result = chain.sync_to_store(project_root, replace=args.replace)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
