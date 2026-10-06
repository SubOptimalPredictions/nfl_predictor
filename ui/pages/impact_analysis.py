"""Impact analysis page for the NFL season simulator."""

import os

import polars as pl
import streamlit as st

from ui.utils import get_base64_image, get_team_conferences


IMPACT_DATA_PATH = "data/impact_analysis_2026.csv"
REQUIRED_COLUMNS = {
    "Name",
    "Current Playoff Probability",
    "Playoff Probability After Next Game Win",
    "Playoff Probability After Next Game Loss",
    "Next Game Opponent",
    "Next Game Win Probability",
    "Next Game Loss Probability",
}


def load_impact_data(csv_path=IMPACT_DATA_PATH):
    """Load the precomputed 2026 impact analysis data."""
    if not os.path.isfile(csv_path):
        return None

    try:
        data = pl.read_csv(csv_path)
    except (OSError, pl.exceptions.PolarsError) as error:
        st.error(f"Error loading impact analysis data: {error}")
        return None

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        st.error(
            "Impact analysis data is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )
        return None

    return data


def render_impact_analysis_page():
    """Render each team's next-game and playoff-probability scenarios."""
    st.subheader("🎯 Playoff Impact Analysis")
    st.markdown(
        "Compare each team's chance to win its next game with its current "
        "playoff odds and the change if it wins or loses."
    )

    impact_data = load_impact_data()
    if impact_data is None:
        st.info(
            f"No usable impact analysis data found. "
            f"Expected `{IMPACT_DATA_PATH}` with the computed 2026 matchup data."
        )
        return

    team_conferences = get_team_conferences()
    known_teams = set(team_conferences)
    data_teams = set(impact_data["Name"].to_list())
    unknown_teams = sorted(data_teams - known_teams)
    if unknown_teams:
        st.warning(
            "These teams are not present in the team records and will be omitted: "
            + ", ".join(unknown_teams)
        )

    impact_data = impact_data.filter(pl.col("Name").is_in(known_teams))
    display_matchups(impact_data)


def _playoff_swing(row):
    """Return the playoff-probability swing between the team's outcomes."""
    return abs(
        row["Playoff Probability After Next Game Win"]
        - row["Playoff Probability After Next Game Loss"]
    )


def _display_team_heading(row):
    """Display a team's logo and name in the matchup header."""
    team = row["Name"]
    logo_data = get_base64_image(f"assets/{team}.png")
    if logo_data:
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:center;"
            f"gap:8px;margin-bottom:4px'>"
            f"<img src='data:image/png;base64,{logo_data}' "
            f"alt='{team} logo' style='width:32px;height:32px;object-fit:contain'>"
            f"<strong style='font-size:0.95rem'>{team}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='text-align:center'><strong>{team}</strong></div>",
            unsafe_allow_html=True,
        )


def _display_comparison_row(left_value, label, right_value):
    """Display a centered metric label between both teams' values."""
    left, middle, right = st.columns([1, 1.2, 1], gap="small")
    left.markdown(
        f"<div style='text-align:center;font-weight:700'>{left_value}</div>",
        unsafe_allow_html=True,
    )
    middle.markdown(
        f"<div style='text-align:center;font-size:0.7rem;color:gray'>{label}</div>",
        unsafe_allow_html=True,
    )
    right.markdown(
        f"<div style='text-align:center;font-weight:700'>{right_value}</div>",
        unsafe_allow_html=True,
    )


def _probability_with_delta(value, current):
    """Format a conditional playoff probability and its baseline change."""
    if value is None:
        return "—"
    delta = (value - current) * 100
    bubble_color = "#15803d" if delta >= 0 else "#b91c1c"
    bubble_background = "#dcfce7" if delta >= 0 else "#fee2e2"
    return (
        f"<strong>{value:.1%}</strong>"
        f"<br><span style='display:inline-block;margin-top:2px;padding:2px 7px;"
        f"border-radius:999px;background:{bubble_background};color:{bubble_color};"
        f"font-size:0.65rem;font-weight:700;line-height:1.2'>"
        f"{delta:+.1f} pp</span>"
    )


