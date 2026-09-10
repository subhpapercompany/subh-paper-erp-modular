# ==============================================================================
# PAGE MODULE: FINANCIAL STATEMENT
# ==============================================================================
# Ledgers, cash/bank books and financial reports.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    st.markdown("<h2 class='section-header'>📚 Financial Statement</h2>", unsafe_allow_html=True)
    render_financial_year_control()
    
    conn = get_db_connection(private=True)
    financial_report = st.selectbox(
        "Select Financial / HR Report",
        ["Financial Entry Report", "Consumable / CF Report", "HR Module Report"],
        key="financial_statement_report"
    )
    
    # Saved Financial Entries can be opened and edited here directly.
    # This edit surface intentionally does not navigate to Entry Mode / Single Entry.
    st.markdown("### ✏️ Open / Edit Saved Financial Entry")
    fs_rows = conn.execute(
        "SELECT id, mode, entry_date, invoice_no, dr_cr, ledger_head, invoice_amount, tds, net_amount, remarks "
        "FROM voucher_entries ORDER BY id DESC"
    ).fetchall()
    if fs_rows:
        fs_df = pd.DataFrame(fs_rows, columns=["ID", "Voucher Type", "Date", "Voucher No.", "Dr / Cr", "Ledger Head", "Amount", "TDS", "Net Amount", "Remarks"])
        fs_df["Select"] = False
        fs_event = st.data_editor(
            fs_df,
            hide_index=True,
            use_container_width=True,
            disabled=[c for c in fs_df.columns if c != "Select"],
            column_config={"Select": st.column_config.CheckboxColumn("Open", default=False)},
            key="financial_saved_entries_editor"
        )
        selected_fs = fs_event[fs_event["Select"] == True] if isinstance(fs_event, pd.DataFrame) else pd.DataFrame()
        if not selected_fs.empty:
            selected_fs_id = int(selected_fs.iloc[0]["ID"])
            st.session_state["financial_statement_edit_id"] = selected_fs_id
            st.session_state["financial_statement_edit_notice"] = True

    fs_edit_id = st.session_state.get("financial_statement_edit_id")
    if fs_edit_id:
        er = conn.execute(
            "SELECT id, mode, entry_date, invoice_no, dr_cr, ledger_head, invoice_amount, tds, net_amount, remarks "
            "FROM voucher_entries WHERE id = ?", (int(fs_edit_id),)
        ).fetchone()
        if er:
            st.info(f"Editing saved financial entry ID {er[0]}. This is direct Financial Statement editing; Single Entry Mode is not opened.")
            e1,e2,e3 = st.columns(3)
            mode_options = ["Payment", "Contra", "Receipt", "Journal", "Sale", "Purchase", "Other Vouchers", "Received"]
            edit_mode = e1.selectbox("Voucher Type", mode_options, index=mode_options.index(er[1]) if er[1] in mode_options else 0, key="fs_edit_mode")
            edit_date, edit_date_str = get_date_input("Date (DD/MM/YYYY)", "fs_edit_date", default_value=er[2] or "")
            edit_invoice = e3.text_input("Voucher / Invoice No.", value=er[3] or "", key="fs_edit_invoice")
            e4,e5,e6 = st.columns(3)
            edit_drcr = e4.selectbox("Dr / Cr", ["Dr", "Cr"], index=0 if str(er[4]).upper() != "CR" else 1, key="fs_edit_drcr")
            ledger_options_fs = [r[0] for r in conn.execute("SELECT ledger_name FROM ledger_master ORDER BY ledger_name").fetchall()]
            if er[5] and er[5] not in ledger_options_fs:
                ledger_options_fs.append(er[5])
            edit_ledger = e5.selectbox("Ledger Head", ledger_options_fs, index=ledger_options_fs.index(er[5]) if er[5] in ledger_options_fs else 0, key="fs_edit_ledger")
            edit_amount = e6.number_input("Amount", min_value=0.0, value=float(er[6] or 0), step=0.01, format="%.2f", key="fs_edit_amount")
            e7,e8 = st.columns(2)
            edit_tds = e7.number_input("TDS", min_value=0.0, value=float(er[7] or 0), step=0.01, format="%.2f", key="fs_edit_tds")
            edit_net = round(max(0.0, edit_amount - edit_tds), 2)
            e8.number_input("Net Amount", min_value=0.0, value=edit_net, disabled=True, format="%.2f", key="fs_edit_net")
            edit_remarks = st.text_input("Remarks", value=er[9] or "", key="fs_edit_remarks")
            u1,u2 = st.columns(2)
            if u1.button("💾 Save Financial Statement Update", type="primary", use_container_width=True, key="fs_save_update"):
                if edit_amount <= 0:
                    st.error("Amount must be greater than zero.")
                elif edit_tds > edit_amount:
                    st.error("TDS cannot be greater than Amount.")
                elif edit_mode == "Sale" and not edit_invoice.strip():
                    st.error("Sale Voucher No. is required.")
                else:
                    conn.execute(
                        "UPDATE voucher_entries SET mode=?, entry_date=?, invoice_no=?, dr_cr=?, ledger_head=?, invoice_amount=?, tds=?, net_amount=?, remarks=? WHERE id=?",
                        (edit_mode, edit_date_str, edit_invoice.strip(), edit_drcr, edit_ledger, float(edit_amount), float(edit_tds), float(edit_net), edit_remarks.strip(), int(fs_edit_id))
                    )
                    conn.commit()
                    st.session_state.pop("financial_statement_edit_id", None)
                    st.success(f"Financial entry ID {fs_edit_id} updated successfully.")
                    st.rerun()
            if u2.button("✖ Close Edit", use_container_width=True, key="fs_close_edit"):
                st.session_state.pop("financial_statement_edit_id", None)
                st.rerun()

    if financial_report == "Financial Entry Report":
        # Create 3 tabs: Camlin, Open Advance, Accounting
        camlin_tab, open_advance_tab, hundi_tab, accounting_tab = st.tabs([
            "Camlin", "Open Advance", "HUNDI", "Accounting"
        ])
        
        # ======================================================================
        # TAB 1: CAMLIN REPORT
        # ======================================================================
        with camlin_tab:
            st.markdown("### Camlin Financial Report")
            
            # Date range filter with dd/mm/yyyy format
            col1, col2 = st.columns(2)
            with col1:
                from_date, from_date_str = get_date_input(
                    "From Date (DD/MM/YYYY)",
                    "camlin_from_date",
                    default_value=datetime.date.today().replace(day=1).strftime('%d/%m/%Y')
                )
            with col2:
                to_date, to_date_str = get_date_input(
                    "To Date (DD/MM/YYYY)",
                    "camlin_to_date",
                    default_value=get_today_str()
                )
            
            if from_date and to_date and from_date > to_date:
                st.error("From Date cannot be later than To Date.")
            else:
                # Fetch Camlin transactions
                camlin_rows = conn.execute("""
                    SELECT id, entry_date, mode, invoice_no, dr_cr, ledger_head, invoice_amount
                    FROM voucher_entries
                    WHERE TRIM(LOWER(ledger_head)) = ?
                    ORDER BY entry_date ASC, id ASC
                """, ("kukuyo camlin ltd.",)).fetchall()
                
                if not camlin_rows:
                    st.info("No Camlin financial entries available.")
                else:
                    # Fetch TDS deductions
                    tds_rows = conn.execute("""
                        SELECT mode, invoice_no, SUM(COALESCE(invoice_amount,0))
                        FROM voucher_entries
                        WHERE TRIM(LOWER(ledger_head)) = ?
                        GROUP BY mode, invoice_no
                    """, ("tds deduction",)).fetchall()
                    
                    tds_by_voucher = {
                        (str(mode), str(invoice_no)): float(amount or 0.0)
                        for mode, invoice_no, amount in tds_rows
                    }
                    
                    # Process data
                    report_data = []
                    opening_balance = 0.0
                    running_balance = 0.0
                    
                    # Calculate opening balance (before from_date)
                    for row in camlin_rows:
                        entry_date = row[1]
                        if entry_date and from_date:
                            try:
                                # Parse date from database
                                if isinstance(entry_date, str):
                                    entry_date_obj = datetime.datetime.strptime(entry_date, '%d/%m/%Y').date()
                                else:
                                    entry_date_obj = entry_date
                                
                                if entry_date_obj < from_date:
                                    amount = float(row[6] or 0.0)
                                    tds_val = tds_by_voucher.get((str(row[2]), str(row[3])), 0.0)
                                    net_amt = amount - tds_val
                                    if str(row[4]).strip().upper() == "DR":
                                        opening_balance += net_amt
                                    else:
                                        opening_balance -= net_amt
                            except:
                                pass
                    
                    running_balance = opening_balance
                    
                    # Process date range
                    for row in camlin_rows:
                        entry_date = row[1]
                        if entry_date and from_date and to_date:
                            try:
                                if isinstance(entry_date, str):
                                    entry_date_obj = datetime.datetime.strptime(entry_date, '%d/%m/%Y').date()
                                else:
                                    entry_date_obj = entry_date
                                
                                if from_date <= entry_date_obj <= to_date:
                                    amount = float(row[6] or 0.0)
                                    tds_val = tds_by_voucher.get((str(row[2]), str(row[3])), 0.0)
                                    net_amt = amount - tds_val
                                    
                                    if str(row[4]).strip().upper() == "DR":
                                        running_balance += net_amt
                                    else:
                                        running_balance -= net_amt
                                    
                                    report_data.append({
                                        "Date": format_date(entry_date),
                                        "Mode": row[2],
                                        "Document Number": row[3],
                                        "Dr / Cr": row[4],
                                        "Ledger Head": row[5],
                                        "Amount": amount,
                                        "TDS": tds_val,
                                        "Closing Balance": round(running_balance, 2)
                                    })
                            except:
                                pass
                    
                    if report_data:
                        df = pd.DataFrame(report_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # Show opening and closing balance
                        opening_side = "Dr" if opening_balance >= 0 else "Cr"
                        closing_side = "Dr" if running_balance >= 0 else "Cr"
                        
                        st.markdown(f"""
                        <div style='margin-top:16px; padding:12px 20px; background:#F8F9FA; border-radius:8px;'>
                            <div style='display:flex; justify-content:space-between;'>
                                <span style='font-weight:600;'>Opening Balance: {abs(opening_balance):,.2f} {opening_side}</span>
                                <span style='font-weight:600;'>Closing Balance: {abs(running_balance):,.2f} {closing_side}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Excel Export
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Camlin', startrow=2)
                        
                        buffer.seek(0)
                        wb = openpyxl.load_workbook(buffer)
                        ws = wb['Camlin']
                        
                        # Title
                        ws.merge_cells('A1:H1')
                        ws['A1'] = 'CAMLIN FINANCIAL REPORT'
                        ws['A1'].font = Font(size=14, bold=True)
                        ws['A1'].alignment = Alignment(horizontal='center')
                        
                        # Date range
                        ws.merge_cells('A2:H2')
                        ws['A2'] = f"From: {format_date(from_date)} To: {format_date(to_date)}"
                        ws['A2'].font = Font(size=10, italic=True)
                        ws['A2'].alignment = Alignment(horizontal='center')
                        
                        # Header style
                        header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                        thin_side = Side(style="thin", color="A6A6A6")
                        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                        
                        for cell in ws[3]:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal='center', vertical='center')
                            cell.border = cell_border
                        
                        # Data rows style
                        for row in ws.iter_rows(min_row=4):
                            for cell in row:
                                cell.border = cell_border
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                        
                        # Column widths
                        column_widths = {'A': 14, 'B': 14, 'C': 18, 'D': 10, 'E': 20, 'F': 16, 'G': 12, 'H': 18}
                        for col, width in column_widths.items():
                            ws.column_dimensions[col].width = width
                        
                        ws.freeze_panes = 'A4'
                        ws.sheet_view.showGridLines = False
                        
                        # Page setup
                        ws.page_setup.paperSize = ws.PAPERSIZE_A4
                        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                        ws.page_setup.fitToWidth = 1
                        ws.page_setup.fitToHeight = 0
                        ws.sheet_properties.pageSetUpPr.fitToPage = True
                        ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                        ws.print_options.horizontalCentered = True
                        ws.print_title_rows = "1:3"
                        
                        final_buffer = BytesIO()
                        wb.save(final_buffer)
                        
                        show_report_preview(
                            df,
                            "KUKUYO CAMLIN LIMITED (GUWAHATI) - LEDGER ACCOUNT",
                            f"From {format_date(from_date)} To {format_date(to_date)}",
                            "camlin_financial_report",
                            company="KUKUYO CAMLIN LIMITED (GUWAHATI)",
                            opening=f"{abs(opening_balance):,.2f} {opening_side}",
                            closing=f"{abs(running_balance):,.2f} {closing_side}"
                        )

                        st.download_button(
                            "⬇️ Download Camlin Report (Excel)",
                            data=final_buffer.getvalue(),
                            file_name=f"Camlin_Report_{format_date(from_date).replace('/', '-')}_to_{format_date(to_date).replace('/', '-')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_camlin_report"
                        )
                    else:
                        st.info("No Camlin entries found for the selected date range.")
        
        # ======================================================================
        # TAB 2: OPEN ADVANCE
        # ======================================================================
        with open_advance_tab:
            st.markdown("### Open Advance Ledger")
            
            # Open Advance filters
            col1, col2 = st.columns(2)
            with col1:
                adv_from_date, adv_from_date_str = get_date_input(
                    "From Date (DD/MM/YYYY)",
                    "adv_from_date",
                    default_value=datetime.date.today().replace(day=1).strftime('%d/%m/%Y')
                )
            with col2:
                adv_to_date, adv_to_date_str = get_date_input(
                    "To Date (DD/MM/YYYY)",
                    "adv_to_date",
                    default_value=get_today_str()
                )
            
            if adv_from_date and adv_to_date and adv_from_date > adv_to_date:
                st.error("From Date cannot be later than To Date.")
            else:
                # Fetch Advance Account transactions
                advance_rows = conn.execute("""
                    SELECT id, entry_date, mode, invoice_no, dr_cr, ledger_head, invoice_amount, remarks
                    FROM voucher_entries
                    WHERE TRIM(LOWER(ledger_head)) = ?
                    ORDER BY entry_date ASC, id ASC
                """, ("advance account",)).fetchall()
                
                if not advance_rows:
                    st.info("No Open Advance entries available.")
                else:
                    advance_data = []
                    running_bal = 0.0
                    
                    for row in advance_rows:
                        entry_date = row[1]
                        if entry_date and adv_from_date and adv_to_date:
                            try:
                                if isinstance(entry_date, str):
                                    entry_date_obj = datetime.datetime.strptime(entry_date, '%d/%m/%Y').date()
                                else:
                                    entry_date_obj = entry_date
                                
                                if adv_from_date <= entry_date_obj <= adv_to_date:
                                    amount = float(row[6] or 0.0)
                                    if str(row[4]).strip().upper() == "DR":
                                        running_bal += amount
                                    else:
                                        running_bal -= amount
                                    
                                    advance_data.append({
                                        "Date": format_date(entry_date),
                                        "Voucher No.": row[3],
                                        "Type": row[2],
                                        "Particulars": row[5],
                                        "Dr / Cr": row[4],
                                        "Amount": amount,
                                        "Running Balance": round(running_bal, 2),
                                        "Remarks": row[7] or ""
                                    })
                            except:
                                pass
                    
                    if advance_data:
                        df = pd.DataFrame(advance_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        st.markdown(f"""
                        <div style='margin-top:16px; padding:12px 20px; background:#F8F9FA; border-radius:8px;'>
                            <span style='font-weight:600;'>Closing Balance: {abs(running_bal):,.2f} {("Dr" if running_bal >= 0 else "Cr")}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Excel Export
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='OpenAdvance', startrow=2)
                        
                        buffer.seek(0)
                        wb = openpyxl.load_workbook(buffer)
                        ws = wb['OpenAdvance']
                        
                        ws.merge_cells('A1:H1')
                        ws['A1'] = 'OPEN ADVANCE LEDGER'
                        ws['A1'].font = Font(size=14, bold=True)
                        ws['A1'].alignment = Alignment(horizontal='center')
                        
                        ws.merge_cells('A2:H2')
                        ws['A2'] = f"From: {format_date(adv_from_date)} To: {format_date(adv_to_date)}"
                        ws['A2'].font = Font(size=10, italic=True)
                        ws['A2'].alignment = Alignment(horizontal='center')
                        
                        header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                        thin_side = Side(style="thin", color="A6A6A6")
                        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                        
                        for cell in ws[3]:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal='center', vertical='center')
                            cell.border = cell_border
                        
                        for row in ws.iter_rows(min_row=4):
                            for cell in row:
                                cell.border = cell_border
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                        
                        column_widths = {'A': 14, 'B': 16, 'C': 14, 'D': 20, 'E': 10, 'F': 16, 'G': 16, 'H': 20}
                        for col, width in column_widths.items():
                            ws.column_dimensions[col].width = width
                        
                        ws.freeze_panes = 'A4'
                        ws.sheet_view.showGridLines = False
                        
                        ws.page_setup.paperSize = ws.PAPERSIZE_A4
                        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                        ws.page_setup.fitToWidth = 1
                        ws.page_setup.fitToHeight = 0
                        ws.sheet_properties.pageSetUpPr.fitToPage = True
                        ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                        ws.print_options.horizontalCentered = True
                        ws.print_title_rows = "1:3"
                        
                        final_buffer = BytesIO()
                        wb.save(final_buffer)
                        
                        show_report_preview(
                            df,
                            "OPEN ADVANCE LEDGER",
                            f"From {format_date(adv_from_date)} To {format_date(adv_to_date)}",
                            "open_advance_report",
                            opening="—",
                            closing=f"{abs(running_bal):,.2f} {('Dr' if running_bal >= 0 else 'Cr')}"
                        )

                        st.download_button(
                            "⬇️ Download Open Advance Report (Excel)",
                            data=final_buffer.getvalue(),
                            file_name=f"OpenAdvance_{format_date(adv_from_date).replace('/', '-')}_to_{format_date(adv_to_date).replace('/', '-')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_open_advance_report"
                        )
                    else:
                        st.info("No Open Advance entries found for the selected date range.")
        
        # ======================================================================
        # TAB 3: HUNDI REPORT
        # ======================================================================
        with hundi_tab:
            st.markdown("### Hundi Report")

            h1, h2 = st.columns([1, 2])
            with h1:
                hundi_bank = st.selectbox(
                    "Select Hundi Bank",
                    ["MUZUHO", "SUMITOMO"],
                    key="hundi_bank"
                )
            with h2:
                st.caption(
                    f"Selected Bank: **{hundi_bank}** — is bank ki hundi activity yahan dikhegi."
                )

            st.subheader("Company Letterhead")
            st.caption("Yeh letterhead report/print ke liye hai — professional & stylish heading.")

            lh_html = """<link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Jost:wght@400;500;600&display=swap' rel='stylesheet'>
<style>
  * { box-sizing: border-box; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  body { margin: 0; font-family: "Jost", "Segoe UI", Arial, sans-serif; background: #dfe6ec; }
  .lh-page {
      width: 794px; height: 1123px; margin: 20px auto; display: flex; flex-direction: column;
      background: linear-gradient(180deg, #fffdf6 0%, #fbf5e6 100%);
      border: 2px solid #c9a94e; border-top: 7px solid #123b5e; border-radius: 10px;
      box-shadow: 0 10px 30px rgba(18, 59, 94, .28);
      padding: 28px 32px 22px 32px; position: relative;
  }
  .lh-hd { display: flex; align-items: center; gap: 20px; flex: none; }
  .lh-logo { flex: none; width: 82px; height: 82px; position: relative; }
  .lh-ring { position: absolute; inset: 0; border-radius: 50%;
      background: conic-gradient(from 0deg, rgba(201,169,78,0), rgba(201,169,78,.55), rgba(201,169,78,0), rgba(201,169,78,.55), rgba(201,169,78,0)); }
  .lh-core { position: absolute; inset: 6px; border-radius: 50%;
      background: linear-gradient(140deg, #123b5e, #1f6a9b); border: 2px solid #c9a94e;
      display: flex; align-items: center; justify-content: center;
      font-family: "Playfair Display", Georgia, serif; font-size: 30px; font-weight: 700; color: #e9c567; }
  .lh-mid { flex: 1; min-width: 0; }
.lh-name { font-family: "Playfair Display", Georgia, serif; font-size: 26px; font-weight: 700;
color: #123b5e; letter-spacing: 2px; white-space: nowrap; line-height: 1.05;
      text-shadow: 0 1px 0 #fff, 0 2px 0 #e9c567; }
  .lh-tagrow { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
  .lh-tagline { white-space: normal; font-size: 10px; letter-spacing: 2px; color: #a07c2a; font-weight: 600; }
  .lh-flank { flex: 1; height: 1px; background: linear-gradient(90deg, transparent, #c9a94e); }
  .lh-flank.r { background: linear-gradient(90deg, #c9a94e, transparent); }
  .lh-panel { flex: none; width: 236px; background: #f6eecd; border: 1px solid #dcc68c;
      border-left: 4px solid #123b5e; border-radius: 6px; padding: 11px 13px; white-space: nowrap; }
  .lh-p { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #2f4453; }
  .lh-p + .lh-p { margin-top: 6px; }
  .lh-p b { color: #b8860b; }
  .lh-gst { font-size: 12.5px; color: #123b5e; font-weight: 600; letter-spacing: .4px; }
  .lh-flourish { flex: none; display: flex; align-items: center; gap: 12px; margin: 20px 0 0 0; }
  .lh-fll { flex: 1; height: 0; border-top: 1px solid #dcc68c; }
  .lh-flc { font-size: 13px; color: #c9a94e; letter-spacing: 6px; }
  .lh-body { flex: 1; }
  .lh-ft { flex: none; border-top: 2px solid #c9a94e; padding-top: 13px; }
  .lh-ftrow { display: flex; align-items: center; justify-content: space-between; gap: 10px;
      font-size: 11.5px; color: #24404f; }
  .lh-ftrow span { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
  .lh-ftrow .sep { color: #c9a94e; font-weight: 700; }
  .lh-ftaddr { text-align: center; font-size: 12.5px; font-weight: 600; color: #24404f; margin-top: 9px; letter-spacing: .3px; }
  @media print {
      @page { size: A4 portrait; margin: 0; }
      html, body { width: 210mm; height: 297mm; margin: 0; padding: 0; background: #fff; }
      .lh-page { width: 210mm; height: 297mm; min-height: 0; margin: 0; overflow: hidden;
          border-radius: 0; border: 2px solid #c9a94e; border-top: 7px solid #123b5e;
          box-shadow: none; padding: 10mm 9mm 7mm 9mm; background: #fffdf6; }
      .lh-hd { flex-wrap: wrap; row-gap: 8px; }
      .lh-name { font-size: 22px; letter-spacing: 1.5px; white-space: normal; }
      .lh-tagline { font-size: 10px; letter-spacing: 1.5px; }
      .lh-panel { width: 205px; }
      .lh-flourish { margin-top: 12px; }
      .lh-ftrow { font-size: 10.5px; }
      .lh-no-print { display: none !important; }
  }
</style>
<div class='lh-no-print' style='text-align:center; margin: 6px auto 0 auto;'>
  <button onclick='window.print()' style='padding:10px 28px; font-size:14px; font-weight:600; cursor:pointer;
      background:linear-gradient(135deg,#123b5e,#1f6a9b); color:#fff; border:none; border-radius:6px;
      border-bottom:3px solid #0a2740;'>Print Letterhead (A4 Portrait)</button>
  <div style='margin:6px auto 0 auto; font-size:12px; color:#7a6a3a; max-width:560px; text-align:center;'>
    Print dialog me <b>Margins: None</b> aur <b>Header &amp; Footer: off</b> karein —
    output bilkul preview (A4 page) jaisa hi milega.
  </div>
</div>
<div class='lh-page'>
  <div class='lh-hd'>
    <div class='lh-logo'><div class='lh-ring'></div><div class='lh-core'>SP</div></div>
    <div class='lh-mid'>
      <div class='lh-name'>SUBH PAPER COMPANY</div>
      <div class='lh-tagrow'>
        <span class='lh-flank'></span>
        <span class='lh-tagline'>MANUFACTURER &amp; EXPORTER OF NOTEBOOKS &amp; PAPER PRODUCTS</span>
        <span class='lh-flank r'></span>
      </div>
    </div>
    <div class='lh-panel'>
      <div class='lh-gst'>GST No. : <b>19AFLFS3701G1ZW</b></div>
      <div class='lh-p'>
        <svg width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='#123b5e' stroke-width='2'><circle cx='12' cy='12' r='9'/><path d='M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z'/></svg>
        <a href='https://www.subhpapercompany.com' target='_blank' style='text-decoration:none; color:#123b5e; font-weight:600;'>www.subhpapercompany.com</a>
      </div>
      <div class='lh-p'>
        <svg width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='#123b5e' stroke-width='2'><rect x='3' y='5' width='18' height='14' rx='2'/><path d='M3 7l9 6 9-6'/></svg>
        <span style='color:#123b5e; font-weight:600;'>email : subhpaperslg@gmail.com</span>
      </div>
    </div>
  </div>
  <div class='lh-flourish'>
    <span class='lh-fll'></span>
    <span class='lh-flc'>✦&nbsp;&nbsp;✦&nbsp;&nbsp;✦</span>
    <span class='lh-fll'></span>
  </div>
  <div class='lh-body'></div>
  <div class='lh-ft'>
    <div class='lh-ftrow'>
      <span><svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='#b8860b' stroke-width='2'><rect x='3' y='5' width='18' height='14' rx='2'/><path d='M3 7l9 6 9-6'/></svg>email : subhpaperslg@gmail.com</span>
      <span class='sep'>|</span>
      <span><svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='#b8860b' stroke-width='2'><circle cx='12' cy='12' r='9'/><path d='M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z'/></svg>www.subhpapercompany.com</span>
      <span class='sep'>|</span>
      <span style='font-weight:600;'>GST No. : 19AFLFS3701G1ZW</span>
    </div>
    <div class='lh-ftaddr'>A14, Fulbari Industrial Park, Chobavita, Jalpaiguri, West Bengal. Pin - 734015</div>
  </div>
</div>"""

            components.html(lh_html, height=1180, scrolling=True)

        # ======================================================================
        # TAB 4: ACCOUNTING (Day Book, Ledger, Others)
        # ======================================================================
        with accounting_tab:
            st.markdown("### Accounting Reports")
            
            # Create 3 sub-tabs within Accounting
            daybook_tab, ledger_tab, others_tab = st.tabs([
                "📖 Day Book", "📒 Ledger", "📊 Others"
            ])
            
            # ==================================================================
            # SUB-TAB 1: DAY BOOK
            # ==================================================================
            with daybook_tab:
                st.markdown("#### Day Book - Daily Transaction Summary")
                
                col1, col2 = st.columns(2)
                with col1:
                    db_from_date, db_from_date_str = get_date_input(
                        "From Date (DD/MM/YYYY)",
                        "db_from_date",
                        default_value=datetime.date.today().replace(day=1).strftime('%d/%m/%Y')
                    )
                with col2:
                    db_to_date, db_to_date_str = get_date_input(
                        "To Date (DD/MM/YYYY)",
                        "db_to_date",
                        default_value=get_today_str()
                    )
                
                if db_from_date and db_to_date and db_from_date > db_to_date:
                    st.error("From Date cannot be later than To Date.")
                else:
                    # Fetch all vouchers for date range
                    db_rows = conn.execute("""
                        SELECT entry_date, mode, invoice_no, dr_cr, ledger_head, invoice_amount, remarks
                        FROM voucher_entries
                        WHERE entry_date >= ? AND entry_date <= ?
                        ORDER BY entry_date ASC, id ASC
                    """, (db_from_date_str, db_to_date_str)).fetchall()
                    
                    if not db_rows:
                        st.info("No transactions found for the selected date range.")
                    else:
                        # Group by date
                        daybook_data = []
                        current_date = None
                        daily_debit = 0.0
                        daily_credit = 0.0
                        
                        for row in db_rows:
                            entry_date = row[0]
                            amount = float(row[5] or 0.0)
                            
                            if current_date is None:
                                current_date = entry_date
                            
                            if entry_date != current_date and current_date is not None:
                                # Add daily summary row
                                if daily_debit > 0 or daily_credit > 0:
                                    daybook_data.append({
                                        "Date": format_date(current_date),
                                        "Particulars": "--- DAILY TOTAL ---",
                                        "Vch Type": "",
                                        "Vch No.": "",
                                        "Debit": daily_debit,
                                        "Credit": daily_credit,
                                        "Remarks": ""
                                    })
                                current_date = entry_date
                                daily_debit = 0.0
                                daily_credit = 0.0
                            
                            if str(row[3]).strip().upper() == "DR":
                                daily_debit += amount
                            else:
                                daily_credit += amount
                            
                            daybook_data.append({
                                "Date": format_date(entry_date),
                                "Particulars": row[4],
                                "Vch Type": row[1],
                                "Vch No.": row[2],
                                "Debit": amount if str(row[3]).strip().upper() == "DR" else 0.0,
                                "Credit": amount if str(row[3]).strip().upper() == "CR" else 0.0,
                                "Remarks": row[6] or ""
                            })
                        
                        # Add final daily total
                        if daily_debit > 0 or daily_credit > 0:
                            daybook_data.append({
                                "Date": format_date(current_date),
                                "Particulars": "--- DAILY TOTAL ---",
                                "Vch Type": "",
                                "Vch No.": "",
                                "Debit": daily_debit,
                                "Credit": daily_credit,
                                "Remarks": ""
                            })
                        
                        if daybook_data:
                            df = pd.DataFrame(daybook_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            # Excel Export
                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False, sheet_name='DayBook', startrow=2)
                            
                            buffer.seek(0)
                            wb = openpyxl.load_workbook(buffer)
                            ws = wb['DayBook']
                            
                            ws.merge_cells('A1:G1')
                            ws['A1'] = 'DAY BOOK - Daily Transaction Summary'
                            ws['A1'].font = Font(size=14, bold=True)
                            ws['A1'].alignment = Alignment(horizontal='center')
                            
                            ws.merge_cells('A2:G2')
                            ws['A2'] = f"From: {format_date(db_from_date)} To: {format_date(db_to_date)}"
                            ws['A2'].font = Font(size=10, italic=True)
                            ws['A2'].alignment = Alignment(horizontal='center')
                            
                            header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                            header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                            thin_side = Side(style="thin", color="A6A6A6")
                            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                            
                            for cell in ws[3]:
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                                cell.border = cell_border
                            
                            for row in ws.iter_rows(min_row=4):
                                for cell in row:
                                    cell.border = cell_border
                                    cell.alignment = Alignment(horizontal='center', vertical='center')
                            
                            column_widths = {'A': 14, 'B': 22, 'C': 14, 'D': 14, 'E': 16, 'F': 16, 'G': 20}
                            for col, width in column_widths.items():
                                ws.column_dimensions[col].width = width
                            
                            ws.freeze_panes = 'A4'
                            ws.sheet_view.showGridLines = False
                            
                            ws.page_setup.paperSize = ws.PAPERSIZE_A4
                            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                            ws.page_setup.fitToWidth = 1
                            ws.page_setup.fitToHeight = 0
                            ws.sheet_properties.pageSetUpPr.fitToPage = True
                            ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                            ws.print_options.horizontalCentered = True
                            ws.print_title_rows = "1:3"
                            
                            final_buffer = BytesIO()
                            wb.save(final_buffer)
                            
                            show_report_preview(
                                df,
                                "DAY BOOK - DAILY TRANSACTION SUMMARY",
                                f"From {format_date(db_from_date)} To {format_date(db_to_date)}",
                                "day_book_report"
                            )

                            st.download_button(
                                "⬇️ Download Day Book (Excel)",
                                data=final_buffer.getvalue(),
                                file_name=f"DayBook_{format_date(db_from_date).replace('/', '-')}_to_{format_date(db_to_date).replace('/', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_daybook_report"
                            )
            
            # ==================================================================
            # SUB-TAB 2: LEDGER (EXACT PATTERN AS IMAGE)
            # ==================================================================
            with ledger_tab:
                st.markdown("#### Ledger Vouchers")
                st.markdown("<div class='ledger-company-name'>🏢 SUBH PAPER COMPANY</div>", unsafe_allow_html=True)
                
                # Ledger selection
                ledger_options = [r[0] for r in conn.execute(
                    "SELECT ledger_name FROM ledger_master ORDER BY ledger_name"
                ).fetchall()]
                
                if not ledger_options:
                    st.warning("No ledgers found. Please create ledgers in Financial Entry.")
                else:
                    col1, col2, col3 = st.columns([2, 1.5, 1.5])
                    with col1:
                        selected_ledger = st.selectbox(
                            "Select Ledger",
                            ledger_options,
                            key="ledger_select"
                        )
                    with col2:
                        led_from_date, led_from_date_str = get_date_input(
                            "From Date (DD/MM/YYYY)",
                            "led_from_date",
                            default_value=datetime.date.today().replace(day=1).strftime('%d/%m/%Y')
                        )
                    with col3:
                        led_to_date, led_to_date_str = get_date_input(
                            "To Date (DD/MM/YYYY)",
                            "led_to_date",
                            default_value=get_today_str()
                        )
                    
                    if led_from_date and led_to_date and led_from_date > led_to_date:
                        st.error("From Date cannot be later than To Date.")
                    else:
                        # Fetch ledger transactions
                        led_rows = conn.execute("""
                            SELECT entry_date, mode, invoice_no, dr_cr, ledger_head, invoice_amount
                            FROM voucher_entries
                            WHERE TRIM(LOWER(ledger_head)) = ?
                            AND entry_date >= ? AND entry_date <= ?
                            ORDER BY entry_date ASC, id ASC
                        """, (selected_ledger.lower(), led_from_date_str, led_to_date_str)).fetchall()
                        
                        if not led_rows:
                            st.info(f"No transactions found for {selected_ledger} in the selected date range.")
                        else:
                            # Format as per image pattern
                            st.markdown(f"<div class='ledger-ledger-name'>📒 Ledger: <b>{selected_ledger}</b></div>", unsafe_allow_html=True)
                            
                            # Process data
                            ledger_data = []
                            opening_bal = 0.0
                            running_bal = 0.0
                            
                            # Calculate opening balance
                            opening_rows = conn.execute("""
                                SELECT entry_date, dr_cr, invoice_amount
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date < ?
                                ORDER BY entry_date ASC, id ASC
                            """, (selected_ledger.lower(), led_from_date_str)).fetchall()
                            
                            for row in opening_rows:
                                amount = float(row[2] or 0.0)
                                if str(row[1]).strip().upper() == "DR":
                                    opening_bal += amount
                                else:
                                    opening_bal -= amount
                            
                            running_bal = opening_bal
                            
                            # Process date range
                            for row in led_rows:
                                amount = float(row[5] or 0.0)
                                dr_cr = row[3]
                                
                                if str(dr_cr).strip().upper() == "DR":
                                    debit = amount
                                    credit = 0.0
                                    running_bal += amount
                                else:
                                    debit = 0.0
                                    credit = amount
                                    running_bal -= amount
                                
                                ledger_data.append({
                                    "Date": format_date(row[0]),
                                    "Particulars": row[4],
                                    "Vch Type": row[1],
                                    "Vch No.": row[2],
                                    "Debit": debit,
                                    "Credit": credit
                                })
                            
                            if ledger_data:
                                df = pd.DataFrame(ledger_data)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                
                                # Footer with opening, total, closing balance
                                total_debit = df['Debit'].sum()
                                total_credit = df['Credit'].sum()
                                
                                opening_side = "Dr" if opening_bal >= 0 else "Cr"
                                closing_side = "Dr" if running_bal >= 0 else "Cr"
                                
                                st.markdown(f"""
                                <div class='ledger-footer'>
                                    <div style='display:flex; justify-content:space-between; padding:4px 0;'>
                                        <span>Opening Balance : {abs(opening_bal):,.2f} {opening_side}</span>
                                        <span>Current Total : {total_debit:,.2f}</span>
                                        <span>Closing Balance : {abs(running_bal):,.2f} {closing_side}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Excel Export - Exact format as image
                                buffer = BytesIO()
                                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                    df.to_excel(writer, index=False, sheet_name='Ledger', startrow=4)
                                
                                buffer.seek(0)
                                wb = openpyxl.load_workbook(buffer)
                                ws = wb['Ledger']
                                
                                # Title
                                ws.merge_cells('A1:F1')
                                ws['A1'] = 'Ledger Vouchers'
                                ws['A1'].font = Font(size=16, bold=True)
                                ws['A1'].alignment = Alignment(horizontal='center')
                                
                                # Company Name
                                ws.merge_cells('A2:F2')
                                ws['A2'] = 'SUBH PAPER COMPANY'
                                ws['A2'].font = Font(size=12, bold=True)
                                ws['A2'].alignment = Alignment(horizontal='center')
                                
                                # Ledger Name
                                ws.merge_cells('A3:F3')
                                ws['A3'] = f'Ledger: {selected_ledger}'
                                ws['A3'].font = Font(size=11, bold=True)
                                ws['A3'].alignment = Alignment(horizontal='left')
                                
                                # Header
                                header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                                header_font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                                thin_side = Side(style="thin", color="A6A6A6")
                                cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                                
                                for cell in ws[4]:
                                    cell.fill = header_fill
                                    cell.font = header_font
                                    cell.alignment = Alignment(horizontal='center', vertical='center')
                                    cell.border = cell_border
                                
                                # Data rows
                                for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
                                    for cell in row:
                                        cell.border = cell_border
                                        cell.alignment = Alignment(horizontal='center', vertical='center')
                                        if cell.column in [5, 6]:  # Debit and Credit columns
                                            cell.alignment = Alignment(horizontal='right', vertical='center')
                                
                                # Footer
                                footer_row = ws.max_row + 2
                                ws.merge_cells(f'A{footer_row}:D{footer_row}')
                                ws[f'A{footer_row}'] = f'Opening Balance : {abs(opening_bal):,.2f} {opening_side}'
                                ws[f'A{footer_row}'].font = Font(bold=True)
                                
                                footer_row2 = footer_row + 1
                                ws.merge_cells(f'A{footer_row2}:D{footer_row2}')
                                ws[f'A{footer_row2}'] = f'Current Total : {total_debit:,.2f}'
                                ws[f'A{footer_row2}'].font = Font(bold=True)
                                
                                footer_row3 = footer_row + 2
                                ws.merge_cells(f'A{footer_row3}:D{footer_row3}')
                                ws[f'A{footer_row3}'] = f'Closing Balance : {abs(running_bal):,.2f} {closing_side}'
                                ws[f'A{footer_row3}'].font = Font(bold=True)
                                
                                # Column widths
                                column_widths = {'A': 14, 'B': 20, 'C': 14, 'D': 16, 'E': 16, 'F': 16}
                                for col, width in column_widths.items():
                                    ws.column_dimensions[col].width = width
                                
                                ws.freeze_panes = 'A5'
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
                                
                                show_report_preview(
                                    df,
                                    f"{selected_ledger} - LEDGER ACCOUNT",
                                    f"From {format_date(led_from_date)} To {format_date(led_to_date)}",
                                    "ledger_report"
                                )

                                st.download_button(
                                    f"⬇️ Download Ledger Report - {selected_ledger} (Excel)",
                                    data=final_buffer.getvalue(),
                                    file_name=f"Ledger_{selected_ledger.replace(' ', '_')}_{format_date(led_from_date).replace('/', '-')}_to_{format_date(led_to_date).replace('/', '-')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_ledger_report"
                                )
            
            # ==================================================================
            # SUB-TAB 3: OTHERS (Trial Balance, P&L, Balance Sheet)
            # ==================================================================
            with others_tab:
                st.markdown("#### Other Reports")
                
                report_type = st.selectbox(
                    "Select Report Type",
                    ["Trial Balance", "Profit & Loss Account", "Balance Sheet"],
                    key="others_report_type"
                )
                
                report_from_date, report_from_str = get_date_input(
                    "From Date (DD/MM/YYYY)",
                    "others_report_from",
                    default_value=get_today_str()
                )
                report_to_date, report_to_str = get_date_input(
                    "To Date (DD/MM/YYYY)",
                    "others_report_to",
                    default_value=get_today_str()
                )

                if report_from_date and report_to_date:
                    if report_type == "Trial Balance":
                        st.markdown("##### Trial Balance")
                        
                        # Fetch all ledgers with balances
                        trial_balance_data = []
                        all_ledgers = conn.execute(
                            "SELECT DISTINCT ledger_head FROM voucher_entries ORDER BY ledger_head"
                        ).fetchall()
                        
                        for ledger in all_ledgers:
                            ledger_name = ledger[0]
                            # Calculate balance for this ledger
                            rows = conn.execute("""
                                SELECT dr_cr, SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                GROUP BY dr_cr
                            """, (ledger_name.lower(), report_from_str, report_to_str)).fetchall()
                            
                            debit_total = 0.0
                            credit_total = 0.0
                            
                            for row in rows:
                                if str(row[0]).strip().upper() == "DR":
                                    debit_total += float(row[1] or 0.0)
                                else:
                                    credit_total += float(row[1] or 0.0)
                            
                            balance = debit_total - credit_total
                            if balance != 0:
                                trial_balance_data.append({
                                    "Ledger Name": ledger_name,
                                    "Debit Balance": abs(balance) if balance > 0 else 0.0,
                                    "Credit Balance": abs(balance) if balance < 0 else 0.0
                                })
                        
                        if trial_balance_data:
                            df = pd.DataFrame(trial_balance_data)
                            total_debit = df['Debit Balance'].sum()
                            total_credit = df['Credit Balance'].sum()
                            
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            st.markdown(f"""
                            <div style='margin-top:12px; padding:10px 16px; background:#F8F9FA; border-radius:6px;'>
                                <div style='display:flex; justify-content:space-between;'>
                                    <span><b>Total Debit:</b> {total_debit:,.2f}</span>
                                    <span><b>Total Credit:</b> {total_credit:,.2f}</span>
                                    <span><b>Difference:</b> {abs(total_debit - total_credit):,.2f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Excel Export
                            # Build the workbook directly with openpyxl.
                            # This avoids the pandas/openpyxl writer finalization issue
                            # that can raise: "At least one sheet must be visible".
                            wb = openpyxl.Workbook()
                            ws = wb.active
                            ws.title = 'TrialBalance'

                            # Title row
                            ws.merge_cells('A1:C1')
                            ws['A1'] = f'TRIAL BALANCE - {report_from_str} TO {report_to_str}'
                            ws['A1'].font = Font(size=14, bold=True)
                            ws['A1'].alignment = Alignment(horizontal='center')

                            # Write dataframe headers at row 3
                            for col_idx, column_name in enumerate(df.columns, start=1):
                                ws.cell(row=3, column=col_idx, value=column_name)

                            # Write dataframe data from row 4
                            for row_idx, row_values in enumerate(df.itertuples(index=False, name=None), start=4):
                                for col_idx, value in enumerate(row_values, start=1):
                                    ws.cell(row=row_idx, column=col_idx, value=value)
                            
                            ws.merge_cells('A1:C1')
                            ws['A1'] = f'TRIAL BALANCE - {report_from_str} TO {report_to_str}'
                            ws['A1'].font = Font(size=14, bold=True)
                            ws['A1'].alignment = Alignment(horizontal='center')
                            
                            header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                            header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                            thin_side = Side(style="thin", color="A6A6A6")
                            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                            
                            for cell in ws[3]:
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = Alignment(horizontal='center', vertical='center')
                                cell.border = cell_border
                            
                            for row in ws.iter_rows(min_row=4):
                                for cell in row:
                                    cell.border = cell_border
                                    cell.alignment = Alignment(horizontal='center', vertical='center')
                            
                            column_widths = {'A': 25, 'B': 18, 'C': 18}
                            for col, width in column_widths.items():
                                ws.column_dimensions[col].width = width
                            
                            ws.freeze_panes = 'A4'
                            ws.sheet_view.showGridLines = False
                            
                            ws.page_setup.paperSize = ws.PAPERSIZE_A4
                            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
                            ws.page_setup.fitToWidth = 1
                            ws.page_setup.fitToHeight = 0
                            ws.sheet_properties.pageSetUpPr.fitToPage = True
                            ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                            ws.print_options.horizontalCentered = True
                            ws.print_title_rows = "1:3"
                            
                            final_buffer = BytesIO()
                            wb.save(final_buffer)
                            
                            show_report_preview(
                                df,
                                "TRIAL BALANCE",
                                f"As on {format_date(report_from_date)} To {format_date(report_to_date)}",
                                "trial_balance_report"
                            )

                            st.download_button(
                                "⬇️ Download Trial Balance (Excel)",
                                data=final_buffer.getvalue(),
                                file_name=f"TrialBalance_{report_from_str.replace('/', '-')}_to_{report_to_str.replace('/', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_trial_balance"
                            )
                        else:
                            st.info("No transactions found to generate Trial Balance.")
                    
                    elif report_type == "Profit & Loss Account":
                        st.markdown("##### Profit & Loss Account")
                        
                        # Fetch all revenue and expense ledgers
                        revenue_ledgers = ["Sale Account", "Sales Account", "Income Account"]
                        expense_ledgers = ["Purchase Account", "Expense Account", "Salary Account", "Rent Account"]
                        
                        total_revenue = 0.0
                        total_expenses = 0.0
                        
                        # Calculate revenue
                        for ledger in revenue_ledgers:
                            rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'CR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            if rows and rows[0]:
                                total_revenue += float(rows[0])
                        
                        # Calculate expenses
                        for ledger in expense_ledgers:
                            rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'DR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            if rows and rows[0]:
                                total_expenses += float(rows[0])
                        
                        # Also fetch from all ledgers to be more comprehensive
                        all_ledgers = conn.execute(
                            "SELECT DISTINCT ledger_head FROM voucher_entries ORDER BY ledger_head"
                        ).fetchall()
                        
                        pnl_data = []
                        for ledger in all_ledgers:
                            ledger_name = ledger[0]
                            # Check if it's revenue (credit balance)
                            credit_rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'CR'
                            """, (ledger_name.lower(), report_from_str, report_to_str)).fetchone()
                            
                            debit_rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'DR'
                            """, (ledger_name.lower(), report_from_str, report_to_str)).fetchone()
                            
                            credit_total = float(credit_rows[0] or 0.0) if credit_rows else 0.0
                            debit_total = float(debit_rows[0] or 0.0) if debit_rows else 0.0
                            
                            net_balance = credit_total - debit_total
                            
                            if net_balance > 0:
                                pnl_data.append({
                                    "Particulars": ledger_name,
                                    "Credit (Revenue)": credit_total,
                                    "Debit (Expense)": debit_total,
                                    "Net Balance": net_balance,
                                    "Type": "Revenue"
                                })
                            elif net_balance < 0:
                                pnl_data.append({
                                    "Particulars": ledger_name,
                                    "Credit (Revenue)": credit_total,
                                    "Debit (Expense)": debit_total,
                                    "Net Balance": abs(net_balance),
                                    "Type": "Expense"
                                })
                        
                        if pnl_data:
                            df = pd.DataFrame(pnl_data)
                            
                            # Separate revenue and expense
                            revenue_df = df[df['Type'] == 'Revenue']
                            expense_df = df[df['Type'] == 'Expense']
                            
                            st.markdown("##### Revenue / Income")
                            if not revenue_df.empty:
                                st.dataframe(revenue_df[['Particulars', 'Credit (Revenue)']], use_container_width=True, hide_index=True)
                                total_rev = revenue_df['Credit (Revenue)'].sum()
                                st.markdown(f"**Total Revenue: {total_rev:,.2f}**")
                            else:
                                st.info("No revenue entries found.")
                            
                            st.markdown("##### Expenses")
                            if not expense_df.empty:
                                st.dataframe(expense_df[['Particulars', 'Debit (Expense)']], use_container_width=True, hide_index=True)
                                total_exp = expense_df['Debit (Expense)'].sum()
                                st.markdown(f"**Total Expenses: {total_exp:,.2f}**")
                            else:
                                st.info("No expense entries found.")
                            
                            if revenue_df.empty and expense_df.empty:
                                st.info("No data available to generate P&L Account.")
                            else:
                                # Net Profit/Loss
                                total_rev = revenue_df['Credit (Revenue)'].sum() if not revenue_df.empty else 0
                                total_exp = expense_df['Debit (Expense)'].sum() if not expense_df.empty else 0
                                net_profit_loss = total_rev - total_exp
                                
                                st.markdown(f"""
                                <div style='margin-top:16px; padding:14px 20px; background:#F8F9FA; border-radius:8px; border-left:4px solid {'#28A745' if net_profit_loss >= 0 else '#DC3545'};'>
                                    <div style='font-size:18px; font-weight:700;'>
                                        {'Net Profit' if net_profit_loss >= 0 else 'Net Loss'}: 
                                        {abs(net_profit_loss):,.2f}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Excel Export
                                buffer = BytesIO()
                                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                    if not revenue_df.empty:
                                        revenue_df[['Particulars', 'Credit (Revenue)']].to_excel(writer, index=False, sheet_name='Revenue', startrow=2)
                                    if not expense_df.empty:
                                        expense_df[['Particulars', 'Debit (Expense)']].to_excel(writer, index=False, sheet_name='Expenses', startrow=2)
                                
                                buffer.seek(0)
                                wb = openpyxl.load_workbook(buffer)
                                
                                for sheet_name in ['Revenue', 'Expenses']:
                                    if sheet_name in wb.sheetnames:
                                        ws = wb[sheet_name]
                                        ws.merge_cells('A1:B1')
                                        ws['A1'] = f'PROFIT & LOSS ACCOUNT - {report_from_str} TO {report_to_str}'
                                        ws['A1'].font = Font(size=14, bold=True)
                                        ws['A1'].alignment = Alignment(horizontal='center')
                                        
                                        header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                                        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                                        thin_side = Side(style="thin", color="A6A6A6")
                                        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                                        
                                        for cell in ws[3]:
                                            cell.fill = header_fill
                                            cell.font = header_font
                                            cell.alignment = Alignment(horizontal='center', vertical='center')
                                            cell.border = cell_border
                                        
                                        for row in ws.iter_rows(min_row=4):
                                            for cell in row:
                                                cell.border = cell_border
                                                cell.alignment = Alignment(horizontal='center', vertical='center')
                                        
                                        ws.column_dimensions['A'].width = 30
                                        ws.column_dimensions['B'].width = 18
                                        
                                        ws.freeze_panes = 'A4'
                                        ws.sheet_view.showGridLines = False
                                        
                                        ws.page_setup.paperSize = ws.PAPERSIZE_A4
                                        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
                                        ws.page_setup.fitToWidth = 1
                                        ws.page_setup.fitToHeight = 0
                                        ws.sheet_properties.pageSetUpPr.fitToPage = True
                                        ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                                        ws.print_options.horizontalCentered = True
                                        ws.print_title_rows = "1:3"
                                
                                final_buffer = BytesIO()
                                wb.save(final_buffer)
                                
                                show_report_preview(
                                    df,
                                    "PROFIT & LOSS ACCOUNT",
                                    f"As on {format_date(report_from_date)} To {format_date(report_to_date)}",
                                    "profit_loss_report"
                                )

                                st.download_button(
                                    "⬇️ Download P&L Account (Excel)",
                                    data=final_buffer.getvalue(),
                                    file_name=f"ProfitLoss_{report_from_str.replace('/', '-')}_to_{report_to_str.replace('/', '-')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_pnl_report"
                                )
                        else:
                            st.info("No data available to generate Profit & Loss Account.")
                    
                    elif report_type == "Balance Sheet":
                        st.markdown("##### Balance Sheet")
                        
                        # Fetch assets and liabilities
                        asset_ledgers = ["Cash Account", "Bank Account", "Advance Account", "Receivable Account"]
                        liability_ledgers = ["Against Bill", "Payable Account", "Loan Account"]
                        
                        assets_data = []
                        liabilities_data = []
                        
                        total_assets = 0.0
                        total_liabilities = 0.0
                        
                        # Calculate assets (debit balance)
                        for ledger in asset_ledgers:
                            rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'DR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            
                            credit_rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'CR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            
                            debit_total = float(rows[0] or 0.0) if rows else 0.0
                            credit_total = float(credit_rows[0] or 0.0) if credit_rows else 0.0
                            net_balance = debit_total - credit_total
                            
                            if net_balance > 0:
                                assets_data.append({
                                    "Particulars": ledger,
                                    "Amount": net_balance
                                })
                                total_assets += net_balance
                        
                        # Calculate liabilities (credit balance)
                        for ledger in liability_ledgers:
                            rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'CR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            
                            debit_rows = conn.execute("""
                                SELECT SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                AND TRIM(UPPER(dr_cr)) = 'DR'
                            """, (ledger.lower(), report_from_str, report_to_str)).fetchone()
                            
                            credit_total = float(rows[0] or 0.0) if rows else 0.0
                            debit_total = float(debit_rows[0] or 0.0) if debit_rows else 0.0
                            net_balance = credit_total - debit_total
                            
                            if net_balance > 0:
                                liabilities_data.append({
                                    "Particulars": ledger,
                                    "Amount": net_balance
                                })
                                total_liabilities += net_balance
                        
                        # Also fetch all other ledgers with balances
                        all_ledgers = conn.execute(
                            "SELECT DISTINCT ledger_head FROM voucher_entries ORDER BY ledger_head"
                        ).fetchall()
                        
                        for ledger in all_ledgers:
                            ledger_name = ledger[0]
                            if ledger_name in asset_ledgers or ledger_name in liability_ledgers:
                                continue
                            
                            rows = conn.execute("""
                                SELECT dr_cr, SUM(COALESCE(invoice_amount,0))
                                FROM voucher_entries
                                WHERE TRIM(LOWER(ledger_head)) = ?
                                AND entry_date >= ? AND entry_date <= ?
                                GROUP BY dr_cr
                            """, (ledger_name.lower(), report_from_str, report_to_str)).fetchall()
                            
                            debit_total = 0.0
                            credit_total = 0.0
                            
                            for row in rows:
                                if str(row[0]).strip().upper() == "DR":
                                    debit_total += float(row[1] or 0.0)
                                else:
                                    credit_total += float(row[1] or 0.0)
                            
                            net_balance = debit_total - credit_total
                            
                            if net_balance > 0:
                                if ledger_name not in [a['Particulars'] for a in assets_data]:
                                    assets_data.append({
                                        "Particulars": ledger_name,
                                        "Amount": net_balance
                                    })
                                    total_assets += net_balance
                            elif net_balance < 0:
                                if ledger_name not in [l['Particulars'] for l in liabilities_data]:
                                    liabilities_data.append({
                                        "Particulars": ledger_name,
                                        "Amount": abs(net_balance)
                                    })
                                    total_liabilities += abs(net_balance)
                        
                        st.markdown("##### Assets")
                        if assets_data:
                            df_assets = pd.DataFrame(assets_data)
                            st.dataframe(df_assets, use_container_width=True, hide_index=True)
                            st.markdown(f"**Total Assets: {total_assets:,.2f}**")
                        else:
                            st.info("No assets found.")
                        
                        st.markdown("##### Liabilities")
                        if liabilities_data:
                            df_liabilities = pd.DataFrame(liabilities_data)
                            st.dataframe(df_liabilities, use_container_width=True, hide_index=True)
                            st.markdown(f"**Total Liabilities: {total_liabilities:,.2f}**")
                        else:
                            st.info("No liabilities found.")
                        
                        if assets_data or liabilities_data:
                            st.markdown(f"""
                            <div style='margin-top:16px; padding:14px 20px; background:#F8F9FA; border-radius:8px; border-left:4px solid {'#28A745' if abs(total_assets - total_liabilities) < 0.01 else '#DC3545'};'>
                                <div style='display:flex; justify-content:space-between;'>
                                    <span style='font-weight:700;'>Total Assets: {total_assets:,.2f}</span>
                                    <span style='font-weight:700;'>Total Liabilities: {total_liabilities:,.2f}</span>
                                    <span style='font-weight:700;'>Difference: {abs(total_assets - total_liabilities):,.2f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Excel Export
                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                if assets_data:
                                    df_assets.to_excel(writer, index=False, sheet_name='Assets', startrow=2)
                                if liabilities_data:
                                    df_liabilities.to_excel(writer, index=False, sheet_name='Liabilities', startrow=2)
                            
                            buffer.seek(0)
                            wb = openpyxl.load_workbook(buffer)
                            
                            for sheet_name in ['Assets', 'Liabilities']:
                                if sheet_name in wb.sheetnames:
                                    ws = wb[sheet_name]
                                    ws.merge_cells('A1:B1')
                                    ws['A1'] = f'BALANCE SHEET - {report_from_str} TO {report_to_str}'
                                    ws['A1'].font = Font(size=14, bold=True)
                                    ws['A1'].alignment = Alignment(horizontal='center')
                                    
                                    header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                                    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                                    thin_side = Side(style="thin", color="A6A6A6")
                                    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                                    
                                    for cell in ws[3]:
                                        cell.fill = header_fill
                                        cell.font = header_font
                                        cell.alignment = Alignment(horizontal='center', vertical='center')
                                        cell.border = cell_border
                                    
                                    for row in ws.iter_rows(min_row=4):
                                        for cell in row:
                                            cell.border = cell_border
                                            cell.alignment = Alignment(horizontal='center', vertical='center')
                                    
                                    ws.column_dimensions['A'].width = 30
                                    ws.column_dimensions['B'].width = 18
                                    
                                    ws.freeze_panes = 'A4'
                                    ws.sheet_view.showGridLines = False
                                    
                                    ws.page_setup.paperSize = ws.PAPERSIZE_A4
                                    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
                                    ws.page_setup.fitToWidth = 1
                                    ws.page_setup.fitToHeight = 0
                                    ws.sheet_properties.pageSetUpPr.fitToPage = True
                                    ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.20, bottom=0.20, header=0.05, footer=0.05)
                                    ws.print_options.horizontalCentered = True
                                    ws.print_title_rows = "1:3"
                            
                            final_buffer = BytesIO()
                            wb.save(final_buffer)
                            
                            balance_preview_df = pd.DataFrame(
                                [{"Particulars": r["Particulars"], "Type": "Asset", "Amount": r["Amount"]} for r in assets_data] +
                                [{"Particulars": r["Particulars"], "Type": "Liability", "Amount": r["Amount"]} for r in liabilities_data]
                            )
                            show_report_preview(
                                balance_preview_df,
                                "BALANCE SHEET",
                                f"As on {format_date(report_from_date)} To {format_date(report_to_date)}",
                                "balance_sheet_report"
                            )

                            st.download_button(
                                "⬇️ Download Balance Sheet (Excel)",
                                data=final_buffer.getvalue(),
                                file_name=f"BalanceSheet_{report_from_str.replace('/', '-')}_to_{report_to_str.replace('/', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_balance_sheet"
                            )
                        else:
                            st.info("No data available to generate Balance Sheet.")
    
    elif financial_report == "Consumable / CF Report":
        st.subheader("🧰 Consumable / CF Report")
        r1, r2, r3 = st.columns([1,1,1.5])
        from_date, from_date_str = get_date_input("From Date", "cf_report_from")
        to_date, to_date_str = get_date_input("To Date", "cf_report_to")
        cf_items = get_consumable_cf_item_options(conn)
        selected_item = r3.selectbox("Item List", ["All Items"] + cf_items, key="cf_report_item")
        if st.button("Generate Consumable / CF Report", key="cf_report_generate"):
            clauses=[]; params=[]
            if from_date_str: clauses.append("entry_date>=?"); params.append(from_date_str)
            if to_date_str: clauses.append("entry_date<=?"); params.append(to_date_str)
            if selected_item != "All Items": clauses.append("item_name=?"); params.append(selected_item)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            q="SELECT entry_date,item_name,in_out,quantity,remarks FROM consumable_cf_entries"+where+" ORDER BY entry_date,id"
            df=pd.read_sql_query(q, conn, params=params)
            if df.empty:
                st.info("No data available for selected filters.")
            else:
                rows=[]; balances={}
                for _,r in df.iterrows():
                    item=r['item_name']; qty=float(r['quantity'] or 0)
                    balances[item]=balances.get(item,0)+(qty if str(r['in_out']).lower()=='in' else -qty)
                    rows.append([r['entry_date'], item, qty if str(r['in_out']).lower()=='in' else 0, qty if str(r['in_out']).lower()=='out' else 0, balances[item], r['remarks']])
                out=pd.DataFrame(rows, columns=['Date','Item Name','In','Out','Closing Stock','Remarks'])
                st.dataframe(out, use_container_width=True, hide_index=True)
                show_report_preview(
                    out,
                    "CONSUMABLE / CF REPORT",
                    f"From {format_date(from_date)} To {format_date(to_date)}",
                    "financial_consumable_cf_report"
                )

    elif financial_report == "HR Module Report":
        st.info("HR Module Report is reserved here. HR entry/report fields will appear after the HR data structure is specified.")
    
    conn.close()
