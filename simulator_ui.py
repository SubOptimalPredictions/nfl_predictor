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
        avg_finish = np.sum(
            [pos * count for pos, count in enumerate(finishing_pos_count, 1)]
        ) / max(num_times_run, 1)

        team_data = {
            "Team": team,
            "Playoff %": playoff_prob,
            "Div Winner %": division_winner_prob,
            "Avg Finish": avg_finish,
        }

        if team_conferences.get(team) == "NFC":
            nfc_data.append(team_data)
        else:
            afc_data.append(team_data)

    # Create separate DataFrames for each conference
    nfc_df = pl.DataFrame(nfc_data).sort("Playoff %", descending=True)
    afc_df = pl.DataFrame(afc_data).sort("Playoff %", descending=True)

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

        st.metric("Top NFC Team", nfc_df.row(0)[0])
        st.metric("Top NFC Playoff %", f"{nfc_df.row(0)[1]:.1f}%")
        st.dataframe(
            nfc_df.select(
                ["Team", "Playoff %", "Div Winner %", "Avg Finish"]
            ).with_columns(
                [
                    pl.col("Playoff %").round(1),
                    pl.col("Div Winner %").round(1),
                    pl.col("Avg Finish").round(2),
                ]
            ),
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

        st.metric("Top AFC Team", afc_df.row(0)[0])
        st.metric("Top AFC Playoff %", f"{afc_df.row(0)[1]:.1f}%")
        st.dataframe(
            afc_df.select(
                ["Team", "Playoff %", "Div Winner %", "Avg Finish"]
            ).with_columns(
                [
                    pl.col("Playoff %").round(1),
                    pl.col("Div Winner %").round(1),
                    pl.col("Avg Finish").round(2),
                ]
            ),
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
