"""
Schedule page for NFL Season Simulator
"""
import streamlit as st
import polars as pl
import textwrap
from team import Team
from ui.utils import get_base64_image
from utils import moneyline_to_probability, generate_team_with_weekly_records_table
from team_colors import TEAM_COLORS
import numpy as np


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

    # Precompute cumulative team records by week directly from schedule data
    record_lookup = {}
    try:
        # Initialize team stats
        teams_in_schedule = set(df_schedule["away_team"]) | set(df_schedule["home_team"])
        team_stats = {t: [0, 0, 0, 0] for t in teams_in_schedule}  # wins, losses, ties, games

        # Process weeks in order and accumulate results
        unique_weeks = sorted(list(df_schedule["week"].unique()))
        for w in unique_weeks:
            week_rows = df_schedule.filter(pl.col("week") == w).iter_rows(named=True)
            # For each game in the week, update team stats
            for r in week_rows:
                away = r.get("away_team")
                home = r.get("home_team")
                away_score = r.get("away_score")
                home_score = r.get("home_score")

                # Only increment games and results if the game has been played (scores present)
                if away_score is not None and home_score is not None:
                    try:
                        team_stats[away][3] += 1
                        team_stats[home][3] += 1

                        if float(away_score) > float(home_score):
                            team_stats[away][0] += 1
                            team_stats[home][1] += 1
                        elif float(away_score) < float(home_score):
                            team_stats[home][0] += 1
                            team_stats[away][1] += 1
                        else:
                            team_stats[away][2] += 1
                            team_stats[home][2] += 1
                    except Exception:
                        # ignore if scores not numeric
                        pass

            # After processing the week, record cumulative stats for all teams
            for t, stats in team_stats.items():
                record_lookup[(t, int(w))] = (int(stats[0]), int(stats[1]), int(stats[2]), int(stats[3]))
    except Exception:
        record_lookup = {}
    
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
            display: block;
            z-index: 1;
        }
        .team-logo-large:hover {
            transform: scale(1.05);
            cursor: pointer;
        }
        .picked-team {
            border: 5px solid #6c757d !important;
            box-shadow: 0 0 20px rgba(108, 117, 125, 0.6) !important;
            background-color: rgba(108, 117, 125, 0.15) !important;
            position: relative !important;
            z-index: 10 !important; /* lift selected image above neighbors */
            overflow: visible !important;
            box-sizing: border-box !important;
        }
        .team-name {
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 4px;
        }
        .team-record {
            font-size: 12px;
            color: #666;
            margin-bottom: 6px;
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
        
        # game_id = game["game_id"]
        away_team = game["away_team"]
        home_team = game["home_team"]
        game_id = away_team + '-' + home_team # TODO: TEMP USE GENERIC GAME ID FOR BETTER USEABILITY ACROSS SEASONS
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
                # Build image HTML with robust fallbacks and enforced sizing so selected logos always appear
                def make_img_html(team, b64, classes):
                    # prefer base64 data URL if available
                    if b64:
                        src = f"data:image/png;base64,{b64}"
                    else:
                        # fallback to local file path (Streamlit will serve assets)
                        src = f"assets/{team}.png"

                    # ensure consistent sizing and ensure selected logos render above others
                    style = 'style="display:block; width:80px; height:80px; object-fit:contain;"'
                    alt = f' alt="{team}"'
                    return f'<img src="{src}" class="{classes}" {style}{alt}>'

                away_img = make_img_html(away_team, away_logo_b64, away_classes)
                home_img = make_img_html(home_team, home_logo_b64, home_classes)
                
                # Add moneyline to team display if available
                # Compute win probabilities: prefer Gemini predictions if present, else derive from moneyline
                away_prob = None
                home_prob = None
                try:
                    # Prefer moneyline-derived probabilities when moneylines are available (more accurate)
                    if away_moneyline not in (None, "") and home_moneyline not in (None, ""):
                        try:
                            ml_probs = moneyline_to_probability(int(away_moneyline), int(home_moneyline))
                            away_prob, home_prob = float(ml_probs[0]), float(ml_probs[1])
                        except Exception:
                            away_prob = None
                            home_prob = None

                    # Fallback to Gemini predictions if moneyline not available or failed
                    if (away_prob is None or home_prob is None):
                        ga = game.get("gemini_away_win_prob")
                        gh = game.get("gemini_home_win_prob")
                        if ga not in (None, "") and gh not in (None, ""):
                            try:
                                away_prob = float(ga)
                                home_prob = float(gh)
                            except Exception:
                                away_prob = None
                                home_prob = None
                except Exception:
                    away_prob = None
                    home_prob = None

                def make_prob_display(prob, is_away=True):
                    if prob is None:
                        return ""
                    # Colors: away -> navy, home -> red
                    color = "#013369" if is_away else "#D50A0A"
                    pct = int(round(prob * 100))
                    return f"<div style=\"margin-top:6px;\"><div style=\"display:flex;justify-content:space-between;font-size:11px;color:#666;margin-bottom:4px;\"><span>{'Win %'}</span><span><strong>{pct}%</strong></span></div><div style=\"background:#eee;border-radius:8px;overflow:hidden;height:8px;\"><div style=\"width:{pct}%;height:100%;background:{color};\"></div></div></div>"

                split_display = ""
                # If we have both probabilities, render a single split bar (away left, home right)
                if away_prob is not None and home_prob is not None:
                    away_pct = int(round(away_prob * 100))
                    home_pct = int(round(home_prob * 100))
                    # adjust rounding to ensure sum == 100
                    if away_pct + home_pct != 100:
                        home_pct = 100 - away_pct

                    # Use team colors for the split bar; fall back to navy/red if missing
                    away_color = TEAM_COLORS.get(away_team, "#013369")
                    home_color = TEAM_COLORS.get(home_team, "#D50A0A")
                    # Include moneyline odds alongside the team names when available
                    # Prepare separate lines for moneyline odds to show under team names
                    away_ml_line = f'<div style="color:#888; font-size:11px; margin-top:2px;">{away_ml_str}</div>' if away_ml_str else ""
                    home_ml_line = f'<div style="color:#888; font-size:11px; margin-top:2px;">{home_ml_str}</div>' if home_ml_str else ""

                    split_display = f'''<div style="width:100%; margin-top:8px;">
                        <div style="display:flex;justify-content:space-between;font-size:11px;color:#666;margin-bottom:6px;">
                            <div style="text-align:left;">
                                <div><strong>{away_team}</strong> <span style="color:#333;">{away_pct}%</span></div>
                            </div>
                            <div style="text-align:right;">
                                <div><strong>{home_team}</strong> <span style="color:#333;">{home_pct}%</span></div>
                            </div>
                        </div>
                        <div style="background:#eee;border-radius:8px;overflow:hidden;height:12px;display:flex;">
                            <div style="width:{away_pct}%;background:{away_color};height:100%;"></div>
                            <div style="width:{home_pct}%;background:{home_color};height:100%;"></div>
                        </div>
                    </div>'''
                    # Show moneyline odds under the main team name in the card
                    away_ml_display = away_ml_line
                    home_ml_display = home_ml_line
                else:
                    away_ml_display = f'<div style="font-size: 12px; color: #888; margin-top: 4px;">{away_ml_str}</div>' if away_ml_str else ""
                    home_ml_display = f'<div style="font-size: 12px; color: #888; margin-top: 4px;">{home_ml_str}</div>' if home_ml_str else ""
                
                # Compute record display: pre-game if unplayed, post-game if played
                def record_html_for(team, week, played):
                    if played:
                        rec = record_lookup.get((team, int(week)))
                    else:
                        rec = record_lookup.get((team, int(week) - 1))

                    if not rec:
                        # If no prior data, default to 0-0
                        return '<div class="team-record">0-0</div>' if not played else ''

                    wins, losses, ties, games = rec
                    if ties and ties > 0:
                        rec_str = f"{wins}-{losses}-{ties}"
                    else:
                        rec_str = f"{wins}-{losses}"
                    # Only show the W-L(-T) string; remove verbose 'Record (pre/post)' label
                    return f'<div class="team-record"><strong>{rec_str}</strong></div>'

                away_record_html = record_html_for(away_team, selected_week, is_played)
                home_record_html = record_html_for(home_team, selected_week, is_played)

                card_html = f'<div class="game-card"><div class="game-header">{weekday} • {gametime} • Week {selected_week}</div><div class="matchup-container"><div class="team-container">{away_img}<div class="team-name">{away_team}</div>{away_record_html}{away_ml_display}<div class="score-val-large">{away_score_str}</div></div><div class="vs-text">@</div><div class="team-container">{home_img}<div class="team-name">{home_team}</div>{home_record_html}{home_ml_display}<div class="score-val-large">{home_score_str}</div></div></div>{split_display}</div>'
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
                # compute post-game records
                def record_html_for_played(team, week):
                    rec = record_lookup.get((team, int(week)))
                    if not rec:
                        return ''
                    wins, losses, ties, games = rec
                    if ties and ties > 0:
                        rec_str = f"{wins}-{losses}-{ties}"
                    else:
                        rec_str = f"{wins}-{losses}"
                    return f'<div class="team-record"><strong>{rec_str}</strong></div>'

                away_record_html = record_html_for_played(away_team, selected_week)
                home_record_html = record_html_for_played(home_team, selected_week)

                card_html = f'<div class="game-card"><div class="game-header">{weekday} • {gametime} • Week {selected_week}</div><div class="matchup-container"><div class="team-container">{away_img}<div class="team-name">{away_team}</div>{away_record_html}<div class="score-val-large">{away_score_str}</div></div><div class="vs-text">@</div><div class="team-container">{home_img}<div class="team-name">{home_team}</div>{home_record_html}<div class="score-val-large">{home_score_str}</div></div></div></div>'
                st.markdown(card_html, unsafe_allow_html=True)

                # (Records are displayed inside each game card; no extra inline record text needed here)
