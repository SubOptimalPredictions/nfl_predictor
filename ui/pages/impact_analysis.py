"""
Impact Analysis page for NFL Season Simulator
Shows how each team's playoff chances change with a win or loss in their next game
"""
import streamlit as st
import polars as pl
import os
from ui.utils import (
    get_base64_image,
    get_team_conferences,
)
from team_colors import TEAM_COLORS



def load_impact_data(csv_path="data/impact_analysis.csv"):
    """Load impact analysis data from CSV file"""
    if not os.path.exists(csv_path):
        return None
    
    try:
        df = pl.read_csv(csv_path)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None


def render_impact_analysis_page():
    """Render the impact analysis page"""
    st.subheader("🎯 Playoff Impact Analysis")
    st.markdown(
        "See how each team's playoff chances change with a win or loss in their next game."
    )
    
    # Load data
    impact_data = load_impact_data()
    
    if impact_data is None:
        st.info("📁 No impact analysis data available. Please ensure `data/impact_analysis.csv` exists.")
        st.markdown("""
        ### Expected CSV Format
        The CSV should have the following columns:
        - `team`: Team abbreviation (e.g., "KC", "SF", "DAL")
        - `opponent`: Opponent abbreviation
        - `is_home`: Boolean (true/false) indicating if team is playing at home
        - `current_probability`: Current playoff probability (0.0-1.0)
        - `win_probability`: Playoff probability if team wins (0.0-1.0)
        - `loss_probability`: Playoff probability if team loses (0.0-1.0)
        """)
        return
    
    # Get team conferences for filtering
    team_conferences = get_team_conferences()
    
    # Separate by conference
    nfc_data = impact_data.filter(impact_data["team"].is_in([t for t, c in team_conferences.items() if c == "NFC"]))
    afc_data = impact_data.filter(impact_data["team"].is_in([t for t, c in team_conferences.items() if c == "AFC"]))
    
    # Sort by impact swing (descending)
    for df in [nfc_data, afc_data]:
        if len(df) > 0:
            df = df.with_columns(
                swing=(pl.col("win_probability") - pl.col("loss_probability")).abs()
            ).sort("swing", descending=True)
    
    # Display results
    nfc_tab, afc_tab = st.tabs(["NFC Impact", "AFC Impact"])
    
    with nfc_tab:
        st.markdown("### NFC Teams - Ranked by Impact")
        if len(nfc_data) > 0:
            display_conference_results(nfc_data)
        else:
            st.info("No NFC data available")
    
    with afc_tab:
        st.markdown("### AFC Teams - Ranked by Impact")
        if len(afc_data) > 0:
            display_conference_results(afc_data)
        else:
            st.info("No AFC data available")


