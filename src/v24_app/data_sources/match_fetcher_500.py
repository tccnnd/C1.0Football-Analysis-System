# -*- coding: utf-8 -*-
"""
500彩票网爬虫模块 v8.2（增强修复版）
修复：日期解析问题、赛事获取不完整、健壮性增强
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin
import json
import os
from typing import List, Dict, Optional, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Match500:
    """500彩票网赛事类"""
    
    def __init__(self, home_team: str, away_team: str, league: str, match_time: str,
                 odds_home: float = None, odds_draw: float = None, odds_away: float = None,
                 match_date: str = None):
        self.home_team = home_team
        self.away_team = away_team
        self.league = league
        self.match_time = match_time
        self.match_date = match_date if match_date else datetime.now().strftime('%Y-%m-%d')
        self.odds_home = odds_home
        self.odds_draw = odds_draw
        self.odds_away = odds_away
        self.match_id = None
        self.is_today = False
        
    def __str__(self):
        return f"{self.match_date} {self.match_time} - {self.league}: {self.home_team} vs {self.away_team}"

class MatchFetcher500:
    """500彩票网赛事获取器（增强修复版）"""
    
    def __init__(self, debug: bool = False, proxy: str = None):
        self.base_url = "https://odds.500.com/europe_jczq.shtml"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.debug = debug
        self.proxy = {'http': proxy, 'https': proxy} if proxy else None
        self.session = requests.Session()
        self.cache_dir = "data/cache"
        self.cache_duration = 300  # 5分钟缓存
        
        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cached_data(self, url: str) -> Optional[str]:
        """获取缓存数据"""
        if not self.cache_dir:
            return None
            
        cache_file = os.path.join(self.cache_dir, f"cache_{hash(url)}.html")
        if os.path.exists(cache_file):
            # 检查缓存是否过期
            file_mtime = os.path.getmtime(cache_file)
            if time.time() - file_mtime < self.cache_duration:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    if self.debug:
                        logger.info(f"从缓存加载: {url}")
                    return f.read()
        return None
    
    def _save_to_cache(self, url: str, content: str):
        """保存到缓存"""
        if not self.cache_dir:
            return
            
        cache_file = os.path.join(self.cache_dir, f"cache_{hash(url)}.html")
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def fetch_page(self, url: str = None, use_cache: bool = True) -> Optional[str]:
        """获取网页内容（带缓存和重试）"""
        url = url or self.base_url
        
        # 尝试从缓存获取
        if use_cache:
            cached_content = self._get_cached_data(url)
            if cached_content:
                return cached_content
        
        retries = 3
        for attempt in range(retries):
            try:
                if self.debug:
                    logger.info(f"请求 {url} (尝试 {attempt + 1}/{retries})")
                
                response = self.session.get(url, headers=self.headers, 
                                          proxies=self.proxy, timeout=15)
                response.raise_for_status()
                
                # 检查是否为有效HTML
                if 'charset=' not in response.text[:1000]:
                    response.encoding = 'gbk'
                else:
                    response.encoding = 'utf-8'
                
                content = response.text
                
                # 保存到缓存
                self._save_to_cache(url, content)
                
                # 保存原始HTML用于调试
                if self.debug:
                    raw_file = f"data/500_odds_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    with open(raw_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"原始HTML已保存: {raw_file}")
                
                return content
                
            except requests.RequestException as e:
                logger.warning(f"请求失败 ({attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    logger.error(f"所有重试失败: {url}")
                    return None
            except Exception as e:
                logger.error(f"获取页面时发生未知错误: {e}")
                return None
    
    def _parse_match_time(self, time_text: str) -> Tuple[str, str, bool]:
        """修复版：解析比赛时间，解决日期识别问题"""
        today = datetime.now()
        today_date = today.strftime("%Y-%m-%d")
        today_str = today.strftime("%m-%d")
        
        # 清理文本
        time_text = time_text.strip()
        
        if self.debug:
            logger.debug(f"解析时间文本: '{time_text}'")
        
        # 处理各种时间格式
        if '周' in time_text:
            # 格式: "01-19 周日 19:30"
            parts = time_text.split()
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[-1] if ':' in parts[-1] else "00:00"
                
                # 添加年份
                year = today.year
                month_day = date_part.split('-')
                if len(month_day) == 2:
                    try:
                        month = int(month_day[0])
                        day = int(month_day[1])
                        
                        # 处理跨年情况
                        if month < today.month:
                            year += 1
                        
                        parsed_date = datetime(year, month, day)
                        is_today = (parsed_date.date() == today.date())
                        return parsed_date.strftime("%Y-%m-%d"), time_part, is_today
                    except ValueError as e:
                        logger.warning(f"日期解析失败 '{date_part}': {e}")
        elif ':' in time_text and '-' in time_text:
            # 格式: "01-19 19:30"
            parts = time_text.split()
            if len(parts) >= 1:
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else "00:00"
                
                # 添加年份
                year = today.year
                month_day = date_part.split('-')
                if len(month_day) == 2:
                    try:
                        month = int(month_day[0])
                        day = int(month_day[1])
                        
                        # 处理跨年情况
                        if month < today.month:
                            year += 1
                        
                        parsed_date = datetime(year, month, day)
                        is_today = (parsed_date.date() == today.date())
                        return parsed_date.strftime("%Y-%m-%d"), time_part, is_today
                    except ValueError as e:
                        logger.warning(f"日期解析失败 '{date_part}': {e}")
        elif ':' in time_text:
            # 只有时间，没有日期 - 默认为今日
            time_part = time_text
            is_today = True
            return today_date, time_part, is_today
        elif '已结束' in time_text or '完场' in time_text:
            # 已结束的比赛
            return today_date, "00:00", True
        
        # 默认返回今日
        return today_date, "00:00", True
    
    def parse_matches(self, html_content: str) -> List[Match500]:
        """解析比赛数据（增强版）"""
        if not html_content:
            return []
        
        matches = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找比赛表格
        table = soup.find('table', {'class': 'lqbf_table'})
        if not table:
            logger.warning("未找到比赛表格")
            return matches
        
        # 查找所有比赛行
        rows = table.find_all('tr', {'class': False})  # 排除表头行
        
        for row in rows:
            try:
                # 跳过空行
                if not row.find('td'):
                    continue
                
                # 获取列数据
                cols = row.find_all('td')
                if len(cols) < 10:
                    continue
                
                # 解析时间
                time_cell = cols[0].get_text(strip=True)
                match_date, match_time, is_today = self._parse_match_time(time_cell)
                
                # 只获取今天和未来的比赛
                if not is_today:
                    parsed_date = datetime.strptime(match_date, "%Y-%m-%d")
                    if parsed_date.date() < datetime.now().date():
                        continue
                
                # 解析联赛
                league_cell = cols[1]
                league = league_cell.get_text(strip=True)
                league = re.sub(r'\[\d+\]', '', league)  # 移除[数字]
                
                # 解析球队
                teams_cell = cols[2]
                team_links = teams_cell.find_all('a')
                if len(team_links) >= 2:
                    home_team = team_links[0].get_text(strip=True)
                    away_team = team_links[1].get_text(strip=True)
                else:
                    # 备用解析方法
                    team_text = teams_cell.get_text(strip=True)
                    if ' vs ' in team_text:
                        home_team, away_team = team_text.split(' vs ', 1)
                    elif ' VS ' in team_text:
                        home_team, away_team = team_text.split(' VS ', 1)
                    else:
                        home_team = team_text[:len(team_text)//2]
                        away_team = team_text[len(team_text)//2:]
                
                # 解析赔率
                try:
                    odds_home = float(cols[3].get_text(strip=True)) if cols[3].get_text(strip=True) else None
                    odds_draw = float(cols[4].get_text(strip=True)) if cols[4].get_text(strip=True) else None
                    odds_away = float(cols[5].get_text(strip=True)) if cols[5].get_text(strip=True) else None
                except ValueError:
                    odds_home = odds_draw = odds_away = None
                
                # 创建比赛对象
                match = Match500(
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_time=match_time,
                    odds_home=odds_home,
                    odds_draw=odds_draw,
                    odds_away=odds_away,
                    match_date=match_date
                )
                match.is_today = is_today
                
                # 生成比赛ID
                match.match_id = f"500_{hash(f'{match_date}{league}{home_team}{away_team}')}"
                
                matches.append(match)
                
                if self.debug:
                    logger.info(f"解析到比赛: {match}")
                    
            except Exception as e:
                logger.error(f"解析比赛行失败: {e}")
                continue
        
        if self.debug:
            logger.info(f"共解析到 {len(matches)} 场比赛")
        
        return matches
    
    @staticmethod
    def _parse_match_datetime(match: "Match500") -> datetime | None:
        try:
            return datetime.strptime(f"{match.match_date} {match.match_time}", "%Y-%m-%d %H:%M")
        except Exception:
            return None

    @staticmethod
    def _current_issue_window(now: datetime) -> tuple[datetime, datetime]:
        issue_start = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if now < issue_start:
            issue_start = issue_start - timedelta(days=1)
        return issue_start, issue_start + timedelta(days=1)

    def get_today_matches(self) -> List[Match500]:
        """获取今日比赛（只获取当天竞彩数据）"""
        logger.info("获取今日竞彩赛事...")
        
        html_content = self.fetch_page()
        if not html_content:
            logger.error("无法获取网页内容")
            return []
        
        all_matches = self.parse_matches(html_content)
        
        # 竞彩期口径：11:00 ~ 次日 11:00
        now = datetime.now()
        issue_start, issue_end = self._current_issue_window(now)
        today_matches = []
        today_date = now.date()

        for match in all_matches:
            match_dt = self._parse_match_datetime(match)
            if match_dt is None:
                logger.warning(f"解析比赛日期失败: {match.match_date} {match.match_time}")
                continue
            if issue_start <= match_dt < issue_end:
                today_matches.append(match)

        logger.info(f"当期比赛数量(11:00~次日11:00): {len(today_matches)}")
        
        # 如果没有今日比赛，尝试获取最近的比赛
        if len(today_matches) == 0 and len(all_matches) > 0:
            logger.info("未找到今日比赛，返回最近的比赛")
            # 返回未来3天内的比赛
            future_matches = []
            for match in all_matches:
                try:
                    match_date = datetime.strptime(match.match_date, "%Y-%m-%d").date()
                    days_diff = (match_date - today_date).days
                    if 0 <= days_diff <= 3:
                        future_matches.append(match)
                except:
                    continue
            
            if future_matches:
                logger.info(f"返回未来 {len(future_matches)} 场比赛")
                return future_matches
        
        return today_matches
    
    def get_upcoming_matches(self, days_ahead: int = 3) -> List[Match500]:
        """获取未来几天的比赛"""
        logger.info(f"获取未来{days_ahead}天赛事...")
        
        html_content = self.fetch_page()
        if not html_content:
            return []
        
        all_matches = self.parse_matches(html_content)
        
        # 筛选未来比赛
        upcoming_matches = []
        today_date = datetime.now().date()
        target_date = today_date + timedelta(days=days_ahead)
        
        for match in all_matches:
            try:
                match_date = datetime.strptime(match.match_date, "%Y-%m-%d").date()
                if today_date <= match_date <= target_date:
                    upcoming_matches.append(match)
            except:
                continue
        
        logger.info(f"未来{days_ahead}天比赛数量: {len(upcoming_matches)}")
        return upcoming_matches

# 创建全局实例
fetcher_500 = MatchFetcher500(debug=False)

if __name__ == "__main__":
    # 测试代码
    print("测试500彩票网爬虫...")
    fetcher = MatchFetcher500(debug=True)
    matches = fetcher.get_today_matches()
    
    print(f"\n找到 {len(matches)} 场今日比赛:")
    for match in matches[:5]:  # 显示前5场
        print(f"  {match.match_date} {match.match_time} | {match.league}")
        print(f"    {match.home_team} vs {match.away_team}")
        print(f"    赔率: 主胜={match.odds_home}, 平={match.odds_draw}, 客胜={match.odds_away}")
        print()
