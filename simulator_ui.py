"""
NFL Season Simulator - Main Entry Point
"""
import streamlit as st
from ui.pages.live_rankings import render_live_rankings_page
from ui.pages.schedule import render_schedule_page

# Page configuration
st.set_page_config(page_title="NFL Season Simulator", page_icon=":football:", layout="wide")

# Navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Live Rankings", "Schedule"])

# Render selected page
if page == "Live Rankings":
    st.title("🏈 NFL Season Simulator - Live Rankings")
    render_live_rankings_page()
elif page == "Schedule":
    render_schedule_page()