def display_conference_results(data):
    """Display impact analysis results for a conference"""
    
    # Calculate derived metrics
    display_data = data.with_columns([
        (pl.col("win_probability") - pl.col("loss_probability")).abs().alias("swing"),
        ((pl.col("win_probability") - pl.col("current_probability")) * 100).alias("win_delta"),
        ((pl.col("loss_probability") - pl.col("current_probability")) * 100).alias("loss_delta"),
    ]).sort("swing", descending=True)
    
    # Display cards vertically (1 column)
    for idx, row in enumerate(display_data.iter_rows(named=True)):
        team = row["team"]
        opponent = row["opponent"]
        is_home = row["is_home"]
        current = row["current_probability"]
        win_prob = row["win_probability"]
        loss_prob = row["loss_probability"]
        swing = row["swing"]
        
        location = "🏠 Home" if is_home else "✈️ Away"
        
        # Determine impact level
        if swing > 0.25:
            impact_level = "🔴 CRITICAL"
        elif swing > 0.15:
            impact_level = "🟡 HIGH STAKES"
        else:
            impact_level = "🟢 MODERATE"
        
        # Get team color for gradient
        team_color = TEAM_COLORS.get(team, "#6366f1")  # Default to indigo if not found
        opponent_color = TEAM_COLORS.get(opponent, "#6366f1")
        
        # Convert hex to RGB for rgba values (simple conversion)
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        team_rgb = hex_to_rgb(team_color)
        opponent_rgb = hex_to_rgb(opponent_color)
        
        # Get team logos
        logo_path = f"assets/{team}.png"
        logo_data = get_base64_image(logo_path)
        team_logo_html = f"<img src='data:image/png;base64,{logo_data}' style='width: 50px; height: 50px; object-fit: contain;'>" if logo_data else ""
        
        opp_logo_path = f"assets/{opponent}.png"
        opp_logo_data = get_base64_image(opp_logo_path)
        opp_logo_html = f"<img src='data:image/png;base64,{opp_logo_data}' style='width: 50px; height: 50px; object-fit: contain;'>" if opp_logo_data else ""
        
        # Create complete card HTML using double quotes to avoid conflicts
        card_html = f"""<div style="background: linear-gradient(135deg, rgba({team_rgb[0]}, {team_rgb[1]}, {team_rgb[2]}, 0.1) 0%, rgba({opponent_rgb[0]}, {opponent_rgb[1]}, {opponent_rgb[2]}, 0.1) 100%); padding: 24px; border-radius: 10px; border: 2px solid #e5e7eb; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <div style="flex: 0.8;"><h3 style="margin: 0; font-size: 28px; font-weight: bold; color: #1f2937;">{team}</h3></div>
                <div style="flex: 0.2; display: flex; justify-content: center;">{team_logo_html}</div>
                <div style="flex: 1; text-align: center;"><p style="margin: 0; font-weight: bold; color: #4b5563;">{location}</p></div>
                <div style="flex: 0.2; display: flex; justify-content: center;">{opp_logo_html}</div>
                <div style="flex: 0.8; text-align: right;"><h3 style="margin: 0; font-size: 28px; font-weight: bold; color: #1f2937;">vs {opponent}</h3></div>
            </div>
            <div style="text-align: center; padding: 12px; background: linear-gradient(135deg, rgba({team_rgb[0]}, {team_rgb[1]}, {team_rgb[2]}, 0.25) 0%, rgba({opponent_rgb[0]}, {opponent_rgb[1]}, {opponent_rgb[2]}, 0.25) 100%); border-radius: 8px; font-weight: bold; border: 1px solid rgba(0,0,0,0.1); margin-bottom: 16px; color: #1f2937;">{impact_level}</div>
            <hr style="margin: 16px 0; border: none; border-top: 1px solid rgba(0,0,0,0.1);">
            <div style="display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 20px;">
                <div><p style="margin: 0 0 8px 0; color: #6b7280; font-size: 12px; font-weight: 600;">IMPACT SWING</p><p style="margin: 0; color: #1f2937; font-size: 24px; font-weight: bold;">{swing*100:.1f}%</p></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                <div style="background: #dcfce7; padding: 12px; border-radius: 8px; border: 1px solid #86efac; text-align: center;"><p style="margin: 0 0 4px 0; color: #166534; font-size: 11px; font-weight: 600;">📈 IF WIN</p><p style="margin: 0 0 4px 0; color: #166534; font-size: 20px; font-weight: bold;">{win_prob*100:.1f}%</p><p style="margin: 0; color: #16a34a; font-size: 11px;">+{(win_prob - current)*100:.1f}%</p></div>
                <div style="background: #fef3c7; padding: 12px; border-radius: 8px; border: 1px solid #fcd34d; text-align: center;"><p style="margin: 0 0 4px 0; color: #92400e; font-size: 11px; font-weight: 600;">➡️ CURRENT</p><p style="margin: 0 0 4px 0; color: #92400e; font-size: 20px; font-weight: bold;">{current*100:.1f}%</p><p style="margin: 0; color: #b45309; font-size: 11px;">Baseline</p></div>
                <div style="background: #fee2e2; padding: 12px; border-radius: 8px; border: 1px solid #fca5a5; text-align: center;"><p style="margin: 0 0 4px 0; color: #7c2d12; font-size: 11px; font-weight: 600;">📉 IF LOSS</p><p style="margin: 0 0 4px 0; color: #7c2d12; font-size: 20px; font-weight: bold;">{loss_prob*100:.1f}%</p><p style="margin: 0; color: #dc2626; font-size: 11px;">{(loss_prob - current)*100:.1f}%</p></div>
            </div>
        </div>"""
        
        st.markdown(card_html, unsafe_allow_html=True)
        st.write("")  # Spacing between cards

