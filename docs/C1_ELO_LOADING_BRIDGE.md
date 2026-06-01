# C1.0 ELO Loading Bridge

**Date**: 2026-05-27  
**Status**: Implemented  
**Impact**: Fixes P0 short-circuit in inference signal strength

## Problem

The C1.0 inference layer was receiving `home_rating = 1500.0` and `away_rating = 1500.0` for nearly all matches, because:

1. `build_inference_input()` reads `home_rating` and `away_rating` from `feature_snapshot.fields`
2. `adapt_legacy_match()` builds `raw_fields` from the caller's `source_payload`
3. The legacy bridge (`legacy_bridge.py`) was not loading ELO ratings from V24's state file

Result: The ELO component in the ensemble had zero signal, and confidence scores were artificially suppressed (0.25–0.42 range).

## Solution

### New Module: `c1/data/elo_loader.py`

Two functions:

- **`load_elo_ratings(project_root: str | Path) -> dict[str, float]`**
  - Loads ELO ratings from `data/state/elo_ratings.json`
  - Returns a dict mapping team name → rating
  - Gracefully handles missing or malformed files (returns empty dict)

- **`resolve_team_rating(team_name: str, ratings: dict[str, float], default: float = 1500.0) -> float`**
  - Resolves a team's rating from the ratings dict
  - Tries exact match first, then case-insensitive match
  - Returns default (1500.0) if not found

### Updated: `c1/runtime/legacy_bridge.py`

Both `run_shadow_for_legacy_match()` and `run_shadow_for_legacy_matches()` now:

1. Load ELO ratings from V24 state at the start
2. Extract home and away team names from the match
3. Resolve their ratings using `resolve_team_rating()`
4. Inject `home_rating` and `away_rating` into `extra_fields` if not already present
5. Pass merged fields to `adapt_legacy_match()`

This ensures that by the time `build_inference_input()` is called, the feature snapshot contains actual ELO ratings.

### Updated: `c1/data/__init__.py`

Exported the new functions:
- `load_elo_ratings`
- `resolve_team_rating`

## Impact

### Before

```
Typical match:
  home_rating: 1500.0 (default)
  away_rating: 1500.0 (default)
  ELO component: zero signal
  confidence: 0.25–0.42 (suppressed)
  missing_elo_loss: 0.5 (triggers MISSING_ELO_LOSS soft reason)
```

### After

```
Typical match (e.g., Manchester United vs Manchester City):
  home_rating: 1756.25 (from V24 state)
  away_rating: 1871.46 (from V24 state)
  ELO component: strong signal
  confidence: expected to increase to 0.50–0.70+ range
  missing_elo_loss: 0.0 (no longer triggers)
```

## Data Source

ELO ratings are loaded from:
- **File**: `data/state/elo_ratings.json`
- **Structure**: `{ "updated_at": "...", "ratings": { "team_name": rating, ... } }`
- **Coverage**: 1,211 teams as of 2026-05-26

The ratings are maintained by V24's settlement process and are updated after each match result.

## Testing

Unit tests in `tests/test_c1_elo_loader.py`:
- Load from file
- Handle missing file
- Handle malformed JSON
- Exact team name match
- Case-insensitive match
- Default fallback

All tests pass.

## Integration Points

1. **Legacy Bridge**: Automatically loads and injects ELO ratings when running shadow comparisons
2. **Feature Snapshot**: ELO ratings are now part of the feature vector
3. **Inference**: ELO component receives real signal instead of default
4. **Governance**: `missing_elo_loss` feature is now accurate (0.0 when ratings are present)
5. **Audit**: ELO ratings are recorded in feature vectors for traceability

## Backward Compatibility

- If ELO ratings file is missing or malformed, falls back to 1500.0 (no breaking change)
- Existing code that passes `home_rating`/`away_rating` explicitly is not affected
- The bridge only injects ratings if they are not already present in `extra_fields`

## Next Steps

1. Re-run C1 shadow comparison on live matches to observe confidence improvement
2. Monitor governance decision distribution (expect fewer DOWNGRADE due to reduced `missing_elo_loss`)
3. Verify that release gate now passes more matches (once `release_cfg.yaml` is updated to allow DOWNGRADE)
