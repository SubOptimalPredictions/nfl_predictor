import streamlit as st
import polars as pl
import time
import random

st.set_page_config(page_title="NFL Predictor", layout="centered")
st.title("🏈 NFL Playoff Predictor (Polars Edition)")

# 1. Setup Data
teams = [
    "Chiefs",
    "Eagles",
    "49ers",
    "Bills",
    "Bengals",
    "Lions",
    "Dolphins",
    "Cowboys",
]
# We keep the running state in a standard Python dict for max speed during updates
team_wins = {team: 0 for team in teams}

# UI Placeholders
chart_holder = st.empty()
stats_holder = st.empty()

# 2. Simulation Loop
# In a real scenario, this loop would be receiving results from your multiprocessing pool
total_sims = 100

for i in range(1, total_sims + 1):
    # --- Simulate a Game/Season ---
    winner = random.choice(teams)
    team_wins[winner] += 1

    # --- Polars Data Handling ---
    # Create a DataFrame from the current state
    # Polars is very fast at creating frames, so doing this in a loop is fine for UI updates
    df = pl.DataFrame(
        {"Team": list(team_wins.keys()), "Wins": list(team_wins.values())}
    )

    # Sort by Wins (descending) to create the "leaderboard shuffling" effect
    df = df.sort("Wins", descending=True)

    # --- Render ---
    # We update the chart every iteration (or every N iterations for speed)
    with chart_holder.container():
        # st.bar_chart handles Polars frames natively
        st.bar_chart(
            data=df,
            x="Team",
            y="Wins",
            color="#FF4B4B",  # Optional: Streamlit brand color
            use_container_width=True,
        )

    # Update text stats
    top_team = df.row(0)[0]  # Get the name of the team in the first row
    stats_holder.markdown(
        f"**Simulations:** `{i}/{total_sims}` | **Current Leader:** `{top_team}`"
    )

    # Control animation speed
    time.sleep(0.05)

st.success("Prediction Run Complete!")
