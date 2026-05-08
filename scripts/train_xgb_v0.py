from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    os.chdir(base_dir)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train XGBoost v0 model for V24.")
    parser.add_argument(
        "--force-min-samples",
        type=int,
        default=None,
        help="Override minimum sample threshold for one-shot training.",
    )
    args = parser.parse_args()

    _bootstrap()

    from v24_app.core import get_xgb_training_status, train_xgb_v0_now

    before = get_xgb_training_status()
    result = train_xgb_v0_now(force_min_samples=args.force_min_samples)
    after = get_xgb_training_status()

    output = {
        "before": before,
        "result": result,
        "after": after,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
