"""Team name to abbreviation mapping.

Provides a canonical mapping from full team name to its common 2-3 letter
abbreviation used across the project.

Example:
    TEAM_NAME_TO_ABBR["Kansas City Chiefs"] == "KC"
"""
from __future__ import annotations

from typing import Dict

# Generated from data/teams.csv
TEAM_NAME_TO_ABBR: Dict[str, str] = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Las Vegas Raiders": "LV",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "Los Angeles Chargers": "LAC",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Los Angeles Rams": "LA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}


def get_abbreviation(team_name: str) -> str | None:
    """Return the abbreviation for a team name or None if unknown.

    The lookup is exact by default; callers should pass the full team name as
    provided in `data/teams.csv`. This helper exists to centralize access and
    allow future normalization logic (aliases, case-insensitive lookup, etc.).
    """
    if team_name is None:
        return None
    return TEAM_NAME_TO_ABBR.get(team_name)
