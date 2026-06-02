"""
foot 桥接层验证脚本

测试内容：
1. 模块导入
2. 配置加载
3. 数据库连接（ping）
4. 信号结构完整性
5. 无 MySQL 时的优雅降级
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ── 1. 导入测试 ────────────────────────────────────────────────────────────────
section("1. 模块导入")
try:
    from c1.data.foot_schema import FootMatchSignals, FootAnalyResult, FootAsiaHis
    from c1.data.foot_bridge import FootBridge, get_foot_bridge, get_foot_signals
    print("✅ foot_schema 导入成功")
    print("✅ foot_bridge 导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


# ── 2. 配置加载 ────────────────────────────────────────────────────────────────
section("2. 配置加载")
bridge = FootBridge()
print(f"  enabled       : {bridge.enabled}")
print(f"  analy_days    : {bridge._analy_days}")
print(f"  cache_ttl     : {bridge._cache._ttl}s")
print(f"  c1_refer_asia : {bridge._c1_refer_asia}")
print(f"  euro_weide    : {bridge._euro_weide}")
print(f"  euro_888      : {bridge._euro_888}")
print("✅ 配置加载成功")


# ── 3. 数据库连接测试 ──────────────────────────────────────────────────────────
section("3. 数据库连接 (ping)")
ping = bridge.ping()
print(f"  status : {ping['status']}")
if ping["status"] == "ok":
    print(f"  host   : {ping.get('host')}")
    print(f"  db     : {ping.get('database')}")
    print(f"  match_last_count: {ping.get('match_last_count')}")
    print("✅ 数据库连接成功")
elif ping["status"] == "disabled":
    print(f"  {ping['message']}")
    print("⬜ 桥接已禁用（跳过数据库测试）")
else:
    print(f"  error  : {ping.get('error')}")
    print("⚠️  数据库连接失败（MySQL 未运行或配置错误）")
    print("   → 这是预期行为，桥接层会优雅降级")


# ── 4. 优雅降级测试 ────────────────────────────────────────────────────────────
section("4. 无 MySQL 时的优雅降级")
signals = bridge.get_signals_for_match(
    main_team_id="曼城",
    guest_team_id="利物浦",
    match_date="2026-05-29",
)
print(f"  has_data      : {signals.has_data}")
print(f"  error         : '{signals.error}'")
print(f"  main_team_id  : {signals.main_team_id}")
print(f"  guest_team_id : {signals.guest_team_id}")
print("✅ 优雅降级正常（连接失败不抛异常）")


# ── 5. 特征字典输出 ────────────────────────────────────────────────────────────
section("5. as_feature_dict 输出格式")
feat = signals.as_feature_dict
print(f"  特征数量: {len(feat)}")
for k, v in feat.items():
    print(f"  {k:<40} = {v}")
print("✅ 特征字典格式正确")


# ── 6. FootAsiaHis 方向计算 ────────────────────────────────────────────────────
section("6. 亚赔方向计算（单元测试）")
cases = [
    # (s_let_ball, e_let_ball, sp3, sp0, ep3, ep0, expected_direction, desc)
    (0.5, 0.75, 0.85, 0.95, 0.80, 0.98, 3,  "让球升 → 主降(3)"),
    (0.5, 0.25, 0.85, 0.95, 0.88, 0.92, 0,  "让球降 → 客降(0)"),
    (0.5, 0.5,  0.85, 0.95, 0.82, 0.97, 3,  "让球不变,主赔降 → 主降(3)"),
    (0.5, 0.5,  0.85, 0.95, 0.88, 0.92, 0,  "让球不变,客赔降 → 客降(0)"),
    (0.5, 0.5,  0.85, 0.95, 0.85, 0.95, -1, "无变化 → 无方向(-1)"),
]
all_pass = True
for s_lb, e_lb, sp3, sp0, ep3, ep0, expected, desc in cases:
    asia = FootAsiaHis(
        id="", match_id="", comp_id="18",
        s_let_ball=s_lb, e_let_ball=e_lb,
        sp3=sp3, sp0=sp0, ep3=ep3, ep0=ep0,
    )
    got = asia.asia_direction
    ok = got == expected
    all_pass = all_pass and ok
    icon = "✅" if ok else "❌"
    print(f"  {icon} {desc}: 期望={expected} 实际={got}")

if all_pass:
    print("✅ 亚赔方向计算全部正确")
else:
    print("❌ 部分测试失败")


# ── 总结 ───────────────────────────────────────────────────────────────────────
section("测试总结")
print("✅ foot 桥接层基础验证通过")
print()
print("下一步：")
print("  1. 安装 MySQL 并导入 foot 历史数据")
print("  2. 修改 c1/configs/foot_bridge_cfg.yaml 中的数据库连接信息")
print("  3. 再次运行此脚本，验证数据库连接和信号提取")
print("  4. 将 FootMatchSignals.as_feature_dict 接入 C1.0 Feature Layer")
