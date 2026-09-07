# ==============================================================================
# PAGE MODULE: MAIN HUB
# ==============================================================================
# Central workspace hub that navigates to every module.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    st.markdown("<h2 style='text-align: center; color: #2C3E50; font-weight:bold;'>🏭 Corporate ERP Control Hub Workspace</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7F8C8D; margin-bottom: 28px;'>Select a destination workflow area to process data:</p>", unsafe_allow_html=True)
    
    r1a, r1b, r1c = st.columns(3, gap='small')
    with r1a:
        st.markdown("<div class='hub-card'><h3>📈 1. Dash Board</h3><p style='color:#666;'>Real-time metrics tracking and live production balances.</p></div>", unsafe_allow_html=True)
        if st.button("Execute Dashboard Node ➡️", key="btn_dash", use_container_width=True):
            st.session_state.current_page = "Dashboard"
            st.rerun()
    with r1b:
        st.markdown("<div class='hub-card' style='border-top-color: #0D9488;'><h3>🗃️ 2. Master</h3><p style='color:#666;'>Central control hub — Inventory &amp; Accounting master groups.</p></div>", unsafe_allow_html=True)
        if st.button("Execute Master Hub ➡️", key="btn_master", use_container_width=True):
            st.session_state.current_page = "Master"
            st.rerun()
    with r1c:
        st.markdown("<div class='hub-card' style='border-top-color: #0D9488;'><h3>📝 3. Entry Module</h3><p style='color:#666;'>Record accounting transactions and financial entries.</p></div>", unsafe_allow_html=True)
        if st.button("Execute Entry Module ➡️", key="btn_entry", use_container_width=True):
            st.session_state.current_page = "Entry Mode"
            st.rerun()

    r2a, r2b, r2c = st.columns(3, gap='small')
    with r2a:
        st.markdown("<div class='hub-card' style='border-top-color: #8E44AD;'><h3>📚 4. Financial Statement</h3><p style='color:#666;'>View accounting ledgers and financial statements.</p></div>", unsafe_allow_html=True)
        if st.button("Execute Financial Statement ➡️", key="btn_financial_statement", use_container_width=True):
            st.session_state.current_page = "Financial Statement"
            st.rerun()
    with r2b:
        st.markdown("<div class='hub-card' style='border-top-color: #6A1B9A;'><h3>📊 5. Production Statement</h3><p style='color:#666;'>Extract production reports and download Excel sheets.</p></div>", unsafe_allow_html=True)
        if st.button("Execute Production Statement ➡️", key="btn_report", use_container_width=True):
            st.session_state.current_page = "Production Statement"
            st.rerun()
    with r2c:
        st.markdown("<div class='hub-card' style='border-top-color: #D35400;'><h3>👥 6. HR Module</h3><p style='color:#666;'>Manage HR-related entries and employee information.</p></div>", unsafe_allow_html=True)
        if st.button("Execute HR Module ➡️", key="btn_hr", use_container_width=True):
            st.session_state.current_page = "HR Module"
            st.rerun()
