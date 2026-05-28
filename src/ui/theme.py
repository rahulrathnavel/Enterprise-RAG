from __future__ import annotations

import streamlit as st


def apply_enterprise_css() -> None:
    """Apply restrained enterprise styling on top of the Streamlit theme."""

    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            color: #0B1F33;
            letter-spacing: 0;
        }
        [data-testid="stSidebar"] {
            background-color: #EAF2FB;
        }
        div[data-testid="stMetricValue"] {
            color: #0B5CAD;
        }
        .stButton > button {
            background-color: #0B5CAD;
            color: #FFFFFF;
            border: 1px solid #0B5CAD;
            border-radius: 6px;
            font-weight: 600;
        }
        .stButton > button:hover {
            background-color: #084B8A;
            color: #FFFFFF;
            border-color: #084B8A;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
