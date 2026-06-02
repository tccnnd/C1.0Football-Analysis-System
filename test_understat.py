"""测试 Understat xG 数据获取"""
from understatapi import UnderstatClient

client = UnderstatClient()
results = client.league(league="EPL").get_match_data(season="2023")
print(f"EPL 2023: {len(results)} matches")
if results:
    m = results[0]
    h = m.get("h", {})
    a = m.get("a", {})
    xg = m.get("xG", {})
    print(f"Sample: {h.get('title')} vs {a.get('title')}")
    print(f"  xG home: {xg.get('h')}  xG away: {xg.get('a')}")
    print(f"  Goals: {h.get('goals')}-{a.get('goals')}")
    print(f"  Match ID: {m.get('id')}")
    print(f"  Date: {m.get('datetime')}")
    print(f"  Keys: {list(m.keys())}")
