# ==============================================================================
# PAGE MODULE: ENTRY MODE
# ==============================================================================
# Financial Entry (Payment/Receipt/Contra/Sale/Purchase/JV/All)
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *

@st.cache_data(ttl=8, show_spinner=False)
def _fetch_recent_entries_cached(table_name, limit=50):
    """Cached read of the most recent rows for the crud panels.

    Turso har query ko network round-trip banata hai, isliye bar-bar kheenchne
    ki bajaye 8s TTL ke saath cache karte hain. Har save ke baad clear() ki
    jati hai taaki nayi entry turant dikhe.
    """
    _conn = get_db_connection(private=True)
    try:
        _cols = [row[1] for row in _conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        date_col = next((c for c in ("entry_date", "po_date", "production_date", "despatch_date") if c in _cols), None)
        if date_col:
            return _conn.execute(
                f"SELECT * FROM {table_name} ORDER BY {date_col} ASC, id ASC LIMIT ?", (limit,)
            ).fetchall()
        return _conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    finally:
        try:
            _conn.close()
        except Exception:
            pass

@st.cache_data(ttl=8, show_spinner=False)
def _sale_item_options_cached():
    """Sale/Purchase item dropdown options (product codes + inventory/consumable items)."""
    opts = []
    _c = get_db_connection(private=True)
    try:
        try:
            pcs = _c.execute(
                "SELECT DISTINCT product_code FROM po_released_entries "
                "WHERE product_code IS NOT NULL AND TRIM(product_code)<>''"
            ).fetchall()
            for (code,) in pcs:
                code = str(code).strip()
                if code and code not in opts:
                    opts.append(code)
        except Exception:
            pass
        try:
            for (nm,) in _c.execute(
                "SELECT item_name FROM inventory_item_master "
                "WHERE item_name IS NOT NULL AND TRIM(item_name)<>'' ORDER BY item_name"
            ).fetchall():
                nm = str(nm).strip()
                if nm and nm not in opts:
                    opts.append(nm)
        except Exception:
            pass
        try:
            for (nm,) in _c.execute(
                "SELECT item_name FROM consumable_item_master "
                "WHERE item_name IS NOT NULL AND TRIM(item_name)<>'' ORDER BY item_name"
            ).fetchall():
                nm = str(nm).strip()
                if nm and nm not in opts:
                    opts.append(nm)
        except Exception:
            pass
        try:
            for (nm,) in _c.execute(
                "SELECT DISTINCT item_name FROM consumable_cf_entries "
                "WHERE item_name IS NOT NULL AND TRIM(item_name)<>'' ORDER BY item_name"
            ).fetchall():
                nm = str(nm).strip()
                if nm and nm not in opts:
                    opts.append(nm)
        except Exception:
            pass
    finally:
        try:
            _c.close()
        except Exception:
            pass
    return opts

@st.cache_data(ttl=8, show_spinner=False)
def _sale_item_meta_cached(name, order_month_str):
    name = str(name or "").strip()
    meta = {"name": name, "hsn": "", "tax": "", "rate": 0.0, "unit": ""}
    _c = get_db_connection(private=True)
    try:
        inv_row = None
        try:
            inv_row = _c.execute(
                "SELECT hsn_code, gst_rate, rate, unit FROM inventory_item_master "
                "WHERE item_name = ? LIMIT 1",
                (name,),
            ).fetchone()
        except Exception:
            pass
        if inv_row:
            meta.update({"hsn": str(inv_row[0] or "").strip(), "tax": str(inv_row[1] or "18").strip(),
                         "rate": float(inv_row[2] or 0), "unit": str(inv_row[3] or "").strip()})
        try:
            prow = _c.execute(
                "SELECT po_rate FROM po_released_entries "
                "WHERE product_code = ? AND order_month = ? ORDER BY id DESC LIMIT 1",
                (name, order_month_str),
            ).fetchone()
        except Exception:
            prow = None
        if prow:
            meta["rate"] = float(prow[0] or 0)
    finally:
        try:
            _c.close()
        except Exception:
            pass
    return meta

def render():
    st.markdown("<h2 class='section-header'>📝 Production Line Multi-Module Data Entry Register</h2>", unsafe_allow_html=True)
    st.markdown("""
    <style>
    /* Entry Mode: keep fields editable and remove number-input +/- controls. */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    div[data-testid="stNumberInput"] input {
        padding-right: 0.5rem !important;
    }

    /* Entry Mode: uniform field sizes and column-wise alignment. */
    div[data-testid="stColumn"] {
        display: flex;
        flex-direction: column;
        align-items: stretch;
    }
    div[data-testid="stColumn"] [data-testid="stWidgetLabel"] {
        min-height: 1.2rem;
        margin-bottom: 2px;
    }
    div[data-testid="stColumn"] [data-testid="stWidgetLabel"] p {
        font-size: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    div[data-testid="stColumn"] div[data-baseweb="input"] {
        width: 100%;
        max-width: 100%;
        min-height: 2.4rem;
        border: 1px solid rgba(49, 51, 63, 0.25) !important;
        border-radius: 6px;
    }
    div[data-testid="stColumn"] div[data-baseweb="select"] > div {
        width: 100%;
        min-height: 2.4rem;
        border: 1px solid rgba(49, 51, 63, 0.25) !important;
        border-radius: 6px;
    }
    div[data-testid="stColumn"] div[data-testid="stSelectbox"],
    div[data-testid="stColumn"] div[data-testid="stSelectbox"] > div {
        max-width: none !important;
        width: 100% !important;
    }
    div[data-testid="stColumn"] div[data-testid="stSelectbox"] {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    div[data-testid="stColumn"] div[data-testid="stMarkdown"] .fe-sale-bal-row {
        margin-top: 3px !important;
        line-height: 1.15;
    }
    div[data-testid="stColumn"] [data-testid="stElementContainer"]:has([data-testid="stMarkdown"] .fe-sale-bal-row) {
        margin-top: -15px !important;
        margin-bottom: 0 !important;
    }
    .fe-item-head {
        display: flex;
        align-items: center;
        width: 100%;
        margin-top: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 700;
        color: #134e4a;
        background: #e6f6f2;
        border: 1px solid #c5d5d2;
        border-radius: 4px;
        white-space: nowrap;
    }
    .fe-sale-amt-box {
        margin-top: 2px;
        padding: 5px 10px;
        font-size: 13px;
        font-weight: 700;
        color: #0f172a;
        background: #ffffff;
        border: 1px solid #94a3b8;
        border-radius: 6px;
        text-align: right;
        white-space: nowrap;
    }
    .fe-sale-editing-badge {
        display: inline-block;
        margin-top: 8px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 700;
        color: #92400e;
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 6px;
        white-space: nowrap;
    }
    div[data-testid="stColumn"] [data-testid="stElementContainer"]:has([data-testid="stMarkdown"] .fe-item-head) {
        margin-top: -8px !important;
        margin-bottom: 0 !important;
    }
    .fe-item-head span.c { flex: 0 1 auto; }
    .fe-item-row {
        display: flex;
        align-items: center;
        width: 100%;
        margin-top: 4px;
        padding: 3px 10px;
        gap: 6px;
        font-size: 12px;
    }
    .fe-item-row > div { min-width: 0; }
    .fe-item-fld.fe-amt {
        justify-content: center;
        text-align: center;
        font-weight: 700;
        color: #0f172a;
        white-space: nowrap;
    }
    .fe-item-row input {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        border-bottom: 1px solid #94a3b8 !important;
        border-radius: 0 !important;
        font-size: 12px !important;
        color: #0f172a !important;
    }
    .fe-item-fld {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 2px 8px !important;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        color: #0f172a;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    div[data-testid="stHorizontalBlock"]:has(.fe-item-fld) [data-testid="stNumberInput"] {
        height: 30px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.fe-item-fld) [data-testid="stNumberInput"] input {
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 6px !important;
        text-align: center !important;
    }
    .fe-summary {
        margin-left: auto;
        margin-top: 10px;
        width: fit-content;
        min-width: 360px;
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 12px;
    }
    .fe-summary .fe-sum-row {
        display: flex;
        justify-content: space-between;
        gap: 40px;
        padding: 2px 0;
    }
    .fe-summary .fe-sum-total {
        border-top: 1px solid #94a3b8;
        margin-top: 4px;
        padding-top: 5px;
        font-weight: 700;
        font-size: 13px;
        color: #134e4a;
    }
    .fe-summary .fe-sum-amt {
        color: #0f172a;
        white-space: nowrap;
    }
    div[data-testid="stColumn"] [data-testid="stInput"] input,
    div[data-testid="stColumn"] input[type="text"],
    div[data-testid="stColumn"] input[type="number"] {
        height: 2.4rem;
        min-height: 2.4rem !important;
    }

    /* Entry Mode selector dropdown: bold items in a distinct font. */
    div[data-testid="stSelectboxVirtualDropdown"] [role="option"] [data-item-hl] {
        font-family: "Trebuchet MS", "Segoe UI", sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px;
    }

    /* Compact Save/Load/Delete action bar (1"–1.5" widgets). */
    div[data-testid="stColumn"] button[data-testid="stBaseButton-secondary"],
    div[data-testid="stColumn"] button[kind="primary"] {
        height: 30px;
        min-height: 30px !important;
        padding: 0 10px !important;
        font-size: 12px !important;
        border-radius: 5px !important;
    }
    div[data-testid="stColumn"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 30px !important;
        height: 30px !important;
    }
    div[data-testid="stColumn"] [data-testid="stSelectbox"] input {
        font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    render_financial_year_control()
    
    modules_list = [
        "Select Entry Mode",
        "1. Purchase Order Form", "2. PO Request Form", "3. PO Released Form",
        "4. Production Form", "5. Despatch Form", "6. Paper Detail",
        "7. Board Detail", "8. Financial Entry", "9. Consumable / CF Entry"
    ]
    with st.container(border=True):
        chosen_module = st.selectbox(
            "Select Target Enterprise Entry Interface Node:",
            modules_list,
            index=0,
            key="entry_mode_selector"
        )
    month_options = get_month_only_options()
    conn = get_db_connection(private=True)
    
    def ensure_tables(conn):
        schemas = {
            "consumable_cf_entries": {
                "entry_date": "TEXT",
                "in_out": "TEXT",
                "item_name": "TEXT",
                "quantity": "REAL",
                "min_label": "REAL",
                "remarks": "TEXT",
            },
            "order_entries": {
                "module_name": "TEXT",
                "order_month": "TEXT",
                "product_code": "TEXT",
                "ruling_type": "TEXT",
                "no_of_page": "TEXT",
                "product_size": "TEXT",
                "order_qty": "INTEGER",
                "production_date": "TEXT",
                "production_qty": "INTEGER",
                "rejection_qty": "INTEGER",
                "ok_notebook": "INTEGER",
                "case_quantity": "INTEGER",
                "making_rate": "REAL",
                "making_charges": "REAL",
                "book_weight": "REAL",
                "paper_consumption": "REAL",
                "board_size": "TEXT",
                "board_consumption": "REAL",
            },
            "po_request_entries": {
                "request_date": "TEXT",
                "request_month": "TEXT",
                "product_code": "TEXT",
                "ruling_type": "TEXT",
                "page": "TEXT",
                "book_size": "TEXT",
                "request_qty": "TEXT",
                "remarks": "TEXT",
                "po_month": "TEXT",
                "po_date": "TEXT",
                "mrp": "REAL",
                "order_qty": "INTEGER",
                "produced_qty": "INTEGER",
                "paper_rate": "REAL",
                "tax_paper": "REAL",
                "current_paper_cost": "REAL",
                "mill_paper": "TEXT",
                "board_rate": "REAL",
                "tax_board": "REAL",
                "current_board_cost": "REAL",
                "mill_board": "TEXT",
                "lamination_type": "TEXT",
            },
            "po_released_entries": {
                "release_date": "TEXT",
                "order_month": "TEXT",
                "product_code": "TEXT",
                "ruling_type": "TEXT",
                "page": "TEXT",
                "book_size": "TEXT",
                "released_qty": "TEXT",
                "mill": "TEXT",
                "remarks": "TEXT",
                "po_rate": "REAL",
                "destination": "TEXT",
                "po_number": "TEXT",
                "po_date": "TEXT",
            },
            "production_form_entries": {
                "production_date": "TEXT",
                "production_month": "TEXT",
                "product_code": "TEXT",
                "ruling_type": "TEXT",
                "page": "TEXT",
                "book_size": "TEXT",
                "plan_qty": "TEXT",
                "ok_notebook": "TEXT",
                "rejection_qty": "TEXT",
                "case_quantity": "TEXT",
                "making_rate": "REAL",
                "making_charges": "REAL",
                "book_weight": "REAL",
                "wip_type": "TEXT",
                "wip_board": "TEXT",
                "paper_consumption": "REAL",
                "board_size": "TEXT",
                "board_consumption": "REAL",
                "book_wt_index": "REAL",
                "index_consumption": "REAL",
                "remarks": "TEXT",
            },
            "despatch_form_entries": {
                "despatch_date": "TEXT",
                "despatch_month": "TEXT",
                "product_code": "TEXT",
                "po_number": "TEXT",
                "destination": "TEXT",
                "product_size": "TEXT",
                "despatch_qty": "TEXT",
                "vehicle_no": "TEXT",
                "invoice_no": "TEXT",
                "remarks": "TEXT",
            },
            "paper_detail_entries": {
                "entry_mode": "TEXT",
                "entry_date": "TEXT",
                "invoice_no": "TEXT",
                "party_name": "TEXT",
                "paper_size": "TEXT",
                "opening_reel": "REAL",
                "inward_qty": "REAL",
                "inward_rate": "REAL",
                "inward_amount": "REAL",
                "process_qty": "REAL",
                "wastage": "REAL",
                "wip_paper": "REAL",
                "reel_no": "TEXT",
                "gsm": "TEXT",
                "quantity": "TEXT",
                "weight": "TEXT",
                "remarks": "TEXT",
            },
            "board_detail_entries": {
                "entry_mode": "TEXT",
                "entry_date": "TEXT",
                "invoice_no": "TEXT",
                "party_name": "TEXT",
                "godown": "TEXT",
                "board_size": "TEXT",
                "opening_stock": "REAL",
                "inward_qty": "REAL",
                "inward_rate": "REAL",
                "gst_percent": "REAL",
                "inward_amount": "REAL",
                "out_for_printing": "REAL",
                "wastage": "REAL",
                "product_code": "TEXT",
                "printed_board_received": "REAL",
                "rate": "REAL",
                "amount": "REAL",
                "consumption": "REAL",
                "reel_no": "TEXT",
                "gsm": "TEXT",
                "quantity": "TEXT",
                "weight": "TEXT",
                "remarks": "TEXT",
            },
            "voucher_entries": {
                "mode": "TEXT",
                "entry_date": "TEXT",
                "invoice_no": "TEXT",
                "dr_cr": "TEXT",
                "ledger_head": "TEXT",
                "invoice_amount": "REAL",
                "tds": "REAL",
                "net_amount": "REAL",
                "remarks": "TEXT",
                "bill_ref": "TEXT",
            },
            "ledger_master": {
                "ledger_name": "TEXT",
                "group_name": "TEXT",
                "opening_balance": "REAL",
                "address": "TEXT",
                "gst_no": "TEXT",
                "mobile_no": "TEXT",
                "contact_person": "TEXT",
                "email": "TEXT",
            },
            "inventory_group_master": {
                "group_name": "TEXT",
            },
            "inventory_item_master": {
                "group_id": "INTEGER",
                "item_name": "TEXT",
                "unit": "TEXT",
                "rate": "REAL",
                "quantity": "REAL",
                "amount": "REAL",
                "gst_applicability": "TEXT",
                "hsn_code": "TEXT",
                "gst_rate": "TEXT",
                "type_of_supply": "TEXT",
            },
            "account_group_master": {
                "group_name": "TEXT",
            },
            "company_master": {
                "company_name": "TEXT",
                "gst_no": "TEXT",
                "address": "TEXT",
                "city": "TEXT",
                "state": "TEXT",
                "country": "TEXT",
                "pincode": "TEXT",
                "phone": "TEXT",
                "email": "TEXT",
                "pan_no": "TEXT",
                "tan_no": "TEXT",
                "contact_person": "TEXT",
                "financial_year_from": "TEXT",
                "financial_year_to": "TEXT",
                "books_from": "TEXT",
                "created_on": "TEXT",
                "address1": "TEXT",
                "address2": "TEXT",
                "telephone": "TEXT",
                "mobile_no": "TEXT",
                "website": "TEXT",
                "currency_symbol": "TEXT",
                "currency_formal_name": "TEXT",
                "company_data_path": "TEXT",
            },
            "app_migrations": {
                "migration_key": "TEXT",
            },
            "voucher_inventory_items": {
                "voucher_no": "TEXT",
                "mode": "TEXT",
                "entry_date": "TEXT",
                "item_name": "TEXT",
                "unit": "TEXT",
                "qty": "REAL",
                "rate": "REAL",
                "amount": "REAL",
            },
        }

        _existing_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for table, columns in schemas.items():
            if table not in _existing_tables:
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT)")
                existing = {
                    row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
                for col, col_type in columns.items():
                    if col not in existing:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        for _drop_col in ("specification", "opening_balance"):
            _item_cols = {row[1] for row in conn.execute("PRAGMA table_info(inventory_item_master)").fetchall()}
            if _drop_col in _item_cols:
                try:
                    conn.execute(f"ALTER TABLE inventory_item_master DROP COLUMN {_drop_col}")
                except Exception:
                    pass
        conn.execute("UPDATE inventory_item_master SET gst_applicability = 'Applicable' WHERE gst_applicability IS NULL")
        conn.execute("UPDATE inventory_item_master SET hsn_code = '' WHERE hsn_code IS NULL")
        conn.execute("UPDATE inventory_item_master SET gst_rate = '18' WHERE gst_rate IS NULL")
        conn.execute("UPDATE inventory_item_master SET type_of_supply = 'Goods' WHERE type_of_supply IS NULL")
        conn.commit()

    if not st.session_state.get("_entry_tables_ensured"):
        ensure_tables(conn)
        st.session_state["_entry_tables_ensured"] = True

    if not st.session_state.get("_entry_bootstrap_done"):
        # Default Ledgers
        _default_ledgers = [
            "Kukuyo Camlin Ltd.",
            "Advance Account",
            "Against Bill",
            "TDS Deduction",
            "Cash Account",
            "Bank Account",
            "Sale Account",
            "Purchase Account",
        ]
        for _ledger_name in _default_ledgers:
            conn.execute(
                "INSERT INTO ledger_master (ledger_name) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM ledger_master WHERE ledger_name = ?)",
                (_ledger_name, _ledger_name)
            )
        conn.commit()

        # Master default groups
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
        conn.commit()

        # Voucher columns compatibility
        voucher_columns = {row[1] for row in conn.execute("PRAGMA table_info(voucher_entries)").fetchall()}
        if "amount" in voucher_columns and "invoice_amount" in voucher_columns:
            conn.execute("UPDATE voucher_entries SET invoice_amount = amount WHERE invoice_amount IS NULL")
            conn.execute("UPDATE voucher_entries SET tds = 0 WHERE tds IS NULL")
            conn.execute("UPDATE voucher_entries SET net_amount = invoice_amount WHERE net_amount IS NULL")
            conn.commit()

        _tds_cleanup_key = "manual_tds_only_v1"
        _already_cleaned = conn.execute(
            "SELECT 1 FROM app_migrations WHERE migration_key = ?",
            (_tds_cleanup_key,)
        ).fetchone()
        if not _already_cleaned:
            conn.execute(
                "UPDATE voucher_entries SET tds = 0, net_amount = invoice_amount "
                "WHERE ROUND(COALESCE(tds,0),2) = ROUND(COALESCE(invoice_amount,0) * 0.001,2) "
                "AND ROUND(COALESCE(net_amount,0),2) = ROUND(COALESCE(invoice_amount,0) - COALESCE(tds,0),2)"
            )
            conn.execute(
                "INSERT INTO app_migrations (migration_key) VALUES (?)",
                (_tds_cleanup_key,)
            )
            conn.commit()

        st.session_state["_entry_bootstrap_done"] = True

    # CRUD Helpers
    def _table_columns(table_name):
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]

    def _fetch_recent_entries(table_name, limit=50):
        return _fetch_recent_entries_cached(table_name, limit)

    def _delete_entry(table_name, entry_id):
        conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (int(entry_id),))
        conn.commit()

    def _clear_form_state(prefix):
        for key in list(st.session_state.keys()):
            if key.startswith(prefix):
                del st.session_state[key]

    def _reset_entry_mode_form_fields():
        """Clear all Entry Mode widget state after a successful save.
        The module selector itself is intentionally preserved.
        """
        prefixes = (
            "po_", "pr22_", "porl_", "prod_", "des_",
            "paper_", "board_", "fe_", "cf_",
            "hr_",
        )
        for key in list(st.session_state.keys()):
            if key.startswith(prefixes):
                del st.session_state[key]
        # Manual entry fields can be restored by the browser widget state on
        # rerun, so the Production/Despatch/Paper forms force-reset them via flags.
        st.session_state["_prod_force_reset"] = True
        st.session_state["_des_force_reset"] = True
        st.session_state["_paper_force_reset"] = True
        st.session_state["_po_force_reset"] = True
        st.session_state["_board_force_reset"] = True
        st.session_state["_pr22_force_reset"] = True
        st.session_state["_porl_force_reset"] = True
        try:
            _fetch_recent_entries_cached.clear()
            _sale_item_options_cached.clear()
            _sale_item_meta_cached.clear()
            _cf_item_options_cached.clear()
        except Exception:
            pass

    def _update_entry(table_name, entry_id, values):
        columns = _table_columns(table_name)
        assignments = []
        params = []
        for col, value in values.items():
            if col == "id" or col not in columns:
                continue
            assignments.append(f"{col} = ?")
            params.append(value)
        if not assignments:
            return
        params.append(int(entry_id))
        conn.execute(f"UPDATE {table_name} SET {', '.join(assignments)} WHERE id = ?", params)
        conn.commit()

    # Entry-mode field definitions.
    # Saved-entry edit screens intentionally use ONLY the fields that are
    # actually present in their corresponding Entry Mode form. Database-only
    # / legacy / report-calculation columns are not exposed here.
    ENTRY_EDIT_FIELDS = {
        "po_crud": [
            ("order_month", "Order Month"),
            ("product_code", "Product Code"),
            ("ruling_type", "Ruling Type"),
            ("no_of_page", "No. of Page"),
            ("product_size", "Product Size"),
            ("order_qty", "Order Qty"),
        ],
        "pr_crud": [
            ("po_month", "PO Month"),
            ("po_date", "Date"),
            ("product_code", "Product Code"),
            ("mrp", "MRP"),
            ("order_qty", "Order Qty"),
            ("produced_qty", "Produced Qty"),
            ("paper_rate", "Paper Rate"),
            ("tax_paper", "Tax Paper (%)"),
            ("current_paper_cost", "Current Paper Cost"),
            ("mill_paper", "Mill (Paper)"),
            ("board_rate", "Board Rate"),
            ("tax_board", "Tax Board (%)"),
            ("current_board_cost", "Current Board Cost"),
            ("mill_board", "Mill (Board)"),
            ("lamination_type", "Lamination Type"),
        ],
        "porl_crud": [
            ("order_month", "Order Month"),
            ("product_code", "Product Code"),
            ("ruling_type", "Ruling Type"),
            ("page", "No. of Page"),
            ("released_qty", "PO Release Qty"),
            ("po_rate", "PO Rate"),
            ("destination", "Destination"),
            ("po_number", "PO Number"),
            ("po_date", "PO Date"),
        ],
        "prod_crud": [
            ("production_month", "Order Month"),
            ("production_date", "Production Date"),
            ("product_code", "Product Code"),
            ("ruling_type", "Ruling"),
            ("plan_qty", "Production Qty"),
            ("rejection_qty", "Rejection"),
            ("ok_notebook", "OK Note Book"),
            ("case_quantity", "Case Quantity"),
            ("making_rate", "Making Rate"),
            ("making_charges", "Making Charges"),
            ("book_weight", "Book Weight"),
            ("wip_type", "WIP Type"),
            ("paper_consumption", "Paper Consumption"),
            ("board_size", "Board Size"),
            ("board_consumption", "Board Consumption"),
            ("book_wt_index", "Book Wt. (Index)"),
            ("index_consumption", "Index Consumption"),
        ],
        "des_crud": [
            ("despatch_date", "Despatch Date"),
            ("despatch_month", "Despatch Month"),
            ("product_code", "Product Code"),
            ("po_number", "PO Number"),
            ("destination", "Destination"),
            ("product_size", "Product Size"),
            ("despatch_qty", "Despatch Qty"),
            ("vehicle_no", "Vehicle No."),
            ("invoice_no", "Invoice No."),
            ("remarks", "Remarks"),
        ],
        "paper_crud": [
            ("entry_mode", "Entry Type"),
            ("entry_date", "Date"),
            ("invoice_no", "Invoice No."),
            ("party_name", "Party Name"),
            ("paper_size", "Paper Size"),
            ("opening_reel", "Opening Reel (Kg.)"),
            ("inward_qty", "Inward Qty (Kg.)"),
            ("inward_rate", "Inward Rate"),
            ("inward_amount", "Inward Amount"),
            ("process_qty", "Process Qty (Kg.)"),
            ("wastage", "Wastage (Kg.)"),
            ("wip_paper", "WIP (Paper) Kg."),
        ],
        "board_crud": [
            ("entry_mode", "Entry Type"),
            ("entry_date", "Date"),
            ("invoice_no", "Invoice No."),
            ("party_name", "Party Name"),
            ("godown", "Godown"),
            ("board_size", "Board Size"),
            ("opening_stock", "Opening Stock (Sheet)"),
            ("inward_qty", "Inward Qty (Sheet)"),
            ("inward_rate", "Inward Rate"),
            ("gst_percent", "GST %"),
            ("inward_amount", "Inward Amount"),
            ("out_for_printing", "Out for Printing (Sheet)"),
            ("wastage", "Wastage (Sheet)"),
            ("product_code", "Product Code"),
            ("printed_board_received", "Printed Board Recd. (Sheet)"),
            ("rate", "Rate"),
            ("amount", "Amount"),
            ("consumption", "Consumption (Sheet)"),
        ],
    }

    def _crud_panel(table_name, key_prefix, title="Saved Entries", entry_fields=None):
        st.markdown(f"#### {title}")
        rows = _fetch_recent_entries(table_name)
        if not rows:
            st.info("No saved entries available.")
            return None

        columns = _table_columns(table_name)
        id_pos = columns.index("id") if "id" in columns else 0

        choices = []
        for row in rows:
            entry_id = row[id_pos]
            preview_parts = []
            for name in ("product_code", "po_number", "invoice_no", "party_name", "entry_date", "po_date", "production_date", "despatch_date"):
                if name in columns:
                    value = row[columns.index(name)]
                    if value not in (None, ""):
                        preview_parts.append(str(value))
            preview = " | ".join(preview_parts[:3])
            choices.append((entry_id, f"ID {entry_id}" + (f" — {preview}" if preview else "")))

        selected = st.selectbox("Select entry", choices, format_func=lambda x: x[1], key=f"{key_prefix}_crud_selected")
        selected_id = selected[0]

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("✏️ Update", use_container_width=True, key=f"{key_prefix}_update_btn"):
                st.session_state[f"{key_prefix}_edit_id"] = selected_id
                st.rerun()
        with b2:
            if st.button("🗑️ Delete", use_container_width=True, key=f"{key_prefix}_delete_btn"):
                _delete_entry(table_name, selected_id)
                st.success(f"Entry ID {selected_id} deleted successfully.")
                st.rerun()
        with b3:
            if st.button("🧹 Clear Form", use_container_width=True, key=f"{key_prefix}_clear_btn"):
                form_prefix_map = {
                    "po_crud": "po_",
                    "pr_crud": "pr22_",
                    "porl_crud": "porl_",
                    "prod_crud": "prod_",
                    "des_crud": "des_",
                    "paper_crud": "paper_",
                    "board_crud": "board_",
                    "voucher_crud": "voucher_",
                }
                _clear_form_state(form_prefix_map.get(key_prefix, key_prefix))
                if key_prefix == "prod_crud":
                    st.session_state["_prod_force_reset"] = True
                elif key_prefix == "des_crud":
                    st.session_state["_des_force_reset"] = True
                elif key_prefix == "paper_crud":
                    st.session_state["_paper_force_reset"] = True
                elif key_prefix == "po_crud":
                    st.session_state["_po_force_reset"] = True
                elif key_prefix == "board_crud":
                    st.session_state["_board_force_reset"] = True
                st.session_state[f"{key_prefix}_clear_requested"] = True
                st.rerun()

        if st.session_state.get(f"{key_prefix}_edit_id") == selected_id:
            selected_row = conn.execute(f"SELECT * FROM {table_name} WHERE id = ?", (int(selected_id),)).fetchone()
            if selected_row:
                st.markdown("**Edit selected entry**")
                edit_values = {}
                # Never expose database-only/legacy/report columns in Entry Mode.
                fields = entry_fields or ENTRY_EDIT_FIELDS.get(key_prefix, [])
                edit_cols = st.columns(4)
                for i, (col, label) in enumerate(fields):
                    if col not in columns:
                        continue
                    current = selected_row[columns.index(col)]
                    with edit_cols[i % 4]:
                        edit_values[col] = st.text_input(
                            label,
                            value="" if current is None else str(current),
                            key=f"{key_prefix}_edit_{col}"
                        )
                if st.button("💾 Save Update", type="primary", use_container_width=True, key=f"{key_prefix}_save_update"):
                    _update_entry(table_name, selected_id, edit_values)
                    st.session_state.pop(f"{key_prefix}_edit_id", None)
                    st.success(f"Entry ID {selected_id} updated successfully.")
                    st.rerun()
        return selected_id

    # ------------------ FORM 1: PURCHASE ORDER ------------------
    if chosen_module == "1. Purchase Order Form":
        st.subheader("📦 Purchase Order Form")
        if st.session_state.pop("_po_force_reset", False):
            for _reset_key, _reset_value in {
                "po_order_month": None,
                "po_product_code": "",
                "po_ruling_type": "",
                "po_no_of_page": "",
                "po_product_size": "",
                "po_order_qty": None,
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_po_autofill_source_code", None)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            om_month = st.selectbox("Order Month", month_options, index=None, placeholder="Select Order Month", key="po_order_month")
        with col_b:
            om_code = st.text_input("Product Code", max_chars=10, key="po_product_code")
        # Auto-fetch Ruling Type, No. of Page & Product Size from Product Code.
        # Session state is updated BEFORE the fields are created, so the change
        # is reflected immediately instead of being absorbed by widget caching.
        current_code = str(om_code).strip()
        last_filled_code = st.session_state.get("_po_autofill_source_code", None)
        if current_code != last_filled_code:
            p_page, p_ruling, _ = parse_product_code(current_code)
            st.session_state["po_ruling_type"] = p_ruling or ""
            st.session_state["po_no_of_page"] = str(p_page) if p_page is not None else ""
            st.session_state["po_product_size"] = get_product_size_from_code(current_code) if len(current_code) >= 3 else ""
            st.session_state["_po_autofill_source_code"] = current_code
        with col_c:
            p_ruling = st.text_input("Ruling Type", key="po_ruling_type")
        col_d, col_e, col_f = st.columns(3)
        with col_d:
            p_page = st.text_input("No. of Page", key="po_no_of_page")
        with col_e:
            p_size = st.text_input("Product Size", key="po_product_size")
        with col_f:
            om_qty = st.number_input("Order Qty", min_value=0, step=1, value=None, key="po_order_qty")
        st.caption("↗ Product Code se Ruling Type, No. of Page & Product Size auto-fetch ho jayega")
        if st.button("💾 Save Purchase Order", type="primary", key="save_purchase_order"):
            if len(om_code) != 10 or not om_code.isdigit():
                st.error("Please enter a valid 10-digit Product Code.")
            elif om_qty is None or om_qty <= 0:
                st.error("Order Qty must be greater than zero.")
            else:
                conn.execute(
                    """INSERT INTO order_entries (order_month, product_code, ruling_type, no_of_page, product_size, order_qty)
                    VALUES (?,?,?,?,?,?)""",
                    (om_month, om_code, p_ruling, str(p_page), p_size, int(om_qty))
                )
                conn.commit()
                st.success("✅ Purchase Order saved successfully.")
                _reset_entry_mode_form_fields()
                st.rerun()
        _crud_panel("order_entries", "po_crud", entry_fields=ENTRY_EDIT_FIELDS["po_crud"])

    # ------------------ FORM 2: PO REQUEST ------------------
    elif chosen_module == "2. PO Request Form":
        st.subheader("📋 PO Form Data")

        # Save / Clear Form ke baad har field blank ho jaye — browser widget
        # state baar-baar purana value restore karta hai, is liye force-set karte
        # hain widgets banne se PEHLE.
        if st.session_state.pop("_pr22_force_reset", False):
            for _reset_key, _reset_value in {
                "pr22_po_month": None,
                "pr22_po_date": None,
                "pr22_po_code": "",
                "pr22_mrp": None,
                "pr22_order_qty": None,
                "pr22_produced_qty": None,
                "pr22_paper_rate": None,
                "pr22_tax_paper": None,
                "pr22_mill_paper": None,
                "pr22_board_rate": None,
                "pr22_tax_board": None,
                "pr22_mill_board": None,
                "pr22_lamination": None,
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_pr22_mrp_source_code", None)
            st.session_state.pop("_pr22_order_qty_signature", None)

        c1, c2, c3, c4 = st.columns(4)
        po_month = c1.selectbox("PO Month", month_options, index=None, placeholder="Select PO Month", key="pr22_po_month")
        with c2:
            po_date, po_date_str = get_date_input(
                "Date (DD/MM/YYYY)",
                "pr22_po_date",
                use_calendar=True
            )
        po_code = c3.text_input("Product Code", max_chars=10, key="pr22_po_code")
        # Auto-fetch MRP (Revised MRP) from case.xlsx when the Product Code changes.
        # Session state is updated BEFORE the widget is created so the change
        # reflects immediately instead of being absorbed by widget caching.
        mrp_signature = st.session_state.get("_pr22_mrp_source_code", None)
        current_mrp_code = str(po_code).strip()
        if current_mrp_code:
            if mrp_signature != current_mrp_code:
                auto_mrp = fetch_case_mrp(current_mrp_code)
                if auto_mrp is not None:
                    st.session_state["pr22_mrp"] = float(auto_mrp)
                else:
                    st.session_state.pop("pr22_mrp", None)
                st.session_state["_pr22_mrp_source_code"] = current_mrp_code
        else:
            st.session_state["pr22_mrp"] = None
            st.session_state.pop("_pr22_mrp_source_code", None)
        mrp = c4.number_input("MRP", min_value=0.0, step=0.01, value=None, format="%.2f", key="pr22_mrp")
        # Order Qty: auto-fetch from Dashboard "ORDER, PRODUCTION AND DESPATCH STATUS"
        # column 4 (Order), which is the Order Qty from Purchase Orders matched by
        # Order Month + Product Code.
        order_qty_auto = 0.0
        if po_code:
            try:
                order_qty_df = pd.read_sql_query(
                    """SELECT COALESCE(SUM(CAST(order_qty AS REAL)), 0) AS order_qty
                       FROM order_entries
                       WHERE CAST(product_code AS TEXT) = ?
                         AND (? IS NULL OR ? = '' OR order_month = ?)""",
                    conn, params=(str(po_code).strip(), po_month, po_month, po_month)
                )
                if order_qty_df.empty or (order_qty_df["order_qty"].iloc[0] or 0) == 0:
                    order_qty_df = pd.read_sql_query(
                        """SELECT COALESCE(SUM(CAST(order_qty AS REAL)), 0) AS order_qty
                           FROM order_entries
                           WHERE CAST(product_code AS TEXT) = ?""",
                        conn, params=(str(po_code).strip(),)
                    )
                if not order_qty_df.empty:
                    order_qty_auto = float(pd.to_numeric(order_qty_df["order_qty"].iloc[0], errors="coerce") or 0)
            except Exception:
                order_qty_auto = 0.0

        # Keep Order Qty blank until a Product Code is entered; then auto-fetch.
        order_qty_signature = f"{po_month or ''}|{str(po_code).strip()}|{order_qty_auto}"
        if po_code:
            if st.session_state.get("_pr22_order_qty_signature") != order_qty_signature:
                st.session_state["pr22_order_qty"] = int(order_qty_auto) if float(order_qty_auto).is_integer() else float(order_qty_auto)
                st.session_state["_pr22_order_qty_signature"] = order_qty_signature
        else:
            st.session_state["pr22_order_qty"] = None
            st.session_state.pop("_pr22_order_qty_signature", None)
        c5, c6, c7, c8 = st.columns(4)
        order_qty = c5.number_input("Order Qty", min_value=0, step=1, value=None, key="pr22_order_qty")
        with c6:
            produced_qty = st.number_input("Produced Qty", min_value=0, step=1, value=None, key="pr22_produced_qty")

            # Net Producible Quantity message:
            # Total Order Quantity - Previous Produce Quantity = Net Produceble Quantity.
            previous_produced_qty = 0.0
            if po_code:
                try:
                    prev_prod_df = pd.read_sql_query(
                        """SELECT COALESCE(SUM(CAST(produced_qty AS REAL)), 0) AS produced
                           FROM po_request_entries
                           WHERE CAST(product_code AS TEXT) = ?""",
                        conn, params=(str(po_code).strip(),)
                    )
                    if not prev_prod_df.empty:
                        previous_produced_qty = float(pd.to_numeric(prev_prod_df["produced"].iloc[0], errors="coerce") or 0)
                except Exception:
                    previous_produced_qty = 0.0

            if po_code and order_qty_auto > 0:
                net_producible_qty = max(order_qty_auto - previous_produced_qty, 0)
                st.caption(f"{order_qty_auto:,.0f} - {previous_produced_qty:,.0f} = {net_producible_qty:,.0f} (Due)")
            elif po_code:
                st.caption(f"0 - {previous_produced_qty:,.0f} = {previous_produced_qty:,.0f}")
        paper_rate = c7.number_input("Paper Rate", min_value=0.0, step=0.01, value=None, format="%.2f", key="pr22_paper_rate")
        tax_paper = c8.number_input("Tax Paper (%)", min_value=0.0, step=0.01, value=None, format="%.2f", key="pr22_tax_paper")
        
        current_paper_cost = None
        if paper_rate is not None and tax_paper is not None:
            current_paper_cost = paper_rate * (100.0 + tax_paper) / 100.0
        
        c9, c10, c11, c12 = st.columns(4)
        c9.text_input("Current Paper Cost", value=(f"{current_paper_cost:.2f}" if current_paper_cost is not None else ""), key=f"pr22_current_paper_cost_display_{current_paper_cost if current_paper_cost is not None else 'blank'}")
        mill_paper = c10.selectbox("Mill (Paper)", MILL_OPTIONS, index=None, placeholder="Select Mill", key="pr22_mill_paper")
        board_rate = c11.number_input("Board Rate", min_value=0.0, step=0.01, value=None, format="%.2f", key="pr22_board_rate")
        tax_board = c12.number_input("Tax Board (%)", min_value=0.0, step=0.01, value=None, format="%.2f", key="pr22_tax_board")
        
        current_board_cost = None
        if board_rate is not None and tax_board is not None:
            current_board_cost = board_rate * (100.0 + tax_board) / 100.0
        
        c13, c14, c15, _ = st.columns(4)
        c13.text_input("Current Board Cost", value=(f"{current_board_cost:.2f}" if current_board_cost is not None else ""), key=f"pr22_current_board_cost_display_{current_board_cost if current_board_cost is not None else 'blank'}")
        mill_board = c14.selectbox("Mill (Board)", MILL_OPTIONS, index=None, placeholder="Select Mill", key="pr22_mill_board")
        lamination_type = c15.selectbox("Lamination Type", LAMINATION_OPTIONS, index=None, placeholder="Select Lamination Type", key="pr22_lamination")

        st.caption("↗ Order Qty Dashboard ke ORDER, PRODUCTION AND DESPATCH STATUS column 4 (Order) se auto-fetch hoga (PO Month + Product Code match par) | MRP case.xlsx ke Revised MRP se auto-fetch hoga")

        if st.button("💾 Save PO Request", type="primary", key="save_po_request"):
            if not po_month:
                st.error("Please select PO Month.")
            elif po_date is None:
                st.error("Please select Date.")
            elif not po_code or len(po_code) != 10 or not po_code.isdigit():
                st.error("Please enter a valid 10-digit Product Code.")
            elif mrp is None:
                st.error("Please enter MRP.")
            elif order_qty is None or order_qty <= 0:
                st.error("Order Qty must be greater than zero.")
            elif produced_qty is None:
                st.error("Please enter Produced Qty.")
            elif paper_rate is None:
                st.error("Please enter Paper Rate.")
            elif tax_paper is None:
                st.error("Please enter Tax Paper (%).")
            elif board_rate is None:
                st.error("Please enter Board Rate.")
            elif tax_board is None:
                st.error("Please enter Tax Board (%).")
            elif not mill_paper:
                st.error("Please select Mill (Paper).")
            elif not mill_board:
                st.error("Please select Mill (Board).")
            elif not lamination_type:
                st.error("Please select Lamination Type.")
            else:
                conn.execute(
                    """INSERT INTO po_request_entries
                    (po_month, po_date, product_code, mrp, order_qty, produced_qty,
                     paper_rate, tax_paper, current_paper_cost, mill_paper, board_rate,
                     tax_board, current_board_cost, mill_board, lamination_type)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (po_month, po_date_str, po_code, float(mrp), int(order_qty), int(produced_qty),
                     float(paper_rate), float(tax_paper), float(current_paper_cost), mill_paper,
                     float(board_rate), float(tax_board), float(current_board_cost), mill_board, lamination_type)
                )
                conn.commit()
                st.success("✅ PO Request saved successfully.")
                _reset_entry_mode_form_fields()
                st.rerun()
        _crud_panel("po_request_entries", "pr_crud", entry_fields=ENTRY_EDIT_FIELDS["pr_crud"])

    # ------------------ FORM 3: PO RELEASED ------------------
    elif chosen_module == "3. PO Released Form":
        st.subheader("📋 PO Release Form")

        # Save / Clear Form ke baad fields blank ho jayein (browser widget state restore).
        if st.session_state.pop("_porl_force_reset", False):
            for _reset_key, _reset_value in {
                "porl_month": None,
                "porl_code": "",
                "porl_ruling": "",
                "porl_page": "",
                "porl_qty": None,
                "porl_destination": None,
                "porl_number": "",
                "porl_date": None,
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_porl_autofill_signature", None)
            st.session_state.pop("_porl_qty_signature", None)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            release_month = st.selectbox("Order Month", month_options, index=None, placeholder="Select Order Month", key="porl_month")
        with c2:
            release_code = st.text_input("Product Code", max_chars=10, key="porl_code")
        # PO Release Form: fetch Ruling Type and No. of Page from Purchase Order.
        # Product-code fallback is used only when the Purchase Order row is unavailable.
        p_page, p_ruling, _ = parse_product_code(release_code)
        if release_code:
            try:
                po_master = pd.read_sql_query(
                    """SELECT ruling_type, no_of_page FROM order_entries
                       WHERE CAST(product_code AS TEXT) = ?
                         AND (? IS NULL OR ? = '' OR order_month = ?)
                       ORDER BY id DESC LIMIT 1""",
                    conn, params=(str(release_code).strip(), release_month, release_month, release_month)
                )
                if po_master.empty:
                    po_master = pd.read_sql_query(
                        "SELECT ruling_type, no_of_page FROM order_entries WHERE CAST(product_code AS TEXT) = ? ORDER BY id DESC LIMIT 1",
                        conn, params=(str(release_code).strip(),)
                    )
                if not po_master.empty:
                    db_ruling = str(po_master.iloc[0].get("ruling_type", "") or "").strip()
                    db_page = str(po_master.iloc[0].get("no_of_page", "") or "").strip()
                    if db_ruling:
                        p_ruling = db_ruling
                    if db_page:
                        p_page = db_page
            except Exception:
                pass

        # Auto-fetch Ruling Type & No. of Page into the fields. Session state is
        # updated BEFORE the widgets are created so the change reflects
        # immediately instead of being absorbed by widget caching. Manual edits
        # are preserved until Order Month / Product Code changes.
        release_signature = f"{release_month or ''}|{str(release_code).strip()}"
        current_ruling = str(p_ruling or "")
        current_page = str(p_page) if p_page not in (None, "") else ""
        if release_code and st.session_state.get("_porl_autofill_signature") != release_signature:
            st.session_state["porl_ruling"] = current_ruling
            st.session_state["porl_page"] = current_page
            st.session_state["_porl_autofill_signature"] = release_signature
        elif not release_code:
            st.session_state["porl_ruling"] = ""
            st.session_state["porl_page"] = ""
            st.session_state.pop("_porl_autofill_signature", None)

        with c3:
            p_ruling = st.text_input("Ruling Type", key="porl_ruling")
        with c4:
            p_page = st.text_input("No. of Page", key="porl_page")
        # PO Rate is automatically calculated from PO Request columns 29+30+31.
        # 29 = Per Book Paper Cost, 30 = Per Book Board Cost, 31 = Conversion Rate.
        po_rate = get_po_release_rate(conn, release_code, release_month)

        c5, c6, c7, c8 = st.columns(4)
        # PO Release Qty: auto-fetch PO Request Form Produced Quantity.
        released_qty_auto = 0.0
        if release_code:
            try:
                req_df = pd.read_sql_query(
                    """SELECT produced_qty FROM po_request_entries
                       WHERE CAST(product_code AS TEXT) = ?
                         AND (? IS NULL OR ? = '' OR po_month = ?)
                       ORDER BY id DESC LIMIT 1""",
                    conn, params=(str(release_code).strip(), release_month, release_month, release_month)
                )
                if req_df.empty:
                    req_df = pd.read_sql_query(
                        "SELECT produced_qty FROM po_request_entries WHERE CAST(product_code AS TEXT) = ? ORDER BY id DESC LIMIT 1",
                        conn, params=(str(release_code).strip(),)
                    )
                if not req_df.empty:
                    released_qty_auto = float(pd.to_numeric(req_df.iloc[0].get("produced_qty", 0), errors="coerce") or 0)
            except Exception:
                released_qty_auto = 0.0

        # Keep PO Release Qty blank until a Product Code is entered; then auto-fetch the Produced Quantity.
        qty_signature = f"{release_month or ''}|{str(release_code).strip()}|{released_qty_auto}"
        if release_code:
            if st.session_state.get("_porl_qty_signature") != qty_signature:
                st.session_state["porl_qty"] = int(released_qty_auto) if float(released_qty_auto).is_integer() else float(released_qty_auto)
                st.session_state["_porl_qty_signature"] = qty_signature
        else:
            st.session_state["porl_qty"] = None
            st.session_state.pop("_porl_qty_signature", None)
        with c5:
            released_qty = st.number_input("PO Release Qty", min_value=0, step=1, value=None, key="porl_qty")
        with c6:
            po_rate = st.number_input(
                "PO Rate",
                min_value=0.0,
                step=0.01,
                value=(float(po_rate) if release_code else None),
                format="%.2f",
                key=f"porl_rate_{release_code}_{release_month or 'blank'}"
            )
        with c7:
            destination = st.selectbox("Destination", DESTINATION_OPTIONS, index=None, placeholder="Select Destination", key="porl_destination")
        with c8:
            po_number = st.text_input("PO Number", key="porl_number")
        c9, _, _, _ = st.columns(4)
        with c9:
            po_date, po_date_str = get_date_input("PO Date (DD/MM/YYYY)", "porl_date")
        st.caption("↗ Ruling Type & No. of Page Purchase Order se auto-fetch honge | PO Release Qty PO Request Produced Quantity se auto-fetch hoga | PO Rate = PO Request Report Col. 29 + 30 + 31")
        if st.button("💾 Save PO Release", type="primary", key="save_po_release"):
            if len(release_code) != 10 or not release_code.isdigit():
                st.error("Please enter a valid 10-digit Product Code.")
            elif released_qty is None or released_qty <= 0:
                st.error("PO Release Qty must be greater than zero.")
            else:
                conn.execute(
                    """INSERT INTO po_released_entries
                    (release_date, order_month, product_code, ruling_type, page,
                     book_size, released_qty, mill, remarks, po_rate,
                     destination, po_number, po_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (po_date_str, release_month, release_code, p_ruling, str(p_page),
                     get_product_size_from_code(release_code), str(released_qty), "", "",
                     float(po_rate), destination, po_number, po_date_str)
                )
                conn.commit()
                st.success("✅ PO Release saved successfully.")
                _reset_entry_mode_form_fields()
                st.rerun()
        _crud_panel("po_released_entries", "porl_crud", entry_fields=ENTRY_EDIT_FIELDS["porl_crud"])

    # ------------------ FORM 4: PRODUCTION ------------------
    elif chosen_module == "4. Production Form":
        st.subheader("🏭 Production Entry")

        # Manual entry fields must reset after Save / Clear Form. Streamlit's
        # browser widget state would otherwise restore the old values on rerun,
        # so force-set them to blank BEFORE the widgets are created.
        if st.session_state.pop("_prod_force_reset", False):
            for _reset_key, _reset_value in {
                "prod_month": None,
                "prod_date": None,
                "prod_code": "",
                "prod_qty": None,
                "prod_rej": None,
                "prod_wip_type": None,
                "prod_board_size": None,
                "prod_wip_board": None,
                "prod_book_wt_index_calc": None,
                "prod_index_consumption_calc": None,
            }.items():
                st.session_state[_reset_key] = _reset_value

        c1, c2, c3, c4 = st.columns(4)
        prod_month = c1.selectbox("Order Month", month_options, index=None, placeholder="Select Order Month", key="prod_month")

        with c2:
            prod_date, prod_date_str = get_date_input("Production Date (DD/MM/YYYY)", "prod_date")

        prod_code = c3.text_input("Product Code", max_chars=10, key="prod_code")
        p_page, p_ruling, _ = parse_product_code(prod_code)
        p_size = get_product_size_from_code(prod_code)
        c4.text_input("Ruling", value=p_ruling, key=f"prod_ruling_{prod_code}")

        c5, c6, c7, c8 = st.columns(4)
        production_qty = c5.number_input("Production Qty", min_value=0, step=1, value=None, key="prod_qty")
        rejection_qty = c6.number_input("Rejection", min_value=0, step=1, value=None, key="prod_rej")

        # Tab 5 formula: OK Note Book = Production Qty - Rejection.
        ok_notebook = max(int(production_qty or 0) - int(rejection_qty or 0), 0)
        ok_display = int(ok_notebook) if production_qty is not None or rejection_qty is not None else None
        st.session_state["prod_ok_calc"] = ok_display
        c7.number_input("OK Note Book", min_value=0, step=1, value=ok_display, key="prod_ok_calc")

        # Existing requested formula: Case Quantity = OK Note Book / PO Request Report Col. 10.
        po_case_qty = fetch_po_request_case_qty(conn, prod_code, prod_month)
        case_quantity = (float(ok_notebook) / float(po_case_qty)) if po_case_qty > 0 and production_qty is not None else None
        st.session_state["prod_case_calc"] = case_quantity
        c8.number_input("Case Quantity", min_value=0.0, step=0.01, value=case_quantity, format="%.2f", key="prod_case_calc")

        c9, c10, c11, c12, c13 = st.columns(5)
        making_rate = fetch_making_rate(prod_code) if prod_code else None
        st.session_state["prod_making_rate_calc"] = making_rate
        c9.number_input("Making Rate", min_value=0.0, step=0.01, value=making_rate, format="%.2f", key="prod_making_rate_calc")

        # Tab 5 formula: Making Charges = OK Note Book × Making Rate.
        making_charges = (float(ok_notebook) * float(making_rate)) if making_rate is not None else None
        st.session_state["prod_making_charges_calc"] = making_charges
        c10.number_input("Making Charges", min_value=0.0, step=0.01, value=making_charges, format="%.2f", key="prod_making_charges_calc")

        # Tab 5 formulas for Book Weight / Paper Consumption / Board Consumption.
        if prod_code and production_qty is not None:
            book_weight, paper_consumption, calculated_board_size, board_consumption = fetch_production_tab5_calculations(
                conn, prod_code, production_qty
            )
            book_weight = float(book_weight)
            paper_consumption = float(paper_consumption)
            board_consumption = float(board_consumption)
        else:
            book_weight = paper_consumption = board_consumption = None
            calculated_board_size = None
        st.session_state["prod_book_weight"] = book_weight
        st.session_state["prod_paper_consumption"] = paper_consumption
        st.session_state["prod_board_consumption"] = board_consumption
        st.session_state["prod_board_size"] = calculated_board_size

        c11.number_input("Book Weight", min_value=0.0, step=0.001, value=book_weight, format="%.3f", key="prod_book_weight")

        # WIP Type dropdown: always starts blank. User must select it manually.
        wip_options = ["Single Line", "Unruled", "Four Line", "Med. Square", "Index"]
        wip_type = c12.selectbox("WIP Type", wip_options, index=None, placeholder="Select WIP Type", key="prod_wip_type")

        c13.number_input("Paper Consumption", min_value=0.0, step=0.001, value=paper_consumption, format="%.3f", key="prod_paper_consumption")

        c14, c15, c16, _, _ = st.columns(5)
        board_options = ["77x98x190", "91x91x190"]
        board_index = board_options.index(calculated_board_size) if calculated_board_size in board_options else None
        board_size = c14.selectbox("Board Size", board_options, index=board_index, placeholder="Select Board Size", key="prod_board_size")
        wip_board_options = sorted({str(r[0]) for r in conn.execute(
            "SELECT DISTINCT item_name FROM inventory_item_master "
            "WHERE item_name IS NOT NULL AND TRIM(item_name)<>'' AND item_name LIKE '%PB%'"
        ).fetchall()})
        wip_board = c15.selectbox("WIP Board", wip_board_options, index=None, placeholder="Select WIP Board", key="prod_wip_board")
        board_consumption = c16.number_input("Board Consumption", min_value=0.0, step=0.001, value=board_consumption, format="%.3f", key="prod_board_consumption")

        # Book Wt. (Index) is fetched from Book Weight.xlsx (col J) and editable;
        # Index Consumption = Production Qty × Book Wt. (Index).
        c17, c18, _, _, _ = st.columns(5)
        book_wt_index = fetch_book_wt_index(prod_code) if prod_code else None
        st.session_state["prod_book_wt_index_calc"] = book_wt_index
        c17.number_input("Book Wt. (Index)", min_value=0.0, step=0.00001, value=book_wt_index, format="%.6f", key="prod_book_wt_index_calc")
        index_consumption = (float(production_qty or 0) * float(book_wt_index or 0)) if production_qty is not None and book_wt_index is not None else None
        st.session_state["prod_index_consumption_calc"] = index_consumption
        c18.number_input("Index Consumption", min_value=0.0, step=0.00001, value=index_consumption, format="%.6f", key="prod_index_consumption_calc")
        sb1, sb2, _ = st.columns([1.0, 0.9, 2.0])
        with sb1:
            if st.button("💾 Save Production Entry", type="primary", key="save_production_entry", use_container_width=True):
                if len(prod_code) != 10 or not prod_code.isdigit():
                    st.error("Enter a valid 10-digit Product Code.")
                elif production_qty is None or production_qty <= 0:
                    st.error("Production Qty must be greater than zero.")
                else:
                    conn.execute(
                        """INSERT INTO production_form_entries
                        (production_date, production_month, product_code, ruling_type, page, book_size,
                         plan_qty, ok_notebook, rejection_qty, case_quantity, making_rate,
                         making_charges, book_weight, wip_type, paper_consumption, board_size, wip_board, board_consumption,
                         book_wt_index, index_consumption)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (prod_date_str, prod_month, prod_code, p_ruling, str(p_page), p_size,
                         str(production_qty), str(ok_notebook), str(rejection_qty), str(case_quantity),
                         float(making_rate), float(making_charges), float(book_weight),
                         wip_type, float(paper_consumption), board_size, wip_board, float(board_consumption),
                         float(book_wt_index) if book_wt_index is not None else None,
                         float(index_consumption) if index_consumption is not None else None)
                    )
                    conn.commit()
                    st.success("✅ Production Entry saved successfully.")
                    _reset_entry_mode_form_fields()
                    st.rerun()
        with sb2:
            if st.button("🧹 Clear Form", key="clear_production_form", use_container_width=True):
                _clear_form_state("prod_")
                for _clear_key in list(st.session_state.keys()):
                    if str(_clear_key).startswith("_prod_"):
                        st.session_state.pop(_clear_key, None)
                st.session_state["_prod_force_reset"] = True
                st.rerun()
        _crud_panel("production_form_entries", "prod_crud", entry_fields=ENTRY_EDIT_FIELDS["prod_crud"])

    # ------------------ FORM 5: DESPATCH ------------------
    elif chosen_module == "5. Despatch Form":
        st.subheader("🚚 Despatch Entry")

        # Manual entry fields must reset after Save / Clear Form. Streamlit's
        # browser widget state would otherwise restore the old values on rerun,
        # so force-set them to blank BEFORE the widgets are created.
        if st.session_state.pop("_des_force_reset", False):
            for _reset_key, _reset_value in {
                "des_month": None,
                "des_date": None,
                "des_code": "",
                "des_po_number": None,
                "des_destination": None,
                "des_size": "",
                "des_qty": None,
                "des_vehicle": "",
                "des_invoice": "",
                "des_remarks": "",
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_des_last_po", None)
            st.session_state.pop("_des_size_signature", None)

        c1, c2, c3 = st.columns(3)
        despatch_month = c1.selectbox("Despatch Month", month_options, index=None, placeholder="Select Despatch Month", key="des_month")
        with c2:
            despatch_date, despatch_date_str = get_date_input("Despatch Date (DD/MM/YYYY)", "des_date")
        despatch_code = c3.text_input("Product Code", max_chars=10, key="des_code")
        c4, c5, c6 = st.columns(3)
        po_number_rows = conn.execute("""SELECT DISTINCT po_number FROM po_released_entries WHERE COALESCE(po_number, '') <> '' ORDER BY po_number""").fetchall()
        po_number_options = [row[0] for row in po_number_rows]
        if po_number_options:
            po_number = c4.selectbox("PO Number", po_number_options, index=None, placeholder="Select PO Number", key="des_po_number")
        else:
            po_number = c4.selectbox("PO Number", [""], index=None, placeholder="Select PO Number", key="des_po_number_empty")

        # Product info from the selected PO Number (used to auto-fetch the
        # Destination from the matching PO Release entry).
        po_info = None
        if po_number:
            po_info = conn.execute(
                """SELECT product_code, destination
                   FROM po_released_entries
                   WHERE po_number = ?
                   ORDER BY id DESC LIMIT 1""",
                (po_number,),
            ).fetchone()

        # Auto-fetch Destination from the selected PO Number.
        if po_info and (
            st.session_state.get("_des_last_po") != po_number
            or not st.session_state.get("des_destination")
        ):
            if po_info[1] and po_info[1] in DESTINATION_OPTIONS:
                st.session_state["des_destination"] = po_info[1]
            st.session_state["_des_last_po"] = po_number

        # Product Size auto-fetch from the Purchase Order (order_entries.product_size).
        _po_product_size = ""
        if despatch_code:
            _po_product_size = fetch_purchase_order_product_size(conn, despatch_code, despatch_month)
            if not _po_product_size:
                _po_product_size = get_product_size_from_code(despatch_code)
        elif po_info and po_info[0]:
            _po_product_size = fetch_purchase_order_product_size(conn, po_info[0], despatch_month)
            if not _po_product_size:
                _po_product_size = get_product_size_from_code(po_info[0])

        # Session state is updated BEFORE the widget is created so the change
        # reflects immediately. Manual edits are preserved until the Product
        # Code or PO Number changes.
        _des_size_signature = f"{str(despatch_code).strip()}|{str(po_number or '')}"
        if despatch_code or po_number:
            if st.session_state.get("_des_size_signature") != _des_size_signature:
                st.session_state["des_size"] = _po_product_size
                st.session_state["_des_size_signature"] = _des_size_signature
        else:
            st.session_state.pop("des_size", None)
            st.session_state.pop("_des_size_signature", None)

        destination = c5.selectbox("Destination", DESTINATION_OPTIONS, index=None, placeholder="Select Destination", key="des_destination")
        product_size = c6.text_input("Product Size", value=_po_product_size or "", key="des_size")
        c7, c8, c9 = st.columns(3)
        des_qty = c7.number_input("Despatch Quantity", min_value=0, step=1, value=None, key="des_qty")
        vehicle = c8.text_input("Vehicle No.", key="des_vehicle")
        invoice = c9.text_input("Invoice No.", key="des_invoice")
        remarks = st.text_input("Remarks", key="des_remarks")
        if st.button("💾 Save Despatch Entry", type="primary"):
            if des_qty is None or des_qty <= 0:
                st.error("Despatch quantity must be greater than zero.")
            else:
                conn.execute(
                    """INSERT INTO despatch_form_entries
                    (despatch_date, despatch_month, product_code, po_number, destination,
                     product_size, despatch_qty, vehicle_no, invoice_no, remarks)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (despatch_date_str, despatch_month, despatch_code, po_number, destination,
                     product_size, str(des_qty), vehicle, invoice, remarks)
                )
                conn.commit()
                st.success("✅ Despatch Entry saved successfully.")
                _reset_entry_mode_form_fields()
                st.rerun()
        _crud_panel("despatch_form_entries", "des_crud", entry_fields=ENTRY_EDIT_FIELDS["des_crud"])

    # ------------------ FORM 6: PAPER DETAIL ------------------
    elif chosen_module == "6. Paper Detail":
        st.subheader("📄 Paper Detail")

        # Manual entry fields must reset after Save / Clear Form. Streamlit's
        # browser widget state would otherwise restore the old values on rerun,
        # so force-set them to blank BEFORE the widgets are created.
        if st.session_state.pop("_paper_force_reset", False):
            for _reset_key, _reset_value in {
                "paper_mode": None,
                "paper_invoice": "",
                "paper_party": None,
                "paper_size": None,
                "paper_opening_reel": None,
                "paper_inward_qty": None,
                "paper_inward_rate": None,
                "paper_inward_amount": None,
                "paper_process_qty": None,
                "paper_wastage": None,
                "paper_wip_type": None,
                "paper_wip": None,
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_paper_amount_signature", None)
            st.session_state.pop("_paper_wip_signature", None)

        c1, c2, c3, c4 = st.columns(4)
        entry_mode = c1.selectbox("Entry Type", ["Purchase / Inward", "Process / Outward"], index=None, placeholder="Select Entry Type", key="paper_mode")
        with c2:
            entry_date, entry_date_str = get_date_input("Date (DD/MM/YYYY)", "paper_date")
        invoice_no = c3.text_input("Invoice No.", key="paper_invoice", disabled=(entry_mode == "Process / Outward"))
        party = c4.selectbox("Party Name", PARTY_OPTIONS, index=None, placeholder="Select Party Name", key="paper_party")
        c5, c6, c7, c8 = st.columns(4)
        paper_size = c5.selectbox("Paper Size", ["90x57x43", "97x37x57", "97x37x54"], index=None, placeholder="Select Paper Size", key="paper_size")
        opening_reel = c6.number_input("Opening Reel (Kg.)", min_value=0.0, step=0.001, value=None, format="%.3f", key="paper_opening_reel", disabled=(entry_mode == "Process / Outward"))
        inward_qty = c7.number_input("Inward Qty (Kg.)", min_value=0.0, step=0.001, value=None, format="%.3f", key="paper_inward_qty", disabled=(entry_mode == "Process / Outward"))
        inward_rate = c8.number_input("Inward Rate", min_value=0.0, step=0.01, value=None, format="%.2f", key="paper_inward_rate", disabled=(entry_mode == "Process / Outward"))
        
        calculated_amount = (float(inward_qty) * float(inward_rate)) if inward_qty is not None and inward_rate is not None else None

        # Inward Amount = Inward Qty x Inward Rate. Session state is updated
        # BEFORE the widget is created so the value reflects immediately and
        # manual edits are preserved until Qty or Rate changes.
        _paper_amount_signature = f"{inward_qty}|{inward_rate}"
        if calculated_amount is not None:
            if st.session_state.get("_paper_amount_signature") != _paper_amount_signature:
                st.session_state["paper_inward_amount"] = round(calculated_amount, 2)
                st.session_state["_paper_amount_signature"] = _paper_amount_signature
        elif st.session_state.get("_paper_amount_signature"):
            st.session_state.pop("paper_inward_amount", None)
            st.session_state.pop("_paper_amount_signature", None)

        c9, c10, c11, c12, c13 = st.columns(5)
        inward_amount = c9.number_input("Inward Amount", min_value=0.0, step=0.01, format="%.2f", value=calculated_amount, key="paper_inward_amount", disabled=(entry_mode == "Process / Outward"))
        process_qty = c10.number_input("Process Qty (Kg.)", min_value=0.0, step=0.001, value=None, format="%.3f", key="paper_process_qty", disabled=(entry_mode == "Purchase / Inward"))
        wastage = c11.number_input("Wastage (Kg.)", min_value=0.0, step=0.001, value=None, format="%.3f", key="paper_wastage", disabled=(entry_mode == "Purchase / Inward"))
        wip_type = c12.selectbox("WIP Type", ["Single Line", "Unruled", "Four Line", "Medium Square", "Index", "Double Rule"], index=None, placeholder="Select Type", key="paper_wip_type", disabled=(entry_mode == "Purchase / Inward"))

        # WIP Paper = Process Qty - Wastage. Session state is updated BEFORE the
        # widget is created so the value reflects immediately and manual edits
        # are preserved until Process Qty or Wastage changes.
        _paper_wip_signature = f"{process_qty}|{wastage}"
        if process_qty is not None and wastage is not None:
            _calculated_wip = float(process_qty) - float(wastage)
            if st.session_state.get("_paper_wip_signature") != _paper_wip_signature:
                st.session_state["paper_wip"] = round(_calculated_wip, 3)
                st.session_state["_paper_wip_signature"] = _paper_wip_signature
        elif st.session_state.get("_paper_wip_signature"):
            st.session_state.pop("paper_wip", None)
            st.session_state.pop("_paper_wip_signature", None)

        wip_paper = c13.number_input("WIP (Paper) Kg.", min_value=0.0, step=0.001, value=None, format="%.3f", key="paper_wip", disabled=(entry_mode == "Purchase / Inward"))
        
        if st.button("💾 Save Paper Detail", type="primary", key="save_paper_detail"):
            conn.execute(
                """INSERT INTO paper_detail_entries
                (entry_mode, entry_date, invoice_no, party_name, paper_size,
                 opening_reel, inward_qty, inward_rate, inward_amount,
                 process_qty, wastage, wip_paper, remarks)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (entry_mode, entry_date_str, invoice_no, party, paper_size,
                 float(opening_reel or 0), float(inward_qty or 0), float(inward_rate or 0),
                 float(inward_amount or 0), float(process_qty or 0), float(wastage or 0), float(wip_paper or 0), str(wip_type if wip_type else ""))
            )
            conn.commit()
            st.success("✅ Paper Detail saved successfully.")
            _reset_entry_mode_form_fields()
            st.rerun()
        _crud_panel("paper_detail_entries", "paper_crud", entry_fields=ENTRY_EDIT_FIELDS["paper_crud"])

    # ------------------ FORM 7: BOARD DETAIL ------------------
    elif chosen_module == "7. Board Detail":
        st.subheader("📦 Board Detail")
        if st.session_state.pop("_board_force_reset", False):
            for _reset_key, _reset_value in {
                "board_mode": None,
                "board_invoice": "",
                "board_party": None,
                "board_godown": None,
                "board_size": None,
                "board_opening_stock": None,
                "board_inward_qty": None,
                "board_inward_rate": None,
                "board_gst": None,
                "board_inward_amount": None,
                "board_out_printing": None,
                "board_wastage": None,
                "board_product_code": "",
                "board_printed_received": None,
                "board_rate": None,
                "board_amount": None,
                "board_consumption": None,
            }.items():
                st.session_state[_reset_key] = _reset_value
            st.session_state.pop("_board_amount_signature", None)
            st.session_state.pop("_board_amount2_signature", None)
        # Compact date field placed between Entry Type and Invoice No.
        c1, c2, c3, c4, c5 = st.columns(5)
        entry_mode = c1.selectbox("Entry Type", ["Purchase / Inward", "Process / Outward"], index=None, placeholder="Select Entry Type", key="board_mode")
        with c2:
            entry_date, entry_date_str = get_date_input("Date (DD/MM/YYYY)", "board_date")
        invoice_no = c3.text_input("Invoice No.", key="board_invoice")
        # Board Detail Party list: exclude the non-supplier options.
        _BOARD_EXCLUDED_PARTIES = {
            "Satia Industries Ltd.", "Tamilnadu Newsprint Papers Ltd.",
            "Fortune Graphics", "Vishruta Packaging", "Salasar", "Rich",
            "Printask", "Our Godown",
        }
        board_party_options = [p for p in PARTY_OPTIONS if p not in _BOARD_EXCLUDED_PARTIES]
        party = c4.selectbox("Party Name", board_party_options, index=None, placeholder="Select Party Name", key="board_party")
        godown = c5.selectbox("Godown", ["SPC Godown", "Fortune", "Rich Printers", "Vishruta", "Salasar", "Printask"], index=None, placeholder="Select Godown", key="board_godown")
        c6, c7, c8, c9 = st.columns(4)
        board_size = c6.selectbox("Board Size", ["77x98x190", "91x91x190"], index=None, placeholder="Select Board Size", key="board_size")
        opening_stock = c7.number_input("Opening Stock (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_opening_stock", disabled=(entry_mode == "Process / Outward"))
        inward_qty = c8.number_input("Inward Qty (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_inward_qty", disabled=(entry_mode == "Process / Outward"))
        inward_rate = c9.number_input("Inward Rate", min_value=0.0, step=0.01, value=None, format="%.2f", key="board_inward_rate", disabled=(entry_mode == "Process / Outward"))
        c10, c11, c12, c13, c14 = st.columns(5)
        gst_percent = c10.number_input("GST %", min_value=0.0, step=0.01, value=None, format="%.2f", key="board_gst")
        # Inward Amount = (Inward Qty x Inward Rate) + GST Amount. Session state
        # is updated BEFORE the widget is created so the value reflects
        # immediately and manual edits are preserved until Qty/Rate/GST changes.
        _board_amount_signature = f"{inward_qty}|{inward_rate}|{gst_percent}"
        _base_amount = (float(inward_qty) * float(inward_rate)) if inward_qty is not None and inward_rate is not None else None
        if _base_amount is not None:
            _gst_amount = _base_amount * (float(gst_percent or 0) / 100.0)
            if st.session_state.get("_board_amount_signature") != _board_amount_signature:
                st.session_state["board_inward_amount"] = round(_base_amount + _gst_amount, 2)
                st.session_state["_board_amount_signature"] = _board_amount_signature
        elif st.session_state.get("_board_amount_signature"):
            st.session_state.pop("board_inward_amount", None)
            st.session_state.pop("_board_amount_signature", None)
        inward_amount = c11.number_input("Inward Amount", min_value=0.0, step=0.01, value=None, format="%.2f", key="board_inward_amount", disabled=(entry_mode == "Process / Outward"))
        out_for_printing = c12.number_input("Out for Printing (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_out_printing", disabled=(entry_mode == "Process / Outward"))
        wastage = c13.number_input("Wastage (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_wastage", disabled=(entry_mode == "Process / Outward"))
        c15, c16, c17, c18 = st.columns(4)
        product_code = c15.text_input("Product Code", max_chars=10, key="board_product_code", disabled=(entry_mode == "Process / Outward"))
        printed_board_received = c16.number_input("Printed Board Recd. (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_printed_received", disabled=(entry_mode == "Process / Outward"))
        rate = c17.number_input("Rate", min_value=0.0, step=0.01, value=None, format="%.2f", key="board_rate")
        # Amount = (Printed Board Recd x Rate) + GST Amount. Session state is
        # updated BEFORE the widget is created so the value reflects immediately
        # and manual edits are preserved until Recd./Rate/GST changes.
        _board_amount2_signature = f"{printed_board_received}|{rate}|{gst_percent}"
        _base2_amount = (float(printed_board_received) * float(rate)) if printed_board_received is not None and rate is not None else None
        if _base2_amount is not None:
            _gst2_amount = _base2_amount * (float(gst_percent or 0) / 100.0)
            if st.session_state.get("_board_amount2_signature") != _board_amount2_signature:
                st.session_state["board_amount"] = round(_base2_amount + _gst2_amount, 2)
                st.session_state["_board_amount2_signature"] = _board_amount2_signature
        elif st.session_state.get("_board_amount2_signature"):
            st.session_state.pop("board_amount", None)
            st.session_state.pop("_board_amount2_signature", None)
        amount = c18.number_input("Amount", min_value=0.0, step=0.01, value=None, format="%.2f", key="board_amount")
        c19, _, _, _ = st.columns(4)
        consumption = c19.number_input("Consumption (Sheet)", min_value=0.0, step=1.0, value=None, format="%.0f", key="board_consumption", disabled=(entry_mode == "Process / Outward"))
        if st.button("💾 Save Board Detail", type="primary", key="save_board_detail"):
            conn.execute(
                """INSERT INTO board_detail_entries
                (entry_mode, entry_date, invoice_no, party_name, godown, board_size,
                 opening_stock, inward_qty, inward_rate, gst_percent, inward_amount,
                 out_for_printing, wastage, product_code, printed_board_received,
                 rate, amount, consumption)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (entry_mode, entry_date_str, invoice_no, party, godown, board_size,
                 float(opening_stock or 0), float(inward_qty or 0), float(inward_rate or 0),
                 float(gst_percent or 0), float(inward_amount or 0), float(out_for_printing or 0),
                 float(wastage or 0), product_code, float(printed_board_received or 0),
                 float(rate or 0), float(amount or 0), float(consumption or 0))
            )
            conn.commit()
            st.success("✅ Board Detail saved successfully.")
            _reset_entry_mode_form_fields()
            st.rerun()
        _crud_panel("board_detail_entries", "board_crud", entry_fields=ENTRY_EDIT_FIELDS["board_crud"])

    # ------------------ FORM 8: FINANCIAL ENTRY (TALLY-STYLE) ------------------
    elif chosen_module == "8. Financial Entry":
        fe_flash = st.session_state.pop("fe_flash", None)
        if fe_flash:
            st.success(fe_flash)
        if st.session_state.get("fe_saved", False):
            saved_no = st.session_state.get("fe_saved_no", "")
            saved_mode = st.session_state.get("fe_saved_mode", "")
            saved_date = st.session_state.get("fe_saved_date", "")
            saved_debit = st.session_state.get("fe_saved_debit", 0.0)
            saved_credit = st.session_state.get("fe_saved_credit", 0.0)
            st.markdown("""
            <div class="fe-topbar">
                <div class="fe-brand">🧾 Financial Entry</div>
                <div class="fe-company">🏢 SUBH PAPER COMPANY</div>
                <div class="fe-help">❓ Help</div>
            </div>
            <div class="fe-titlebar">
                <b>Voucher Saved</b>
                <span>SUBH PAPER COMPANY - (from 1-Apr-25)</span>
            </div>
            """, unsafe_allow_html=True)
            st.success(f"✅ Voucher No. {saved_no} ({saved_mode}) saved successfully. Entry mode is now locked.")
            if st.button("➕ New Entry", type="primary", use_container_width=True, key="fe_new_entry"):
                for key in list(st.session_state.keys()):
                    if key.startswith("fe_"):
                        st.session_state.pop(key, None)
                st.session_state["fe_row_count"] = 2
                st.rerun()
            st.caption("No entry fields are active after saving. Click New Entry to create the next voucher.")
        else:
            voucher_mode = st.session_state.get("fe_mode")
            if not voucher_mode:
                st.markdown("""
                <div class="fe-topbar">
                    <div class="fe-brand">🧾 Financial Entry</div>
                    <div class="fe-company">🏢 SUBH PAPER COMPANY</div>
                    <div class="fe-help">❓ Help</div>
                </div>
                <div class="fe-titlebar">
                    <b>Voucher Entry Creation</b>
                    <span>SUBH PAPER COMPANY - (from 1-Apr-25)</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<div class='fe-gate-title'>📋 <b>Voucher Type Chunein (Tally-style):</b></div>", unsafe_allow_html=True)
                tally_types = [
                    ("Payment", "F5 · Payment", "Cash/Bank se Payment (Bhugatan)"),
                    ("Receipt", "F6 · Receipt", "Cash/Bank me Receipt (Aamdani)"),
                    ("Contra", "F7 · Contra", "Cash ↔ Bank Transfer"),
                    ("Sale", "F8 · Sale", "Bech (Sale) Voucher"),
                    ("Purchase", "F9 · Purchase", "Khareed (Purchase) Voucher"),
                    ("Journal", "F10 · Journal", "General Ledger Adjustment"),
                ]
                gw_cols = st.columns(3)
                for idx, (vt, label, desc) in enumerate(tally_types):
                    with gw_cols[idx % 3]:
                        if st.button(label, key=f"fe_gate_{vt}", use_container_width=True, help=desc):
                            for key in list(st.session_state.keys()):
                                if str(key).startswith("fe_"):
                                    st.session_state.pop(key, None)
                            st.session_state["fe_mode"] = vt
                            st.session_state["fe_row_count"] = 2
                            st.rerun()
                st.markdown(
                    "<div class='fe-gate-hint'>👆 Upar se Voucher Type chunein — entry screen khul jayegi. "
                    "Neeche Voucher Register me kisi bhi voucher par <b>↩ Open</b> dabayein to bhi entry khul jayegi.</div>",
                    unsafe_allow_html=True
                )
            else:
                editing_group = st.session_state.get("fe_editing_group")
                editing_no = st.session_state.get("fe_editing_no")
                editing_ids = st.session_state.get("fe_editing_ids")
                # ---- SALE / PURCHASE MODE: FRESH BLANK PAGE ----
                if voucher_mode in ("Sale", "Purchase"):
                    _vm = voucher_mode
                    _is_purchase = (_vm == "Purchase")
                    _pty_side = "Cr" if _is_purchase else "Dr"
                    _acct_side = "Dr" if _is_purchase else "Cr"
                    _gst_side = "Dr" if _is_purchase else "Cr"
                    _sale_next_no = 1
                    try:
                        _sale_nums = conn.execute(f"SELECT invoice_no FROM voucher_entries WHERE mode='{_vm}'").fetchall()
                        _sale_int = []
                        for (val,) in _sale_nums:
                            try:
                                _sale_int.append(int(str(val).strip()))
                            except (TypeError, ValueError):
                                continue
                        _sale_next_no = (max(_sale_int) + 1) if _sale_int else 1
                    except Exception:
                        _sale_next_no = 1
                    _sale_tok = int(st.session_state.get("fe_sale_form_tok", 0))
                    _sale_pk = f"fe_sale_{_sale_tok}"
                    _sale_editing_no = st.session_state.get(f"{_sale_pk}_editing_no")
                    _sale_display_no = _sale_editing_no if _sale_editing_no else _sale_next_no
                    _flash_msg = st.session_state.pop("fe_flash", None)
                    if _flash_msg:
                        st.success(_flash_msg)
                    st.markdown(f"""
                    <div class="fe-topbar">
                        <div class="fe-brand">🧾 Financial Entry — {_vm}</div>
                        <div class="fe-company">🏢 SUBH PAPER COMPANY</div>
                    </div>
                    """, unsafe_allow_html=True)
                    _pending_load = st.session_state.get("fe_sale_pending_load")
                    if _pending_load:
                        _pd_party = _pending_load.get("party")
                        _pd_sales = _pending_load.get("sales")
                        _pd_date = _pending_load.get("date")
                        _pd_items = _pending_load.get("items") or []
                        if _pd_party:
                            st.session_state[f"{_sale_pk}_party_pick"] = _pd_party
                            st.session_state[f"{_sale_pk}_selected_party"] = _pd_party
                        if _pd_sales:
                            st.session_state[f"{_sale_pk}_sales_pick"] = _pd_sales
                            st.session_state[f"{_sale_pk}_selected_salesledger"] = _pd_sales
                        if _pd_date:
                            st.session_state[f"{_sale_pk}_date"] = _pd_date
                        st.session_state[f"{_sale_pk}_item_count"] = max(1, len(_pd_items))
                        _pd_round = _pending_load.get("round_off", 0.0)
                        st.session_state[f"{_sale_pk}_round_off"] = float(_pd_round or 0)
                        for _pi, (it, qq, rr) in enumerate(_pd_items):
                            st.session_state[f"{_sale_pk}_item_{_pi}"] = str(it)
                            st.session_state[f"{_sale_pk}_lastitem_{_pi}"] = str(it)
                            st.session_state[f"{_sale_pk}_qty_{_pi}"] = float(qq or 0)
                            st.session_state[f"{_sale_pk}_rate_{_pi}"] = float(rr or 0)
                        _pd_vno = _pending_load.get("voucher_no")
                        if _pd_vno:
                            st.session_state[f"{_sale_pk}_editing_no"] = _pd_vno
                        st.session_state["fe_flash"] = f"Voucher #{_pd_vno} load ho gaya — ab edit karke Save dabayein."
                        st.session_state.pop("fe_sale_pending_load", None)
                        st.rerun()
                    cl, cr = st.columns([3.6, 1.6], vertical_alignment="center")
                    with cl:
                        back_col, no_col = st.columns([0.5, 4])
                        with back_col:
                            if st.button("⬅", key="fe_back_type", help="Voucher Type list par wapas jayen"):
                                for key in list(st.session_state.keys()):
                                    if str(key).startswith("fe_") or key == "voucher_date":
                                        st.session_state.pop(key, None)
                                st.rerun()
                        with no_col:
                            st.markdown(
                                f"<span class='tally-avc-type-sm'>{_vm}&nbsp;&nbsp;No.&nbsp;:</span>"
                                f"<span class='fe-sale-auto-no'><b>{_sale_display_no}</b></span>",
                                unsafe_allow_html=True
                            )
                    with cr:
                        _sale_def_date = st.session_state.get(f"{_sale_pk}_date") or datetime.date.today()
                        _sale_dt = st.date_input(
                            f"{_vm} Date (F2)",
                            value=_sale_def_date,
                            format="DD/MM/YYYY",
                            key=f"{_sale_pk}_date",
                        )
                        _sale_months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                        _sale_disp = f"{_sale_dt.day:02d}-{_sale_months[_sale_dt.month-1]}-{_sale_dt.year}"
                        st.markdown(
                            f"<div class='fe-sale-datebox'>{_sale_disp}</div>"
                            f"<div class='fe-sale-day'>{_sale_dt.strftime('%A')}</div>",
                            unsafe_allow_html=True
                        )
                    st.components.v1.html("""
                    <script>
                    (()=>{
                      const p=window.parent;
                      try{
                        const findWrap=()=>{
                          const labels=Array.from(p.document.querySelectorAll('label'));
                          const lab=Array.from(labels).find(x=>(x.innerText||'').includes(' Date (F2)'));
                          return lab ? (lab.closest('[data-testid="stElementContainer"]') || lab.parentElement.parentElement) : null;
                        };
                        const hideWidget=()=>{
                          const w=findWrap();
                          if(!w) return false;
                          w.style.display='none';
                          return true;
                        };
                        if(!hideWidget()){
                          const t=setInterval(()=>{ if(hideWidget()) clearInterval(t); },250);
                        }
                        p.document.addEventListener('keydown', function(e){
                          if(e.key==='F2'){
                            e.preventDefault();
                            const w=findWrap();
                            if(w && w.style.display==='none') w.style.display='block';
                            const d=w && w.querySelector('[data-testid="stDateInput"]');
                            const inp=w && w.querySelector('[data-testid="stDateInput"] input');
                            const btn=w && (w.querySelector('[data-testid="stDateInputCalendarIconButton"]') || w.querySelector('[data-testid="stDateInput"] button'));
                            const target=btn||inp;
                            if(target){ if(target.focus) target.focus(); target.click(); }
                          }
                        }, true);
                        p.document.addEventListener('click', function(e){
                          const w=findWrap();
                          if(!w) return;
                          const d=w.querySelector('[data-testid="stDateInput"]');
                          if(d && !d.contains(e.target)){
                            const outside=!e.target.closest('[data-baseweb="popover"]');
                            if(outside && w.style.display!=='none') w.style.display='none';
                          }
                        }, true);
                        const rs=setInterval(()=>{ const w=findWrap(); if(w) { w.style.height='0'; w.style.overflow='hidden'; } },300);
                        setTimeout(()=>clearInterval(rs),3000);
                      }catch(err){}
                    })();
                    </script>
                    """, height=0, width=0)
                    st.markdown("<div style='border-top:1px solid #d1d5db; margin:6px 0 6px 0;'></div>", unsafe_allow_html=True)
                    # ---- PARTY A/c NAME + SALES LEDGER (TALLY STYLE) ----
                    _sel_party = st.session_state.get(f"{_sale_pk}_selected_party")
                    _sel_sales = st.session_state.get(f"{_sale_pk}_selected_salesledger")
                    _st_code_map = {
                        "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
                        "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
                        "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
                        "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
                        "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
                        "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
                        "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
                        "34": "Puducherry", "35": "Andaman and Nicobar Islands", "36": "Telangana",
                        "37": "Andhra Pradesh", "38": "Ladakh",
                    }
                    _comp_state_code = None
                    _party_state_code = None

                    def _sale_item_options():
                        return _sale_item_options_cached()

                    def _sale_item_meta(name):
                        return _sale_item_meta_cached(name, _sale_dt.strftime("%B %Y"))

                    def _sale_net_from_state():
                        _n = max(1, int(st.session_state.get(f"{_sale_pk}_item_count", 1)))
                        _tot = 0.0
                        _grps = {}
                        for _i in range(_n):
                            _nm = st.session_state.get(f"{_sale_pk}_item_{_i}")
                            if not _nm:
                                continue
                            _meta = _sale_item_meta(_nm)
                            _ql = float(st.session_state.get(f"{_sale_pk}_qty_{_i}", 0.0) or 0.0)
                            _pr = st.session_state.get(f"{_sale_pk}_lastitem_{_i}")
                            if _nm != _pr:
                                _rt = float(_meta["rate"] or 0)
                            else:
                                _rt = float(st.session_state.get(f"{_sale_pk}_rate_{_i}", _meta["rate"]) or _meta["rate"] or 0)
                            _am = round(_ql * _rt, 2)
                            _tot += _am
                            try:
                                _tv = float(str(_meta.get("tax") or "").strip() or 0)
                            except (TypeError, ValueError):
                                _tv = 0.0
                            _grps[_tv] = _grps.get(_tv, 0.0) + _am
                        _gt = 0.0
                        for _gr in _grps:
                            if _gr > 0 and _grps[_gr] > 0:
                                _gt += round(_grps[_gr] * _gr / 100.0, 2)
                        return round(_tot + _gt, 2)

                    # ---- SALES ITEMS GRID (metadata shared) ----
                    try:
                        _comp_state = (conn.execute("SELECT state FROM company_master LIMIT 1").fetchone() or (None,))[0]
                        if _comp_state:
                            for _c, _n in _st_code_map.items():
                                if str(_comp_state).strip().lower() == _n.lower():
                                    _comp_state_code = _c
                                    break
                    except Exception:
                        pass
                    _party_gst_no = None
                    try:
                        if _sel_party:
                            _r = conn.execute(
                                "SELECT gst_no FROM ledger_master WHERE LOWER(TRIM(ledger_name)) = LOWER(?) LIMIT 1",
                                (_sel_party,),
                            ).fetchone()
                            if _r:
                                _party_gst_no = str(_r[0] or "").strip()
                                if _party_gst_no and _party_gst_no[:2].isdigit():
                                    _party_state_code = _party_gst_no[:2]
                    except Exception:
                        pass
                    _pcol = st.container()
                    with _pcol:
                        _pl_l, _pl_f, _pl_a = st.columns([0.9, 3.6, 1.0], vertical_alignment="center")
                        with _pl_l:
                            st.markdown("<div class='fe-sale-inline-label'>Party A/c Name :</div>", unsafe_allow_html=True)
                        with _pl_f:
                            _all_ledgers = [r[0] for r in conn.execute(
                                "SELECT ledger_name FROM ledger_master ORDER BY ledger_name"
                            ).fetchall()]
                            _chose = st.selectbox(
                                "Party Ledger chunein:",
                                _all_ledgers,
                                index=None,
                                key=f"{_sale_pk}_party_pick",
                                placeholder="Type karke ledger chunein...",
                                label_visibility="collapsed",
                            )
                            if _chose:
                                st.session_state[f"{_sale_pk}_selected_party"] = _chose
                                _sel_party = _chose
                            if _sel_party:
                                _bal_open = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(opening_balance,0)),0) FROM ledger_master "
                                    "WHERE LOWER(TRIM(ledger_name)) = LOWER(?)",
                                    (_sel_party,),
                                ).fetchone()[0]
                                _bal_dr = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(net_amount,0) - COALESCE(tds,0)),0) FROM voucher_entries "
                                    "WHERE LOWER(TRIM(ledger_head)) = LOWER(?) AND UPPER(TRIM(dr_cr)) = 'DR'",
                                    (_sel_party,),
                                ).fetchone()[0]
                                _bal_cr = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(net_amount,0) - COALESCE(tds,0)),0) FROM voucher_entries "
                                    "WHERE LOWER(TRIM(ledger_head)) = LOWER(?) AND UPPER(TRIM(dr_cr)) = 'CR'",
                                    (_sel_party,),
                                ).fetchone()[0]
                                _bal_cur = float(_bal_open or 0) + float(_bal_dr or 0) - float(_bal_cr or 0)
                                _pty_color = "#15803d" if _is_purchase else ""
                                st.markdown(
                                    f"<div class='fe-sale-bal-row fe-sale-plabel' style='font-size:12px;font-weight:400;'>Current Balance :"
                                    f"<span class='fe-sale-cbalance' style='color:{_pty_color};font-size:12px;font-weight:400;'> {abs(_bal_cur):,.2f} {_pty_side}</span></div>",
                                    unsafe_allow_html=True,
                                )
                        with _pl_a:
                            _party_amt = _sale_net_from_state()
                            st.markdown(
                                f"<div class='fe-sale-inline-label' style='margin-top:14px;'>{'Credit' if _is_purchase else 'Debit'} Amount :</div>"
                                f"<div class='fe-sale-amt-box'>₹ {_party_amt:,.2f}</div>",
                                unsafe_allow_html=True,
                            )
                        _sl_l, _sl_f, _sl_x = st.columns([0.9, 3.6, 1.0], vertical_alignment="center")
                        with _sl_l:
                            st.markdown(f"<div class='fe-sale-inline-label' style='margin-top:12px;'>{_vm} Ledger :</div>", unsafe_allow_html=True)
                        with _sl_f:
                            _all_sl = [r[0] for r in conn.execute(
                                "SELECT ledger_name FROM ledger_master ORDER BY ledger_name"
                            ).fetchall()]
                            _chose_sl = st.selectbox(
                                f"{_vm} Ledger chunein:",
                                _all_sl,
                                index=None,
                                key=f"{_sale_pk}_sales_pick",
                                placeholder="Type karke ledger chunein...",
                                label_visibility="collapsed",
                            )
                            if _chose_sl:
                                st.session_state[f"{_sale_pk}_selected_salesledger"] = _chose_sl
                                _sel_sales = _chose_sl
                            if _sel_sales:
                                _sb_open = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(opening_balance,0)),0) FROM ledger_master "
                                    "WHERE LOWER(TRIM(ledger_name)) = LOWER(?)",
                                    (_sel_sales,),
                                ).fetchone()[0]
                                _sb_dr = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(net_amount,0) - COALESCE(tds,0)),0) FROM voucher_entries "
                                    "WHERE LOWER(TRIM(ledger_head)) = LOWER(?) AND UPPER(TRIM(dr_cr)) = 'DR'",
                                    (_sel_sales,),
                                ).fetchone()[0]
                                _sb_cr = conn.execute(
                                    "SELECT COALESCE(SUM(COALESCE(net_amount,0) - COALESCE(tds,0)),0) FROM voucher_entries "
                                    "WHERE LOWER(TRIM(ledger_head)) = LOWER(?) AND UPPER(TRIM(dr_cr)) = 'CR'",
                                    (_sel_sales,),
                                ).fetchone()[0]
                                _sb_cur = float(_sb_open or 0) + float(_sb_dr or 0) - float(_sb_cr or 0)
                                _sal_color = "#15803d" if not _is_purchase else ""
                                st.markdown(
                                    f"<div class='fe-sale-bal-row fe-sale-plabel' style='font-size:12px;font-weight:400;'>Current Balance :"
                                    f"<span class='fe-sale-cbalance' style='color:{_sal_color};font-size:12px;font-weight:400;'> {abs(_sb_cur):,.2f} {_acct_side}</span></div>",
                                    unsafe_allow_html=True,
                                )
                    st.markdown(
                        "<div class='fe-item-head'>"
                        "<span class='c' style='width:52%;'>Particulars / Item Name</span>"
                        "<span class='c' style='width:11%; text-align:center;'>HSN/SAC</span>"
                        "<span class='c' style='width:6%; text-align:center;'>Tax%</span>"
                        "<span class='c' style='width:9%; text-align:center;'>Quantity</span>"
                        "<span class='c' style='width:8%; text-align:center;'>Rate</span>"
                        "<span class='c' style='width:12%; text-align:center;'>Amount</span>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    # ---- SALE ITEMS GRID ----
                    sale_item_count = max(1, int(st.session_state.get(f"{_sale_pk}_item_count", 1)))
                    _sale_item_opts = _sale_item_options()
                    sale_item_rows = []
                    _sale_item_total = 0.0
                    for _si in range(sale_item_count):
                        _prev_item = st.session_state.get(f"{_sale_pk}_lastitem_{_si}")
                        _ic = st.columns([52, 11, 6, 9, 8, 12], vertical_alignment="center")
                        with _ic[0]:
                            _isd, _iss = st.columns([0.5, 6.5], vertical_alignment="center")
                            _del_item = _isd.button("🗑", key=f"{_sale_pk}_item_del_{_si}", help="Row delete karein")
                            with _iss:
                                _itm = st.selectbox(
                                    "Particulars", _sale_item_opts, index=(_sale_item_opts.index(_prev_item) if _prev_item in _sale_item_opts else None),
                                    key=f"{_sale_pk}_item_{_si}", placeholder="Item chunein...",
                                    label_visibility="collapsed")
                        if _itm != _prev_item:
                            if _itm:
                                _new_meta = _sale_item_meta(_itm)
                                st.session_state[f"{_sale_pk}_lastitem_{_si}"] = _itm
                                st.session_state[f"{_sale_pk}_rate_{_si}"] = _new_meta["rate"]
                                st.session_state[f"{_sale_pk}_qty_{_si}"] = 0.0
                            else:
                                st.session_state[f"{_sale_pk}_lastitem_{_si}"] = None
                        _im = _sale_item_meta(_itm) if _itm else {"name": "", "hsn": "", "tax": "", "rate": 0.0, "unit": ""}
                        with _ic[1]:
                            st.markdown(f"<div class='fe-item-fld'>{html.escape(_im['hsn'])}</div>", unsafe_allow_html=True)
                        with _ic[2]:
                            st.markdown(f"<div class='fe-item-fld'>{html.escape(_im['tax'])}</div>", unsafe_allow_html=True)
                        with _ic[3]:
                            _sqty = st.number_input("Qty", min_value=0.0, step=1.0, value=None,
                                                    format="%.2f", key=f"{_sale_pk}_qty_{_si}", label_visibility="collapsed")
                        with _ic[4]:
                            _srt = st.number_input("Rate", min_value=0.0, step=0.01, value=None,
                                                   format="%.2f", key=f"{_sale_pk}_rate_{_si}", label_visibility="collapsed")
                        _qtr = float(_sqty or 0)
                        _amt = round(_qtr * float(_srt or 0), 2)
                        with _ic[5]:
                            st.markdown(f"<div class='fe-item-fld fe-amt'>₹ {_amt:,.2f}</div>", unsafe_allow_html=True)
                        sale_item_rows.append((_itm, _im, _qtr, float(_srt or 0), _amt, _del_item))
                        _sale_item_total += _amt
                    _si_del = next((i for i, r in enumerate(sale_item_rows) if r[5]), None)
                    if _si_del is not None:
                        _cur = sale_item_count
                        if _cur <= 1:
                            st.warning("Kam se kam ek item row required hai.")
                        else:
                            for _fj in range(_si_del, _cur - 1):
                                _to = _fj
                                _fr = _fj + 1
                                for _fld in ("item", "qty", "rate"):
                                    _sk = f"{_sale_pk}_{_fld}_{_fr}"
                                    _dk = f"{_sale_pk}_{_fld}_{_to}"
                                    if _sk in st.session_state:
                                        st.session_state[_dk] = st.session_state[_sk]
                                _sk = f"{_sale_pk}_lastitem_{_fr}"
                                _dk = f"{_sale_pk}_lastitem_{_to}"
                                if _sk in st.session_state:
                                    st.session_state[_dk] = st.session_state[_sk]
                            for _fld in ("item", "qty", "rate"):
                                st.session_state.pop(f"{_sale_pk}_{_fld}_{_cur - 1}", None)
                            st.session_state.pop(f"{_sale_pk}_lastitem_{_cur - 1}", None)
                            st.session_state[f"{_sale_pk}_item_count"] = _cur - 1
                            st.rerun()
                    _icb = st.columns([0.5, 4.5])
                    if _icb[0].button("＋ Item", key=f"{_sale_pk}_item_add"):
                        st.session_state[f"{_sale_pk}_item_count"] = sale_item_count + 1
                        st.rerun()
                    _tax_groups = {}
                    for _row in sale_item_rows:
                        _ri_tax = str((_row[1].get("tax") if _row[1] else "") or "").strip()
                        try:
                            _ri_taxv = float(_ri_tax) if _ri_tax else 0.0
                        except (TypeError, ValueError):
                            _ri_taxv = 0.0
                        _tax_groups[_ri_taxv] = _tax_groups.get(_ri_taxv, 0.0) + round(float(_row[4] or 0), 2)
                    _is_interstate = bool(_comp_state_code and _party_state_code and _comp_state_code != _party_state_code)
                    _gst_total = 0.0
                    _gst_lines = ""
                    for _grt in sorted(_tax_groups, reverse=True):
                        if _grt <= 0 or _tax_groups[_grt] <= 0:
                            continue
                        _gst_amt = round(_tax_groups[_grt] * _grt / 100.0, 2)
                        _gst_total += _gst_amt
                        if _is_interstate:
                            _gst_lines += (
                                f"<div class='fe-sum-row'><span>IGST @ {_grt:.1f}%</span>"
                                f"<span class='fe-sum-amt'>₹ {_gst_amt:,.2f}</span></div>"
                            )
                        else:
                            _gst_lines += (
                                f"<div class='fe-sum-row'><span>CGST @ {_grt/2:.1f}% &ensp;+&ensp; SGST @ {_grt/2:.1f}%</span>"
                                f"<span class='fe-sum-amt'>₹ {_gst_amt:,.2f}</span></div>"
                            )
                    _net_amt = round(_sale_item_total + _gst_total, 2)
                    _adj_row = st.columns([0.5, 2.4, 2.6])
                    with _adj_row[1]:
                        _round_off_val = st.number_input(
                            "Round Off (₹)", min_value=-10000.0,
                            value=None,
                            step=0.01, format="%.2f", key=f"{_sale_pk}_round_off")
                    _net_final = round(_net_amt + float(_round_off_val or 0), 2)
                    _round_diff = round(_net_final - _net_amt, 2)
                    _round_line = ""
                    if _round_diff != 0:
                        _round_line = (
                            f"<div class='fe-sum-row'><span>Round Off {'(+)' if _round_diff > 0 else '(−)'}"
                            f"</span><span class='fe-sum-amt'>₹ {abs(_round_diff):,.2f}</span></div>"
                        )
                    _icb[1].markdown(
                        f"<div class='fe-summary'>"
                        f"<div class='fe-sum-row'><span>Total</span><span class='fe-sum-amt'>₹ {_sale_item_total:,.2f}</span></div>"
                        f"{_gst_lines}"
                        f"{_round_line}"
                        f"<div class='fe-sum-row fe-sum-total'><span>Net Amount</span><span class='fe-sum-amt'>₹ {_net_final:,.2f}</span></div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # ---- SALE SAVE / EDIT / DELETE ----
                    _sale_editing_no = st.session_state.get(f"{_sale_pk}_editing_no")
                    _sale_existing = []
                    try:
                        _sale_existing = [str(r[0]) for r in conn.execute(
                            f"SELECT DISTINCT invoice_no FROM voucher_entries WHERE mode='{_vm}' "
                            "ORDER BY CAST(invoice_no AS INTEGER) DESC"
                        ).fetchall()]
                    except Exception:
                        pass
                    _act = st.columns([1.15, 0.55, 0.65, 1.4, 0.65, 1.1], vertical_alignment="center")
                    with _act[0]:
                        _edit_pick = st.selectbox(
                            "Edit / Load Saved Voucher:", [""] + _sale_existing,
                            index=(_sale_existing.index(_sale_editing_no) + 1) if _sale_editing_no in _sale_existing else 0,
                            key=f"{_sale_pk}_pick_existing", label_visibility="collapsed",
                            placeholder="Pick Voucher #...")
                    with _act[1]:
                        _load_clicked = st.button("↩ Load", key="fe_sale_load_voucher", use_container_width=True,
                                                  help="Saved voucher ko form me load karein (Edit)")
                    with _act[2]:
                        _del_existing_clicked = st.button("🗑 Delete", key="fe_sale_del_existing",
                                                          use_container_width=True, disabled=(not _sale_editing_no),
                                                          help="Current loaded voucher delete karein")
                    with _act[3]:
                        _sale_save_clicked = st.button("💾 Save Voucher (F11)", type="primary",
                                                       use_container_width=True, key="fe_sale_save_voucher")
                    with _act[4]:
                        _sale_clear_clicked = st.button("🧹 Clear", use_container_width=True, key="fe_sale_clear")
                    with _act[5]:
                        if _sale_editing_no:
                            st.markdown(
                                f"<div class='fe-sale-editing-badge'>✏️ Editing #{html.escape(_sale_editing_no)}</div>",
                                unsafe_allow_html=True
                            )
                    if _load_clicked and _edit_pick:
                        _ln = str(_edit_pick)
                        _lrows = conn.execute(
                            "SELECT dr_cr, ledger_head, net_amount, entry_date FROM voucher_entries "
                            f"WHERE mode='{_vm}' AND invoice_no=? ORDER BY id ASC", (_ln,)
                        ).fetchall()
                        _lparty = next((r[1] for r in _lrows if str(r[0]).upper() == _pty_side.upper()), None)
                        _lsales = next((r[1] for r in _lrows if str(r[0]).upper() == _acct_side.upper() and "GST" not in str(r[1]).upper() and str(r[1]).strip() not in ("CGST GST Output", "SGST GST Output", "IGST GST Output")), None)
                        _ldate = None
                        for r in _lrows:
                            _dstr = str(r[3] or "").strip() if len(r) > 3 else ""
                            if _dstr:
                                try:
                                    _ldate = datetime.datetime.strptime(_dstr, "%d/%m/%Y").date()
                                except (TypeError, ValueError):
                                    try:
                                        _ldate = datetime.datetime.strptime(_dstr, "%Y-%m-%d").date()
                                    except (TypeError, ValueError):
                                        pass
                                if _ldate:
                                    break
                        _litems = conn.execute(
                            "SELECT item_name, qty, rate FROM voucher_inventory_items "
                            f"WHERE mode='{_vm}' AND voucher_no=? ORDER BY id ASC", (_ln,)
                        ).fetchall()
                        _lround = next(
                            ((1.0 if (str(r[0]).upper() == "DR") == _is_purchase else -1.0) * float(r[2] or 0))
                            for r in _lrows if str(r[1]).strip() == "Rounding Off"
                        ) if any(str(r[1]).strip() == "Rounding Off" for r in _lrows) else 0.0
                        st.session_state["fe_sale_pending_load"] = {
                            "party": _lparty, "sales": _lsales, "date": _ldate,
                            "items": [(r[0], r[1], r[2]) for r in _litems],
                            "round_off": float(_lround or 0),
                            "voucher_no": _ln,
                        }
                        st.rerun()
                    if _del_existing_clicked and _sale_editing_no:
                        _dno = str(_sale_editing_no)
                        _drestore = conn.execute(
                            f"SELECT item_name, qty FROM voucher_inventory_items WHERE mode='{_vm}' AND voucher_no=?",
                            (_dno,)
                        ).fetchall()
                        for dt, dq in _drestore:
                            conn.execute(
                                "UPDATE inventory_item_master SET quantity = COALESCE(quantity,0) {sign} ? WHERE item_name = ?".format(
                                    sign="-" if _is_purchase else "+"),
                                (float(dq or 0), dt)
                            )
                        conn.execute(f"DELETE FROM voucher_inventory_items WHERE mode='{_vm}' AND voucher_no=?", (_dno,))
                        conn.execute(f"DELETE FROM voucher_entries WHERE mode='{_vm}' AND invoice_no=?", (_dno,))
                        conn.commit()
                        st.session_state["fe_sale_form_tok"] = _sale_tok + 1
                        st.session_state["fe_flash"] = f"{_vm} Voucher #{_dno} delete ho gaya."
                        st.rerun()
                    if _sale_clear_clicked:
                        st.session_state["fe_sale_form_tok"] = _sale_tok + 1
                        st.rerun()
                    if _sale_save_clicked:
                        _valid_items = []
                        _inv_total = 0.0
                        for _row in sale_item_rows:
                            if _row[0] and float(_row[2] or 0) > 0:
                                _valid_items.append(_row)
                                _inv_total += float(_row[4] or 0)
                        _inv_total = round(_inv_total, 2)
                        if not _sel_party:
                            st.error("Party A/c Name select karein.")
                        elif not _sel_sales:
                            st.error(f"{_vm} Ledger select karein.")
                        elif not _valid_items:
                            st.error("Kam se kam ek item quantity ke saath chahiye.")
                        else:
                            _vno = _sale_editing_no if _sale_editing_no else str(_sale_next_no)
                            _old_map = {}
                            if _sale_editing_no:
                                _drestore = conn.execute(
                                    f"SELECT item_name, qty FROM voucher_inventory_items WHERE mode='{_vm}' AND voucher_no=?",
                                    (_vno,)
                                ).fetchall()
                                _old_map = {str(dt or ""): float(dq or 0) for dt, dq in _drestore}
                                conn.execute(f"DELETE FROM voucher_inventory_items WHERE mode='{_vm}' AND voucher_no=?", (_vno,))
                                conn.execute(f"DELETE FROM voucher_entries WHERE mode='{_vm}' AND invoice_no=?", (_vno,))
                            _sale_date_str = _sale_dt.strftime("%d/%m/%Y")
                            _remarks_val = st.session_state.get("fe_remarks", "")
                            conn.execute(
                                """INSERT INTO voucher_entries
                                (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                 invoice_amount, tds, net_amount, remarks, bill_ref)
                                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                (_vm, _sale_date_str, _vno, _pty_side, _sel_party,
                                 _net_final, 0.0, _net_final, _remarks_val, f"{_vm}Party")
                            )
                            conn.execute(
                                """INSERT INTO voucher_entries
                                (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                 invoice_amount, tds, net_amount, remarks, bill_ref)
                                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                (_vm, _sale_date_str, _vno, _acct_side, _sel_sales,
                                 _sale_item_total, 0.0, _sale_item_total, _remarks_val, f"{_vm}Sales")
                            )
                            for _grt in sorted(_tax_groups, reverse=True):
                                if _grt <= 0 or _tax_groups[_grt] <= 0:
                                    continue
                                _gst_amt = round(_tax_groups[_grt] * _grt / 100.0, 2)
                                if _is_interstate:
                                    conn.execute(
                                        """INSERT INTO voucher_entries
                                        (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                         invoice_amount, tds, net_amount, remarks, bill_ref)
                                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                        (_vm, _sale_date_str, _vno, _gst_side, "IGST GST Output",
                                         _gst_amt, 0.0, _gst_amt, _remarks_val, f"{_vm}GST")
                                    )
                                    used_ledger = "IGST GST Output"
                                else:
                                    _cgst_amt = round(_gst_amt / 2.0, 2)
                                    _sgst_amt = round(_gst_amt - _cgst_amt, 2)
                                    conn.execute(
                                        """INSERT INTO voucher_entries
                                        (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                         invoice_amount, tds, net_amount, remarks, bill_ref)
                                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                        (_vm, _sale_date_str, _vno, _gst_side, "CGST GST Output",
                                         _cgst_amt, 0.0, _cgst_amt, _remarks_val, f"{_vm}GST")
                                    )
                                    conn.execute(
                                        """INSERT INTO voucher_entries
                                        (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                         invoice_amount, tds, net_amount, remarks, bill_ref)
                                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                        (_vm, _sale_date_str, _vno, _gst_side, "SGST GST Output",
                                         _sgst_amt, 0.0, _sgst_amt, _remarks_val, f"{_vm}GST")
                                    )
                            if _round_diff != 0:
                                _rd_drcr = "Cr" if (float(_round_diff) > 0) != _is_purchase else "Dr"
                                conn.execute(
                                    """INSERT INTO voucher_entries
                                    (mode, entry_date, invoice_no, dr_cr, ledger_head,
                                     invoice_amount, tds, net_amount, remarks, bill_ref)
                                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                    (_vm, _sale_date_str, _vno, _rd_drcr, "Rounding Off",
                                     abs(_round_diff), 0.0, abs(_round_diff), _remarks_val, f"{_vm}GST")
                                )
                            for _row in _valid_items:
                                _uv = _row[1].get("unit") if _row[1] else ""
                                conn.execute(
                                    """INSERT INTO voucher_inventory_items
                                    (voucher_no, mode, entry_date, item_name, unit, qty, rate, amount)
                                    VALUES (?,?,?,?,?,?,?,?)""",
                                    (_vno, _vm, _sale_date_str, _row[0], _uv, _row[2], _row[3], _row[4])
                                )
                                _newq = float(_row[2] or 0)
                                _oldq = _old_map.get(_row[0], 0.0) if _sale_editing_no else 0.0
                                _inv_delta = (_newq if _is_purchase else -_newq) - (_oldq if _is_purchase else -_oldq)
                                conn.execute(
                                    "UPDATE inventory_item_master SET quantity = COALESCE(quantity,0) + ? WHERE item_name = ?",
                                    (_inv_delta, _row[0])
                                )
                            conn.commit()
                            st.session_state["fe_sale_form_tok"] = _sale_tok + 1
                            st.session_state["fe_flash"] = (
                                f"{_vm} Voucher #{_vno} {'updated' if _sale_editing_no else 'saved'} successfully — form clear ho gaya."
                            )
                            st.rerun()
                    st.markdown("---")
                    st.stop()
                pending_cells = st.session_state.get("fe_pending_cells")
                if pending_cells:
                    for i, cell in enumerate(pending_cells):
                        st.session_state[f"fe_drcr_{i}"] = cell[0]
                        st.session_state[f"fe_ledger_{i}"] = cell[1]
                        st.session_state[f"fe_debit_{i}"] = cell[2]
                        st.session_state[f"fe_credit_{i}"] = cell[3]
                        if len(cell) > 4 and cell[4]:
                            st.session_state[f"fe_billref_{i}"] = cell[4]
                    if "fe_pending_date" in st.session_state:
                        st.session_state["voucher_date"] = st.session_state["fe_pending_date"]
                    if "fe_pending_remarks" in st.session_state:
                        st.session_state["fe_remarks"] = st.session_state["fe_pending_remarks"]
                    st.session_state.pop("fe_pending_cells", None)
                    st.session_state.pop("fe_pending_date", None)
                    st.session_state.pop("fe_pending_remarks", None)
                st.markdown("""
                <div class="fe-topbar">
                    <div class="fe-brand">🧾 """ + (f"{voucher_mode} VOUCHER · EDIT #{editing_no}" if editing_group else f"{voucher_mode} VOUCHER · NEW") + """</div>
                    <div class="fe-company">🏢 SUBH PAPER COMPANY</div>
                    <div class="fe-help">❓ Help</div>
                </div>
                """, unsafe_allow_html=True)

                def _next_voucher_no(mode):
                    values = conn.execute("SELECT invoice_no FROM voucher_entries WHERE mode=?", (mode,)).fetchall()
                    nums = []
                    for (value,) in values:
                        try:
                            n = int(str(value).strip())
                            if n >= 0:
                                nums.append(n)
                        except (TypeError, ValueError):
                            continue
                    return (max(nums) + 1) if nums else 1

                # Secondary/Tally-style header: voucher number stays left, Date is always at the far right.
                h0, h1, h2, h3 = st.columns([0.75, 1.20, 1.25, 1.45])
                with h0:
                    if st.button("⬅ Types", key="fe_back_type", use_container_width=True, help="Voucher Type list par wapas jayen"):
                        for key in list(st.session_state.keys()):
                            if str(key).startswith("fe_") or key == "voucher_date":
                                st.session_state.pop(key, None)
                        st.rerun()
                if editing_group:
                    voucher_no = editing_no
                    h1.text_input("Voucher No.", value=str(voucher_no or ""), key="fe_edit_no_display", disabled=True)
                    h2.markdown("<div class='fe-note'><b>Tax Invoice</b></div>", unsafe_allow_html=True)
                    with h3:
                        voucher_date, voucher_date_str = get_date_input("Date (DD/MM/YYYY)", "voucher_date")
                else:
                    voucher_no = _next_voucher_no(voucher_mode)
                    h1.text_input("Voucher No.", value=str(voucher_no), key=f"fe_auto_voucher_no_{voucher_mode}", disabled=True)
                    h2.markdown(f"<div class='fe-note' style='padding-top:28px'><b>{html.escape(str(voucher_mode))}</b></div>", unsafe_allow_html=True)
                    with h3:
                        voucher_date, voucher_date_str = get_date_input("Date (DD/MM/YYYY)", "voucher_date")
            
            editing_group = st.session_state.get("fe_editing_group")
            ledger_options = [r[0] for r in conn.execute("SELECT ledger_name FROM ledger_master ORDER BY ledger_name").fetchall()]
            ledger_choices = ledger_options
            row_count = max(2, int(st.session_state.get("fe_row_count", 2)))
            show_billref = voucher_mode in ("Receipt", "Payment", "Purchase")
            BILL_REF_OPTIONS = ["Advance", "Agst Ref", "New ref", "on account"]
            rows=[]
            if show_billref:
                if show_billref:
                    _fe_head_cls = "fe-table-head"
                    _fe_head_cells = ("<div class='fe-drcr-head'>Dr / Cr</div>"
                                      "<div class='fe-ledger-head'>Ledger Head</div>"
                                      "<div class='fe-billref-head'>Bill Ref</div>"
                                      "<div class='fe-debit-head'>Debit (₹)</div>"
                                      "<div class='fe-credit-head'>Credit (₹)</div><div></div>")
                else:
                    _fe_head_cls = "fe-table-head-noref"
                    _fe_head_cells = ("<div class='fe-drcr-head'>Dr / Cr</div>"
                                      "<div class='fe-ledger-head'>Ledger Head</div>"
                                      "<div class='fe-debit-head'>Debit (₹)</div>"
                                      "<div class='fe-credit-head'>Credit (₹)</div><div></div>")
                st.markdown(f"""
            <div class="{_fe_head_cls}">
                {_fe_head_cells}
            </div>
            """, unsafe_allow_html=True)
                for i in range(row_count):
                    if show_billref:
                        c1,c2,c3,c4,c5,c6=st.columns([0.85,3.1,1.6,1.15,1.15,0.34])
                    else:
                        c1,c2,c3,c4,c5=st.columns([0.85,3.1,1.15,1.15,0.34])
                    drcr=c1.selectbox("Dr/Cr", ["Dr","Cr"], index=None, placeholder="Select", key=f"fe_drcr_{i}", label_visibility="collapsed")
                    ledger=c2.selectbox("Select Ledger", ledger_choices, index=None, placeholder="Select Ledger", key=f"fe_ledger_{i}", label_visibility="collapsed")
                    billref=None
                    if show_billref and ledger:
                        billref=c3.selectbox("Bill Ref", BILL_REF_OPTIONS, index=None, placeholder="Bill Ref", key=f"fe_billref_{i}", label_visibility="collapsed")
                    if show_billref:
                        debit=c4.number_input("Debit", min_value=0.0, step=0.01, value=None, format="%.2f", key=f"fe_debit_{i}", label_visibility="collapsed")
                        credit=c5.number_input("Credit", min_value=0.0, step=0.01, value=None, format="%.2f", key=f"fe_credit_{i}", label_visibility="collapsed")
                        delete_btn=c6.button("🗑", key=f"fe_delete_{i}", help="Delete this row")
                    else:
                        debit=c3.number_input("Debit", min_value=0.0, step=0.01, value=None, format="%.2f", key=f"fe_debit_{i}", label_visibility="collapsed")
                        credit=c4.number_input("Credit", min_value=0.0, step=0.01, value=None, format="%.2f", key=f"fe_credit_{i}", label_visibility="collapsed")
                        delete_btn=c5.button("🗑", key=f"fe_delete_{i}", help="Delete this row")
                    rows.append({"drcr":drcr, "ledger":ledger, "billref":billref, "debit":float(debit or 0) if drcr=="Dr" else 0.0, "credit":float(credit or 0) if drcr=="Cr" else 0.0, "delete":delete_btn})
            deleted=next((i for i,r in enumerate(rows) if r["delete"]),None)
            if deleted is not None:
                if row_count <= 2:
                    st.warning("At least two entry rows are required.")
                else:
                    for j in range(deleted, row_count-1):
                        src_i=j+1
                        for field in ("drcr","ledger","billref","debit","credit"):
                            sk=f"fe_{field}_{src_i}"
                            dk=f"fe_{field}_{j}"
                            if sk in st.session_state:
                                st.session_state[dk]=st.session_state[sk]
                    for field in ("drcr","ledger","billref","debit","credit"):
                        st.session_state.pop(f"fe_{field}_{row_count-1}",None)
                    st.session_state["fe_row_count"]=row_count-1
                    st.rerun()
            if st.button("＋ Add More", key="fe_add_more"):
                st.session_state["fe_row_count"]=row_count+1
                st.rerun()
            # Tally-style keyboard flow + contextual right-side list.
            # When the user tabs/clicks into Item, Bill Ref, GST/Tax or Other,
            # the matching list is highlighted in the right-side panel.
            st.components.v1.html("""
            <script>
            (()=>{
              const root=window.parent.document;
              const scan=()=>{
                root.querySelectorAll('[data-testid="stHorizontalBlock"]').forEach(b=>{
                  const cb=b.querySelectorAll('[role="combobox"]');
                  const inp=b.querySelectorAll('input[data-testid="stNumberInputField"]');
                  if (!cb.length || inp.length<2) return;
                  const t=(cb[0].textContent||'').trim();
                  if (t==='Dr' && inp[0]) inp[0].focus();
                  else if (t==='Cr' && inp[1]) inp[1].focus();
                });
              };
              const setContext=(name)=>{
                root.querySelectorAll('[data-subh-context]').forEach(x=>{
                  const active=x.getAttribute('data-subh-context')===name;
                  x.style.display=active?'block':'none';
                });
                root.querySelectorAll('[data-subh-context-tab]').forEach(x=>{
                  x.style.fontWeight=x.getAttribute('data-subh-context-tab')===name?'800':'600';
                  x.style.background=x.getAttribute('data-subh-context-tab')===name?'#dff5f1':'#eef7f5';
                });
              };
              const bind=()=>{
                root.querySelectorAll('[data-testid="stSelectbox"]').forEach(box=>{
                  if(box.dataset.subhCtxBound==='1') return;
                  box.dataset.subhCtxBound='1';
                  const text=(box.innerText||'').toLowerCase();
                  let ctx='ledger';
                  if(text.includes('item')) ctx='item';
                  else if(text.includes('bill ref')) ctx='bill';
                  else if(text.includes('gst') || text.includes('tax')) ctx='gst';
                  box.addEventListener('focusin',()=>setContext(ctx),true);
                  box.addEventListener('click',()=>setContext(ctx),true);
                });
                root.querySelectorAll('input,textarea').forEach(el=>{
                  if(el.dataset.subhCtxBound==='1') return;
                  el.dataset.subhCtxBound='1';
                  const box=el.closest('[data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stTextArea"]');
                  const text=(box?.innerText||'').toLowerCase();
                  let ctx=text.includes('gst')||text.includes('tax')?'gst':text.includes('bill')?'bill':text.includes('other')?'other':'ledger';
                  el.addEventListener('focusin',()=>setContext(ctx),true);
                });
              };
              scan(); bind();
              if(window.__subhCtxTimer) clearInterval(window.__subhCtxTimer);
              window.__subhCtxTimer=setInterval(()=>{scan();bind();},700);
            })();
            </script>
            """, height=0)
            # ---------------- SECONDARY VOUCHER CONTEXT PANEL ----------------
            # Kept beside the entry area so Tab/click navigation feels like the
            # supplied Tally-style screen. Item/Bill Ref/GST/Other use the same
            # compact right-side list style.
            # ---------------- INVENTORY MODE (PURCHASE) ----------------
            inventory_items_meta = {}
            inv_rows_captured = []
            if voucher_mode == "Purchase":
                inv_rows_sql = conn.execute(
                    "SELECT item_name, unit, rate FROM inventory_item_master ORDER BY item_name"
                ).fetchall()
                inventory_items_meta = {r[0]: {"unit": r[1] or "", "rate": float(r[2] or 0)} for r in inv_rows_sql}
                inventory_item_choices = list(inventory_items_meta.keys())
                inv_count = max(1, int(st.session_state.get("fe_inv_count", 1)))
                st.markdown("<div class='inv-table-head'>📦 📦 Inventory Items</div>", unsafe_allow_html=True)
                inv_rows_captured = []
                for ii in range(inv_count):
                    ic1, ic2, ic3, ic4, ic5, ic6 = st.columns([3.4, 0.9, 1.1, 1.1, 1.2, 0.4])
                    item = ic1.selectbox("Item", inventory_item_choices, index=None, placeholder="Select Item", key=f"fe_inv_item_{ii}", label_visibility="collapsed")
                    qty = ic2.number_input("Qty", min_value=0.0, step=0.01, value=None, format="%.2f", key=f"fe_inv_qty_{ii}", label_visibility="collapsed")
                    meta = inventory_items_meta.get(item) if item else None
                    qty_val = float(qty or 0)
                    rate_val = meta["rate"] if meta else 0.0
                    amt_val = round(qty_val * rate_val, 2)
                    unit_txt = html.escape((meta["unit"] if meta else "") or "-")
                    ic3.markdown(f"<div class='inv-unit'>📦 {unit_txt}</div>", unsafe_allow_html=True)
                    ic4.markdown(f"<div class='inv-unit'>₹ {rate_val:,.2f}</div>", unsafe_allow_html=True)
                    ic5.markdown(f"<div class='inv-unit amt'>₹ {amt_val:,.2f}</div>", unsafe_allow_html=True)
                    del_btn = ic6.button("🗑", key=f"fe_inv_del_{ii}", help="Delete this item")
                    inv_rows_captured.append({"item": item, "unit": (meta["unit"] if meta else ""), "qty_val": qty_val, "rate_val": rate_val, "amt_val": amt_val, "delete": del_btn})
                inv_deleted = next((i for i, r in enumerate(inv_rows_captured) if r["delete"]), None)
                if inv_deleted is not None:
                    if inv_count <= 1:
                        st.warning("At least one inventory item row is required.")
                    else:
                        for fj in range(inv_deleted, inv_count - 1):
                            s2 = fj + 1
                            for field in ("item", "qty"):
                                sk = f"fe_inv_{field}_{s2}"
                                dk = f"fe_inv_{field}_{fj}"
                                if sk in st.session_state:
                                    st.session_state[dk] = st.session_state[sk]
                        for field in ("item", "qty"):
                            st.session_state.pop(f"fe_inv_{field}_{inv_count - 1}", None)
                        st.session_state["fe_inv_count"] = inv_count - 1
                        st.rerun()
                if st.button("＋ Add Item", key="fe_inv_add_more"):
                    st.session_state["fe_inv_count"] = inv_count + 1
                    st.rerun()
                total_inv_amount = round(sum(r["amt_val"] for r in inv_rows_captured), 2)
                st.markdown(f"<div class='inv-total'><b>Total Inventory Value:</b> ₹ {total_inv_amount:,.2f}</div>", unsafe_allow_html=True)
            with st.expander("➕ Create Ledger", expanded=False):
                lc1,lc2=st.columns([4,1])
                new_ledger_name=lc1.text_input("Ledger Name", key="fe_new_ledger_name", placeholder="Enter new ledger name")
                if lc2.button("Create Ledger", key="fe_create_ledger"):
                    ledger_name_clean=new_ledger_name.strip()
                    if not ledger_name_clean:
                        st.error("Ledger name is required.")
                    else:
                        exists=conn.execute("SELECT 1 FROM ledger_master WHERE LOWER(ledger_name)=LOWER(?)", (ledger_name_clean,)).fetchone()
                        if exists:
                            st.warning("This ledger already exists.")
                        else:
                            conn.execute("INSERT INTO ledger_master (ledger_name) VALUES (?)", (ledger_name_clean,))
                            conn.commit()
                            st.success(f"Ledger '{ledger_name_clean}' created successfully.")
                            st.rerun()
            remarks=st.text_area("Remarks", key="fe_remarks", placeholder="Enter narration / remarks", height=90)
            total_debit=round(sum(r["debit"] for r in rows),2)
            total_credit=round(sum(r["credit"] for r in rows),2)
            if editing_group:
                b1,b2=st.columns([1.25,1.25])
                save_clicked=b1.button("💾 Save Update (Replace Voucher)", type="primary", use_container_width=True, key="fe_save_edit_voucher")
                clear_clicked=b2.button("🧹 Clear Form (F6)", use_container_width=True, key="fe_clear_voucher")
            else:
                b1,b2=st.columns([1.25,1.25])
                save_clicked=b1.button("💾 Save Voucher (F11)", type="primary", use_container_width=True, key="fe_save_voucher")
                clear_clicked=b2.button("🧹 Clear Form (F6)", use_container_width=True, key="fe_clear_voucher")
            st.markdown(f"<div class='fe-totals'><span><b>Total Debit:</b> ₹ {total_debit:,.2f}</span><span><b>Total Credit:</b> ₹ {total_credit:,.2f}</span></div>", unsafe_allow_html=True)
            if clear_clicked:
                for key in list(st.session_state.keys()):
                    if key.startswith("fe_"):
                        st.session_state.pop(key,None)
                st.session_state["fe_row_count"]=2
                st.rerun()
            if save_clicked:
                valid_rows=[r for r in rows if r["ledger"] and r["ledger"]!="Select Ledger" and (r["debit"]>0 or r["credit"]>0)]
                inv_rows_for_save = []
                inv_total = 0.0
                if voucher_mode == "Purchase":
                    for ir in inv_rows_captured:
                        if ir["item"] and ir["item"] in inventory_items_meta and ir["qty_val"] > 0:
                            inv_rows_for_save.append(ir)
                            inv_total += ir["amt_val"]
                    inv_total = round(inv_total, 2)
                if editing_group:
                    vno = str(editing_no or "")
                else:
                    vno = _next_voucher_no(voucher_mode)
                calc_debit = total_debit + (inv_total if voucher_mode == "Purchase" else 0.0)
                calc_credit = total_credit
                if vno is None:
                    pass
                elif not valid_rows and not inv_rows_for_save:
                    st.error("Please enter at least one ledger/amount or an inventory item.")
                elif not voucher_date:
                    st.error("Please select an entry Date from the calendar.")
                elif abs(calc_debit-calc_credit)>0.005:
                    st.error("Debit and Credit totals must be equal (including inventory).")
                else:
                    if editing_ids:
                        placeholders = ",".join("?" for _ in editing_ids)
                        conn.execute(f"DELETE FROM voucher_entries WHERE id IN ({placeholders})", editing_ids)
                    if editing_group and vno:
                        _old_inv = conn.execute(
                            "SELECT item_name, qty FROM voucher_inventory_items WHERE mode=? AND voucher_no=?",
                            (voucher_mode, str(vno))
                        ).fetchall()
                        _restore_sign = -1
                        for inv_item, inv_q in _old_inv:
                            conn.execute(
                                "UPDATE inventory_item_master SET quantity = COALESCE(quantity,0) + ? WHERE item_name = ?",
                                (_restore_sign * float(inv_q or 0), inv_item)
                            )
                        conn.execute("DELETE FROM voucher_inventory_items WHERE mode=? AND voucher_no=?", (voucher_mode, str(vno)))
                    for r in valid_rows:
                        amount = r["debit"] if r["drcr"] == "Dr" else r["credit"]
                        billref_val = r.get("billref") or ""
                        conn.execute(
                            """INSERT INTO voucher_entries
                            (mode, entry_date, invoice_no, dr_cr, ledger_head,
                             invoice_amount, tds, net_amount, remarks, bill_ref)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (voucher_mode, voucher_date_str, str(vno),
                             r["drcr"], r["ledger"], amount, 0.0, amount, remarks.strip(), billref_val)
                        )
                    if inv_rows_for_save:
                        auto_drcr, auto_ledger = "Dr", "Purchase Account"
                        conn.execute(
                            """INSERT INTO voucher_entries
                            (mode, entry_date, invoice_no, dr_cr, ledger_head,
                             invoice_amount, tds, net_amount, remarks, bill_ref)
                            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (voucher_mode, voucher_date_str, str(vno),
                             auto_drcr, auto_ledger, inv_total, 0.0, inv_total, remarks.strip(), "Inventory")
                        )
                        for ir in inv_rows_for_save:
                            conn.execute(
                                """INSERT INTO voucher_inventory_items
                                (voucher_no, mode, entry_date, item_name, unit, qty, rate, amount)
                                VALUES (?,?,?,?,?,?,?,?)""",
                                (str(vno), voucher_mode, voucher_date_str,
                                 ir["item"], ir.get("unit") or "", ir["qty_val"], ir["rate_val"], ir["amt_val"])
                            )
                            _sign = 1
                            conn.execute(
                                "UPDATE inventory_item_master SET quantity = COALESCE(quantity,0) + ? WHERE item_name = ?",
                                (_sign * ir["qty_val"], ir["item"])
                            )
                    # recompute displayed totals including inventory
                    display_debit = round(total_debit + (inv_total if voucher_mode == "Purchase" else 0.0), 2)
                    display_credit = round(total_credit, 2)
                    conn.commit()
                    if editing_group:
                        for key in ("fe_editing_group","fe_editing_no","fe_editing_ids"):
                            st.session_state.pop(key, None)
                        st.session_state["fe_flash"] = f"Voucher {voucher_mode} #{vno} updated successfully."
                    else:
                        _reset_entry_mode_form_fields()
                        st.session_state["fe_saved"] = True
                        st.session_state["fe_saved_no"] = str(vno)
                        st.session_state["fe_saved_mode"] = voucher_mode
                        st.session_state["fe_saved_date"] = voucher_date_str
                        st.session_state["fe_saved_debit"] = display_debit
                        st.session_state["fe_saved_credit"] = display_credit
                    st.rerun()
            
            # ---------------- TALLY VOUCHER REGISTER (PERIOD WISE) ----------------
            st.markdown("<div class='tally-register-head'>📒 VOUCHER REGISTER · PERIOD WISE</div>", unsafe_allow_html=True)
            rp1, rp2 = st.columns(2)
            _today_d = datetime.date.today()
            _fy_start = datetime.date(_today_d.year - 1 if _today_d.month < 4 else _today_d.year, 4, 1)
            with rp1:
                reg_from, reg_from_str = get_date_input("From Date", "fe_reg_from", default_value=_fy_start.strftime('%d/%m/%Y'))
            with rp2:
                reg_to, reg_to_str = get_date_input("To Date", "fe_reg_to", default_value=get_today_str())

            grouped = {}
            if reg_from and reg_to and reg_from > reg_to:
                st.error("From Date cannot be later than To Date.")
            else:
                fetch_rows = conn.execute(
                    "SELECT id, mode, entry_date, invoice_no, dr_cr, ledger_head, invoice_amount, tds, net_amount, remarks, bill_ref "
                    "FROM voucher_entries ORDER BY entry_date ASC, id ASC"
                ).fetchall()
                for row in fetch_rows:
                    row_id, mode, entry_date, invoice_no, dr_cr, ledger_head, invoice_amount, tds, net_amount, remarks = row[:10]
                    group_key = (str(mode or ""), str(invoice_no or ""))
                    if group_key not in grouped:
                        grouped[group_key] = {"id": row_id, "mode": mode, "date": entry_date, "invoice_no": invoice_no, "rows": []}
                    grouped[group_key]["id"] = min(int(grouped[group_key]["id"]), int(row_id))
                    grouped[group_key]["rows"].append(row)

                reg_groups = []
                for group in grouped.values():
                    gd = parse_date_input(str(group["date"] or ""))
                    if gd and reg_from and reg_to and (gd < reg_from or gd > reg_to):
                        continue
                    reg_groups.append(group)
                reg_groups.sort(key=lambda g: (parse_date_input(str(g["date"])) or datetime.date(1900, 1, 1), g["id"]))

                if not reg_groups:
                    st.info("Is period me koi voucher available nahi hai.")
                else:
                    st.markdown(
                        "<div class='tally-reg-colhead'><span>Date</span><span>Voucher No.</span><span>Type</span>"
                        "<span>Parties / Narration</span><span>Debit ₹</span><span>Credit ₹</span><span>Actions</span></div>",
                        unsafe_allow_html=True
                    )
                    for group in reg_groups:
                        gid = group["id"]
                        tdr = round(sum(float(r[6] or 0) for r in group["rows"] if str(r[4]).upper() == "DR"), 2)
                        tcr = round(sum(float(r[6] or 0) for r in group["rows"] if str(r[4]).upper() == "CR"), 2)
                        parties = ", ".join(dict.fromkeys(str(r[5]) for r in group["rows"]))[:60]
                        nar = str(group["rows"][0][9] or "").strip()[:40]
                        party_txt = (parties + (" | " + nar if nar else ""))[:75]
                        c1, c2, c3, c4, c5, c6, c7 = st.columns([0.85, 0.95, 0.95, 2.3, 1.0, 1.0, 1.7])
                        c1.markdown(f"<div class='fe-reg-cell'>{html.escape(str(group['date'] or '-'))}</div>", unsafe_allow_html=True)
                        c2.markdown(f"<div class='fe-reg-cell strong'>{html.escape(str(group['invoice_no'] or '-'))}</div>", unsafe_allow_html=True)
                        c3.markdown(f"<div class='fe-reg-cell'>{html.escape(str(group['mode']))}</div>", unsafe_allow_html=True)
                        c4.markdown(f"<div class='fe-reg-cell small'>{html.escape(party_txt)}</div>", unsafe_allow_html=True)
                        c5.markdown(f"<div class='fe-reg-cell amt'>{tdr:,.2f}</div>", unsafe_allow_html=True)
                        c6.markdown(f"<div class='fe-reg-cell amt'>{tcr:,.2f}</div>", unsafe_allow_html=True)
                        with c7:
                            a1, a2, a3 = st.columns([1, 1, 1])
                            open_clicked = a1.button("↩", key=f"fe_open_{gid}", help="Tally-style: voucher par 'Enter' jab ke barabar — entry kholein")
                            print_clicked = a2.button("🖨", key=f"fe_print_{gid}", help="Voucher preview / print")
                            del_clicked = a3.button("🗑", key=f"fe_del_{gid}", help="Voucher delete karein")
                        if del_clicked:
                            ids = [int(r[0]) for r in group["rows"]]
                            placeholders = ",".join("?" for _ in ids)
                            conn.execute(f"DELETE FROM voucher_entries WHERE id IN ({placeholders})", ids)
                            gmode = str(group["mode"])
                            gno = str(group["invoice_no"] or "")
                            if gmode in ("Sale", "Purchase"):
                                inv_to_restore = conn.execute(
                                    "SELECT item_name, qty FROM voucher_inventory_items WHERE mode=? AND voucher_no=?", (gmode, gno)
                                ).fetchall()
                                _restore_sign = 1 if gmode == "Sale" else -1
                                for inv_item, inv_q in inv_to_restore:
                                    conn.execute(
                                        "UPDATE inventory_item_master SET quantity = COALESCE(quantity,0) + ? WHERE item_name = ?",
                                        (_restore_sign * float(inv_q or 0), inv_item)
                                    )
                                conn.execute("DELETE FROM voucher_inventory_items WHERE mode=? AND voucher_no=?", (gmode, gno))
                            conn.commit()
                            if st.session_state.get("fe_editing_group") is not None:
                                for key in ("fe_editing_group", "fe_editing_no", "fe_editing_ids"):
                                    st.session_state.pop(key, None)
                            st.session_state["fe_flash"] = f"Voucher {group['mode']} #{group['invoice_no']} deleted successfully."
                            st.rerun()
                        if open_clicked:
                            group_key = f"{group['mode']}|{group['invoice_no']}"
                            st.session_state["fe_mode"] = group["mode"]
                            st.session_state["fe_editing_group"] = group_key
                            st.session_state["fe_editing_no"] = str(group["invoice_no"])
                            st.session_state["fe_editing_ids"] = [int(r[0]) for r in group["rows"]]
                            st.session_state["fe_row_count"] = len(group["rows"])
                            g_rows = group["rows"]
                            pending_cells = []
                            for r in g_rows:
                                is_dr = str(r[4]).upper() == "DR"
                                pending_cells.append(
                                    ("Dr" if is_dr else "Cr", str(r[5]),
                                     (float(r[6] or 0) if is_dr else 0.0),
                                     (float(r[6] or 0) if not is_dr else 0.0),
                                     (str(r[10] or ""))
                                    )
                                )
                            st.session_state["fe_pending_cells"] = pending_cells
                            gmode_for_inv = str(group["mode"])
                            if gmode_for_inv in ("Sale", "Purchase"):
                                ginv = conn.execute(
                                    "SELECT item_name, unit, qty, rate, amount FROM voucher_inventory_items WHERE mode=? AND voucher_no=? ORDER BY id",
                                    (gmode_for_inv, str(group["invoice_no"] or ""))
                                ).fetchall()
                                if ginv:
                                    st.session_state["fe_inv_count"] = len(ginv)
                                    for inv_idx, (inv_item, inv_unit, inv_q, inv_rate, inv_amt) in enumerate(ginv):
                                        st.session_state[f"fe_inv_item_{inv_idx}"] = inv_item
                                        st.session_state[f"fe_inv_qty_{inv_idx}"] = float(inv_q or 0)
                            pd_ = parse_date_input(str(group["date"] or ""))
                            if pd_:
                                st.session_state["fe_pending_date"] = pd_
                            st.session_state["fe_pending_remarks"] = str(g_rows[0][9] or "")
                            st.session_state["fe_saved"] = False
                            st.rerun()
                        if print_clicked:
                            st.session_state["fe_print_group"] = f"{group['mode']}|{group['invoice_no']}"
                            st.rerun()

            def _voucher_print_html(group):
                title = str(group["mode"]).upper()
                vno = group["invoice_no"]
                vdate = group["date"] or "-"
                lines = []
                for r in group["rows"]:
                    rid, m, d, no, dc, lh, amt, tds, net, rmk = r
                    is_dr = str(dc).upper() == "DR"
                    lines.append(
                        f"<tr><td>{html.escape(str(lh))}</td>"
                        f"<td style='text-align:right'>{(float(amt or 0) if is_dr else 0):,.2f}</td>"
                        f"<td style='text-align:right'>{(float(amt or 0) if not is_dr else 0):,.2f}</td></tr>"
                    )
                tdr = round(sum(float(r[6] or 0) for r in group["rows"] if str(r[4]).upper() == "DR"), 2)
                tcr = round(sum(float(r[6] or 0) for r in group["rows"] if str(r[4]).upper() == "CR"), 2)
                narration = html.escape(str(group["rows"][0][9] or ""))
                return f"""
                <div class="voucher-print-page">
                    <div class="vp-co">SUBH PAPER COMPANY</div>
                    <div class="vp-addr">CORVALLIS ROAD · MANAGEMENT DOCUMENT</div>
                    <div class="vp-title">{title} VOUCHER</div>
                    <div class="vp-meta">
                        <span>Voucher No : {html.escape(str(vno or '-'))}</span>
                        <span>Date : {html.escape(str(vdate))}</span>
                        <span>Period : {html.escape(str(reg_from_str))} to {html.escape(str(reg_to_str))}</span>
                    </div>
                    <table>
                        <thead><tr><th style='text-align:left'>Ledger</th><th style='text-align:right'>Debit (₹)</th><th style='text-align:right'>Credit (₹)</th></tr></thead>
                        <tbody>{''.join(lines)}</tbody>
                        <tfoot><tr class='vp-total-row'><td>Total</td><td style='text-align:right'>{tdr:,.2f}</td><td style='text-align:right'>{tcr:,.2f}</td></tr></tfoot>
                    </table>
                    <div class="vp-narration">Narration : {narration or '—'}</div>
                    <div class="vp-sig"><span>Prepared By</span><span>Authorised Signatory</span></div>
                </div>"""

            print_key = st.session_state.get("fe_print_group")
            if print_key:
                pg = next((g for g in grouped.values() if f"{g['mode']}|{g['invoice_no']}" == print_key), None)
                if pg:
                    with st.expander(f"🖨 Print Preview — {pg['mode']} Voucher #{pg['invoice_no']}", expanded=True):
                        st.markdown(_voucher_print_html(pg), unsafe_allow_html=True)
                        st.download_button(
                            "⬇ Download Voucher (HTML) — browser me kholein, phir Ctrl+P se Print karein",
                            data=_voucher_print_html(pg).encode("utf-8"),
                            file_name=f"Voucher_{pg['mode']}_{pg['invoice_no']}.html",
                            mime="text/html",
                            use_container_width=True,
                            key="fe_download_print"
                        )

    # ------------------ FORM 9: CONSUMABLE / CF ENTRY ------------------
    elif chosen_module == "9. Consumable / CF Entry":
        st.subheader("🧰 Consumable / CF Entry")

        item_options = get_consumable_cf_item_options(conn)

        # Select an existing saved entry when Update/Delete is required.
        try:
            saved_rows = conn.execute(
                "SELECT id, entry_date, in_out, item_name, quantity, min_label, remarks "
                "FROM consumable_cf_entries ORDER BY id DESC"
            ).fetchall()
        except Exception:
            saved_rows = []

        entry_labels = ["➕ New Entry"]
        entry_id_by_label = {}
        for row in saved_rows:
            entry_id = int(row[0])
            label = f"ID {entry_id} | {row[1] or ''} | {row[3] or ''} | {row[2] or ''} | Qty {float(row[4] or 0):g}"
            entry_labels.append(label)
            entry_id_by_label[label] = entry_id

        # Apply a requested selector reset before the widget is instantiated.
        # Streamlit does not allow changing a widget's keyed session state after
        # that widget has already been created in the current run.
        if st.session_state.pop("cf_reset_selected_entry", False):
            st.session_state["cf_selected_entry"] = "➕ New Entry"

        selected_entry_label = st.selectbox(
            "Saved Entry (for Update / Delete)",
            entry_labels,
            key="cf_selected_entry"
        )
        selected_entry_id = entry_id_by_label.get(selected_entry_label)

        selected_row = None
        if selected_entry_id is not None:
            selected_row = next((r for r in saved_rows if int(r[0]) == selected_entry_id), None)

        if selected_row:
            default_date = selected_row[1] or ""
            default_in_out = selected_row[2] or ""
            default_item = selected_row[3] or ""
            default_qty = float(selected_row[4] or 0)
            default_min = float(selected_row[5] or 0)
            default_remarks = selected_row[6] or ""
        else:
            default_date = ""
            default_in_out = ""
            default_item = ""
            default_qty = None
            default_min = None
            default_remarks = ""

        # Compact single-line entry layout.
        # Dynamic widget keys ensure that selecting another saved entry loads
        # that entry's values correctly instead of reusing the previous values.
        cf_key_suffix = str(selected_entry_id) if selected_entry_id is not None else "new"
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            cf_date, cf_date_str = get_date_input(
                "Date (DD/MM/YYYY)", f"cf_entry_date_{cf_key_suffix}", default_value=default_date
            )
        with c2:
            in_out = st.selectbox(
                "In / Out", ["In", "Out"],
                index=(["In", "Out"].index(default_in_out) if default_in_out in ["In", "Out"] else None),
                placeholder="Select",
                key=f"cf_in_out_{cf_key_suffix}"
            )
        with c3:
            item_choices = item_options.copy()
            if default_item and default_item not in item_choices:
                item_choices.append(default_item)
            item_choices.append("➕ Add New Item")
            item_index = item_choices.index(default_item) if default_item in item_choices else None
            item_choice = st.selectbox(
                "Item List", item_choices,
                index=item_index, placeholder="Select Item", key=f"cf_item_choice_{cf_key_suffix}"
            )
        new_item = ""
        if item_choice == "➕ Add New Item":
            new_item = st.text_input("New Item Name", key=f"cf_new_item_{cf_key_suffix}").strip()
        item_name = new_item if item_choice == "➕ Add New Item" else (item_choice or "")
        with c4:
            quantity = st.number_input(
                "Quantity", min_value=0.0, step=0.01, value=default_qty, key=f"cf_qty_{cf_key_suffix}"
            )
        with c5:
            min_label = st.number_input(
                "Min. Label", min_value=0.0, step=0.01, value=default_min, key=f"cf_min_label_{cf_key_suffix}"
            )
        with c6:
            remarks = st.text_input("Remarks", value=default_remarks, key=f"cf_remarks_{cf_key_suffix}")

        b1, b2, b3, b4 = st.columns(4)

        if b1.button("Save", type="primary", use_container_width=True, key="save_cf_entry"):
            if selected_entry_id is not None:
                st.warning("Please select New Entry before saving a new entry.")
            elif cf_date is None:
                st.error("Please enter Date.")
            elif not in_out:
                st.error("Please select In / Out.")
            elif not item_name:
                st.error("Please select or enter Item Name.")
            elif quantity <= 0:
                st.error("Quantity must be greater than zero.")
            else:
                conn.execute(
                    "INSERT INTO consumable_cf_entries (entry_date,in_out,item_name,quantity,min_label,remarks) VALUES (?,?,?,?,?,?)",
                    (cf_date_str, in_out, item_name.strip(), float(quantity), float(min_label), remarks.strip())
                )
                conn.commit()
                st.success("Consumable / CF Entry saved successfully.")
                _reset_entry_mode_form_fields()
                st.rerun()

        if b2.button("Update", use_container_width=True, key="update_cf_entry"):
            if selected_entry_id is None:
                st.warning("Please select a saved entry to update.")
            elif cf_date is None or not in_out or not item_name:
                st.error("Date, In / Out and Item Name are required.")
            elif quantity <= 0:
                st.error("Quantity must be greater than zero.")
            else:
                conn.execute(
                    "UPDATE consumable_cf_entries SET entry_date=?, in_out=?, item_name=?, quantity=?, min_label=?, remarks=? WHERE id=?",
                    (cf_date_str, in_out, item_name.strip(), float(quantity), float(min_label), remarks.strip(), int(selected_entry_id))
                )
                conn.commit()
                st.success(f"Consumable / CF Entry ID {selected_entry_id} updated successfully.")
                _reset_entry_mode_form_fields()
                st.session_state["cf_reset_selected_entry"] = True
                st.rerun()

        if b3.button("Delete", use_container_width=True, key="delete_cf_entry"):
            if selected_entry_id is None:
                st.warning("Please select a saved entry to delete.")
            else:
                conn.execute("DELETE FROM consumable_cf_entries WHERE id=?", (int(selected_entry_id),))
                conn.commit()
                st.success(f"Consumable / CF Entry ID {selected_entry_id} deleted successfully.")
                _reset_entry_mode_form_fields()
                st.session_state["cf_reset_selected_entry"] = True
                st.rerun()

        if b4.button("Clear Form", use_container_width=True, key="clear_cf_form"):
            st.session_state["cf_reset_selected_entry"] = True
            for key in list(st.session_state.keys()):
                if str(key).startswith(("cf_entry_date_", "cf_in_out_", "cf_item_choice_", "cf_new_item_", "cf_qty_", "cf_min_label_", "cf_remarks_")):
                    st.session_state.pop(key, None)
            st.rerun()

        try:
            cf_df = pd.read_sql_query(
                "SELECT id AS ID, entry_date AS Date, in_out AS 'In/Out', item_name AS 'Item Name', quantity AS Quantity, min_label AS 'Min. Label', remarks AS Remarks FROM consumable_cf_entries ORDER BY id DESC",
                conn
            )
            st.dataframe(cf_df, use_container_width=True, hide_index=True)
        except Exception:
            pass

    conn.close()
