# ==============================================================================
# PAGE MODULE: COMPANY PORTAL
# ==============================================================================
# Company create / update / select portal.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    st.markdown("<h2 style='text-align: center; color: #2C3E50; font-weight:bold;'>🏢 Company Management Portal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7F8C8D; margin-bottom: 20px;'>Company create, update aur select — sab yahin se manage karein.</p>", unsafe_allow_html=True)
    cp_conn = get_db_connection()
    _cp_schema = {
        "company_name": "TEXT", "gst_no": "TEXT", "address": "TEXT", "city": "TEXT",
        "state": "TEXT", "country": "TEXT", "pincode": "TEXT", "phone": "TEXT",
        "pan_no": "TEXT", "tan_no": "TEXT", "contact_person": "TEXT",
        "financial_year_from": "TEXT", "financial_year_to": "TEXT", "books_from": "TEXT",
        "created_on": "TEXT",
    }
    _cp_schema.update({
        "address1": "TEXT", "address2": "TEXT", "telephone": "TEXT", "mobile_no": "TEXT",
        "website": "TEXT", "currency_symbol": "TEXT", "currency_formal_name": "TEXT",
        "company_data_path": "TEXT",
    })
    cp_conn.execute("CREATE TABLE IF NOT EXISTS company_master (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    _cp_existing = {row[1] for row in cp_conn.execute("PRAGMA table_info(company_master)").fetchall()}
    for _cp_c, _cp_t in _cp_schema.items():
        if _cp_c not in _cp_existing:
            cp_conn.execute(f"ALTER TABLE company_master ADD COLUMN {_cp_c} {_cp_t}")
    cp_conn.commit()
    INDIA_STATES = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
        "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
        "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
        "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
        "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman & Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli and Daman & Diu",
        "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    ]
    _cp_fnonce = st.session_state.get("cp_form_nonce", 0)
    cp_tab1, cp_tab2, cp_tab3 = st.tabs(["1. Select Company", "2. Create Company", "3. Alter / Delete Company"])

    with cp_tab1:
        st.markdown("##### ✅ Select Company — Upar Kaam Shuru Karein")
        _sl_list = cp_conn.execute("SELECT id, company_name FROM company_master ORDER BY company_name").fetchall()
        if not _sl_list:
            st.info("Koi company available nahi hai. Pehle 'Create Company' tab me company banao.")
        for _co_id, _co_name in _sl_list:
            r1, r2 = st.columns([5, 1])
            with r1:
                st.markdown(f"<div style='border:1px solid #CBD5E1;border-radius:8px;padding:10px 14px;background:#F8FAFC;'><b>🏢 {html.escape(str(_co_name))}</b></div>", unsafe_allow_html=True)
            with r2:
                if st.button("Select", key=f"cp_sel_{_co_id}", use_container_width=True, type="primary"):
                    st.session_state.selected_company = str(_co_name)
                    st.session_state.selected_company_id = int(_co_id)
                    st.session_state.current_page = "Main Hub"
                    st.rerun()

    with cp_tab2:
        st.markdown("##### 🆕 Create Company")
        c1, c2 = st.columns(2)
        with c1:
            _cc_name = st.text_input("Company Name", key=f"cp_cre_company_name_{_cp_fnonce}")
            _cc_addr1 = st.text_input("Address 1", key=f"cp_cre_address1_{_cp_fnonce}")
            _cc_state = st.selectbox("State", INDIA_STATES, index=None, placeholder="Select State", key=f"cp_cre_state_{_cp_fnonce}")
            _cc_country = st.text_input("Country", value="India", key=f"cp_cre_country_{_cp_fnonce}")
            _cc_pin = st.text_input("Pin Code", key=f"cp_cre_pincode_{_cp_fnonce}")
            _cc_tele = st.text_input("Telephone", key=f"cp_cre_telephone_{_cp_fnonce}")
        with c2:
            _cc_addr2 = st.text_input("Address 2", key=f"cp_cre_address2_{_cp_fnonce}")
            _cc_mob = st.text_input("Mobile No.", key=f"cp_cre_mobile_no_{_cp_fnonce}")
            _cc_email = st.text_input("Email", key=f"cp_cre_email_{_cp_fnonce}")
            _cc_web = st.text_input("Website", key=f"cp_cre_website_{_cp_fnonce}")
        st.markdown("##### 💱 Currency")
        cu1, cu2 = st.columns(2)
        with cu1:
            _cc_cur_sym = st.text_input("Basic Currency Symbol", key=f"cp_cre_currency_symbol_{_cp_fnonce}")
        with cu2:
            _cc_cur_name = st.text_input("Formal Name", value="INR", key=f"cp_cre_currency_formal_name_{_cp_fnonce}")
        st.markdown("##### 📅 Financial Year & Books")
        fy1, fy2 = st.columns(2)
        with fy1:
            _cc_fy_from = st.text_input("Financial Year Beginning From (DD/MM/YYYY)", key=f"cp_cre_fy_from_{_cp_fnonce}")
        with fy2:
            _cc_books = st.text_input("Books Beginning From (DD/MM/YYYY)", key=f"cp_cre_books_from_{_cp_fnonce}")
        _cc_path = st.text_input("Company Data Path", key=f"cp_cre_data_path_{_cp_fnonce}")
        if st.button("➕ Create Company", type="primary", use_container_width=True, key="cp_cre_save"):
            if not (_cc_name or "").strip():
                st.error("Company Name is required.")
            else:
                cp_conn.execute(
                    "INSERT INTO company_master (company_name, address1, address2, state, country, pincode, telephone, mobile_no, email, website, currency_symbol, currency_formal_name, financial_year_from, books_from, company_data_path, created_on) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (_cc_name.strip(), _cc_addr1, _cc_addr2, _cc_state or "", _cc_country or "India", _cc_pin, _cc_tele, _cc_mob, _cc_email, _cc_web, _cc_cur_sym, _cc_cur_name or "INR", _cc_fy_from, _cc_books, _cc_path, datetime.date.today().strftime('%d/%m/%Y')),
                )
                cp_conn.commit()
                st.session_state.cp_form_nonce = _cp_fnonce + 1
                for _k in list(st.session_state):
                    if _k.startswith("cp_cre_"):
                        st.session_state.pop(_k, None)
                st.success(f"Company '{_cc_name.strip()}' create ho gayi.")
                st.rerun()

    with cp_tab3:
        st.markdown("##### 🔧 Alter / Delete Company")
        _cc_list = cp_conn.execute("SELECT id, company_name FROM company_master ORDER BY company_name").fetchall()
        if not _cc_list:
            st.info("Koi company nahi hai. Pehle 'Create Company' tab me company banao.")
        else:
            cid = st.selectbox("Select Company to Alter / Delete", _cc_list, format_func=lambda x: x[1], key="cp_alt_csel")
            _valid_ids = {int(c[0]) for c in _cc_list}
            if cid is None or int(cid[0]) not in _valid_ids:
                st.session_state.pop("cp_alt_csel", None)
                st.rerun()
            _row = cp_conn.execute("SELECT company_name, address1, address2, state, country, pincode, telephone, mobile_no, email, website, currency_symbol, currency_formal_name, financial_year_from, books_from, company_data_path FROM company_master WHERE id = ?", (int(cid[0]),)).fetchone()
            if _row is None:
                st.session_state.pop("cp_alt_csel", None)
                st.error("Company data load nahi ho saka. Dobara select karein.")
                st.rerun()
            _state_idx = None
            if _row[3]:
                try:
                    _state_idx = INDIA_STATES.index(_row[3])
                except ValueError:
                    _state_idx = None
            a1, a2 = st.columns(2)
            with a1:
                _up_name = st.text_input("Company Name", value=_row[0], key=f"cp_alt_{cid[0]}_name")
                _up_addr1 = st.text_input("Address 1", value=_row[1], key=f"cp_alt_{cid[0]}_address1")
                _up_state = st.selectbox("State", INDIA_STATES, index=_state_idx, placeholder="Select State", key=f"cp_alt_{cid[0]}_state")
                _up_country = st.text_input("Country", value=_row[4] or "India", key=f"cp_alt_{cid[0]}_country")
                _up_pin = st.text_input("Pin Code", value=_row[5], key=f"cp_alt_{cid[0]}_pincode")
                _up_tele = st.text_input("Telephone", value=_row[6], key=f"cp_alt_{cid[0]}_telephone")
            with a2:
                _up_addr2 = st.text_input("Address 2", value=_row[2], key=f"cp_alt_{cid[0]}_address2")
                _up_mob = st.text_input("Mobile No.", value=_row[7], key=f"cp_alt_{cid[0]}_mobile_no")
                _up_email = st.text_input("Email", value=_row[8], key=f"cp_alt_{cid[0]}_email")
                _up_web = st.text_input("Website", value=_row[9], key=f"cp_alt_{cid[0]}_website")
            st.markdown("##### 💱 Currency")
            cu1, cu2 = st.columns(2)
            with cu1:
                _up_cur_sym = st.text_input("Basic Currency Symbol", value=_row[10], key=f"cp_alt_{cid[0]}_currency_symbol")
            with cu2:
                _up_cur_name = st.text_input("Formal Name", value=_row[11] or "INR", key=f"cp_alt_{cid[0]}_currency_formal_name")
            st.markdown("##### 📅 Financial Year & Books")
            fy1, fy2 = st.columns(2)
            with fy1:
                _up_fy_from = st.text_input("Financial Year Beginning From (DD/MM/YYYY)", value=_row[12], key=f"cp_alt_{cid[0]}_fy_from")
            with fy2:
                _up_books = st.text_input("Books Beginning From (DD/MM/YYYY)", value=_row[13], key=f"cp_alt_{cid[0]}_books_from")
            _up_path = st.text_input("Company Data Path", value=_row[14], key=f"cp_alt_{cid[0]}_data_path")
            if st.button("💾 Save Company Changes", type="primary", use_container_width=True, key="cp_alt_save"):
                if not (_up_name or "").strip():
                    st.error("Company Name is required.")
                else:
                    cp_conn.execute(
                        "UPDATE company_master SET company_name=?, address1=?, address2=?, state=?, country=?, pincode=?, telephone=?, mobile_no=?, email=?, website=?, currency_symbol=?, currency_formal_name=?, financial_year_from=?, books_from=?, company_data_path=? WHERE id=?",
                        (_up_name.strip(), _up_addr1, _up_addr2, _up_state or "", _up_country or "India", _up_pin, _up_tele, _up_mob, _up_email, _up_web, _up_cur_sym, _up_cur_name or "INR", _up_fy_from, _up_books, _up_path, int(cid[0])),
                    )
                    cp_conn.commit()
                    st.success("Company updated.")
                    st.rerun()
            st.divider()
            _del_cid = int(cid[0])
            st.markdown("##### 🗑️ Delete Company")
            if st.session_state.get("cp_del_confirm_cid") != _del_cid:
                st.caption(f"**{_row[0]}** ko permanently delete karein.")
                if st.button("🗑️ Delete This Company", use_container_width=True, key="cp_del_btn"):
                    st.session_state.cp_del_confirm_cid = _del_cid
                    st.rerun()
            else:
                st.warning(f"Kya aap **{_row[0]}** ko delete karna chahte hain? Ye action wapas nahi hoga.")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("✅ Haan, Delete Karo", type="primary", use_container_width=True, key="cp_del_yes"):
                        cp_conn.execute("DELETE FROM company_master WHERE id = ?", (_del_cid,))
                        cp_conn.commit()
                        st.session_state.cp_del_confirm_cid = None
                        if st.session_state.get("selected_company_id") == _del_cid:
                            st.session_state.pop("selected_company", None)
                            st.session_state.pop("selected_company_id", None)
                        st.success("Company delete ho gayi.")
                        st.rerun()
                with dc2:
                    if st.button("❌ Cancel", use_container_width=True, key="cp_del_no"):
                        st.session_state.cp_del_confirm_cid = None
                        st.rerun()
