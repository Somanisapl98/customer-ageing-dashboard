from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json
import re
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input"
DATA = ROOT / "data"
LOGS = ROOT / "logs"
AGING_FILE = INPUT / "Customer Aging Analyses Bill To Bill.xlsx"
MASTER_FILE = INPUT / "Customer Master.xlsx"
OUTPUT = DATA / "dashboard-data.json"

DATA.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)


def clean_text(value):
    return "" if value is None else str(value).strip()


def normalize_heading(value):
    return re.sub(r"[^a-z0-9]", "", clean_text(value).lower())


def normalize_code(value):
    return re.sub(r"[^A-Z0-9]", "", clean_text(value).upper())


def to_number(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value).replace("₹", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return None


def find_header(ws, required_alias_groups, max_rows=50):
    for row_number in range(1, min(ws.max_row, max_rows) + 1):
        headings = {normalize_heading(ws.cell(row_number, col).value): col for col in range(1, ws.max_column + 1)}
        if all(any(normalize_heading(alias) in headings for alias in aliases) for aliases in required_alias_groups):
            return row_number, headings
    return None, {}


def find_col(headings, *aliases):
    for alias in aliases:
        key = normalize_heading(alias)
        if key in headings:
            return headings[key]
    return None


def read_customer_master():
    if not MASTER_FILE.exists():
        print("WARNING: Customer Master.xlsx not found. Continuing with Aging data only.")
        return {}

    wb = load_workbook(MASTER_FILE, read_only=False, data_only=True)
    ws = wb.active
    header_row, headings = find_header(ws, [
        ("Code", "Customer Code"),
        ("Customer", "Customer Name"),
        ("Sales Executive", "Salesman"),
    ])
    if not header_row:
        raise ValueError("Could not locate Customer Master headers: Code, Customer and Sales Executive")

    c_sales = find_col(headings, "Sales Executive", "Salesman")
    c_code = find_col(headings, "Code", "Customer Code")
    c_customer = find_col(headings, "Customer", "Customer Name")
    c_contact = find_col(headings, "Contact_Person", "Contact Person")
    c_days = find_col(headings, "Cr Days", "Credit Days")
    c_limit = find_col(headings, "Cr_Limit", "Credit Limit")
    c_used = find_col(headings, "Used_Cr_Limit", "Used Credit Limit")
    c_remaining = find_col(headings, "Rem_Cr_Limit", "Remaining Credit Limit")
    c_gst = find_col(headings, "GST Category")

    master = {}
    for row in range(header_row + 1, ws.max_row + 1):
        code = clean_text(ws.cell(row, c_code).value)
        customer = clean_text(ws.cell(row, c_customer).value)
        if not code or not customer:
            continue
        master[normalize_code(code)] = {
            "Code": code,
            "Customer": customer,
            "Salesman": clean_text(ws.cell(row, c_sales).value),
            "ContactPerson": clean_text(ws.cell(row, c_contact).value) if c_contact else "",
            "CreditDays": int(to_number(ws.cell(row, c_days).value) or 0) if c_days else 0,
            "CreditLimit": to_number(ws.cell(row, c_limit).value) or 0,
            "UsedCredit": to_number(ws.cell(row, c_used).value) or 0,
            "RemainingCredit": to_number(ws.cell(row, c_remaining).value) or 0,
            "GSTCategory": clean_text(ws.cell(row, c_gst).value) if c_gst else "",
        }
    wb.close()
    print(f"Loaded {len(master)} customers from Customer Master")
    return master


def read_grouped_aging(master):
    if not AGING_FILE.exists():
        raise FileNotFoundError(f"Missing report: {AGING_FILE}")

    wb = load_workbook(AGING_FILE, read_only=False, data_only=True)
    ws = wb.active

    # This AlignBooks export intentionally has no Customer column in the detail header.
    # Customer names appear in separate rows such as: Customer: A S SPARES RAIPUR
    header_row, headings = find_header(ws, [
        ("party_code", "Party Code"),
        ("Outstanding_Amt", "Outstanding Amount"),
        ("Days", "Ageing Days"),
    ])
    if not header_row:
        raise ValueError("Could not locate Aging detail headers: party_code, Outstanding_Amt and Days")

    c_branch = find_col(headings, "Branch")
    c_bill = find_col(headings, "Bill No", "Invoice No")
    c_code = find_col(headings, "party_code", "Party Code")
    c_outstanding = find_col(headings, "Outstanding_Amt", "Outstanding Amount")
    c_days = find_col(headings, "Days", "Ageing Days")
    c_salesman = find_col(headings, "salesman_name", "Salesman")

    grouped = defaultdict(lambda: {
        "Code": "", "Customer": "", "Outstanding": 0.0, "AgeingDays": 0,
        "OpenBills": 0, "Salesman": "", "Branch": ""
    })
    current_customer = ""

    for row in range(header_row + 1, ws.max_row + 1):
        first_cell = clean_text(ws.cell(row, 1).value)
        if first_cell.lower().startswith("customer:"):
            current_customer = first_cell.split(":", 1)[1].strip()
            continue

        code = clean_text(ws.cell(row, c_code).value)
        outstanding = to_number(ws.cell(row, c_outstanding).value)
        days = to_number(ws.cell(row, c_days).value)
        bill = clean_text(ws.cell(row, c_bill).value) if c_bill else ""

        # Skip subtotal rows and blank rows.
        if not code or outstanding is None or days is None or not bill:
            continue
        # Include both debit and credit/negative outstanding lines.
        # This is required to reconcile exactly to the AlignBooks grand total.
        key = normalize_code(code)
        master_row = master.get(key, {})
        record = grouped[key]
        record["Code"] = code
        record["Customer"] = current_customer or master_row.get("Customer", code)
        record["Outstanding"] += outstanding
        record["AgeingDays"] = max(record["AgeingDays"], int(days))
        record["OpenBills"] += 1
        record["Salesman"] = clean_text(ws.cell(row, c_salesman).value) if c_salesman else master_row.get("Salesman", "")
        record["Branch"] = clean_text(ws.cell(row, c_branch).value) if c_branch else ""

    wb.close()

    customers = []
    for key, record in grouped.items():
        master_row = master.get(key, {})
        days = record["AgeingDays"]
        record["Outstanding"] = round(record["Outstanding"], 2)
        record["Salesman"] = record["Salesman"] or master_row.get("Salesman", "")
        record["AgeingBand"] = "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
        record["ContactPerson"] = master_row.get("ContactPerson", "")
        record["CreditDays"] = master_row.get("CreditDays", 0)
        record["CreditLimit"] = master_row.get("CreditLimit", 0)
        record["UsedCredit"] = master_row.get("UsedCredit", 0)
        record["RemainingCredit"] = master_row.get("RemainingCredit", 0)
        record["GSTCategory"] = master_row.get("GSTCategory", "")
        record["Mobile"] = ""  # WhatsApp intentionally ignored for now.
        customers.append(record)

    customers.sort(key=lambda item: item["Customer"].casefold())
    return customers


def main():
    master = read_customer_master()
    customers = read_grouped_aging(master)
    payload = {
        "updatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "summary": {
            "customers": len(customers),
            "outstanding": round(sum(item["Outstanding"] for item in customers), 2),
            "above30": sum(item["AgeingDays"] > 30 for item in customers),
            "above60": sum(item["AgeingDays"] > 60 for item in customers),
        },
        "customers": customers,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {OUTPUT} with {len(customers)} customers")
    print(f"Total outstanding: {payload['summary']['outstanding']:.2f}")
    print(f"Customers above 60 days: {payload['summary']['above60']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        with (LOGS / "process_ageing_error.log").open("a", encoding="utf-8") as log:
            log.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {type(exc).__name__}: {exc}\n")
        raise
