"""
foot (Go) 项目数据结构定义

对应 foot-api/module/ 下的 pojo 结构，用 Python dataclass 表示。
命名保持与 Go 原始字段一致，方便对照。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ── 比赛 ──────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FootMatchLast:
    """t_match_last — 当日比赛临时表"""
    id: str
    match_date: Optional[datetime]
    league_id: str
    main_team_id: str
    guest_team_id: str
    main_team_goals: int = -1   # -1 表示未开赛
    guest_team_goals: int = -1
    data_date: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_finished(self) -> bool:
        return self.main_team_goals >= 0 and self.guest_team_goals >= 0

    @property
    def match_result(self) -> int:
        """3=主胜 1=平 0=客胜 -1=未知"""
        if not self.is_finished:
            return -1
        if self.main_team_goals > self.guest_team_goals:
            return 3
        if self.main_team_goals < self.guest_team_goals:
            return 0
        return 1


@dataclass(slots=True)
class FootMatchHis:
    """t_match_his — 历史比赛表"""
    id: str
    match_date: Optional[datetime]
    league_id: str
    main_team_id: str
    guest_team_id: str
    main_team_goals: int
    guest_team_goals: int
    data_date: Optional[datetime] = None


# ── 赔率 ──────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FootAsiaHis:
    """t_asia_his — 亚赔历史（初盘+即时盘）"""
    id: str
    match_id: str
    comp_id: str            # 公司 ID
    s_let_ball: float       # 初盘让球
    e_let_ball: float       # 即时让球
    sp3: float              # 初盘主胜赔率
    sp0: float              # 初盘客胜赔率
    ep3: float              # 即时主胜赔率
    ep0: float              # 即时客胜赔率

    @property
    def asia_direction(self) -> int:
        """
        亚赔方向：3=主降（利主）0=客降（利客）-1=无明确方向
        复现 AnalyService.AsiaDirection() 逻辑
        """
        slb = self.s_let_ball
        elb = self.e_let_ball
        ep3_small = self.ep3 < self.sp3
        ep0_small = self.ep0 < self.sp0

        if elb > 0:
            if elb > slb:
                return 3
            if elb < slb:
                return 0
            # 让球不变，看赔率
            if ep3_small and not ep0_small:
                return 3
            if not ep3_small and ep0_small:
                return 0
        else:
            if elb < slb:
                return 0
            if elb > slb:
                return 3
            if ep3_small and not ep0_small:
                return 3
            if not ep3_small and ep0_small:
                return 0
        return -1

    @property
    def main_is_giving_ball(self) -> bool:
        """主队是否是让球方（复现 mainLetball 逻辑）"""
        if self.e_let_ball > 0:
            return True
        if self.e_let_ball < 0:
            return False
        # 平盘，看赔率
        return self.ep3 <= self.ep0


@dataclass(slots=True)
class FootEuroHis:
    """t_euro_his — 欧赔历史（初盘+即时盘）"""
    id: str
    match_id: str
    comp_id: str
    sp3: float      # 初盘主胜
    sp1: float      # 初盘平
    sp0: float      # 初盘客胜
    ep3: float      # 即时主胜
    ep1: float      # 即时平
    ep0: float      # 即时客胜


# ── 基本面 ────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FootBFScore:
    """t_b_f_score — 积分榜"""
    id: str
    match_id: str
    team_id: str
    type: str           # "总" / "主" / "客"
    ranking: int        # 排名（越小越好）
    match_count: int    # 已打场次
    win: int = 0
    draw: int = 0
    lose: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0


@dataclass(slots=True)
class FootBFBattle:
    """t_b_f_battle — 主客队对战历史"""
    id: str
    match_id: str
    battle_main_team_id: str
    battle_guest_team_id: str
    battle_main_team_goals: int
    battle_guest_team_goals: int
    battle_date: Optional[datetime] = None


@dataclass(slots=True)
class FootBFJin:
    """t_b_f_jin — 近期战绩"""
    id: str
    match_id: str
    home_team: str
    guest_team: str
    home_score: int
    guest_score: int
    match_date: Optional[datetime] = None


@dataclass(slots=True)
class FootBFFutureEvent:
    """t_b_f_future_event — 未来赛事"""
    id: str
    match_id: str
    event_main_team_id: str
    event_guest_team_id: str
    event_league_id: str
    event_date: Optional[datetime] = None


# ── 分析结果 ──────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FootAnalyResult:
    """t_analy_result — 分析预测结果"""
    id: str
    match_id: str
    match_date: Optional[datetime]
    al_flag: str            # 模型名：A1/C1/E2/...
    al_seq: str             # 分析序列号
    pre_result: int         # 预测结果：3=主胜 1=平 0=客胜
    result: str             # 命中/错误/未知/待定/走盘
    hit_count: int          # 命中计数（置信度代理）
    t_hit_count: int        # 目标命中次数
    let_ball: float         # 即时让球
    s_let_ball: float       # 初盘让球
    my_let_ball: float      # 模型计算让球（C1专用）
    to_void: bool           # 是否作废（杯赛等）
    to_void_desc: str       # 作废原因

    @property
    def pre_result_label(self) -> str:
        """预测结果文字"""
        return {3: "主胜", 1: "平局", 0: "客胜"}.get(self.pre_result, "未知")

    @property
    def is_hit(self) -> bool:
        return self.result == "命中"

    @property
    def is_valid(self) -> bool:
        """是否是有效结果（非作废、非杯赛）"""
        return not self.to_void

    @property
    def confidence_proxy(self) -> float:
        """
        用 hit_count 作为置信度代理。
        foot 项目中 hit_count >= 3 才进入推荐列表。
        归一化到 [0, 1]，最大值设为 10。
        """
        return min(self.hit_count / 10.0, 1.0)


# ── 联赛 ──────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class FootLeague:
    """t_league — 联赛表"""
    id: str
    name: str

    @property
    def is_cup(self) -> bool:
        """是否是杯赛（复现 IsCupMatch 逻辑）"""
        return "杯" in self.name or "锦" in self.name


# ── 聚合信号（桥接层输出） ────────────────────────────────────────────────────

@dataclass
class FootMatchSignals:
    """
    针对单场比赛，从 foot MySQL 提取的所有信号聚合体。
    这是桥接层向 C1.0 Feature Layer 输出的标准格式。
    """
    match_id: str                       # foot 内部 match_id
    match_date: Optional[datetime]
    main_team_id: str
    guest_team_id: str
    league_id: str
    league_name: str = ""

    # ── 亚赔信号 ──
    asia_direction: int = -1            # 多公司亚赔方向共识：3/0/-1
    asia_direction_consensus: float = 0.0  # 共识强度 [0,1]
    asia_let_ball_instant: float = 0.0  # 即时让球
    asia_let_ball_opening: float = 0.0  # 初盘让球
    asia_let_ball_move: float = 0.0     # 让球变化量（即时-初盘）

    # ── 欧赔信号 ──
    euro_direction: int = -1            # 欧赔方向：3=主降 0=客降 -1=无
    euro_asia_conflict: bool = False    # 欧亚联动冲突（A1 核心信号）

    # ── 基本面信号（C1 模型） ──
    ranking_diff: float = 0.0           # 积分榜排名差（主-客，负值=主队排名更好）
    h2h_main_win_rate: float = 0.0      # 近期对战主队胜率
    recent_main_win_rate: float = 0.0   # 近期战绩主队胜率
    recent_guest_win_rate: float = 0.0  # 近期战绩客队胜率
    c1_my_let_ball: float = 0.0         # C1 模型计算的 BF 让球
    c1_let_ball_diff: float = 0.0       # BF让球 - 盘口让球

    # ── 模型结论信号 ──
    model_signals: dict[str, int] = field(default_factory=dict)
    # 格式：{"A1": 3, "C1": 3, "E2": 3}  值：3=主胜 1=平 0=客胜 -1=无结论

    model_consensus: int = -1           # 多模型共识方向
    model_consensus_count: int = 0      # 共识模型数量
    model_conflict: bool = False        # 模型间是否有冲突

    # ── 元数据 ──
    fetched_at: str = ""
    source: str = "foot_mysql"
    error: str = ""                     # 非空表示获取失败

    @property
    def has_data(self) -> bool:
        return not self.error and (
            self.asia_direction != -1
            or self.euro_direction != -1
            or bool(self.model_signals)
        )

    @property
    def as_feature_dict(self) -> dict[str, Any]:
        """转换为 C1.0 Feature Layer 可直接使用的字典"""
        return {
            "foot_asia_direction": self.asia_direction,
            "foot_asia_direction_consensus": self.asia_direction_consensus,
            "foot_asia_let_ball_instant": self.asia_let_ball_instant,
            "foot_asia_let_ball_opening": self.asia_let_ball_opening,
            "foot_asia_let_ball_move": self.asia_let_ball_move,
            "foot_euro_direction": self.euro_direction,
            "foot_euro_asia_conflict": int(self.euro_asia_conflict),
            "foot_ranking_diff": self.ranking_diff,
            "foot_h2h_main_win_rate": self.h2h_main_win_rate,
            "foot_recent_main_win_rate": self.recent_main_win_rate,
            "foot_recent_guest_win_rate": self.recent_guest_win_rate,
            "foot_c1_my_let_ball": self.c1_my_let_ball,
            "foot_c1_let_ball_diff": self.c1_let_ball_diff,
            "foot_model_consensus": self.model_consensus,
            "foot_model_consensus_count": self.model_consensus_count,
            "foot_model_conflict": int(self.model_conflict),
            # 各模型单独信号
            **{
                f"foot_{k.lower()}_signal": v
                for k, v in self.model_signals.items()
            },
        }
