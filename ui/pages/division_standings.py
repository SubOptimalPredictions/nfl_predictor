"""
Division Standings page

Displays current standings for each division in AFC and NFC using
`get_current_standings` from the project's `utils` module.
"""
from typing import Dict

import pandas as pd
import streamlit as st

from utils import get_current_standings
from ui.utils import get_base64_image


def _render_divisions_from_df(df: pd.DataFrame, conf: str):
    """Try to render standings split by division when possible.

    The pro-football-reference standings tables sometimes come back as a
    wide DataFrame with a MultiIndex columns or with division names as top
    level columns. This helper handles a few common shapes and falls back
    to showing the whole table.
    """
    df = _clean_division_rows(df, conf)

    # MultiIndex columns (e.g. top-level headers are division names)
    if isinstance(df.columns, pd.MultiIndex):
        top_headers = list(df.columns.get_level_values(0).unique())
        for h in top_headers:
            sub = df[h].dropna(how="all").reset_index(drop=True)
            if sub.empty:
                continue
            st.subheader(h)
            _render_table_with_logos(sub)
        return

    # If the DataFrame has division-like column names (e.g. 'AFC East')
    division_candidates = [c for c in df.columns if any(k in str(c) for k in ("East", "North", "South", "West"))]
    if division_candidates:
        # Show columns that correspond to each division header
        for c in division_candidates:
            sub = df[[c]].dropna(how="all")
            if sub.empty:
                continue
            st.subheader(str(c))
            _render_table_with_logos(sub.reset_index(drop=True))
        return

    # Fallback: show the full table (cleaned)
    st.subheader("Standings")
    _render_table_with_logos(df.reset_index(drop=True))


def _find_team_col(df: pd.DataFrame):
    for c in df.columns:
        name = str(c).lower()
        if "team" in name or name in ("tm", "team/name", "school"):
            return c
    # fallback: first column
    return df.columns[0]


def _render_table_with_logos(df: pd.DataFrame):
    """Render DataFrame as an HTML table including team logos (if possible)."""
    if df.empty:
        st.write("No data")
        return

    team_col = _find_team_col(df)

    # build HTML table
    headers = list(df.columns)
    table_rows = []
    for _, row in df.iterrows():
        cols = []
        for h in headers:
            val = row[h]
            if h == team_col and isinstance(val, str) and val.strip():
                team_name = val.strip()
                logo_b64 = get_base64_image(f"assets/{team_name}.png")
                if logo_b64:
                    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:20px;margin-right:8px;vertical-align:middle;border-radius:4px;">'
                else:
                    logo_html = ""
                cols.append(f"<td style='padding:6px;white-space:nowrap;'>{logo_html}<strong>{team_name}</strong></td>")
            else:
                cols.append(f"<td style='padding:6px'>{'' if pd.isna(val) else str(val)}</td>")
        table_rows.append("<tr>" + "".join(cols) + "</tr>")

    header_html = "".join([f"<th style='text-align:left;padding:6px'>{h}</th>" for h in headers])
    body_html = "".join(table_rows)
    table_html = f"<table style='border-collapse:collapse;width:100%;'><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)


def _clean_division_rows(d: pd.DataFrame, conf: str) -> pd.DataFrame:
    # remove rows that are just division headers (e.g., 'AFC North')
    cleaned = d.copy()
    division_names = [f"{conf} {x}" for x in ("East", "North", "South", "West")]

    def is_divider_row(row):
        for v in row:
            try:
                if isinstance(v, str) and v.strip() in division_names:
                    return True
            except Exception:
                continue
        return False

    cleaned = cleaned.loc[~cleaned.apply(is_divider_row, axis=1)]
    cleaned = cleaned.dropna(how="all")
    return cleaned


def _find_stat_col(df: pd.DataFrame, candidates: list[str]):
    for c in df.columns:
        name = str(c).lower()
        for cand in candidates:
            if cand in name:
                return c
    return None


def _prepare_division_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and sort a division DataFrame for display."""
    # Preserve the order provided by the source; do not reorder rows.
    # We only reset the index for clean display.
    if df.empty:
        return df

    return df.reset_index(drop=True)


def render_division_standings_page():
    st.header("🏅 Division Standings")

    try:
        afc, nfc = get_current_standings()
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Unable to fetch current standings: {exc}")
        return
    # Prefer the structured split helper if available (clean division tables)
    from utils import split_standings_by_division

    # AFC
    st.markdown("### AFC")
    try:
        # get_current_standings may already return a dict {division: DataFrame}
        if isinstance(afc, dict):
            afc_divs = afc
        else:
            afc_divs = split_standings_by_division(afc)

        # Render divisions in the order they are provided by the source.
        keys = list(afc_divs.keys())
        # show the original order to the user
        if keys:
            order_text = " → ".join([str(k) for k in keys])
            st.markdown(f"<div style='color:#666;font-size:13px;margin-bottom:8px'>Original order: {order_text}</div>", unsafe_allow_html=True)
        if not keys:
            st.info("No division data available for AFC")
        else:
            # Render as rows with two columns, preserving order
            for i in range(0, len(keys), 2):
                row_keys = keys[i : i + 2]
                cols = st.columns(2)
                for col, key in zip(cols, row_keys):
                    with col:
                        sub_df = afc_divs[key]
                        sub_df = _clean_division_rows(sub_df, "AFC")
                        sub_df = _prepare_division_df(sub_df)
                        label = key if ("AFC" in str(key) or "NFC" in str(key)) else f"AFC {key}"
                        st.subheader(label)
                        if sub_df.empty:
                            st.info("No data for this division")
                            continue
                        _render_table_with_logos(sub_df.reset_index(drop=True))
    except Exception:
        # Fallback to best-effort renderer
        _render_divisions_from_df(afc, "AFC")

    st.markdown("---")

    # NFC
    st.markdown("### NFC")
    try:
        if isinstance(nfc, dict):
            nfc_divs = nfc
        else:
            nfc_divs = split_standings_by_division(nfc)

        keys = list(nfc_divs.keys())
        if keys:
            order_text = " → ".join([str(k) for k in keys])
            st.markdown(f"<div style='color:#666;font-size:13px;margin-bottom:8px'>Original order: {order_text}</div>", unsafe_allow_html=True)
        if not keys:
            st.info("No division data available for NFC")
        else:
            for i in range(0, len(keys), 2):
                row_keys = keys[i : i + 2]
                cols = st.columns(2)
                for col, key in zip(cols, row_keys):
                    with col:
                        sub_df = nfc_divs[key]
                        sub_df = _clean_division_rows(sub_df, "NFC")
                        sub_df = _prepare_division_df(sub_df)
                        label = key if ("AFC" in str(key) or "NFC" in str(key)) else f"NFC {key}"
                        st.subheader(label)
                        if sub_df.empty:
                            st.info("No data for this division")
                            continue
                        _render_table_with_logos(sub_df.reset_index(drop=True))
    except Exception:
        _render_divisions_from_df(nfc, "NFC")
