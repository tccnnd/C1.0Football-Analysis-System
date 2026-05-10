from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from v24_app.core import get_recent_settlements
from v24_app.training_samples import export_statsbomb_review_training_samples


def main() -> int:
    parser = argparse.ArgumentParser(description="Build post-match StatsBomb review training samples.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0, help="Settlement limit. 0 means all available settlements.")
    args = parser.parse_args()

    settlements = get_recent_settlements(limit=max(0, int(args.limit)))
    result = export_statsbomb_review_training_samples(
        project_dir=args.project_root,
        settlements=settlements,
        output_path=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
