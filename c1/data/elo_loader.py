from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_elo_ratings(project_root: str | Path) -> dict[str, float]:
    """
    Load ELO ratings from V24 state files (both club and national).
    
    Returns a dict mapping team name to rating.
    If files don't exist or are malformed, returns empty dict.
    
    Loads from:
    - data/state/elo_ratings.json (club teams)
    - data/state/national_team_elo_ratings.json (national teams)
    """
    root = Path(project_root)
    ratings = {}
    
    # Load club ELO ratings
    club_file = root / "data" / "state" / "elo_ratings.json"
    if club_file.exists():
        try:
            payload = json.loads(club_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                club_ratings = payload.get("ratings", {})
                if isinstance(club_ratings, dict):
                    for key, value in club_ratings.items():
                        if value not in (None, ""):
                            ratings[str(key)] = float(value)
        except Exception:
            pass
    
    # Load national ELO ratings
    national_file = root / "data" / "state" / "national_team_elo_ratings.json"
    if national_file.exists():
        try:
            payload = json.loads(national_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                national_ratings = payload.get("ratings", {})
                if isinstance(national_ratings, dict):
                    for key, value in national_ratings.items():
                        if value not in (None, ""):
                            ratings[str(key)] = float(value)
        except Exception:
            pass
    
    return ratings


def resolve_team_rating(team_name: str, ratings: dict[str, float], default: float = 1500.0) -> float:
    """
    Resolve a team's ELO rating from the ratings dict.
    
    Tries multiple matching strategies:
    1. Exact match
    2. Case-insensitive match
    3. Substring match (for teams with suffixes like "联" or "FC")
    4. Fuzzy match (Levenshtein distance)
    
    Returns default if not found.
    """
    if not team_name:
        return default
    
    text = str(team_name).strip()
    
    # Strategy 1: Exact match
    if text in ratings:
        return float(ratings[text])
    
    # Strategy 2: Case-insensitive match
    text_lower = text.lower()
    for key, value in ratings.items():
        if str(key).lower() == text_lower:
            return float(value)
    
    # Strategy 3: Substring match (for Chinese teams with suffixes)
    # e.g., "阿德莱德联" -> "阿德莱德"
    for key, value in ratings.items():
        key_str = str(key)
        # Check if key is a substring of text or vice versa
        if key_str in text or text in key_str:
            # Prefer longer matches (more specific)
            if len(key_str) > 2:  # Avoid matching too short strings
                return float(value)
    
    # Strategy 4: Fuzzy match using simple Levenshtein distance
    # Only use if no other match found
    min_distance = float('inf')
    best_match = None
    
    for key, value in ratings.items():
        key_str = str(key)
        # Only consider keys of similar length
        if abs(len(key_str) - len(text)) <= 3:
            distance = _levenshtein_distance(text, key_str)
            if distance < min_distance:
                min_distance = distance
                best_match = value
    
    # Use fuzzy match if distance is small enough
    if best_match is not None and min_distance <= 2:
        return float(best_match)
    
    return default


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]
