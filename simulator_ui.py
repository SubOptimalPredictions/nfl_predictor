import streamlit as st
import streamlit.components.v1 as components
import polars as pl
import numpy as np
import time
import altair as alt
import base64
import os
import textwrap
from simulator import get_aggregator_dict, parallel_simulatation, simulate
from team import Team
from team_colors import TEAM_COLORS

st.set_page_config(page_title="NFL Season Simulator", page_icon=":football:", layout="wide")
st.title("🏈 NFL Season Simulator - Live Rankings")


def get_base64_image(image_path):
    """
    Load image with robust path handling (case-insensitive folder/file, fallback to 'assets').
    """
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

    # Handle path variations for deployment (Case sensitivity, Folder typo)
    folder, filename = os.path.split(image_path)
    
    # Check for folder existence or case-insensitive match
    search_folders = [folder]
    if folder == "assests":
        search_folders.append("assets")  # Fix common typo
    
    found_folder = None
    # Look for the folder in current directory
    try:
        current_ls = os.listdir(".")
        for f in search_folders:
            # direct match
            if f in current_ls:
                found_folder = f
                break
            # case insensitive match
            for existing_dir in current_ls:
                if existing_dir.lower() == f.lower():
                    found_folder = existing_dir
                    break
            if found_folder: break
    except Exception:
        pass
        
    if not found_folder:
        return ""

    # Look for file in the found folder (case-insensitive)
    try:
        files = os.listdir(found_folder)
        for f in files:
            if f.lower() == filename.lower():
                full_path = os.path.join(found_folder, f)
                with open(full_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
    except Exception:
        pass
        
    return ""


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


def render_html_ranking_table(df, color, conference_id):
    """
    Render a custom HTML table for rankings with merged Logo+Team column.
    """
    # Unique class for this conference to handle specific border colors if needed, 
    # though we use inline styles for the variable color.
    table_class = f"ranking-table-{conference_id}"
    
    # CSS with sticky header support and dark/light mode friendly borders
    style_block = textwrap.dedent(f"""
    <style>
        .{table_class} {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 14px;
            font-family: sans-serif;
        }}
        .{table_class} th {{
            text-align: left;
            padding: 8px 12px;
            color: gray;
            font-weight: 500;
            background-color: var(--background-color, var(--primary-background-color, canvas));
            position: sticky;
            top: 0;
            z-index: 50;
        }}
        .{table_class} th::after {{
            content: "";
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            height: 4px;
            background-color: {color};
        }}
        .{table_class} td {{
            padding: 8px 12px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            vertical-align: middle;
        }}
        .{table_class} tr:last-child td {{
            border-bottom: none;
        }}
        .{table_class} .team-cell {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .{table_class} .team-logo {{
            width: 24px;
            height: 24px;
            object-fit: contain;
        }}
        .{table_class} .stat-cell {{
            text-align: right;
            font-variant-numeric: tabular-nums; 
        }}
        .{table_class} .rank-cell {{
            color: gray;
            width: 40px;
            text-align: center;
        }}
    </style>
    """)

    rows_html = ""
    for row in df.iter_rows(named=True):
        seed = row["Predicted Seed"]
        logo = row["Logo"]
        team = row["Team"]
        playoff = row["Playoff %"]
        div_win = row["Div Winner %"]
        seed1 = row["1st Seed %"]
        
        # Construct row with minimal/zero indentation
        row_html = f"""
<tr>
<td class="rank-cell">{seed}</td>
<td>
<div class="team-cell">
<img src="{logo}" class="team-logo">
<span style="font-weight: 600;">{team}</span>
</div>
</td>
<td class="stat-cell">{playoff:.1f}%</td>
<td class="stat-cell">{div_win:.1f}%</td>
<td class="stat-cell">{seed1:.1f}%</td>
</tr>"""
        rows_html += row_html

    # Assemble final table with zero indentation to avoid code block detection
    table_html = f"""
{style_block}
<div style="max-height: 500px; overflow-y: auto; margin-top: 10px; border: 1px solid rgba(128,128,128,0.2); border-radius: 8px;">
<table class="{table_class}">
<thead>
<tr>
<th class="rank-cell">Seed</th>
<th>Team</th>
<th style="text-align: right;">Playoff %</th>
<th style="text-align: right;">Div Win %</th>
<th style="text-align: right;">1st Seed %</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
"""
    
    st.markdown(table_html, unsafe_allow_html=True)


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


def render_schedule_page():
    # Initialize session state for user picks if not exists
    if "user_picks" not in st.session_state:
        st.session_state.user_picks = {}

    # Handle query params for picks
    query_params = st.query_params
    if "pick" in query_params:
        try:
            pick_data = query_params["pick"]
            if isinstance(pick_data, list):
                pick_data = pick_data[0]
            
            if ":" in pick_data:
                game_id_param, team_param = pick_data.split(":", 1)
                
                # Check if this team is already selected
                current_pick = st.session_state.user_picks.get(game_id_param)
                
                if current_pick == team_param:
                    # Deselect
                    del st.session_state.user_picks[game_id_param]
                else:
                    # Select or switch
                    st.session_state.user_picks[game_id_param] = team_param
                
                # Clear query params and rerun
                st.query_params.clear()
                st.rerun()
        except Exception:
            pass
            
    st.header("📅 NFL Season Schedule")
    
    # Load data
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    df_schedule = pl.read_csv("data/schedules_2025.csv")
    
    # Get sorted unique weeks
    weeks = df_schedule["week"].unique().sort()
    
    selected_week = st.selectbox("Select Week", weeks, index=0)
    
    # Filter for selected week
    week_games = df_schedule.filter(pl.col("week") == selected_week)
    
    st.markdown("---")
    
    # CSS for cards with pick styling and JavaScript for interaction
    st.markdown(textwrap.dedent("""
        <style>
        .game-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: var(--background-color, var(--primary-background-color, canvas));
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            text-align: center;
        }
        .game-header {
            font-size: 13px;
            color: gray;
            margin-bottom: 15px;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        .matchup-container {
            display: flex;
            justify-content: space-around;
            align-items: center;
            margin-bottom: 15px;
        }
        .team-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 45%;
        }
        .team-logo-large {
            width: 80px;
            height: 80px;
            object-fit: contain;
            margin-bottom: 10px;
            border-radius: 50%;
            border: 3px solid transparent;
            transition: all 0.2s ease;
        }
        .team-logo-large:hover {
            transform: scale(1.05);
            cursor: pointer;
        }
        .picked-team {
            border: 5px solid #6c757d !important;
            box-shadow: 0 0 20px rgba(108, 117, 125, 0.6) !important;
            background-color: rgba(108, 117, 125, 0.2) !important;
        }
        .team-name {
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 4px;
        }
        .score-val-large {
            font-size: 28px;
            font-weight: bold;
            color: var(--text-color, #333);
        }
        .vs-text {
            font-size: 14px;
            font-weight: 600;
            color: #999;
            margin: 0 10px;
        }
        .game-location-simple {
            font-size: 12px;
            color: #888;
            margin-top: 10px;
            border-top: 1px solid #eee;
            padding-top: 8px;
        }
        </style>
    """), unsafe_allow_html=True)
    
    # Layout games in a grid
    cols = st.columns(3)  # 3 games per row
    
    for i, game in enumerate(week_games.iter_rows(named=True)):
        col_idx = i % 3
        
        game_id = game["game_id"]
        away_team = game["away_team"]
        home_team = game["home_team"]
        location = game["location"]
        weekday = game.get("weekday", "")
        gametime = game.get("gametime", "")
        
        away_score = game.get("away_score")
        home_score = game.get("home_score")
        
        # Get moneyline data
        away_moneyline = game.get("away_moneyline")
        home_moneyline = game.get("home_moneyline")
        
        is_played = away_score is not None and home_score is not None
        
        away_score_str = str(away_score) if away_score is not None else "-"
        home_score_str = str(home_score) if home_score is not None else "-"
        
        # Format moneyline for display
        def format_moneyline(ml):
            if ml is None or ml == "":
                return ""
            try:
                ml_val = int(ml)
                return f"{ml_val:+d}" if ml_val != 0 else ""
            except:
                return ""
        
        away_ml_str = format_moneyline(away_moneyline)
        home_ml_str = format_moneyline(home_moneyline)
        
        # Check for user pick
        user_pick = st.session_state.user_picks.get(game_id)
        
        # Get logos
        away_logo_b64 = get_base64_image(f"assets/{away_team}.png")
        home_logo_b64 = get_base64_image(f"assets/{home_team}.png")
        
        # Construct classes
        away_classes = "team-logo-large"
        home_classes = "team-logo-large"
        
        if user_pick == away_team:
            away_classes += " picked-team"
        if user_pick == home_team:
            home_classes += " picked-team"
            
        # Build card content
        with cols[col_idx]:
            # For unplayed games, show the card and add selection buttons
            if not is_played:
                # Build the HTML card structure with moneyline
                away_img = f'<img src="data:image/png;base64,{away_logo_b64}" class="{away_classes}">' if away_logo_b64 else ""
                home_img = f'<img src="data:image/png;base64,{home_logo_b64}" class="{home_classes}">' if home_logo_b64 else ""
                
                # Add moneyline to team display if available
                away_ml_display = f'<div style="font-size: 12px; color: #888; margin-top: 4px;">{away_ml_str}</div>' if away_ml_str else ""
                home_ml_display = f'<div style="font-size: 12px; color: #888; margin-top: 4px;">{home_ml_str}</div>' if home_ml_str else ""
                
                card_html = f'<div class="game-card"><div class="game-header">{weekday} • {gametime} • Week {selected_week}</div><div class="matchup-container"><div class="team-container">{away_img}<div class="team-name">{away_team}</div>{away_ml_display}<div class="score-val-large">{away_score_str}</div></div><div class="vs-text">@</div><div class="team-container">{home_img}<div class="team-name">{home_team}</div>{home_ml_display}<div class="score-val-large">{home_score_str}</div></div></div></div>'
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Add selection buttons below the card
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    btn_label = f"✓ {away_team}" if user_pick == away_team else f"Select {away_team}"
                    if st.button(btn_label, key=f"btn_{game_id}_{away_team}", use_container_width=True, type="primary" if user_pick == away_team else "secondary"):
                        if user_pick == away_team:
                            del st.session_state.user_picks[game_id]
                        else:
                            st.session_state.user_picks[game_id] = away_team
                        st.rerun()
                
                with btn_cols[1]:
                    btn_label = f"✓ {home_team}" if user_pick == home_team else f"Select {home_team}"
                    if st.button(btn_label, key=f"btn_{game_id}_{home_team}", use_container_width=True, type="primary" if user_pick == home_team else "secondary"):
                        if user_pick == home_team:
                            del st.session_state.user_picks[game_id]
                        else:
                            st.session_state.user_picks[game_id] = home_team
                        st.rerun()
            else:
                # For played games, use the simple HTML card
                away_img = f'<img src="data:image/png;base64,{away_logo_b64}" class="team-logo-large">' if away_logo_b64 else ""
                home_img = f'<img src="data:image/png;base64,{home_logo_b64}" class="team-logo-large">' if home_logo_b64 else ""
                
                card_html = f'<div class="game-card"><div class="game-header">{weekday} • {gametime} • Week {selected_week}</div><div class="matchup-container"><div class="team-container">{away_img}<div class="team-name">{away_team}</div><div class="score-val-large">{away_score_str}</div></div><div class="vs-text">@</div><div class="team-container">{home_img}<div class="team-name">{home_team}</div><div class="score-val-large">{home_score_str}</div></div></div></div>'
                st.markdown(card_html, unsafe_allow_html=True)


# UI Setup

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Live Rankings", "Schedule"])

if page == "Live Rankings":
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

elif page == "Schedule":
    render_schedule_page()
