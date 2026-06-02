"""彻底重置赛果回收相关数据，从今天开始"""
import json
import shutil
from pathlib import Path
from datetime import datetime

state_dir = Path("data/state")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
today = datetime.now().strftime("%Y-%m-%d")

# 需要清空的回收相关文件
reset_targets = [
    "settlements.json",
    "analysis_history.json",
    "result_recovery_runs.json",
    "parlay_tickets.json",
    "snapshot_result_cache.json",
    "daily_parlay_repair_audit_log.json",
]

print("=== 彻底重置赛果回收数据 ===\n")

for name in reset_targets:
    f = state_dir / name
    if not f.exists():
        print(f"  跳过（不存在）: {name}")
        continue
    # 备份（如果还没备份过）
    bak = state_dir / f"{name}.fullreset_bak"
    if not bak.exists():
        shutil.copy(f, bak)
    # 清空
    f.write_text(json.dumps({
        "updated_at": now,
        "items": [],
        "reset_note": f"Full reset on {today} for C1.0 fresh start"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已清空: {name}")

# prediction_snapshots.json 保留今日的快照（删除非今日的）
snap_file = state_dir / "prediction_snapshots.json"
if snap_file.exists():
    try:
        data = json.loads(snap_file.read_text(encoding="utf-8"))
        items = data.get("items", {}) if isinstance(data, dict) else {}
        if isinstance(items, dict):
            # 只保留今日及未来的比赛快照
            kept = {}
            removed = 0
            for mid, rec in items.items():
                match = rec.get("match", {}) if isinstance(rec, dict) else {}
                md = str(match.get("match_date", ""))
                if md >= today:
                    kept[mid] = rec
                else:
                    removed += 1
            data["items"] = kept
            snap_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n  prediction_snapshots.json: 保留今日 {len(kept)} 场，删除历史 {removed} 场")
    except Exception as e:
        print(f"\n  prediction_snapshots.json 处理失败: {e}")

# settled_ledger.json 是结算幂等性的权威来源，重置时必须一并清空，
# 否则今日及之后的比赛会因账本残留而被永久跳过结算。
ledger_file = state_dir / "settled_ledger.json"
if ledger_file.exists():
    bak = state_dir / "settled_ledger.json.fullreset_bak"
    if not bak.exists():
        shutil.copy(ledger_file, bak)
    ledger_file.write_text(json.dumps({
        "updated_at": now,
        "settled_ids": [],
        "reset_note": f"Full reset on {today} for C1.0 fresh start",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n  已清空: settled_ledger.json")
else:
    print("\n  跳过（不存在）: settled_ledger.json")

print("\n✅ 重置完成。赛果回收将只处理今日及之后的比赛。")
print("   备份文件后缀: .fullreset_bak")