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
    parser = argparse.ArgumentParser(description="Auto fetch finished matches and settle results.")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=2,
        help="Look back N days (including today) when scanning finished matches. Default: 2",
    )
    args = parser.parse_args()

    _bootstrap()

    from v24_app.core import auto_settle_finished_matches

    result = auto_settle_finished_matches(
        prediction_cache=None,
        lookback_days=max(0, min(int(args.lookback_days), 7)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
