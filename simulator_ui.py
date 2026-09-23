"""
NFL Season Simulator - Main Entry Point
"""
import streamlit as st
from ui.pages.live_rankings import render_live_rankings_page
from ui.pages.schedule import render_schedule_page
from ui.pages.impact_analysis import render_impact_analysis_page
# Page configuration
st.set_page_config(page_title="NFL Season Simulator", page_icon=":football:", layout="wide")

# Main title
st.title("🏈 NFL Season Simulator")

# Tab-based navigation
tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Rankings", "📅 Schedule", "🏅 Division Standings", "🎯 Impact Analysis"])

with tab1:
    render_live_rankings_page()

with tab2:
    render_schedule_page()

with tab3:
    from ui.pages.division_standings import render_division_standings_page

    render_division_standings_page()

with tab4:
    render_impact_analysis_page()
