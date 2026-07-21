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

# Verified 211 web addresses (researched 2026-07-20). Platform is a
# base_url = the official public 211 site for that region.
# Platform is a best-effort guess. VisionLink = *.communityos.org. findhelp =
# states confirmed to run their 211 on the findhelp (auntbertha) national
# network. Everything else stays UNKNOWN until its primary platform is verified.
_OVERRIDES: dict[str, tuple[PlatformType, str | None]] = {
    "AL": (PlatformType.UNKNOWN, "https://www.211connectsalabama.org/"),
    "AK": (PlatformType.UNKNOWN, "https://www.unitedwayanc.org/work/alaska-211"),
    "AZ": (PlatformType.UNKNOWN, "https://211arizona.org/"),
    "AR": (PlatformType.UNKNOWN, "https://arkansas211.org/"),
    "CA": (PlatformType.FINDHELP, "https://www.211california.org/"),
    "CO": (PlatformType.UNKNOWN, "https://www.211colorado.org/"),
    "CT": (PlatformType.UNKNOWN, "https://www.211ct.org/"),
    "DE": (PlatformType.UNKNOWN, "https://uwde.org/what-we-do/get-help/delaware-211/"),
    "DC": (PlatformType.UNKNOWN, "https://211warmline.dc.gov/"),
    "FL": (PlatformType.UNKNOWN, "https://informfl.org/florida-211/"),
    "GA": (PlatformType.UNKNOWN, "https://211online.unitedwayatlanta.org/"),
    "HI": (PlatformType.UNKNOWN, "https://www.auw.org/about/211-hawaii/"),
    "ID": (PlatformType.VISIONLINK, "https://211-idaho.communityos.org/"),
    "IL": (PlatformType.UNKNOWN, "https://211illinois.org/"),
    "IN": (PlatformType.VISIONLINK, "https://in211.communityos.org"),
    "IA": (PlatformType.UNKNOWN, "https://211iowa.org/"),
    "KS": (PlatformType.UNKNOWN, "https://211kansas-resources.sophia-app.com/"),
    "KY": (PlatformType.UNKNOWN, "https://unitedwayck.org/2-1-1/"),
    "LA": (PlatformType.UNKNOWN, "https://211la.org/resources"),
    "ME": (PlatformType.UNKNOWN, "https://211maine.org/"),
    "MD": (PlatformType.UNKNOWN, "https://211md.org/"),
    "MA": (PlatformType.UNKNOWN, "https://mass211.org/"),
    "MI": (PlatformType.UNKNOWN, "https://www.uwmich.org/michigan-211"),
    "MN": (PlatformType.UNKNOWN, "https://www.gtcuw.org/get-assistance/211-resource-helpline/"),
    "MS": (PlatformType.UNKNOWN, "https://www.myunitedway.com/211"),
    "MO": (PlatformType.UNKNOWN, "https://mo211.myresourcedirectory.com/"),
    "MT": (PlatformType.UNKNOWN, "https://montana211.org/"),
    "NE": (PlatformType.UNKNOWN, "https://uwm211.org/"),
    "NV": (PlatformType.UNKNOWN, "https://adsd.nv.gov/Programs/2-1-1/2-1-1/"),
    "NH": (PlatformType.UNKNOWN, "https://211nh.org/"),
    "NJ": (PlatformType.ICAROL, "https://www.nj.gov/njoem/plan/nj211assist.html"),
    "NM": (PlatformType.UNKNOWN, "https://uwncnm.org/211a-2/"),
    "NY": (PlatformType.UNKNOWN, "https://www.211newyork.org/"),
    "NC": (PlatformType.UNKNOWN, "https://www.unitedwaync.org/nc-211"),
    "ND": (PlatformType.UNKNOWN, "https://myfirstlink.org/"),
    "OH": (PlatformType.UNKNOWN, "https://www.211oh.org/"),
    "OK": (PlatformType.UNKNOWN, "https://211eok.org/211-oklahoma/"),
    "OR": (PlatformType.UNKNOWN, "https://www.211info.org/"),
    "PA": (PlatformType.UNKNOWN, "https://www.uwp.org/programs/pa211/"),
    "RI": (PlatformType.ICAROL, "https://www.unitedwayri.org/get-help/2-1-1/"),
    "SC": (PlatformType.UNKNOWN, "https://www.uwasc.org/sc211"),
    "SD": (PlatformType.UNKNOWN, "https://www.helplinecenter.org/"),
    "TN": (PlatformType.VISIONLINK, "https://easttn211.communityos.org/"),
    "TX": (PlatformType.FINDHELP, "https://www.211texas.org/"),
    "UT": (PlatformType.UNKNOWN, "https://211utah.org/"),
    "VT": (PlatformType.UNKNOWN, "https://vermont211.org/"),
    "VA": (PlatformType.UNKNOWN, "https://211virginia.org/"),
    "WA": (PlatformType.UNKNOWN, "https://wa211.org/"),
    "WV": (PlatformType.UNKNOWN, "https://bfa.wv.gov/page/west-virginia-211"),
    "WI": (PlatformType.VISIONLINK, "https://211wisconsin.communityos.org/"),
    "WY": (PlatformType.UNKNOWN, "https://wyoming211.org/"),
    # Territories: 211 is not operated as a US-state-style program here;
    # no standalone public 211 site found (2026-07-20).
    "PR": (PlatformType.UNKNOWN, None),
    "VI": (PlatformType.UNKNOWN, None),
    "GU": (PlatformType.UNKNOWN, None),
    "AS": (PlatformType.UNKNOWN, None),
    "MP": (PlatformType.UNKNOWN, None),
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
