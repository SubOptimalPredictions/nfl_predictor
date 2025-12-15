import streamlit as st
import polars as pl
import numpy as np
import time
import altair as alt
from simulator import get_aggregator_dict, parallel_simulatation, simulate
from team import Team
from team_colors import TEAM_COLORS

st.set_page_config(page_title="NFL Season Simulator", layout="wide")
st.title("🏈 NFL Season Simulator - Live Rankings")


def calculate_playoff_probability(finishing_pos_count, num_times_run):
    """Calculate probability of making playoffs (top 7)"""
    if num_times_run == 0:
        return 0.0
    return np.sum(finishing_pos_count[:7]) / num_times_run


def calculate_division_winner_probability(finishing_pos_count, num_times_run):
    """Calculate probability of winning division (top 4)"""
    if num_times_run == 0:
        return 0.0
    return np.sum(finishing_pos_count[:4]) / num_times_run


def get_team_conferences():
    """Load teams and return a dict mapping team abbreviation to conference"""
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    return {team.abbreviation: team.conference for _, team in teams.items()}


def get_team_divisions():
    """Load teams and return a dict mapping team abbreviation to division"""
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    return {team.abbreviation: team.division for _, team in teams.items()}


def render_division_filter(conference, key_prefix):
    st.write(f"**Filter by Division ({conference})**")
    cols = st.columns(5)
    
    # "All" checkbox
    is_all = cols[0].checkbox("All", value=True, key=f"{key_prefix}_all")
    
    divisions = ["North", "South", "East", "West"]
    selected_divisions = []
    
    if is_all:
        selected_divisions = divisions[:]
    
    for i, div in enumerate(divisions):
        # Render checkbox for each division
        # Disabled if "All" is checked
        checked = cols[i+1].checkbox(div, value=True, disabled=is_all, key=f"{key_prefix}_{div}")
        
        if not is_all and checked:
            selected_divisions.append(div)
            
    return selected_divisions


def get_projected_order(team_list, aggregator):
    """
    Determine the projected order of teams based on finish probabilities.
    Rank 1: Team most likely to finish 1st.
    Rank 2: Team most likely to finish 2nd (excluding rank 1 selection).
    ...
    """
    ordered_teams = []
    # Create a copy so we don't modify the original list if it's reused
    available_teams = set(team_list)
    num_positions = len(team_list)

    for i in range(num_positions):
        best_team = None
        max_count = -1

        for team in available_teams:
            # aggregator[team] is a list of counts for pos 1, pos 2, ...
            # We want the count for position i (0-indexed)
            counts = aggregator.get(team, [])
            count = counts[i] if i < len(counts) else 0

            if count > max_count:
                max_count = count
                best_team = team
            elif count == max_count:
                # Tie-breaker: alphabetical to be deterministic
                if best_team is None or team < best_team:
                    best_team = team

        if best_team:
            ordered_teams.append(best_team)
            available_teams.remove(best_team)
        else:
            # Fallback if something goes wrong (e.g. strict subset logic issues), take any
            if available_teams:
                remaining = sorted(list(available_teams))
                ordered_teams.extend(remaining)
                break

    return ordered_teams


# UI Setup
st.sidebar.header("Simulation Settings")

# Simulation parameters
num_iterations = st.sidebar.number_input(
    "Number of Simulations", min_value=10, max_value=10000, value=1000, step=100
)
batch_size = st.sidebar.number_input(
    "Batch Size (per process)", min_value=10, max_value=1000, value=100, step=10
)

