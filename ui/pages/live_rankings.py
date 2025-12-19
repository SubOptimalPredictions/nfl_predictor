"""
Live Rankings page for NFL Season Simulator
"""
import streamlit as st
import polars as pl
import time
import altair as alt
import textwrap
from simulator import parallel_simulatation
from team_colors import TEAM_COLORS
from simulator import Simulator
import numpy as np
from ui.utils import (
    get_base64_image,
    calculate_playoff_probability,
    calculate_division_winner_probability,
    get_team_conferences,
    get_team_divisions,
    render_division_filter,
    render_html_ranking_table,
    get_projected_order
)
from utils import update_schedule


def render_live_rankings_page():
    st.sidebar.header("Simulation Settings")

    # Simulation parameters
    num_iterations = st.sidebar.number_input(
        "Number of Simulations", min_value=10, max_value=10000, value=1000, step=100
    )
    batch_size = st.sidebar.number_input(
        "Batch Size (per process)", min_value=10, max_value=1000, value=100, step=10
    )

    # Show any user-selected picks from the Schedule page, grouped by week
    if st.session_state.get("user_picks"):
        try:
            df_schedule = pl.read_csv("data/schedules_2025.csv")
            picks = st.session_state.user_picks

            # Build mapping week -> list of picks
            picks_by_week = {}
            # Iterate schedule rows and match against user_picks keys
            for row in df_schedule.iter_rows(named=True):
                game_id = row["away_team"] + "-" + row["home_team"]
                if game_id in picks:
                    away_score = row.get("away_score")
                    home_score = row.get("home_score")
                    is_played = away_score is not None and home_score is not None
                    # Only show picks for unplayed games
                    if is_played:
                        continue

                    week = row.get("week")
                    selected_team = picks.get(game_id)

                    picks_by_week.setdefault(week, []).append(
                        {
                            "game_id": game_id,
                            "away": row.get("away_team"),
                            "home": row.get("home_team"),
                            "selected": selected_team,
                        }
                    )

            if picks_by_week:
                # Header with optional Unselect All button
                header_cols = st.columns([0.9, 0.1])
                with header_cols[0]:
                    st.subheader("✅ Selected Game Picks (by Week)")
                with header_cols[1]:
                    if st.button("Unselect All", key="unselect_all_picks"):
                        st.session_state.user_picks = {}
                        st.rerun()

                # Sort weeks numerically if possible
                for week in sorted(picks_by_week.keys(), key=lambda w: int(w) if str(w).isdigit() else str(w)):
                    st.markdown(f"**Week {week}**")
                    for pick in picks_by_week[week]:
                        # Columns: away logo, home logo, matchup text, selected indicator
                        pick_cols = st.columns([0.12, 0.12, 0.56, 0.2])
                        away_logo = get_base64_image(f"assets/{pick['away']}.png")
                        home_logo = get_base64_image(f"assets/{pick['home']}.png")

                        # Away logo
                        with pick_cols[0]:
                            if away_logo:
                                st.image(f"data:image/png;base64,{away_logo}", width=40)
                            else:
                                st.image(f"assets/{pick['away']}.png", width=40)

                        # Home logo
                        with pick_cols[1]:
                            if home_logo:
                                st.image(f"data:image/png;base64,{home_logo}", width=40)
                            else:
                                st.image(f"assets/{pick['home']}.png", width=40)

                        # Matchup text with selected team highlighted
                        with pick_cols[2]:
                            away = pick['away']
                            home = pick['home']
                            selected = pick['selected']
                            # Bold the selected team in the matchup
                            if selected == away:
                                md = f"- **{away}** @ {home} — **Selected: {away}**"
                            elif selected == home:
                                md = f"- {away} @ **{home}** — **Selected: {home}**"
                            else:
                                md = f"- {away} @ {home} — **Selected: {selected}**"
                            st.markdown(md)

                        # Right: selected team's logo (if available)
                        with pick_cols[3]:
                            sel_logo = get_base64_image(f"assets/{pick['selected']}.png")
                            if sel_logo:
                                st.image(f"data:image/png;base64,{sel_logo}", width=40)
                            else:
                                st.image(f"assets/{pick['selected']}.png", width=40)

                st.markdown("---")
        except Exception:
            # Fail silently if schedule can't be loaded or something unexpected happens
            pass

    # After handling/displaying current picks, independently detect out-of-date simulations
    if st.session_state.get("simulation_complete"):
        last_picks = st.session_state.get("last_simulation_picks", {}) or {}
        curr_picks = st.session_state.get("user_picks", {}) or {}

        if last_picks != curr_picks:
            # Compute diffs
            added = [g for g in curr_picks.keys() if g not in last_picks.keys()]
            removed = [g for g in last_picks.keys() if g not in curr_picks.keys()]
            changed = [g for g in curr_picks.keys() if g in last_picks.keys() and curr_picks[g] != last_picks[g]]

            # Load schedule to render readable game info
            try:
                df_schedule = pl.read_csv("data/schedules_2025.csv")
                game_map = {}
                for r in df_schedule.iter_rows(named=True):
                    gid = r["away_team"] + "-" + r["home_team"]
                    game_map[gid] = f"{r.get('away_team')} @ {r.get('home_team')} (Week {r.get('week')})"
            except Exception:
                game_map = {}

            st.warning("Out of date simulation: your current picks differ from those used for the last simulation.")

            if added:
                st.markdown("**Added picks:**")
                for g in added:
                    label = game_map.get(g, g)
                    st.markdown(f"- {label} — **Selected: {curr_picks.get(g)}**")

            if removed:
                st.markdown("**Removed picks:**")
                for g in removed:
                    label = game_map.get(g, g)
                    st.markdown(f"- {label} — previously selected: **{last_picks.get(g)}**")

            if changed:
                st.markdown("**Changed picks:**")
                for g in changed:
                    label = game_map.get(g, g)
                    st.markdown(f"- {label} — was **{last_picks.get(g)}**, now **{curr_picks.get(g)}**")

            # Action: clear previous simulation results
            if st.button("Clear previous simulation results", key="clear_sim_results"):
                for k in ["simulation_complete", "aggregator", "num_times_run", "last_simulation_picks", "last_simulation_at"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.success("Previous simulation results cleared. Please re-run the simulation.")
                st.rerun()

    # Prevent starting another simulation while one is already running
    if "simulation_running" not in st.session_state:
        st.session_state.simulation_running = False

    start_disabled = bool(st.session_state.get("simulation_running", False))
    if start_disabled:
        st.sidebar.info("Simulation running... Please wait until it completes.")
    if st.sidebar.button("▶️ Start Simulation", type="primary", disabled=start_disabled):
        # Mark that a simulation is in progress so the button is disabled on reruns
        st.session_state.simulation_running = True
        update_schedule('data/schedules_2025.csv')
        team_conferences = get_team_conferences()
        

        progress_bar = st.progress(0, text="Starting simulation...")
        start_time = time.time()

        try:
            print(st.session_state.user_picks)
            sim = Simulator()
            for game in st.session_state.user_picks:
                
            
                game_obj = sim.base_season.lookup_game(game)
                winning_team = st.session_state.user_picks[game]
                print(game, winning_team)
                if winning_team == game_obj.get_home_team().abbreviation:
                    modified_probs = np.array([0.0, 1.0])
                elif winning_team == game_obj.get_away_team().abbreviation:
                    modified_probs = np.array([1.0, 0.0])
                sim.modify_game_probabilities(game_obj, modified_probs)
            
            aggregator, num_times_run = sim.simulate(num_iterations=1000)
            end_time = time.time()
            elapsed_time = end_time - start_time
            progress_bar.progress(1.0, text="Simulation complete!")

            st.session_state.aggregator = aggregator
            st.session_state.num_times_run = num_times_run
            st.session_state.simulation_complete = True
            # Record the picks that were used for this simulation so we can detect changes later
            st.session_state.last_simulation_picks = dict(st.session_state.get("user_picks", {}) or {})
            st.session_state.last_simulation_at = time.time()
            # Clear running flag before rerunning so UI enables the Start button
            st.session_state.simulation_running = False
            # Re-run to refresh UI so warning about out-of-date picks clears immediately
            st.rerun()

            st.success(
                f"✅ Simulation Complete! Ran {num_times_run} successful iterations in {elapsed_time:.2f} seconds ({num_times_run/elapsed_time:.1f} iterations/sec)"
            )
        except Exception as e:
            st.error(f"❌ Simulation failed: {str(e)}")
            # Ensure we clear running flag on failure so the button becomes available
            st.session_state.simulation_running = False
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

            # Prepare logo data URL for st.column_config.ImageColumn
            img_path = f"assets/{team}.png"
            b64_img = get_base64_image(img_path)
            logo_url = f"data:image/png;base64,{b64_img}" if b64_img else ""

            team_data = {
                "Team": team,
                "Logo": logo_url,
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
            # Load NFC Logo
            nfc_logo_b64 = get_base64_image("assets/NFC.png")
            if nfc_logo_b64:
                 st.markdown(textwrap.dedent(
                    f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{nfc_logo_b64}" style="height: 50px;">
                        <h3 style="margin: 0;">NFC Conference</h3>
                    </div>
                    """),
                    unsafe_allow_html=True
                )
            else:
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
            
            img_path = f"assets/{top_nfc_team}.png"
            img_base64 = get_base64_image(img_path)
            
            logo_html = ""
            if img_base64:
                logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 50px; margin-left: 20px; vertical-align: middle; pointer-events: none;">'
                
            st.markdown(textwrap.dedent(
                f"""
                <div style="margin-bottom: 10px;">
                    <p style="font-size: 14px; margin-bottom: 0px; color: rgb(120, 120, 120);">Top NFC Team</p>
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 32px; font-weight: 600;">{top_nfc_team}</span>
                        {logo_html}
                    </div>
                </div>
                """),
                unsafe_allow_html=True
            )

            nfc_1st_counts = aggregator.get(top_nfc_team, [])
            nfc_1st_prob = (
                (nfc_1st_counts[0] / num_times_run * 100)
                if num_times_run > 0 and len(nfc_1st_counts) > 0
                else 0.0
            )
            st.metric("Top NFC 1st Seed Chance", f"{nfc_1st_prob:.1f}%")
            
            # Render Custom HTML Table
            render_html_ranking_table(nfc_df, "#013369", "nfc")

        # Display AFC results
        with afc_col:
            # Load AFC Logo
            afc_logo_b64 = get_base64_image("assets/AFC.png")
            if afc_logo_b64:
                 st.markdown(textwrap.dedent(
                    f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <img src="data:image/png;base64,{afc_logo_b64}" style="height: 50px;">
                        <h3 style="margin: 0;">AFC Conference</h3>
                    </div>
                    """),
                    unsafe_allow_html=True
                )
            else:
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
            
            img_path = f"assests/{top_afc_team}.png"
            img_base64 = get_base64_image(img_path)
            
            logo_html = ""
            if img_base64:
                logo_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 50px; margin-left: 20px; vertical-align: middle; pointer-events: none;">'
                
            st.markdown(textwrap.dedent(
                f"""
                <div style="margin-bottom: 10px;">
                    <p style="font-size: 14px; margin-bottom: 0px; color: rgb(120, 120, 120);">Top AFC Team</p>
                    <div style="display: flex; align-items: center;">
                        <span style="font-size: 32px; font-weight: 600;">{top_afc_team}</span>
                        {logo_html}
                    </div>
                </div>
                """),
                unsafe_allow_html=True
            )

            afc_1st_counts = aggregator.get(top_afc_team, [])
            afc_1st_prob = (
                (afc_1st_counts[0] / num_times_run * 100)
                if num_times_run > 0 and len(afc_1st_counts) > 0
                else 0.0
            )
            st.metric("Top AFC 1st Seed Chance", f"{afc_1st_prob:.1f}%")
            
            # Render Custom HTML Table
            render_html_ranking_table(afc_df, "#D50A0A", "afc")

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
