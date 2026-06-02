"""调试：测试每场比赛的预测是否成功"""
import sys, traceback
sys.path.insert(0, "src")
from v24_app.core import fetch_matches_v24, predict_match

result = fetch_matches_v24()
print(f"Fetched: {len(result.matches)} matches\n")

ok = 0
fail = 0
for i, m in enumerate(result.matches, 1):
    try:
        p = predict_match(m)
        overlay = p.get("c1_overlay", {})
        model = "C1.0" if overlay.get("applied") else "V24"
        print(f"  OK  {i}: {m.league} {m.home_team} vs {m.away_team} [{model}]")
        ok += 1
    except Exception as e:
        print(f"  FAIL {i}: {m.league} {m.home_team} vs {m.away_team}")
        print(f"        ERROR: {e}")
        traceback.print_exc()
        fail += 1
        print()

print(f"\nResult: {ok} OK, {fail} FAIL")
