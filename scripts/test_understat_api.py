"""
测试 understatapi 的数据结构，了解可用字段
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from understatapi import UnderstatClient

with UnderstatClient() as client:
    # 1. 英超 2023-24 赛季比赛列表
    print("=== 英超 2023-24 赛季比赛列表 ===")
    matches = client.league(league="EPL").get_match_data(season="2023")
    print(f"总场次: {len(matches)}")
    m = matches[0]
    print("字段:", list(m.keys()))
    print("示例:", json.dumps(m, ensure_ascii=False, indent=2))

    # 2. 单场射门数据
    print("\n=== 单场射门数据 ===")
    match_id = str(m.get("id", ""))
    shots = client.match(match_id=match_id).get_shot_data()
    print(f"类型: {type(shots)}")
    if isinstance(shots, dict):
        home_shots = shots.get("h", [])
        away_shots = shots.get("a", [])
        print(f"主队: {len(home_shots)}次  客队: {len(away_shots)}次")
        if home_shots:
            print("射门字段:", list(home_shots[0].keys()))
            print("射门示例:", json.dumps(home_shots[0], ensure_ascii=False, indent=2))
