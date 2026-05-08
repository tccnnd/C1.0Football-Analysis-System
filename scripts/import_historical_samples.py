from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _bootstrap() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    os.chdir(base_dir)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return base_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Import historical football data into V24 XGB samples.")
    parser.add_argument("--input", required=True, help="Path to historical data file (.csv/.json/.jsonl).")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing xgb_training_samples.json instead of merging.",
    )
    parser.add_argument(
        "--sync-ratings",
        action="store_true",
        help="Also write the reconstructed end-of-history Elo ratings into elo_ratings.json.",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train XGB immediately after import.",
    )
    parser.add_argument(
        "--force-min-samples",
        type=int,
        default=None,
        help="Override the minimum sample threshold for one-shot training.",
    )
    args = parser.parse_args()

    base_dir = _bootstrap()

    from v24_app.core import get_xgb_training_status, train_xgb_v0_now
    from v24_app.training_samples import import_historical_xgb_samples

    before = get_xgb_training_status()
    imported = import_historical_xgb_samples(
        project_dir=base_dir,
        input_path=Path(args.input),
        replace=args.replace,
        sync_ratings=args.sync_ratings,
    )

    output: dict[str, object] = {
        "before": before,
        "import": imported,
    }
    if args.train:
        output["train"] = train_xgb_v0_now(force_min_samples=args.force_min_samples)
    output["after"] = get_xgb_training_status()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
