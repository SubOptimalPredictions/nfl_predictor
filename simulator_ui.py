"""
NFL Season Simulator - Main Entry Point
"""
import streamlit as st
from ui.pages.live_rankings import render_live_rankings_page
from ui.pages.schedule import render_schedule_page

# Page configuration
st.set_page_config(page_title="NFL Season Simulator", page_icon=":football:", layout="wide")

# Main title
st.title("🏈 NFL Season Simulator")

# Tab-based navigation
tab1, tab2 = st.tabs(["📊 Live Rankings", "📅 Schedule"])

with tab1:
    render_live_rankings_page()

with tab2:
    render_schedule_page()
