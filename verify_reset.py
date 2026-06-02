import json
from pathlib import Path
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
print(f"今天: {today}\n")

for name in ["settlements.json", "analysis_history.json", "prediction_snapshots.json", "result_recovery_runs.json"]:
    f = Path("data/state") / name
    d = json.loads(f.read_text(encoding="utf-8"))
    items = d.get("items", {})
    cnt = len(items) if isinstance(items, (list, dict)) else 0
    print(f"{name}: {cnt} 条")

snap = json.loads(Path("data/state/prediction_snapshots.json").read_text(encoding="utf-8"))
print("\n快照中的比赛:")
for mid, rec in snap.get("items", {}).items():
    m = rec.get("match", {})
    print(f"  {m.get('match_date')} {m.get('home_team')} vs {m.get('away_team')}")
