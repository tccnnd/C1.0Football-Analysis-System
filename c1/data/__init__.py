from .adapters import LegacyMatchAdapterOutput, adapt_legacy_match, adapt_legacy_matches
from .availability import build_match_context, build_team_availability
from .availability_store import C1AvailabilityStore, load_rows_from_file
from .availability_templates import (
    TEMPLATE_COLUMNS,
    build_availability_template_rows,
    export_availability_template_csv,
)
from .contracts import CanonicalMatch, MatchContext, OddsSnapshot, TeamAvailability
from .providers import (
    ApiFootballAvailabilityProvider,
    AvailabilityProviderChain,
    AvailabilityProviderResult,
    CrawlerAvailabilityProvider,
    FileAvailabilityProvider,
    HttpAvailabilityProvider,
    StoredAvailabilityProvider,
    TitanDetailAvailabilityProvider,
    load_availability_provider_config,
)
from .provider_normalizers import normalize_api_football_rows, normalize_provider_rows, normalize_sportmonks_rows

__all__ = [
    "C1AvailabilityStore",
    "ApiFootballAvailabilityProvider",
    "AvailabilityProviderChain",
    "AvailabilityProviderResult",
    "CanonicalMatch",
    "CrawlerAvailabilityProvider",
    "FileAvailabilityProvider",
    "HttpAvailabilityProvider",
    "LegacyMatchAdapterOutput",
    "MatchContext",
    "OddsSnapshot",
    "StoredAvailabilityProvider",
    "TitanDetailAvailabilityProvider",
    "TEMPLATE_COLUMNS",
    "TeamAvailability",
    "adapt_legacy_match",
    "adapt_legacy_matches",
    "build_availability_template_rows",
    "build_match_context",
    "build_team_availability",
    "export_availability_template_csv",
    "load_availability_provider_config",
    "load_rows_from_file",
    "normalize_api_football_rows",
    "normalize_provider_rows",
    "normalize_sportmonks_rows",
]
