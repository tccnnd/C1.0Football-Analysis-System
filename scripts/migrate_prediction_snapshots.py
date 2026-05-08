from __future__ import annotations

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
    _bootstrap()

    from v24_app.core import get_prediction_snapshot_migration_report, migrate_prediction_snapshots

    result = migrate_prediction_snapshots()
    output = {
        "result": result,
        "report": get_prediction_snapshot_migration_report(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
