"""
Playoff Bracket page for NFL Season Simulator
"""
import streamlit as st
import textwrap
import streamlit.components.v1 as components
from ui.utils import get_base64_image, get_team_conferences, get_projected_order


def _render_conference_bracket(conference_name, order, aggregator, num_times_run, accent):
    # Build HTML for a single conference bracket (seed list + wild card matchups)
    rows = []

    # Seed rows (1..7). Seed 1 has the bye
    for i in range(1, 8):
        team = order[i - 1] if i <= len(order) else "-"
        logo_b64 = get_base64_image(f"assets/{team}.png") if team != "-" else ""
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="team-logo">' if logo_b64 else ""

        if i == 1:
            # Bye row
            rows.append(f"""
            <div class="seed-row">
                <div class="seed-num">1</div>
                <div class="team-box bye">{logo_html}<div class="team-name">{team}</div><div class="badge">BYE</div></div>
                <div class="seed-connector empty"></div>
            </div>
            """)
        else:
            rows.append(f"""
            <div class="seed-row">
                <div class="seed-num">{i}</div>
                <div class="team-box">{logo_html}<div class="team-name">{team}</div></div>
                <div class="seed-connector"></div>
            </div>
            """)

    # Wild-card matchups (2v7, 3v6, 4v5)
    wc_html = ""
    pairs = [(2, 7), (3, 6), (4, 5)]
    for a, b in pairs:
        ta = order[a - 1] if a <= len(order) else "-"
        tb = order[b - 1] if b <= len(order) else "-"
        logo_a = get_base64_image(f"assets/{ta}.png") if ta != "-" else ""
        logo_b = get_base64_image(f"assets/{tb}.png") if tb != "-" else ""
        a_html = f'<img src="data:image/png;base64,{logo_a}" class="mini-logo">' if logo_a else ""
        b_html = f'<img src="data:image/png;base64,{logo_b}" class="mini-logo">' if logo_b else ""

        wc_html += f"""
        <div class="match-row">
            <div class="team-left">{a_html}<span class="team-label">{a}. {ta}</span></div>
            <div class="vs">vs</div>
            <div class="team-right">{b_html}<span class="team-label">{b}. {tb}</span></div>
        </div>
        """

    # Assemble the conference block
    block = f"""
    <div class="conference-block">
        <div class="conference-title">{conference_name}</div>
        <div class="seeds">{''.join(rows)}</div>
        <div class="wildcards">{wc_html}</div>
    </div>
    """

    return block


def render_playoff_bracket_page():
    st.header("🏆 Predicted Playoff Bracket")

    if not st.session_state.get("simulation_complete"):
        st.info("Run a simulation in Live Rankings first to generate predictions.")
        return

    aggregator = st.session_state.aggregator
    num_times_run = st.session_state.num_times_run

    team_conferences = get_team_conferences()

    nfc_teams = [t for t in aggregator.keys() if team_conferences.get(t) == "NFC"]
    afc_teams = [t for t in aggregator.keys() if team_conferences.get(t) == "AFC"]

    nfc_order = get_projected_order(nfc_teams, aggregator)[:7]
    afc_order = get_projected_order(afc_teams, aggregator)[:7]

    # CSS for bracket look
    css = textwrap.dedent("""
    <style>
    html, body { margin:0; padding:0; }
    /* Use system UI / neutral sans-serif for consistent look */
    body, .conference-block, .team-name, .seed-num, .match-row { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size:14px; }

    .bracket-grid { display:flex; gap:24px; align-items:flex-start; width:100%; box-sizing:border-box; }
    .conference-block { flex:1 1 0; min-width:320px; border-radius:8px; padding:16px; background:var(--background-color, #fff); box-shadow: 0 4px 12px rgba(0,0,0,0.04); box-sizing:border-box; }
    .conference-title { font-weight:700; margin-bottom:12px; font-size:18px; }
    .seed-row { display:flex; align-items:center; gap:12px; padding:6px 0; }
    .seed-num { width:28px; font-weight:700; color: #666; }
    .team-box { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:6px; background: rgba(0,0,0,0.03); flex:1; }
    .team-box.bye { background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(0,0,0,0.02)); border: 2px dashed rgba(0,0,0,0.06); }
    .team-logo { height:28px; width:28px; object-fit:contain; border-radius:50%; }
    .team-name { font-weight:600; }
    .badge { background:#ffd966; color:#4a3b00; padding:3px 6px; border-radius:4px; font-weight:700; margin-left:8px; font-size:12px; }
    .seed-connector { width:28px; height:1px; background:transparent; }
    .wildcards { margin-top:12px; }
    .match-row { display:flex; align-items:center; justify-content:space-between; padding:8px; border-radius:6px; margin-bottom:8px; background: transparent; }
    .match-row .team-left, .match-row .team-right { display:flex; align-items:center; gap:8px; font-weight:600; }
    .mini-logo { height:20px; width:20px; object-fit:contain; border-radius:50%; }
    .vs { color:#888; font-weight:700; }

    /* Make sure the iframe content uses full width without unexpected max-width */
    .bracket-wrapper { width:100%; max-width:100%; }
    </style>
    """)

    nfc_block = _render_conference_bracket("NFC", nfc_order, aggregator, num_times_run, "#013369")
    afc_block = _render_conference_bracket("AFC", afc_order, aggregator, num_times_run, "#D50A0A")

    html = css + f"<div class=\"bracket-grid\">{nfc_block}{afc_block}</div>"

    # Use components.html to ensure the raw HTML/CSS renders correctly and take full width
    components.html(f'<div class="bracket-wrapper">{html}</div>', height=780, scrolling=True)

    st.caption("Seeds 1 receive the bye. Wild-card matchups shown as 2v7, 3v6, 4v5.")

