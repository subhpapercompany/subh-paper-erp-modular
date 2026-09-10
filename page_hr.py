# ==============================================================================
# PAGE MODULE: HR MODULE
# ==============================================================================
# Employee master, attendance, wages and payroll.
# Isolated tab module. Editing this file never touches other tabs.
# ==============================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from shared_helpers import *
def render():
    st.markdown("<h2 class='section-header'>👥 HR Module</h2>", unsafe_allow_html=True)
    render_financial_year_control()

    hr_conn = get_db_connection(private=True)

    # Employee Master schema
    hr_conn.execute("""
        CREATE TABLE IF NOT EXISTS hr_employee_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            daily_wage REAL,
            ot_rate REAL,
            basic_salary REAL DEFAULT 0,
            conveyance REAL DEFAULT 0,
            mobile_no TEXT,
            aadhaar_no TEXT,
            bank_account TEXT,
            ifsc_code TEXT,
            bank_name TEXT,
            address TEXT,
            date_of_joining TEXT,
            attachment_name TEXT,
            attachment_path TEXT,
            advance_balance REAL DEFAULT 0,
            pf_percent REAL DEFAULT 0,
            esi_percent REAL DEFAULT 0,
            professional_tax REAL DEFAULT 0,
            is_outside_india INTEGER DEFAULT 0
        )
    """)
    
    existing_hr_columns = {
        row[1] for row in hr_conn.execute(
            "PRAGMA table_info(hr_employee_master)"
        ).fetchall()
    }
    hr_new_columns = {
        "category": "TEXT",
        "basic_salary": "REAL DEFAULT 0",
        "conveyance": "REAL DEFAULT 0",
        "mobile_no": "TEXT",
        "aadhaar_no": "TEXT",
        "bank_account": "TEXT",
        "ifsc_code": "TEXT",
        "bank_name": "TEXT",
        "address": "TEXT",
        "date_of_joining": "TEXT",
        "attachment_name": "TEXT",
        "attachment_path": "TEXT",
        "pf_percent": "REAL DEFAULT 0",
        "esi_percent": "REAL DEFAULT 0",
        "professional_tax": "REAL DEFAULT 0",
        "is_outside_india": "INTEGER DEFAULT 0",
    }
    for col, col_type in hr_new_columns.items():
        if col not in existing_hr_columns:
            hr_conn.execute(
                f"ALTER TABLE hr_employee_master ADD COLUMN {col} {col_type}"
            )

    # Attendance table
    hr_conn.execute("""
        CREATE TABLE IF NOT EXISTS hr_daily_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_date TEXT NOT NULL,
            emp_id TEXT NOT NULL,
            employee_name TEXT,
            shift_status TEXT,
            duty_type TEXT,
            overtime REAL DEFAULT 0,
            UNIQUE(attendance_date, emp_id, shift_status)
        )
    """)
    
    attendance_columns = {
        row[1] for row in hr_conn.execute(
            "PRAGMA table_info(hr_daily_attendance)"
        ).fetchall()
    }
    attendance_new_columns = {
        "employee_name": "TEXT",
        "shift_status": "TEXT",
        "duty_type": "TEXT",
        "overtime": "REAL DEFAULT 0",
    }
    for col, col_type in attendance_new_columns.items():
        if col not in attendance_columns:
            hr_conn.execute(
                f"ALTER TABLE hr_daily_attendance ADD COLUMN {col} {col_type}"
            )
    hr_conn.commit()

    HR_CATEGORY_OPTIONS = ["Wages", "Payroll"]

    # -------------------- HR MAIN MODES --------------------
    hr_entry_mode, hr_reporting_mode = st.tabs([
        "1. Entry Mode",
        "2. Reporting Mode"
    ])

    # ==========================================================================
    # 1. ENTRY MODE
    # ==========================================================================
    with hr_entry_mode:
        employee_master_tab, daily_attendance_tab = st.tabs([
            "1. Employee Master",
            "2. Daily Attendance"
        ])

        # ----------------------------------------------------------------------
        # 1. Employee Master
        # ----------------------------------------------------------------------
        with employee_master_tab:
            st.markdown("### Add / Edit Employee Details")

            if st.session_state.pop("hr_employee_form_reset", False):
                st.session_state["hr_employee_form_version"] = (
                    st.session_state.get("hr_employee_form_version", 0) + 1
                )

            hr_form_version = st.session_state.get("hr_employee_form_version", 0)
            hr_key = lambda name: f"hr_{name}_{hr_form_version}"

            _pending_edit = st.session_state.pop("hr_emp_edit_pending", None)
            if _pending_edit:
                st.session_state["hr_emp_edit_id"] = _pending_edit.get("id")
                _emp_edit_map = {
                    "emp_id": "emp_id", "emp_name": "name", "category": "category",
                    "daily_wage": "daily_wage", "ot_rate": "ot_rate",
                    "basic_salary": "basic_salary", "conveyance": "conveyance",
                    "pf_percent": "pf_percent", "esi_percent": "esi_percent",
                    "professional_tax": "professional_tax", "mobile_no": "mobile_no",
                    "aadhaar_no": "aadhaar_no", "bank_account": "bank_account",
                    "ifsc_code": "ifsc_code", "bank_name": "bank_name",
                    "address": "address", "date_of_joining": "date_of_joining",
                }
                _txt_fields = {"emp_id", "emp_name", "mobile_no", "aadhaar_no",
                               "bank_account", "ifsc_code", "bank_name", "address"}
                for _fk, _pk in _emp_edit_map.items():
                    _val = _pending_edit.get(_pk)
                    if _fk == "date_of_joining":
                        st.session_state[hr_key(_fk)] = parse_date_input(_val) if _val else None
                    elif _fk == "category":
                        st.session_state[hr_key(_fk)] = _val if _val in HR_CATEGORY_OPTIONS else None
                    else:
                        if _fk in _txt_fields and _val is None:
                            _val = ""
                        st.session_state[hr_key(_fk)] = _val

            e1, e2, e3, e4, e5 = st.columns([1.0, 1.7, 1.15, 1.25, 1.25])

            with e1:
                emp_id = st.text_input("EMP ID", key=hr_key("emp_id"))

            with e2:
                emp_name = st.text_input("Name", key=hr_key("emp_name"))

            with e3:
                emp_category = st.selectbox(
                    "Category",
                    HR_CATEGORY_OPTIONS,
                    index=None,
                    placeholder="Select Category",
                    key=hr_key("category")
                )

            with e4:
                daily_wage = st.number_input(
                    "Daily Wages (Rs.)",
                    min_value=0.0,
                    step=0.01,
                    key=hr_key("daily_wage"),
                   
                )

            with e5:
                ot_rate = st.number_input(
                    "OT Rate (Rs.)",
                    min_value=0.0,
                    step=0.01,
                    key=hr_key("ot_rate"),
                   
                )

            e6, e7, e8, e9 = st.columns([1.3, 1.3, 1.0, 1.0])

            with e6:
                basic_salary = st.number_input(
                    "Basic Salary (Rs.)",
                    min_value=0.0,
                    step=0.01,
                    key=hr_key("basic_salary"),
                   
                )

            with e7:
                conveyance = st.number_input(
                    "Conveyance (Rs.)",
                    min_value=0.0,
                    step=0.01,
                    key=hr_key("conveyance"),
                   
                )

            with e8:
                pf_percent = st.number_input(
                    "PF %",
                    min_value=0.0,
                    step=0.1,
                    key=hr_key("pf_percent"),
                   
                )

            with e9:
                esi_percent = st.number_input(
                    "ESI %",
                    min_value=0.0,
                    step=0.1,
                    key=hr_key("esi_percent"),
                   
                )

            e10, e11, e12 = st.columns([1.0, 1.5, 1.5])

            with e10:
                professional_tax = st.number_input(
                    "Professional Tax (Rs.)",
                    min_value=0.0,
                    step=0.01,
                    key=hr_key("professional_tax"),
                   
                )

            with e11:
                mobile_no = st.text_input(
                    "Mobile No.",
                    key=hr_key("mobile_no")
                )

            with e12:
                aadhaar_no = st.text_input(
                    "Aadhaar No.",
                    key=hr_key("aadhaar_no")
                )

            e13, e14, e15, e16 = st.columns([1.35, 1.0, 1.15, 1.7])

            with e13:
                bank_account = st.text_input(
                    "Bank Account",
                    key=hr_key("bank_account")
                )

            with e14:
                ifsc_code = st.text_input(
                    "IFSC Code",
                    key=hr_key("ifsc_code")
                )

            with e15:
                bank_name = st.text_input(
                    "Bank Name",
                    key=hr_key("bank_name")
                )

            with e16:
                address = st.text_input(
                    "Address",
                    key=hr_key("address")
                )

            e17, e18, e19 = st.columns([1.0, 1.5, 1.0])

            with e17:
                date_of_joining, doj_str = get_date_input(
                    "Date of Joining (DD/MM/YYYY)",
                    hr_key("date_of_joining"),
                    default_value=None
                )

            with e18:
                employee_attachment = st.file_uploader(
                    "ID Proof Attachment",
                    type=["pdf", "jpg", "jpeg", "png"],
                    key=hr_key("employee_attachment"),
                    help="Attach Aadhaar Card / ID Proof / other employee document."
                )

            with e19:
                st.write("")
                st.write("")
                _hr_edit_id = st.session_state.get("hr_emp_edit_id")
                _emp_id_val = str(emp_id).strip() if emp_id is not None else ""
                _emp_name_val = str(emp_name).strip() if emp_name is not None else ""
                if st.button(
                    "Update Employee" if _hr_edit_id else "Save Employee",
                    key=hr_key("save_employee"),
                    type="primary",
                    use_container_width=True
                ):
                    if not _emp_id_val or not _emp_name_val:
                        st.error("EMP ID and Name are required.")
                    elif not emp_category:
                        st.error("Please select Category: Wages or Payroll.")
                    else:
                        existing = hr_conn.execute(
                            "SELECT id, name FROM hr_employee_master WHERE emp_id = ? AND id != ?",
                            (_emp_id_val, int(_hr_edit_id) if _hr_edit_id else -1)
                        ).fetchone()

                        if existing:
                            st.error(
                                f"Duplicate Employee Code: EMP ID '{_emp_id_val}' "
                                f"already exists for '{existing[1]}'. "
                                "Please use a unique EMP ID."
                            )
                        else:
                            attachment_name = None
                            attachment_path = None
                            _old_attachment = (None, None)
                            if _hr_edit_id:
                                _old_attachment = hr_conn.execute(
                                    "SELECT attachment_name, attachment_path FROM hr_employee_master WHERE id=?",
                                    (int(_hr_edit_id),)
                                ).fetchone() or (None, None)

                            if employee_attachment is not None:
                                upload_root = Path("hr_employee_attachments")
                                upload_root.mkdir(parents=True, exist_ok=True)

                                safe_emp_id = re.sub(
                                    r"[^A-Za-z0-9_-]+", "_", _emp_id_val
                                ).strip("_") or "employee"

                                employee_folder = upload_root / safe_emp_id
                                employee_folder.mkdir(parents=True, exist_ok=True)

                                original_name = Path(employee_attachment.name).name
                                safe_name = re.sub(
                                    r"[^A-Za-z0-9._-]+", "_", original_name
                                )
                                attachment_file = employee_folder / safe_name

                                with open(attachment_file, "wb") as f:
                                    f.write(employee_attachment.getbuffer())

                                attachment_name = safe_name
                                attachment_path = str(attachment_file)

                            if _hr_edit_id:
                                hr_conn.execute(
                                    """UPDATE hr_employee_master SET
                                       emp_id=?, name=?, category=?, daily_wage=?, ot_rate=?,
                                       basic_salary=?, conveyance=?, mobile_no=?,
                                       aadhaar_no=?, bank_account=?, ifsc_code=?,
                                       bank_name=?, address=?, date_of_joining=?,
                                       attachment_name=?, attachment_path=?,
                                       pf_percent=?, esi_percent=?, professional_tax=?
                                       WHERE id=?""",
                                    (
                                        _emp_id_val,
                                        _emp_name_val,
                                        emp_category,
                                        float(daily_wage),
                                        float(ot_rate),
                                        float(basic_salary),
                                        float(conveyance),
                                        mobile_no.strip(),
                                        aadhaar_no.strip(),
                                        bank_account.strip(),
                                        ifsc_code.strip().upper(),
                                        bank_name.strip(),
                                        address.strip(),
                                        doj_str if date_of_joining else None,
                                        attachment_name if attachment_name else _old_attachment[0],
                                        attachment_path if attachment_path else _old_attachment[1],
                                        float(pf_percent),
                                        float(esi_percent),
                                        float(professional_tax),
                                        int(_hr_edit_id)
                                    )
                                )
                                hr_conn.commit()
                                st.success("Employee details updated.")
                            else:
                                hr_conn.execute(
                                    """INSERT INTO hr_employee_master
                                       (emp_id, name, category, daily_wage, ot_rate,
                                        basic_salary, conveyance, mobile_no,
                                        aadhaar_no, bank_account, ifsc_code,
                                        bank_name, address, date_of_joining,
                                        attachment_name, attachment_path,
                                        advance_balance, pf_percent, esi_percent,
                                        professional_tax, is_outside_india)
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                                    (
                                        _emp_id_val,
                                        _emp_name_val,
                                        emp_category,
                                        float(daily_wage),
                                        float(ot_rate),
                                        float(basic_salary),
                                        float(conveyance),
                                        mobile_no.strip(),
                                        aadhaar_no.strip(),
                                        bank_account.strip(),
                                        ifsc_code.strip().upper(),
                                        bank_name.strip(),
                                        address.strip(),
                                        doj_str if date_of_joining else None,
                                        attachment_name,
                                        attachment_path,
                                        float(pf_percent),
                                        float(esi_percent),
                                        float(professional_tax),
                                        0  # is_outside_india = 0 by default
                                    )
                                )
                                hr_conn.commit()
                                st.success("Employee details saved.")
                            st.session_state.pop("hr_emp_edit_id", None)
                            st.session_state.pop("hr_emp_edit_pending", None)
                            for _k in list(st.session_state.keys()):
                                if _k.startswith("hr_"):
                                    del st.session_state[_k]
                            st.session_state["hr_employee_form_reset"] = True
                            st.rerun()

            # ---- COMPACT EDIT / DELETE FOR EXISTING EMPLOYEES ----
            st.markdown("#### Manage Existing Employees")
            _emp_common = hr_conn.execute(
                "SELECT id, emp_id, name FROM hr_employee_master ORDER BY id"
            ).fetchall()
            if _emp_common:
                _cur_edit_id = st.session_state.get("hr_emp_edit_id")
                if _cur_edit_id:
                    _erow = hr_conn.execute(
                        "SELECT emp_id, name FROM hr_employee_master WHERE id=?",
                        (int(_cur_edit_id),)
                    ).fetchone()
                    if _erow:
                        st.info(f"✏️ Editing EMP: {_erow[0]} — {_erow[1]}  (Save karne par update hoga)")
                _emp_opts = {f"{r[1]} — {r[2]}": r[0] for r in _emp_common}
                _pick_label = list(_emp_opts.keys())
                _act = st.columns([2.6, 0.7, 0.8], vertical_alignment="center")
                with _act[0]:
                    _sel_emp = st.selectbox(
                        "Employee chunein (Edit / Delete):", _pick_label,
                        index=None, placeholder="Employee chunein...",
                        key="hr_emp_pick", label_visibility="collapsed"
                    )
                _sel_id = _emp_opts.get(_sel_emp)
                with _act[1]:
                    _emp_edit_clk = st.button("↩ Edit", key="hr_emp_edit_btn",
                                             use_container_width=True,
                                             disabled=(not _sel_id))
                with _act[2]:
                    _emp_del_clk = st.button("🗑 Delete", key="hr_emp_del_btn",
                                             use_container_width=True,
                                             disabled=(not _sel_id))
                if _emp_edit_clk and _sel_id:
                    _crow = hr_conn.execute(
                        "SELECT * FROM hr_employee_master WHERE id=?", (int(_sel_id),)
                    ).fetchone()
                    if _crow:
                        _ccols = [d[1] for d in hr_conn.execute(
                            "PRAGMA table_info(hr_employee_master)").fetchall()]
                        st.session_state["hr_emp_edit_pending"] = dict(zip(_ccols, _crow))
                        st.session_state["hr_employee_form_reset"] = True
                        st.rerun()
                _del_pending = st.session_state.get("hr_emp_del_pending")
                if _emp_del_clk and _sel_id:
                    st.session_state["hr_emp_del_pending"] = _sel_id
                    _del_pending = _sel_id
                if _del_pending:
                    _drow = hr_conn.execute(
                        "SELECT id, emp_id, name FROM hr_employee_master WHERE id=?",
                        (int(_del_pending),)
                    ).fetchone()
                    if _drow:
                        _dcols = st.columns([1.2, 0.7, 0.7], vertical_alignment="center")
                        with _dcols[0]:
                            st.warning(f"Delete {_drow[1]} — {_drow[2]} ?")
                        with _dcols[1]:
                            _del_ok = st.button("⚡ Confirm Delete", key="hr_emp_del_ok",
                                                type="primary", use_container_width=True)
                        with _dcols[2]:
                            _del_no = st.button("✖ Cancel", key="hr_emp_del_no",
                                                use_container_width=True)
                        if _del_no:
                            st.session_state.pop("hr_emp_del_pending", None)
                            st.rerun()
                        if _del_ok:
                            _dpath_row = hr_conn.execute(
                                "SELECT attachment_path FROM hr_employee_master WHERE id=?",
                                (int(_del_pending),)
                            ).fetchone()
                            if _dpath_row and _dpath_row[0]:
                                try:
                                    _dp = Path(_dpath_row[0])
                                    if _dp.exists():
                                        _dp.unlink()
                                    if _dp.parent.exists():
                                        _dp.parent.rmdir()
                                except Exception:
                                    pass
                            hr_conn.execute(
                                "DELETE FROM hr_employee_master WHERE id=?",
                                (int(_del_pending),)
                            )
                            hr_conn.commit()
                            st.session_state.pop("hr_emp_del_pending", None)
                            if st.session_state.get("hr_emp_edit_id") == _del_pending:
                                st.session_state.pop("hr_emp_edit_id", None)
                            st.rerun()
            else:
                st.caption("Abhi koi employee add nahi hua hai.")

            employee_df = pd.read_sql_query(
                """SELECT
                       emp_id AS 'EMP ID',
                       name AS 'EMPLOYEE NAME',
                       category AS 'CATEGORY',
                       daily_wage AS 'DAILY WAGES (Rs.)',
                       ot_rate AS 'OT RATE (Rs.)',
                       basic_salary AS 'BASIC SALARY (Rs.)',
                       conveyance AS 'CONVEYANCE (Rs.)',
                       pf_percent AS 'PF %',
                       esi_percent AS 'ESI %',
                       professional_tax AS 'PROFESSIONAL TAX (Rs.)',
                       mobile_no AS 'MOBILE NO.',
                       aadhaar_no AS 'AADHAAR NO.',
                       bank_account AS 'BANK ACCOUNT',
                       ifsc_code AS 'IFSC CODE',
                       bank_name AS 'BANK NAME',
                       address AS 'ADDRESS',
                       date_of_joining AS 'DATE OF JOINING',
                       attachment_name AS 'ID PROOF ATTACHMENT',
                       advance_balance AS 'ADVANCE BALANCE (Rs.)',
                       CASE WHEN is_outside_india = 1 THEN 'Yes' ELSE 'No' END AS 'OUTSIDE INDIA'
                   FROM hr_employee_master
                   ORDER BY id""",
                hr_conn
            )

            # Format date column
            if 'DATE OF JOINING' in employee_df.columns:
                employee_df['DATE OF JOINING'] = employee_df['DATE OF JOINING'].apply(format_date)

            st.dataframe(
                employee_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "DAILY WAGES (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                    "OT RATE (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                    "BASIC SALARY (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                    "CONVEYANCE (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                    "PF %": st.column_config.NumberColumn(format="%.1f"),
                    "ESI %": st.column_config.NumberColumn(format="%.1f"),
                    "PROFESSIONAL TAX (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                    "ADVANCE BALANCE (Rs.)": st.column_config.NumberColumn(format="%.2f"),
                },
            )

            st.markdown("#### Employee ID Proof / Attachment")
            attachment_emp_id = st.text_input(
                "Enter EMP ID to view attachment",
                key="hr_attachment_view_emp_id"
            ).strip()

            if attachment_emp_id:
                attachment_row = hr_conn.execute(
                    "SELECT attachment_name, attachment_path "
                    "FROM hr_employee_master WHERE emp_id = ?",
                    (attachment_emp_id,)
                ).fetchone()

                if attachment_row and attachment_row[1]:
                    attachment_file = Path(attachment_row[1])
                    if attachment_file.exists():
                        st.success(f"Attached document: {attachment_row[0]}")
                        with open(attachment_file, "rb") as f:
                            st.download_button(
                                "⬇️ Download / Open ID Proof",
                                data=f.read(),
                                file_name=attachment_row[0] or "employee_document",
                                key=f"hr_download_attachment_{attachment_emp_id}",
                            )
                    else:
                        st.warning(
                            "Attachment record exists, but the file is not available."
                        )
                else:
                    st.info("No attachment found for this EMP ID.")

        # ----------------------------------------------------------------------
        # 2. Daily Attendance
        # ----------------------------------------------------------------------
        with daily_attendance_tab:
            st.markdown("### Daily Attendance Entry")

            if st.session_state.pop("hr_attendance_form_reset", False):
                st.session_state["hr_attendance_form_version"] = (
                    st.session_state.get("hr_attendance_form_version", 0) + 1
                )
            attendance_version = st.session_state.get(
                "hr_attendance_form_version", 0
            )
            att_key = lambda name: f"hr_att_{name}_{attendance_version}"

            wages_duty_types = [
                "Full Present (P.P)",
                "Half Day (P.A)",
                "Absent (A.A)",
            ]
            payroll_duty_types = [
                "Present (P)",
                "Half Day (HD)",
                "Holiday (H)",
                "Absent (A)",
            ]

            employee_rows = hr_conn.execute(
                """SELECT emp_id, name, category
                   FROM hr_employee_master
                   ORDER BY name, emp_id"""
            ).fetchall()

            if not employee_rows:
                st.info("Please add employees in Employee Master first.")
            else:
                employee_options = [
                    f"{row[0]} - {row[1]} ({row[2]})"
                    for row in employee_rows
                ]
                employee_lookup = {
                    f"{row[0]} - {row[1]} ({row[2]})": row
                    for row in employee_rows
                }

                a1, a2, a3, a4, a5 = st.columns([1.25, 2.3, 1.25, 2.0, 1.25])

                with a1:
                    attendance_date, att_date_str = get_date_input(
                        "Date (DD/MM/YYYY)",
                        att_key("date"),
                        use_calendar=True
                    )

                with a2:
                    selected_employee = st.selectbox(
                        "Employee Name / ID",
                        employee_options,
                        index=None,
                        placeholder="Select Employee",
                        key=att_key("employee")
                    )

                selected_employee_row = (
                    employee_lookup.get(selected_employee)
                    if selected_employee else None
                )

                with a3:
                    shift_status = st.selectbox(
                        "Shift Status",
                        ["Day", "Night"],
                        index=None,
                        placeholder="Select Shift",
                        key=att_key("shift")
                    )

                with a4:
                    employee_category = (
                        selected_employee_row[2]
                        if selected_employee_row else None
                    )

                    if employee_category == "Wages":
                        duty_options = wages_duty_types
                    elif employee_category == "Payroll":
                        duty_options = payroll_duty_types
                    else:
                        duty_options = []

                    duty_type = st.selectbox(
                        "Duty Type",
                        duty_options,
                        index=None,
                        placeholder=(
                            "Select Duty Type"
                            if duty_options else
                            "Select Employee first"
                        ),
                        key=att_key("duty")
                    )

                with a5:
                    overtime = st.number_input(
                        "Overtime (Hrs.)",
                        min_value=0.0,
                        step=0.5,
                        format="%.2f",
                        key=att_key("overtime")
                    )

                if employee_category:
                    if employee_category == "Wages":
                        st.caption(
                            "Wages Category: P.P / P.A / A.A available."
                        )
                    else:
                        st.caption(
                            "Payroll Category: P / HD / H / A available."
                        )

                if st.button(
                    "Mark Attendance",
                    key=att_key("save"),
                    type="primary",
                    use_container_width=False
                ):
                    if not selected_employee_row:
                        st.error("Please select Employee Name / ID.")
                    elif not shift_status:
                        st.error("Please select Shift Status.")
                    elif not duty_type:
                        st.error("Please select Duty Type.")
                    elif attendance_date is None:
                        st.error("Please enter a valid date.")
                    else:
                        selected_emp_id, selected_emp_name, selected_category = (
                            selected_employee_row
                        )

                        valid_types = (
                            wages_duty_types
                            if selected_category == "Wages"
                            else payroll_duty_types
                        )
                        if duty_type not in valid_types:
                            st.error("Selected Duty Type is not valid for this Category.")
                        else:
                            existing_attendance = hr_conn.execute(
                                """SELECT id
                                   FROM hr_daily_attendance
                                   WHERE attendance_date=?
                                     AND emp_id=?
                                     AND shift_status=?""",
                                (
                                    att_date_str,
                                    selected_emp_id,
                                    shift_status,
                                )
                            ).fetchone()

                            if existing_attendance:
                                hr_conn.execute(
                                    """UPDATE hr_daily_attendance
                                       SET employee_name=?, duty_type=?, overtime=?
                                       WHERE id=?""",
                                    (
                                        selected_emp_name,
                                        duty_type,
                                        float(overtime or 0),
                                        existing_attendance[0],
                                    )
                                )
                                st.success("Attendance updated successfully.")
                            else:
                                hr_conn.execute(
                                    """INSERT INTO hr_daily_attendance
                                       (attendance_date, emp_id, employee_name,
                                        shift_status, duty_type, overtime)
                                       VALUES (?, ?, ?, ?, ?, ?)""",
                                    (
                                        att_date_str,
                                        selected_emp_id,
                                        selected_emp_name,
                                        shift_status,
                                        duty_type,
                                        float(overtime or 0),
                                    )
                                )
                                st.success("Attendance marked successfully.")

                            hr_conn.commit()
                            for _rk in list(st.session_state.keys()):
                                if _rk.startswith("hr_"):
                                    del st.session_state[_rk]
                            st.session_state["hr_attendance_form_reset"] = True
                            st.rerun()

                if att_date_str:
                    attendance_df = pd.read_sql_query(
                        """SELECT
                               id AS 'LOG ID',
                               attendance_date AS 'DATE',
                               emp_id AS 'EMP ID',
                               employee_name AS 'EMPLOYEE NAME',
                               shift_status AS 'SHIFT STATUS',
                               duty_type AS 'DUTY TYPE',
                               overtime AS 'OVERTIME (HRS.)'
                           FROM hr_daily_attendance
                           WHERE attendance_date=?
                           ORDER BY id DESC""",
                        hr_conn,
                        params=(att_date_str,)
                    )
                else:
                    # No date selected: do not show attendance records from other dates.
                    attendance_df = pd.DataFrame(columns=[
                        'LOG ID', 'DATE', 'EMP ID', 'EMPLOYEE NAME',
                        'SHIFT STATUS', 'DUTY TYPE', 'OVERTIME (HRS.)'
                    ])

                # Format date column
                if 'DATE' in attendance_df.columns:
                    attendance_df['DATE'] = attendance_df['DATE'].apply(format_date)

                st.markdown("#### Attendance Entries")
                attendance_df = attendance_df.reset_index(drop=True)
                attendance_df.insert(0, "SELECT", False)

                edited_attendance_df = st.data_editor(
                    attendance_df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=[
                        "LOG ID",
                        "DATE",
                        "EMP ID",
                        "EMPLOYEE NAME",
                        "SHIFT STATUS",
                        "DUTY TYPE",
                        "OVERTIME (HRS.)",
                    ],
                    column_config={
                        "SELECT": st.column_config.CheckboxColumn(
                            "Select",
                            help="Select one attendance entry to update or delete.",
                            default=False,
                        ),
                        "OVERTIME (HRS.)": st.column_config.NumberColumn(
                            "OVERTIME (HRS.)",
                            format="%.2f",
                        ),
                    },
                    key=att_key("entries"),
                )

                selected_rows = edited_attendance_df[
                    edited_attendance_df["SELECT"] == True
                ]

                u1, u2, u3 = st.columns([1.0, 1.0, 5.0])
                with u1:
                    update_entry = st.button(
                        "✏️ Update Entry",
                        key=att_key("update"),
                        use_container_width=True,
                    )
                with u2:
                    delete_entry = st.button(
                        "🗑️ Delete Entry",
                        key=att_key("delete"),
                        use_container_width=True,
                    )

                if update_entry:
                    if len(selected_rows) != 1:
                        st.error("Please select exactly one attendance entry to update.")
                    else:
                        row = selected_rows.iloc[0]
                        st.session_state["hr_attendance_edit_id"] = int(row["LOG ID"])
                        st.session_state["hr_attendance_edit_values"] = {
                            "date": str(row["DATE"]),
                            "emp_id": str(row["EMP ID"]),
                            "employee_name": str(row["EMPLOYEE NAME"]),
                            "shift_status": str(row["SHIFT STATUS"]),
                            "duty_type": str(row["DUTY TYPE"]),
                            "overtime": float(row["OVERTIME (HRS.)"] or 0),
                        }
                        st.rerun()

                if delete_entry:
                    if len(selected_rows) != 1:
                        st.error("Please select exactly one attendance entry to delete.")
                    else:
                        row = selected_rows.iloc[0]
                        st.session_state["hr_attendance_delete_id"] = int(row["LOG ID"])
                        st.rerun()

                delete_id = st.session_state.get("hr_attendance_delete_id")
                if delete_id:
                    st.warning(f"Delete attendance entry LOG ID {delete_id}?")
                    d1, d2 = st.columns([1, 1])
                    with d1:
                        if st.button(
                            "Yes, Delete",
                            key=att_key("confirm_delete"),
                            type="primary",
                            use_container_width=True,
                        ):
                            hr_conn.execute(
                                "DELETE FROM hr_daily_attendance WHERE id=?",
                                (delete_id,),
                            )
                            hr_conn.commit()
                            st.session_state.pop("hr_attendance_delete_id", None)
                            st.success("Attendance entry deleted successfully.")
                            st.rerun()
                    with d2:
                        if st.button(
                            "Cancel",
                            key=att_key("cancel_delete"),
                            use_container_width=True,
                        ):
                            st.session_state.pop("hr_attendance_delete_id", None)
                            st.rerun()

                edit_id = st.session_state.get("hr_attendance_edit_id")
                edit_values = st.session_state.get("hr_attendance_edit_values")
                if edit_id and edit_values:
                    st.markdown("#### Update Attendance Entry")

                    edit_employee_label = (
                        f"{edit_values['emp_id']} - "
                        f"{edit_values['employee_name']} "
                        f"({next((r[2] for r in employee_rows if str(r[0]) == edit_values['emp_id']), '')})"
                    )
                    edit_options = employee_options

                    e1, e2, e3, e4, e5 = st.columns(
                        [1.25, 2.3, 1.25, 2.0, 1.25]
                    )
                    with e1:
                        edit_date, edit_date_str = get_date_input(
                            "Date (DD/MM/YYYY)",
                            att_key("edit_date"),
                            default_value=edit_values["date"]
                        )
                    with e2:
                        edit_employee = st.selectbox(
                            "Employee Name / ID",
                            edit_options,
                            index=(
                                edit_options.index(edit_employee_label)
                                if edit_employee_label in edit_options else None
                            ),
                            key=att_key("edit_employee"),
                        )
                    with e3:
                        edit_shift = st.selectbox(
                            "Shift Status",
                            ["Day", "Night"],
                            index=(
                                ["Day", "Night"].index(edit_values["shift_status"])
                                if edit_values["shift_status"] in ["Day", "Night"] else None
                            ),
                            key=att_key("edit_shift"),
                        )
                    with e4:
                        edit_emp_row = employee_lookup.get(edit_employee)
                        edit_category = edit_emp_row[2] if edit_emp_row else None
                        edit_duty_options = (
                            wages_duty_types if edit_category == "Wages"
                            else payroll_duty_types if edit_category == "Payroll"
                            else []
                        )
                        edit_duty = st.selectbox(
                            "Duty Type",
                            edit_duty_options,
                            index=(
                                edit_duty_options.index(edit_values["duty_type"])
                                if edit_values["duty_type"] in edit_duty_options else None
                            ),
                            key=att_key("edit_duty"),
                        )
                    with e5:
                        edit_overtime = st.number_input(
                            "Overtime (Hrs.)",
                            min_value=0.0,
                            step=0.5,
                            format="%.2f",
                            value=edit_values["overtime"],
                            key=att_key("edit_overtime"),
                        )

                    x1, x2 = st.columns([1, 1])
                    with x1:
                        save_edit = st.button(
                            "💾 Save Update",
                            key=att_key("save_update"),
                            type="primary",
                            use_container_width=True,
                        )
                    with x2:
                        cancel_edit = st.button(
                            "Cancel",
                            key=att_key("cancel_update"),
                            use_container_width=True,
                        )

                    if save_edit:
                        if not edit_employee or not edit_shift or not edit_duty:
                            st.error("Please complete all attendance fields.")
                        elif edit_date is None:
                            st.error("Please enter a valid date.")
                        else:
                            emp_id, emp_name, emp_category = employee_lookup[edit_employee]

                            duplicate = hr_conn.execute(
                                """SELECT id FROM hr_daily_attendance
                                   WHERE attendance_date=? AND emp_id=? AND shift_status=? AND id<>?""",
                                (
                                    edit_date_str,
                                    emp_id,
                                    edit_shift,
                                    edit_id,
                                ),
                            ).fetchone()

                            if duplicate:
                                st.error(
                                    "Another attendance entry already exists for this employee, date and shift."
                                )
                            else:
                                hr_conn.execute(
                                    """UPDATE hr_daily_attendance
                                       SET attendance_date=?, emp_id=?, employee_name=?,
                                           shift_status=?, duty_type=?, overtime=?
                                       WHERE id=?""",
                                    (
                                        edit_date_str,
                                        emp_id,
                                        emp_name,
                                        edit_shift,
                                        edit_duty,
                                        float(edit_overtime or 0),
                                        edit_id,
                                    ),
                                )
                                hr_conn.commit()
                                st.session_state.pop("hr_attendance_edit_id", None)
                                st.session_state.pop("hr_attendance_edit_values", None)
                                st.success("Attendance entry updated successfully.")
                                st.rerun()

                    if cancel_edit:
                        st.session_state.pop("hr_attendance_edit_id", None)
                        st.session_state.pop("hr_attendance_edit_values", None)
                        st.rerun()

    # ==========================================================================
    # 2. REPORTING MODE
    # ==========================================================================
    with hr_reporting_mode:
        st.markdown("### HR Reporting Mode")
        
        wages_report_tab, payroll_report_tab, leave_app_tab = st.tabs([
            "💰 Wages Report",
            "📊 Payroll Report",
            "📝 Leave Application"
        ])
        
        # ----------------------------------------------------------------------
        # WAGES REPORT
        # ----------------------------------------------------------------------
        with wages_report_tab:
            st.markdown("#### WEEKLY ATTENDANCE, ADVANCE LEDGER & PAYROLL REGISTER")

            r1, r2 = st.columns([1.4, 1.4])
            with r1:
                report_from_date, report_from_date_str = get_date_input(
                    "From Date (DD/MM/YYYY)",
                    "hr_weekly_report_from_date_wages",
                    default_value=(datetime.date.today() - datetime.timedelta(days=6)).strftime('%d/%m/%Y')
                )
            
            if report_from_date:
                report_to_date = report_from_date + datetime.timedelta(days=6)
                with r2:
                    st.text_input(
                        "To Date (Auto)",
                        value=format_date(report_to_date),
                        disabled=True,
                        key="hr_weekly_report_to_date_wages"
                    )

                st.caption(
                    f"Report period: {format_date(report_from_date)} to "
                    f"{format_date(report_to_date)} — exactly 7 days"
                )

                week_dates = [
                    report_from_date + datetime.timedelta(days=i) for i in range(7)
                ]

                employee_rows = hr_conn.execute(
                    """SELECT emp_id, name, category, daily_wage, ot_rate,
                              basic_salary, conveyance, advance_balance
                       FROM hr_employee_master
                       WHERE category = ?
                       ORDER BY name, emp_id""",
                    ("Wages",)
                ).fetchall()

                attendance_lookup = {}
                attendance_by_name_lookup = {}
                attendance_rows = hr_conn.execute(
                    """SELECT attendance_date, emp_id, employee_name, shift_status, duty_type,
                              COALESCE(overtime, 0)
                       FROM hr_daily_attendance
                       WHERE attendance_date BETWEEN ? AND ?
                       ORDER BY attendance_date, id""",
                    (report_from_date_str, format_date(report_to_date))
                ).fetchall()

                ot_lookup = {}
                ot_by_name_lookup = {}

                for adate, emp_id, attendance_name, shift, duty, overtime_hours in attendance_rows:
                    adate_key = str(adate)
                    emp_id_key = str(emp_id)
                    name_key = str(attendance_name or "").strip().upper()
                    shift_key = str(shift or "")

                    exact_key = (emp_id_key, name_key, adate_key, shift_key)
                    name_key_full = (name_key, adate_key, shift_key)

                    attendance_lookup[exact_key] = str(duty or "")
                    attendance_by_name_lookup[name_key_full] = str(duty or "")

                    try:
                        ot_value = float(overtime_hours or 0)
                    except (ValueError, TypeError):
                        ot_value = 0.0

                    ot_lookup[exact_key] = ot_value
                    ot_by_name_lookup[name_key_full] = ot_value

                def _get_attendance(emp_id, employee_name, adate, shift):
                    name_key = str(employee_name or "").strip().upper()
                    exact_key = (str(emp_id), name_key, str(adate), str(shift or ""))
                    name_key_full = (name_key, str(adate), str(shift or ""))

                    if exact_key in attendance_lookup:
                        return attendance_lookup[exact_key]
                    return attendance_by_name_lookup.get(name_key_full, "")

                def _get_ot(emp_id, employee_name, adate, shift):
                    name_key = str(employee_name or "").strip().upper()
                    exact_key = (str(emp_id), name_key, str(adate), str(shift or ""))
                    name_key_full = (name_key, str(adate), str(shift or ""))

                    if exact_key in ot_lookup:
                        return ot_lookup[exact_key]
                    return ot_by_name_lookup.get(name_key_full, 0.0)

                def _attendance_halves(duty):
                    d = str(duty or "").strip().upper()
                    if d in ("FULL PRESENT (P.P)", "P.P", "PRESENT (P)", "P"):
                        return "P", "P"
                    if d in ("HALF DAY (P.A)", "P.A", "HALF DAY (HD)", "HD"):
                        return "P", "A"
                    if d in ("HOLIDAY (H)", "H"):
                        return "H", "H"
                    return "A", "A"

                def _day_credit(day_halves, night_halves):
                    all_halves = [*day_halves, *night_halves]
                    if "P" in all_halves:
                        if all_halves.count("P") >= 2:
                            return 1.0
                        return 0.5
                    if "H" in all_halves:
                        return 1.0
                    return 0.0

                report_rows = []
                for emp_id, name, category, daily_wage, ot_rate, basic_salary, conveyance, advance_balance in employee_rows:
                    daily_wage = float(daily_wage or 0)
                    ot_rate = float(ot_rate or 0)
                    old_advance = float(advance_balance or 0)
                    date_values = []
                    total_days = 0.0
                    total_ot = 0.0

                    for d in week_dates:
                        d_str = d.strftime('%d/%m/%Y')
                        day_halves = _attendance_halves(
                            _get_attendance(emp_id, name, d_str, "Day")
                        )
                        night_halves = _attendance_halves(
                            _get_attendance(emp_id, name, d_str, "Night")
                        )
                        first_half_values = [day_halves[0], night_halves[0]]
                        second_half_values = [day_halves[1], night_halves[1]]

                        first_half = (
                            "P" if "P" in first_half_values
                            else "H" if "H" in first_half_values
                            else "A"
                        )
                        second_half = (
                            "P" if "P" in second_half_values
                            else "H" if "H" in second_half_values
                            else "A"
                        )

                        date_values.extend([first_half, second_half])
                        total_days += _day_credit(day_halves, night_halves)
                        total_ot += _get_ot(emp_id, name, d_str, "Day")
                        total_ot += _get_ot(emp_id, name, d_str, "Night")

                    total_ot = round(total_ot, 2)
                    gross_wages = round(total_days * daily_wage + total_ot * ot_rate, 2)
                    prev_adjustment = 0.0
                    new_advance = 0.0
                    advance_deduction = 0.0
                    advance_balance_after = round(old_advance + new_advance - advance_deduction, 2)
                    net_pay = round(gross_wages + prev_adjustment - advance_deduction, 2)

                    cash_paid = net_pay
                    wages_due = round(net_pay - cash_paid, 2)
                    carry_forward = wages_due

                    has_present_or_half_day = "P" in date_values
                    has_overtime = total_ot > 0

                    if has_present_or_half_day or has_overtime:
                        report_rows.append([
                            emp_id, name, daily_wage, ot_rate, *date_values,
                            round(total_days, 2), round(total_ot, 2), gross_wages,
                            prev_adjustment, old_advance, new_advance, advance_deduction,
                            advance_balance_after, net_pay, cash_paid, wages_due, carry_forward
                        ])

                fixed_columns = ["Sl. No.", "Name", "Daily Wages", "OT Rate"]
                for d in week_dates:
                    fixed_columns.extend([
                        f"{format_date(d)} - 1st Half",
                        f"{format_date(d)} - 2nd Half"
                    ])
                fixed_columns.extend([
                    "Total Day", "Total OT", "Gross Wages", "Prev. Adjustment",
                    "Old Advance", "New Advance", "Advance Deduct", "Adv. Balance",
                    "Net Pay", "Cash Paid", "Wages Due", "Carry Forwards"
                ])

                display_rows = []
                for idx, row in enumerate(report_rows, 1):
                    display_rows.append([idx] + row[1:])

                if display_rows:
                    report_df = pd.DataFrame(display_rows, columns=fixed_columns)
                    st.dataframe(
                        report_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Daily Wages": st.column_config.NumberColumn(format="%.2f"),
                            "OT Rate": st.column_config.NumberColumn(format="%.2f"),
                            "Total Day": st.column_config.NumberColumn(format="%.2f"),
                            "Total OT": st.column_config.NumberColumn(format="%.2f"),
                            "Gross Wages": st.column_config.NumberColumn(format="%.2f"),
                            "Prev. Adjustment": st.column_config.NumberColumn(format="%.2f"),
                            "Old Advance": st.column_config.NumberColumn(format="%.2f"),
                            "New Advance": st.column_config.NumberColumn(format="%.2f"),
                            "Advance Deduct": st.column_config.NumberColumn(format="%.2f"),
                            "Adv. Balance": st.column_config.NumberColumn(format="%.2f"),
                            "Net Pay": st.column_config.NumberColumn(format="%.2f"),
                            "Cash Paid": st.column_config.NumberColumn(format="%.2f"),
                            "Wages Due": st.column_config.NumberColumn(format="%.2f"),
                            "Carry Forwards": st.column_config.NumberColumn(format="%.2f"),
                        }
                    )

                    # Excel Export for Wages
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        report_df.to_excel(writer, index=False, sheet_name='Weekly Report', startrow=3)
                    
                    buffer.seek(0)
                    wb = openpyxl.load_workbook(buffer)
                    ws = wb['Weekly Report']
                    
                    # Title
                    ws.merge_cells(f'A1:{get_column_letter(len(fixed_columns))}1')
                    ws['A1'] = 'WEEKLY ATTENDANCE, ADVANCE LEDGER & PAYROLL REGISTER'
                    ws['A1'].font = Font(size=14, bold=True)
                    ws['A1'].alignment = Alignment(horizontal='center')
                    
                    # Period
                    ws.merge_cells(f'A2:{get_column_letter(len(fixed_columns))}2')
                    ws['A2'] = f"From: {format_date(report_from_date)} To: {format_date(report_to_date)}"
                    ws['A2'].font = Font(size=10, italic=True)
                    ws['A2'].alignment = Alignment(horizontal='center')
                    
                    # Header
                    header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                    sub_fill = PatternFill(fill_type="solid", fgColor="244A73")
                    header_font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                    thin_side = Side(style="thin", color="A6A6A6")
                    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                    
                    for row_no in (3, 4):
                        for cell in ws[row_no]:
                            cell.fill = header_fill if row_no == 3 else sub_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                            cell.border = cell_border
                    
                    for row in ws.iter_rows(min_row=5):
                        for cell in row:
                            cell.font = Font(name="Arial", size=8)
                            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                            cell.border = cell_border
                    
                    # Column widths
                    widths = [8, 22, 12, 10] + [7] * 14 + [10, 10, 12, 14, 12, 12, 13, 13, 12, 12, 12, 14]
                    for i, width in enumerate(widths, 1):
                        ws.column_dimensions[get_column_letter(i)].width = width
                    
                    ws.row_dimensions[1].height = 24
                    ws.row_dimensions[2].height = 22
                    ws.row_dimensions[3].height = 22
                    ws.row_dimensions[4].height = 22
                    
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
                        report_df,
                        "WEEKLY ATTENDANCE, ADVANCE LEDGER & PAYROLL REGISTER",
                        f"From {format_date(report_from_date)} To {format_date(report_to_date)}",
                        "hr_weekly_wages_report"
                    )

                    st.download_button(
                        "⬇️ Download Weekly HR Report (Excel)",
                        data=final_buffer.getvalue(),
                        file_name=f"HR_Weekly_Report_{format_date(report_from_date).replace('/', '-')}_to_{format_date(report_to_date).replace('/', '-')}_wages.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_hr_weekly_report_wages_{format_date(report_from_date).replace('/', '-')}"
                    )
                else:
                    st.info("No attendance records found for the selected week.")

        # ----------------------------------------------------------------------
        # PAYROLL REPORT
        # ----------------------------------------------------------------------
        with payroll_report_tab:
            st.markdown("#### MONTHLY PAYROLL REPORT")
            st.markdown("##### Attendance Register with Salary Components")
            
            payroll_month = st.selectbox(
                "Select Payroll Month",
                get_month_year_options(),
                key="payroll_month_select"
            )
            
            try:
                month_name, year_str = payroll_month.split()
                year = int(year_str)
                month_num = datetime.datetime.strptime(month_name, "%B").month
                
                first_day = datetime.date(year, month_num, 1)
                if month_num == 12:
                    last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    last_day = datetime.date(year, month_num + 1, 1) - datetime.timedelta(days=1)
                
                days_in_month = last_day.day
                first_day_str = first_day.strftime('%d/%m/%Y')
                last_day_str = last_day.strftime('%d/%m/%Y')
            except:
                st.error("Invalid month selection")
                days_in_month = 31
                first_day = datetime.date.today().replace(day=1)
                last_day = first_day.replace(day=31)
                first_day_str = first_day.strftime('%d/%m/%Y')
                last_day_str = last_day.strftime('%d/%m/%Y')
            
            st.caption(f"Payroll Period: {format_date(first_day)} to {format_date(last_day)}")
            
            payroll_employees = hr_conn.execute("""
                SELECT 
                    emp_id, name, basic_salary, conveyance, 
                    pf_percent, esi_percent, professional_tax,
                    COALESCE(advance_balance, 0) as advance_balance,
                    COALESCE(is_outside_india, 0) as is_outside_india
                FROM hr_employee_master 
                WHERE category = 'Payroll'
                ORDER BY name
            """).fetchall()
            
            if not payroll_employees:
                st.info("No Payroll employees found. Please add employees with 'Payroll' category.")
            else:
                attendance_data = {}
                for emp in payroll_employees:
                    emp_id = emp[0]
                    attendance_data[emp_id] = {}
                    
                    for day in range(1, days_in_month + 1):
                        date_obj = datetime.date(year, month_num, day)
                        date_str = date_obj.strftime('%d/%m/%Y')
                        
                        att_row = hr_conn.execute("""
                            SELECT duty_type, overtime
                            FROM hr_daily_attendance
                            WHERE emp_id = ? AND attendance_date = ?
                            ORDER BY shift_status
                            LIMIT 1
                        """, (emp_id, date_str)).fetchone()
                        
                        if att_row:
                            duty_type = att_row[0] or ""
                            overtime = att_row[1] or 0
                            
                            if "PRESENT" in duty_type.upper() or duty_type.upper() == "P":
                                status = "P"
                            elif "HALF" in duty_type.upper() or duty_type.upper() == "HD":
                                status = "HD"
                            elif "HOLIDAY" in duty_type.upper() or duty_type.upper() == "H":
                                status = "H"
                            elif "ABSENT" in duty_type.upper() or duty_type.upper() == "A":
                                status = "A"
                            else:
                                status = duty_type
                        else:
                            # No attendance entry for this date = blank report cell.
                            # Do not treat a missing entry as Absent.
                            status = ""
                            overtime = 0
                        
                        attendance_data[emp_id][day] = {
                            "status": status,
                            "overtime": overtime
                        }
                
                report_data = []
                for emp in payroll_employees:
                    emp_id, name, basic, conveyance, pf_pct, esi_pct, ptax, advance, is_outside_india = emp
                    
                    present_days = 0
                    half_days = 0
                    holiday_days = 0
                    total_overtime = 0
                    
                    day_statuses = []
                    for day in range(1, days_in_month + 1):
                        day_info = attendance_data.get(emp_id, {}).get(day, {"status": "", "overtime": 0})
                        status = day_info["status"]
                        overtime = day_info["overtime"]
                        
                        day_statuses.append(status)
                        total_overtime += overtime
                        
                        if status == "P":
                            present_days += 1
                        elif status == "HD":
                            half_days += 1
                        elif status == "H":
                            holiday_days += 1
                    
                    basic_salary = float(basic or 0)
                    conveyance_allowance = float(conveyance or 0)
                    
                    da = basic_salary * 0.5
                    gross_salary = basic_salary + da + conveyance_allowance
                    
                    total_working_days = days_in_month
                    total_p = present_days + (half_days * 0.5) + holiday_days
                    
                    if total_working_days > 0:
                        daily_rate = gross_salary / total_working_days
                        monthly_earnings = total_p * daily_rate
                    else:
                        monthly_earnings = gross_salary
                    
                    if is_outside_india == 1:
                        pf_amount = 0.0
                        esi_amount = 0.0
                        ptax_amount = 0.0
                    else:
                        pf_amount = monthly_earnings * 0.12
                        if pf_amount > 1800:
                            pf_amount = 1800
                        
                        if basic_salary < 25000:
                            esi_amount = monthly_earnings * 0.0075
                        else:
                            esi_amount = 0.0
                        
                        if monthly_earnings <= 10000:
                            ptax_amount = 0.0
                        elif monthly_earnings <= 15000:
                            ptax_amount = 110.0
                        elif monthly_earnings <= 25000:
                            ptax_amount = 130.0
                        elif monthly_earnings <= 40000:
                            ptax_amount = 150.0
                        else:
                            ptax_amount = 200.0
                    
                    advance_deduction = float(advance or 0)
                    
                    total_deductions = pf_amount + esi_amount + ptax_amount + advance_deduction
                    net_payable = monthly_earnings - total_deductions
                    
                    row = [
                        name,
                        round(basic_salary, 2),
                        round(da, 2),
                    ] + day_statuses + [
                        round(total_p, 1),
                        round(total_overtime, 2),
                        round(monthly_earnings, 2),
                        round(pf_amount, 2),
                        round(esi_amount, 2),
                        round(ptax_amount, 2),
                        round(advance_deduction, 2),
                        round(total_deductions, 2),
                        round(net_payable, 2)
                    ]
                    report_data.append(row)
                
                columns = ["Employee Name", "Basic", "DA"] + [str(i).zfill(2) for i in range(1, days_in_month + 1)] + [
                    "Total P", "OT Hrs", "Gross Earnings", "PF", "ESI", "Prof Tax", "Advance", "Total Ded", "Net Pay"
                ]
                
                df = pd.DataFrame(report_data, columns=columns)
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Employee Name": st.column_config.TextColumn("Employee Name", width="medium"),
                        "Basic": st.column_config.NumberColumn("Basic", format="%.2f"),
                        "DA": st.column_config.NumberColumn("DA", format="%.2f"),
                        "Total P": st.column_config.NumberColumn("Total P", format="%.1f"),
                        "OT Hrs": st.column_config.NumberColumn("OT Hrs", format="%.2f"),
                        "Gross Earnings": st.column_config.NumberColumn("Gross Earnings", format="%.2f"),
                        "PF": st.column_config.NumberColumn("PF", format="%.2f"),
                        "ESI": st.column_config.NumberColumn("ESI", format="%.2f"),
                        "Prof Tax": st.column_config.NumberColumn("Prof Tax", format="%.2f"),
                        "Advance": st.column_config.NumberColumn("Advance", format="%.2f"),
                        "Total Ded": st.column_config.NumberColumn("Total Ded", format="%.2f"),
                        "Net Pay": st.column_config.NumberColumn("Net Pay", format="%.2f"),
                    }
                )
                
                # Excel Export for Payroll
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Payroll', startrow=2)
                
                buffer.seek(0)
                wb = openpyxl.load_workbook(buffer)
                ws = wb['Payroll']
                
                ws.merge_cells(f'A1:{get_column_letter(len(columns))}1')
                ws['A1'] = f'MONTHLY PAYROLL REPORT - {payroll_month}'
                ws['A1'].font = Font(size=14, bold=True)
                ws['A1'].alignment = Alignment(horizontal='center')
                
                ws.merge_cells(f'A2:{get_column_letter(len(columns))}2')
                ws['A2'] = f'Period: {format_date(first_day)} to {format_date(last_day)}'
                ws['A2'].font = Font(size=10, italic=True)
                ws['A2'].alignment = Alignment(horizontal='center')
                
                header_fill = PatternFill(fill_type="solid", fgColor="17365D")
                header_font = Font(name="Arial", size=8, bold=True, color="FFFFFF")
                thin_side = Side(style="thin", color="A6A6A6")
                cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
                
                for cell in ws[3]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = cell_border
                
                for row in ws.iter_rows(min_row=4):
                    for cell in row:
                        cell.font = Font(name="Arial", size=8)
                        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                        cell.border = cell_border
                
                for i, col in enumerate(columns, 1):
                    if i <= 3:
                        ws.column_dimensions[get_column_letter(i)].width = 20
                    elif i <= len(columns) - 9:
                        ws.column_dimensions[get_column_letter(i)].width = 4
                    else:
                        ws.column_dimensions[get_column_letter(i)].width = 12
                
                ws.row_dimensions[1].height = 28
                ws.row_dimensions[2].height = 22
                ws.row_dimensions[3].height = 32
                for idx in range(4, ws.max_row + 1):
                    ws.row_dimensions[idx].height = 20
                
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
                final_buffer.seek(0)
                
                show_report_preview(
                    df,
                    f"MONTHLY PAYROLL REPORT - {payroll_month}",
                    f"Period: {format_date(first_day)} to {format_date(last_day)}",
                    "hr_payroll_report"
                )

                st.download_button(
                    "⬇️ Download Payroll Report (Excel)",
                    data=final_buffer.getvalue(),
                    file_name=f"Payroll_Report_{payroll_month.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_payroll_report"
                )

    # ----------------------------------------------------------------------
    # LEAVE APPLICATION FORM
    # ----------------------------------------------------------------------
        with leave_app_tab:
            st.markdown("#### 📝 LEAVE APPLICATION FORM")

            company_row = hr_conn.execute(
                "SELECT company_name, address1, address2, city, pincode, phone FROM company_master ORDER BY id LIMIT 1"
            ).fetchone()
            company_name = (company_row[0] if company_row and company_row[0] else "SUBH PAPER COMPANY").upper()
            company_phone = (str(company_row[5]).strip() if company_row and company_row[5] and str(company_row[5]).strip() else "")
            company_address = ""
            if company_row:
                company_address = ", ".join(
                    str(p).strip() for p in [
                        company_row[1], company_row[2], company_row[3],
                        (company_row[4] if str(company_row[4]).strip() else "")
                    ] if p and str(p).strip()
                )

            st.caption("A4 portrait — har page par 2 blank leave applications (Original + Duplicate) print hongi. Fields haath se bhare jayenge.")

            def _leave_app_html(copy_label="ORIGINAL"):
                rules_html = "".join(
                    "<div class='rline'></div>" for _ in range(5)
                )
                return f"""<div class='leave-app'>
                <div class='band'>
                    <div class='mono'><span class='ml'>SP</span></div>
                    <div class='bhead'>
                        <div class='bname'>{company_name}</div>
                        <div class='btag'>{company_address}</div>
                    </div>
                    <div class='bmeta'>
                        <div class='bcopy'>{copy_label}</div>
                        <div class='bphone'>{('Ph: ' + company_phone) if company_phone else ''}</div>
                        <div class='bdept'>HUMAN RESOURCE DEPARTMENT</div>
                    </div>
                </div>
                <div class='title'>
                    <span class='tleft'></span>
                    <span class='tmid'>Leave Application</span>
                    <span class='tright'></span>
                </div>
                <div class='field name-field'>
                    <div class='k'>1. Name of Employee</div>
                    <div class='wline wempty'></div>
                </div>
                <div class='tri-row'>
                    <div class='item'>
                        <div class='k'>2. From Date</div>
                        <div class='wline wempty'></div>
                    </div>
                    <div class='item'>
                        <div class='k'>3. To Date</div>
                        <div class='wline wempty'></div>
                    </div>
                    <div class='item item-days'>
                        <div class='k'>4. Total Days</div>
                        <div class='wline wdays wempty'></div>
                    </div>
                </div>
                <div class='purpose'>
                    <div class='k'>5. Purpose of Leave Taken</div>
                    <div class='rules'>{rules_html}</div>
                </div>
                <div class='sign'>
                    <div class='sbl'>
                        <div class='slab'>Approval Executive</div>
                        <div class='sgap'></div>
                        <div class='sline'></div>
                        <div class='snote'>(Authorised Signatory)</div>
                    </div>
                    <div class='sc'>
                        <div class='slab'>Date</div>
                        <div class='sgap'></div>
                        <div class='sline'></div>
                    </div>
                    <div class='sbr'>
                        <div class='slab'>Signature of Employee</div>
                        <div class='sgap'></div>
                        <div class='sline'></div>
                    </div>
                </div>
                <div class='ffoot'>
                    {company_name} - This is a system generated leave application record.
                </div>
                </div>"""

            app_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<style>
    @page {{ size: A4 portrait; margin: 9mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', Arial, 'Times New Roman', sans-serif; margin: 0; color: #1a2733; }}
    .leave-app {{
        position: relative; height: 50%; display: flex; flex-direction: column;
        background: #fdfcf9; border: 1.4px solid #b9c6cf; border-radius: 7px;
        box-shadow: inset 0 0 0 2px #fff, inset 0 0 0 3px #dbe4ea;
        padding: 0 18px 10px 18px; overflow: hidden;
        page-break-after: always; margin-bottom: 2mm;
    }}
    .leave-app:last-child {{ page-break-after: auto; }}
    .band {{ display: flex; align-items: center; gap: 12px;
        background: linear-gradient(135deg, #0e3a5c 0%, #14507a 55%, #0e3a5c 100%);
        color: #fff; margin: 0 -18px 0 -18px; padding: 10px 18px; }}
    .mono {{ width: 44px; height: 44px; border-radius: 50%; border: 2px solid #e9c567;
        display: flex; align-items: center; justify-content: center; flex: none; }}
    .mono .ml {{ font-family: Georgia, serif; font-size: 17px; font-weight: 700; color: #e9c567; letter-spacing: 1px; }}
    .bhead {{ flex: 1; min-width: 0; }}
    .bname {{ font-family: Georgia, serif; font-size: 21px; font-weight: 700; letter-spacing: 2.5px; line-height: 1.1; }}
    .btag {{ font-size: 9px; opacity: .92; margin-top: 2px; letter-spacing: .3px; }}
    .bmeta {{ text-align: right; flex: none; font-size: 8.5px; line-height: 1.4; letter-spacing: .3px; }}
    .bcopy {{ display: inline-block; background: #e9c567; color: #0e3a5c; font-weight: 800;
        font-size: 8.5px; padding: 2px 10px; border-radius: 3px; letter-spacing: 1px; margin-bottom: 3px; }}
    .title {{ display: flex; align-items: center; gap: 10px; margin: 13px 0 11px 0; }}
    .tleft, .tright {{ flex: 1; height: 0; border-top: 1.5px solid #b9c6cf; }}
    .tmid {{ font-family: Georgia, serif; font-size: 16px; font-weight: 700; color: #0e3a5c;
        letter-spacing: 3.5px; text-transform: uppercase; }}
    .field {{ margin-bottom: 12px; }}
    .tri-row {{ display: flex; gap: 10px; margin-bottom: 12px; }}
    .item {{ flex: 1; }}
    .item-days {{ flex: 0 0 22%; }}
    .k {{ font-size: 10px; font-weight: 700; color: #155e86; text-transform: uppercase;
        letter-spacing: .8px; margin-bottom: 4px; }}
    .wline {{ min-height: 36px; border-bottom: 2px solid #0e3a5c; padding: 5px 8px 2px 8px;
        font-size: 13.5px; font-weight: 600; color: #0e3a5c; letter-spacing: .4px; }}
    .wempty {{ background-image: repeating-linear-gradient(to bottom, transparent 0px, transparent 27px, #c9d6e0 27px, #c9d6e0 28px); }}
    .wdays {{ font-weight: 800; text-align: center; }}
    .purpose {{ margin-bottom: 8px; }}
    .rules {{ position: relative; border: 1px solid #c4d2dc; border-radius: 4px;
        background: #fff; min-height: 132px; }}
    .rline {{ height: 26px; border-top: 1px solid #c4d2dc; margin: 0 6px; }}
    .rline:last-child {{ border-bottom: none; }}
    .rules .rline:first-of-type {{ border-color: transparent; }}
    .ptext {{ position: absolute; top: 4px; left: 10px; right: 10px; font-size: 12.5px;
        font-weight: 600; color: #0e3a5c; min-height: 20px; }}
    .sign {{ margin-top: auto; display: flex; gap: 12px; padding-top: 6px; }}
    .sbl, .sc, .sbr {{ flex: 1; text-align: center; }}
    .slab {{ font-size: 10px; font-weight: 700; color: #155e86; text-transform: uppercase; letter-spacing: .8px; }}
    .sgap {{ height: 40px; }}
    .sline {{ border-top: 2px solid #0e3a5c; }}
    .snote {{ font-size: 8px; color: #6b7a86; margin-top: 3px; font-style: italic; }}
    .ffoot {{ margin-top: 8px; border-top: 1px solid #dbe4ea; padding-top: 4px;
        font-size: 7.5px; color: #8a97a2; text-align: center; letter-spacing: .4px; }}
    @media print {{
        body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        .no-print {{ display: none !important; }}
        .sheet {{ width: 100%; }}
        .leave-app {{ height: 50%; page-break-after: always; margin: 0; box-shadow: none; }}
        .leave-app:last-child {{ page-break-after: auto; }}
    }}
    @media screen {{
        body {{ background: #dfe6ec; }}
        .sheet {{ width: 794px; height: 1123px; margin: 18px auto; background: #fdfcf9;
            padding: 20px 20px 6px 20px; border-radius: 6px;
            box-shadow: 0 8px 28px rgba(14,58,92,.35); }}
    }}
</style>
</head>
<body>
<div class='no-print' style='text-align:center; margin: 14px auto;'>
<div style='margin-bottom:8px; font-size:11px; color:#4b5a68;'>A4 portrait — har page par 2 applications (Original + Duplicate) print hongi. Form blank printed rahega, fields me haath se bhar sakte hain.</div>
<button onclick='window.print()' style='padding: 12px 30px; font-size: 15px; font-weight: bold; cursor: pointer;
    background: linear-gradient(135deg,#0e3a5c,#14507a); color:#fff; border:none; border-radius:7px;
    border-bottom:3px solid #0a2c47;'>Print Leave Application</button>
</div>
<div class='sheet'>
    {_leave_app_html("ORIGINAL")}
    {_leave_app_html("DUPLICATE")}
</div>
</body>
</html>"""

            components.html(
                app_html,
                height=820,
                scrolling=True
            )

    hr_conn.close()
