from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Import local availability snapshots into C1 state store.")
    parser.add_argument("--input", required=True, help="Path to CSV/JSON/JSONL availability snapshot file")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]), help="Project root path")
    parser.add_argument("--replace", action="store_true", help="Replace existing availability snapshot store")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    sys.path.insert(0, str(project_root))

    from c1.data import C1AvailabilityStore, load_rows_from_file

    rows = load_rows_from_file(args.input)
    store = C1AvailabilityStore(project_root)
    result = store.import_rows(rows, replace=args.replace)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
