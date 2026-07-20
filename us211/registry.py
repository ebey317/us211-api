"""Registry mapping US states, DC, and territories to their 211 platform.

211 is federated: each state/region runs on one of a few platforms. This
registry is the single source of truth for "which platform serves which
region", so adding nationwide coverage is a matter of filling in rows, not
writing new scrapers.

Platform values are best-effort. Only entries verified against a live site
should carry a real base_url; everything else is "unknown" until confirmed.
"""
from __future__ import annotations

from enum import Enum


class PlatformType(str, Enum):
    """Known 211 backend platforms."""

    VISIONLINK = "visionlink"
    ICAROL = "icarol"
    FINDHELP = "findhelp"
    UNKNOWN = "unknown"


class Source:
    """A single region's 211 source description."""

    def __init__(self, state: str, name: str, platform: PlatformType, base_url: str | None):
        self.state = state
        self.name = name
        self.platform = platform
        self.base_url = base_url

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "name": self.name,
            "platform": self.platform.value,
            "base_url": self.base_url,
            "wired": self.platform is not PlatformType.UNKNOWN and self.base_url is not None,
        }


# All 50 states + DC + 5 territories.
_STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia",
    # Territories
    "PR": "Puerto Rico", "VI": "U.S. Virgin Islands", "GU": "Guam",
    "AS": "American Samoa", "MP": "Northern Mariana Islands",
}

# Verified/wired overrides. Only Indiana is confirmed so far.
_OVERRIDES: dict[str, tuple[PlatformType, str | None]] = {
    "IN": (PlatformType.VISIONLINK, "https://in211.communityos.org"),
}

REGISTRY: dict[str, Source] = {}
for _code, _name in _STATE_NAMES.items():
    _platform, _url = _OVERRIDES.get(_code, (PlatformType.UNKNOWN, None))
    REGISTRY[_code] = Source(_code, f"{_name} 211", _platform, _url)


def get_source(state_code: str) -> Source | None:
    """Return the Source for a 2-letter state/territory code, or None."""
    return REGISTRY.get(state_code.upper())


def list_states() -> list[dict]:
    """Return every registered region as a serializable dict."""
    return [s.to_dict() for s in REGISTRY.values()]
