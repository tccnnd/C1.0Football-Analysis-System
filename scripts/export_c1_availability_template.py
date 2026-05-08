from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a fillable C1 availability template for current V24 matches.")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]), help="Project root path")
    parser.add_argument("--output", default="", help="CSV output path")
    parser.add_argument("--strict-today", action="store_true", help="Only include today's not-started matches")
    parser.add_argument("--limit", type=int, default=0, help="Optional max row count")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "src"))

    from c1.data import build_availability_template_rows, export_availability_template_csv
    from v24_app.core import fetch_matches_v24

    fetch_result = fetch_matches_v24(strict_today=bool(args.strict_today))
    matches = list(fetch_result.matches)
    if args.limit and args.limit > 0:
        matches = matches[: args.limit]

    rows = build_availability_template_rows(matches)
    output_path = Path(args.output) if args.output else (
        project_root
        / "reports"
        / f"c1_availability_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    written = export_availability_template_csv(output_path, rows)
    print({"rows": len(rows), "output": str(written), "source": fetch_result.diagnostics.source})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
