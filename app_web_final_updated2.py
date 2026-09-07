# ==============================================================================
# SUBH PAPER COMPANY - ERP  |  MAIN ENTRY (ROUTER)
# ==============================================================================
# Streamlit entry point. Each top-level tab is rendered by its own page_*.py
# module (page_company_portal, page_main_hub, page_dashboard, page_master,
# page_entry, page_financial, page_production, page_hr). Route below is the
# ONLY place that decides which tab renders.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *

# ==============================================================================
st.set_page_config(page_title="SUBH PAPER COMPANY - ERP", layout="wide", initial_sidebar_state="expanded")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "Main Hub"


if "financial_year" not in st.session_state:
    st.session_state.financial_year = _financial_year_label()

st.markdown("""
    <style>
    /* Reduce Streamlit top blank space to maximize dashboard workspace */
    [data-testid="stAppViewContainer"] > .main .block-container {
        padding-top: 10mm !important; /* Exact top page margin */
        padding-bottom: 1rem !important;
    }
    .main-title { font-size:40px !important; font-weight: bold; color: #1E88E5; text-align: center; margin-top: 2px; }
    .subtitle { font-size:20px !important; color: #555; text-align: center; margin-bottom: 30px; font-style: italic; }
    .hub-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #F6F8FA 100%);
        padding: 18px 10px 14px 10px;
        border-radius: 14px;
        border-top: 4px solid #1E88E5;
        box-shadow: 0 5px 16px rgba(31, 45, 61, 0.10);
        text-align: center;
        margin-bottom: 10px;
        min-height: 166px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        overflow: hidden;
    }
    .hub-card h3 {
        font-size: 17px !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        margin: 4px 0 14px 0 !important;
        color: #243447 !important;
        font-weight: 700 !important;
    }
    .hub-card p {
        font-size: 12px !important;
        line-height: 1.55 !important;
        margin: 0 !important;
        color: #687684 !important;
        max-width: 165px;
    }
    .section-header { color: #1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 5px; margin-bottom: 20px; font-weight: bold; }
    .fe-topbar { background: linear-gradient(90deg,#0B4F8A,#145A94); color:#fff; min-height:46px; padding:7px 12px; display:flex; align-items:center; gap:24px; border-radius:4px 4px 0 0; }
    .fe-brand { font-size:20px; font-weight:700; white-space:nowrap; }
    .fe-company { margin-left:auto; font-size:13px; font-weight:600; }
    .fe-help { font-size:13px; font-weight:600; white-space:nowrap; }
    .fe-titlebar { background:#EEF7FD; border:1px solid #C7DDEB; padding:7px 12px; display:flex; justify-content:space-between; font-size:14px; color:#163F63; }
    .fe-table-head { display:grid; grid-template-columns:.85fr 3.1fr 1.6fr 1.15fr 1.15fr .34fr; background:#EEF6FC; border:1px solid #CBDCE8; border-bottom:0; margin-top:14px; padding:7px 8px; font-size:13px; font-weight:700; }
    .fe-table-head-noref { display:grid; grid-template-columns:.85fr 3.1fr 1.15fr 1.15fr .34fr; background:#EEF6FC; border:1px solid #CBDCE8; border-bottom:0; margin-top:14px; padding:7px 8px; font-size:13px; font-weight:700; }
    .fe-drcr-head,.fe-ledger-head,.fe-billref-head,.fe-debit-head,.fe-credit-head { text-align:center; }
    .fe-totals { display:flex; justify-content:flex-end; gap:35px; border-top:1px solid #CBDCE8; padding:7px 10px; margin-bottom:8px; font-size:13px; color:#173F60; }
    .inv-table-head { background:#FDF3E7; border:1px solid #E6C9A6; padding:8px 10px; margin-top:18px; font-size:14px; font-weight:700; color:#7A4A12; }
    .inv-total { border-top:1px solid #E6C9A6; padding:7px 10px; margin-bottom:8px; font-size:13px; color:#7A4A12; text-align:right; }
    .inv-unit { background:#FFFFFF; border:1px solid #E6C9A6; border-radius:6px; padding:7px 10px; font-size:13px; color:#7A4A12; min-height:38px; text-align:center; }
    .inv-unit.amt { font-weight:700; text-align:right; }
    .ledger-report-title { font-size:24px; font-weight:700; color:#17365D; text-align:center; margin-bottom:4px; }
    .ledger-company-name { font-size:16px; font-weight:600; color:#4A6A8A; text-align:center; margin-bottom:16px; }
    .ledger-ledger-name { font-size:18px; font-weight:700; color:#17365D; margin:12px 0; padding:8px 16px; background:#EEF7FD; border-left:4px solid #17365D; }
    .ledger-footer { margin-top:16px; padding:10px 16px; background:#F8F9FA; border-top:2px solid #17365D; font-weight:600; }
    .ledger-amount { text-align:right; font-weight:600; }

    /* Tally-style voucher gateway + register + print */
    .fe-gate-title { margin:14px 0 10px; font-size:16px; color:#163F63; font-weight:600; }
    .fe-gate-hint { margin:12px 0; padding:10px 14px; background:#EEF7FD; border:1px dashed #7FA9CC; border-radius:4px; color:#173F60; font-size:13px; }
    .fe-note { font-size:11px; color:#555; padding-top:10px; }
    .tally-avc-bar {
        background:#1B4F91; color:#fff; display:flex; align-items:center;
        justify-content:space-between; padding:7px 12px; margin:0 0 0 0;
        font-family:Tahoma,"Segoe UI",sans-serif; font-size:14px; font-weight:700;
        letter-spacing:.2px;
    }
    .tally-avc-canvas {
        background:#E8F5C8; border:1px solid #8AA06A; padding:8px 12px 14px;
        font-family:Tahoma,"Segoe UI",sans-serif; color:#111;
    }
    .tally-avc-type-sm {
        display:inline-block; vertical-align:middle; background:#15803d; color:#fff;
        padding:2px 8px 3px; font-size:15px; font-weight:700; min-width:62px;
        text-align:center; line-height:1.2; border-radius:3px;
    }
    .tally-avc-no { font-size:15px; font-weight:700; padding-top:6px; }
    .fe-sale-auto-no { font-size:16px; font-weight:800; color:#134e4a; vertical-align:middle; padding-left:8px; display:inline-block; min-width:36px; }
    .fe-sale-datebox { text-align:right; font-size:15px; font-weight:800; color:#134e4a; letter-spacing:.4px; }
    .fe-sale-day { text-align:right; font-size:12px; font-weight:600; color:#0f766e; margin-top:2px; }
    .tally-avc-datebox { text-align:right; font-size:15px; font-weight:700; line-height:1.25; }
    .tally-avc-datebox .dow { font-size:13px; font-weight:600; }
    .tally-avc-label {
        font-size:13px; color:#111; font-weight:600; padding-top:10px; white-space:nowrap;
    }
    .tally-avc-bal { font-size:13px; color:#222; min-height:28px; padding-top:8px; }
    .tally-avc-itemhead {
        display:grid; grid-template-columns:3.5fr .85fr .95fr .7fr 1.15fr .35fr;
        border-top:1px solid #111; border-bottom:1px solid #111;
        padding:5px 4px; margin-top:12px; font-size:13px; font-weight:700;
    }
    .tally-avc-itemhead span:nth-child(2),
    .tally-avc-itemhead span:nth-child(3),
    .tally-avc-itemhead span:nth-child(4),
    .tally-avc-itemhead span:nth-child(5) { text-align:right; }
    .tally-avc-amtline {
        margin-left:auto; width:168px; text-align:right; font-weight:800;
        border-top:1px solid #111; border-bottom:3px double #111;
        padding:4px 6px; font-size:14px;
    }
    .tally-avc-narration { font-size:13px; font-weight:700; padding-top:8px; }
    .tally-avc-label-i { font-style:italic; font-size:12px; font-weight:500; color:#333; }
    .tally-avc-subbar {
        background:#D6E8F8; border:1px solid #8FB0D0; border-top:0;
        display:flex; align-items:center; justify-content:space-between;
        padding:6px 12px 8px; font-family:Tahoma,"Segoe UI",sans-serif;
    }
    .stApp:has(.tally-avc-bar) { background:#E8F5C8 !important; }
    .stApp:has(.tally-avc-bar) [data-testid="stMainBlockContainer"] {
        background:#E8F5C8; padding-top:0.4rem;
    }
    .stApp:has(.tally-avc-bar) [data-testid="stTextInput"] input:focus {
        background:#FFF4C4 !important;
    }
    .stApp:has(.tally-avc-bar) .tally-avc-itemhead + div,
    .stApp:has(.tally-avc-bar) div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
        background:transparent;
    }
    .tally-register-head { background:linear-gradient(90deg,#0B4F8A,#145A94); color:#fff; padding:8px 12px; border-radius:4px 4px 0 0; font-size:14px; font-weight:700; margin-top:18px; }
    .tally-reg-colhead { display:grid; grid-template-columns:.9fr 1fr 1fr 2.3fr 1fr 1fr 1.6fr; gap:4px; background:#EEF7FD; border:1px solid #C7DDEB; border-top:0; padding:6px 8px; font-size:11px; font-weight:700; color:#163F63; text-align:center; }
    .fe-reg-cell { font-size:12px; color:#1D3A55; padding:8px 4px; border-bottom:1px solid #D9E6F0; min-height:34px; display:flex; align-items:center; }
    .fe-reg-cell.strong { font-weight:700; color:#0B4F8A; }
    .fe-reg-cell.small { font-size:11px; color:#44596B; }
    .fe-reg-cell.amt { justify-content:flex-end; font-weight:600; }
    .voucher-print-page { background:#fff; border:1px solid #C9D2DA; padding:22px; margin-top:10px; color:#000; font-family:'Courier New',Consolas,monospace; box-shadow:0 3px 12px rgba(31,45,61,.12); }
    .voucher-print-page .vp-co { text-align:center; font-size:15px; font-weight:800; letter-spacing:1px; }
    .voucher-print-page .vp-addr { text-align:center; font-size:10px; color:#333; margin-top:2px; }
    .voucher-print-page .vp-title { text-align:center; font-size:13px; font-weight:800; border-bottom:2px solid #000; padding-bottom:6px; margin:8px 0; }
    .voucher-print-page .vp-meta { display:flex; justify-content:space-between; font-size:11px; font-weight:700; margin:6px 0; }
    .voucher-print-page table { width:100%; border-collapse:collapse; font-size:11px; }
    .voucher-print-page th, .voucher-print-page td { border:1px solid #000; padding:4px 6px; }
    .voucher-print-page th { background:#EEF6FC; }
    .voucher-print-page .vp-total-row td { border-top:2px solid #000; font-weight:800; }
    .voucher-print-page .vp-narration { margin-top:8px; font-size:11px; font-weight:600; }
    .voucher-print-page .vp-sig { display:flex; justify-content:space-between; margin-top:26px; font-size:10px; font-weight:700; }

    /* Dashboard: compact Excel-style embossed reporting */
    .dashboard-main-title { margin-top: 0 !important; margin-bottom: 10px !important; }
    .dash-status-strip { display:grid; grid-template-columns:repeat(30,minmax(0,1fr)); gap:7px; margin:6px 0 10px 0; width:100%; }
    .dash-mini-box { grid-column:span 5; min-height:56px; padding:7px 9px 8px; border:1px solid #9AAAB8; border-radius:5px; background:#D8E0E8; box-shadow: inset 0 1px 0 rgba(255,255,255,.75), inset 0 -2px 3px rgba(50,70,90,.12), 0 1px 2px rgba(50,60,70,.12); }
    .dash-mini-box:nth-child(n+7) { grid-column:span 6; }
    .dash-mini-box.blue { border-color:#86A9C9; background:#C9D8E7; }
    .dash-mini-box.green { border-color:#88B495; background:#CDE3D2; }
    .dash-mini-box.orange { border-color:#C79D70; background:#EFD7BC; }
    .dash-mini-box.amber { border-color:#C6AD58; background:#EBDDAD; }
    .dash-mini-label { font-size:11px; line-height:1.15; color:#243545; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .dash-mini-value { font-size:14px; line-height:1.25; font-weight:800; color:#263747; margin-top:4px; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .dash-kpi-row { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:6px; margin:4px 0 10px 0; width:100%; }
    .dash-kpi { min-height:62px; padding:6px 8px 7px; border:1px solid #C7D2DE; border-radius:5px; background:#FBFCFD; box-shadow: inset 0 1px 0 #FFFFFF, inset 0 -3px 5px rgba(70,90,110,.07), 0 2px 4px rgba(50,60,70,.08); }
    .dash-kpi.blue { border-color:#B8D0E8; background:#F5F9FE; }
    .dash-kpi.green { border-color:#C5DEC9; background:#F6FBF6; }
    .dash-kpi.orange { border-color:#E9CDAE; background:#FFF9F4; }
    .dash-kpi-label { font-size:10px; font-weight:800; color:#3D4C5C; padding-bottom:5px; border-bottom:1px solid rgba(100,120,140,.22); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .dash-kpi-value { font-size:17px; line-height:1.05; font-weight:700; color:#173F60; margin-top:8px; }
    .dash-kpi-value span { font-size:10px; font-weight:600; }
    .dash-kpi.green .dash-kpi-value { color:#2F7D45; }
    .dash-kpi.orange .dash-kpi-value { color:#B85A16; }
    .dash-kpi-badge { display:inline-block; margin-top:4px; padding:2px 6px; border-radius:10px; background:#E9F7EC; color:#2D8A45; font-size:8px; font-weight:600; }
    .dash-report-box { border:1px solid #BFCBD6; border-radius:4px; overflow:hidden; margin-bottom:9px; background:#FFFFFF; box-shadow: inset 0 1px 0 #FFFFFF, inset 0 -2px 4px rgba(70,90,110,.05), 0 1px 2px rgba(50,60,70,.07); }
    .dash-report-title { text-align:center; font-size:12px; font-weight:700; color:#243B53; padding:5px 6px; background:#F2F6FA; border-bottom:1px solid #C7D2DC; letter-spacing:.1px; }
    .paper-box .dash-report-title, .order-box .dash-report-title, .board-box .dash-report-title { background:#F7F9FB; }
    .dash-report-table { width:100%; border-collapse:collapse; table-layout:fixed; font-size:10px; color:#273746; }
    .dash-report-table th, .dash-report-table td { border:1px solid #CDD5DC; padding:3px 4px; line-height:1.15; vertical-align:middle; }
    .dash-report-table th { background:#FFF600; color:#111; font-size:9px; font-weight:700; text-align:center; }
    .dash-report-table td { text-align:right; background:#FFF; }
    .dash-report-table td:first-child { text-align:left; font-weight:600; }
    .paper-box .dash-report-table th { background:#FFF600; }
    .order-table th { background:#FFF600; }
    .order-table td { font-size:9px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .order-table th { white-space:nowrap; }
    .order-table th:nth-child(1), .order-table td:nth-child(1) { width:12%; min-width:74px; }
    .order-table th:nth-child(2), .order-table td:nth-child(2) { width:13%; min-width:86px; }
    .order-table th:nth-child(3), .order-table td:nth-child(3) { width:10%; }
    .order-table td:nth-child(2), .order-table td:nth-child(3) { text-align:left; }
    .order-table .positive { color:#00A65A; font-weight:700; }
    .order-table .blank-row td { height:17px; background:#FFF; }
    .board-table th { background:#FFF600; }
        .board-table .summary-row td { font-weight:700; }
    .board-table .grand-row td { font-weight:800; border-top:2px solid #6F7D89; }
    .empty-cell { text-align:center !important; color:#7A8793; padding:12px !important; }
    @media (max-width: 1000px) {
        .dash-status-strip { grid-template-columns:repeat(6,minmax(0,1fr)); }
        .dash-kpi-row { grid-template-columns:repeat(3,minmax(0,1fr)); }
    }
    @media (max-width: 700px) {
        .dash-status-strip { grid-template-columns:repeat(3,minmax(0,1fr)); }
        .dash-kpi-row { grid-template-columns:1fr; }
    }
    /* Print-style report preview: based on the supplied ledger screenshot. */
    .spc-preview-page {
        background:#FFFFFF; border:1px solid #C9D2DA; border-radius:2px;
        padding:28px 28px 20px; margin:14px 0 18px;
        box-shadow:0 5px 18px rgba(31,45,61,.10); color:#111;
    }
    .spc-preview-company { text-align:center; font-size:16px; font-weight:800; color:#111; letter-spacing:.2px; }
    .spc-preview-address { text-align:center; font-size:10px; color:#555; margin-top:2px; }
    .spc-preview-title { text-align:center; font-size:17px; font-weight:800; margin-top:10px; color:#17365D; }
    .spc-preview-subtitle { text-align:center; font-size:10px; color:#555; margin-top:3px; }
    .spc-preview-divider { border-top:1px solid #111; margin:12px 0 0; }
    .spc-preview-table-wrap { overflow-x:auto; width:100%; }
    .spc-preview-table { width:100%; min-width:760px; border-collapse:collapse; margin-top:0; font-family:Arial,sans-serif; font-size:10px; }
    .spc-preview-table th { background:#EEF6FC; color:#111; border:1px solid #8FA0AD; padding:5px 6px; text-align:center; font-weight:700; white-space:nowrap; }
    .spc-preview-table td { border:1px solid #B7C1C9; padding:4px 6px; vertical-align:middle; background:#fff; }
    .spc-preview-table td:first-child { white-space:nowrap; }
    .spc-preview-table tr:nth-child(even) td { background:#FBFCFD; }
    .spc-preview-footer { display:flex; justify-content:space-between; gap:24px; border-top:1px solid #222; margin-top:8px; padding:8px 4px 2px; font-size:11px; }
    .spc-preview-note { margin-top:8px; font-size:9px; color:#777; font-style:italic; }
    .spc-preview-page-footer { margin-top:14px; padding-top:7px; border-top:1px solid #C9D2DA; text-align:right; font-size:9px; color:#777; }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# TEAL PROFESSIONAL THEME (pattern overrides)
# ==============================================================================
st.markdown("""
    <style>
    /* Page background - light teal */
    .stApp { background-color: #e7f2ee; }
    [data-testid="stSidebar"] { background-color: #d9ebe5; }
    [data-testid="stHeader"] { background: transparent; }

    /* Brand accent overrides (blue -> teal) */
    .main-title { color: #0d9488 !important; }
    .subtitle { color: #5b716b !important; }
    .section-header {
        color: #0d9488 !important;
        border-bottom: 2px solid #0d9488 !important;
    }
    .hub-card { border-top: 4px solid #0d9488 !important; }
    .hub-card h3 { color: #134e4a !important; }
    .fe-topbar { background: linear-gradient(90deg, #0f766e, #0d9488) !important; }
    .fe-titlebar {
        background: #e6f6f2 !important;
        border: 1px solid #c5d5d2 !important;
        color: #134e4a !important;
    }
    .fe-table-head,
    .fe-table-head-noref {
        background: #e6f6f2 !important;
        border: 1px solid #c5d5d2 !important;
    }

    /* Consistent white entry fields with a thin border */
    div[data-testid="stTextInput"],
    div[data-testid="stNumberInput"],
    div[data-testid="stDateInput"],
    div[data-testid="stTextArea"],
    div[data-testid="stMultiselect"],
    div[data-testid="stSelectbox"] {
        max-width: 260px !important;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stTextArea"] textarea {
        background-color: #ffffff !important;
        color: #134e4a !important;
        border: 1px solid #c5d5d2 !important;
        border-radius: 4px !important;
        min-height: 30px;
        font-size: 12px;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #c5d5d2 !important;
        border-radius: 4px !important;
        min-height: 30px;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div span {
        font-size: 12px;
    }
    div[data-testid="stMultiselect"] div[data-baseweb="tag"] {
        background: #e6f6f2 !important;
        border: 1px solid #c5d5d2 !important;
    }

    /* Focus effect - teal */
    div[data-testid="stTextInput"]:focus-within input,
    div[data-testid="stNumberInput"]:focus-within input,
    div[data-testid="stDateInput"]:focus-within input,
    div[data-testid="stTextArea"]:focus-within textarea,
    div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div,
    div[data-testid="stMultiselect"]:focus-within {
        border-color: #0d9488 !important;
        box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.18) !important;
    }

    /* Consistent compact labels */
    [data-testid="stWidgetLabel"] {
        color: #134e4a !important;
        font-size: 0.68rem !important;
        font-weight: 600 !important;
    }

    /* Buttons - teal base (JS assigns Save=green / Update=orange / Delete=red / Clear Form=sky blue) */
    div.stButton > button[kind="primary"],
    div.stFormSubmitButton > button[kind="primary"] {
        background-color: #0d9488;
        color: #ffffff;
        border: 1px solid #0d9488;
        border-radius: 4px;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stFormSubmitButton > button[kind="primary"]:hover {
        background-color: #0f766e;
        border-color: #0f766e;
        color: #ffffff;
    }
    div.stButton > button:not([kind="primary"]),
    div.stFormSubmitButton > button:not([kind="primary"]) {
        background-color: #ffffff;
        color: #0d9488;
        border: 1px solid #0d9488;
        border-radius: 4px;
    }
    div.stButton > button:not([kind="primary"]):hover,
    div.stFormSubmitButton > button:not([kind="primary"]):hover {
        background-color: #0d9488;
        color: #ffffff;
    }
    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {
        filter: brightness(0.94);
    }

    /* Sidebar interactive controls - teal accents */
    [data-testid="stSidebar"] input[type="radio"]:checked,
    [data-testid="stSidebar"] input[type="checkbox"]:checked { accent-color: #0d9488; }

    /* Dataframe / tables - soft teal borders */
    [data-testid="stDataFrame"] {
        border: 1px solid #c5d5d2 !important;
        border-radius: 6px !important;
        overflow: hidden;
    }

    /* Dropdown controls - match the border of text/number inputs */
    div[data-testid="stSelectbox"] div[role="group"] {
        border: 1px solid rgb(197, 213, 210) !important;
        border-radius: 4px;
    }

    /* Dropdown option lists - bold items in a distinct font */
    div[data-testid="stSelectboxVirtualDropdown"] [role="option"] [data-item-hl] {
        font-family: "Trebuchet MS", "Segoe UI", sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# Color-code action buttons by label in Teal Professional pattern:
# Save=green, Update=orange, Delete=red, Clear Form=sky blue.
components.html("""
    <script>
    (function(){
      try {
        const P = window.parent.document;
        const btnMap = [
          [/\\u{1F4BE}/u, '#16a34a'],  // 💾 Save -> green
          [/\\u{270F}/u, '#f97316'],   // ✏️ Update -> orange
          [/\\u{1F5D1}/u, '#e11d48'],  // 🗑️ Delete -> red
          [/\\u{1F9F9}/u, '#0ea5e9'],  // 🧹 Clear Form -> sky blue
        ];
        P.querySelectorAll('div[data-testid="stButton"] button, button[data-testid="stButton"]').forEach(function(btn){
          const txt = (btn.textContent || '').trim();
          for (var i = 0; i < btnMap.length; i++) {
            if (btnMap[i][0].test(txt)) {
              btn.style.backgroundColor = btnMap[i][1];
              btn.style.borderColor = btnMap[i][1];
              btn.style.color = '#ffffff';
              break;
            }
          }
        });
      } catch(err) {}
    })();
    </script>
    """, height=0, width=0)

# ==============================================================================
# PAGE 1: LOGIN GATEWAY
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown("<div class='main-title'>Welcome to SUBH PAPER COMPANY</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.subheader("🔐 Secure Terminal Sign-In")
        username = st.text_input("User ID", placeholder="Enter official identity ID...")
        password = st.text_input("Password", type="password", placeholder="Enter confidential key...")
        
        if st.button("Access Dashboard", use_container_width=True, type="primary"):
            if username.strip().lower() == "admin" and password.strip() == "subh123":
                st.session_state.logged_in = True
                st.session_state.current_page = "Company Portal"
                st.rerun()
            else:
                st.error("❌ Authentication Failed: Invalid credentials sequence provided.")
    st.stop()

# ==============================================================================
# SIDEBAR CONTROL PANEL
# ==============================================================================
with st.sidebar:
    st.markdown("### 🏭 **SUBH PAPER CO.**")
    st.write("👤 User: **Admin Operator**")
    _cur_co = st.session_state.get("selected_company")
    if _cur_co:
        st.caption(f"🏢 Active Company: **{_cur_co}**")
    if st.button("🏠 Central Workspace Hub", use_container_width=True, type="primary"):
        st.session_state.current_page = "Main Hub"
        st.rerun()
    if st.button("🏢 Company Portal", use_container_width=True, type="secondary"):
        st.session_state.current_page = "Company Portal"
        st.rerun()
    st.markdown("---")
    if st.button("❌ Terminate Session", use_container_width=True, type="secondary"):
        st.session_state.logged_in = False
        st.session_state.current_page = "Main Hub"
        st.rerun()





# ---- Keyboard shortcuts: Alt+C create, Alt+D delete, Ctrl+Enter edit ----
components.html(r"""
<div id="subh_keys" style="display:none"></div>
<script>
(function(){
  try {
    var p = window.parent;
    if (p.__subhKeysHK) return;
    p.__subhKeysHK = true;
    var d = p.document;
    function norm(s){ return ('' + (s||'')).replace(/\s+/g,' ').trim(); }
    function visibles(list){
      var out=[];
      for (var i=0;i<list.length;i++){
        var e=list[i], r=e.getBoundingClientRect();
        if (r.width>0 && r.height>0 && e.offsetParent !== null) out.push(e);
      }
      return out;
    }
    function firstVisibleClick(btns, re){
      var v=visibles(btns);
      for (var i=0;i<v.length;i++){ if (re.test(norm(v[i].textContent))){ v[i].click(); return true; } }
      return false;
    }
    function contextBox(){
      var n=d.activeElement, guard=0;
      while(n && n!==d.body && guard++<10){
        if (n.getAttribute && n.getAttribute('data-testid')==='stHorizontalBlock') return n;
        n=n.parentElement;
      }
      return null;
    }
    function contextualDelete(){
      var box=contextBox();
      if (box && firstVisibleClick(box.querySelectorAll('button'), /^🗑 Delete$/)) return true;
      if (box && firstVisibleClick(box.querySelectorAll('button'), /^🗑$/)) return true;
      if (firstVisibleClick(d.querySelectorAll('button'), /^🗑 Delete$/)) return true;
      return false;
    }
    function contextualEdit(){
      var box=contextBox();
      if (box && firstVisibleClick(box.querySelectorAll('button'), /^✏️ Edit$/)) return true;
      if (box && firstVisibleClick(box.querySelectorAll('button'), /^↩ Open/)) return true;
      if (firstVisibleClick(d.querySelectorAll('button'), /^✏️ Edit$/)) return true;
      return false;
    }
    function focusLedgerName(){
      var inx=d.querySelector('input[aria-label="Ledger Name"], textarea[aria-label="Ledger Name"]');
      if (inx){ inx.focus(); return true; }
      return false;
    }
    function createFlow(){
      if (firstVisibleClick(d.querySelectorAll('button'), /^➕ Add /)) return true;
      var sums=visibles(d.querySelectorAll('summary'));
      for (var i=0;i<sums.length;i++){
        if (norm(sums[i].textContent).indexOf('Create Ledger')>=0){
          var dt=sums[i].parentElement;
          if (dt && dt.tagName==='DETAILS' && !dt.open){ sums[i].click(); }
          focusLedgerName();
          return true;
        }
      }
      var heads=visibles(d.querySelectorAll('button'));
      for (var j=0;j<heads.length;j++){
        if (norm(heads[j].textContent).indexOf('Create Ledger')>=0){
          if (focusLedgerName()) return true;
          heads[j].click();
          return true;
        }
      }
      return false;
    }
    d.addEventListener('keydown', function(e){
      var lk=((e.key||e.code||'').toLowerCase());
      if (e.altKey && !e.ctrlKey && !e.metaKey && (lk==='c')){
        if (createFlow()){ if (e.preventDefault) e.preventDefault(); }
        return;
      }
      if ((e.altKey && !e.metaKey) && (lk==='d' || lk==='delete')){
        if (contextualDelete()){ if (e.preventDefault) e.preventDefault(); }
        return;
      }
      if (e.ctrlKey && !e.altKey && !e.metaKey && lk==='enter'){
        if (contextualEdit()){ if (e.preventDefault) e.preventDefault(); }
        return;
      }
    }, true);
  } catch(err) {}
})();
</script>
""", height=0)


# ==============================================================================
# TAB DISPATCH
# ==============================================================================
if st.session_state.current_page == "Company Portal":
    import page_company_portal
    page_company_portal.render()
elif st.session_state.current_page == "Main Hub":
    import page_main_hub
    page_main_hub.render()
elif st.session_state.current_page == "Master":
    import page_master
    page_master.render()
elif st.session_state.current_page == "Dashboard":
    import page_dashboard
    page_dashboard.render()
elif st.session_state.current_page == "Entry Mode":
    import page_entry
    page_entry.render()
elif st.session_state.current_page == "Financial Statement":
    import page_financial
    page_financial.render()
elif st.session_state.current_page == "Production Statement":
    import page_production
    page_production.render()
elif st.session_state.current_page == "HR Module":
    import page_hr
    page_hr.render()

# ==============================================================================
# END OF MAIN APPLICATION
# ==============================================================================
