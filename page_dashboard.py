# ==============================================================================
# PAGE MODULE: DASHBOARD
# ==============================================================================
# Real-time executive dashboard.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *

@st.cache_data(ttl=12, show_spinner=False)
def _load_dash_data():
    """Load all dashboard aggregates in one cached call.

    Turso par har query network round-trip hai, isliye poori dashboard data
    load 12s TTL ke saath cache karte hain.
    """
    _conn = get_db_connection(private=True)
    try:
        t_ord = float(pd.read_sql_query("SELECT SUM(CAST(order_qty AS REAL)) FROM order_entries", _conn).iloc[0, 0] or 0)
        t_prod = float(pd.read_sql_query("SELECT SUM(CAST(ok_notebook AS REAL)) FROM production_form_entries", _conn).iloc[0, 0] or 0)
        t_desp = float(pd.read_sql_query("SELECT SUM(CAST(despatch_qty AS REAL)) FROM despatch_form_entries", _conn).iloc[0, 0] or 0)
        paper_status = _dashboard_paper_status(_conn)
        board_sizes, board_balances, board_wip_balances = _dashboard_board_status(_conn)
        order_status = _dashboard_order_status(_conn)
        cf = pd.read_sql_query(
            "SELECT id, item_name, in_out, quantity, min_label FROM consumable_cf_entries ORDER BY id", _conn
        )
        return t_ord, t_prod, t_desp, paper_status, board_sizes, board_balances, board_wip_balances, order_status, cf
    finally:
        try:
            _conn.close()
        except Exception:
            pass

@st.cache_data(ttl=30, show_spinner=False)
def _load_hr_counts():
    _hr_conn = get_db_connection(private=True)
    try:
        wages = int(_hr_conn.execute("SELECT COUNT(*) FROM hr_employee_master WHERE category='Wages'").fetchone()[0])
        payroll = int(_hr_conn.execute("SELECT COUNT(*) FROM hr_employee_master WHERE category='Payroll'").fetchone()[0])
        return wages, payroll
    except Exception:
        return 0, 0
    finally:
        try:
            _hr_conn.close()
        except Exception:
            pass