if st.sidebar.button("▶️ Start Simulation", type="primary"):
    team_conferences = get_team_conferences()

    progress_bar = st.progress(0, text="Starting simulation...")
    start_time = time.time()

    try:
        aggregator, num_times_run = parallel_simulatation(
            num_iterations, batch_size, num_workers=None
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        progress_bar.progress(1.0, text="Simulation complete!")

        st.session_state.aggregator = aggregator
        st.session_state.num_times_run = num_times_run
        st.session_state.simulation_complete = True

        st.success(
            f"✅ Simulation Complete! Ran {num_times_run} successful iterations in {elapsed_time:.2f} seconds ({num_times_run/elapsed_time:.1f} iterations/sec)"
        )
    except Exception as e:
        st.error(f"❌ Simulation failed: {str(e)}")
        # Clear state on failure
        if "simulation_complete" in st.session_state:
            del st.session_state.simulation_complete
        st.stop()

if st.session_state.get("simulation_complete"):
    aggregator = st.session_state.aggregator
    num_times_run = st.session_state.num_times_run
    team_conferences = get_team_conferences()
    team_divisions = get_team_divisions()

    # Display results
    nfc_col, afc_col = st.columns(2)

    # Separate teams by conference
    nfc_data = []
    afc_data = []

    for team, finishing_pos_count in aggregator.items():
        playoff_prob = (
            calculate_playoff_probability(finishing_pos_count, num_times_run) * 100
        )
        division_winner_prob = (
            calculate_division_winner_probability(finishing_pos_count, num_times_run)
            * 100
        )
        first_seed_prob = (
            (finishing_pos_count[0] / num_times_run * 100)
            if num_times_run > 0 and len(finishing_pos_count) > 0
            else 0.0
        )

        team_data = {
            "Team": team,
            "Playoff %": playoff_prob,
            "Div Winner %": division_winner_prob,
            "1st Seed %": first_seed_prob,
        }

        if team_conferences.get(team) == "NFC":
            nfc_data.append(team_data)
        else:
            afc_data.append(team_data)

    # Sort data based on projected order
    nfc_teams_list = [d["Team"] for d in nfc_data]
    nfc_order = get_projected_order(nfc_teams_list, aggregator)
    nfc_order_map = {team: i for i, team in enumerate(nfc_order)}
    nfc_data.sort(key=lambda x: nfc_order_map.get(x["Team"], 999))

    afc_teams_list = [d["Team"] for d in afc_data]
    afc_order = get_projected_order(afc_teams_list, aggregator)
    afc_order_map = {team: i for i, team in enumerate(afc_order)}
    afc_data.sort(key=lambda x: afc_order_map.get(x["Team"], 999))

    # Create separate DataFrames for each conference
    nfc_df = pl.DataFrame(nfc_data).with_row_index("Predicted Seed", offset=1)
    afc_df = pl.DataFrame(afc_data).with_row_index("Predicted Seed", offset=1)

    # Display NFC results
    with nfc_col:
        st.subheader("🔵 NFC Conference")
        # Custom Altair chart for NFC Playoff Chances with restricted bounds
        nfc_playoff_chart = (
            alt.Chart(nfc_df)
            .mark_bar()
            .encode(
                x=alt.X("Team"),
                y=alt.Y("Playoff %", scale=alt.Scale(domain=[0, 100])),
                color=alt.value("#013369"),
                tooltip=["Team", alt.Tooltip("Playoff %", format=".1f")],
            )
            .properties(height=400)
            .interactive(bind_y=False)
        )
        st.altair_chart(nfc_playoff_chart, use_container_width=True)

        # "Seed" is column 0, "Team" is column 1
        top_nfc_team = nfc_df["Team"][0]
        st.metric("Top NFC Team", top_nfc_team)

        nfc_1st_counts = aggregator.get(top_nfc_team, [])
        nfc_1st_prob = (
            (nfc_1st_counts[0] / num_times_run * 100)
            if num_times_run > 0 and len(nfc_1st_counts) > 0
            else 0.0
        )
        st.metric("Top NFC 1st Seed Chance", f"{nfc_1st_prob:.1f}%")
        st.dataframe(
            nfc_df.select(
                ["Predicted Seed", "Team", "Playoff %", "Div Winner %", "1st Seed %"]
            ).with_columns(
                [
                    pl.col("Playoff %").round(1),
                    pl.col("Div Winner %").round(1),
                    pl.col("1st Seed %").round(1),
                ]
            ),
            column_config={
                "Predicted Seed": st.column_config.NumberColumn(width="small"),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
        )

    # Display AFC results
    with afc_col:
        st.subheader("🔴 AFC Conference")
        # Custom Altair chart for AFC Playoff Chances with restricted bounds
        afc_playoff_chart = (
            alt.Chart(afc_df)
            .mark_bar()
            .encode(
                x=alt.X("Team"),
                y=alt.Y("Playoff %", scale=alt.Scale(domain=[0, 100])),
                color=alt.value("#D50A0A"),
                tooltip=["Team", alt.Tooltip("Playoff %", format=".1f")],
            )
            .properties(height=400)
            .interactive(bind_y=False)
        )
        st.altair_chart(afc_playoff_chart, use_container_width=True)

        # "Seed" is column 0, "Team" is column 1
        top_afc_team = afc_df["Team"][0]
        st.metric("Top AFC Team", top_afc_team)

        afc_1st_counts = aggregator.get(top_afc_team, [])
        afc_1st_prob = (
            (afc_1st_counts[0] / num_times_run * 100)
            if num_times_run > 0 and len(afc_1st_counts) > 0
            else 0.0
        )
        st.metric("Top AFC 1st Seed Chance", f"{afc_1st_prob:.1f}%")
        st.dataframe(
            afc_df.select(
                ["Predicted Seed", "Team", "Playoff %", "Div Winner %", "1st Seed %"]
            ).with_columns(
                [
                    pl.col("Playoff %").round(1),
                    pl.col("Div Winner %").round(1),
                    pl.col("1st Seed %").round(1),
                ]
            ),
            column_config={
                "Predicted Seed": st.column_config.NumberColumn(width="small"),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
        )

    # Final detailed results by conference
    st.subheader("📊 NFC Final Ranking Distribution")

    # Graph for NFC
    st.write("### NFC Finish Probability Graph")
    nfc_team_names = sorted(
        [t for t in aggregator.keys() if team_conferences.get(t) == "NFC"]
    )
    
    # Division Filter (NFC) - Checkboxes
    nfc_divs_selected = render_division_filter("NFC", "nfc_div_filter_chk")
    
    nfc_defaults = [
        t for t in nfc_team_names 
        if team_divisions.get(t) in nfc_divs_selected
    ]
        
    nfc_selected_teams = st.multiselect(
        "Select NFC Teams to View", 
        nfc_team_names, 
        default=nfc_defaults,
        # Update key to force refresh when division selection changes
        key=f"nfc_multiselect_{tuple(sorted(nfc_divs_selected))}"
    )

    if nfc_selected_teams:
        nfc_graph_data = []
        for team in nfc_selected_teams:
            counts = aggregator.get(team, [])
            probs = [(c / num_times_run) for c in counts]
            # Ensure we have 16 positions padded with 0 if needed
            probs = probs + [0.0] * (16 - len(probs))
            probs = probs[:16]

            for rank, prob in enumerate(probs, 1):
                nfc_graph_data.append(
                    {"Team": team, "Position": rank, "Probability": prob}
                )

        nfc_chart_df = pl.DataFrame(nfc_graph_data)

        # Create Altair chart
        nfc_chart = (
            alt.Chart(nfc_chart_df)
            .mark_bar()
            .encode(
                x=alt.X("Position:O", title="Finishing Position"),
                y=alt.Y("Probability:Q", title="Probability", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color(
                    "Team:N",
                    scale=alt.Scale(
                        domain=list(nfc_selected_teams),
                        range=[
                            TEAM_COLORS.get(t, "#000000") for t in nfc_selected_teams
                        ],
                    ),
                    legend=alt.Legend(title="Team"),
                ),
                xOffset="Team:N",
                tooltip=["Team", "Position", alt.Tooltip("Probability", format=".1%")],
            )
            .properties(height=500)
            .interactive(bind_y=False)
        )
        st.altair_chart(nfc_chart, use_container_width=True)

    st.subheader("📊 AFC Final Ranking Distribution")

    # Graph for AFC
    st.write("### AFC Finish Probability Graph")
    afc_team_names = sorted(
        [t for t in aggregator.keys() if team_conferences.get(t) == "AFC"]
    )
    
    # Division Filter (AFC) - Checkboxes
    afc_divs_selected = render_division_filter("AFC", "afc_div_filter_chk")
    
    afc_defaults = [
        t for t in afc_team_names 
        if team_divisions.get(t) in afc_divs_selected
    ]

    afc_selected_teams = st.multiselect(
        "Select AFC Teams to View", 
        afc_team_names, 
        default=afc_defaults,
        key=f"afc_multiselect_{tuple(sorted(afc_divs_selected))}"
    )

    if afc_selected_teams:
        afc_graph_data = []
        for team in afc_selected_teams:
            counts = aggregator.get(team, [])
            probs = [(c / num_times_run) for c in counts]
            # Ensure we have 16 positions padded with 0 if needed
            probs = probs + [0.0] * (16 - len(probs))
            probs = probs[:16]

            for rank, prob in enumerate(probs, 1):
                afc_graph_data.append(
                    {"Team": team, "Position": rank, "Probability": prob}
                )

        afc_chart_df = pl.DataFrame(afc_graph_data)

        # Create Altair chart
        afc_chart = (
            alt.Chart(afc_chart_df)
            .mark_bar()
            .encode(
                x=alt.X("Position:O", title="Finishing Position"),
                y=alt.Y("Probability:Q", title="Probability", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color(
                    "Team:N",
                    scale=alt.Scale(
                        domain=list(afc_selected_teams),
                        range=[
                            TEAM_COLORS.get(t, "#000000") for t in afc_selected_teams
                        ],
                    ),
                    legend=alt.Legend(title="Team"),
                ),
                xOffset="Team:N",
                tooltip=["Team", "Position", alt.Tooltip("Probability", format=".1%")],
            )
            .properties(height=500)
            .interactive(bind_y=False)
        )
        st.altair_chart(afc_chart, use_container_width=True)

else:
    if not st.session_state.get("simulation_complete"):
        st.info("👈 Configure settings and click 'Start Simulation' to begin")
