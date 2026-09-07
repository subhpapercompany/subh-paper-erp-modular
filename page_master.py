# ==============================================================================
# PAGE MODULE: MASTER
# ==============================================================================
# Inventory & Accounting master groups.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    conn = get_db_connection()

    _master_schemas = {
        "inventory_group_master": {"group_name": "TEXT"},
        "inventory_item_master": {"group_id": "INTEGER", "item_name": "TEXT", "unit": "TEXT", "rate": "REAL", "quantity": "REAL", "amount": "REAL", "gst_applicability": "TEXT", "hsn_code": "TEXT", "gst_rate": "TEXT", "type_of_supply": "TEXT"},
        "account_group_master": {"group_name": "TEXT"},
    }
    _ledger_add_cols = {
        "group_name": "TEXT",
        "opening_balance": "REAL",
        "address": "TEXT",
        "gst_no": "TEXT",
        "mobile_no": "TEXT",
        "contact_person": "TEXT",
        "email": "TEXT",
    }
    _ledger_cols = {row[1] for row in conn.execute("PRAGMA table_info(ledger_master)").fetchall()}
    for _lc, _lct in _ledger_add_cols.items():
        if _lc not in _ledger_cols:
            conn.execute(f"ALTER TABLE ledger_master ADD COLUMN {_lc} {_lct}")
    for _t, _cols in _master_schemas.items():
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_t} (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        _existing = {row[1] for row in conn.execute(f"PRAGMA table_info({_t})").fetchall()}
        for _c, _ct in _cols.items():
            if _c not in _existing:
                conn.execute(f"ALTER TABLE {_t} ADD COLUMN {_c} {_ct}")
    for _g in ("Paper", "Board", "Consumable"):
        conn.execute(
            "INSERT INTO inventory_group_master (group_name) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM inventory_group_master WHERE group_name = ?)",
            (_g, _g),
        )
    for _g in ("Default", "Current Assets", "Bank/Cash", "Income", "Expenses", "Liabilities", "Capital"):
        conn.execute(
            "INSERT INTO account_group_master (group_name) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM account_group_master WHERE group_name = ?)",
            (_g, _g),
        )
    conn.execute("UPDATE ledger_master SET group_name = 'Default' WHERE group_name IS NULL OR group_name = ''")
    conn.execute("UPDATE ledger_master SET opening_balance = 0 WHERE opening_balance IS NULL")
    conn.execute("UPDATE inventory_item_master SET quantity = 0 WHERE quantity IS NULL")
    conn.execute("UPDATE inventory_item_master SET amount = 0 WHERE amount IS NULL")
    conn.execute("UPDATE inventory_item_master SET gst_applicability = 'Applicable' WHERE gst_applicability IS NULL")
    conn.execute("UPDATE inventory_item_master SET hsn_code = '' WHERE hsn_code IS NULL")
    conn.execute("UPDATE inventory_item_master SET gst_rate = '18' WHERE gst_rate IS NULL")
    conn.execute("UPDATE inventory_item_master SET type_of_supply = 'Goods' WHERE type_of_supply IS NULL")
    conn.commit()

    for _pfx in ("invgrp", "accgrp"):
        _pend = st.session_state.pop(f"m_{_pfx}_gsel_pending", None)
        if _pend is not None:
            st.session_state[f"m_{_pfx}_gsel"] = _pend

    st.markdown("<h2 class='section-header'>🗃️ Master Control Hub</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#7F8C8D;'>Inventory aur Accounting Masters — dono me Groups banao aur har group ke andar items / ledgers add karo.</p>", unsafe_allow_html=True)

    def _master_child_count(table_name, parent_col, parent_val):
        return conn.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE {parent_col} = ?",
            (parent_val,),
        ).fetchone()[0]

    def _master_group_manager(table_name, prefix, label):
        st.markdown(f"##### {label} — Group Create Karein")
        g1, g2 = st.columns([4, 1])
        gname = g1.text_input(f"New {label} Group", key=f"m_{prefix}_gname", placeholder=f"e.g. {label} Group")
        if g2.button("➕ Create Group", key=f"m_{prefix}_gcreate"):
            gn = gname.strip()
            if not gn:
                st.error("Group name required.")
            else:
                dup = conn.execute(
                    f"SELECT 1 FROM {table_name} WHERE LOWER(group_name) = LOWER(?)",
                    (gn,),
                ).fetchone()
                if dup:
                    st.warning("This group already exists.")
                else:
                    conn.execute(f"INSERT INTO {table_name} (group_name) VALUES (?)", (gn,))
                    conn.commit()
                    st.success(f"Group '{gn}' created.")
                    st.rerun()
        groups = conn.execute(f"SELECT id, group_name FROM {table_name} ORDER BY group_name").fetchall()
        if not groups:
            st.info("Abhi koi group nahi hai.")
            return None, []
        gl = st.selectbox(f"Select {label} Group", groups, format_func=lambda x: x[1], key=f"m_{prefix}_gsel")
        if st.button("🗑 Delete Selected Group", key=f"m_{prefix}_gdel"):
            if prefix == "invgrp":
                cnt = _master_child_count("inventory_item_master", "group_id", int(gl[0]))
            else:
                cnt = _master_child_count("ledger_master", "group_name", str(gl[1]))
            if cnt:
                st.warning("Is group ke andar records hain — pehle unhe delete karein.")
            else:
                conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (int(gl[0]),))
                conn.commit()
                st.success(f"Group '{gl[1]}' deleted.")
                st.rerun()
        return gl, groups

    def _master_child_editor(parent_col, parent_val, table_name, fields, item_label, prefix, group_options=None, group_val_kind="id", ob_supported=True):
        st.markdown(f"##### {item_label} — Add Karein")
        _dfields = [f for f in fields if f[2] != "section"]
        _colbuf = []
        params_by_col = {}

        def _flush_add():
            if not _colbuf:
                return
            _cols = st.columns(len(_colbuf))
            for _i, _f in enumerate(_colbuf):
                _col, _label, _kind = _f[0], _f[1], _f[2]
                with _cols[_i]:
                    if _kind == "calc":
                        try:
                            _amt = float(params_by_col.get(_f[3][0]) or 0.0) * float(params_by_col.get(_f[3][1]) or 0.0)
                        except Exception:
                            _amt = 0.0
                        params_by_col[_col] = _amt
                        st.text_input(_label, value=f"₹ {_amt:,.2f}", key=f"m_{prefix}_a_amount_calcbx_{_amt}")
                    elif _kind == "number":
                        params_by_col[_col] = st.number_input(_label, min_value=-9999999999.0 if _col == "opening_balance" else 0.0, value=None, step=0.01, format="%.2f", key=f"m_{prefix}_a_{_col}")
                    elif _kind == "choice":
                        params_by_col[_col] = st.selectbox(_label, list(_f[3]), key=f"m_{prefix}_a_{_col}")
                    else:
                        params_by_col[_col] = st.text_input(_label, key=f"m_{prefix}_a_{_col}")
            _colbuf.clear()

        for _f in fields:
            if _f[2] == "section":
                _flush_add()
                st.markdown(f"##### {_f[1]}")
                continue
            if len(_colbuf) >= 4:
                _flush_add()
            _colbuf.append(_f)
        _flush_add()
        grp_sel = None
        if group_options is not None:
            _gi = next((i for i, g in enumerate(group_options) if (g[0] if group_val_kind == "id" else g[1]) == parent_val), 0)
            grp_sel = st.selectbox("Assign to Group", list(group_options), format_func=lambda x: x[1], index=_gi, key=f"m_{prefix}_grp")
        if st.button(f"➕ Add {item_label}", key=f"m_{prefix}_add", type="primary"):
            _first_col = _dfields[0][0]
            first = params_by_col.get(_first_col, "")
            if first in (None, ""):
                st.error(f"{_dfields[0][1]} is required.")
            else:
                parent_actual = parent_val
                if grp_sel is not None:
                    parent_actual = grp_sel[0] if group_val_kind == "id" else grp_sel[1]
                _colvals = {}
                for f in _dfields:
                    _col, label, kind = f[0], f[1], f[2]
                    v = params_by_col.get(_col)
                    if kind == "number":
                        _colvals[_col] = float(v) if v is not None else 0.0
                    elif kind == "calc":
                        _colvals[_col] = float(_colvals.get(f[3][0]) or 0.0) * float(_colvals.get(f[3][1]) or 0.0)
                    else:
                        _colvals[_col] = str(v if v is not None else "")
                cols_q = [parent_col] + [f[0] for f in _dfields]
                vals = [parent_actual] + [_colvals[f[0]] for f in _dfields]
                conn.execute(
                    f"INSERT INTO {table_name} ({','.join(cols_q)}) VALUES ({','.join('?' for _ in cols_q)})",
                    vals,
                )
                conn.commit()
                if grp_sel is not None:
                    st.session_state[f"m_{prefix}_gsel_pending"] = grp_sel
                st.success(f"'{first}' add ho gaya.")
                st.rerun()
        rows = conn.execute(
            f"SELECT id, {','.join(f[0] for f in _dfields)} FROM {table_name} WHERE {parent_col} = ? ORDER BY id DESC",
            (parent_val,),
        ).fetchall()
        if not rows:
            st.info(f"Is group me abhi koi {item_label} nahi.")
            return
        st.dataframe(
            pd.DataFrame(rows, columns=["ID"] + [f[1] for f in _dfields]),
            use_container_width=True,
            hide_index=True,
        )
        sel = st.selectbox(
            f"Select {item_label} (Edit / Delete)",
            [(r[0], f"ID {r[0]} — {r[1]}") for r in rows],
            format_func=lambda x: x[1],
            key=f"m_{prefix}_sel",
        )
        if ob_supported:
            d1, d2, d3 = st.columns(3)
        else:
            d1, d2 = st.columns(2)
        with d1:
            if st.button("🗑 Delete", key=f"m_{prefix}_del", use_container_width=True):
                conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (int(sel[0]),))
                conn.commit()
                st.session_state.pop(f"m_{prefix}_edit_id", None)
                st.session_state.pop(f"m_{prefix}_ob_edit", None)
                st.success("Deleted.")
                st.rerun()
        with d2:
            if st.button("✏️ Edit", key=f"m_{prefix}_edit", use_container_width=True):
                st.session_state[f"m_{prefix}_edit_id"] = sel[0]
                st.session_state.pop(f"m_{prefix}_ob_edit", None)
                st.rerun()
        if ob_supported:
            with d3:
                if st.button("💹 Update Opening Balance", key=f"m_{prefix}_ob", use_container_width=True):
                    st.session_state[f"m_{prefix}_ob_edit"] = sel[0]
                    st.session_state.pop(f"m_{prefix}_edit_id", None)
                    st.rerun()
        if st.session_state.get(f"m_{prefix}_edit_id") == sel[0]:
            row = conn.execute(
                f"SELECT {','.join(f[0] for f in _dfields)} FROM {table_name} WHERE id = ?",
                (int(sel[0]),),
            ).fetchone()
            if row:
                st.caption("✏️ Edit selected — nayi values bharo:")
                newvals_by_col = {}
                _colbuf2 = []
                _rowidx = {f[0]: i for i, f in enumerate(_dfields)}

                def _flush_edit():
                    if not _colbuf2:
                        return
                    _cols = st.columns(len(_colbuf2))
                    for _i, _f in enumerate(_colbuf2):
                        _col, _label, _kind = _f[0], _f[1], _f[2]
                        _idx = _rowidx[_col]
                        with _cols[_i]:
                            if _kind == "calc":
                                try:
                                    _amt = float(newvals_by_col.get(_f[3][0]) or 0.0) * float(newvals_by_col.get(_f[3][1]) or 0.0)
                                except Exception:
                                    _amt = 0.0
                                newvals_by_col[_col] = _amt
                                st.text_input(_label, value=f"₹ {_amt:,.2f}", key=f"m_{prefix}_e_amount_calcbx_{_amt}")
                            elif _kind == "number":
                                newvals_by_col[_col] = st.number_input(_label, min_value=-9999999999.0 if _col == "opening_balance" else 0.0, value=float(row[_idx] or 0), step=0.01, format="%.2f", key=f"m_{prefix}_e_{_col}")
                            elif _kind == "choice":
                                cur = "" if row[_idx] is None else str(row[_idx])
                                options = list(_f[3])
                                newvals_by_col[_col] = st.selectbox(_label, options, index=options.index(cur) if cur in options else 0, key=f"m_{prefix}_e_{_col}")
                            else:
                                newvals_by_col[_col] = st.text_input(_label, value="" if row[_idx] is None else str(row[_idx]), key=f"m_{prefix}_e_{_col}")
                    _colbuf2.clear()

                for _f in fields:
                    if _f[2] == "section":
                        _flush_edit()
                        st.markdown(f"##### {_f[1]}")
                        continue
                    if len(_colbuf2) >= 4:
                        _flush_edit()
                    _colbuf2.append(_f)
                _flush_edit()
                if st.button("💾 Save Update", type="primary", key=f"m_{prefix}_upd"):
                    _uvals = []
                    for f in _dfields:
                        _col, label, kind = f[0], f[1], f[2]
                        v = newvals_by_col.get(_col)
                        if kind == "number":
                            _uvals.append(float(v) if v is not None else 0.0)
                        elif kind == "calc":
                            _uvals.append(float(newvals_by_col.get(f[3][0]) or 0.0) * float(newvals_by_col.get(f[3][1]) or 0.0))
                        else:
                            _uvals.append(str(v if v is not None else ""))
                    assigns = ", ".join(f"{f[0]} = ?" for f in _dfields)
                    conn.execute(
                        f"UPDATE {table_name} SET {assigns} WHERE id = ?",
                        _uvals + [int(sel[0])],
                    )
                    conn.commit()
                    st.session_state.pop(f"m_{prefix}_edit_id", None)
                    st.success("Updated.")
                    st.rerun()

        if ob_supported and st.session_state.get(f"m_{prefix}_ob_edit") == sel[0]:
            ob_row = conn.execute(f"SELECT opening_balance FROM {table_name} WHERE id = ?", (int(sel[0]),)).fetchone()
            if ob_row is not None:
                st.caption("💹 Opening Balance correction karein:")
                o1, o2 = st.columns([4, 1])
                newob = o1.number_input("Opening Balance", min_value=-9999999999.0, value=float(ob_row[0] or 0), step=0.01, format="%.2f", key=f"m_{prefix}_ob_in")
                if o2.button("💾 Save Opening Balance", type="primary", key=f"m_{prefix}_ob_save"):
                    conn.execute(f"UPDATE {table_name} SET opening_balance = ? WHERE id = ?", (float(newob), int(sel[0])))
                    conn.commit()
                    st.session_state.pop(f"m_{prefix}_ob_edit", None)
                    st.success("Opening Balance updated.")
                    st.rerun()

    inv_tab, acc_tab = st.tabs(["📦 Inventory Master", "🧮 Accounting Master"])
    with inv_tab:
        sel_inv, _groups_inv = _master_group_manager("inventory_group_master", "invgrp", "Inventory")
        if sel_inv:
            st.markdown("---")
            _master_child_editor(
                "group_id",
                int(sel_inv[0]),
                "inventory_item_master",
                [("item_name", "Item Name", "text"), ("unit", "Unit of Measurement", "choice", ["Kg", "Sheet", "Nos", "Pcs"]), ("__section__", "Statutory Detail", "section"), ("gst_applicability", "GST Applicability", "choice", ["Applicable", "Not Applicable"]), ("hsn_code", "HSN/SAC Code", "text"), ("gst_rate", "GST Rate", "choice", ["3", "5", "12", "18", "28"]), ("type_of_supply", "Type of Supply", "choice", ["Goods", "services", "Capital Goods"]), ("quantity", "Opening Quantity", "number"), ("rate", "Rate", "number"), ("amount", "Amount", "calc", ("rate", "quantity"))],
                "Inventory Item",
                "invgrp",
                group_options=_groups_inv,
                group_val_kind="id",
                ob_supported=False,
            )
    with acc_tab:
        sel_acc, _groups_acc = _master_group_manager("account_group_master", "accgrp", "Accounting")
        if sel_acc:
            st.markdown("---")
            _master_child_editor(
                "group_name",
                str(sel_acc[1]),
                "ledger_master",
                [("ledger_name", "Ledger Name", "text"),
                 ("contact_person", "Contact Person", "text"),
                 ("mobile_no", "Mobile No.", "text"),
                 ("email", "Email", "text"),
                 ("address", "Address", "text"),
                 ("gst_no", "GST No.", "text"),
                 ("opening_balance", "Opening Balance", "number")],
                "Ledger",
                "accgrp",
                group_options=_groups_acc,
                group_val_kind="name",
            )