def render():
    st.markdown("<h2 class='section-header dashboard-main-title'>📈 Real-time Corporate Executive Dashboard Summary</h2>", unsafe_allow_html=True)
    render_financial_year_control()
    try:
        t_ord, t_prod, t_desp, paper_status, board_sizes, board_balances, board_wip_balances, order_status, cf = _load_dash_data()

        # Total Finished Storage (OK Volume) must use the exact totals shown
        # in ORDER, PRODUCTION AND DESPATCH STATUS:
        # Column 6 (Production) total minus Column 8 (Despatched) total.
        # This intentionally uses the report rows, not all raw production/
        # despatch entries in the database.
        if not order_status.empty:
            report_production_total = float(pd.to_numeric(order_status["Production"], errors="coerce").fillna(0).sum())
            report_despatched_total = float(pd.to_numeric(order_status["Despatched"], errors="coerce").fillna(0).sum())
        else:
            report_production_total = 0.0
            report_despatched_total = 0.0
        total_finished_storage = report_production_total - report_despatched_total

        paper_total = sum(row[3] for row in paper_status)
        board_total = sum(sum(values) for values in board_balances.values()) + sum(sum(values) for values in board_wip_balances.values())
        total_est_prod = float(t_prod)

        est_paper_req = 0.0
        # Est. Board Req.: Product Code 3rd digit 3 => Order Qty / 8; 3rd digit 5 => Order Qty / 3.
        est_board_req = 0.0
        if not order_status.empty:
            for _, rr in order_status.iterrows():
                code = str(rr["Barcode"])
                page, _, third = parse_product_code(code)
                col6 = page or 0
                if code in {"1132101132", "1132201140", "1132103132", "1132203140", "1132205140", "1132208140"}:
                    col6 = 120
                order_val = _safe_num(rr["Order"])
                prod_val = _safe_num(rr["Production"])
                order_qty_value = order_val - prod_val
                if third == "5":
                    paper_gsm, reel_w, cutoff = 57, 90, 43
                    paper_wt = (paper_gsm * reel_w * cutoff) / 20000 / 500 * (col6 / 12)
                    # Exact requested dashboard rule: 3rd digit 5 => Order Qty / 3.
                    est_board_req += order_qty_value / 3.0
                elif third == "3":
                    paper_gsm = 54 if page is not None and page <= 56 else 57
                    paper_wt = (paper_gsm * 97 * 37) / 20000 / 500 * (col6 / 16)
                    # Exact requested dashboard rule: 3rd digit 3 => Order Qty / 8.
                    est_board_req += order_qty_value / 8.0
                else:
                    paper_wt = 0.0
                est_paper_req += order_qty_value * paper_wt

        # Additional requirement can never be negative.
        additional_paper_required = max(0.0, est_paper_req - paper_total)
        additional_board_required = max(0.0, est_board_req - board_total)
        # Consumable alert: count unique items whose current closing stock is below their latest Min. Label.
        consu_alert_count = 0
        if cf is not None and not cf.empty:
            for item, g in cf.groupby("item_name"):
                closing = g.apply(lambda r: float(r["quantity"] or 0) if str(r["in_out"]).lower()=="in" else -float(r["quantity"] or 0), axis=1).sum()
                latest_min = float(g.iloc[-1]["min_label"] or 0)
                if latest_min > 0 and closing < latest_min:
                    consu_alert_count += 1
        consu_alert = str(consu_alert_count)
    except Exception:
        t_ord, t_prod, t_desp = 0, 0, 0
        total_finished_storage = 0.0
        paper_status = [(s, 0.0, 0.0, 0.0) for s in ["97x37x57", "90x43x57", "97x37x54"]]
        board_sizes = ["45.5x91x190", "45.5x98x200", "91x91x190", "77x98x190"]
        board_balances = {}
        board_wip_balances = {}
        order_status = pd.DataFrame()
        paper_total = board_total = total_est_prod = est_paper_req = est_board_req = 0.0
        additional_paper_required = additional_board_required = 0.0
        consu_alert_count = 0
        consu_alert = "0"

    # Compact embossed KPI/status boxes.
    top_items = [
        ("📅", "Date", get_today_str(), "blue"),
        ("👥", "Wages", "—", "blue"),
        ("👥", "Payroll", "—", "blue"),
        ("📄", "Paper", f"{paper_total:,.0f} Kg.", "green"),
        ("▣", "Board", f"{board_total:,.0f}", "orange"),
        ("⚠", "Consu. Alert", consu_alert, "amber"),
        ("🏭", "Total Production", f"{total_est_prod:,.0f} Pcs", "green"),
        ("📄", "Est. Paper Req.", f"{est_paper_req:,.0f} Kg.", "blue"),
        ("▣", "Est. Board Req.", f"{est_board_req:,.0f}", "orange"),
        ("📄", "Add. Paper Rq.", f"{additional_paper_required:,.0f} Kg.", "green"),
        ("▣", "Add. Board Req.", f"{additional_board_required:,.0f}", "orange"),
    ]

    # Wages/Payroll are linked to HR employee master when the HR tables exist.
    wages_count, payroll_count = _load_hr_counts()
    top_items[1] = ("👥", "Wages", f"{wages_count}", "blue")
    top_items[2] = ("👥", "Payroll", f"{payroll_count}", "blue")

    top_html = "<div class='dash-status-strip'>"
    for icon, label, value, tone in top_items:
        top_html += f"<div class='dash-mini-box {tone}'><div class='dash-mini-label'>{icon} {label}</div><div class='dash-mini-value'>{value}</div></div>"
    top_html += "</div>"
    st.markdown(top_html, unsafe_allow_html=True)

    # Compact KPI row.
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3, gap="small")

    with kpi_col1:
        st.markdown(f"""
        <div class='dash-kpi blue'>
          <div class='dash-kpi-label'>📦 Cumulative Order Demands</div>
          <div class='dash-kpi-value'>{float(t_ord) - float(total_est_prod):,.0f} <span>Pcs</span></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class='dash-kpi green'>
          <div class='dash-kpi-label'>🏭 Total Finished Storage (OK Volume)</div>
          <div class='dash-kpi-value'>{float(total_finished_storage):,.0f} <span>Pcs</span></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
        <div class='dash-kpi orange'>
          <div class='dash-kpi-label'>🚚 Distribution Despatch Output</div>
          <div class='dash-kpi-value'>{float(t_desp):,.0f} <span>Pcs</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ----------------------------------------------------------------------
    # Excel-style Reporting Columns
    # ----------------------------------------------------------------------
    left_col, right_col = st.columns([1.0, 1.65], gap="small")

    with left_col:
        paper_rows_html = ""
        for size, reel, wip, total in paper_status:
            paper_rows_html += f"<tr><td>{size.upper()}</td><td>{reel:,.0f}</td><td>{wip:,.0f}</td><td>{total:,.0f}</td></tr>"
        paper_html = f"""
        <div class='dash-report-box paper-box'>
          <div class='dash-report-title'>Paper Status</div>
          <table class='dash-report-table'>
            <thead><tr><th>Paper Type</th><th>Reel Form<br>(in Kg.)</th><th>WIP<br>(in Kgs.)</th><th>Total<br>(in Kg.)</th></tr></thead>
            <tbody>{paper_rows_html}</tbody>
          </table>
        </div>
        """
        st.markdown(paper_html, unsafe_allow_html=True)

        # Board Stock: Sheet Wt. row removed. Only parties having actual
        # material in at least one board size are displayed.
        party_rows = []
        all_board_parties = []
        for party in list(board_balances.keys()) + list(board_wip_balances.keys()):
            if party not in all_board_parties:
                all_board_parties.append(party)

        for party in all_board_parties:
            raw_values = board_balances.get(party, [0.0] * len(board_sizes))
            wip_values = board_wip_balances.get(party, [0.0] * len(board_sizes))
            # Party-wise Board Stock shows actual available quantity (Raw + WIP).
            display_values = [raw_values[i] + wip_values[i] for i in range(len(board_sizes))]
            if not any(v > 0 for v in display_values):
                continue
            cells = "".join(
                f"<td>{v:,.0f}</td>" if v > 0 else "<td>-</td>"
                for v in display_values
            )
            party_rows.append(f"<tr><td>{party}</td>{cells}</tr>")

        board_rows_html = "".join(party_rows)
        if not board_rows_html:
            board_rows_html = (
                f"<tr><td colspan='{len(board_sizes) + 1}' class='empty-cell'>"
                "No Board Stock available.</td></tr>"
            )

        total_raw = [0.0] * len(board_sizes)
        total_wip = [0.0] * len(board_sizes)
        for values in board_balances.values():
            for i, value in enumerate(values):
                total_raw[i] += value
        for values in board_wip_balances.values():
            for i, value in enumerate(values):
                total_wip[i] += value
        grand_total = [total_raw[i] + total_wip[i] for i in range(len(board_sizes))]

        board_header_html = "".join(f"<th>{size}</th>" for size in board_sizes)
        total_raw_html = "".join(
            f"<td>{value:,.0f}</td>" if value > 0 else "<td>-</td>"
            for value in total_raw
        )
        total_wip_html = "".join(
            f"<td>{value:,.0f}</td>" if value > 0 else "<td>-</td>"
            for value in total_wip
        )
        grand_total_html = "".join(
            f"<td>{value:,.0f}</td>" if value > 0 else "<td>-</td>"
            for value in grand_total
        )

        # Keep HTML construction simple and pre-built so Streamlit renders the
        # rows instead of showing <tr> text on the screen.
        board_html = (
            "<div class='dash-report-box board-box'>"
            "<div class='dash-report-title'>Board Stock</div>"
            "<table class='dash-report-table board-table'>"
            "<thead><tr><th>Party</th>" + board_header_html + "</tr></thead>"
            "<tbody>" + board_rows_html
            + "<tr class='summary-row'><td>Total Raw</td>" + total_raw_html + "</tr>"
            + "<tr class='summary-row'><td>Total WIP</td>" + total_wip_html + "</tr>"
            + "<tr class='grand-row'><td>G.Total</td>" + grand_total_html + "</tr>"
            + "</tbody></table></div>"
        )
        st.markdown(board_html, unsafe_allow_html=True)

    with right_col:
        if order_status.empty:
            order_rows_html = "<tr><td colspan='11' class='empty-cell'>No Purchase Order data available.</td></tr>"
        else:
            order_rows_html = ""
            for _, rr in order_status.iterrows():
                order_rows_html += (
                    "<tr>"
                    f"<td>{rr['Order Month']}</td>"
                    f"<td>{rr['Barcode']}</td>"
                    f"<td>{rr['Ruling']}</td>"
                    f"<td>{rr['Order']:,.0f}</td>"
                    f"<td>{rr['Old']}</td>"
                    f"<td>{rr['Production']:,.0f}</td>"
                    f"<td>{rr['Due for Production']:,.0f}</td>"
                    f"<td class='positive'>{rr['Despatched']:,.0f}</td>"
                    f"<td>{rr['Due for Despatched']:,.0f}</td>"
                    f"<td>{rr['Cl. Stock']:,.0f}</td>"
                    f"<td>{rr['Remarks']}</td>"
                    "</tr>"
                )
            # Only one row per Purchase Order entry; all remaining rows are blank.
            for _ in range(max(0, 3 - len(order_status))):
                order_rows_html += "<tr class='blank-row'>" + "<td>&nbsp;</td>" * 11 + "</tr>"

        order_html = f"""
        <div class='dash-report-box order-box'>
          <div class='dash-report-title'>ORDER, PRODUCTION AND DESPATCH STATUS</div>
          <table class='dash-report-table order-table'>
            <thead><tr>
              <th>Order<br>Month</th><th>Barcode</th><th>Ruling</th><th>Order</th><th>Old</th>
              <th>Production</th><th>Due for<br>Production</th><th>Despatched</th>
              <th>Due for<br>Despatched</th><th>Cl. Stock</th><th>Remarks</th>
            </tr></thead>
            <tbody>{order_rows_html}</tbody>
          </table>
        </div>
        """
        st.markdown(order_html, unsafe_allow_html=True)