def display_matchups(data):
    """Display each matchup once, pairing team projections when available."""
    if data.is_empty():
        st.info("No matchup data available.")
        return

    rows = {row["Name"]: row for row in data.iter_rows(named=True)}
    matchups = []
    displayed_teams = set()
    for team, row in rows.items():
        if team in displayed_teams:
            continue

        opponent = row["Next Game Opponent"]
        opponent_row = rows.get(opponent)
        is_reciprocal = (
            opponent_row is not None
            and opponent_row["Next Game Opponent"] == team
        )
        paired_row = opponent_row if is_reciprocal else None
        displayed_teams.add(team)
        if paired_row is not None:
            displayed_teams.add(opponent)

        swing = _playoff_swing(row)
        if paired_row is not None:
            swing = max(swing, _playoff_swing(paired_row))
        matchups.append((swing, row, paired_row))

    matchups.sort(key=lambda matchup: matchup[0], reverse=True)
    st.caption(
        "Scenario changes are percentage-point shifts from current playoff odds. "
        "Matchups are combined when both teams list each other as their next game."
    )
    for start in range(0, len(matchups), 2):
        matchup_columns = st.columns(2, gap="medium")
        for column, (_, row, paired_row) in zip(
            matchup_columns, matchups[start : start + 2]
        ):
            team = row["Name"]
            opponent = row["Next Game Opponent"]
            with column:
                with st.container(border=True, key=f"impact-card-{team}"):
                    left, center, right = st.columns([1, 0.35, 1], gap="small")
                    with left:
                        _display_team_heading(row)
                    with center:
                        st.markdown(
                            "<div style='text-align:center;font-size:0.7rem;"
                            "padding-top:8px'>MATCHUP</div>",
                            unsafe_allow_html=True,
                        )
                    with right:
                        if paired_row is not None:
                            _display_team_heading(paired_row)
                        else:
                            opponent_logo = get_base64_image(f"assets/{opponent}.png")
                            if opponent_logo:
                                st.markdown(
                                    f"<div style='display:flex;align-items:center;"
                                    f"justify-content:center;gap:8px;margin-bottom:4px'>"
                                    f"<img src='data:image/png;base64,{opponent_logo}' "
                                    f"alt='{opponent} logo' "
                                    "style='width:32px;height:32px;object-fit:contain'>"
                                    f"<strong style='font-size:0.95rem'>{opponent}</strong>"
                                    "</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f"<div style='text-align:center'>"
                                    f"<strong>{opponent}</strong></div>",
                                    unsafe_allow_html=True,
                                )

                    opponent_current = (
                        paired_row["Current Playoff Probability"]
                        if paired_row is not None
                        else None
                    )
                    _display_comparison_row(
                        f"<strong>{row['Next Game Win Probability']:.1%}</strong>",
                        "Chance to win",
                        (
                            f"<strong>{paired_row['Next Game Win Probability']:.1%}</strong>"
                            if paired_row is not None
                            else (
                                "<strong>"
                                f"{row['Next Game Loss Probability']:.1%}"
                                "</strong>"
                            )
                        ),
                    )
                    _display_comparison_row(
                        f"<strong>{row['Current Playoff Probability']:.1%}</strong>",
                        "Current playoff chance",
                        (
                            f"<strong>{opponent_current:.1%}</strong>"
                            if opponent_current is not None
                            else "—"
                        ),
                    )
                    _display_comparison_row(
                        _probability_with_delta(
                            row["Playoff Probability After Next Game Win"],
                            row["Current Playoff Probability"],
                        ),
                        "Playoff chance if they win",
                        (
                            _probability_with_delta(
                                paired_row[
                                    "Playoff Probability After Next Game Win"
                                ],
                                opponent_current,
                            )
                            if paired_row is not None
                            else "—"
                        ),
                    )
                    _display_comparison_row(
                        _probability_with_delta(
                            row["Playoff Probability After Next Game Loss"],
                            row["Current Playoff Probability"],
                        ),
                        "Playoff chance if they lose",
                        (
                            _probability_with_delta(
                                paired_row[
                                    "Playoff Probability After Next Game Loss"
                                ],
                                opponent_current,
                            )
                            if paired_row is not None
                            else "—"
                        ),
                    )
                    if paired_row is None:
                        st.caption(
                            "Opponent playoff projections are not paired in the CSV."
                        )
