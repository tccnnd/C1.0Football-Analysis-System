"""清除旧的分析历史，从今天开始重新计算"""
import json
from pathlib import Path
from datetime import datetime

state_dir = Path("data/state")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 清除 analysis_history.json
ah = state_dir / "analysis_history.json"
if ah.exists():
    ah.write_text(json.dumps({
        "updated_at": now,
        "items": [],
        "reset_note": "Cleared for C1.0 fresh start on 2026-05-29"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cleared: {ah}")

print("\nDone. 胜率统计从今天开始重新计算。")
print("旧数据已备份到:")
print("  - settlements_backup_20260529.json")
print("  - analysis_history_backup_20260529.json")
