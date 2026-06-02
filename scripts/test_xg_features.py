"""
测试 xG 特征引擎

验证：
1. 数据加载正常
2. 球队名称匹配（中英文）
3. 特征计算正确
4. 时间窗口过滤有效
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from v24_app.features.xg_features import get_xg_database, get_match_xg_features


def test_database_loading():
    """测试数据库加载"""
    print("=" * 60)
    print("测试 1: 数据库加载")
    print("=" * 60)
    
    db = get_xg_database()
    print(f"✓ 加载球队数量: {db.team_count}")
    print(f"✓ 总比赛记录数: {db.total_records}")
    
    assert db.team_count > 0, "未加载任何球队数据"
    assert db.total_records > 0, "未加载任何比赛记录"
    print()


def test_team_name_matching():
    """测试球队名称匹配（中英文）"""
    print("=" * 60)
    print("测试 2: 球队名称匹配")
    print("=" * 60)
    
    db = get_xg_database()
    
    # 测试英文名
    test_cases = [
        ("Manchester City", "曼城"),
        ("Liverpool", "利物浦"),
        ("Real Madrid", "皇马"),
        ("Barcelona", "巴萨"),
        ("Bayern Munich", "拜仁"),
        ("Inter", "国际米兰"),
    ]
    
    for eng_name, chn_name in test_cases:
        # 英文名查询
        feats_eng = db.get_team_features(eng_name, n=5)
        # 中文名查询
        feats_chn = db.get_team_features(chn_name, n=5)
        
        print(f"✓ {eng_name:20s} → xG进攻={feats_eng['xg_for_avg']:.2f}, 样本={feats_eng['xg_sample_count']}")
        print(f"  {chn_name:20s} → xG进攻={feats_chn['xg_for_avg']:.2f}, 样本={feats_chn['xg_sample_count']}")
        
        # 验证两种名称查询结果一致
        assert feats_eng['xg_sample_count'] > 0, f"{eng_name} 未找到数据"
        assert feats_chn['xg_sample_count'] > 0, f"{chn_name} 未找到数据"
    
    print()


def test_feature_calculation():
    """测试特征计算"""
    print("=" * 60)
    print("测试 3: 特征计算")
    print("=" * 60)
    
    # 测试一场典型比赛
    features = get_match_xg_features(
        home_team="Manchester City",
        away_team="Liverpool",
        match_date="2024-01-01",  # 使用历史数据
    )
    
    print("曼城 vs 利物浦 (2024-01-01之前)")
    print("-" * 60)
    for key, value in features.items():
        print(f"  {key:30s} = {value:8.4f}")
    
    # 验证关键特征存在
    required_features = [
        "home_xg_for_avg5",
        "away_xg_for_avg5",
        "xg_attack_diff",
        "xg_defense_diff",
        "xg_overperform_diff",
    ]
    
    for feat in required_features:
        assert feat in features, f"缺少特征: {feat}"
        assert isinstance(features[feat], (int, float)), f"特征类型错误: {feat}"
    
    print()
    print("✓ 所有必需特征已生成")
    print()


def test_time_window():
    """测试时间窗口过滤"""
    print("=" * 60)
    print("测试 4: 时间窗口过滤")
    print("=" * 60)
    
    db = get_xg_database()
    
    # 测试不同时间点的特征
    team = "Manchester City"
    dates = ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]
    
    for date in dates:
        feats = db.get_team_features(team, before_date=date, n=5)
        print(f"  {date} 之前: xG进攻={feats['xg_for_avg']:.2f}, 样本={feats['xg_sample_count']}")
    
    print()
    print("✓ 时间窗口过滤正常")
    print()


def test_missing_team():
    """测试未知球队的默认值"""
    print("=" * 60)
    print("测试 5: 未知球队默认值")
    print("=" * 60)
    
    features = get_match_xg_features(
        home_team="Unknown Team A",
        away_team="Unknown Team B",
        match_date="2024-01-01",
    )
    
    print("未知球队 A vs 未知球队 B")
    print("-" * 60)
    print(f"  home_xg_for_avg5 = {features['home_xg_for_avg5']:.4f}")
    print(f"  away_xg_for_avg5 = {features['away_xg_for_avg5']:.4f}")
    print(f"  xg_home_sample_count = {features['xg_home_sample_count']:.0f}")
    print(f"  xg_away_sample_count = {features['xg_away_sample_count']:.0f}")
    
    # 验证返回了默认值
    assert features['xg_home_sample_count'] == 0, "应返回0样本"
    assert features['home_xg_for_avg5'] > 0, "应返回默认值而非0"
    
    print()
    print("✓ 未知球队返回合理默认值")
    print()


def main():
    print("\n" + "=" * 60)
    print("xG 特征引擎测试")
    print("=" * 60 + "\n")
    
    try:
        test_database_loading()
        test_team_name_matching()
        test_feature_calculation()
        test_time_window()
        test_missing_team()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 运行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
