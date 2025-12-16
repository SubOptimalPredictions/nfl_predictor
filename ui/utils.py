"""
Shared utility functions for NFL Season Simulator UI
"""
import streamlit as st
import polars as pl
import numpy as np
import base64
import os
import textwrap
from team import Team


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
