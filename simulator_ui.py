import streamlit as st
import polars as pl
import numpy as np
import time
from simulator import get_aggregator_dict, parallel_simulatation, simulate
from team import Team

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
    "Number of Simulations", min_value=10, max_value=100000, value=1000, step=100
)
batch_size = st.sidebar.number_input(
    "Batch Size (per process)", min_value=10, max_value=10000, value=100, step=10
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

        st.success(
            f"✅ Simulation Complete! Ran {num_times_run} successful iterations in {elapsed_time:.2f} seconds ({num_times_run/elapsed_time:.1f} iterations/sec)"
        )
    except Exception as e:
        st.error(f"❌ Simulation failed: {str(e)}")
        st.stop()

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
        st.bar_chart(
            data=nfc_df,
            x="Team",
            y="Playoff %",
            color="#013369",
            use_container_width=True,
            height=400,
        )

        # "Seed" is column 0, "Team" is column 1
        top_nfc_team = nfc_df["Team"][0]
        st.metric("Top NFC Team", top_nfc_team)
        
        nfc_1st_counts = aggregator.get(top_nfc_team, [])
        nfc_1st_prob = (nfc_1st_counts[0] / num_times_run * 100) if num_times_run > 0 and len(nfc_1st_counts) > 0 else 0.0
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
        st.bar_chart(
            data=afc_df,
            x="Team",
            y="Playoff %",
            color="#D50A0A",
            use_container_width=True,
            height=400,
        )

        # "Seed" is column 0, "Team" is column 1
        top_afc_team = afc_df["Team"][0]
        st.metric("Top AFC Team", top_afc_team)

        afc_1st_counts = aggregator.get(top_afc_team, [])
        afc_1st_prob = (afc_1st_counts[0] / num_times_run * 100) if num_times_run > 0 and len(afc_1st_counts) > 0 else 0.0
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
    nfc_teams = sorted(
        [
            (team, count)
            for team, count in aggregator.items()
            if team_conferences.get(team) == "NFC"
        ],
        key=lambda x: calculate_playoff_probability(x[1], num_times_run),
        reverse=True,
    )
    for team, finishing_pos_count in nfc_teams:
        playoff_prob = (
            calculate_playoff_probability(finishing_pos_count, num_times_run) * 100
        )
        division_winner_prob = (
            calculate_division_winner_probability(finishing_pos_count, num_times_run)
            * 100
        )
        st.write(
            f"**{team}**: {playoff_prob:.1f}% playoff chance | {division_winner_prob:.1f}% division winner chance"
        )

        dist = (
            finishing_pos_count / num_times_run
            if num_times_run > 0
            else finishing_pos_count
        )
        positions = {
            f"#{i+1}": f"{val:.1%}" for i, val in enumerate(dist) if val > 0.01
        }
        if positions:
            st.caption(f"Position distribution: {positions}")

    st.subheader("📊 AFC Final Ranking Distribution")
    afc_teams = sorted(
        [
            (team, count)
            for team, count in aggregator.items()
            if team_conferences.get(team) == "AFC"
        ],
        key=lambda x: calculate_playoff_probability(x[1], num_times_run),
        reverse=True,
    )
    for team, finishing_pos_count in afc_teams:
        playoff_prob = (
            calculate_playoff_probability(finishing_pos_count, num_times_run) * 100
        )
        division_winner_prob = (
            calculate_division_winner_probability(finishing_pos_count, num_times_run)
            * 100
        )
        st.write(
            f"**{team}**: {playoff_prob:.1f}% playoff chance | {division_winner_prob:.1f}% division winner chance"
        )

        dist = (
            finishing_pos_count / num_times_run
            if num_times_run > 0
            else finishing_pos_count
        )
        positions = {
            f"#{i+1}": f"{val:.1%}" for i, val in enumerate(dist) if val > 0.01
        }
        if positions:
            st.caption(f"Position distribution: {positions}")

else:
    st.info("👈 Configure settings and click 'Start Simulation' to begin")
