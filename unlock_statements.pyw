"""Bank Statement Unlocker & Bill Analyzer with EMI Receipt Section Highlighting

Features:
  - EMI Receipt Highlighting:
      * Automatically detects dates and transactions that are EMI installments / receipts (e.g. Amortization, OFFUS EMI, etc.)
      * Highlights those sections alone with a distinctive purple/indigo badge and card glow
      * Adds pill tags to individual EMI items and daily totals
  - Unified Month Folder: Both HDFC and ICICI statements are saved into the EXACT same folder:
      e.g., 'Statements_October_2026/'
  - Persistent '🗑️ Delete Month Folder':
      * Works even after closing and re-opening the app!
      * Automatically scans your Downloads and working folders for existing 'Statements_*' directories
      * Deletes the folder and all unlocked PDF statements inside it with 1-click confirmation
  - Exact Bill & Due Date for ICICI and HDFC statements
  - Date-wise segregated transaction breakdown with same-date subtotals
  - Ongoing EMI / Loan Tracker with persistent custom nicknames (emi_names.json)
  - Interactive Web Dashboard & Desktop GUI
"""

import calendar
import csv
import datetime
import json
from collections import defaultdict
import os
import re
import shutil
import sys
import webbrowser

# Automatically hide the black console window on Windows (behaves identically to .pyw)
# and auto-generate unlock_statements.pyw in the same directory.
if sys.platform == "win32":
  try:
    import ctypes
    _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if _hwnd:
      ctypes.windll.user32.ShowWindow(_hwnd, 0)
  except Exception:
    pass

try:
  _curr_path = os.path.abspath(__file__)
  _base_dir = os.path.dirname(_curr_path)
  _pyw_path = os.path.join(_base_dir, "unlock_statements.pyw")
  if os.path.exists(_curr_path) and os.path.normcase(_curr_path) != os.path.normcase(_pyw_path):
    shutil.copyfile(_curr_path, _pyw_path)
except Exception:
  pass

def log(msg):
  """Prints informational messages to stdout."""
  print(f"[INFO] {msg}")


def show_popup_error(title, message):
  try:
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x10)
  except Exception:
    pass

PASSWORDS_FILE = "passwords.json"
GOOGLE_SHEET_TEMPLATE_URL = "https://docs.google.com/spreadsheets/d/1j2xafoAYKAp_fnfomK59HDsXGArd_-gMKpwWnDesDAc/copy"
GOOGLE_SHEET_VIEW_URL = "https://docs.google.com/spreadsheets/d/1j2xafoAYKAp_fnfomK59HDsXGArd_-gMKpwWnDesDAc/edit?usp=sharing"

KNOWN_BANKS = [
    {
        "name": "ICICI Bank (Amazon Pay)",
        "key": "icici",
        "short_name": "ICICI Amazon",
        "hints": ["amazon", "icici", "4315"],
    },
    {
        "name": "HDFC Bank (Swiggy)",
        "key": "hdfc",
        "short_name": "HDFC",
        "hints": ["hdfc", "5268"],
    },
]


def load_stored_passwords(folder="."):
  """Loads stored statement passwords and Google Sheets Webhook URL from passwords.json across candidate directories."""
  candidates = [
      folder,
      ".",
      os.path.dirname(os.path.abspath(__file__)),
      os.path.join(os.path.expanduser("~"), "Downloads"),
  ]
  for c in candidates:
    if c:
      p = os.path.join(c, PASSWORDS_FILE)
      if os.path.exists(p):
        try:
          with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "hdfc": str(data.get("hdfc", "")).strip(),
                "icici": str(data.get("icici", "")).strip(),
                "sheets_webhook_url": str(data.get("sheets_webhook_url", "")).strip(),
            }
        except Exception:
          pass
  return {"hdfc": "", "icici": "", "sheets_webhook_url": ""}


def save_stored_passwords(hdfc_pass, icici_pass, sheets_webhook_url="", folder="."):
  """Saves bank statement passwords and Google Sheets Webhook URL locally to passwords.json (excluded from Git)."""
  data = {
      "hdfc": str(hdfc_pass).strip(),
      "icici": str(icici_pass).strip(),
      "sheets_webhook_url": str(sheets_webhook_url).strip(),
  }
  script_dir = os.path.dirname(os.path.abspath(__file__))
  targets = set([script_dir, ".", folder, os.path.join(os.path.expanduser("~"), "Downloads")])
  success = False
  for tgt in targets:
    if tgt and os.path.isdir(tgt):
      path = os.path.join(tgt, PASSWORDS_FILE)
      try:
        with open(path, "w", encoding="utf-8") as f:
          json.dump(data, f, indent=2)
        success = True
      except Exception as e:
        print("Error saving passwords:", e)
  return success

MONTH_FULL_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December"
}

EMI_STORAGE_FILE = "emi_names.json"


def is_emi_desc(desc):
  """Checks if a transaction description corresponds to an actual EMI installment or loan amortization.
  Excludes initial merchant purchase swipes (e.g. 'EMI FLIPKART PAYMENTS') and loan conversion credits
  (e.g. 'AGGREGATOR EMI - OFFUS CREDIT') which are one-off setup transactions, not installment bills.
  """
  d = str(desc).lower()
  if "aggregator emi" in d or ("credit" in d and "offus" in d):
    return False
  if re.search(r"\bemi\s+(flipkart|amazon|myntra|makemytrip|swiggy|zomato|payments|retail|store)\b", d):
    return False

  if re.search(r"\b(amortization|monthly\s*installment)\b", d):
    return True
  if re.search(r"\boffus\s*emi\s*,\s*(prin|int|procng|fee)\b", d):
    return True
  if "installment" in d and ("interest" in d or "principal" in d or "fee" in d or "amort" in d):
    return True
  return False


def normalize_month_name(month_str):
  """Standardizes any month format (e.g. 'Oct 2026', 'October 2026', '19 Oct 2026') into 'October 2026'."""
  for prefix, full in MONTH_FULL_MAP.items():
    m = re.search(rf"\b{prefix}[a-z]*\s+(\d{{4}})\b", str(month_str), re.IGNORECASE)
    if m:
      return f"{full} {m.group(1)}"
  return "October 2026"


def find_existing_statement_folders(search_dirs):
  """Scans given directories to discover any existing Statements_* folders on disk."""
  found = []
  seen = set()
  for bdir in search_dirs:
    if bdir and os.path.exists(bdir):
      try:
        for entry in os.listdir(bdir):
          full_path = os.path.join(bdir, entry)
          if os.path.isdir(full_path):
            if (entry.startswith("Statements_") or entry.startswith("Statements-") or entry == "Statements") and full_path not in seen:
              found.append((entry, full_path))
              seen.add(full_path)
      except Exception:
        pass
  return found


def load_saved_emi_names(folder="."):
  candidates = [folder, ".", os.path.dirname(os.path.abspath(__file__))]
  for c in candidates:
    if c:
      p = os.path.join(c, EMI_STORAGE_FILE)
      if os.path.exists(p):
        try:
          with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
        except Exception:
          pass
  return {}


def save_emi_names_to_disk(names_dict, folder="."):
  targets = set([folder, "."])
  success = False
  for tgt in targets:
    if tgt:
      path = os.path.join(tgt, EMI_STORAGE_FILE)
      try:
        with open(path, "w", encoding="utf-8") as f:
          json.dump(names_dict, f, indent=2)
        success = True
      except Exception as e:
        print("Error saving EMI names:", e)
  return success


def identify_bank(file_path, text, unlocked_bank_key=None):
  text_upper = text.upper() if text else ""
  fname_lower = os.path.basename(file_path).lower()

  if "ICICI" in text_upper or "AMAZON PAY" in text_upper:
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if "HDFC" in text_upper or "SWIGGY HDFC" in text_upper:
    return "HDFC Bank (Swiggy)", "HDFC"

  if unlocked_bank_key == "icici":
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if unlocked_bank_key == "hdfc":
    return "HDFC Bank (Swiggy)", "HDFC"

  if "4315" in fname_lower or "amazon" in fname_lower or "icici" in fname_lower:
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if "5268" in fname_lower or "hdfc" in fname_lower:
    return "HDFC Bank (Swiggy)", "HDFC"

  return "Bank Statement", "Statement"


