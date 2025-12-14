import streamlit as st
import polars as pl
import numpy as np
import time
from simulator import (
    get_aggregator_dict,
    aggregate_final_ranking,
    simulate_single_season,
)

st.set_page_config(page_title="NFL Season Simulator", layout="wide")
st.title("🏈 NFL Season Simulator - Live Rankings")


def calculate_playoff_probability(finishing_pos_count, num_times_run):
    """Calculate probability of making playoffs (top 7)"""
    if num_times_run == 0:
        return 0.0
    return np.sum(finishing_pos_count[:7]) / num_times_run


# UI Setup
col1, col2 = st.columns([2, 1])
chart_holder = col1.empty()
stats_holder = col2.empty()
progress_holder = st.empty()

# Simulation parameters
num_iterations = st.sidebar.number_input(
    "Number of Simulations", min_value=10, max_value=10000, value=100, step=10
)
update_frequency = st.sidebar.slider(
    "Update Every N Iterations", min_value=1, max_value=50, value=1
)
animation_speed = st.sidebar.slider(
    "Animation Speed (seconds)", min_value=0.0, max_value=0.5, value=0.05, step=0.01
)

if st.sidebar.button("▶️ Start Simulation", type="primary"):
    aggregator = get_aggregator_dict()
    num_times_run = 0

    progress_bar = progress_holder.progress(0)

    for i in range(num_iterations):
        try:
            nfc_ranking, afc_ranking = simulate_single_season()
            aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking)
            num_times_run += 1

            # Update UI every N iterations
            if i % update_frequency == 0 or i == num_iterations - 1:
                # Calculate playoff probabilities for each team
                teams_data = []
                for team, finishing_pos_count in aggregator.items():
                    playoff_prob = (
                        calculate_playoff_probability(
                            finishing_pos_count, num_times_run
                        )
                        * 100
                    )
                    avg_finish = np.sum(
                        [
                            pos * count
                            for pos, count in enumerate(finishing_pos_count, 1)
                        ]
                    ) / max(num_times_run, 1)
                    teams_data.append(
                        {
                            "Team": team,
                            "Playoff %": playoff_prob,
                            "Avg Finish": avg_finish,
                        }
                    )

                # Create Polars DataFrame and sort by playoff probability
                df = pl.DataFrame(teams_data).sort("Playoff %", descending=True)

                # Update chart
                with chart_holder.container():
                    st.bar_chart(
                        data=df,
                        x="Team",
                        y="Playoff %",
                        color="#1f77b4",
                        use_container_width=True,
                        height=500,
                    )

                # Update stats table
                with stats_holder.container():
                    st.metric("Simulations", f"{num_times_run}/{num_iterations}")
                    st.metric("Top Team", df.row(0)[0])
                    st.metric("Top Team Playoff %", f"{df.row(0)[1]:.1f}%")
                    st.divider()
                    st.dataframe(
                        df.select(["Team", "Playoff %", "Avg Finish"]).with_columns(
                            [
                                pl.col("Playoff %").round(1),
                                pl.col("Avg Finish").round(2),
                            ]
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )

                # Update progress bar
                progress_bar.progress((i + 1) / num_iterations)

                # Animation delay
                if animation_speed > 0:
                    time.sleep(animation_speed)

        except NotImplementedError:
            pass

    st.success(f"✅ Simulation Complete! Ran {num_times_run} successful iterations.")

    # Final detailed results
    st.subheader("📊 Final Ranking Distribution")
    for team, finishing_pos_count in sorted(
        aggregator.items(),
        key=lambda x: calculate_playoff_probability(x[1], num_times_run),
        reverse=True,
    ):
        playoff_prob = (
            calculate_playoff_probability(finishing_pos_count, num_times_run) * 100
        )
        st.write(f"**{team}**: {playoff_prob:.1f}% playoff chance")

        # Show distribution across positions
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
