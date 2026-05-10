from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from v24_app.training_samples import export_statsbomb_sandbox_fewshot_samples


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build StatsBomb sandbox few-shot samples for Evaluation Agent review.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    state_dir = args.project_root / "data" / "state"
    input_path = args.input or state_dir / "statsbomb_event_baseline.json"
    result = export_statsbomb_sandbox_fewshot_samples(
        project_dir=args.project_root,
        baseline_payload=read_json(input_path),
        output_path=args.output,
        limit=max(0, int(args.limit)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
