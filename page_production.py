# ==============================================================================
# PAGE MODULE: PRODUCTION STATEMENT
# ==============================================================================
# Production, PO, despatch and consumable reports.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    st.markdown("<h2 class='section-header'>📊 Production Statement</h2>", unsafe_allow_html=True)
    render_financial_year_control()
    
    conn = get_db_connection()
    
    report_table = st.selectbox("Select Production Report", [
        "Purchase Orders", "PO Requests", "PO Released", "Production Report",
        "Despatch", "Paper Detail", "Board Detail", "9. Consumable / CF Report"
    ])

    # ----------------------------------------------------------------------
    # 9. CONSUMABLE / CF REPORT
    # ----------------------------------------------------------------------
    if report_table == "9. Consumable / CF Report":
        st.subheader("🧰 9. Consumable / CF Report")

        r1, r2, r3 = st.columns([1, 1, 1.6])

        with r1:
            from_date, from_date_str = get_date_input(
                "From Date (DD/MM/YYYY)",
                "production_cf_report_from"
            )
        with r2:
            to_date, to_date_str = get_date_input(
                "To Date (DD/MM/YYYY)",
                "production_cf_report_to"
            )

        cf_items = get_consumable_cf_item_options(conn)

        with r3:
            selected_item = st.selectbox(
                "Item List",
                ["All Items"] + cf_items,
                key="production_cf_report_item"
            )

        if from_date and to_date and from_date > to_date:
            st.error("From Date cannot be later than To Date.")
        elif st.button("Generate Consumable / CF Report", type="primary", key="production_cf_report_generate"):
            # Read all transactions so the Closing Stock remains a true running
            # stock balance, including stock carried forward from before From Date.
            cf_df = pd.read_sql_query(
                """SELECT id, entry_date, item_name, in_out, quantity, remarks
                   FROM consumable_cf_entries
                   ORDER BY id""",
                conn
            )

            if not cf_df.empty:
                cf_df["_date"] = pd.to_datetime(
                    cf_df["entry_date"].astype(str),
                    format="%d/%m/%Y",
                    errors="coerce"
                )
                cf_df["quantity"] = pd.to_numeric(cf_df["quantity"], errors="coerce").fillna(0.0)
                cf_df["item_name"] = cf_df["item_name"].fillna("").astype(str).str.strip()
                cf_df["in_out"] = cf_df["in_out"].fillna("").astype(str).str.strip().str.lower()

                if from_date_str:
                    report_from = pd.Timestamp(from_date)
                    cf_df = cf_df[cf_df["_date"].notna()]
                else:
                    report_from = None

                report_to = pd.Timestamp(to_date) if to_date_str and to_date else None

                if selected_item != "All Items":
                    cf_df = cf_df[cf_df["item_name"] == selected_item]

                # Opening balance = all valid transactions before From Date.
                balances = {}
                if report_from is not None:
                    opening_df = cf_df[cf_df["_date"] < report_from]
                    for _, rr in opening_df.iterrows():
                        item = rr["item_name"]
                        qty = float(rr["quantity"] or 0)
                        balances[item] = balances.get(item, 0.0) + (qty if rr["in_out"] == "in" else -qty)

                # Display only transactions inside the requested date range.
                display_df = cf_df.copy()
                if report_from is not None:
                    display_df = display_df[display_df["_date"] >= report_from]
                if report_to is not None:
                    display_df = display_df[display_df["_date"] <= report_to]
                display_df = display_df.sort_values(["_date", "id"], na_position="last")

                rows = []
                for _, rr in display_df.iterrows():
                    item = rr["item_name"]
                    qty = float(rr["quantity"] or 0)
                    if rr["in_out"] == "in":
                        in_qty, out_qty = qty, 0.0
                        balances[item] = balances.get(item, 0.0) + qty
                    else:
                        in_qty, out_qty = 0.0, qty
                        balances[item] = balances.get(item, 0.0) - qty

                    rows.append([
                        rr["_date"].strftime("%d/%m/%Y") if pd.notna(rr["_date"]) else str(rr["entry_date"]),
                        item,
                        in_qty,
                        out_qty,
                        round(balances[item], 2),
                        rr["remarks"] or ""
                    ])

                output = pd.DataFrame(
                    rows,
                    columns=["Date", "Item Name", "In", "Out", "Closing Stock", "Remarks"]
                )

                if output.empty:
                    st.info("No data available for selected filters.")
                else:
                    st.dataframe(
                        output,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "In": st.column_config.NumberColumn("In", format="%.2f"),
                            "Out": st.column_config.NumberColumn("Out", format="%.2f"),
                            "Closing Stock": st.column_config.NumberColumn("Closing Stock", format="%.2f"),
                        }
                    )

                    # Excel export: A4 landscape and compact six-column statement.
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        output.to_excel(writer, index=False, sheet_name="Consumable CF Report", startrow=3)
                    buffer.seek(0)
                    wb = openpyxl.load_workbook(buffer)
                    ws = wb["Consumable CF Report"]

                    last_col = get_column_letter(len(output.columns))
                    ws.merge_cells(f"A1:{last_col}1")
                    ws["A1"] = "CONSUMABLE / CF REPORT"
                    ws["A1"].font = Font(size=14, bold=True)
                    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

                    ws.merge_cells(f"A2:{last_col}2")
                    ws["A2"] = f"From: {format_date(from_date)}   To: {format_date(to_date)}"
                    ws["A2"].font = Font(size=10, italic=True)
                    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

                    ws.merge_cells(f"A3:{last_col}3")
                    ws["A3"] = f"Item: {selected_item}"
                    ws["A3"].font = Font(size=10, bold=True)
                    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

                    header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                    header_font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                    thin_side = Side(style="thin", color="A6A6A6")
                    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

                    for cell in ws[4]:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        cell.border = cell_border

                    for row in ws.iter_rows(min_row=5):
                        for cell in row:
                            cell.font = Font(name="Arial", size=8)
                            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                            cell.border = cell_border

                    widths = [14, 28, 12, 12, 16, 28]
                    for i, width in enumerate(widths, 1):
                        ws.column_dimensions[get_column_letter(i)].width = width

                    ws.row_dimensions[1].height = 24
                    ws.row_dimensions[2].height = 20
                    ws.row_dimensions[3].height = 20
                    ws.row_dimensions[4].height = 28
                    ws.freeze_panes = "A5"
                    ws.sheet_view.showGridLines = False
                    ws.page_setup.paperSize = ws.PAPERSIZE_A4
                    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                    ws.page_setup.fitToWidth = 1
                    ws.page_setup.fitToHeight = 0
                    ws.sheet_properties.pageSetUpPr.fitToPage = True
                    ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                    ws.print_options.horizontalCentered = True
                    ws.print_title_rows = "1:4"

                    final_buffer = BytesIO()
                    wb.save(final_buffer)
                    final_buffer.seek(0)

                    show_report_preview(
                        output,
                        "CONSUMABLE / CF REPORT",
                        f"From {format_date(from_date)} To {format_date(to_date)}",
                        "production_consumable_cf_report"
                    )

                    st.download_button(
                        "⬇️ Download Consumable / CF Report (Excel)",
                        data=final_buffer.getvalue(),
                        file_name=f"Consumable_CF_Report_{format_date(from_date).replace('/', '-')}_to_{format_date(to_date).replace('/', '-')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_production_cf_report"
                    )
            else:
                st.info("No Consumable / CF entries found.")

    # ----------------------------------------------------------------------
    def _production_excel_bytes(df, sheet_name, title=None, from_date=None, to_date=None):
        """Create an Excel workbook for a production report using openpyxl."""
        from io import BytesIO
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name[:31]

        if from_date is not None or to_date is not None:
            # Compact one-line date range, matching the requested report format.
            ws.cell(1, 1, "From Date")
            ws.cell(1, 2, from_date or "")
            ws.cell(1, 3, "To Date")
            ws.cell(1, 4, to_date or "")
            for c in (1, 3):
                ws.cell(1, c).font = Font(bold=True)
            for c in (1, 2, 3, 4):
                ws.cell(1, c).alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions["A"].width = 12
            ws.column_dimensions["B"].width = 12
            ws.column_dimensions["C"].width = 10
            ws.column_dimensions["D"].width = 12
            start_row = 3 if title else 2
        elif title:
            start_row = 3
        else:
            start_row = 1

        if title:
            ws.merge_cells(start_row=2 if (from_date is not None or to_date is not None) else 1,
                           start_column=1,
                           end_row=2 if (from_date is not None or to_date is not None) else 1,
                           end_column=max(1, len(df.columns)))
            title_row = 2 if (from_date is not None or to_date is not None) else 1
            cell = ws.cell(title_row, 1, title)
            cell.font = Font(bold=True, size=14)
            cell.alignment = Alignment(horizontal="center", vertical="center")

        header_fill = PatternFill(fill_type="solid", fgColor="0B2E6F")
        header_font = Font(color="FFFFFF", bold=True)

        for col_idx, col_name in enumerate(df.columns, 1):
            cell = ws.cell(start_row, col_idx, col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for row_idx, row in enumerate(df.itertuples(index=False), start_row + 1):
            for col_idx, value in enumerate(row, 1):
                ws.cell(row_idx, col_idx, value)

        for col_idx, col_name in enumerate(df.columns, 1):
            values = [str(col_name)] + [str(v) if v is not None else "" for v in df.iloc[:, col_idx - 1].tolist()]
            width = min(max(max((len(v) for v in values), default=10) + 2, 10), 28)
            ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else ws.cell(1, col_idx).column_letter].width = width

        ws.freeze_panes = ws.cell(start_row + 1, 1).coordinate
        ws.auto_filter.ref = ws.dimensions

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    # Hide Streamlit's built-in CSV action for these report tables.
    st.markdown("""
    <style>
    div[data-testid="stDataFrame"] button[aria-label*="CSV"],
    div[data-testid="stDataFrame"] button[title*="CSV"],
    div[data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label*="CSV"],
    div[data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[title*="CSV"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # PRODUCTION REPORT - TWO TABS
    # ----------------------------------------------------------------------
    if report_table == "Production Report":
        prod_report_tab, mfg_cost_tab = st.tabs(["Production Report", "Prod. Mfg. Cost"])

        def _production_report_dates(prefix):
            d1, s1 = get_date_input("From Date", f"{prefix}_from")
            d2, s2 = get_date_input("To Date", f"{prefix}_to")
            return d1, s1, d2, s2

        with prod_report_tab:
            st.markdown("### PRODUCTION REPORT")
            from_date, from_date_str, to_date, to_date_str = _production_report_dates("production_report")

            clauses = []
            params = []
            if from_date_str:
                clauses.append("p.production_date >= ?")
                params.append(from_date_str)
            if to_date_str:
                clauses.append("p.production_date <= ?")
                params.append(to_date_str)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

            prod_sql = f"""
                SELECT
                    p.production_month AS order_month,
                    p.production_date,
                    p.product_code,
                    p.ruling_type AS ruling,
                    p.page,
                    COALESCE(o.mrp, 0) AS mrp,
                    p.plan_qty AS production_quantity,
                    p.rejection_qty AS rejection,
                    p.ok_notebook AS ok_note_book,
                    p.book_size AS paper_size,
                    p.paper_consumption,
                    p.board_size,
                    p.board_consumption,
                    p.case_quantity,
                    p.making_rate,
                    p.making_charges
                FROM production_form_entries p
                LEFT JOIN order_entries o
                  ON o.id = (
                    SELECT MAX(o2.id) FROM order_entries o2
                    WHERE o2.product_code = p.product_code
                      AND (o2.order_month = p.production_month OR p.production_month IS NULL OR p.production_month = '')
                  )
                {where}
                ORDER BY p.production_date, p.id
            """
            try:
                production_output = pd.read_sql_query(prod_sql, conn, params=params)
            except Exception:
                # Fallback without the optional MRP lookup if an older database schema differs.
                fallback_sql = f"""
                    SELECT
                        production_month AS order_month,
                        production_date,
                        product_code,
                        ruling_type AS ruling,
                        page,
                        0 AS mrp,
                        plan_qty AS production_quantity,
                        rejection_qty AS rejection,
                        ok_notebook AS ok_note_book,
                        book_size AS paper_size,
                        paper_consumption,
                        board_size,
                        board_consumption,
                        case_quantity,
                        making_rate,
                        making_charges
                    FROM production_form_entries p
                    {where.replace('p.', '')}
                    ORDER BY production_date, id
                """
                production_output = pd.read_sql_query(fallback_sql, conn, params=params)

            report_columns = [
                "Order Month", "Production Date", "Product Code", "Ruling", "Page", "MRP",
                "Production Quantity", "Rejection", "OK Note Book", "Paper Size",
                "Paper Consumption", "Board Size", "Board Consumption", "Case Quantity",
                "Making Rate", "Making Charges"
            ]

            if production_output.empty:
                st.info("No production data available for selected date range.")
            else:
                production_output.columns = report_columns
                for col in ["MRP", "Production Quantity", "Rejection", "OK Note Book", "Paper Consumption",
                            "Board Consumption", "Case Quantity", "Making Rate", "Making Charges"]:
                    production_output[col] = pd.to_numeric(production_output[col], errors="coerce").fillna(0)
                st.dataframe(
                    production_output,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "MRP": st.column_config.NumberColumn("MRP", format="%.2f"),
                        "Production Quantity": st.column_config.NumberColumn("Production Quantity", format="%.0f"),
                        "Rejection": st.column_config.NumberColumn("Rejection", format="%.0f"),
                        "OK Note Book": st.column_config.NumberColumn("OK Note Book", format="%.0f"),
                        "Paper Consumption": st.column_config.NumberColumn("Paper Consumption", format="%.3f"),
                        "Board Consumption": st.column_config.NumberColumn("Board Consumption", format="%.3f"),
                        "Case Quantity": st.column_config.NumberColumn("Case Quantity", format="%.2f"),
                        "Making Rate": st.column_config.NumberColumn("Making Rate", format="%.2f"),
                        "Making Charges": st.column_config.NumberColumn("Making Charges", format="%.2f"),
                    }
                )
                show_report_preview(
                    production_output,
                    "PRODUCTION REPORT",
                    f"From {format_date(from_date)} To {format_date(to_date)}",
                    "production_report"
                )

                st.download_button(
                    "📥 Download Excel Report",
                    data=_production_excel_bytes(production_output, "Production Report", "PRODUCTION REPORT"),
                    file_name="Production_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="production_report_excel_download"
                )

        with mfg_cost_tab:
            st.markdown("### RANJIT MAKING CHARGES")

            # Compact one-line date range, matching the requested report layout.
            date_label1, date_value1, date_label2, date_value2, _date_spacer = st.columns([0.55, 0.95, 0.55, 0.95, 3.0])
            with date_label1:
                st.markdown("<div style='padding-top:8px;'>From Date</div>", unsafe_allow_html=True)
            with date_value1:
                from_date2, from_date_str2 = get_date_input(
                    "",
                    "mfg_cost_report_from",
                    help_text="Enter date in DD/MM/YYYY format"
                )
            with date_label2:
                st.markdown("<div style='padding-top:8px;'>To Date</div>", unsafe_allow_html=True)
            with date_value2:
                to_date2, to_date_str2 = get_date_input(
                    "",
                    "mfg_cost_report_to",
                    help_text="Enter date in DD/MM/YYYY format"
                )
            st.markdown(
                "<style>"
                "[data-testid='stTextInput'] input {padding-left: 8px; padding-right: 8px;}"
                "[data-testid='stTextInput'] label {display:none;}"
                "</style>",
                unsafe_allow_html=True
            )

            clauses2 = []
            params2 = []
            if from_date_str2:
                clauses2.append("production_date >= ?")
                params2.append(from_date_str2)
            if to_date_str2:
                clauses2.append("production_date <= ?")
                params2.append(to_date_str2)
            where2 = (" WHERE " + " AND ".join(clauses2)) if clauses2 else ""

            cost_sql = f"""
                SELECT production_date, product_code, plan_qty, rejection_qty,
                       ok_notebook, making_rate, making_charges
                FROM production_form_entries
                {where2}
                ORDER BY production_date, id
            """
            cost_output = pd.read_sql_query(cost_sql, conn, params=params2)
            cost_output.columns = [
                "Production Date", "Product Code", "Production Quantity", "Rejection",
                "OK Note Book", "Making Rate", "Making Charges"
            ]

            if cost_output.empty:
                st.info("No production data available for selected date range.")
            else:
                for col in ["Production Quantity", "Rejection", "OK Note Book", "Making Rate", "Making Charges"]:
                    cost_output[col] = pd.to_numeric(cost_output[col], errors="coerce").fillna(0)
                st.dataframe(
                    cost_output,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Production Quantity": st.column_config.NumberColumn("Production Quantity", format="%.0f"),
                        "Rejection": st.column_config.NumberColumn("Rejection", format="%.0f"),
                        "OK Note Book": st.column_config.NumberColumn("OK Note Book", format="%.0f"),
                        "Making Rate": st.column_config.NumberColumn("Making Rate", format="%.2f"),
                        "Making Charges": st.column_config.NumberColumn("Making Charges", format="%.2f"),
                    }
                )
                show_report_preview(
                    cost_output,
                    "RANJI MAKING CHARGES",
                    f"From {format_date(from_date2)} To {format_date(to_date2)}",
                    "production_mfg_cost_report"
                )

                st.download_button(
                    "📥 Download Excel Report",
                    data=_production_excel_bytes(
                        cost_output,
                        "Prod. Mfg. Cost",
                        "RANJI MAKING CHARGES",
                        from_date=from_date_str2,
                        to_date=to_date_str2
                    ),
                    file_name="Prod_Mfg_Cost.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="prod_mfg_cost_excel_download"
                )

    table_map = {
        "Purchase Orders": "order_entries",
        "PO Requests": "po_request_entries",
        "PO Released": "po_released_entries",
        "Production": "production_form_entries",
        "Despatch": "despatch_form_entries",
        "Paper Detail": "paper_detail_entries",
        "Board Detail": "board_detail_entries"
    }
    if report_table not in ("9. Consumable / CF Report", "Production Report"):
        table_name = table_map[report_table]
    
    if report_table in ("9. Consumable / CF Report", "Production Report"):
        pass
    elif report_table == "Purchase Orders":
        st.subheader("📦 Purchase Orders Report")
        
        output = calculate_purchase_order_report(conn)
        
        if not output.empty:
            st.dataframe(output, use_container_width=True, hide_index=True)
            
            # Excel Export with formatting
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                output.to_excel(writer, index=False, sheet_name='Report', startrow=1)
            
            buffer.seek(0)
            wb = openpyxl.load_workbook(buffer)
            ws = wb['Report']
            
            ws.merge_cells('A1:N1')
            ws['A1'] = 'PURCHASE ORDER REPORT'
            ws['A1'].font = Font(size=14, bold=True)
            ws['A1'].alignment = Alignment(horizontal='center')
            
            header_fill = PatternFill(fill_type="solid", fgColor="17365D")
            header_font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
            thin_side = Side(style="thin", color="A6A6A6")
            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
            
            for cell in ws[2]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = cell_border
            
            for row in ws.iter_rows(min_row=3):
                for cell in row:
                    cell.font = Font(name="Arial", size=8)
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = cell_border
            
            column_widths = [11, 13, 11, 10, 13, 11, 11, 14, 13, 14, 15, 15, 16, 16]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = width
            
            ws.row_dimensions[1].height = 24
            ws.row_dimensions[2].height = 32
            for i in range(3, ws.max_row + 1):
                ws.row_dimensions[i].height = 20
            
            ws.freeze_panes = 'A3'
            ws.sheet_view.showGridLines = False
            
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
            ws.print_options.horizontalCentered = True
            ws.print_title_rows = "1:2"
            
            final_buffer = BytesIO()
            wb.save(final_buffer)
            
            show_report_preview(
                output,
                "PURCHASE ORDERS REPORT",
                "Current Purchase Orders",
                "purchase_orders_report"
            )

            st.download_button(
                "⬇️ Download Purchase Orders Report (Excel)",
                data=final_buffer.getvalue(),
                file_name="Purchase_Orders_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_purchase_orders_report"
            )
        else:
            st.info("No purchase orders found.")
    
    elif report_table == "PO Requests":
        st.subheader("📋 PO Requests Report")
        
        raw_df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id", conn)
        
        if not raw_df.empty:
            report_columns = [
                "Date", "Type of Binding", "Product Size (cm)", "Cover Soft / Hard",
                "Product Code", "No of Pages", "Ruling", "MRP", "Inner Qty",
                "Case Qty", "Order Qty", "Produced Qty", "Board GSM",
                "Sheet Width in cm", "Sheet Length in cm", "Paper GSM",
                "Reel / Sheet Width in cm", "Reel Cut off Size (In cm)",
                "Book Weight Paper", "Book Weight Board", "Paper Rate", "Tax (Paper)",
                "Current Paper Cost", "Mill (Paper)", "Board Rate", "Tax (Board)",
                "Current Board Cost", "Mill (Board)", "Per Book Paper Cost",
                "Per Book Board Cost", "Conversion Rate", "Lam. Type",
                "KCL Approved Rate"
            ]
            
            report_rows = []
            for _, source_row in raw_df.iterrows():
                report_rows.append(calculate_po_request_full_row(source_row.to_dict()))
            
            output = pd.DataFrame(report_rows, columns=report_columns)
            output["KCL Approved Rate"] = "N/A"
            
            st.dataframe(output, use_container_width=True, hide_index=True)
            
            # Excel Export - PO Request format with 33 columns
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                output.to_excel(writer, index=False, sheet_name='Report')
            
            buffer.seek(0)
            wb = openpyxl.load_workbook(buffer)
            ws = wb['Report']
            
            header_fill = PatternFill(fill_type="solid", fgColor="17365D")
            header_font = Font(name="Arial", size=7, bold=True, color="FFFFFF")
            thin_side = Side(style="thin", color="A6A6A6")
            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = cell_border
            
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.font = Font(name="Arial", size=7)
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = cell_border
            
            po_widths = [5.5, 7.0, 9.0, 7.0, 10.0, 7.0, 8.0, 6.0, 6.0, 6.0,
                        7.0, 8.0, 7.0, 7.0, 7.0, 7.0, 10.0, 11.0, 9.0, 9.0,
                        7.0, 5.0, 11.0, 7.0, 8.0, 5.0, 11.0, 7.0, 11.0, 11.0,
                        9.0, 8.0, 9.0]
            for col_idx in range(1, ws.max_column + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = po_widths[col_idx - 1]
            
            ws.row_dimensions[1].height = 40
            for row_idx in range(2, ws.max_row + 1):
                ws.row_dimensions[row_idx].height = 18
            
            ws.freeze_panes = 'A2'
            ws.sheet_view.showGridLines = False
            
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.page_margins = PageMargins(left=0.10, right=0.10, top=0.15, bottom=0.15, header=0.05, footer=0.05)
            ws.print_options.horizontalCentered = True
            ws.print_title_rows = "1:1"
            
            final_buffer = BytesIO()
            wb.save(final_buffer)
            
            show_report_preview(
                output,
                "PO REQUESTS REPORT",
                "Current PO Requests",
                "po_requests_report"
            )

            st.download_button(
                "⬇️ Download PO Requests Report (Excel)",
                data=final_buffer.getvalue(),
                file_name="PO_Requests_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_po_requests_report"
            )
        else:
            st.info("No PO requests found.")
    
    elif report_table == "PO Released":
        st.subheader("📋 PO Released Report")

        released_df = pd.read_sql_query("SELECT * FROM po_released_entries ORDER BY id", conn)
        report_rows = []

        for _, rel in released_df.iterrows():
            order_month = str(rel.get("order_month", "") or "")
            product_code = str(rel.get("product_code", "") or "").strip()

            # 1-5: Purchase Order values (exact Order Month + Product Code, then Product Code fallback).
            po_df = pd.read_sql_query(
                "SELECT order_month, product_code, no_of_page, ruling_type, order_qty "
                "FROM order_entries WHERE product_code = ? AND order_month = ? ORDER BY id DESC LIMIT 1",
                conn, params=(product_code, order_month)
            )
            if po_df.empty:
                po_df = pd.read_sql_query(
                    "SELECT order_month, product_code, no_of_page, ruling_type, order_qty "
                    "FROM order_entries WHERE product_code = ? ORDER BY id DESC LIMIT 1",
                    conn, params=(product_code,)
                )

            if not po_df.empty:
                po = po_df.iloc[0]
                report_month = po.get("order_month", order_month) or order_month
                report_code = str(po.get("product_code", product_code) or product_code)
                page = po.get("no_of_page", rel.get("page", ""))
                ruling = po.get("ruling_type", rel.get("ruling_type", ""))
                order_qty = _safe_num(po.get("order_qty", 0))
            else:
                report_month = order_month
                report_code = product_code
                page = rel.get("page", "")
                ruling = rel.get("ruling_type", "")
                order_qty = 0.0

            # 6: Existing Case Quantity logic from Product/Page.
            try:
                page_no = int(float(page))
            except (TypeError, ValueError):
                try:
                    page_no = int(product_code[-3:])
                except (TypeError, ValueError):
                    page_no = 0
            if len(product_code) >= 3 and product_code[2] == "5":
                case_qty = {52:192, 76:144, 100:120, 140:84, 176:72, 240:48}.get(page_no, 0)
            elif len(product_code) >= 3 and product_code[2] == "3":
                case_qty = {56:288, 92:192, 120:144, 164:96, 176:96}.get(page_no, 0)
            else:
                case_qty = 0

            # 7: Produced Quantity from PO Request Report / PO Request entry.
            req_df = pd.read_sql_query(
                "SELECT * FROM po_request_entries WHERE product_code = ? AND po_month = ? ORDER BY id DESC LIMIT 1",
                conn, params=(product_code, report_month)
            )
            if req_df.empty:
                req_df = pd.read_sql_query(
                    "SELECT * FROM po_request_entries WHERE product_code = ? ORDER BY id DESC LIMIT 1",
                    conn, params=(product_code,)
                )
            produced_qty = _safe_num(req_df.iloc[0].get("produced_qty", 0)) if not req_df.empty else 0.0

            # 8: KCL Approved Rate = PO Request Report Column 29 + 30 + 31.
            kcl_rate = get_po_release_rate(conn, product_code, report_month)

            # 9-11 and 15: PO Released Entry values.
            destination = rel.get("destination", "") or ""
            po_number = rel.get("po_number", "") or ""
            po_date = rel.get("po_date", "") or rel.get("release_date", "") or ""
            mail_reference_date = rel.get("release_date", "") or ""

            # 12: Despatched from Despatch Report, matched to Product Code + PO Number when available.
            if str(po_number).strip():
                des_df = pd.read_sql_query(
                    "SELECT despatch_qty FROM despatch_form_entries WHERE product_code = ? AND po_number = ?",
                    conn, params=(product_code, str(po_number))
                )
            else:
                des_df = pd.read_sql_query(
                    "SELECT despatch_qty FROM despatch_form_entries WHERE product_code = ?",
                    conn, params=(product_code,)
                )
            despatched = float(pd.to_numeric(des_df.get("despatch_qty", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not des_df.empty else 0.0

            # 13-14: final formulas.
            due_despatched = produced_qty - despatched
            cs_due = (due_despatched / case_qty) if case_qty else 0.0

            report_rows.append({
                "Order Month": report_month,
                "Product Code": report_code,
                "No. of Pages": page,
                "Ruling": ruling,
                "Case Quantity": case_qty,
                "Order Quantity": order_qty,
                "Produced Quantity": produced_qty,
                "KCL Approved Rate": kcl_rate,
                "Destination": destination,
                "P.O. Number": po_number,
                "P.O. Date": po_date,
                "Despatched": despatched,
                "Due for Despatched": due_despatched,
                "C/S Due": cs_due,
                "Mail Reference Date": mail_reference_date,
            })

        output = pd.DataFrame(report_rows, columns=[
            "Order Month", "Product Code", "No. of Pages", "Ruling", "Case Quantity",
            "Order Quantity", "Produced Quantity", "KCL Approved Rate", "Destination",
            "P.O. Number", "P.O. Date", "Despatched", "Due for Despatched", "C/S Due",
            "Mail Reference Date"
        ])

        if output.empty:
            st.info("No PO Released entries found.")
        else:
            st.dataframe(output, use_container_width=True, hide_index=True)
            show_report_preview(output, "PO RELEASED REPORT", "Current PO Released Status", "po_released_report")

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                output.to_excel(writer, index=False, sheet_name="PO Released")
            buffer.seek(0)
            st.download_button(
                "⬇️ Download PO Released Report (Excel)",
                data=buffer.getvalue(),
                file_name="PO_Released_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_po_released_report"
            )

    elif report_table == "Paper Detail":
        st.subheader("📄 Paper Detail Report")

        # Report filters: Date Range + Paper Size + WIP Type
        pf1, pf2, pf3, pf4 = st.columns([1, 1, 1.2, 1.2])
        with pf1:
            paper_from_date, paper_from_date_str = get_date_input(
                "From Date (DD/MM/YYYY)",
                "paper_detail_report_from_date"
            )
        with pf2:
            paper_to_date, paper_to_date_str = get_date_input(
                "To Date (DD/MM/YYYY)",
                "paper_detail_report_to_date"
            )
        with pf3:
            paper_size_filter = st.selectbox(
                "Paper Size",
                ["All", "97x57x37", "97x54x37x", "90x57x43"],
                key="paper_detail_report_paper_size"
            )
        with pf4:
            wip_type_filter = st.selectbox(
                "WIP Type",
                ["All", "Single Line", "Unruled", "Four Line", "Med. Square", "Index", "Double Rule"],
                key="paper_detail_report_wip_type"
            )

        if paper_from_date and paper_to_date and paper_from_date > paper_to_date:
            st.error("From Date cannot be later than To Date.")
        else:
            # Paper Detail report format and formulas:
            # Cl. Reel Stock = Op. Reel Qnty. + Inward Qnty. - Process Qnty.
            # Cl. WIP Paper  = Process Qnty. - Wastage - Consumption
            output = pd.read_sql_query(
                """SELECT entry_date AS 'Date', invoice_no AS 'Invoice No.',
                          party_name AS 'Party Name', paper_size AS 'Paper Size',
                          opening_reel AS 'Op. Reel Qnty.', inward_qty AS 'Inward Qnty.',
                          process_qty AS 'Process Qnty.', wastage AS 'Wastage',
                          remarks AS 'WIP Type'
                   FROM paper_detail_entries ORDER BY id""", conn
            )

            # Production paper consumption is used as the report Consumption value.
            # Matching is by production date and WIP/Ruling type.
            try:
                production_consumption = pd.read_sql_query(
                    """SELECT production_date, ruling_type, paper_consumption
                       FROM production_form_entries ORDER BY id""", conn
                )
            except Exception:
                production_consumption = pd.DataFrame(
                    columns=['production_date', 'ruling_type', 'paper_consumption']
                )

            def _normalise_wip_type(value):
                text = str(value or '').strip().casefold()
                aliases = {
                    'medium square': 'med. square',
                    'med square': 'med. square',
                    'med. square': 'med. square',
                    'single line': 'single line',
                    'unruled': 'unruled',
                    'four line': 'four line',
                    'index': 'index',
                    'double rule': 'double rule',
                }
                return aliases.get(text, text)

            if not production_consumption.empty:
                production_consumption['Consumption Date Key'] = pd.to_datetime(
                    production_consumption['production_date'], dayfirst=True, errors='coerce'
                ).dt.date
                production_consumption['WIP Type Key'] = production_consumption['ruling_type'].apply(_normalise_wip_type)
                production_consumption['Consumption Value'] = pd.to_numeric(
                    production_consumption['paper_consumption'], errors='coerce'
                ).fillna(0.0)
                consumption_map = production_consumption.groupby(
                    ['Consumption Date Key', 'WIP Type Key'], dropna=False
                )['Consumption Value'].sum().to_dict()
            else:
                consumption_map = {}

            if not output.empty:
                parsed_report_dates = pd.to_datetime(output['Date'], dayfirst=True, errors='coerce')
                if paper_from_date:
                    output = output.loc[parsed_report_dates >= pd.Timestamp(paper_from_date)].copy()
                if paper_to_date and not output.empty:
                    parsed_report_dates = pd.to_datetime(output['Date'], dayfirst=True, errors='coerce')
                    output = output.loc[parsed_report_dates <= pd.Timestamp(paper_to_date)].copy()

                # Compare Paper Size by dimensions so alternate stored order (e.g.
                # 97x37x57) also matches the requested report dropdown size.
                if paper_size_filter != "All" and not output.empty:
                    def _paper_size_key(value):
                        nums = re.findall(r"\d+(?:\.\d+)?", str(value or ""))
                        if len(nums) >= 3:
                            return tuple(sorted(float(x) for x in nums[:3]))
                        return tuple()
                    selected_paper_size_key = _paper_size_key(paper_size_filter)
                    output = output.loc[
                        output['Paper Size'].apply(_paper_size_key) == selected_paper_size_key
                    ].copy()

                if wip_type_filter != "All" and not output.empty:
                    selected_wip_key = _normalise_wip_type(wip_type_filter)
                    output = output.loc[
                        output['WIP Type'].apply(_normalise_wip_type) == selected_wip_key
                    ].copy()

            if not output.empty:
                # Numeric fields.
                for col in ['Op. Reel Qnty.', 'Inward Qnty.', 'Process Qnty.', 'Wastage']:
                    output[col] = pd.to_numeric(output[col], errors='coerce').fillna(0.0)

                output['_Date Key'] = pd.to_datetime(output['Date'], dayfirst=True, errors='coerce').dt.date
                output['_WIP Key'] = output['WIP Type'].apply(_normalise_wip_type)

                # Consumption is fetched from matching Production Entry.
                output['Consumption'] = output.apply(
                    lambda row: float(consumption_map.get((row['_Date Key'], row['_WIP Key']), 0.0)),
                    axis=1
                )

                # FINAL USER-APPROVED FORMULAS
                output['Cl. Reel Stock'] = (
                    output['Op. Reel Qnty.'] + output['Inward Qnty.'] - output['Process Qnty.']
                )
                output['Cl. WIP Paper'] = (
                    output['Process Qnty.'] - output['Wastage'] - output['Consumption']
                )

                output = output[[
                    'Date', 'Invoice No.', 'Party Name', 'Paper Size',
                    'Op. Reel Qnty.', 'Inward Qnty.', 'Process Qnty.', 'Wastage',
                    'Cl. Reel Stock', 'WIP Type', 'Consumption', 'Cl. WIP Paper'
                ]]
                output['Date'] = output['Date'].apply(format_date)

                st.dataframe(output, use_container_width=True, hide_index=True)

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    output.to_excel(writer, index=False, sheet_name='PaperDetail', startrow=1)
                buffer.seek(0)
                wb = openpyxl.load_workbook(buffer)
                ws = wb['PaperDetail']
                ws.merge_cells('A1:L1')
                ws['A1'] = 'PAPER DETAIL REPORT'
                ws['A1'].font = Font(size=11, bold=True)
                ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
                header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                header_font = Font(name="Arial", size=8, bold=True, color="FFFFFF")
                thin_side = Side(style="thin", color="A6A6A6")
                cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                for cell in ws[2]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = cell_border
                for row in ws.iter_rows(min_row=3):
                    for cell in row:
                        cell.font = Font(name="Arial", size=7)
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                        cell.border = cell_border
                        if cell.column in (5, 6, 7, 8, 9, 11, 12):
                            cell.alignment = Alignment(horizontal='right', vertical='center')
                            cell.number_format = '#,##0.000'
                column_widths = [11, 13, 18, 12, 14, 14, 14, 11, 14, 14, 14, 14]
                for i, width in enumerate(column_widths, 1):
                    ws.column_dimensions[get_column_letter(i)].width = width
                ws.row_dimensions[1].height = 20
                ws.row_dimensions[2].height = 30
                ws.freeze_panes = 'A3'
                ws.sheet_view.showGridLines = False
                ws.page_setup.paperSize = ws.PAPERSIZE_A4
                ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.page_margins = PageMargins(left=0.10, right=0.10, top=0.15, bottom=0.15, header=0.05, footer=0.05)
                final_buffer = BytesIO()
                wb.save(final_buffer)
                show_report_preview(output, "PAPER DETAIL REPORT", "Filtered paper detail transactional logs", "production_paper_detail_report")
                st.download_button(
                    "⬇️ Download Paper Detail Report (Excel)",
                    data=final_buffer.getvalue(),
                    file_name="Paper_Detail_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_paper_detail_custom_report"
                )
            else:
                st.info("No paper detail entries found for the selected filters.")

    elif report_table == "Board Detail":
        st.subheader("📦 Board Detail Report")

        # Report filters: Date Range + Board Size
        bf1, bf2, bf3 = st.columns([1, 1, 1.2])
        with bf1:
            board_from_date, board_from_date_str = get_date_input(
                "From Date (DD/MM/YYYY)",
                "board_detail_report_from_date"
            )
        with bf2:
            board_to_date, board_to_date_str = get_date_input(
                "To Date (DD/MM/YYYY)",
                "board_detail_report_to_date"
            )
        with bf3:
            board_size_filter = st.selectbox(
                "Board Size",
                ["All"] + ["45.5x91x190", "45.5x91x200", "77x98x190", "91x91x190"],
                key="board_detail_report_board_size"
            )

        if board_from_date and board_to_date and board_from_date > board_to_date:
            st.error("From Date cannot be later than To Date.")
        else:
            output = pd.read_sql_query(
                """SELECT entry_date AS 'Date', invoice_no AS 'Invoice No.',
                          party_name AS 'Party Name', godown AS 'Godown', board_size AS 'Board Size',
                          opening_stock AS 'Op. Stock Qnty.', inward_qty AS 'Inward Qnty.',
                          out_for_printing AS 'Out Printing Qnty.', wastage AS 'Wastage',
                          product_code AS 'Product Code', printed_board_received AS 'Printed Recd.'
                   FROM board_detail_entries ORDER BY id""", conn
            )

            if not output.empty:
                parsed_report_dates = pd.to_datetime(output['Date'], dayfirst=True, errors='coerce')
                if board_from_date:
                    output = output.loc[parsed_report_dates >= pd.Timestamp(board_from_date)].copy()
                    parsed_report_dates = pd.to_datetime(output['Date'], dayfirst=True, errors='coerce')
                if board_to_date:
                    output = output.loc[parsed_report_dates <= pd.Timestamp(board_to_date)].copy()

                if board_size_filter != "All" and not output.empty:
                    output = output.loc[
                        output['Board Size'].fillna('').astype(str).str.strip() == board_size_filter
                    ].copy()

            if not output.empty:
                output['Date'] = output['Date'].apply(format_date)
                for col in ['Op. Stock Qnty.', 'Inward Qnty.', 'Out Printing Qnty.', 'Wastage', 'Printed Recd.']:
                    output[col] = pd.to_numeric(output[col], errors='coerce').fillna(0.0)
                st.dataframe(output, use_container_width=True, hide_index=True)
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    output.to_excel(writer, index=False, sheet_name='BoardDetail', startrow=1)
                buffer.seek(0)
                wb = openpyxl.load_workbook(buffer)
                ws = wb['BoardDetail']
                ws.merge_cells('A1:K1')
                ws['A1'] = 'BOARD DETAIL REPORT'
                ws['A1'].font = Font(size=11, bold=True)
                ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
                header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                header_font = Font(name="Arial", size=8, bold=True, color="FFFFFF")
                thin_side = Side(style="thin", color="A6A6A6")
                cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                for cell in ws[2]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = cell_border
                for row in ws.iter_rows(min_row=3):
                    for cell in row:
                        cell.font = Font(name="Arial", size=7)
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                        cell.border = cell_border
                        if cell.column in (6, 7, 8, 9, 11):
                            cell.alignment = Alignment(horizontal='right', vertical='center')
                            cell.number_format = '#,##0'
                column_widths = [11, 13, 16, 14, 12, 14, 14, 14, 11, 13, 14]
                for i, width in enumerate(column_widths, 1):
                    ws.column_dimensions[get_column_letter(i)].width = width
                ws.row_dimensions[1].height = 20
                ws.row_dimensions[2].height = 28
                ws.freeze_panes = 'A3'
                ws.sheet_view.showGridLines = False
                ws.page_setup.paperSize = ws.PAPERSIZE_A4
                ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.page_margins = PageMargins(left=0.10, right=0.10, top=0.15, bottom=0.15, header=0.05, footer=0.05)
                final_buffer = BytesIO()
                wb.save(final_buffer)
                show_report_preview(output, "BOARD DETAIL REPORT", "Filtered board detail transactional logs", "production_board_detail_report")
                st.download_button("⬇️ Download Board Detail Report (Excel)", data=final_buffer.getvalue(), file_name="Board_Detail_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_board_detail_custom_report")
            else:
                st.info("No board detail entries found for the selected filters.")

    else:
        st.subheader(f"{report_table} Report")
        output = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY id", conn)
        if not output.empty:
            date_columns = ['entry_date', 'po_date', 'release_date', 'production_date', 'despatch_date']
            for col in date_columns:
                if col in output.columns:
                    output[col] = output[col].apply(format_date)
            st.dataframe(output, use_container_width=True, hide_index=True)
            buffer = BytesIO()
            output.to_excel(buffer, index=False, sheet_name='Report')
            buffer.seek(0)
            show_report_preview(output, f"{report_table.upper()} REPORT", "Current report data", f"production_{report_table.replace(' ', '_').replace('/', '_')}_report")
            st.download_button(f"⬇️ Download {report_table} Report (Excel)", data=buffer.getvalue(), file_name=f"{report_table.replace(' ', '_')}_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"download_{report_table.replace(' ', '_')}_report")
        else:
            st.info(f"No {report_table.lower()} found.")
    
    conn.close()
