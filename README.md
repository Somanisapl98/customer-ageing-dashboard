# Customer Ageing Dashboard

A clean, standalone dashboard project built from the three supplied Excel workbooks. It is separate from every other dashboard project.

## Included files
- `index.html`, `styles.css`, `app.js`: dashboard website
- `data/dashboard-data.json`: ready-to-use data generated from the supplied ageing and master files
- `input/`: original Excel source files
- `scripts/update_data.py`: rebuilds the JSON after replacing the Excel files
- `start_dashboard.cmd`: starts the local dashboard

## Run on Windows
1. Extract the ZIP.
2. Double-click `start_dashboard.cmd`.
3. Open `http://localhost:8000` if it does not open automatically.

## Update with a new daily ageing file
Fast option: open the dashboard and click **Upload latest Excel**. This updates the current browser session.

Permanent option:
1. Replace `input/Customer Aging Analyses Bill To Bill.xlsx`.
2. Run `python scripts\update_data.py`.
3. Refresh the dashboard.

## GitHub Pages
Upload all extracted files to the repository root, commit, and enable GitHub Pages from the main branch/root folder.

## Current logic
- Party matching key: party code
- Party codes are normalized by removing hyphens and spaces when joining with Customer Master
- Ageing slabs: 0-30, 31-60, 61-90, 91-120, 121-180, 180+
- Priority: Good (0-60), Watch (61-90), Need Work (91-180), Critical (180+)
- Negative outstanding values remain included because they may represent credits/returns