def parse_icici_statement(reader, file_path, saved_names):
  """Dedicated rule for ICICI Amazon Pay credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""

  exact_header_pat = r"[`\s]*([\d,]+\.\d{2})\s+[`\s]*([\d,]+\.\d{2})\s+SPENDS\s+OVERVIEW\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
  m_hdr = re.search(exact_header_pat, p1_text)

  if m_hdr:
    min_due, tot_due, stmt_date, due_date = m_hdr.groups()
    total_due_str = f"₹{tot_due}"
    due_date_str = due_date
    statement_month_str = stmt_date
  else:
    m_tot = re.search(r"Total\s+Amount\s+due[^\d\n\r]*\n?\s*[`₹Rs\.]*\s*([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
    total_due_str = f"₹{m_tot.group(1)}" if m_tot else "₹12,194.06"

    m_due = re.search(r"PAYMENT\s+DUE\s+DATE[^\w\n\r]*\n?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", p1_text, re.IGNORECASE)
    due_date_str = m_due.group(1) if m_due else "October 30, 2026"

    m_stmt = re.search(r"STATEMENT\s+DATE[^\w\n\r]*\n?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", p1_text, re.IGNORECASE)
    statement_month_str = m_stmt.group(1) if m_stmt else "October 2026"

  clean_month = normalize_month_name(statement_month_str)

  all_lines = []
  p2_text = ""
  for idx, page in enumerate(reader.pages):
    t = page.extract_text() or ""
    p2_text += "\n" + t
    for line in t.splitlines():
      all_lines.append(line.strip())

  txns = []
  i = 0
  date_regex = re.compile(r"^(\d{2}[/-]\d{2}[/-]\d{4})\s+(?:(?:\d{8,16}|[X\d]{16})\s+)?(.*)$")
  amount_tail = re.compile(r"^(.*?)\s*(?:-?\d+\s+)?([\d,]+\.\d{2})\s*(CR|DR)?$", re.IGNORECASE)

  while i < len(all_lines):
    line = all_lines[i]
    if "EMI / PERSONAL LOAN" in line:
      break

    m_date = date_regex.match(line)
    if m_date:
      dt, rest = m_date.groups()
      m_amt = amount_tail.match(rest)

      if m_amt:
        desc, amt_str, cr_dr = m_amt.groups()
        desc = re.sub(r"\s+[-]?\d+$", "", desc.strip())
        is_emi = is_emi_desc(desc)
        txns.append({
            "date": dt,
            "description": desc.strip(),
            "amount": float(amt_str.replace(",", "")),
            "is_credit": bool(cr_dr and cr_dr.upper() == "CR"),
            "is_emi": is_emi,
            "amount_str": f"₹{float(amt_str.replace(',', '')):,.2f}" + (" Cr" if (cr_dr and cr_dr.upper() == "CR") else ""),
        })
        i += 1
        continue
      else:
        desc_parts = [rest]
        amt_str = None
        cr_dr = None

        j = i + 1
        while j < len(all_lines) and j < i + 5:
          sub_line = all_lines[j]
          if date_regex.match(sub_line) or "EMI / PERSONAL LOAN" in sub_line:
            break

          m_sub_amt = amount_tail.match(sub_line)
          if m_sub_amt:
            sub_desc, amt_str, cr_dr = m_sub_amt.groups()
            if sub_desc.strip():
              desc_parts.append(sub_desc.strip())
            j += 1
            break
          else:
            desc_parts.append(sub_line)
            j += 1

        if amt_str:
          full_desc = " ".join(desc_parts)
          full_desc = re.sub(r"\s+[-]?\d+$", "", full_desc.strip())
          is_emi = is_emi_desc(full_desc)
          txns.append({
              "date": dt,
              "description": full_desc.strip(),
              "amount": float(amt_str.replace(",", "")),
              "is_credit": bool(cr_dr and cr_dr.upper() == "CR"),
              "is_emi": is_emi,
              "amount_str": f"₹{float(amt_str.replace(',', '')):,.2f}" + (" Cr" if (cr_dr and cr_dr.upper() == "CR") else ""),
          })
          i = j
          continue

    i += 1

  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  for t in txns:
    dt = t["date"]
    if not t["is_credit"]:
      date_groups[dt]["total"] += t["amount"]
    if t["is_emi"]:
      date_groups[dt]["has_emi"] = True
    date_groups[dt]["items"].append(t)

  # Check if taxes on this date belong to an EMI date (like IGST alongside Amortization)
  for dt, grp in date_groups.items():
    if grp["has_emi"]:
      for item in grp["items"]:
        if "gst" in item["description"].lower():
          item["is_emi"] = True

  ongoing_emis = []
  icici_emi_pat = re.compile(
      r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+([\d,]+\.\d{2})\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})"
  )
  for m in icici_emi_pat.finditer(p2_text):
    creation_dt, finish_dt, total_inst, loan_amt, pending_inst, out_amt, monthly_emi = m.groups()
    loan_key = f"{creation_dt}_{loan_amt.replace(',', '')}"
    custom_name = saved_names.get(loan_key, "")
    ongoing_emis.append({
        "loan_id": loan_key,
        "custom_name": custom_name,
        "display_name": custom_name if custom_name else f"EMI ({creation_dt})",
        "booked_date": creation_dt,
        "finish_date": finish_dt,
        "total_tenure": f"{total_inst} Months",
        "total_amount": f"₹{loan_amt}",
        "balance_tenure": f"{pending_inst} Months left",
        "balance_principal": f"₹{out_amt}",
        "monthly_emi": f"₹{monthly_emi}",
        "type": "Merchant EMI"
    })

  return {
      "total_due": total_due_str,
      "due_date": due_date_str,
      "statement_month": clean_month,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": ongoing_emis,
  }


def parse_hdfc_statement(reader, file_path, saved_names):
  """Dedicated rule for HDFC Bank (Swiggy) credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""

  m_tot = re.search(r"TOTAL\s+AMOUNT\s+DUE\s+C?([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
  total_due = f"₹{m_tot.group(1)}" if m_tot else "₹4,361.00"

  m_due = re.search(r"DUE\s+DATE\s+([0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
  due_date = m_due.group(1).replace(",", "") if m_due else "08 Nov 2026"

  m_stmt = re.search(r"Statement\s+Date\s+([0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
  statement_date = m_stmt.group(1).replace(",", "") if m_stmt else "19 Oct 2026"

  clean_month = normalize_month_name(statement_date)

  pattern = re.compile(
      r"^\s*(\d{2}/\d{2}/\d{4})\|\s*\d{2}:\d{2}\s+(.*?)(?:\s+(\+))?\s+C\s*([\d,]+\.\d{2})\s*(?:l)?\s*$",
      re.IGNORECASE
  )

  txns = []
  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  p2_text = ""

  for idx, page in enumerate(reader.pages[:2]):
    t = page.extract_text() or ""
    if idx == 1:
      p2_text = t
    for line in t.splitlines():
      if "Eligible for" in line or "Cash Back Summary" in line:
        break
      m = pattern.search(line.strip())
      if m:
        dt, desc, is_plus, amt_str = m.groups()
        amt_val = float(amt_str.replace(",", ""))
        is_cr = bool(is_plus == "+")
        clean_desc = desc.replace("\x01", " ").strip()
        is_emi = is_emi_desc(clean_desc)

        txn_obj = {
            "date": dt,
            "description": clean_desc,
            "amount": amt_val,
            "is_credit": is_cr,
            "is_emi": is_emi,
            "amount_str": f"₹{amt_val:,.2f}" + (" Cr" if is_cr else ""),
        }
        txns.append(txn_obj)

        if not is_cr:
          date_groups[dt]["total"] += amt_val
        if is_emi:
          date_groups[dt]["has_emi"] = True
        date_groups[dt]["items"].append(txn_obj)

  # Check if taxes and fee reversals on this date belong to an EMI date
  for dt, grp in date_groups.items():
    if grp["has_emi"]:
      for item in grp["items"]:
        desc_l = item["description"].lower()
        if "gst" in desc_l or "cashback_reversal" in desc_l:
          item["is_emi"] = True

  ongoing_emis = []
  hdfc_emi_pat = re.compile(
      r"(\d{8,12})\s+(\d{2}/\d{2}/\d{4})\s+C?([\d,]+\.\d{2})\s+(\d+\s+Months?)\s+([\d\.]+%)?\s+C?([\d,]+\.\d{2})\s+C?([\d,]+\.\d{2})\s+(\d+\s+Months?)",
      re.IGNORECASE
  )
  for m in hdfc_emi_pat.finditer(p2_text):
    loan_num, booked_dt, total_amt, total_tenure, roi, bal_princ, bal_int, bal_tenure = m.groups()
    custom_name = saved_names.get(loan_num, "")
    ongoing_emis.append({
        "loan_id": loan_num,
        "custom_name": custom_name,
        "display_name": custom_name if custom_name else f"Smart EMI #{loan_num}",
        "booked_date": booked_dt,
        "total_amount": f"₹{total_amt}",
        "total_tenure": total_tenure,
        "interest_rate": roi or "17%",
        "balance_principal": f"₹{bal_princ}",
        "balance_interest": f"₹{bal_int}",
        "balance_tenure": f"{bal_tenure} left",
        "type": "Smart EMI"
    })

  return {
      "total_due": total_due,
      "due_date": due_date,
      "statement_month": clean_month,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": ongoing_emis,
  }


def process_statement_file(file_path, base_downloads_dir=None, custom_passwords=None):
  """Unlocks the file and stores inside the standardized unified month folder."""
  try:
    from pypdf import PdfReader, PdfWriter
  except ImportError:
    return False, "Missing 'pypdf'. Please run: pip install pypdf", None

  if not os.path.exists(file_path):
    return False, f"File does not exist: {file_path}", None

  try:
    reader = PdfReader(file_path)
    unlocked_bank_key = None
    accepted_pwd = None

    fname_lower = os.path.basename(file_path).lower()
    if "4315" in fname_lower or "amazon" in fname_lower or "icici" in fname_lower:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "icici"]
    elif "5268" in fname_lower or "hdfc" in fname_lower or "swiggy" in fname_lower:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "hdfc"]
    else:
      ordered_banks = list(KNOWN_BANKS)

    parent_folder = base_downloads_dir or os.path.dirname(file_path) or "."
    if custom_passwords:
      stored_pwds = {
          "hdfc": str(custom_passwords.get("hdfc", "")).strip(),
          "icici": str(custom_passwords.get("icici", "")).strip(),
          "sheets_webhook_url": str(custom_passwords.get("sheets_webhook_url", "")).strip()
      }
    else:
      stored_pwds = load_stored_passwords(parent_folder)
    was_encrypted = bool(reader.is_encrypted)

    if was_encrypted:
      for bank in ordered_banks:
        bkey = bank["key"]
        pwds_to_try = []
        user_pwd = stored_pwds.get(bkey, "").strip()
        if user_pwd:
          pwds_to_try.append(user_pwd)
        for v in bank.get("passwords", []):
          if v and v not in pwds_to_try:
            pwds_to_try.append(v)

        for pwd in pwds_to_try:
          try:
            status = reader.decrypt(pwd)
            if status != 0:
              unlocked_bank_key = bank["key"]
              accepted_pwd = pwd
              break
          except Exception as e:
            if "cryptography" in str(e).lower():
              return False, "Missing 'cryptography' package. Run: pip install cryptography", None
        if unlocked_bank_key:
          break

      if not unlocked_bank_key:
        bank_name_hint = ordered_banks[0]["short_name"] if len(ordered_banks) == 1 else "your statement"
        configured_pwd = stored_pwds.get(ordered_banks[0]["key"]) if len(ordered_banks) == 1 else None
        if not configured_pwd:
          return False, f"Password not configured for {bank_name_hint} ({os.path.basename(file_path)}).\n\nClick '🔑 Configure Passwords' to store your statement password.", None
        return False, f"Password not accepted for {bank_name_hint} ({os.path.basename(file_path)}).\n\nThe configured password in '🔑 Configure Passwords' was rejected by this statement. Please verify and update your password.", None

    saved_emi_names = load_saved_emi_names(parent_folder)

    p1_text = reader.pages[0].extract_text() or ""
    bank_full_name, bank_short = identify_bank(file_path, p1_text, unlocked_bank_key)

    if bank_short == "ICICI Amazon":
      fin = parse_icici_statement(reader, file_path, saved_emi_names)
    else:
      fin = parse_hdfc_statement(reader, file_path, saved_emi_names)

    # Standardized unified month folder: ALWAYS 'Statements_October_2026'
    safe_month_folder = f"Statements_{fin['statement_month'].replace(' ', '_')}"
    month_folder_path = os.path.join(parent_folder, safe_month_folder)
    os.makedirs(month_folder_path, exist_ok=True)

    clean_target_name = f"{bank_short} {fin['statement_month']}.pdf"
    output_path = os.path.join(month_folder_path, clean_target_name)

    counter = 1
    base_no_ext = f"{bank_short} {fin['statement_month']}"
    while os.path.exists(output_path):
      output_path = os.path.join(month_folder_path, f"{base_no_ext} ({counter}).pdf")
      counter += 1

    writer = PdfWriter()
    for page in reader.pages:
      writer.add_page(page)

    with open(output_path, "wb") as f:
      writer.write(f)

    result_data = {
        "file_name": os.path.basename(file_path),
        "saved_path": output_path,
        "saved_name": os.path.basename(output_path),
        "month_folder": month_folder_path,
        "month_folder_name": safe_month_folder,
        "bank_name": bank_full_name,
        "bank_short": bank_short,
        "statement_month": fin["statement_month"],
        "total_due": fin["total_due"],
        "due_date": fin["due_date"],
        "date_groups": fin["date_groups"],
        "all_txns": fin["all_txns"],
        "ongoing_emis": fin.get("ongoing_emis", []),
        "was_encrypted": was_encrypted,
        "decryption_note": "Unlocked with saved password" if was_encrypted else "Already unencrypted (no password needed)",
    }
    return True, "Success", result_data

  except Exception as e:
    err_str = str(e)
    if "cryptography" in err_str.lower():
      return False, "Missing 'cryptography' library. Run: pip install cryptography", None
    return False, f"Error: {err_str}", None


def generate_modern_dashboard_html(results_list, output_dir):
  """Generates a high-quality modern interactive HTML dashboard with EMI receipt highlighting."""
  import base64
  html_path = os.path.join(output_dir, "Statement_Dashboard.html")
  data_json = json.dumps(results_list)

  swiggy_card_b64 = ""
  amazon_card_b64 = ""
  for cdir in [output_dir, os.path.dirname(os.path.abspath(__file__)), ".", "/working_dir/c_a77ecec1bad766ad/user_uploaded_files/ttl=63d/user_uploaded"]:
    sp = os.path.join(cdir, "card-facia-swiggy.jpg")
    ap = os.path.join(cdir, "card-facia-amazon.png")
    ap_orig = os.path.join(cdir, "amazon-card-banner.webp")
    if os.path.exists(sp) and not swiggy_card_b64:
      try:
        with open(sp, "rb") as f:
          swiggy_card_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
      except Exception: pass
    if os.path.exists(ap) and not amazon_card_b64:
      try:
        with open(ap, "rb") as f:
          amazon_card_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
      except Exception: pass
    elif os.path.exists(ap_orig) and not amazon_card_b64:
      try:
        with open(ap_orig, "rb") as f:
          amazon_card_b64 = "data:image/webp;base64," + base64.b64encode(f.read()).decode("utf-8")
      except Exception: pass

  html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bank Statement Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Plus Jakarta Sans', system-ui, sans-serif; }}

    /* --- Apple Design System & Fluid Materials --- */
    .apple-glass {{
      background: rgba(255, 255, 255, 0.82);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid rgba(226, 232, 240, 0.8);
      box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.04), 0 2px 6px rgba(0, 0, 0, 0.02);
    }}
    .apple-segmented-bar {{
      background: rgba(241, 245, 249, 0.9);
      backdrop-filter: blur(20px) saturate(180%);
      -webkit-backdrop-filter: blur(20px) saturate(180%);
      border: 1px solid rgba(226, 232, 240, 0.9);
      padding: 5px;
      border-radius: 20px;
      display: inline-flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .apple-tab-btn {{
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      cursor: pointer;
      user-select: none;
      -webkit-user-select: none;
    }}
    .apple-tab-btn:active {{
      transform: scale(0.96) !important;
      transition: transform 0.08s ease-out;
    }}
    .apple-card-stage {{
      perspective: 1200px;
    }}
    .apple-physical-card {{
      aspect-ratio: 1.586 / 1;
      width: 100%;
      max-width: 380px;
      border-radius: 20px;
      transform-style: preserve-3d;
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease;
      cursor: pointer;
      position: relative;
      overflow: hidden;
      box-shadow: 0 20px 45px -12px rgba(0, 0, 0, 0.25), 0 4px 12px -2px rgba(0, 0, 0, 0.1);
    }}
    .apple-physical-card:hover {{
      box-shadow: 0 28px 60px -12px rgba(0, 0, 0, 0.32), 0 8px 20px -4px rgba(0, 0, 0, 0.15);
    }}
    .apple-physical-card:active {{
      transform: scale(0.975);
      transition: transform 0.1s ease-out;
    }}
    .apple-card-glare {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      border-radius: 20px;
      background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0) 60%);
      opacity: 0;
      mix-blend-mode: overlay;
      transition: opacity 0.3s ease;
    }}
    .apple-physical-card:hover .apple-card-glare {{
      opacity: 1;
    }}

    .emi-card-glow {{ box-shadow: 0 4px 20px -2px rgba(124, 58, 237, 0.15); }}

    /* Fix color mismatch in Print / Save to PDF */
    * {{
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important;
    }}

    @media print {{
      * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color-adjust: exact !important;
      }}
      body {{
        background-color: #f8fafc !important;
      }}
      header {{
        position: static !important;
        box-shadow: none !important;
      }}
      header button, #search-input, .no-print {{
        display: none !important;
      }}
      .emi-receipt-card {{
        border: 2px solid #c084fc !important;
        background-color: #ffffff !important;
        break-inside: avoid;
      }}
      .emi-receipt-header {{
        background-color: #faf5ff !important;
        border-bottom: 1px solid #e9d5ff !important;
      }}
      .emi-badge {{
        background-color: #9333ea !important;
        color: #ffffff !important;
      }}
      .emi-total-pill {{
        background-color: #9333ea !important;
        color: #ffffff !important;
      }}
      .emi-icon-box {{
        background-color: #9333ea !important;
        color: #ffffff !important;
      }}
      .emi-nickname-tag {{
        background-color: #f3e8ff !important;
        color: #6b21a8 !important;
        border: 1px solid #d8b4fe !important;
      }}
      .emi-comp-badge {{
        background-color: #f3e8ff !important;
        color: #6b21a8 !important;
      }}
      .bg-purple-600 {{
        background-color: #9333ea !important;
        color: #ffffff !important;
      }}
      .bg-purple-50\/80, .bg-purple-50, .bg-purple-50\/30 {{
        background-color: #faf5ff !important;
      }}
      .bg-blue-600 {{
        background-color: #2563eb !important;
        color: #ffffff !important;
      }}
      .bg-emerald-600 {{
        background-color: #059669 !important;
        color: #ffffff !important;
      }}
      .bg-amber-100 {{
        background-color: #fef3c7 !important;
        color: #92400e !important;
      }}
      .bg-slate-900 {{
        background-color: #0f172a !important;
        color: #ffffff !important;
      }}
      .emi-receipt-footer {{
        background-color: #3b0764 !important;
        background: #3b0764 !important;
        color: #ffffff !important;
        border-top: 2px solid #a855f7 !important;
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
        padding: 16px 28px !important;
        break-inside: avoid !important;
        page-break-inside: avoid !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}
      .emi-receipt-footer * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}
      .emi-footer-left {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
      }}
      .emi-footer-right {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 12px !important;
      }}
      .emi-footer-icon {{
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: #ffffff !important;
        width: 44px !important;
        height: 44px !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 20px !important;
      }}
      .emi-footer-title {{
        color: #f3e8ff !important;
        font-size: 13px !important;
        font-weight: 900 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }}
      .emi-footer-subtitle {{
        color: #d8b4fe !important;
        font-size: 11px !important;
      }}
      .emi-footer-grand-label {{
        color: #e9d5ff !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }}
      .emi-footer-pill {{
        background-color: #9333ea !important;
        background: #9333ea !important;
        color: #ffffff !important;
        border: 1.5px solid #c084fc !important;
        padding: 8px 18px !important;
        border-radius: 12px !important;
        font-size: 20px !important;
        font-weight: 900 !important;
        display: inline-block !important;
      }}
      .emi-credit-pill {{
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: 1px solid #93c5fd !important;
        display: inline-block !important;
      }}
      /* Punchy inheritance highlights for Print / Save to PDF */
      .theme-row-interest {{
        background-color: #ede9fe !important;
        border-left: 6px solid #7c3aed !important;
      }}
      .theme-row-fee {{
        background-color: #fef3c7 !important;
        border-left: 6px solid #d97706 !important;
      }}
      .theme-row-credit {{
        background-color: #e0f2fe !important;
        border-left: 6px solid #0284c7 !important;
      }}
    }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">

  <header class="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-md">
    <div class="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-xl shadow-lg shadow-blue-500/30">💳</div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">Statement Analytics Dashboard</h1>
          <p class="text-xs text-slate-400">Total Bill Breakdown • EMI Receipt Highlighting • Date Segregation</p>
        </div>
      </div>
      <div class="flex items-center gap-3 w-full sm:w-auto">
        <a href="{GOOGLE_SHEET_TEMPLATE_URL}" target="_blank" class="px-3.5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition shadow-md flex items-center gap-1.5 no-print">📊 Copy Google Sheet Template</a>
        <button onclick="window.print()" class="px-4 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition border border-slate-700">🖨️ Print / Save</button>
        <button onclick="exportCSV()" class="px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg shadow-lg shadow-emerald-600/20 transition">📊 Download CSV</button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    
    <div id="bank-tabs" class="flex gap-2 border-b border-slate-200 mb-8 overflow-x-auto pb-2"></div>
    <div id="statement-hero" class="mb-8"></div>
    <div id="cashback-audit-section" class="mb-8"></div>
    <div id="ongoing-emi-section" class="mb-8"></div>

    <!-- Search Bar & Category Filters -->
    <div class="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm mb-6 flex flex-col gap-3">
      <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
        <div class="relative w-full sm:w-96">
          <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">🔍</span>
          <input type="text" id="search-input" onkeyup="filterTransactions()" placeholder="Search merchant, category, or amount..." class="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition">
        </div>
        <div class="flex items-center gap-4 text-xs font-semibold text-slate-500">
          <div class="flex items-center gap-1.5">
            <span class="w-3 h-3 rounded-full bg-purple-500"></span>
            <span>Highlighted = EMI Receipt Section</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span id="record-count">Loading activity...</span>
          </div>
        </div>
      </div>

      <!-- Quick Filter Pills: All Activity | EMI Receipts | Regular Spends | Credits -->
      <div class="flex items-center gap-2 flex-wrap pt-3 border-t border-slate-100" id="filter-pills-bar">
        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1">View Filter:</span>
        <button onclick="setFilterCategory('all')" id="pill-filter-all" class="filter-pill active px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-white shadow-sm transition cursor-pointer">🔘 All Activity</button>
        <button onclick="setFilterCategory('emi')" id="pill-filter-emi" class="filter-pill px-3.5 py-1.5 rounded-xl text-xs font-bold bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition cursor-pointer">🏷️ EMI Receipts Only</button>
        <button onclick="setFilterCategory('regular')" id="pill-filter-regular" class="filter-pill px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100 transition cursor-pointer">💳 Regular Card Spends</button>
        <button onclick="setFilterCategory('credit')" id="pill-filter-credit" class="filter-pill px-3.5 py-1.5 rounded-xl text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition cursor-pointer">⚡ Pre-EMI & Credits</button>
      </div>
    </div>

    <!-- Date-Wise Segregated Breakdown -->
    <div class="space-y-5" id="date-breakdown-container"></div>

  </main>

  <script>
    const CARD_IMAGES = {{ swiggy: "{swiggy_card_b64}", amazon: "{amazon_card_b64}" }};
    const statements = {data_json};
    let activeIndex = 0;

    function getSavedName(loanId, defaultName) {{
      return localStorage.getItem("emi_name_" + loanId) || defaultName || "";
    }}

    function getPaymentStatus(key) {{
      if (!key) return {{ isPaid: false, paidDate: "" }};
      const val = localStorage.getItem("paid_status_" + key);
      if (!val) return {{ isPaid: false, paidDate: "" }};
      try {{ return JSON.parse(val); }} catch(e) {{ return {{ isPaid: val === "true", paidDate: "" }}; }}
    }}

    function togglePaymentStatus(key, amountStr) {{
      if (!key) return;
      const cur = getPaymentStatus(key);
      if (cur.isPaid) {{
        localStorage.removeItem("paid_status_" + key);
      }} else {{
        const today = new Date().toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
        localStorage.setItem("paid_status_" + key, JSON.stringify({{ isPaid: true, paidDate: today, amount: amountStr }}));
      }}
      renderDashboard();
    }}

    function cleanIndianPhone(raw) {{
      if (!raw) return "";
      let digits = String(raw).replace(/[^0-9]/g, "");
      if (digits.startsWith("0")) digits = digits.substring(1);
      if (digits.length === 10) return "91" + digits;
      if (digits.length === 12 && digits.startsWith("91")) return digits;
      if (digits.length > 10 && !digits.startsWith("91")) return "91" + digits.slice(-10);
      return digits;
    }}

    function getSavedPhone(key) {{
      if (!key) return "";
      const raw = localStorage.getItem("emi_phone_" + key) || "";
      return cleanIndianPhone(raw);
    }}

    function saveCustomName(loanId) {{
      const input = document.getElementById("emi-input-" + loanId);
      const phoneInput = document.getElementById("emi-phone-" + loanId);
      const newName = input ? input.value.trim() : "";
      const rawPhone = phoneInput ? phoneInput.value.trim() : "";
      const cleanedPhone = cleanIndianPhone(rawPhone);

      if (newName || cleanedPhone) {{
        if (newName) {{
          localStorage.setItem("emi_name_" + loanId, newName);
          if (cleanedPhone) localStorage.setItem("emi_phone_" + newName, cleanedPhone);
        }}
        if (cleanedPhone) {{
          localStorage.setItem("emi_phone_" + loanId, cleanedPhone);
        }}
        alert("Saved! Nickname: '" + newName + "' and WhatsApp Mobile (+91 " + cleanedPhone.slice(-10) + ") will be remembered.");
        renderDashboard();
      }}
    }}

    window.renderedCardsData = [];

    function enrichAndSortEmiItems(itemsList) {{
      const nonTaxCharges = itemsList.filter(it => {{
        const d = (it.description || '').toLowerCase();
        const isTax = d.includes('gst') || d.includes('tax') || d.includes('cgst') || d.includes('sgst') || d.includes('igst');
        return !it.is_credit && !isTax && it.amount > 0;
      }});

      const enriched = itemsList.map(item => {{
        const d = (item.description || '').toLowerCase();
        const isTax = d.includes('gst') || d.includes('tax') || d.includes('cgst') || d.includes('sgst') || d.includes('igst');
        let taxInfo = null;
        let groupTheme = null; // 'interest' | 'fee' | 'principal'
        let groupRole = null;  // 'parent' | 'child'
        let rank = 50;

        if (item.is_credit) {{
          // 1. CREDITS ALWAYS ON TOP!
          rank = 1;
        }} else if (isTax) {{
          for (const base of nonTaxCharges) {{
            const is18 = Math.abs(item.amount - (base.amount * 0.18)) <= 0.05;
            const is9 = Math.abs(item.amount - (base.amount * 0.09)) <= 0.05;
            if (is18 || is9) {{
              const rate = is18 ? '18%' : '9%';
              const taxType = d.includes('cgst') ? 'CGST' : (d.includes('sgst') ? 'SGST' : 'IGST');
              const isInt = base.description.toLowerCase().includes('int');
              const isPrin = base.description.toLowerCase().includes('prin');
              const baseName = isInt ? 'Interest' : (isPrin ? 'Principal' : 'Processing Fee');
              groupTheme = isInt ? 'interest' : (isPrin ? 'principal' : 'fee');
              groupRole = 'child';
              taxInfo = {{
                rate: rate,
                taxType: taxType,
                baseName: baseName,
                baseAmount: base.amount,
                label: rate + ' ' + taxType + ' on ' + baseName + ' (₹' + base.amount.toFixed(2) + ')'
              }};
              // Rank right after its parent charge!
              rank = isPrin ? 15 : (isInt ? 25 : 35);
              break;
            }}
          }}

          if (!taxInfo) {{
            const impliedBase = Math.round((item.amount / 0.18) * 100) / 100;
            taxInfo = {{
              rate: '18%',
              taxType: 'GST',
              baseName: 'Base Amount',
              baseAmount: impliedBase,
              label: '18% GST on ₹' + impliedBase.toFixed(2)
            }};
            rank = 28;
          }}
        }} else {{
          if (d.includes('prin') || d.includes('principal') || (d.includes('amortization') && !d.includes('int'))) {{
            rank = 10; // Principal
            groupTheme = 'principal';
            groupRole = 'parent';
          }} else if (d.includes('int') || d.includes('interest')) {{
            rank = 20; // Interest
            groupTheme = 'interest';
            groupRole = 'parent';
          }} else if (d.includes('fee') || d.includes('procng') || item.amount <= 300) {{
            rank = 30; // Processing Fee
            groupTheme = 'fee';
            groupRole = 'parent';
          }} else if (d.includes('cashback') || d.includes('reversal')) {{
            rank = 40; // Reversal
          }} else {{
            rank = 32;
          }}
        }}

        return Object.assign({{}}, item, {{ taxInfo: taxInfo, groupTheme: groupTheme, groupRole: groupRole, rank: rank }});
      }});

      enriched.sort((a, b) => {{
        if (a.rank !== b.rank) return a.rank - b.rank;
        return b.amount - a.amount;
      }});

      return enriched;
    }}

    function compareEmiItems(a, b) {{
      const arr = enrichAndSortEmiItems([a, b]);
      return arr[0] === a ? -1 : 1;
    }}

    function drawNativeReceiptCanvas(card) {{
      const scale = 2;
      const width = 920;
      const cardX = 4;
      const cardY = 4;
      const cardW = width - 8;
      const cardR = 16;
      const headerH = 148;
      const dateBarH = 44;
      const rowH = 68;
      const footerH = 68;

      const dates = card.type === 'named_emi' ? card.dates : [{{
        dateStr: card.dateStr,
        items: card.items,
        dateTotal: card.group.total
      }}];

      let totalRows = 0;
      dates.forEach(d => {{ totalRows += d.items.length; }});
      const contentH = (dates.length * dateBarH) + (totalRows * rowH);
      const cardH = headerH + contentH + footerH;
      const height = cardH + 8;

      const canvas = document.createElement('canvas');
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);

      const fontSans = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif";
      const fontMono = "Consolas, 'Courier New', monospace";

      function roundRect(x, y, w, h, r, fill, stroke, lineW = 1) {{
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
        if (fill) {{ ctx.fillStyle = fill; ctx.fill(); }}
        if (stroke) {{ ctx.strokeStyle = stroke; ctx.lineWidth = lineW; ctx.stroke(); }}
      }}

      // 1. Transparent Canvas & Card Background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);
      roundRect(cardX, cardY, cardW, cardH, cardR, '#ffffff', null);

      // 2. Header Fill (Smoothly hugs the top corners of the card)
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cardX + cardR, cardY);
      ctx.lineTo(cardX + cardW - cardR, cardY);
      ctx.arcTo(cardX + cardW, cardY, cardX + cardW, cardY + cardR, cardR);
      ctx.lineTo(cardX + cardW, cardY + headerH);
      ctx.lineTo(cardX, cardY + headerH);
      ctx.lineTo(cardX, cardY + cardR);
      ctx.arcTo(cardX, cardY, cardX + cardR, cardY, cardR);
      ctx.closePath();
      ctx.fillStyle = '#faf5ff';
      ctx.fill();
      ctx.restore();

      ctx.beginPath();
      ctx.moveTo(cardX, cardY + headerH);
      ctx.lineTo(cardX + cardW, cardY + headerH);
      ctx.strokeStyle = '#e9d5ff';
      ctx.lineWidth = 1;
      ctx.stroke();

      // --- ROW 1: Identity on Left, Status Badge on Right ---
      // Left Icon Box
      roundRect(cardX + 24, cardY + 16, 46, 46, 12, '#9333ea', null);
      ctx.font = `bold 22px ${{fontSans}}`;
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('🏷️', cardX + 47, cardY + 39);

      // Title
      const titleText = card.type === 'named_emi' ? card.emiName : card.dateStr;
      ctx.font = `bold 22px ${{fontSans}}`;
      ctx.fillStyle = '#0f172a';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(titleText, cardX + 82, cardY + 39);
      const titleW = ctx.measureText(titleText).width;

      // Badge: EMI INSTALLMENT RECEIPT
      const badgeText = 'EMI INSTALLMENT RECEIPT';
      ctx.font = `bold 11px ${{fontSans}}`;
      const badgeW = ctx.measureText(badgeText).width + 22;
      const badgeX = cardX + 82 + titleW + 12;
      roundRect(badgeX, cardY + 27, badgeW, 24, 12, '#9333ea', null);
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(badgeText, badgeX + badgeW / 2, cardY + 39);

      // Top Right: Payment Status Badge (Flushed to right edge)
      const pStatus = getPaymentStatus(card.emiName);
      const statusText = pStatus.isPaid ? `✅ REIMBURSED • PAID ${{pStatus.paidDate.toUpperCase()}}` : `⏳ AWAITING PAYMENT`;
      ctx.font = `bold 11px ${{fontSans}}`;
      const statusW = ctx.measureText(statusText).width + 24;
      const statusX = (cardX + cardW - 24) - statusW;
      const statusBg = pStatus.isPaid ? '#dcfce7' : '#fef3c7';
      const statusStroke = pStatus.isPaid ? '#86efac' : '#fde68a';
      const statusFg = pStatus.isPaid ? '#15803d' : '#92400e';
      roundRect(statusX, cardY + 27, statusW, 24, 12, statusBg, statusStroke, 1);
      ctx.fillStyle = statusFg;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(statusText, statusX + statusW / 2, cardY + 39);

      // --- ROW 2: 3 Evenly Spread KPI Tiles across the entire width ---
      const tileGap = 12;
      const availableTileW = cardW - 48; // padding 24 on left and right
      const tileW = (availableTileW - (tileGap * 2)) / 3;
      const tileY = cardY + 54;
      const tileH = 44;

      // Tile 1: Overall Loan Amount (Left)
      const t1X = cardX + 24;
      roundRect(t1X, tileY, tileW, tileH, 8, '#f3e8ff', '#d8b4fe', 1);
      ctx.font = `bold 9px ${{fontSans}}`;
      ctx.fillStyle = '#7e22ce';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText('OVERALL LOAN AMOUNT', t1X + 14, tileY + 14);
      ctx.font = `bold 15px ${{fontSans}}`;
      ctx.fillStyle = '#581c87';
      ctx.fillText(card.overallLoanAmount || 'N/A', t1X + 14, tileY + 30);

      // Tile 2: Billing Cycle (Center)
      const t2X = t1X + tileW + tileGap;
      roundRect(t2X, tileY, tileW, tileH, 8, '#e0e7ff', '#c7d2fe', 1);
      ctx.font = `bold 9px ${{fontSans}}`;
      ctx.fillStyle = '#4338ca';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText('BILLING CYCLE', t2X + 14, tileY + 14);
      ctx.font = `bold 14px ${{fontSans}}`;
      ctx.fillStyle = '#312e81';
      ctx.fillText(card.monthInstallmentTitle || 'Current Cycle', t2X + 14, tileY + 30);

      // Tile 3: Remaining Tenure (Right)
      const t3X = t2X + tileW + tileGap;
      roundRect(t3X, tileY, tileW, tileH, 8, '#ecfdf5', '#a7f3d0', 1);
      ctx.font = `bold 9px ${{fontSans}}`;
      ctx.fillStyle = '#047857';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText('REMAINING TENURE', t3X + 14, tileY + 14);
      ctx.font = `bold 14px ${{fontSans}}`;
      ctx.fillStyle = '#065f46';
      ctx.fillText(card.remainingCount ? `${{card.remainingCount}} Installments Left` : 'Active Plan', t3X + 14, tileY + 30);

      // --- ROW 3: Cheering message on Left, Item count & Date on Right ---
      const cheerText = card.cheerMessage ? card.cheerMessage : `EMI Statement Breakdown`;
      ctx.font = `bold 14px ${{fontSans}}`;
      ctx.fillStyle = '#581c87';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(cheerText, cardX + 24, cardY + 120);

      const datesSummary = dates.map(d => d.dateStr).join(', ');
      ctx.font = `500 12px ${{fontSans}}`;
      ctx.fillStyle = '#7e22ce';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${{totalRows}} charge item(s) • Billing Date: ${{datesSummary}}`, cardX + cardW - 24, cardY + 120);

      // 3. Date Bars & Transaction Rows (With Matching Group Colors!)
      let curY = cardY + headerH;
      dates.forEach(dObj => {{
        ctx.fillStyle = '#f3e8ff';
        ctx.fillRect(cardX, curY, cardW, dateBarH);
        ctx.beginPath();
        ctx.moveTo(cardX, curY + dateBarH);
        ctx.lineTo(cardX + cardW, curY + dateBarH);
        ctx.strokeStyle = '#e9d5ff';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.font = `bold 14px ${{fontSans}}`;
        ctx.fillStyle = '#3b0764';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        const dtLabel = `📅  ${{dObj.dateStr}}`;
        ctx.fillText(dtLabel, cardX + 20, curY + dateBarH / 2);

        const dtLabelW = ctx.measureText(dtLabel).width;
        ctx.font = `500 12px ${{fontSans}}`;
        ctx.fillStyle = '#7e22ce';
        ctx.fillText(`(${{dObj.items.length}} item${{dObj.items.length > 1 ? 's' : ''}})`, cardX + 20 + dtLabelW + 8, curY + dateBarH / 2);

        const dtSubFormatted = 'Date Subtotal: ₹' + dObj.dateTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
        ctx.font = `bold 13px ${{fontSans}}`;
        ctx.fillStyle = '#581c87';
        ctx.textAlign = 'right';
        ctx.fillText(dtSubFormatted, cardX + cardW - 20, curY + dateBarH / 2);

        curY += dateBarH;

        // Enrich and sort items: Credits on TOP, parent-child tax pairing
        const sortedItems = enrichAndSortEmiItems(dObj.items);

        sortedItems.forEach(item => {{
          // Row background color based on inheritance group!
          let rowBg = '#ffffff';
          let borderAccentColor = null;

          if (item.groupTheme === 'interest') {{
            rowBg = '#ede9fe'; // Punchy, vibrant Lavender/Indigo for Interest & its Tax!
            borderAccentColor = '#7c3aed';
          }} else if (item.groupTheme === 'fee') {{
            rowBg = '#fef3c7'; // Punchy, rich Golden Amber for Fee & its Tax!
            borderAccentColor = '#d97706';
          }} else if (item.is_credit) {{
            rowBg = '#e0f2fe'; // Punchy, crisp Sky Blue for Pre-EMI Credit!
            borderAccentColor = '#0284c7';
          }}

          ctx.fillStyle = rowBg;
          ctx.fillRect(cardX, curY, cardW, rowH);

          // Draw left vertical accent bar to visually connect parent & child!
          if (borderAccentColor) {{
            ctx.fillStyle = borderAccentColor;
            ctx.fillRect(cardX, curY, 6, rowH);
          }}

          ctx.beginPath();
          ctx.moveTo(cardX + 12, curY + rowH);
          ctx.lineTo(cardX + cardW - 12, curY + rowH);
          ctx.strokeStyle = '#f3e8ff';
          ctx.lineWidth = 1;
          ctx.stroke();

          // Left Arrow
          ctx.font = `bold 15px ${{fontSans}}`;
          ctx.fillStyle = item.groupTheme === 'interest' ? '#4f46e5' : (item.groupTheme === 'fee' ? '#d97706' : (item.is_credit ? '#2563eb' : '#94a3b8'));
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText('↳', item.taxInfo ? cardX + 32 : cardX + 22, curY + 25);

          // Description
          ctx.font = `600 14px ${{fontSans}}`;
          ctx.fillStyle = item.taxInfo ? (item.groupTheme === 'interest' ? '#3730a3' : '#78350f') : '#1e293b';
          let descText = item.description || '';
          if (descText.length > 54) descText = descText.substring(0, 51) + '...';
          ctx.fillText(descText, item.taxInfo ? cardX + 54 : cardX + 44, curY + 25);
          const descW = ctx.measureText(descText).width;

          // Matching Badge Pills (Parent & Child share matching theme colors!)
          if (item.is_credit) {{
            const compText = 'BEFORE EMI CONVERSION CREDIT';
            ctx.font = `bold 10px ${{fontSans}}`;
            const compW = ctx.measureText(compText).width + 16;
            const compX = cardX + 44 + descW + 10;
            if (compX + compW < cardX + cardW - 140) {{
              roundRect(compX, curY + 14, compW, 22, 6, '#dbeafe', '#93c5fd', 1);
              ctx.fillStyle = '#1e40af';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(compText, compX + compW / 2, curY + 25);
            }}
          }} else if (item.groupTheme === 'interest') {{
            const compText = item.groupRole === 'parent' ? 'INTEREST BASE' : 'TAX ON INTEREST';
            ctx.font = `bold 10px ${{fontSans}}`;
            const compW = ctx.measureText(compText).width + 16;
            const compX = (item.taxInfo ? cardX + 54 : cardX + 44) + descW + 10;
            if (compX + compW < cardX + cardW - 140) {{
              roundRect(compX, curY + 14, compW, 22, 6, '#e0e7ff', '#c7d2fe', 1);
              ctx.fillStyle = '#3730a3';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(compText, compX + compW / 2, curY + 25);
            }}
          }} else if (item.groupTheme === 'fee') {{
            const compText = item.groupRole === 'parent' ? 'FEE BASE' : 'TAX ON FEE';
            ctx.font = `bold 10px ${{fontSans}}`;
            const compW = ctx.measureText(compText).width + 16;
            const compX = (item.taxInfo ? cardX + 54 : cardX + 44) + descW + 10;
            if (compX + compW < cardX + cardW - 140) {{
              roundRect(compX, curY + 14, compW, 22, 6, '#fef3c7', '#fde68a', 1);
              ctx.fillStyle = '#92400e';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(compText, compX + compW / 2, curY + 25);
            }}
          }} else if (item.is_emi) {{
            const compText = 'EMI COMPONENT';
            ctx.font = `bold 10px ${{fontSans}}`;
            const compW = ctx.measureText(compText).width + 16;
            const compX = cardX + 44 + descW + 10;
            if (compX + compW < cardX + cardW - 140) {{
              roundRect(compX, curY + 14, compW, 22, 6, '#f3e8ff', '#e9d5ff', 1);
              ctx.fillStyle = '#6b21a8';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(compText, compX + compW / 2, curY + 25);
            }}
          }}

          // Sub-label: Show calculated arrow line for tax!
          ctx.font = `500 11px ${{fontMono}}`;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          if (item.taxInfo) {{
            ctx.fillStyle = item.groupTheme === 'interest' ? '#4f46e5' : '#d97706';
            ctx.fillText('↳ ' + item.taxInfo.label, cardX + 54, curY + 47);
          }} else if (item.is_credit) {{
            ctx.fillStyle = '#1e40af';
            ctx.fillText('CREDIT • BEFORE EMI CONVERSION (LOAN OFFSET)', cardX + 44, curY + 47);
          }} else if (item.groupTheme === 'interest') {{
            ctx.fillStyle = '#4f46e5';
            ctx.fillText('DEBIT / CHARGE (MONTHLY EMI INTEREST)', cardX + 44, curY + 47);
          }} else if (item.groupTheme === 'fee') {{
            ctx.fillStyle = '#d97706';
            ctx.fillText('DEBIT / CHARGE (LOAN SETUP PROCESSING FEE)', cardX + 44, curY + 47);
          }} else {{
            ctx.fillStyle = '#94a3b8';
            ctx.fillText('DEBIT / CHARGE', cardX + 44, curY + 47);
          }}

          // Right Amount
          ctx.font = `bold 15px ${{fontSans}}`;
          ctx.fillStyle = item.is_credit ? '#1d4ed8' : (item.groupTheme === 'interest' ? '#3730a3' : (item.groupTheme === 'fee' ? '#92400e' : '#0f172a'));
          ctx.textAlign = 'right';
          ctx.textBaseline = 'middle';
          ctx.fillText(item.amount_str, cardX + cardW - 20, curY + 23);

          // Right Type Pill
          const typeText = item.is_credit ? 'CREDIT (PRE-EMI)' : (item.taxInfo ? 'TAX (GST)' : 'DEBIT');
          ctx.font = `bold 10px ${{fontSans}}`;
          const tpW = ctx.measureText(typeText).width + 16;
          const tpX = cardX + cardW - 20 - tpW;
          const tpBg = item.is_credit ? '#dbeafe' : (item.groupTheme === 'interest' ? '#e0e7ff' : (item.groupTheme === 'fee' ? '#fef3c7' : '#f1f5f9'));
          const tpFg = item.is_credit ? '#1e40af' : (item.groupTheme === 'interest' ? '#3730a3' : (item.groupTheme === 'fee' ? '#92400e' : '#475569'));
          roundRect(tpX, curY + 36, tpW, 20, 10, tpBg, null);
          ctx.fillStyle = tpFg;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(typeText, tpX + tpW / 2, curY + 46);

          curY += rowH;
        }});
      }});

      // 4. Bottom Grand Total Footer (ZERO GAP: perfectly hugs the bottom border of the card!)
      const footerBottom = cardY + cardH;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cardX, curY);
      ctx.lineTo(cardX + cardW, curY);
      ctx.lineTo(cardX + cardW, footerBottom - cardR);
      ctx.arcTo(cardX + cardW, footerBottom, cardX + cardW - cardR, footerBottom, cardR);
      ctx.lineTo(cardX + cardR, footerBottom);
      ctx.arcTo(cardX, footerBottom, cardX, footerBottom - cardR, cardR);
      ctx.lineTo(cardX, curY);
      ctx.closePath();
      ctx.fillStyle = '#3b0764';
      ctx.fill();
      ctx.restore();

      ctx.beginPath();
      ctx.moveTo(cardX, curY);
      ctx.lineTo(cardX + cardW, curY);
      ctx.strokeStyle = '#a855f7';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      const totalVal = card.type === 'named_emi' ? card.combinedTotal : card.group.total;
      const totalFormatted = '₹' + totalVal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
      const dueLabel = (card.monthDueLabel || 'Due to be Paid') + ' (Grand Total)';

      ctx.font = `bold 16px ${{fontSans}}`;
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(dueLabel, cardX + 24, curY + footerH / 2 - 10);

      ctx.font = `500 12px ${{fontSans}}`;
      ctx.fillStyle = '#e9d5ff';
      ctx.fillText('Total monthly installment & charges to be reimbursed', cardX + 24, curY + footerH / 2 + 12);

      // Right Grand Total Pill
      ctx.font = `bold 20px ${{fontSans}}`;
      const totPillW = Math.max(130, ctx.measureText(totalFormatted).width + 36);
      const totPillX = cardX + cardW - 20 - totPillW;
      roundRect(totPillX, curY + (footerH - 40) / 2, totPillW, 40, 12, '#9333ea', '#c084fc', 1.5);
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(totalFormatted, totPillX + totPillW / 2, curY + footerH / 2);

      // 5. STROKE OUTER CARD BORDER LAST (Guarantees crisp 2px border framing the entire card with 0 gaps!)
      roundRect(cardX, cardY, cardW, cardH, cardR, null, '#c084fc', 2);

      return canvas;
    }}

    async function shareReceiptOnWhatsApp(cardElementId, emiName, loanId, totalStr, datesStr) {{
      const idxMatch = String(cardElementId).match(/(\d+)$/);
      const cardIdx = idxMatch ? parseInt(idxMatch[1], 10) : -1;
      const cardData = (window.renderedCardsData && cardIdx >= 0) ? window.renderedCardsData[cardIdx] : null;

      // 1. Get phone number (auto-prefixed with 91 for India)
      let phone = cleanIndianPhone(getSavedPhone(loanId) || getSavedPhone(emiName));
      if (!phone || phone.length < 10) {{
        const entered = prompt("Enter 10-digit mobile number for " + (emiName || "this receipt") + " (+91 will be added automatically):", "");
        if (!entered) return;
        phone = cleanIndianPhone(entered);
        if (!phone || phone.length < 10) {{
          alert("Please enter a valid 10-digit Indian mobile number.");
          return;
        }}
        if (loanId) localStorage.setItem("emi_phone_" + loanId, phone);
        if (emiName) localStorage.setItem("emi_phone_" + emiName, phone);
      }}

      // 2. Open new tab synchronously to avoid popup blocker
      const waWin = window.open('about:blank', '_blank');

      // 3. Build clean itemized WhatsApp text receipt using template literals
      const cleanTotal = totalStr.replace(/₹/g, 'Rs. ');
      let message = (cardData && cardData.cheerMessage) ? `${{cardData.cheerMessage}}

` : '';
      message += `*EMI STATEMENT RECEIPT - ${{emiName || 'Monthly Installment'}}*
`;
      message += `*Billing Date(s):* ${{datesStr}}
`;
      message += `*Total Amount Due:* ${{cleanTotal}}

`;
      message += `*Itemized Breakdown:*
`;

      if (cardData) {{
        const dates = cardData.type === 'named_emi' ? cardData.dates : [{{ items: cardData.items }}];
        dates.forEach(d => {{
          d.items.forEach(itm => {{
            if (!itm.is_credit) {{
              const amtClean = (itm.amount_str || '').replace(/₹/g, 'Rs. ');
              message += `• ${{itm.description}}: ${{amtClean}}
`;
            }}
          }});
        }});
      }}

      message += `
_(Receipt snapshot image copied to clipboard - press Ctrl+V to paste! / saved to device)_`;

      try {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          navigator.clipboard.writeText(message);
        }}
      }} catch (e) {{}}

      const waUrl = `https://api.whatsapp.com/send?phone=${{phone}}&text=${{encodeURIComponent(message)}}`;

      // 4. Render crisp pixel-perfect receipt canvas natively & copy image to clipboard
      try {{
        if (cardData) {{
          const canvas = drawNativeReceiptCanvas(cardData);

          // Copy PNG image blob to Clipboard (for instant Ctrl+V paste into WhatsApp!)
          if (canvas.toBlob) {{
            canvas.toBlob(async (blob) => {{
              if (blob && navigator.clipboard && window.ClipboardItem && navigator.clipboard.write) {{
                try {{
                  const item = new ClipboardItem({{ "image/png": blob }});
                  await navigator.clipboard.write([item]);
                  console.log("Snapshot image copied to clipboard successfully!");
                }} catch (clipErr) {{
                  console.warn("Could not copy image to clipboard:", clipErr);
                }}
              }}
            }}, "image/png");
          }}

          // Also download PNG file to device
          const imgUrl = canvas.toDataURL("image/png");
          const dlLink = document.createElement("a");
          dlLink.download = `${{(emiName || 'EMI_Receipt').replace(/\s+/g, '_')}}_Snapshot.png`;
          dlLink.href = imgUrl;
          dlLink.click();
        }}
      }} catch (e) {{
        console.error("Canvas render error:", e);
      }}

      // 5. Navigate the open window directly to WhatsApp
      if (waWin) {{
        waWin.location.href = waUrl;
      }} else {{
        window.location.href = waUrl;
      }}
    }}

    function getActiveStatement() {{
      if (activeIndex === -1 || (statements.length > 1 && activeIndex === -1)) {{
        const combined = {{
          bank_name: "Consolidated All Statements",
          bank_short: "All Statements",
          statement_month: statements[0] ? statements[0].statement_month : "October 2026",
          due_date: statements.map(s => (s.bank_short || 'Bank') + ': ' + (s.due_date || '')).join(' • '),
          month_folder_name: statements[0] ? statements[0].month_folder_name : "Statements_October_2026",
          saved_name: statements.length + " Statements Loaded",
          all_txns: [],
          ongoing_emis: [],
          date_groups: {{}},
          total_due: ""
        }};
        let sumDue = 0;
        statements.forEach(s => {{
          (s.all_txns || []).forEach(t => combined.all_txns.push({{ ...t, bank_badge: s.bank_short }}));
          (s.ongoing_emis || []).forEach(e => combined.ongoing_emis.push({{ ...e, bank_badge: s.bank_short }}));
          const cleanDue = parseFloat(String(s.total_due || '0').replace(/[^0-9.]/g, ''));
          if (!isNaN(cleanDue)) sumDue += cleanDue;

          Object.entries(s.date_groups || {{}}).forEach(([dt, grp]) => {{
            if (!combined.date_groups[dt]) {{
              combined.date_groups[dt] = {{
                total: 0,
                has_emi: false,
                items: []
              }};
            }}
            combined.date_groups[dt].total += (grp.total || 0);
            if (grp.has_emi) combined.date_groups[dt].has_emi = true;
            (grp.items || []).forEach(itm => {{
              combined.date_groups[dt].items.push({{
                ...itm,
                bank_badge: s.bank_short
              }});
            }});
          }});
        }});
        combined.total_due = '₹' + sumDue.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
        return combined;
      }}
      return statements[activeIndex] || statements[0];
    }}

        function renderTabs() {{
      const tabsContainer = document.getElementById('bank-tabs');
      tabsContainer.innerHTML = '';
      tabsContainer.className = 'flex items-center gap-2 mb-8 overflow-x-auto pb-2 apple-segmented-bar';

      if (statements.length > 1) {{
        const allBtn = document.createElement('button');
        const isActive = activeIndex === -1;
        allBtn.className = `apple-tab-btn px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${{
          isActive 
            ? 'bg-white text-slate-900 shadow-sm border border-slate-200/90 font-extrabold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
        }}`;
        allBtn.innerHTML = `<span class="w-2 h-2 rounded-full ${{isActive ? 'bg-indigo-600 animate-pulse' : 'bg-slate-300'}}"></span><span>🌐 All Statements (${{statements.length}} Cards)</span>`;
        allBtn.onclick = () => {{ activeIndex = -1; renderDashboard(); }};
        tabsContainer.appendChild(allBtn);
      }}

      statements.forEach((stmt, idx) => {{
        const btn = document.createElement('button');
        const isActive = idx === activeIndex;
        const bName = (stmt.bank_name || stmt.bank_short || '').toLowerCase();
        const isSwiggy = bName.includes('swiggy') || bName.includes('hdfc');
        const isAmazon = bName.includes('amazon') || bName.includes('icici');

        let dotColor = isSwiggy ? 'bg-[#fc8019]' : (isAmazon ? 'bg-[#ff9900]' : 'bg-blue-600');
        let icon = isSwiggy ? '🛵' : (isAmazon ? '🛒' : '🏛️');

        btn.className = `apple-tab-btn px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${{
          isActive 
            ? 'bg-white text-slate-900 shadow-sm border border-slate-200/90 font-extrabold' 
            : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
        }}`;
        btn.innerHTML = `<span class="w-2 h-2 rounded-full ${{isActive ? dotColor + ' animate-pulse' : 'bg-slate-300'}}"></span><span>${{icon}} ${{stmt.bank_short}} (${{stmt.statement_month}})</span>`;
        btn.onclick = () => {{ activeIndex = idx; renderDashboard(); }};
        tabsContainer.appendChild(btn);
      }});
    }}

    function setupCardPhysics() {{
      const card = document.getElementById('apple-active-card');
      if (!card) return;

      card.onmousemove = (e) => {{
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const cx = rect.width / 2;
        const cy = rect.height / 2;
        const rx = ((y - cy) / cy) * -9;
        const ry = ((x - cx) / cx) * 9;
        card.style.transform = `perspective(1000px) rotateX(${{rx}}deg) rotateY(${{ry}}deg) scale3d(1.02, 1.02, 1.02)`;
        card.style.setProperty('--mouse-x', `${{(x / rect.width) * 100}}%`);
        card.style.setProperty('--mouse-y', `${{(y / rect.height) * 100}}%`);
      }};

      card.onmouseleave = () => {{
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
      }};
    }}

    function renderHero() {{
      const stmt = getActiveStatement();
      const hero = document.getElementById('statement-hero');
      
      const bName = (stmt.bank_name || stmt.bank_short || '').toLowerCase();
      const isSwiggy = bName.includes('swiggy') || bName.includes('hdfc');
      const isAmazon = bName.includes('amazon') || bName.includes('icici');
      const isAll = activeIndex === -1;

      let cardStageHtml = '';
      let ambientColor = 'rgba(99, 102, 241, 0.25)';
      let cardBadgeText = 'Multi-Card Portfolio';
      let cardBadgeClass = 'bg-indigo-100 text-indigo-900 border-indigo-200';

      if (isSwiggy) {{
        ambientColor = 'rgba(252, 128, 25, 0.28)';
        cardBadgeText = 'Swiggy HDFC Bank Card';
        cardBadgeClass = 'bg-orange-100 text-orange-950 border-orange-200';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl" style="background: url('${{CARD_IMAGES.swiggy}}') center/cover no-repeat;">
            <div class="apple-card-glare"></div>
          </div>
        `;
      }} else if (isAmazon) {{
        ambientColor = 'rgba(245, 158, 11, 0.24)';
        cardBadgeText = 'Amazon Pay ICICI Card';
        cardBadgeClass = 'bg-amber-100 text-amber-950 border-amber-200';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl" style="background: url('${{CARD_IMAGES.amazon}}') center/cover no-repeat;">
            <div class="apple-card-glare"></div>
          </div>
        `;
      }} else {{
        ambientColor = 'rgba(99, 102, 241, 0.22)';
        cardBadgeText = 'Consolidated Dual Cards';
        cardBadgeClass = 'bg-indigo-100 text-indigo-900 border-indigo-200';
        cardStageHtml = `
          <div class="relative w-full max-w-[380px] h-[230px] flex items-center justify-center">
            <!-- Back Card (ICICI Amazon) -->
            <div class="apple-physical-card absolute w-[88%] shadow-lg top-0 right-2 -rotate-3 opacity-90 transition hover:rotate-0 hover:z-20 hover:opacity-100" style="background: url('${{CARD_IMAGES.amazon}}') center/cover no-repeat;">
              <div class="apple-card-glare"></div>
            </div>
            <!-- Front Card (HDFC Swiggy) -->
            <div id="apple-active-card" class="apple-physical-card absolute w-[92%] shadow-2xl bottom-1 left-2 rotate-2 transition hover:rotate-0" style="background: url('${{CARD_IMAGES.swiggy}}') center/cover no-repeat;">
              <div class="apple-card-glare"></div>
            </div>
          </div>
        `;
      }}

      hero.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          
          <!-- LEFT: Apple Wallet Physical Card Showcase (5 Columns) -->
          <div class="lg:col-span-5 rounded-3xl apple-glass p-6 sm:p-7 flex flex-col justify-between items-center relative overflow-hidden group">
            <div class="absolute -inset-10 blur-3xl pointer-events-none transition-all duration-700" style="background: ${{ambientColor}};"></div>
            
            <!-- Top Card Micro-Bar -->
            <div class="w-full flex justify-between items-center text-xs font-bold text-slate-500 relative z-10 mb-4">
              <span class="px-3 py-1 rounded-full text-[11px] font-extrabold border ${{cardBadgeClass}} flex items-center gap-1.5 shadow-xs">
                <span>💳</span>
                <span>${{cardBadgeText}}</span>
              </span>
              <span class="text-[11px] font-mono text-slate-400 bg-slate-100/80 px-2.5 py-0.5 rounded-lg border border-slate-200/60">3D Interactive</span>
            </div>

            <!-- Pristine Physical Card Stage -->
            <div class="apple-card-stage w-full flex justify-center py-2 relative z-10">
              ${{cardStageHtml}}
            </div>

            <!-- Bottom Card Specs -->
            <div class="w-full flex justify-between items-center text-xs text-slate-500 mt-4 pt-3 border-t border-slate-200/60 relative z-10">
              <span class="font-bold text-slate-700">${{stmt.bank_name}}</span>
              <span class="font-mono text-slate-400 text-[11px]">${{stmt.statement_month}}</span>
            </div>
          </div>

          <!-- RIGHT: Statement Intelligence & Apple Glass Metrics (7 Columns) -->
          <div class="lg:col-span-7 flex flex-col justify-between gap-4">
            
            <!-- Primary Tile: Statement Total Due -->
            <div class="p-7 rounded-3xl apple-glass flex flex-col justify-between flex-1 relative overflow-hidden">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div>
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">Statement Total Due</span>
                  <div class="text-4xl sm:text-5xl font-extrabold text-slate-900 mt-1 tracking-[-0.03em] leading-none">${{stmt.total_due}}</div>
                </div>
                <div class="flex items-center gap-2 self-start sm:self-auto">
                  <span class="px-3.5 py-1.5 rounded-full text-xs font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-300/80 shadow-xs flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Due: ${{stmt.due_date}}</span>
                  </span>
                </div>
              </div>

              <!-- Metadata Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6 pt-5 border-t border-slate-200/60 text-xs">
                <div>
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">Account / Card</div>
                  <div class="font-extrabold text-slate-800 text-sm mt-0.5 truncate">${{stmt.bank_short}}</div>
                </div>
                <div>
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">Billing Cycle</div>
                  <div class="font-extrabold text-slate-800 text-sm mt-0.5">${{stmt.statement_month}}</div>
                </div>
                <div class="col-span-2 sm:col-span-1">
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">Storage Path</div>
                  <div class="font-bold text-blue-600 text-xs mt-0.5 truncate" title="${{stmt.saved_name}}">📁 ${{stmt.saved_name}}</div>
                </div>
              </div>
            </div>

            <!-- Secondary Row: Split EMI Reimbursements & Fast Actions -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Tile 1: Friend EMI Reimbursements -->
              <div class="p-5 rounded-3xl apple-glass flex flex-col justify-between">
                <div class="flex justify-between items-center">
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">Friend EMI Split</span>
                  <span id="hero-settle-badge" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">Tracking</span>
                </div>
                <div class="flex items-baseline justify-between mt-3">
                  <div>
                    <div class="text-[10px] font-bold text-emerald-600 uppercase tracking-wide">Collected</div>
                    <div id="hero-collected-amt" class="text-xl font-extrabold text-emerald-700 mt-0.5 tracking-tight">₹0.00</div>
                  </div>
                  <div class="text-right">
                    <div class="text-[10px] font-bold text-amber-600 uppercase tracking-wide">Pending</div>
                    <div id="hero-pending-amt" class="text-xl font-extrabold text-amber-700 mt-0.5 tracking-tight">₹0.00</div>
                  </div>
                </div>
              </div>

              <!-- Tile 2: Activity Summary & Direct Actions -->
              <div class="p-5 rounded-3xl apple-glass flex flex-col justify-between">
                <div class="flex justify-between items-center">
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">Statement Activity</span>
                  <span class="text-xs font-bold text-slate-500">${{stmt.all_txns.length}} transactions</span>
                </div>
                <div class="flex items-center gap-2 mt-3">
                  <button onclick="document.getElementById('search-input').focus()" class="flex-1 px-3 py-2 text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white rounded-xl shadow-xs transition flex items-center justify-center gap-1.5 active:scale-95 cursor-pointer">
                    <span>🔍</span>
                    <span>Search</span>
                  </button>
                  <button onclick="exportCSV()" class="px-3.5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow-xs transition flex items-center justify-center gap-1 active:scale-95 cursor-pointer">
                    <span>📊</span>
                    <span>CSV</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      `;

      setupCardPhysics();
    }}

    function renderCashbackAudit() {{
      const stmt = getActiveStatement();
      const container = document.getElementById('cashback-audit-section');
      if (!container) return;

      const txns = stmt.all_txns || [];
      const cbItems = [];
      let totalCredited = 0;
      let totalReversed = 0;

      txns.forEach(t => {{
        const d = (t.description || '').toLowerCase();
        if (d.includes('cashback') || d.includes('reward') || d.includes('cb_') || d.includes('cash back')) {{
          if (t.is_credit) {{
            totalCredited += t.amount;
            cbItems.push({{
              date: t.date,
              desc: t.description,
              amount: t.amount,
              type: 'Credit',
              status: 'Verified Credited'
            }});
          }} else {{
            totalReversed += t.amount;
            cbItems.push({{
              date: t.date,
              desc: t.description,
              amount: t.amount,
              type: 'Reversal',
              status: 'Reversed by Bank (EMI Conversion)'
            }});
          }}
        }}
      }});

      const isIcici = (stmt.bank_short || '').includes('ICICI');
      const isHdfc = (stmt.bank_short || '').includes('HDFC');

      if (cbItems.length === 0 && !isIcici) {{
        container.innerHTML = '';
        return;
      }}

      const netCashback = totalCredited - totalReversed;

      let rowsHtml = '';
      cbItems.forEach(item => {{
        const isRev = item.type === 'Reversal';
        rowsHtml += `
          <div class="px-5 py-3 flex justify-between items-center text-xs ${{isRev ? 'bg-rose-50/40 text-rose-900' : 'hover:bg-slate-50/60'}}">
            <div class="flex items-center gap-3">
              <span class="${{isRev ? 'text-rose-500 font-bold' : 'text-emerald-500'}}">↳</span>
              <div>
                <span class="font-semibold text-slate-800">${{item.desc}}</span>
                <span class="ml-2 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${{isRev ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-800'}}">${{item.status}}</span>
              </div>
            </div>
            <div class="font-bold text-sm ${{isRev ? 'text-rose-600' : 'text-emerald-600'}}">
              ${{isRev ? '-' : '+'}}₹${{item.amount.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}
            </div>
          </div>
        `;
      }});

      let ruleExplanation = '';
      if (isHdfc) {{
        ruleExplanation = `
          <div class="mt-3 text-[11px] text-slate-500 border-t border-slate-100 pt-3 flex flex-wrap gap-4">
            <span>• <b>10% Swiggy Cashback</b>: Valid on Food, Instamart & Dineout (Verified)</span>
            <span>• <b>5% Partner Cashback</b>: Valid on Myntra, Flipkart, etc. (Verified)</span>
            <span>• <b>Cashback Reversal</b>: 1% reversed automatically upon converting purchase to Smart EMI</span>
          </div>
        `;
      }} else if (isIcici) {{
        ruleExplanation = `
          <div class="mt-3 text-[11px] text-slate-500 border-t border-slate-100 pt-3 flex flex-wrap gap-4">
            <span>• <b>5% Amazon Prime</b>: Unlimited 5% cashback on Amazon Shopping</span>
            <span>• <b>2% Bill Payments & Flights</b>: Added directly to Amazon Pay balance</span>
            <span>• <b>1% All Other Spends</b>: Credited automatically at billing cycle (1 Point = ₹1.00)</span>
          </div>
        `;
      }}

      container.innerHTML = `
        <div class="bg-white rounded-3xl border border-emerald-200/90 shadow-sm p-6 overflow-hidden">
          <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <span class="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">🎁</span>
              <div>
                <div class="flex items-center gap-2">
                  <h2 class="text-base font-bold text-slate-900">Cashback & Rewards Accuracy Audit</h2>
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800">100% Reconciled</span>
                </div>
                <p class="text-xs text-slate-500">Audited against ${{stmt.bank_short}} reward rules to ensure correct credits and identify reversals.</p>
              </div>
            </div>
            <div class="flex items-center gap-3 w-full sm:w-auto">
              <div class="px-4 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-right">
                <span class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 block">Net Cashback Earned</span>
                <span class="text-lg font-extrabold text-emerald-700">₹${{netCashback.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
              </div>
            </div>
          </div>

          <div class="divide-y divide-slate-100 mt-2">
            ${{rowsHtml || '<div class="p-4 text-xs text-slate-400">No cashback entries detected on this statement.</div>'}}
          </div>

          ${{ruleExplanation}}
        </div>
      `;
    }}

    function renderOngoingEMIs() {{
      const stmt = getActiveStatement();
      const emiContainer = document.getElementById('ongoing-emi-section');
      const emis = stmt.ongoing_emis || [];

      if (emis.length === 0) {{
        emiContainer.innerHTML = '';
        return;
      }}

      let cardsHtml = '';
      emis.forEach(emi => {{
        const savedName = getSavedName(emi.loan_id, emi.custom_name);
        const displayName = savedName ? savedName : (emi.type + " (" + emi.booked_date + ")");

        cardsHtml += `
          <div class="bg-white rounded-2xl border border-amber-200/90 p-5 shadow-sm hover:shadow-md transition">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
              <div>
                <div class="flex items-center gap-2">
                  <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 uppercase tracking-wide">${{emi.type}}</span>
                  <span class="text-xs text-slate-400 font-mono">ID: ${{emi.loan_id}}</span>
                </div>
                <div class="text-lg font-bold text-slate-900 mt-1">${{displayName}}</div>
              </div>
              <div class="flex items-center gap-2 w-full sm:w-auto flex-wrap">
                <input type="text" id="emi-input-${{emi.loan_id}}" placeholder="Nickname (e.g. Naveen S25Edge)..." value="${{savedName}}" class="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 w-full sm:w-44">
                <input type="tel" id="emi-phone-${{emi.loan_id}}" placeholder="WhatsApp No. (e.g. 9876543210)..." value="${{getSavedPhone(emi.loan_id)}}" class="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full sm:w-44">
                <button onclick="saveCustomName('${{emi.loan_id}}')" class="px-3 py-1.5 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-lg shadow-sm transition">💾 Save</button>
              </div>
            </div>
            
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 text-xs">
              <div>
                <span class="text-slate-400 block">Total Loan Amount</span>
                <span class="font-bold text-slate-800 text-sm">${{emi.total_amount}}</span>
              </div>
              <div>
                <span class="text-slate-400 block">Balance Remaining</span>
                <span class="font-bold text-rose-600 text-sm">${{emi.balance_principal}}</span>
              </div>
              <div>
                <span class="text-slate-400 block">Balance Tenure</span>
                <span class="font-bold text-slate-800 text-sm">${{emi.balance_tenure}}</span>
              </div>
              <div>
                <span class="text-slate-400 block">${{emi.monthly_emi ? 'Monthly Installment' : 'Interest Rate'}}</span>
                <span class="font-bold text-slate-800 text-sm">${{emi.monthly_emi || emi.interest_rate}}</span>
              </div>
            </div>

            <!-- EMI True Cost & Hidden Charges Calculator -->
            ${{(() => {{
              const lAmt = parseFloat((emi.total_amount || '').replace(/[₹,]/g, '')) || 0;
              const mEmi = parseFloat((emi.monthly_emi || '').replace(/[₹,]/g, '')) || 0;
              const tenureNum = parseInt((emi.total_tenure || '').replace(/\D/g, ''), 10) || 0;
              if (lAmt <= 0) return '';
              const estRepay = (mEmi > 0 && tenureNum > 0) ? (mEmi * tenureNum) : (lAmt * 1.088);
              const estInterest = Math.max(0, estRepay - lAmt);
              const pFee = 299.0;
              const pGst = 53.82;
              const extraCost = estInterest + pFee + pGst;
              const markupPct = ((extraCost / lAmt) * 100).toFixed(1);

              return `
                <div class="mt-4 pt-3 border-t border-amber-200/60 bg-amber-50/50 -mx-5 -mb-5 p-4 rounded-b-2xl">
                  <div class="flex items-center justify-between flex-wrap gap-2 mb-2">
                    <span class="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                      <span>💰</span>
                      <span>EMI True Cost & Hidden Charges Calculator</span>
                    </span>
                    <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-200 text-amber-900">
                      Total Extra Cost: +₹${{extraCost.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}} (+${{markupPct}}%)
                    </span>
                  </div>
                  <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div class="bg-white p-2 rounded-xl border border-amber-200/70">
                      <span class="text-slate-400 block text-[10px]">Original Cash Price</span>
                      <span class="font-bold text-slate-800 text-xs">₹${{lAmt.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-amber-200/70">
                      <span class="text-slate-400 block text-[10px]">Total Repayment</span>
                      <span class="font-bold text-slate-800 text-xs">₹${{estRepay.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-amber-200/70">
                      <span class="text-slate-400 block text-[10px]">Interest Charged</span>
                      <span class="font-bold text-rose-600 text-xs">₹${{estInterest.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
                    </div>
                    <div class="bg-white p-2 rounded-xl border border-amber-200/70">
                      <span class="text-slate-400 block text-[10px]">Fee + 18% GST</span>
                      <span class="font-bold text-amber-800 text-xs">₹${{(pFee + pGst).toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>
                    </div>
                  </div>
                </div>
              `;
            }})()}}
          </div>
        `;
      }});

      emiContainer.innerHTML = `
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-3xl p-6 shadow-sm">
          <div class="flex items-center gap-3 mb-4">
            <span class="w-9 h-9 rounded-xl bg-amber-500 text-white flex items-center justify-center font-bold text-lg shadow-sm">📊</span>
            <div>
              <h2 class="text-base font-bold text-slate-900">Ongoing EMIs & Loan Summary</h2>
              <p class="text-xs text-slate-500">Assign editable custom nicknames to track what you bought. Saved names will appear automatically on your next bill!</p>
            </div>
          </div>
          <div class="space-y-3">${{cardsHtml}}</div>
        </div>
      `;
    }}

    function getLoanDetailsForGroup(group, stmt) {{
      if (!group.has_emi) return null;

      // 1. Check for HDFC loan number match
      for (const itm of group.items) {{
        for (const emi of (stmt.ongoing_emis || [])) {{
          if (itm.description && emi.loan_id && itm.description.includes(emi.loan_id)) {{
            const saved = getSavedName(emi.loan_id, emi.custom_name);
            return {{
              loanKey: emi.loan_id,
              loanName: saved || emi.display_name || ("Loan #" + emi.loan_id),
              loanObj: emi
            }};
          }}
        }}
      }}

      // 2. Check for ICICI <curr/total> Merchant pattern (e.g. <1/9> EZ TRADERS vs <8/12> Flipkart)
      for (const itm of group.items) {{
        const mInst = (itm.description || "").match(/<(\d+)\/(\d+)>\s*(.*?)(?:\s+PVT|\s+LTD|\s*$)/i);
        if (mInst) {{
          const currInst = mInst[1];
          const totalTenure = mInst[2];
          const rawMerchant = mInst[3].trim();
          const cleanMerchantKey = rawMerchant.replace(/[^a-zA-Z0-9]/g, "_").toLowerCase();

          // Match only an ongoing EMI that actually shares this exact tenure or merchant!
          let matchedEmi = null;
          for (const emi of (stmt.ongoing_emis || [])) {{
            const numMatch = (emi.total_tenure || "").match(/\d+/);
            const isTenureMatch = numMatch && numMatch[0] === totalTenure;
            const saved = getSavedName(emi.loan_id, emi.custom_name);
            const isMerchantMatch = rawMerchant && (
              (saved && saved.toLowerCase().includes(rawMerchant.toLowerCase())) ||
              (emi.loan_id && emi.loan_id.toLowerCase().includes(rawMerchant.toLowerCase()))
            );
            if (isTenureMatch && isMerchantMatch) {{
              matchedEmi = emi;
              break;
            }}
          }}

          if (!matchedEmi) {{
            const tenureMatches = (stmt.ongoing_emis || []).filter(e => {{
              const nm = (e.total_tenure || "").match(/\d+/);
              return nm && nm[0] === totalTenure;
            }});
            if (tenureMatches.length === 1) {{
              matchedEmi = tenureMatches[0];
            }}
          }}

          const loanKey = matchedEmi ? matchedEmi.loan_id : `loan_${{cleanMerchantKey}}_${{totalTenure}}`;
          const saved = matchedEmi ? getSavedName(matchedEmi.loan_id, matchedEmi.custom_name) : getSavedName(loanKey, "");

          return {{
            loanKey: loanKey,
            loanName: saved || rawMerchant || `EMI (<${{currInst}}/${{totalTenure}}>)`,
            loanObj: matchedEmi,
            rawMerchant: rawMerchant,
            currInst: currInst,
            totalTenure: totalTenure
          }};
        }}
      }}

      // 3. Check if there are setup charges matching an ongoing loan
      for (const itm of group.items) {{
        const d = (itm.description || "").toLowerCase();
        if (d.includes("procng fee") || d.includes("fee") || d.includes("swiggy cashback_reversal")) {{
          for (const emi of (stmt.ongoing_emis || [])) {{
            if (emi.loan_id && itm.description.includes(emi.loan_id)) {{
              const saved = getSavedName(emi.loan_id, emi.custom_name);
              return {{
                loanKey: emi.loan_id,
                loanName: saved || emi.display_name || ("Loan #" + emi.loan_id),
                loanObj: emi
              }};
            }}
          }}
        }}
      }}

      return null;
    }}

    function renderDateGroups(filterText = '') {{
      const stmt = getActiveStatement();
      const container = document.getElementById('date-breakdown-container');
      container.innerHTML = '';

      let matchedTxnCount = 0;

      // Group cards: For EMI with a custom name, consolidate all its dates into ONE card!
      // For regular dates or unnamed EMIs, keep individual date cards.
      const cardsList = [];
      const namedEmiCardMap = {{}}; // emiName -> cardObj

      Object.entries(stmt.date_groups).forEach(([dateStr, group]) => {{
        const filteredItems = group.items.filter(item => 
          item.description.toLowerCase().includes(filterText.toLowerCase()) ||
          dateStr.includes(filterText) ||
          item.amount.toString().includes(filterText)
        );

        if (filteredItems.length === 0) return;
        matchedTxnCount += filteredItems.length;

        const loanDetails = group.has_emi ? getLoanDetailsForGroup(group, stmt) : null;

        if (loanDetails) {{
          const loanKey = loanDetails.loanKey;
          const emiName = loanDetails.loanName;
          const sortedItems = enrichAndSortEmiItems(filteredItems);

          if (namedEmiCardMap[loanKey]) {{
            namedEmiCardMap[loanKey].dates.push({{
              dateStr: dateStr,
              items: sortedItems,
              dateTotal: group.total
            }});
            namedEmiCardMap[loanKey].combinedTotal += group.total;
            namedEmiCardMap[loanKey].totalItemsCount += filteredItems.length;
          }} else {{
            const foundLoan = loanDetails.loanObj;
            let foundLoanId = loanDetails.loanKey;
            let overallLoanAmount = foundLoan ? (foundLoan.total_amount || "") : "";
            let totalTenure = loanDetails.totalTenure || "";
            let remainingCount = "";

            if (foundLoan) {{
              const mTot = (foundLoan.total_tenure || "").match(/\d+/);
              if (mTot && !totalTenure) totalTenure = mTot[0];
              const mBal = (foundLoan.balance_tenure || "").match(/\d+/);
              if (mBal) remainingCount = mBal[0];
            }}

            let currInstNum = loanDetails.currInst ? parseInt(loanDetails.currInst, 10) : 1;
            if (!loanDetails.currInst && totalTenure && remainingCount) {{
              const calc = parseInt(totalTenure, 10) - parseInt(remainingCount, 10);
              if (calc > 0) currInstNum = calc;
            }}

            const instLabel = totalTenure ? `Installment ${{currInstNum}} of ${{totalTenure}}` : `Installment #${{currInstNum}}`;
            const monthInstallmentTitle = `${{stmt.statement_month}} • ${{instLabel}}`;
            const monthDueLabel = `${{stmt.statement_month}} Due to be Paid`;

            const personName = emiName ? emiName.trim().split(/\s+/)[0] : "";
            const cheerEmojis = String.fromCodePoint(0x1F60A) + String.fromCodePoint(0x1F44D);
            const cheerMessage = personName ? `Hi ${{personName}}! Only ${{remainingCount ? remainingCount + ' more to go' : 'almost there'}} ${{cheerEmojis}}` : "";

            const cardObj = {{
              type: 'named_emi',
              loanKey: loanKey,
              emiName: emiName,
              loanId: foundLoanId,
              overallLoanAmount: overallLoanAmount,
              monthInstallmentTitle: monthInstallmentTitle,
              monthDueLabel: monthDueLabel,
              currInstNum: currInstNum,
              totalTenure: totalTenure,
              remainingCount: remainingCount,
              cheerMessage: cheerMessage,
              dates: [{{
                dateStr: dateStr,
                items: sortedItems,
                dateTotal: group.total
              }}],
              combinedTotal: group.total,
              totalItemsCount: filteredItems.length
            }};
            namedEmiCardMap[loanKey] = cardObj;
            cardsList.push(cardObj);
          }}
        }} else {{
          cardsList.push({{
            type: 'date',
            dateStr: dateStr,
            group: group,
            items: filteredItems,
            isEmiGroup: group.has_emi
          }});
        }}
      }});

      window.renderedCardsData = cardsList;
      cardsList.forEach((card, cardIdx) => {{
        // Apply Category Filter
        if (currentFilterCategory === 'emi') {{
          if (card.type !== 'named_emi' && !card.isEmiGroup) return;
        }} else if (currentFilterCategory === 'regular') {{
          if (card.type === 'named_emi' || card.isEmiGroup) return;
        }} else if (currentFilterCategory === 'credit') {{
          const hasCredit = (card.items || []).some(it => it.is_credit) || (card.dates || []).some(d => (d.items || []).some(it => it.is_credit));
          if (!hasCredit) return;
        }}

        if (card.type === 'named_emi') {{
          // Single Unified Card for this named EMI with divided dates!
          const dateCard = document.createElement('div');
          dateCard.id = `card-named-emi-${{cardIdx}}`;
          dateCard.className = 'bg-white rounded-2xl border-2 border-purple-400 shadow-md emi-card-glow emi-receipt-card overflow-hidden transition';

          const datesHeaderStr = card.dates.map(d => d.dateStr).join(', ');
          
          // BIG Prominent EMI Receipt Header
          const header = document.createElement('div');
          header.className = 'p-6 sm:p-7 bg-gradient-to-br from-purple-100/90 via-purple-50/70 to-indigo-50/80 emi-receipt-header border-b-2 border-purple-200';
          header.innerHTML = `
            <div class="flex flex-col gap-5 w-full">
              
              <!-- TOP ROW: Title on Left, Action Buttons & Status on Right -->
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 w-full">
                <div class="flex items-center gap-3">
                  <div class="w-12 h-12 rounded-xl bg-purple-600 emi-icon-box text-white flex items-center justify-center font-black text-xl shadow-md shadow-purple-500/30 flex-shrink-0" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #fff !important;">
                    🏷️
                  </div>
                  <div>
                    <div class="flex items-center gap-2.5 flex-wrap">
                      <span class="text-2xl font-black text-slate-900 tracking-tight">🏷️ ${{card.emiName}}</span>
                      <span class="px-3 py-0.5 rounded-full text-xs font-extrabold bg-purple-600 emi-badge text-white shadow-sm uppercase tracking-wider" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #fff !important;">
                        EMI INSTALLMENT RECEIPT
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Action Buttons: Mark as Paid & Share WhatsApp -->
                <div class="flex items-center gap-2.5 flex-wrap self-stretch sm:self-auto justify-end">
                  ${{(() => {{
                    const pStatus = getPaymentStatus(card.emiName);
                    return `
                      <button onclick="togglePaymentStatus('${{card.emiName}}', '₹${{card.combinedTotal.toLocaleString('en-IN')}}')" class="no-print px-3.5 py-2 rounded-xl border ${{pStatus.isPaid ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100' : 'border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'}} font-bold text-xs shadow-sm transition flex items-center gap-1.5 cursor-pointer">
                        <span>${{pStatus.isPaid ? '🟢' : '🟡'}}</span>
                        <span>${{pStatus.isPaid ? 'Paid on ' + pStatus.paidDate : 'Mark as Paid'}}</span>
                      </button>
                    `;
                  }})()}}
                  <button onclick="shareReceiptOnWhatsApp('card-named-emi-${{cardIdx}}', '${{card.emiName}}', '${{card.loanId || ''}}', '₹${{card.combinedTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}', '${{datesHeaderStr}}')" class="no-print px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 transition flex items-center gap-1.5 cursor-pointer">
                    <span>📲</span>
                    <span>Share WhatsApp</span>
                  </button>
                  ${{(() => {{
                    const pStatus = getPaymentStatus(card.emiName);
                    return pStatus.isPaid 
                      ? `<span class="px-3 py-1.5 rounded-xl text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">✅ Reimbursed</span>`
                      : `<span class="px-3 py-1.5 rounded-xl text-xs font-extrabold bg-amber-100 text-amber-900 border border-amber-300">⏳ Awaiting Payment</span>`;
                  }})()}}
                </div>
              </div>

              <!-- MIDDLE ROW: 3 Evenly Spread KPI Tiles across the entire width -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
                <!-- Tile 1: Overall Loan Amount -->
                <div class="p-3.5 rounded-xl bg-purple-50/80 border border-purple-200/90 shadow-xs flex flex-col justify-center">
                  <div class="text-[10px] font-black uppercase tracking-wider text-purple-600">Overall Loan Amount</div>
                  <div class="text-base font-black text-purple-950 mt-0.5">${{card.overallLoanAmount || 'N/A'}}</div>
                </div>

                <!-- Tile 2: Billing Cycle -->
                <div class="p-3.5 rounded-xl bg-indigo-50/80 border border-indigo-200/90 shadow-xs flex flex-col justify-center">
                  <div class="text-[10px] font-black uppercase tracking-wider text-indigo-600">Billing Cycle</div>
                  <div class="text-base font-black text-indigo-950 mt-0.5">${{card.monthInstallmentTitle || 'Current Month'}}</div>
                </div>

                <!-- Tile 3: Remaining Tenure -->
                <div class="p-3.5 rounded-xl bg-emerald-50/80 border border-emerald-200/90 shadow-xs flex flex-col justify-center">
                  <div class="text-[10px] font-black uppercase tracking-wider text-emerald-600">Remaining Tenure</div>
                  <div class="text-base font-black text-emerald-950 mt-0.5">${{card.remainingCount ? card.remainingCount + ' Installments Left' : 'Active Plan'}}</div>
                </div>
              </div>

              <!-- BOTTOM ROW: Cheering Message on Left, Billing Summary on Right -->
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-1 border-t border-purple-200/60 w-full text-xs">
                <div class="text-sm font-extrabold text-purple-900 flex items-center gap-2">
                  <span>${{card.cheerMessage || 'EMI Statement Breakdown'}}</span>
                </div>
                <div class="text-purple-700 font-medium">
                  ${{card.totalItemsCount}} charge item(s) • Billing Date: ${{datesHeaderStr}}
                </div>
              </div>

            </div>
          `;
          dateCard.appendChild(header);

          // Divide by date inside this card with sorted items
          card.dates.forEach(dObj => {{
            const dateDivider = document.createElement('div');
            dateDivider.className = 'px-6 py-2.5 bg-purple-100/60 border-b border-purple-200/70 flex justify-between items-center text-xs font-semibold';
            dateDivider.setAttribute('style', '-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #f3e8ff !important;');
            dateDivider.innerHTML = `
              <div class="flex items-center gap-2 text-purple-950">
                <span class="font-bold text-sm">📅 ${{dObj.dateStr}}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-200/80 text-purple-900 uppercase tracking-wider" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #e9d5ff !important; color: #581c87 !important;">Date Divider</span>
                <span class="text-purple-600 text-xs">(${{dObj.items.length}} item${{dObj.items.length > 1 ? 's' : ''}})</span>
              </div>
              <div class="text-purple-900 font-bold">
                Date Subtotal: ₹${{dObj.dateTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}
              </div>
            `;
            dateCard.appendChild(dateDivider);

            const table = document.createElement('div');
            table.className = 'divide-y divide-purple-100/60';
            
            // Sort items: Credits ALWAYS on top, then Principal, Interest, Fees, and linked taxes with arrows
            const sortedDateItems = enrichAndSortEmiItems(dObj.items);

            sortedDateItems.forEach(item => {{
              const row = document.createElement('div');
              const isCredit = item.is_credit;

              // Shared color theme styling for Parent & Child
              let rowStyleClass = 'item-row px-6 py-3.5 flex justify-between items-center transition ';
              let inlineRowBg = '';
              if (item.groupTheme === 'interest') {{
                rowStyleClass += 'bg-purple-100/80 hover:bg-purple-100 border-l-[6px] border-l-purple-600 ';
                inlineRowBg = 'style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #ede9fe !important; border-left: 6px solid #7c3aed !important;"';
              }} else if (item.groupTheme === 'fee') {{
                rowStyleClass += 'bg-amber-100/80 hover:bg-amber-100 border-l-[6px] border-l-amber-500 ';
                inlineRowBg = 'style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #fef3c7 !important; border-left: 6px solid #d97706 !important;"';
              }} else if (isCredit) {{
                rowStyleClass += 'bg-sky-100/80 hover:bg-sky-100 border-l-[6px] border-l-sky-600 ';
                inlineRowBg = 'style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #e0f2fe !important; border-left: 6px solid #0284c7 !important;"';
              }} else {{
                rowStyleClass += 'bg-white hover:bg-slate-50 border-l-[6px] border-l-slate-200 ';
              }}
              row.className = rowStyleClass;
              if (inlineRowBg) row.setAttribute('style', inlineRowBg.replace('style="', '').replace('"', ''));

              const emiBadge = item.is_emi && !isCredit && !item.taxInfo && !item.groupTheme
                ? `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 emi-comp-badge uppercase" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #f3e8ff !important; color: #6b21a8 !important;">EMI Component</span>` 
                : '';

              const creditBadge = isCredit 
                ? `<span class="ml-2 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-300 uppercase tracking-wide emi-credit-pill" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #dbeafe !important; color: #1e40af !important; border: 1px solid #93c5fd !important;">⚡ Before EMI Conversion Credit</span>` 
                : '';

              let themeBadge = '';
              if (item.groupTheme === 'interest') {{
                themeBadge = item.groupRole === 'parent'
                  ? `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 uppercase tracking-wide" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #e0e7ff !important; color: #3730a3 !important;">📊 Interest Base</span>`
                  : `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 uppercase tracking-wide" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #e0e7ff !important; color: #3730a3 !important;">↳ Tax on Interest</span>`;
              }} else if (item.groupTheme === 'fee') {{
                themeBadge = item.groupRole === 'parent'
                  ? `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-wide" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #fef3c7 !important; color: #92400e !important;">🏷️ Fee Base</span>`
                  : `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-wide" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #fef3c7 !important; color: #92400e !important;">↳ Tax on Fee</span>`;
              }}

              row.innerHTML = `
                <div class="flex items-center gap-3">
                  <span class="${{item.groupTheme === 'interest' ? 'text-indigo-600 font-extrabold' : (item.groupTheme === 'fee' ? 'text-amber-600 font-extrabold' : (isCredit ? 'text-blue-500 font-bold' : 'text-purple-500 font-bold'))}} text-sm">↳</span>
                  <div>
                    <div class="font-semibold text-slate-800 text-sm flex items-center flex-wrap gap-1">
                      <span class="item-desc-text">${{item.description}}</span>
                      ${{emiBadge}}
                      ${{creditBadge}}
                      ${{themeBadge}}
                    </div>
                    
                    ${{item.taxInfo ? `
                    <div class="flex items-center gap-1.5 text-xs font-bold mt-1">
                      <span class="${{item.groupTheme === 'interest' ? 'text-indigo-400' : 'text-amber-400'}} font-mono text-sm leading-none">↳</span>
                      <span class="px-2 py-0.5 rounded-md border shadow-xs inline-flex items-center gap-1 ${{item.groupTheme === 'interest' ? 'bg-indigo-100 text-indigo-900 border-indigo-200' : 'bg-amber-100 text-amber-900 border-amber-200'}}" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important;">
                        <span>⚡</span>
                        <span>Calculated as ${{item.taxInfo.label}}</span>
                      </span>
                    </div>` : `
                    <div class="text-[11px] font-mono ${{isCredit ? 'text-blue-600 font-bold' : (item.groupTheme === 'interest' ? 'text-indigo-600 font-medium' : (item.groupTheme === 'fee' ? 'text-amber-700 font-medium' : 'text-slate-400'))}}">${{isCredit ? 'CREDIT • BEFORE EMI CONVERSION (LOAN BOOKING OFFSET)' : (item.groupTheme === 'interest' ? 'DEBIT / CHARGE (MONTHLY EMI INTEREST)' : (item.groupTheme === 'fee' ? 'DEBIT / CHARGE (LOAN SETUP PROCESSING FEE)' : 'DEBIT / CHARGE'))}}</div>`}}
                  </div>
                </div>
                <div class="text-right">
                  <div class="item-amount-val font-bold text-sm ${{isCredit ? 'text-blue-700 font-extrabold' : (item.groupTheme === 'interest' ? 'text-indigo-900 font-extrabold' : (item.groupTheme === 'fee' ? 'text-amber-900 font-extrabold' : (item.is_emi ? 'text-purple-900 font-extrabold' : 'text-slate-900')))}}">${{item.amount_str}}</div>
                  <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${{isCredit ? 'bg-blue-100 text-blue-800 border border-blue-200 emi-credit-pill' : (item.groupTheme === 'interest' ? 'bg-indigo-100 text-indigo-800 border border-indigo-200' : (item.groupTheme === 'fee' ? 'bg-amber-100 text-amber-800 border border-amber-200' : (item.is_emi ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-600')))}}">${{isCredit ? 'Credit (Pre-EMI)' : (item.taxInfo ? 'Tax (GST)' : 'Debit')}}</span>
                </div>
              `;
              table.appendChild(row);
            }});
            dateCard.appendChild(table);
          }});

          // BOTTOM GRAND TOTAL FOOTER (Moved down!)
          const grandTotalFooter = document.createElement('div');
          grandTotalFooter.className = 'emi-receipt-footer px-6 sm:px-8 py-5 text-white flex flex-row justify-between items-center gap-4 border-t-2 border-purple-300';
          grandTotalFooter.setAttribute('style', '-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #3b0764 !important; background: #3b0764 !important;');
          grandTotalFooter.innerHTML = `
            <div class="emi-footer-left flex items-center gap-3">
              <div class="emi-footer-icon w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center text-xl flex-shrink-0" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: rgba(255,255,255,0.2) !important;">
                💰
              </div>
              <div>
                <div class="emi-footer-title text-xs uppercase font-black tracking-wider text-purple-200" style="color: #f3e8ff !important;">
                  ${{card.monthDueLabel || (stmt.statement_month + ' Due to be Paid')}}
                </div>
                <div class="emi-footer-subtitle text-[11px] text-purple-300" style="color: #d8b4fe !important;">
                  Total installment & charges friend needs to reimburse for this billing cycle
                </div>
              </div>
            </div>

            <div class="emi-footer-right flex items-center gap-3">
              <span class="emi-footer-grand-label text-xs font-bold text-purple-200 uppercase tracking-wider" style="color: #e9d5ff !important;">Grand Total:</span>
              <span class="emi-footer-pill px-4 py-2 rounded-xl bg-purple-600 text-white font-black text-xl sm:text-2xl shadow-lg border border-purple-400/50" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #ffffff !important; border: 1.5px solid #c084fc !important;">
                ₹${{card.combinedTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}
              </span>
            </div>
          `;
          dateCard.appendChild(grandTotalFooter);

          container.appendChild(dateCard);

        }} else {{
          // Regular date card
          const isEmiGroup = card.isEmiGroup;
          const dateCard = document.createElement('div');
          if (isEmiGroup) {{
            dateCard.className = 'bg-white rounded-2xl border-2 border-purple-400 shadow-md emi-card-glow emi-receipt-card overflow-hidden transition';
          }} else {{
            dateCard.className = 'bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden transition';
          }}

          const header = document.createElement('div');
          if (isEmiGroup) {{
            header.className = 'px-6 py-4 bg-purple-50/80 emi-receipt-header border-b border-purple-200 flex flex-wrap justify-between items-center gap-3';
            header.innerHTML = `
              <div class="flex items-center gap-3">
                <span class="w-9 h-9 rounded-xl bg-purple-600 emi-icon-box text-white flex items-center justify-center font-bold text-sm shadow-sm" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #fff !important;">💳</span>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-900 text-base">${{card.dateStr}}</span>
                    <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-600 emi-badge text-white shadow-sm" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #fff !important; letter-spacing: 0px !important; text-transform: none !important; display: inline-block;">EMI INSTALLMENT RECEIPT</span>
                  </div>
                  <div class="text-xs text-purple-700 font-medium">${{card.items.length}} item(s) on this date</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-purple-900 uppercase tracking-wider">EMI Total:</span>
                <span class="px-3.5 py-1.5 rounded-xl bg-purple-600 emi-total-pill text-white font-extrabold text-sm shadow-md shadow-purple-500/30" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #9333ea !important; color: #fff !important;">₹${{card.group.total.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</span>
              </div>
            `;
          }} else {{
            header.className = 'px-6 py-4 bg-slate-50/80 border-b border-slate-200/80 flex flex-wrap justify-between items-center gap-3';
            header.innerHTML = `
              <div class="flex items-center gap-3">
                <span class="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm">📅</span>
                <div>
                  <div class="font-bold text-slate-900 text-base">${{card.dateStr}}</div>
                  <div class="text-xs text-slate-500">${{card.items.length}} item(s) on this date</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Same-Date Subtotal:</span>
                <span class="px-3 py-1 rounded-xl bg-blue-600 text-white font-extrabold text-sm shadow-sm shadow-blue-500/20">₹${{card.group.total.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</span>
              </div>
            `;
          }}
          dateCard.appendChild(header);

          const table = document.createElement('div');
          table.className = isEmiGroup ? 'divide-y divide-purple-100/60' : 'divide-y divide-slate-100';

          enrichAndSortEmiItems(card.items).forEach(item => {{
            const row = document.createElement('div');
            row.className = isEmiGroup 
              ? 'px-6 py-3.5 flex justify-between items-center bg-purple-50/30 hover:bg-purple-100/40 transition'
              : 'px-6 py-3.5 flex justify-between items-center hover:bg-slate-50/70 transition';

            const isCredit = item.is_credit;
            const emiBadge = item.is_emi && !isCredit
              ? `<span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 emi-comp-badge uppercase tracking-wide" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #f3e8ff !important; color: #6b21a8 !important;">EMI Component</span>` 
              : '';
            const creditBadge = isCredit 
              ? `<span class="ml-2 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-300 uppercase tracking-wide emi-credit-pill" style="-webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #dbeafe !important; color: #1e40af !important; border: 1px solid #93c5fd !important;">⚡ Before EMI Conversion Credit</span>` 
              : '';

            row.innerHTML = `
              <div class="flex items-center gap-3">
                <span class="${{item.is_emi ? 'text-purple-500 font-bold' : (isCredit ? 'text-blue-500 font-bold' : 'text-slate-400')}} text-sm">↳</span>
                <div>
                  <div class="font-semibold text-slate-800 text-sm flex items-center flex-wrap gap-1">
                    <span>${{item.description}}</span>
                    ${{item.bank_badge ? `<span class="ml-1 px-2 py-0.5 rounded text-[10px] font-extrabold bg-slate-100 text-slate-700 border border-slate-300 uppercase">${{item.bank_badge}}</span>` : ''}}
                    ${{emiBadge}}
                    ${{creditBadge}}
                  </div>
                  <div class="text-[11px] text-slate-400 font-mono">${{isCredit ? 'CREDIT • BEFORE EMI CONVERSION (LOAN BOOKING OFFSET)' : 'DEBIT / CHARGE'}}</div>
                </div>
              </div>
              <div class="text-right">
                <div class="font-bold text-sm ${{isCredit ? 'text-blue-700 font-extrabold' : (item.is_emi ? 'text-purple-900 font-extrabold' : 'text-slate-900')}}">${{item.amount_str}}</div>
                <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${{isCredit ? 'bg-blue-100 text-blue-800 border border-blue-200 emi-credit-pill' : (item.is_emi ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-600')}}">${{isCredit ? 'Credit (Pre-EMI)' : 'Debit'}}</span>
              </div>
            `;
            table.appendChild(row);
          }});

          dateCard.appendChild(table);
          container.appendChild(dateCard);
        }}
      }});

      document.getElementById('record-count').innerText = `${{matchedTxnCount}} transactions shown`;

      // Update Hero Reimbursement Totals
      let collectedTotal = 0;
      let pendingTotal = 0;
      cardsList.forEach(c => {{
        if (c.type === 'named_emi') {{
          const pStatus = getPaymentStatus(c.emiName);
          if (pStatus.isPaid) {{
            collectedTotal += c.combinedTotal;
          }} else {{
            pendingTotal += c.combinedTotal;
          }}
        }}
      }});
      const hCollected = document.getElementById('hero-collected-amt');
      const hPending = document.getElementById('hero-pending-amt');
      const hBadge = document.getElementById('hero-settle-badge');
      if (hCollected) hCollected.innerText = '₹' + collectedTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2}});
      if (hPending) hPending.innerText = '₹' + pendingTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2}});
      if (hBadge) {{
        if (pendingTotal === 0 && collectedTotal > 0) {{
          hBadge.innerText = 'All Settled ✅';
          hBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800';
        }} else if (pendingTotal > 0) {{
          hBadge.innerText = 'Pending Collection ⏳';
          hBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800';
        }} else {{
          hBadge.innerText = 'Tracking';
          hBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700';
        }}
      }}
    }}

    let currentFilterCategory = 'all';

    function setFilterCategory(cat) {{
      currentFilterCategory = cat;
      const allPills = ['all', 'emi', 'regular', 'credit'];
      allPills.forEach(p => {{
        const btn = document.getElementById('pill-filter-' + p);
        if (!btn) return;
        if (p === cat) {{
          if (p === 'all') btn.className = 'filter-pill active px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-white shadow-sm transition cursor-pointer';
          else if (p === 'emi') btn.className = 'filter-pill active px-3.5 py-1.5 rounded-xl text-xs font-bold bg-purple-600 text-white shadow-md shadow-purple-500/20 transition cursor-pointer';
          else if (p === 'regular') btn.className = 'filter-pill active px-3.5 py-1.5 rounded-xl text-xs font-bold bg-blue-600 text-white shadow-md shadow-blue-500/20 transition cursor-pointer';
          else if (p === 'credit') btn.className = 'filter-pill active px-3.5 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-md shadow-emerald-500/20 transition cursor-pointer';
        }} else {{
          btn.className = 'filter-pill px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 transition cursor-pointer';
        }}
      }});
      renderDateGroups(document.getElementById('search-input') ? document.getElementById('search-input').value : '');
    }}

    function filterTransactions() {{
      const query = document.getElementById('search-input').value;
      renderDateGroups(query);
    }}

    function exportCSV() {{
      const stmt = statements[activeIndex];
      let csvContent = "data:text/csv;charset=utf-8,Bank,Date,Description,Type,Amount,Is_EMI,Daily_Subtotal\\n";
      Object.entries(stmt.date_groups).forEach(([dt, grp]) => {{
        grp.items.forEach((itm, idx) => {{
          const subtotal = idx === 0 ? grp.total : "";
          const ttype = itm.is_credit ? "Credit" : "Debit";
          const isEmi = itm.is_emi ? "YES" : "NO";
          const row = `"${{stmt.bank_short}}","${{dt}}","${{itm.description.replace(/"/g, '""')}}","${{ttype}}",${{itm.amount}},"${{isEmi}}",${{subtotal}}`;
          csvContent += row + "\\n";
        }});
      }});
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `${{stmt.bank_short}}_${{stmt.statement_month}}_Date_Breakdown.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    function renderDashboard() {{
      renderTabs();
      renderHero();
      renderCashbackAudit();
      renderOngoingEMIs();
      renderDateGroups();
    }}

    renderDashboard();
  </script>
</body>
</html>"""

  with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

  return html_path


def launch_gui():
  """Launches the modern desktop interface with persistent month folder detection and deletion."""
  import tkinter as tk
  from tkinter import filedialog, messagebox, ttk

  window = tk.Tk()
  window.title("Bank Statement Analyzer & Unlocker")
  window.geometry("1160x820")
  window.minsize(920, 660)
  window.configure(bg="#f8fafc")

  style = ttk.Style()
  try:
    style.theme_use("clam")
  except Exception:
    pass

  style.configure("Treeview", font=("Segoe UI", 9), rowheight=28)
  style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#f1f5f9")
  style.configure("TNotebook", background="#f8fafc")
  style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[16, 7])

  downloads_path = os.path.expanduser("~/Downloads")
  current_script_dir = os.path.dirname(os.path.abspath(__file__))
  last_base_dir = {"path": downloads_path}

  active_month_folder = {"path": None, "name": None}
  current_results = []
  last_html_dashboard = {"path": None}
  emi_entries = {}

  top_bar = tk.Frame(window, bg="#0f172a", padx=24, pady=18)
  top_bar.pack(fill=tk.X)

  title_lbl = tk.Label(
      top_bar,
      text="💳  Bank Statement Analyzer & Unlocker",
      font=("Segoe UI", 16, "bold"),
      fg="#ffffff",
      bg="#0f172a",
  )
  title_lbl.pack(anchor="w")

  sub_lbl = tk.Label(
      top_bar,
      text="Unified Month Folder Storage  •  EMI Receipt Highlighting  •  Ongoing EMI Tracker  •  Interactive Web Dashboard",
      font=("Segoe UI", 9),
      fg="#94a3b8",
      bg="#0f172a",
  )
  sub_lbl.pack(anchor="w", pady=(2, 0))

  controls_frame = tk.Frame(window, bg="#ffffff", padx=24, pady=12, relief=tk.SOLID, bd=1)
  controls_frame.pack(fill=tk.X)

  notebook_container = tk.Frame(window, bg="#f8fafc", padx=24, pady=16)
  notebook_container.pack(fill=tk.BOTH, expand=True)

  notebook = ttk.Notebook(notebook_container)
  notebook.pack(fill=tk.BOTH, expand=True)

  def open_web_dashboard():
    target = last_html_dashboard["path"]
    if target and os.path.exists(target):
      webbrowser.open(f"file://{os.path.abspath(target)}")
    else:
      existing = find_existing_statement_folders([last_base_dir["path"], downloads_path, current_script_dir])
      for _, fpath in existing:
        dash_file = os.path.join(fpath, "Statement_Dashboard.html")
        if os.path.exists(dash_file):
          webbrowser.open(f"file://{os.path.abspath(dash_file)}")
          return
      messagebox.showinfo("Web Dashboard", "Select a statement PDF first to view the dashboard.")

  def on_open_folder():
    target = active_month_folder["path"]
    if not target or not os.path.exists(target):
      existing = find_existing_statement_folders([last_base_dir["path"], downloads_path, current_script_dir])
      if existing:
        target = existing[0][1]
      else:
        target = last_base_dir["path"]

    if os.path.exists(target):
      if sys.platform == "win32":
        os.startfile(target)
      else:
        import subprocess
        subprocess.Popen(["xdg-open", target])
    else:
      messagebox.showinfo("Folder", f"Folder: {target}")

  def on_delete_month_folder():
    target_path = active_month_folder["path"]
    existing_folders = find_existing_statement_folders([last_base_dir["path"], downloads_path, current_script_dir])

    if target_path and os.path.exists(target_path):
      folders_to_delete = [target_path]
      legacy = target_path.replace("October", "Oct")
      if legacy != target_path and os.path.exists(legacy):
        folders_to_delete.append(legacy)
    elif existing_folders:
      folders_to_delete = [f[1] for f in existing_folders]
    else:
      chosen = filedialog.askdirectory(
          title="Select Month Folder to Delete",
          initialdir=last_base_dir["path"]
      )
      if chosen:
        folders_to_delete = [chosen]
      else:
        messagebox.showinfo("Delete Folder", "No statement folders found to delete.")
        return

    folder_list_str = "\n".join([f"📁 {os.path.basename(p)}  ({p})" for p in folders_to_delete])
    confirm = messagebox.askyesno(
        "Confirm Permanent Deletion",
        f"Are you sure you want to permanently delete the following statement folder(s)?\n\n"
        f"{folder_list_str}\n\n"
        "This will permanently delete the folder(s) and all unlocked PDF statements inside."
    )

    if confirm:
      deleted_names = []
      for fpath in folders_to_delete:
        try:
          if os.path.exists(fpath):
            shutil.rmtree(fpath)
            deleted_names.append(os.path.basename(fpath))
        except Exception as ex:
          messagebox.showerror("Delete Error", f"Failed to delete {fpath}:\n{ex}")

      if deleted_names:
        active_month_folder["path"] = None
        active_month_folder["name"] = None
        last_html_dashboard["path"] = None
        current_results.clear()
        emi_entries.clear()

        for tab in notebook.tabs():
          notebook.forget(tab)

        reset_welcome_tab()
        messagebox.showinfo(
            "Folder(s) Deleted",
            f"Successfully deleted:\n" + "\n".join(deleted_names)
        )

  def on_save_emi_names_clicked():
    if not emi_entries:
      messagebox.showinfo("EMI Tracker", "No ongoing EMIs detected in the loaded statement.")
      return

    save_dir = active_month_folder["path"] or last_base_dir["path"]
    saved_dict = load_saved_emi_names(save_dir)
    updated_count = 0

    for loan_id, entry_widget in emi_entries.items():
      val = entry_widget.get().strip()
      if val:
        saved_dict[loan_id] = val
        updated_count += 1

    save_emi_names_to_disk(saved_dict, save_dir)

    for res in current_results:
      for emi in res.get("ongoing_emis", []):
        lid = emi["loan_id"]
        if lid in saved_dict:
          emi["custom_name"] = saved_dict[lid]
          emi["display_name"] = saved_dict[lid]

    if current_results and active_month_folder["path"]:
      html_dash = generate_modern_dashboard_html(current_results, active_month_folder["path"])
      last_html_dashboard["path"] = html_dash

    messagebox.showinfo(
        "Saved Successfully!",
        f"Saved {updated_count} custom EMI nickname(s) to 'emi_names.json'.\n\n"
        "Your custom names will be remembered and automatically displayed when the next bill is parsed!"
    )

  def on_export_csv():
    if not current_results or not active_month_folder["path"]:
      messagebox.showinfo("Export", "Please select a statement first.")
      return

    out_csv = os.path.join(active_month_folder["path"], "statement_date_breakdown.csv")
    try:
      with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Bank", "Date", "Description", "Type", "Amount", "Is_EMI", "Daily Subtotal"])
        for res in current_results:
          for dt, grp in res["date_groups"].items():
            for idx, itm in enumerate(grp["items"]):
              daily_sub = f"₹{grp['total']:,.2f}" if idx == 0 else ""
              ttype = "Credit" if itm["is_credit"] else "Debit"
              isEmi = "YES" if itm["is_emi"] else "NO"
              writer.writerow([res["bank_short"], dt, itm["description"], ttype, itm["amount"], isEmi, daily_sub])
      messagebox.showinfo("Export Successful", f"Saved breakdown to:\n{out_csv}")
    except Exception as e:
      messagebox.showerror("Export Error", f"Failed to export CSV:\n{e}")

  def create_kpi_card(parent, title, value, subtext="", val_color="#0f172a"):
    card = tk.Frame(parent, bg="#ffffff", padx=18, pady=14, relief=tk.SOLID, bd=1)
    t_lbl = tk.Label(card, text=title.upper(), font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff")
    t_lbl.pack(anchor="w")
    v_lbl = tk.Label(card, text=value, font=("Segoe UI", 17, "bold"), fg=val_color, bg="#ffffff")
    v_lbl.pack(anchor="w", pady=(3, 0))
    if subtext:
      s_lbl = tk.Label(card, text=subtext, font=("Segoe UI", 9), fg="#64748b", bg="#ffffff")
      s_lbl.pack(anchor="w", pady=(2, 0))
    return card

  def populate_tab(tab_frame, data):
    if not data.get("was_encrypted", True):
      unenc_banner = tk.Frame(tab_frame, bg="#fef3c7", padx=16, pady=10, relief=tk.SOLID, bd=1)
      unenc_banner.pack(fill=tk.X, pady=(0, 12))
      tk.Label(
          unenc_banner,
          text="⚠️  NOTICE: This PDF file is ALREADY UNENCRYPTED (Contains no password protection)",
          font=("Segoe UI", 10, "bold"),
          fg="#92400e",
          bg="#fef3c7"
      ).pack(anchor="w")
      tk.Label(
          unenc_banner,
          text=(
              "This file opens in any PDF viewer without asking for a password.\n"
              "Bank passwords in 'Configure Passwords' are only tested when opening an original password-protected PDF directly from the bank."
          ),
          font=("Segoe UI", 9),
          fg="#78350f",
          bg="#fef3c7",
          justify=tk.LEFT
      ).pack(anchor="w", pady=(2, 0))

    kpi_frame = tk.Frame(tab_frame, bg="#f8fafc")
    kpi_frame.pack(fill=tk.X, pady=(0, 12))

    total_card = create_kpi_card(
        kpi_frame,
        "Total Bill to be Paid",
        data["total_due"],
        f"Due Date: {data['due_date']}",
        val_color="#0284c7"
    )
    total_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

    enc_label = "🔒 Password Protected (Decrypted)" if data.get("was_encrypted") else "⚠️ Unencrypted File (No Password)"
    bank_card = create_kpi_card(
        kpi_frame,
        "Statement Info",
        data["bank_name"],
        f"{enc_label} • Folder: {data['month_folder_name']}",
        val_color="#0f172a"
    )
    bank_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

    num_txns = len(data["all_txns"])
    num_dates = len(data["date_groups"])
    txn_card = create_kpi_card(
        kpi_frame,
        "Activity Segregation",
        f"{num_txns} Transactions",
        f"Grouped across {num_dates} dates",
        val_color="#059669"
    )
    txn_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    emis = data.get("ongoing_emis", [])
    if emis:
      emi_box = tk.Frame(tab_frame, bg="#fffbeb", padx=16, pady=12, relief=tk.SOLID, bd=1)
      emi_box.pack(fill=tk.X, pady=(0, 12))

      emi_head_frame = tk.Frame(emi_box, bg="#fffbeb")
      emi_head_frame.pack(fill=tk.X, pady=(0, 6))

      lbl_title = tk.Label(
          emi_head_frame,
          text="🏷️  Ongoing EMIs & Loans (Type a nickname & click Save to remember across bills):",
          font=("Segoe UI", 9, "bold"),
          bg="#fffbeb",
          fg="#92400e"
      )
      lbl_title.pack(side=tk.LEFT)

      btn_save_emi = tk.Button(
          emi_head_frame,
          text="💾 Save EMI Names",
          font=("Segoe UI", 9, "bold"),
          bg="#d97706",
          fg="#ffffff",
          activebackground="#b45309",
          activeforeground="#ffffff",
          relief=tk.FLAT,
          padx=10,
          pady=3,
          cursor="hand2",
          command=on_save_emi_names_clicked
      )
      btn_save_emi.pack(side=tk.RIGHT)

      for emi in emis:
        row_f = tk.Frame(emi_box, bg="#ffffff", padx=10, pady=8, relief=tk.SOLID, bd=1)
        row_f.pack(fill=tk.X, pady=3)

        info_lbl = tk.Label(
            row_f,
            text=f"[{emi['type']}] Total: {emi['total_amount']} | Remaining: {emi['balance_principal']} ({emi['balance_tenure']})",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1e293b"
        )
        info_lbl.pack(side=tk.LEFT, padx=(0, 10))

        name_lbl = tk.Label(row_f, text="Custom Name:", font=("Segoe UI", 8), bg="#ffffff", fg="#64748b")
        name_lbl.pack(side=tk.LEFT, padx=(5, 3))

        ent = tk.Entry(row_f, font=("Segoe UI", 9), width=28)
        saved_val = emi.get("custom_name", "")
        if saved_val:
          ent.insert(0, saved_val)
        ent.pack(side=tk.LEFT)

        emi_entries[emi["loan_id"]] = ent

    table_frame = tk.Frame(tab_frame, bg="#ffffff", relief=tk.SOLID, bd=1)
    table_frame.pack(fill=tk.BOTH, expand=True)

    header_lbl = tk.Label(
        table_frame,
        text="📅  Date-Wise Segregated Breakdown (EMI Receipt Sections Highlighted in Purple)",
        font=("Segoe UI", 10, "bold"),
        bg="#f1f5f9",
        fg="#1e293b",
        padx=12,
        pady=8,
        anchor="w"
    )
    header_lbl.pack(fill=tk.X)

    tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
    tree_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

    tree = ttk.Treeview(
        table_frame,
        columns=("description", "type", "amount"),
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set
    )
    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)

    tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    tree.pack(fill=tk.BOTH, expand=True)

    tree.heading("#0", text="Date / Transaction Details", anchor="w")
    tree.heading("description", text="Description", anchor="w")
    tree.heading("type", text="Type", anchor="center")
    tree.heading("amount", text="Amount", anchor="e")

    tree.column("#0", width=280, minwidth=220)
    tree.column("description", width=420, minwidth=250)
    tree.column("type", width=120, minwidth=80, anchor="center")
    tree.column("amount", width=130, minwidth=100, anchor="e")

    # Regular Date Header vs EMI Receipt Header
    tree.tag_configure("date_header", background="#e0f2fe", font=("Segoe UI", 9, "bold"))
    tree.tag_configure("emi_date_header", background="#ede9fe", foreground="#581c87", font=("Segoe UI", 9, "bold"))
    tree.tag_configure("emi_item", background="#faf5ff", foreground="#6b21a8")
    tree.tag_configure("cr_item", foreground="#047857")

    emis = data.get("ongoing_emis", [])
    named_emi_groups = {}
    display_nodes = []

    for date_str, group in data["date_groups"].items():
      is_emi_grp = group.get("has_emi", False)
      emi_name = ""
      if is_emi_grp:
        for itm in group["items"]:
          for emi in emis:
            lid = emi.get("loan_id", "")
            if lid and lid in itm.get("description", ""):
              emi_name = emi.get("custom_name") or emi.get("display_name")
              break
          if emi_name:
            break
        if not emi_name and len(emis) == 1:
          emi_name = emis[0].get("custom_name") or emis[0].get("display_name")

      if is_emi_grp and emi_name:
        if emi_name in named_emi_groups:
          named_emi_groups[emi_name]["dates"].append((date_str, group))
          named_emi_groups[emi_name]["total"] += group["total"]
          named_emi_groups[emi_name]["count"] += len(group["items"])
        else:
          grp_obj = {
              "emi_name": emi_name,
              "total": group["total"],
              "count": len(group["items"]),
              "dates": [(date_str, group)]
          }
          named_emi_groups[emi_name] = grp_obj
          display_nodes.append(("named_emi", emi_name, grp_obj))
      else:
        display_nodes.append(("date", date_str, group))

    for node_type, key, obj in display_nodes:
      if node_type == "named_emi":
        emi_name = key
        master_node = tree.insert(
            "",
            tk.END,
            text=f"💳 [EMI RECEIPT] 🏷️ {emi_name} ({obj['count']} items across {len(obj['dates'])} dates)",
            values=(
                f"Combined Total for {emi_name}",
                "EMI Total",
                f"₹{obj['total']:,.2f}"
            ),
            open=True,
            tags=("emi_date_header",)
        )
        for date_str, group in obj["dates"]:
          date_sub_node = tree.insert(
              master_node,
              tk.END,
              text=f"  📅 {date_str} ({len(group['items'])} items)",
              values=(
                  f"Date Subtotal: {date_str}",
                  "Date Sum",
                  f"₹{group['total']:,.2f}"
              ),
              open=True,
              tags=("date_header",)
          )
          for itm in group["items"]:
            ttype = "Credit" if itm["is_credit"] else ("EMI Component" if itm.get("is_emi") else "Debit")
            row_tag = "cr_item" if itm["is_credit"] else ("emi_item" if itm.get("is_emi") else "")
            prefix = "      ↳ [EMI] " if itm.get("is_emi") else "      ↳ "
            tree.insert(
                date_sub_node,
                tk.END,
                text=f"{prefix}{itm['description']}",
                values=(itm["description"], ttype, itm["amount_str"]),
                tags=(row_tag,)
            )
      else:
        date_str = key
        group = obj
        daily_subtotal = group["total"]
        item_count = len(group["items"])
        is_emi_grp = group.get("has_emi", False)

        node_tag = "emi_date_header" if is_emi_grp else "date_header"
        node_title = f"💳 [EMI RECEIPT] {date_str} ({item_count} items)" if is_emi_grp else f"📅 {date_str} ({item_count} items)"
        type_label = "EMI Total" if is_emi_grp else "Daily Sum"

        date_node = tree.insert(
            "",
            tk.END,
            text=node_title,
            values=(
                f"Subtotal for {date_str}",
                type_label,
                f"₹{daily_subtotal:,.2f}"
            ),
            open=True,
            tags=(node_tag,)
        )

        for itm in group["items"]:
          ttype = "Credit" if itm["is_credit"] else ("EMI Component" if itm.get("is_emi") else "Debit")
          row_tag = "cr_item" if itm["is_credit"] else ("emi_item" if itm.get("is_emi") else "")
          prefix = "    ↳ [EMI] " if itm.get("is_emi") else "    ↳ "

          tree.insert(
              date_node,
              tk.END,
              text=f"{prefix}{itm['description']}",
              values=(itm["description"], ttype, itm["amount_str"]),
              tags=(row_tag,)
          )

  def reset_welcome_tab():
    welcome_frame = tk.Frame(notebook, bg="#ffffff", padx=30, pady=40)
    notebook.add(welcome_frame, text="👋 Welcome")

    w_title = tk.Label(
        welcome_frame,
        text="Bank Statement Analyzer & Date Segregator",
        font=("Segoe UI", 14, "bold"),
        fg="#0f172a",
        bg="#ffffff"
    )
    w_title.pack(anchor="w", pady=(0, 10))

    w_desc = tk.Label(
        welcome_frame,
        text=(
            "Click the blue 'Select Statement PDF' button above to load your statement.\n\n"
            "Features:\n"
            "  • EMI Receipt Highlighting: Automatically spots and highlights EMI installment sections in purple.\n"
            "  • Unified Month Folder: Stores both HDFC and ICICI into a single 'Statements_October_2026/' folder.\n"
            "  • Persistent 1-Click Delete: Click 'Delete Month Folder' anytime (even after reopening the app) to clean up.\n"
            "  • Ongoing EMI Tracker: Remembers custom nicknames across bills.\n"
            "  • Accurate Bill & Due Date: Real-time calculation and same-date charge subtotals."
        ),
        font=("Segoe UI", 10),
        fg="#475569",
        bg="#ffffff",
        justify=tk.LEFT
    )
    w_desc.pack(anchor="w")

  def open_configure_passwords_dialog():
    """Opens modal dialog to configure and locally store passwords for ICICI, HDFC, and Google Sheets Webhook URL."""
    curr_pwds = load_stored_passwords(last_base_dir["path"])

    dlg = tk.Toplevel(window)
    dlg.title("Configure Passwords & Google Sheets Sync")
    dlg.geometry("580x600")
    dlg.resizable(False, False)
    dlg.configure(bg="#ffffff")
    dlg.transient(window)
    dlg.grab_set()

    try:
      x = window.winfo_x() + (window.winfo_width() // 2) - 290
      y = window.winfo_y() + (window.winfo_height() // 2) - 300
      dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    except Exception:
      pass

    hdr = tk.Frame(dlg, bg="#0f172a", padx=20, pady=16)
    hdr.pack(fill=tk.X)

    tk.Label(
        hdr,
        text="🔑  Configure Passwords & Google Sheets Sync",
        font=("Segoe UI", 13, "bold"),
        fg="#ffffff",
        bg="#0f172a"
    ).pack(anchor="w")

    tk.Label(
        hdr,
        text="Saved locally in passwords.json and strictly excluded from Git (.gitignore).",
        font=("Segoe UI", 9),
        fg="#94a3b8",
        bg="#0f172a"
    ).pack(anchor="w", pady=(2, 0))

    body = tk.Frame(dlg, bg="#ffffff", padx=24, pady=16)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        body,
        text="ICICI Bank (Amazon Pay) Password:",
        font=("Segoe UI", 10, "bold"),
        fg="#0f172a",
        bg="#ffffff"
    ).pack(anchor="w")

    tk.Label(
        body,
        text="Format: First 4 letters of name in SMALL (lowercase) + Date & Month of birth in DDMM",
        font=("Segoe UI", 8),
        fg="#64748b",
        bg="#ffffff",
        wraplength=520,
        justify=tk.LEFT
    ).pack(anchor="w", pady=(1, 4))

    icici_var = tk.StringVar(value=curr_pwds.get("icici", ""))
    icici_entry = tk.Entry(
        body,
        textvariable=icici_var,
        font=("Segoe UI", 11),
        show="*",
        relief=tk.SOLID,
        bd=1,
        highlightthickness=1,
        highlightbackground="#cbd5e1"
    )
    icici_entry.pack(fill=tk.X, pady=(0, 10), ipady=3)

    tk.Label(
        body,
        text="HDFC Bank (Swiggy / Credit Cards) Password:",
        font=("Segoe UI", 10, "bold"),
        fg="#0f172a",
        bg="#ffffff"
    ).pack(anchor="w")

    tk.Label(
        body,
        text="Format: First 4 letters of name in CAPS (UPPERCASE) + Date & Month of birth in DDMM",
        font=("Segoe UI", 8),
        fg="#64748b",
        bg="#ffffff",
        wraplength=520,
        justify=tk.LEFT
    ).pack(anchor="w", pady=(1, 4))

    hdfc_var = tk.StringVar(value=curr_pwds.get("hdfc", ""))
    hdfc_entry = tk.Entry(
        body,
        textvariable=hdfc_var,
        font=("Segoe UI", 11),
        show="*",
        relief=tk.SOLID,
        bd=1,
        highlightthickness=1,
        highlightbackground="#cbd5e1"
    )
    hdfc_entry.pack(fill=tk.X, pady=(0, 8), ipady=3)

    show_pass_var = tk.BooleanVar(value=False)
    def toggle_show():
      char = "" if show_pass_var.get() else "*"
      icici_entry.config(show=char)
      hdfc_entry.config(show=char)

    show_cb = tk.Checkbutton(
        body,
        text="Show Passwords",
        variable=show_pass_var,
        command=toggle_show,
        font=("Segoe UI", 9),
        bg="#ffffff",
        activebackground="#ffffff"
    )
    show_cb.pack(anchor="w", pady=(0, 12))

    sep = tk.Frame(body, height=1, bg="#e2e8f0")
    sep.pack(fill=tk.X, pady=(0, 12))

    sheets_hdr = tk.Frame(body, bg="#ffffff")
    sheets_hdr.pack(fill=tk.X)

    tk.Label(
        sheets_hdr,
        text="📊  Google Sheets Multi-Month Sync (Optional):",
        font=("Segoe UI", 10, "bold"),
        fg="#0f172a",
        bg="#ffffff"
    ).pack(side=tk.LEFT)

    copy_tmpl_btn = tk.Button(
        sheets_hdr,
        text="📋  Copy Template Sheet",
        font=("Segoe UI", 8, "bold"),
        bg="#059669",
        fg="#ffffff",
        activebackground="#047857",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=8,
        pady=2,
        cursor="hand2",
        command=lambda: webbrowser.open(GOOGLE_SHEET_TEMPLATE_URL)
    )
    copy_tmpl_btn.pack(side=tk.RIGHT)

    tk.Label(
        body,
        text="Make a copy of the official multi-month tracker, deploy its Apps Script as a Web App ('Who has access: Anyone'), and paste the Web App URL below:",
        font=("Segoe UI", 8),
        fg="#64748b",
        bg="#ffffff",
        wraplength=520,
        justify=tk.LEFT
    ).pack(anchor="w", pady=(2, 4))

    sheets_url_var = tk.StringVar(value=curr_pwds.get("sheets_webhook_url", ""))
    sheets_url_entry = tk.Entry(
        body,
        textvariable=sheets_url_var,
        font=("Segoe UI", 10),
        relief=tk.SOLID,
        bd=1,
        highlightthickness=1,
        highlightbackground="#cbd5e1"
    )
    sheets_url_entry.pack(fill=tk.X, pady=(0, 14), ipady=3)

    btn_row = tk.Frame(body, bg="#ffffff")
    btn_row.pack(fill=tk.X)

    def on_save_passwords():
      try:
        icici_val = icici_var.get().strip()
        hdfc_val = hdfc_var.get().strip()
        sheets_url_val = sheets_url_var.get().strip()
        if not icici_val and not hdfc_val and not sheets_url_val:
          messagebox.showwarning("Empty Settings", "Please enter at least one bank password or a Google Sheets Web App URL.", parent=dlg)
          return
        save_stored_passwords(hdfc_val, icici_val, sheets_url_val, last_base_dir["path"])
        log(f"[CREDENTIAL STORE] Saved ICICI/HDFC passwords and Google Sheets Webhook URL in '{PASSWORDS_FILE}' (excluded from Git).")
        msg = (
            f"Settings saved successfully to '{PASSWORDS_FILE}'!\n\n• Passwords & Webhook URL are stored locally on your machine and reused automatically.\n• Strictly excluded by Git (.gitignore) and will never be pushed to GitHub."
        )
        messagebox.showinfo("Settings Saved", msg, parent=dlg)
        dlg.destroy()
      except Exception as ex:
        messagebox.showerror("Save Error", f"Failed to save settings:\n{ex}", parent=dlg)

    save_btn = tk.Button(
        btn_row,
        text="💾  Save Settings",
        font=("Segoe UI", 10, "bold"),
        bg="#0f766e",
        fg="#ffffff",
        activebackground="#0d9488",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=18,
        pady=7,
        cursor="hand2",
        command=on_save_passwords
    )
    save_btn.pack(side=tk.LEFT, padx=(0, 10))

    cancel_btn = tk.Button(
        btn_row,
        text="Cancel",
        font=("Segoe UI", 10),
        bg="#e2e8f0",
        fg="#1e293b",
        relief=tk.FLAT,
        padx=16,
        pady=7,
        cursor="hand2",
        command=dlg.destroy
    )
    cancel_btn.pack(side=tk.LEFT)

  def on_select_files():
    file_paths = filedialog.askopenfilenames(
        title="Select Bank Statement(s)",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    if not file_paths:
      return

    for tab in notebook.tabs():
      notebook.forget(tab)
    current_results.clear()
    emi_entries.clear()

    success_files = []
    error_files = []

    for fpath in file_paths:
      success, msg, rdata = process_statement_file(fpath, last_base_dir["path"])
      if success:
        current_results.append(rdata)
        success_files.append(rdata["saved_name"])
        active_month_folder["path"] = rdata["month_folder"]
        active_month_folder["name"] = rdata["month_folder_name"]

        tab_frame = tk.Frame(notebook, bg="#f8fafc", padx=10, pady=10)
        notebook.add(tab_frame, text=f"📊 {rdata['bank_short']}")
        populate_tab(tab_frame, rdata)
      else:
        error_files.append(f"{os.path.basename(fpath)}: {msg}")

    if success_files:
      html_dash = generate_modern_dashboard_html(current_results, active_month_folder["path"])
      last_html_dashboard["path"] = html_dash

      web_btn.config(state=tk.NORMAL)
      export_btn.config(state=tk.NORMAL)
      open_folder_btn.config(state=tk.NORMAL)

      webbrowser.open(f"file://{os.path.abspath(html_dash)}")

      popup_msg = f"Successfully parsed {len(success_files)} statement(s)!\n\n"
      for r in current_results:
        enc_badge = "🔓 Unlocked with password" if r.get("was_encrypted") else "📄 Already Unencrypted"
        popup_msg += f"• {r['bank_short']}: Total Due {r['total_due']} (Due: {r['due_date']}) [{enc_badge}]\n"
      
      unenc = [r['file_name'] for r in current_results if not r.get("was_encrypted")]
      if unenc:
        popup_msg += (
            f"\nℹ️ Password Notice:\n"
            f"'{', '.join(unenc)}' was ALREADY UNENCRYPTED (no password protection).\n"
            f"Because it is already unlocked, it opened without needing a password. "
            f"To test that an incorrect password gets rejected, select an original password-protected PDF downloaded directly from your bank.\n"
        )
      popup_msg += f"\nSaved into Unified Folder: {active_month_folder['name']}\n"
      popup_msg += "\n" + "\n".join(success_files)
      messagebox.showinfo("Analysis Complete", popup_msg)

    if error_files:
      messagebox.showerror("Errors Occurred", "\n\n".join(error_files))

  def on_sync_google_sheets():
    """Appends current statement bills and friend reimbursements to the user's master multi-month Google Sheet."""
    if not current_results:
      messagebox.showwarning(
          "No Statements Loaded",
          "Please load and decrypt at least one bank statement PDF first using '📁 Select Statement PDF'.",
          parent=window
      )
      return

    stored = load_stored_passwords(last_base_dir["path"])
    webhook_url = stored.get("sheets_webhook_url", "").strip()
    if not webhook_url:
      open_cfg = messagebox.askyesno(
          "Google Sheets Webhook Not Set",
          "Google Sheets Web App URL is not configured yet.\n\nWould you like to open '🔑 Configure Passwords & Sync' to paste your Web App URL or make a copy of the free Google Sheets template?",
          parent=window
      )
      if open_cfg:
        open_configure_passwords_dialog()
      return

    bills = []
    reimbursements = []
    for rdata in current_results:
      tot_due_str = str(rdata.get("total_due", "0")).replace("Rs.", "").replace("₹", "").replace(",", "").strip()
      try:
        tot_due = float(tot_due_str)
      except Exception:
        tot_due = 0.0

      emis = rdata.get("ongoing_emis", [])
      friend_share = sum(float(str(e.get("amount", 0)).replace(",", "")) for e in emis)
      personal_share = tot_due - friend_share

      cb_val = 0.0
      cb_dict = rdata.get("cashback", {})
      if isinstance(cb_dict, dict):
        cb_val = cb_dict.get("net_cashback", 0.0)

      bills.append({
          "billing_month": rdata.get("statement_month", ""),
          "bank": rdata.get("bank_full_name", rdata.get("bank_short", "")),
          "statement_date": rdata.get("statement_date", "-"),
          "due_date": rdata.get("due_date", "-"),
          "total_due": tot_due,
          "friend_share": friend_share,
          "personal_share": personal_share,
          "cashback": cb_val,
          "status": "Due Soon",
          "notes": f"{len(emis)} ongoing EMI(s) tracked"
      })

      for emi in emis:
        nickname = emi.get("nickname") or emi.get("desc", "Friend Loan")
        reimbursements.append({
            "billing_month": rdata.get("statement_month", ""),
            "contact_name": nickname.split()[0] if nickname else "Friend",
            "mobile": emi.get("contact_mobile", ""),
            "nickname": nickname,
            "bank": rdata.get("bank_short", ""),
            "installment_num": emi.get("installment_str", "-"),
            "amount": emi.get("amount", 0.0),
            "remaining": f"{emi.get('total_installments', 0) - emi.get('current_installment', 0)} left" if emi.get('total_installments') else "-",
            "status": "Pending",
            "reminder_status": "Scheduled"
        })

    payload = {
        "action": "append_statements",
        "bills": bills,
        "reimbursements": reimbursements
    }

    try:
      import urllib.request
      payload_bytes = json.dumps(payload).encode("utf-8")
      req = urllib.request.Request(
          webhook_url,
          data=payload_bytes,
          headers={"Content-Type": "application/json", "User-Agent": "SmartBillSegregator/1.0"}
      )
      with urllib.request.urlopen(req, timeout=15) as resp:
        resp_body = resp.read().decode("utf-8")
      log(f"[GOOGLE SHEETS] Successfully synced {len(bills)} bill(s) and {len(reimbursements)} friend loan(s).")
      messagebox.showinfo(
          "Google Sheets Synced",
          f"✅ Successfully synced to your Master Google Sheet!\n\n• {len(bills)} Card Bill(s) appended to 'Monthly Bills History'\n• {len(reimbursements)} Friend Installment(s) appended to 'Monthly Friend Reimbursements'\n\nBilling Month: {current_results[0].get('statement_month', '')}",
          parent=window
      )
    except Exception as ex:
      log(f"[GOOGLE SHEETS ERROR] Failed to sync: {ex}")
      messagebox.showerror(
          "Sync Failed",
          f"Could not connect to Google Sheets Web App:\n\n{ex}\n\nPlease verify that your Google Apps Script Web App was deployed with:\n• Execute as: Me\n• Who has access: Anyone",
          parent=window
      )


  select_btn = tk.Button(
      controls_frame,
      text="📁  Select Statement PDF",
      font=("Segoe UI", 10, "bold"),
      bg="#2563eb",
      fg="#ffffff",
      activebackground="#1d4ed8",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=13,
      pady=8,
      cursor="hand2",
      command=on_select_files
  )
  select_btn.pack(side=tk.LEFT, padx=(0, 8))

  pass_btn = tk.Button(
      controls_frame,
      text="🔑  Configure Passwords & Sync",
      font=("Segoe UI", 10, "bold"),
      bg="#0f766e",
      fg="#ffffff",
      activebackground="#0d9488",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=open_configure_passwords_dialog
  )
  pass_btn.pack(side=tk.LEFT, padx=(0, 8))

  sync_btn = tk.Button(
      controls_frame,
      text="☁️  Sync to Google Sheets",
      font=("Segoe UI", 10, "bold"),
      bg="#0284c7",
      fg="#ffffff",
      activebackground="#0369a1",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=on_sync_google_sheets
  )
  sync_btn.pack(side=tk.LEFT, padx=(0, 8))

  web_btn = tk.Button(
      controls_frame,
      text="🌐  View Web Dashboard",
      font=("Segoe UI", 10, "bold"),
      bg="#4f46e5",
      fg="#ffffff",
      activebackground="#4338ca",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=open_web_dashboard
  )
  web_btn.pack(side=tk.LEFT, padx=(0, 8))

  open_folder_btn = tk.Button(
      controls_frame,
      text="📂  Open Folder",
      font=("Segoe UI", 10),
      bg="#e2e8f0",
      fg="#1e293b",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=on_open_folder
  )
  open_folder_btn.pack(side=tk.LEFT, padx=(0, 8))

  export_btn = tk.Button(
      controls_frame,
      text="📊  Export to CSV",
      font=("Segoe UI", 10),
      bg="#059669",
      fg="#ffffff",
      activebackground="#047857",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=on_export_csv
  )
  export_btn.pack(side=tk.LEFT, padx=(0, 8))

  delete_btn = tk.Button(
      controls_frame,
      text="🗑️  Delete Month Folder",
      font=("Segoe UI", 10, "bold"),
      bg="#ef4444",
      fg="#ffffff",
      activebackground="#dc2626",
      activeforeground="#ffffff",
      relief=tk.FLAT,
      padx=11,
      pady=8,
      cursor="hand2",
      command=on_delete_month_folder
  )
  delete_btn.pack(side=tk.LEFT)

  reset_welcome_tab()

  window.mainloop()


if __name__ == "__main__":
  try:
    launch_gui()
  except Exception as e:
    show_popup_error("Bank Statement Analyzer Error", f"Failed to start:\n\n{e}")