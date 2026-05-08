# Historical Training Sample Schema

This project can use `2021-2026` historical matches as XGB training samples.

## Goal

Import historical match data into:

- `E:\APP\ELO\data\state\xgb_training_samples.json`
- optionally `E:\APP\ELO\data\state\elo_ratings.json`

The importer converts raw historical rows into the current XGB feature set:

- `market_home`
- `market_draw`
- `market_away`
- `odds_home`
- `odds_draw`
- `odds_away`
- `home_rating`
- `away_rating`
- `rating_diff`
- `rating_gap_abs`
- `league_strength`
- `match_minutes`
- `is_weekend`

## Supported Input Files

- `.csv`
- `.json`
- `.jsonl`

## Minimum Required Fields

The importer accepts aliases, but the logical fields below are required:

| Logical Field | Meaning |
|---|---|
| `match_date` | match date |
| `league` | competition name |
| `home_team` | home team |
| `away_team` | away team |
| `odds_home` | home win odds |
| `odds_draw` | draw odds |
| `odds_away` | away win odds |
| `home_goals` | full-time home goals |
| `away_goals` | full-time away goals |

## Optional Fields

These fields improve downstream usefulness but are not mandatory:

| Logical Field | Meaning |
|---|---|
| `match_time` | kickoff time, default `00:00` |
| `kickoff` | combined datetime field |
| `home_ht_goals` | half-time home goals |
| `away_ht_goals` | half-time away goals |
| `handicap_line` | handicap line |
| `league_strength` | league strength override |
| `home_rating` | explicit pre-match home rating |
| `away_rating` | explicit pre-match away rating |
| `match_id` | custom unique id |

If `home_rating` / `away_rating` are missing, the importer rebuilds pre-match Elo chronologically from the historical results themselves.

## Accepted Header Aliases

Examples of accepted aliases:

- `match_date`: `date`, `kickoff_date`, `matchday`
- `match_time`: `time`, `kickoff_time`
- `kickoff`: `datetime`, `kickoff_datetime`, `start_time`
- `league`: `competition`, `league_name`, `tournament`
- `home_team`: `home`, `home_name`
- `away_team`: `away`, `away_name`
- `odds_home`: `home_odds`, `win_odds`, `sp_home`
- `odds_draw`: `draw_odds`, `tie_odds`, `sp_draw`
- `odds_away`: `away_odds`, `lose_odds`, `sp_away`
- `home_goals`: `home_score`, `full_home_score`, `ft_home_goals`
- `away_goals`: `away_score`, `full_away_score`, `ft_away_goals`

## CSV Example

```csv
match_date,match_time,league,home_team,away_team,odds_home,odds_draw,odds_away,home_goals,away_goals,home_ht_goals,away_ht_goals,handicap_line
2024-09-01,19:35,中超,上海海港,山东泰山,1.68,3.70,4.60,2,1,1,0,-1
2024-09-01,21:00,英超,阿森纳,切尔西,1.95,3.45,3.90,1,1,0,1,-0.5
```

## Import Command

Merge into current sample pool:

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\import_historical_samples.py --input D:\data\history_matches.csv
```

Replace current sample pool:

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\import_historical_samples.py --input D:\data\history_matches.csv --replace
```

Import and train immediately:

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\import_historical_samples.py --input D:\data\history_matches.csv --replace --train
```

Import and sync rebuilt Elo ratings into the live app:

```powershell
E:\APP\ELO\venv\Scripts\python.exe E:\APP\ELO\scripts\import_historical_samples.py --input D:\data\history_matches.csv --replace --sync-ratings
```

## Current Scope

This importer currently trains the `1X2` XGB model only.

It already preserves enough metadata for later expansion to:

- total goals
- half/full-time
- score
- handicap

## Recommended Split

Do not evaluate with random split.

Use time split:

- train: `2021-2024`
- validation: `2025`
- test: `2026`

## Practical Recommendation

For your current app, the safest first run is:

1. Import all historical data into `xgb_training_samples.json`
2. Train XGB once
3. Verify label distribution and model status
4. Then decide whether to sync rebuilt Elo ratings into the live app
