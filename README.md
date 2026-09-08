# SUBH PAPER COMPANY - ERP (Modular)

Streamlit-based ERP for Subh Paper Company. The app was **modularized** so that every
top-level tab lives in its own `page_*.py` file — future updates to one module never
delete or break the code of another.

## Structure

| File | Role |
|------|------|
| `app_web_final_updated2.py` | Main entry point. Configures the page, CSS/JS, login gate, sidebar, and routes to one of 8 tab modules. |
| `shared_helpers.py` | Shared helpers, constants, and DB access used by every module. |
| `page_company_portal.py` | Company create / update / select portal. |
| `page_main_hub.py` | Central workspace hub that navigates to every module. |
| `page_master.py` | Inventory & Accounting master groups. |
| `page_dashboard.py` | Real-time executive dashboard. |
| `page_entry.py` | Financial Entry (Payment / Receipt / Contra / Sale / Purchase / JV / All). |
| `page_financial.py` | Ledgers, cash/bank books and financial reports. |
| `page_production.py` | Production, PO, despatch and consumable reports. |
| `page_hr.py` | Employee master, attendance, wages and payroll. |

## How the routing works

`app_web_final_updated2.py` holds one `current_page` value in
`st.session_state` and dispatch a simple `if/elif` chain, each branch importing and
calling `page_xxx.render()`. Only this file decides which tab renders.

## Run

```bash
pip install -r requirements.txt
streamlit run app_web_final_updated2.py --server.port 8510
```

Log in with `admin` / `subh123`.

### Fresh clone (no database)

The database (`subh_paper_erp.db`) is intentionally **not** committed — it holds live
business data and is excluded via `.gitignore`. On a fresh clone the app **auto-creates**
the schema and default ledger groups on first run, but it starts **empty** (no company
data). To run with your real data, copy `subh_paper_erp.db` from the working machine
beside the scripts.

### Notes

- Always start Streamlit **from the repo folder** so the relative DB path resolves.
- On another machine on the same LAN: `streamlit run app_web_final_updated2.py --server.port 8510 --server.address 0.0.0.0` and open `http://<that-ip>:8510`.
