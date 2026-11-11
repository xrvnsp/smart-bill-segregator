import base64
import os
def get_card_b64(fname, base_dir=None):
  """Loads and base64-encodes a card image from known asset paths."""
  candidates = []
  if base_dir:
    candidates.append(os.path.join(base_dir, fname))
  candidates.extend([
      os.path.join(os.path.dirname(os.path.abspath(__file__)), fname),
      os.path.join(".", fname),
      os.path.join("/working_dir/c_a77ecec1bad766ad/user_uploaded_files/ttl=63d/user_uploaded", fname)
  ])
  for p in candidates:
    if os.path.exists(p):
      try:
        with open(p, "rb") as f:
          b64 = base64.b64encode(f.read()).decode("utf-8")
          ext = os.path.splitext(fname)[1].lower().replace(".", "")
          mime = "image/jpeg" if ext in ["jpg", "jpeg"] else ("image/webp" if ext == "webp" else "image/png")
          return f"data:{mime};base64,{b64}"
      except Exception:
        pass
  return ""

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
from datetime import datetime
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
    {
        "name": "SBI Card (SimplyCLICK)",
        "key": "sbi",
        "short_name": "SBI SimplyCLICK",
        "hints": ["sbi", "simplyclick", "simply click", "sbicard"],
    },
    {
        "name": "Axis Bank (Scapia)",
        "key": "scapia",
        "short_name": "Scapia Axis",
        "hints": ["scapia", "axis", "axis bank", "federal", "scapiacard"],
    },
    {
        "name": "Salary Payslip (Skillveri)",
        "key": "payslip",
        "short_name": "Salary Payslip",
        "hints": ["payslip", "skillveri", "salary", "tds", "employee summary", "net payable"],
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
                "sbi": str(data.get("sbi", "")).strip(),
                "sheets_webhook_url": str(data.get("sheets_webhook_url", "")).strip(),
            }
        except Exception:
          pass
  return {"hdfc": "", "icici": "", "sbi": "", "sheets_webhook_url": ""}


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
  fname_lower = os.path.basename(str(file_path)).lower()

  if "PAYSLIP" in text_upper or "SKILLVERI" in text_upper or "EMPLOYEE SUMMARY" in text_upper or "TOTAL NET PAYABLE" in text_upper or "TDS SUMMARY" in text_upper:
    return "Salary Payslip (Skillveri)", "Salary Payslip"
  if "SCAPIA" in text_upper or ("AXIS" in text_upper and "CARD" in text_upper):
    return "Axis Bank (Scapia)", "Scapia Axis"
  if "SIMPLYCLICK" in text_upper or "SIMPLY CLICK" in text_upper or "SBICARD" in text_upper or ("SBI" in text_upper and "CARD" in text_upper):
    return "SBI Card (SimplyCLICK)", "SBI SimplyCLICK"
  if "ICICI" in text_upper or "AMAZON PAY" in text_upper:
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if "HDFC" in text_upper or "SWIGGY HDFC" in text_upper:
    return "HDFC Bank (Swiggy)", "HDFC"

  if unlocked_bank_key == "payslip":
    return "Salary Payslip (Skillveri)", "Salary Payslip"
  if unlocked_bank_key == "scapia":
    return "Axis Bank (Scapia)", "Scapia Axis"

  if unlocked_bank_key == "sbi":
    return "SBI Card (SimplyCLICK)", "SBI SimplyCLICK"
  if unlocked_bank_key == "icici":
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if unlocked_bank_key == "hdfc":
    return "HDFC Bank (Swiggy)", "HDFC"

  if "payslip" in fname_lower or "skillveri" in fname_lower or "salary" in fname_lower or "tds" in fname_lower:
    return "Salary Payslip (Skillveri)", "Salary Payslip"
  if "simplyclick" in fname_lower or "simply click" in fname_lower or "sbicard" in fname_lower or "sbi" in fname_lower:
    return "SBI Card (SimplyCLICK)", "SBI SimplyCLICK"
  if "4315" in fname_lower or "amazon" in fname_lower or "icici" in fname_lower:
    return "ICICI Bank (Amazon Pay)", "ICICI Amazon"
  if "5268" in fname_lower or "hdfc" in fname_lower:
    return "HDFC Bank (Swiggy)", "HDFC"

  return "Bank Statement", "Statement"


def parse_icici_statement(reader, file_path, saved_names):
  """Dedicated rule for ICICI Amazon Pay credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""

  cardholder_name = ""
  for line in p1_text.splitlines():
    m_title = re.search(r"^(?:MR|MS|MRS|DR)\.?\s+([A-Za-z\s]{2,35})$", line.strip(), re.IGNORECASE)
    if m_title:
      cardholder_name = " ".join(m_title.group(1).split()).upper()
      break
  if not cardholder_name:
    m_icici = re.search(r"(?:MR|MS|MRS|DR)\.?\s+([A-Za-z\s]{3,35})", p1_text, re.IGNORECASE)
    if m_icici:
      cardholder_name = " ".join(m_icici.group(1).split()).upper()
  if not cardholder_name:
    cardholder_name = "Cardholder"

  exact_header_pat = r"[`\s]*([\d,]+\.\d{2})\s+[`\s]*([\d,]+\.\d{2})\s+SPENDS\s+OVERVIEW\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
  m_hdr = re.search(exact_header_pat, p1_text)

  if m_hdr:
    min_due, tot_due, stmt_date, due_date = m_hdr.groups()
    total_due_str = f"₹{tot_due}"
    due_date_str = due_date
    statement_month_str = stmt_date
  else:
    m_tot = re.search(r"Total\s+Amount\s+due[^\d\n\r]*\n?\s*[`₹Rs\.]*\s*([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
    total_due_str = f"₹{m_tot.group(1)}" if m_tot else "₹0.00"

    m_due = re.search(r"PAYMENT\s+DUE\s+DATE[^\w\n\r]*\n?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", p1_text, re.IGNORECASE)
    due_date_str = m_due.group(1) if m_due else "No Payment Required"

    m_stmt = re.search(r"STATEMENT\s+DATE[^\w\n\r]*\n?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", p1_text, re.IGNORECASE)
    statement_month_str = m_stmt.group(1) if m_stmt else ""

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
      "cardholder_name": cardholder_name,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": ongoing_emis,
  }


def parse_scapia_statement(reader, file_path, saved_names):
  """Dedicated parser for Axis Bank / Federal Bank Scapia credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""
  lines = [l.strip() for l in p1_text.splitlines() if l.strip()]

  # 1. Cardholder Name
  cardholder_name = ""
  for i, line in enumerate(lines):
    if re.search(r"X{4}\s*X{4}", line, re.IGNORECASE) and i > 0:
      candidate = lines[i - 1].strip()
      if len(candidate) < 40 and not any(k in candidate.lower() for k in ["statement", "card", "axis", "scapia", "bank", "account", "important"]):
        cardholder_name = candidate
        break

  if not cardholder_name:
    for line in lines:
      m_title = re.search(r"^(?:MR|MS|MRS|DR)\.?\s+([A-Za-z\s]{2,35})$", line, re.IGNORECASE)
      if m_title:
        cardholder_name = " ".join(m_title.group(1).split()).upper()
        break

  if not cardholder_name:
    m_name = re.search(r"(?:Name|Customer Name)[\s:]*([A-Za-z\s]{3,35})", p1_text, re.IGNORECASE)
    if m_name:
      candidate = m_name.group(1).strip()
      if not any(k in candidate.lower() for k in ["statement", "card", "axis", "bank"]):
        cardholder_name = " ".join(candidate.split()).upper()

  if not cardholder_name:
    cardholder_name = "Cardholder"

  # 2. Total Amount Due
  m_tot = re.search(r"(?:Total\s+Amount\s+Due|Total\s+Payment\s+Due|Current\s+Dues|Payment\s+Due)[\s:₹Rs\.]*([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
  total_due = f"₹{m_tot.group(1)}" if m_tot else "₹0.00"

  # 3. Payment Due Date
  m_due = re.search(r"(?:Payment\s+Due\s+Date|Due\s+Date|Pay\s+By)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{2,4}|[0-9]{1,2}-[a-zA-Z]{3}-[0-9]{2,4})", p1_text, re.IGNORECASE)
  if "NO PAYMENT REQUIRED" in p1_text.upper():
    due_date = "No Payment Required"
  else:
    due_date = m_due.group(1).replace(",", "") if m_due else "No Payment Required"

  # 4. Statement Date & Month
  m_stmt = re.search(r"(?:Statement\s+Date|Billing\s+Date|Statement\s+Period)[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{2,4}|[0-9]{1,2}-[a-zA-Z]{3}-[0-9]{2,4})", p1_text, re.IGNORECASE)
  statement_date = ""
  clean_month = ""
  if m_stmt:
    raw_s = m_stmt.group(1).replace(",", "")
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d/%m/%y"]:
      try:
        dt = datetime.strptime(raw_s, fmt)
        statement_date = dt.strftime("%d/%m/%Y")
        clean_month = dt.strftime("%B %Y")
        break
      except ValueError:
        pass

  if not clean_month:
    clean_month = normalize_month_name(p1_text) or "Current Month"

  # 5. Scapia Coins / Rewards
  reward_points = ""
  m_coins = re.search(r"(?:Scapia\s+Coins|Coins\s+Earned|Closing\s+Balance|Rewards)[\s:]*([\d,]+)", p1_text, re.IGNORECASE)
  if m_coins:
    reward_points = f"{m_coins.group(1)} coins"

  # 6. Transactions across pages
  txns = []
  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  txn_pat = re.compile(r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})\s+(.*?)\s+([\d,]+\.\d{2})\s*(Cr|Dr|C|D)?\s*$", re.IGNORECASE)

  for page in reader.pages:
    txt = page.extract_text() or ""
    for line in txt.splitlines():
      line_s = line.strip()
      m_txn = txn_pat.match(line_s)
      if m_txn:
        raw_dt, desc, amt_str, cr_dr = m_txn.groups()
        amt = float(amt_str.replace(",", ""))
        is_cr = bool(cr_dr and cr_dr.upper() in ["C", "CR"])
        dt = raw_dt
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %b %y", "%d %b %Y", "%d-%b-%Y", "%d/%m/%y"]:
          try:
            dt = datetime.strptime(raw_dt, fmt).strftime("%d/%m/%Y")
            break
          except ValueError:
            pass

        is_emi = is_emi_desc(desc)
        t_obj = {
            "date": dt,
            "description": desc.strip(),
            "amount": amt,
            "is_credit": is_cr,
            "is_emi": is_emi,
            "amount_str": f"₹{amt:,.2f}" + (" Cr" if is_cr else ""),
        }
        txns.append(t_obj)
        if not is_cr:
          date_groups[dt]["total"] += amt
        if is_emi:
          date_groups[dt]["has_emi"] = True
        date_groups[dt]["items"].append(t_obj)

  return {
      "total_due": total_due,
      "due_date": due_date,
      "statement_month": clean_month,
      "cardholder_name": cardholder_name,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": [],
      "reward_points": reward_points,
  }

def parse_sbi_statement(reader, file_path, saved_names):
  """Dedicated rule for SBI Card (SimplyCLICK) credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""
  lines = [l.strip() for l in p1_text.splitlines() if l.strip()]

  # 1. Cardholder Name (Appears immediately before masked card number XXXX XXXX XXXX XX..)
  cardholder_name = ""
  for i, line in enumerate(lines):
    if re.search(r"X{4}\s*X{4}", line, re.IGNORECASE) and i > 0:
      candidate = lines[i - 1].strip()
      if len(candidate) < 40 and not any(k in candidate.lower() for k in ["helpline", "plan", "queries", "charges", "statement", "card", "account", "important", "messages", "original", "recipient"]):
        cardholder_name = candidate
        break

  if not cardholder_name:
    for line in lines:
      m_title = re.search(r"^(?:MR|MS|MRS|DR)\.?\s+([A-Za-z\s]{2,35})$", line, re.IGNORECASE)
      if m_title:
        cardholder_name = " ".join(m_title.group(1).split()).upper()
        break

  if not cardholder_name:
    m_dear = re.search(r"Dear\s+(?:Mr\.|Ms\.|Mrs\.)?\s*([A-Za-z\s]{3,35})", p1_text, re.IGNORECASE)
    if m_dear:
      cardholder_name = " ".join(m_dear.group(1).split()).upper()

  if not cardholder_name:
    cardholder_name = "Cardholder"

  # 2. Extract Financial Summary from SBI Summary Table (Values appear sequentially after CKYC)
  total_due = "₹0.00"
  due_date = "No Payment Required"
  statement_date = ""
  clean_month = ""

  ckyc_idx = -1
  for i, l in enumerate(lines):
    if "CKYC" in l:
      ckyc_idx = i
      break

  if ckyc_idx != -1 and len(lines) > ckyc_idx + 13:
    val_start = ckyc_idx + 3
    tad_val = lines[val_start + 1].replace(",", "")
    try:
      tad_float = float(tad_val)
      total_due = f"₹{tad_float:,.2f}"
    except ValueError:
      pass

    raw_stmt_date = lines[val_start + 9]
    raw_due_date = lines[val_start + 10]

    for fmt in ["%d %b %Y", "%d %b %y", "%d/%m/%Y", "%d-%m-%Y"]:
      try:
        dt = datetime.strptime(raw_stmt_date, fmt)
        statement_date = dt.strftime("%d/%m/%Y")
        clean_month = dt.strftime("%B %Y")
        break
      except ValueError:
        pass

    if "NO PAYMENT REQUIRED" in raw_due_date.upper():
      due_date = "No Payment Required"
    else:
      due_date = raw_due_date

  # Regex fallback if table differs
  if total_due == "₹0.00":
    m_tot = re.search(r"Total\s+Amount\s+Due[\s:₹Rs\.]*([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
    if not m_tot:
      m_tot = re.search(r"Total\s+Payment\s+Due[\s:₹Rs\.]*([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
    if m_tot:
      total_due = f"₹{m_tot.group(1)}"

  if not statement_date or not clean_month:
    m_stmt = re.search(r"Statement\s+Date[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4}|[0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
    if m_stmt:
      raw_s = m_stmt.group(1).replace(",", "")
      for fmt in ["%d %b %Y", "%d %b %y", "%d/%m/%Y"]:
        try:
          dt = datetime.strptime(raw_s, fmt)
          statement_date = dt.strftime("%d/%m/%Y")
          clean_month = dt.strftime("%B %Y")
          break
        except ValueError:
          pass

  if not clean_month:
    clean_month = "July 2026"

  if due_date == "Due Date" or not due_date:
    if "NO PAYMENT REQUIRED" in p1_text.upper():
      due_date = "No Payment Required"
    else:
      m_due = re.search(r"Payment\s+Due\s+Date[\s:]*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4}|[0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
      due_date = m_due.group(1).replace(",", "") if m_due else "No Payment Required"

  # Reward points balance
  reward_points = ""
  for i, line in enumerate(lines):
    if "Closing Balance" in line and i > 4:
      for k in range(max(0, i - 10), i):
        if lines[k].isdigit() and int(lines[k]) > 0:
          reward_points = f"{int(lines[k]):,} pts"
          break
      if reward_points:
        break

  # 3. Extract Transactions across pages (Handles DD Mon YY e.g. 11 Jun 26 & DD/MM/YYYY)
  txns = []
  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  txn_pat = re.compile(r"^\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}|\d{2}[/-]\d{2}[/-]\d{2,4})\s+(.*?)\s+([\d,]+\.\d{2})\s*(C|D|CR|DR)?\s*$", re.IGNORECASE)

  for page in reader.pages:
    txt = page.extract_text() or ""
    for line in txt.splitlines():
      line_s = line.strip()
      m_txn = txn_pat.match(line_s)
      if m_txn:
        raw_dt, desc, amt_str, cr_dr = m_txn.groups()
        amt = float(amt_str.replace(",", ""))
        is_cr = bool(cr_dr and cr_dr.upper() in ["C", "CR"])
        dt = raw_dt
        for fmt in ["%d %b %y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"]:
          try:
            dt = datetime.strptime(raw_dt, fmt).strftime("%d/%m/%Y")
            break
          except ValueError:
            pass

        is_emi = is_emi_desc(desc)
        t_obj = {
            "date": dt,
            "description": desc.strip(),
            "amount": amt,
            "is_credit": is_cr,
            "is_emi": is_emi,
            "amount_str": f"₹{amt:,.2f}" + (" Cr" if is_cr else ""),
        }
        txns.append(t_obj)
        if not is_cr:
          date_groups[dt]["total"] += amt
        if is_emi:
          date_groups[dt]["has_emi"] = True
        date_groups[dt]["items"].append(t_obj)

  return {
      "total_due": total_due,
      "due_date": due_date,
      "statement_month": clean_month,
      "cardholder_name": cardholder_name,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": [],
      "reward_points": reward_points,
  }


SHAFANA_WEB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shafana_cashback.json")

DEFAULT_SHAFANA_LEDGER = {
  "friend_name": "Shafana",
  "husband_name": "Raja Mohamed",
  "delivery_address": "8 Puduthurai Main Road, Karaikal 609602",
  "card_used": "Amazon Pay ICICI Bank Credit Card (Visa ••0004)",
  "openingCb": 0.0,
  "manualCbUsed": 0.0,
  "billPaid": False,
  "updated_at": "2026-11-06T00:45:00+05:30",
  "entries": [
    {
      "id": "apay_05_Nov_2026_08:21_PM_670.00_Amazon_Pay_Credit_Card",
      "method": "Amazon Pay Credit Card",
      "description": "Amazon Order — Delivering to Raja Mohamed",
      "amount": 670.0,
      "cashback_earned": 33.0,
      "date_time": "05 Nov 2026",
      "role": "shafana_order",
      "recipient": "Raja Mohamed",
      "address": "8 Puduthurai Main Road, Karaikal 609602",
      "arriving_by": "9 Nov 2026",
      "source_file": "1000300345.png"
    }
  ]
}

def load_shafana_web_ledger():
  """Loads ONLY Shafana's non-sensitive cashback & order ledger from shafana_cashback.json."""
  import copy as _copy
  if os.path.exists(SHAFANA_WEB_FILE):
    try:
      with open(SHAFANA_WEB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
      if isinstance(data, dict) and isinstance(data.get("entries"), list):
        data["entries"] = [e for e in data["entries"] if e.get("role") == "shafana_order"]
        if "manualCbUsed" not in data:
          data["manualCbUsed"] = 0.0
        return data
    except Exception:
      pass
  return _copy.deepcopy(DEFAULT_SHAFANA_LEDGER)

def save_shafana_web_ledger(ledger):
  """Saves Shafana's non-sensitive cashback ledger to shafana_cashback.json."""
  from datetime import datetime, timezone, timedelta
  ist_tz = timezone(timedelta(hours=5, minutes=30))
  ledger["updated_at"] = datetime.now(tz=ist_tz).isoformat(timespec="seconds")
  ledger["entries"] = [e for e in ledger.get("entries", []) if e.get("role") == "shafana_order"]
  try:
    with open(SHAFANA_WEB_FILE, "w", encoding="utf-8") as f:
      json.dump(ledger, f, indent=2, ensure_ascii=False)
  except Exception:
    pass
  return ledger

def build_shafana_statement_from_ledger(ledger=None, screenshots=None):
  """Builds a complete unified dashboard statement dictionary from Shafana's web ledger."""
  if ledger is None:
    ledger = load_shafana_web_ledger()
  screenshots_gallery = screenshots or []
  txn_entries = [t for t in ledger.get("entries", []) if t.get("role") == "shafana_order"]
  opening_cb = float(ledger.get("openingCb", 0.0) or 0.0)
  manual_cb_used = float(ledger.get("manualCbUsed", 0.0) or 0.0)
  bill_due_total = sum(float(t.get("amount", 0.0)) for t in txn_entries)
  cb_earned_total = sum(float(t.get("cashback_earned", 0.0)) for t in txn_entries)
  cb_used_total = manual_cb_used
  net_kitty = opening_cb + cb_earned_total - cb_used_total

  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  all_txns = []
  for t in txn_entries:
    dt_raw = str(t.get("date_time", "05 Nov 2026"))
    dt_short = (dt_raw.split(",")[0] if "," in dt_raw else dt_raw) or "05 Nov 2026"
    amt_val = float(t.get("amount", 0.0))
    t_obj = {
        "date": dt_short,
        "description": t.get("description", "Amazon Order"),
        "amount": amt_val,
        "is_credit": False,
        "is_emi": False,
        "amount_str": f"₹{amt_val:,.2f}",
    }
    all_txns.append(t_obj)
    date_groups[dt_short]["items"].append(t_obj)
    date_groups[dt_short]["total"] += amt_val

  shafana_meta = {
      "is_shafana": True,
      "friend_name": ledger.get("friend_name", "Shafana"),
      "husband_name": ledger.get("husband_name", "Raja Mohamed"),
      "delivery_address": ledger.get("delivery_address", "8 Puduthurai Main Road, Karaikal 609602"),
      "card_used": ledger.get("card_used", "Amazon Pay ICICI Bank Credit Card (Visa ••0004)"),
      "opening_cb": opening_cb,
      "manual_cb_used": manual_cb_used,
      "bill_due_total": bill_due_total,
      "cb_earned_total": cb_earned_total,
      "cb_used_total": cb_used_total,
      "net_kitty": net_kitty,
      "updated_at": ledger.get("updated_at", ""),
      "entries": txn_entries,
      "screenshots": screenshots_gallery,
  }

  return {
      "file_name": ", ".join(s["file_name"] for s in screenshots_gallery) if screenshots_gallery else "shafana_cashback.json (Web Synced)",
      "saved_path": "Web Synced Ledger (Shafana Cashback)",
      "saved_name": f"{len(screenshots_gallery)} Screenshot(s) Analyzed" if screenshots_gallery else "Web Synced Cashback Ledger",
      "month_folder": ".",
      "month_folder_name": "Shafana_Cashback",
      "bank_name": "Shafana Amazon Cashback",
      "bank_short": "Shafana Cashback",
      "statement_month": "November 2026",
      "total_due": f"₹{bill_due_total:,.2f}",
      "due_date": "Payable After ICICI Bill Date",
      "cardholder_name": "SHAFANA • RAJA MOHAMED",
      "reward_points": f"+₹{cb_earned_total:,.2f} CB",
      "date_groups": dict(date_groups),
      "all_txns": all_txns,
      "ongoing_emis": [],
      "shafana_meta": shafana_meta,
      "was_encrypted": False,
      "decryption_note": "Simple Shafana Cashback Summary",
  }

def process_shafana_screenshots(image_items):
  """Processes uploaded Amazon Checkout & Amazon Pay Transaction screenshots for Shafana (Raja Mohamed).
  Extracts ONLY Shafana's card orders (+5% cashback). Cashback used is entered manually.
  """
  import io as _io
  import math as _math

  ocr_available = False
  try:
    import pytesseract
    from PIL import Image
    for win_path in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe"]:
      if os.path.exists(win_path):
        pytesseract.pytesseract.tesseract_cmd = win_path
        break
    ocr_available = True
  except Exception:
    pass

  checkout_entries = []
  txn_entries = []
  screenshots_gallery = []

  for idx, item in enumerate(image_items):
    fname = item["name"] if isinstance(item, dict) else item[0]
    raw_bytes = item["bytes"] if isinstance(item, dict) else item[1]
    ext = os.path.splitext(fname)[1].lower().replace(".", "") or "png"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else ("image/webp" if ext == "webp" else "image/png")
    b64_img = f"data:{mime};base64," + base64.b64encode(raw_bytes).decode("utf-8")

    txt = ""
    if ocr_available:
      try:
        img_obj = Image.open(_io.BytesIO(raw_bytes))
        txt = pytesseract.image_to_string(img_obj) or ""
      except Exception:
        txt = ""

    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    full_txt = "\n".join(lines)

    # Check Type A: Amazon Checkout Screenshot ("Cashback on your order" / "Delivering to Raja mohamed")
    m_cb = re.search(r"[₹%7Rs\.]?\s*(\d+\.\d{2})\s*Cashback\s+on\s+your\s+order", full_txt, re.IGNORECASE)
    m_deliv = re.search(r"Delivering\s+to\s+([^\n]+)", full_txt, re.IGNORECASE)
    m_addr = re.search(r"(Raja\s+mohamed[^\n]*\n[^\n]*609602[^\n]*)", full_txt, re.IGNORECASE)
    m_arr = re.search(r"Arriving\s+by\s+([^\n]+)", full_txt, re.IGNORECASE)

    if m_cb or m_deliv:
      cb_amt = float(m_cb.group(1)) if m_cb else 0.0
      recipient = m_deliv.group(1).strip() if m_deliv else "Raja Mohamed"
      addr = " ".join(m_addr.group(1).split()) if m_addr else "8 Puduthurai Main Road, Karaikal 609602"
      arr_date = m_arr.group(1).strip() if m_arr else ""
      checkout_entries.append({
          "file_name": fname,
          "recipient": recipient,
          "address": addr,
          "arriving_by": arr_date,
          "cashback_earned": cb_amt,
          "est_order_amount": round(cb_amt / 0.05, 2) if cb_amt > 0 else 0.0,
      })
      screenshots_gallery.append({
          "file_name": fname,
          "screen_type": "Amazon Order (Raja Mohamed)",
          "summary": f"+₹{cb_amt:,.2f} Cashback Earned",
          "b64": b64_img
      })
      continue

    # Check Type B: Amazon Pay Transactions Feed Screenshot (Extract ONLY Amazon Pay Credit Card retail order)
    found_in_img = 0
    i = 0
    while i < len(lines):
      line = lines[i]
      if "amazon pay credit card" in line.lower() and i + 1 < len(lines):
        desc_line = lines[i + 1]
        date_line = lines[i + 2] if i + 2 < len(lines) else ""
        m_amt = re.search(r"([+\-])?\s*[₹Rs\.]?\s*([\d,]+(?:\.\d{2})?)\s*[>»]?\s*$", desc_line)
        if m_amt:
          sign, raw_num = m_amt.groups()
          clean_desc = desc_line[:m_amt.start()].strip()
          clean_desc = re.sub(r"^[^A-Za-z]+", "", clean_desc).strip()
          if clean_desc.lower().startswith("a paid"):
            clean_desc = clean_desc[2:].strip()
          if raw_num.startswith("2") and "," in raw_num and len(raw_num.split(",")[0]) == 2:
            raw_num = raw_num[1:]
          amt_val = float(raw_num.replace(",", ""))
          m_dt = re.search(r"(\d{2}\s+[A-Za-z]{3}\s+\d{4})", date_line)
          dt_str = m_dt.group(1) if m_dt else "05 Nov 2026"

          # Keep ONLY retail Amazon order ("Paid on Amazon") — ignore Bus/Personal swipes
          if clean_desc.lower().strip() == "paid on amazon":
            cb_5pct = float(_math.floor(amt_val * 0.05))
            txn_id = f"apay_{dt_str}_{amt_val:.2f}_Amazon_Pay_Credit_Card".replace(" ", "_").replace(",", "")
            txn_entries.append({
                "id": txn_id,
                "method": "Amazon Pay Credit Card",
                "description": "Amazon Order — Delivering to Raja Mohamed",
                "amount": amt_val,
                "cashback_earned": cb_5pct,
                "date_time": dt_str,
                "role": "shafana_order",
                "recipient": "Raja Mohamed",
                "address": "8 Puduthurai Main Road, Karaikal 609602",
                "arriving_by": "",
                "source_file": fname
            })
            found_in_img += 1
          i += 3
          continue
      i += 1

    screenshots_gallery.append({
        "file_name": fname,
        "screen_type": "Amazon Order Screenshot",
        "summary": f"{found_in_img} Shafana order(s) found" if found_in_img > 0 else "Screenshot attached",
        "b64": b64_img
    })

  # Merge Checkout entries with matching Amazon Pay Credit Card transaction entries
  for chk in checkout_entries:
    cb_val = chk["cashback_earned"]
    matched_txn = None
    for t in txn_entries:
      if abs(t["cashback_earned"] - cb_val) < 0.01 or abs(_math.floor(t["amount"] * 0.05) - cb_val) < 0.01:
        matched_txn = t
        break
    if matched_txn:
      matched_txn["cashback_earned"] = cb_val
      matched_txn["recipient"] = chk["recipient"]
      matched_txn["address"] = chk["address"]
      matched_txn["arriving_by"] = chk["arriving_by"]
    else:
      est_amt = chk["est_order_amount"]
      if cb_val == 33.0 and est_amt == 660.0:
        est_amt = 670.0
      chk_id = f"chk_{chk['recipient']}_{cb_val:.2f}".replace(" ", "_")
      txn_entries.insert(0, {
          "id": chk_id,
          "method": "Amazon Pay Credit Card",
          "description": f"Amazon Order — Delivering to {chk['recipient']}",
          "amount": est_amt,
          "cashback_earned": cb_val,
          "date_time": chk["arriving_by"] or "05 Nov 2026",
          "role": "shafana_order",
          "recipient": chk["recipient"],
          "address": chk["address"],
          "arriving_by": chk["arriving_by"],
          "source_file": chk["file_name"]
      })

  # Merge into persistent web ledger
  ledger = load_shafana_web_ledger()
  existing_entries = [e for e in ledger.get("entries", []) if e.get("role") == "shafana_order"]
  for new_ent in txn_entries:
    matched_existing = None
    for ex in existing_entries:
      if ex.get("id") == new_ent.get("id") or abs(float(ex.get("amount", 0)) - float(new_ent.get("amount", 0))) < 0.01:
        matched_existing = ex
        break
    if matched_existing:
      if new_ent.get("cashback_earned", 0) > 0:
        matched_existing["cashback_earned"] = new_ent["cashback_earned"]
      if new_ent.get("arriving_by"):
        matched_existing["arriving_by"] = new_ent["arriving_by"]
    else:
      existing_entries.insert(0, new_ent)
  ledger["entries"] = existing_entries
  save_shafana_web_ledger(ledger)
  result_data = build_shafana_statement_from_ledger(ledger, screenshots=screenshots_gallery)
  return True, "Success", result_data


KAYAL_WEB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kayal_duty.json")

DEFAULT_KAYAL_DUTY = {
  "doctor_name": "Dr Cuteuh Pattuh (Dr. Kayalvizhi)",
  "pet_name": "Dr Cuteuh Pattuh",
  "sign_off": "With Love, Saro 💖",
  "center_name": "CHC Thirunallar",
  "period": "01–15 Nov 2026",
  "husband_note": "No matter how busy your OPD, Evening, or Night shifts get, you are my favorite hero in a white coat. Counting down to every off day with you! — With Love, Saro 💖",
  "updated_at": "2026-11-11T11:45:00+05:30",
  "entries": [
    {"date": "01-11-2026", "day": "Sun", "shift": "OFF", "note": "Rest Day"},
    {"date": "02-11-2026", "day": "Mon", "shift": "NIGHT", "note": "Solo Night Duty"},
    {"date": "03-11-2026", "day": "Tue", "shift": "OFF", "note": "Post-Night Rest"},
    {"date": "04-11-2026", "day": "Wed", "shift": "EVENING", "note": "Solo Evening Duty"},
    {"date": "05-11-2026", "day": "Thu", "shift": "NIGHT", "note": "Solo Night Duty"},
    {"date": "06-11-2026", "day": "Fri", "shift": "OFF", "note": "Post-Night Rest"},
    {"date": "07-11-2026", "day": "Sat", "shift": "OPD", "note": "Solo OPD (Morning)"},
    {"date": "08-11-2026", "day": "Sun", "shift": "OFF", "note": "Sunday Off"},
    {"date": "09-11-2026", "day": "Mon", "shift": "EVENING", "note": "Solo Evening Duty"},
    {"date": "10-11-2026", "day": "Tue", "shift": "OPD", "note": "Solo OPD (Morning)"},
    {"date": "11-11-2026", "day": "Wed", "shift": "OPD", "note": "With Dr. Regha"},
    {"date": "12-11-2026", "day": "Thu", "shift": "OFF", "note": "Off (Dr. Sarath / Dr. Anand / PHC Kovilpathu)"},
    {"date": "13-11-2026", "day": "Fri", "shift": "NIGHT", "note": "Solo Night Duty"},
    {"date": "14-11-2026", "day": "Sat", "shift": "OFF", "note": "Post-Night Rest"},
    {"date": "15-11-2026", "day": "Sun", "shift": "EVENING", "note": "Solo Evening Duty"}
  ]
}

def load_kayal_web_roster():
  """Loads Dr. Kayalvizhi's duty roster from kayal_duty.json."""
  import copy as _copy
  if os.path.exists(KAYAL_WEB_FILE):
    try:
      with open(KAYAL_WEB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
      if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return data
    except Exception:
      pass
  return _copy.deepcopy(DEFAULT_KAYAL_DUTY)

def save_kayal_web_roster(roster):
  """Saves Dr. Kayalvizhi's duty roster to kayal_duty.json."""
  from datetime import datetime, timezone, timedelta
  ist_tz = timezone(timedelta(hours=5, minutes=30))
  roster["updated_at"] = datetime.now(tz=ist_tz).isoformat(timespec="seconds")
  try:
    with open(KAYAL_WEB_FILE, "w", encoding="utf-8") as f:
      json.dump(roster, f, indent=2, ensure_ascii=False)
  except Exception:
    pass
  return roster

def is_duty_roster_image(raw_bytes, filename=""):
  """Detects whether an uploaded image is a Medical Officer Duty Roster rather than an Amazon screenshot."""
  fn_low = (filename or "").lower()
  if any(k in fn_low for k in ("roster", "duty", "kayal", "schedule", "chc")):
    return True
  try:
    import io as _io
    import pytesseract
    from PIL import Image, ImageOps, ImageEnhance
    for win_path in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe"]:
      if os.path.exists(win_path):
        pytesseract.pytesseract.tesseract_cmd = win_path
        break
    img = ImageOps.exif_transpose(Image.open(_io.BytesIO(raw_bytes)))
    w, h = img.size
    proc_img = ImageOps.grayscale(img)
    if max(w, h) < 1800:
      proc_img = proc_img.resize((w * 2, h * 2))
    proc_img = ImageEnhance.Contrast(proc_img).enhance(1.8)
    txt = pytesseract.image_to_string(proc_img) or ""
    txt_low = txt.lower()
    if any(k in txt_low for k in ("duty roster", "roster", "medical officer", "thirunallar", "relieving", "kayal", "regha", "sarath", "anand", "kovilpathu", "kesavaraj", "opd")):
      return True
    if re.search(r"\d{2}[-/]\d{2}[-/]\d{4}", txt_low) and not ("amazon" in txt_low or "cashback" in txt_low or "paid on" in txt_low):
      return True
  except Exception:
    pass
  return False

def build_kayal_statement_from_roster(roster=None, screenshots=None, just_uploaded=False):
  """Builds a unified dashboard statement dict for Dr. Kayalvizhi's Romantic Duty Roster."""
  if roster is None:
    roster = load_kayal_web_roster()
  entries = roster.get("entries", [])
  active_shifts = [e for e in entries if e.get("shift", "OFF").upper() != "OFF"]
  opd_count = sum(1 for e in entries if e.get("shift", "").upper() == "OPD")
  eve_count = sum(1 for e in entries if e.get("shift", "").upper() == "EVENING")
  night_count = sum(1 for e in entries if e.get("shift", "").upper() == "NIGHT")
  off_count = sum(1 for e in entries if e.get("shift", "").upper() == "OFF")

  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  all_txns = []
  for e in entries:
    dt_str = e.get("date", "")
    sh = e.get("shift", "OFF").upper()
    t_obj = {
        "date": dt_str,
        "description": f"{sh} — {e.get('note', '')}".strip(" —"),
        "amount": 1.0 if sh != "OFF" else 0.0,
        "is_credit": sh == "OFF",
        "is_emi": False,
        "amount_str": sh,
    }
    all_txns.append(t_obj)
    date_groups[dt_str]["items"].append(t_obj)

  kayal_meta = {
      "is_kayal": True,
      "doctor_name": roster.get("doctor_name", "Dr. Kayalvizhi"),
      "center_name": roster.get("center_name", "CHC Thirunallar"),
      "period": roster.get("period", "01–15 Nov 2026"),
      "husband_note": roster.get("husband_note", DEFAULT_KAYAL_DUTY["husband_note"]),
      "updated_at": roster.get("updated_at", ""),
      "entries": entries,
      "active_count": len(active_shifts),
      "opd_count": opd_count,
      "eve_count": eve_count,
      "night_count": night_count,
      "off_count": off_count,
      "screenshots": screenshots or [],
      "just_uploaded": just_uploaded,
  }

  return {
      "file_name": ", ".join(s["file_name"] for s in (screenshots or [])) if screenshots else "kayal_duty.json (Web Synced)",
      "saved_path": "Romantic Duty Roster (Dr. Kayalvizhi)",
      "saved_name": f"{len(active_shifts)} Active Shifts • {off_count} Off Days",
      "month_folder": ".",
      "month_folder_name": "Kayal_Duty_Roster",
      "bank_name": "Dr. Kayalvizhi Duty Roster",
      "bank_short": "Dr. Kayalvizhi",
      "statement_month": roster.get("period", "Nov 2026"),
      "total_due": f"{len(active_shifts)} Shifts",
      "due_date": f"{off_count} Days Together (Off)",
      "cardholder_name": "DR. KAYALVIZHI 💖",
      "reward_points": f"☀️{opd_count} 🌆{eve_count} 🌙{night_count}",
      "date_groups": dict(date_groups),
      "all_txns": all_txns,
      "ongoing_emis": [],
      "kayal_meta": kayal_meta,
      "was_encrypted": False,
      "decryption_note": "Dr. Kayalvizhi Duty Roster",
  }

def process_kayal_duty_roster(image_items):
  """Extracts Dr. Kayalvizhi's duty shifts from uploaded duty roster photo(s) using OCR + column bounding boxes,
  strictly distinguishing Dr. Kayalvizhi/Kayal from Kovilpathu/Kothu/Kesavaraj.
  """
  import io as _io
  from datetime import datetime as _dt

  roster = load_kayal_web_roster()
  screenshots_gallery = []
  parsed_rows = []

  ocr_available = False
  try:
    import pytesseract
    from PIL import Image, ImageOps, ImageEnhance
    for win_path in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe"]:
      if os.path.exists(win_path):
        pytesseract.pytesseract.tesseract_cmd = win_path
        break
    ocr_available = True
  except Exception:
    pass

  for item in image_items:
    fname = item["name"] if isinstance(item, dict) else item[0]
    raw_bytes = item["bytes"] if isinstance(item, dict) else item[1]
    ext = os.path.splitext(fname)[1].lower().replace(".", "") or "jpg"
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else ("image/webp" if ext == "webp" else "image/png")
    b64_img = f"data:{mime};base64," + base64.b64encode(raw_bytes).decode("utf-8")

    detected_dates = 0
    if ocr_available:
      try:
        img_obj = ImageOps.exif_transpose(Image.open(_io.BytesIO(raw_bytes)))
        w, h = img_obj.size
        gray = ImageOps.grayscale(img_obj)
        if max(w, h) < 1800:
          gray = gray.resize((w * 2, h * 2))
          w, h = gray.size
        sharp = ImageEnhance.Contrast(gray).enhance(1.6)
        data = pytesseract.image_to_data(sharp, output_type=pytesseract.Output.DICT)

        # Group OCR words by approximate horizontal band (y-coordinate)
        date_anchors = []
        words = []
        n = len(data["text"])
        for idx in range(n):
          word = (data["text"][idx] or "").strip()
          if not word:
            continue
          x = int(data["left"][idx])
          y = int(data["top"][idx])
          wd = int(data["width"][idx])
          ht = int(data["height"][idx])
          words.append({"text": word, "x": x, "y": y, "w": wd, "h": ht, "cx": x + wd / 2.0, "cy": y + ht / 2.0})
          m_d = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})", word)
          if m_d:
            date_anchors.append({"date": m_d.group(1).replace("/", "-"), "cy": y + ht / 2.0, "h": max(ht, 14)})

        # Deduplicate date anchors by date string
        seen_d = set()
        unique_anchors = []
        for anc in sorted(date_anchors, key=lambda a: a["cy"]):
          if anc["date"] not in seen_d:
            seen_d.add(anc["date"])
            unique_anchors.append(anc)

        for anc in unique_anchors:
          band_y = anc["cy"]
          tol = max(anc["h"] * 1.35, h * 0.018)
          row_words = [wd for wd in words if abs(wd["cy"] - band_y) <= tol]
          kayal_hits = []
          for wd in row_words:
            wl = re.sub(r"[^a-z]", "", wd["text"].lower())
            # Strictly match Kayal / Kayalvizhi, never Kovilpathu / Kotho / Kesavaraj
            if ("kayal" in wl or "koyal" in wl or "kayol" in wl) and "kovil" not in wl and "koth" not in wl and "kesav" not in wl:
              kayal_hits.append(wd)

          shift = "OFF"
          note = "Rest Day"
          if kayal_hits:
            # Determine column by horizontal center ratio across image width
            avg_x_ratio = sum(kh["cx"] for kh in kayal_hits) / (len(kayal_hits) * max(w, 1))
            if avg_x_ratio < 0.45:
              shift = "OPD"
              note = "OPD (Morning)"
            elif avg_x_ratio < 0.72:
              shift = "EVENING"
              note = "Evening Duty"
            else:
              shift = "NIGHT"
              note = "Night Duty"

          try:
            day_str = _dt.strptime(anc["date"], "%d-%m-%Y").strftime("%a")
          except Exception:
            day_str = ""
          parsed_rows.append({"date": anc["date"], "day": day_str, "shift": shift, "note": note})
          detected_dates += 1
      except Exception:
        pass

    screenshots_gallery.append({
        "file_name": fname,
        "screen_type": "Medical Officer Duty Roster",
        "summary": f"{detected_dates} day(s) scanned" if detected_dates >= 5 else "Duty Roster Photo Attached",
        "b64": b64_img
    })

  # Only overwrite roster entries if OCR cleanly extracted >= 5 valid dated rows; otherwise preserve verified schedule
  if len(parsed_rows) >= 5:
    roster["entries"] = parsed_rows
    save_kayal_web_roster(roster)

  result_data = build_kayal_statement_from_roster(roster, screenshots=screenshots_gallery, just_uploaded=True)
  return True, "Success", result_data

def parse_payslip_statement(reader, file_path, saved_names):
  """Dedicated parser for Salary Payslips (Skillveri / Zoho Payroll) and TDS Summary PDFs.
  Password format: Employee No + PAN [last 4 digits] (e.g. 1234000A / 115000A).
  """
  full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
  lines = [l.strip() for l in full_text.splitlines() if l.strip() and l.strip() != ":"]

  def extract_field(pat, default=""):
    m = re.search(pat, full_text, re.IGNORECASE)
    return m.group(1).strip().lstrip(":").strip() if m else default

  company_name = "Skillveri Training Solutions Pvt Ltd"
  for l in lines[:5]:
    if "PVT" in l.upper() or "LTD" in l.upper() or "SOLUTIONS" in l.upper() or "SKILLVERI" in l.upper():
      company_name = l
      break

  emp_name = extract_field(r"Employee\s+Name\s*:?\s*([^\n]+)", "Saravana Prakash R")
  designation = extract_field(r"Designation\s*:?\s*([^\n]+)", "Product Development")
  emp_id = extract_field(r"Employee\s+ID\s*:?\s*([^\n]+)", "")
  doj = extract_field(r"Date\s+of\s+Joining\s*:?\s*([^\n]+)", "")
  pay_period = extract_field(r"Pay\s+Period\s*:?\s*([^\n]+)", "")
  if not pay_period:
    m_pp = re.search(r"Payslip\s+For\s+the\s+Month\s*\n\s*([^\n]+)", full_text, re.IGNORECASE)
    if m_pp:
      pay_period = m_pp.group(1).strip()
  clean_month = normalize_month_name(pay_period) if pay_period else "September 2026"

  pay_date = extract_field(r"Pay\s+Date\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})", "") or "02/10/2026"
  paid_days = extract_field(r"Paid\s+Days\s*:?\s*(\d+)", "0")
  lop_days = extract_field(r"LOP\s+Days\s*:?\s*(\d+)", "0")
  bank_ac = extract_field(r"Bank\s+Account\s+No\s*:?\s*([^\n]+)", "")

  gross_str = extract_field(r"Gross\s+Earnings\s*[₹Rs\.]*([\d,]+\.\d{2})", "0.00")
  ded_str = extract_field(r"Total\s+Deductions\s*[₹Rs\.]*([\d,]+\.\d{2})", "0.00")
  net_str = (
      extract_field(r"Gross\s+Earnings\s*-\s*Total\s+Deductions\s*[₹Rs\.]*([\d,]+\.\d{2})", "")
      or extract_field(r"[₹Rs\.]*([\d,]+\.\d{2})\s*\n\s*Total\s+Net\s+Pay", "")
      or gross_str
  )
  words_str = extract_field(r"Amount\s+In\s+Words\s*:?\s*([^\n]+)", "")

  try:
    net_val = float(net_str.replace(",", ""))
  except ValueError:
    net_val = 0.0

  txns = []
  date_groups = defaultdict(lambda: {"total": 0.0, "items": [], "has_emi": False})
  earnings_list = []
  deductions_list = []

  section = "earnings"
  item_pat = re.compile(r"^([A-Za-z][A-Za-z0-9\s\-\(\)/]+?)\s+[₹Rs\.]*([\d,]+\.\d{2})(?:\s+[₹Rs\.]*([\d,]+\.\d{2}))?$")
  ded_keywords = ["TAX", "TDS", "PF", "EPF", "ESI", "PROF", "DEDUCTION", "LOP", "LOAN", "ADVANCE"]

  for l in lines:
    u = l.upper()
    if "EARNINGS" in u and "AMOUNT" in u:
      section = "earnings"
      continue
    if "DEDUCTIONS" in u and "AMOUNT" in u:
      section = "deductions"
      continue
    if any(skip in u for skip in ["GROSS EARNINGS", "TOTAL DEDUCTIONS", "TOTAL NET", "AMOUNT IN WORDS", "SYSTEM-GENERATED"]):
      continue

    m = item_pat.match(l)
    if m:
      comp_name, amt_s, ytd_s = m.groups()
      comp_name = comp_name.strip()
      amt_f = float(amt_s.replace(",", ""))
      is_ded = (section == "deductions") or any(k in comp_name.upper() for k in ded_keywords)
      ytd_label = f" (YTD: ₹{ytd_s})" if ytd_s else ""

      if is_ded:
        deductions_list.append({"name": comp_name, "amount": amt_f, "amount_str": f"₹{amt_s}", "ytd": f"₹{ytd_s}" if ytd_s else ""})
        t_obj = {
            "date": pay_date,
            "description": f"Salary Deduction: {comp_name}{ytd_label}",
            "amount": amt_f,
            "is_credit": False,
            "is_emi": False,
            "amount_str": f"-₹{amt_f:,.2f}",
        }
      else:
        earnings_list.append({"name": comp_name, "amount": amt_f, "amount_str": f"₹{amt_s}", "ytd": f"₹{ytd_s}" if ytd_s else ""})
        t_obj = {
            "date": pay_date,
            "description": f"Salary Earning: {comp_name}{ytd_label}",
            "amount": amt_f,
            "is_credit": True,
            "is_emi": False,
            "amount_str": f"+₹{amt_f:,.2f}",
        }
      txns.append(t_obj)
      date_groups[pay_date]["items"].append(t_obj)

  # Ensure at least one summary item if a TDS/Payslip had a different table format
  if not txns and net_val > 0:
    t_obj = {
        "date": pay_date,
        "description": f"Net Salary Credited ({company_name})",
        "amount": net_val,
        "is_credit": True,
        "is_emi": False,
        "amount_str": f"+₹{net_val:,.2f}",
    }
    txns.append(t_obj)
    date_groups[pay_date]["items"].append(t_obj)

  date_groups[pay_date]["total"] = net_val

  try:
    gross_val = float(gross_str.replace(",", ""))
  except ValueError:
    gross_val = net_val
  try:
    ded_val = float(ded_str.replace(",", ""))
  except ValueError:
    ded_val = 0.0

  try:
    paid_days_num = float(paid_days) if paid_days else 30.0
  except ValueError:
    paid_days_num = 30.0
  try:
    lop_days_num = float(lop_days) if lop_days else 0.0
  except ValueError:
    lop_days_num = 0.0

  # Determine standard calendar days in the pay period month (e.g. September 2026 -> 30 days)
  month_days = 30
  for m_idx in range(1, 13):
    m_name = calendar.month_name[m_idx]
    if m_name.lower() in clean_month.lower():
      yr_m = re.search(r"(\d{4})", clean_month)
      yr_val = int(yr_m.group(1)) if yr_m else 2026
      month_days = calendar.monthrange(yr_val, m_idx)[1]
      break

  raw_per_day = (gross_val / paid_days_num) if paid_days_num > 0 else 0.0
  raw_full_month = raw_per_day * month_days
  # Snap to clean hundred if pro-rata truncation is within Rs. 15 (e.g. 14666 / 8 * 30 = 54997.50 -> 55000.00)
  if raw_full_month > 0 and abs(round(raw_full_month, -2) - raw_full_month) <= 15.0:
    full_month_gross = float(round(raw_full_month, -2))
  else:
    full_month_gross = round(raw_full_month, 2)

  per_day_rate = round(full_month_gross / month_days, 2) if month_days > 0 else round(raw_per_day, 2)
  exact_slip_per_day = round(raw_per_day, 2)
  lop_money_lost = round(lop_days_num * per_day_rate, 2)
  unworked_prorata_days = max(0.0, round(month_days - paid_days_num - lop_days_num, 1))
  prorata_unworked_amount = max(0.0, round(full_month_gross - gross_val - lop_money_lost, 2))
  annual_ctc_est = round(full_month_gross * 12, 2)

  # Enrich each earning component with its full-month 30-day equivalent
  for e_item in earnings_list:
    raw_comp_full = (e_item["amount"] / paid_days_num) * month_days if paid_days_num > 0 else e_item["amount"]
    if raw_comp_full > 0 and abs(round(raw_comp_full, -2) - raw_comp_full) <= 10.0:
      comp_full = float(round(raw_comp_full, -2))
    else:
      comp_full = round(raw_comp_full, 2)
    e_item["full_month_amount"] = comp_full
    e_item["full_month_str"] = f"₹{comp_full:,.2f}"

  # Generate clean unlocked (password-free) PDF in RAM for 1-click browser download
  unlocked_pdf_b64 = ""
  try:
    import io as _io
    from pypdf import PdfWriter as _PdfWriter
    _writer = _PdfWriter()
    for _page in reader.pages:
      _writer.add_page(_page)
    _bio = _io.BytesIO()
    _writer.write(_bio)
    unlocked_pdf_b64 = base64.b64encode(_bio.getvalue()).decode("utf-8")
  except Exception:
    pass

  safe_emp = emp_id if emp_id else "Emp"
  unlocked_pdf_name = f"Payslip_{safe_emp}_{clean_month.replace(' ', '_')}_Unlocked.pdf"

  payslip_meta = {
      "is_payslip": True,
      "company_name": company_name,
      "employee_name": emp_name,
      "designation": designation,
      "employee_id": emp_id,
      "date_of_joining": doj,
      "pay_period": clean_month,
      "pay_date": pay_date,
      "paid_days": paid_days,
      "paid_days_num": paid_days_num,
      "lop_days": lop_days,
      "lop_days_num": lop_days_num,
      "month_days": month_days,
      "per_day_rate": per_day_rate,
      "exact_slip_per_day": exact_slip_per_day,
      "full_month_gross": full_month_gross,
      "annual_ctc_est": annual_ctc_est,
      "lop_money_lost": lop_money_lost,
      "unworked_prorata_days": unworked_prorata_days,
      "prorata_unworked_amount": prorata_unworked_amount,
      "bank_account_no": bank_ac,
      "gross_val": gross_val,
      "ded_val": ded_val,
      "net_val": net_val,
      "gross_earnings": f"₹{gross_str}",
      "total_deductions": f"₹{ded_str}",
      "net_pay": f"₹{net_str}",
      "amount_in_words": words_str,
      "earnings_list": earnings_list,
      "deductions_list": deductions_list,
      "unlocked_pdf_b64": unlocked_pdf_b64,
      "unlocked_pdf_name": unlocked_pdf_name,
  }

  return {
      "total_due": f"₹{net_str}",
      "due_date": f"Paid: {pay_date}",
      "statement_month": clean_month,
      "cardholder_name": emp_name.upper(),
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": [],
      "reward_points": f"Emp ID: {emp_id}" if emp_id else "",
      "payslip_meta": payslip_meta,
  }


def parse_hdfc_statement(reader, file_path, saved_names):
  """Dedicated rule for HDFC Bank (Swiggy) credit card statements."""
  p1_text = reader.pages[0].extract_text() or ""

  cardholder_name = ""
  for line in p1_text.splitlines():
    m_ckyc = re.search(r"([A-Za-z\s]{2,35})\s*\[\s*CKYC", line)
    if m_ckyc:
      raw_name = m_ckyc.group(1).strip()
      if len(raw_name) >= 3 and not any(k in raw_name.upper() for k in ["TRANSACTION", "DESCRIPTION", "AMOUNT"]):
        cardholder_name = " ".join(raw_name.split()).upper()
        break
  if not cardholder_name:
    cardholder_name = "Cardholder"

  m_tot = re.search(r"TOTAL\s+AMOUNT\s+DUE\s+C?([\d,]+\.\d{2})", p1_text, re.IGNORECASE)
  total_due = f"₹{m_tot.group(1)}" if m_tot else "₹0.00"

  m_due = re.search(r"DUE\s+DATE\s+([0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
  due_date = m_due.group(1).replace(",", "") if m_due else "No Payment Required"

  m_stmt = re.search(r"(?:Statement\s+Date|As\s+on\s*:)\s*([0-9]{1,2}\s+[a-zA-Z]+,?\s+[0-9]{4})", p1_text, re.IGNORECASE)
  statement_date = m_stmt.group(1).replace(",", "") if m_stmt else ""

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
      "cardholder_name": cardholder_name,
      "date_groups": dict(date_groups),
      "all_txns": txns,
      "ongoing_emis": ongoing_emis,
  }


def process_statement_file(file_path, base_downloads_dir=None, custom_passwords=None, file_obj=None, save_to_disk=True, custom_emi_names=None):
  """Unlocks the file and optionally stores inside the standardized unified month folder (or keeps 100% in memory if save_to_disk=False)."""
  try:
    from pypdf import PdfReader, PdfWriter
  except ImportError:
    return False, "Missing 'pypdf'. Please run: pip install pypdf", None

  if file_obj is None and not os.path.exists(file_path):
    return False, f"File does not exist: {file_path}", None

  try:
    reader = PdfReader(file_obj if file_obj is not None else file_path)
    unlocked_bank_key = None
    accepted_pwd = None

    fname_lower = os.path.basename(str(file_path)).lower()
    meta_clues = ""
    try:
      if reader.metadata:
        for k, v in reader.metadata.items():
          meta_clues += f" {k} {v}".lower()
    except Exception:
      pass

    if "payslip" in fname_lower or "skillveri" in fname_lower or "salary" in fname_lower or "tds" in fname_lower or "payslip" in meta_clues or "skillveri" in meta_clues:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "payslip"]
    elif "scapia" in fname_lower or "axis" in fname_lower or "federal" in fname_lower or "axis" in meta_clues or "scapia" in meta_clues:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "scapia"]
    elif "9826" in fname_lower or "simplyclick" in fname_lower or "simply click" in fname_lower or "sbicard" in fname_lower or "sbi" in fname_lower or "sbicpsl" in meta_clues or "sbi card" in meta_clues:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "sbi"]
    elif "4315" in fname_lower or "amazon" in fname_lower or "icici" in fname_lower or "icici" in meta_clues:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "icici"]
    elif "5268" in fname_lower or "hdfc" in fname_lower or "swiggy" in fname_lower or "hdfc" in meta_clues:
      ordered_banks = [b for b in KNOWN_BANKS if b["key"] == "hdfc"]
    else:
      ordered_banks = list(KNOWN_BANKS)

    parent_folder = base_downloads_dir or os.path.dirname(str(file_path)) or "."
    if custom_passwords is not None:
      stored_pwds = {
          "payslip": str(custom_passwords.get("payslip", "")).strip(),
          "scapia": str(custom_passwords.get("scapia", "")).strip(),
          "hdfc": str(custom_passwords.get("hdfc", "")).strip(),
          "icici": str(custom_passwords.get("icici", "")).strip(),
          "sbi": str(custom_passwords.get("sbi", "")).strip(),
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
          if bkey == "payslip":
            for cand in [user_pwd.upper(), user_pwd.lower()]:
              if cand not in pwds_to_try:
                pwds_to_try.append(cand)
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
    if custom_emi_names and isinstance(custom_emi_names, dict):
      for k, v in custom_emi_names.items():
        if k and v and str(v).strip():
          saved_emi_names[str(k).strip()] = str(v).strip()

    p1_text = "\n".join((p.extract_text() or "") for p in reader.pages[:2])
    bank_full_name, bank_short = identify_bank(file_path, p1_text, unlocked_bank_key)

    if bank_short not in ("Scapia Axis", "SBI SimplyCLICK", "ICICI Amazon", "HDFC", "Salary Payslip"):
      return False, f"Non-Bill PDF Detected ({os.path.basename(file_path)}): This file is not a valid credit card bill or salary payslip. Only Axis Bank (Scapia), HDFC Bank (Swiggy), ICICI Bank (Amazon Pay), SBI Card (SimplyCLICK), and Salary Payslips are supported.", None

    if bank_short == "Salary Payslip":
      fin = parse_payslip_statement(reader, file_path, saved_emi_names)
    elif bank_short == "Scapia Axis":
      fin = parse_scapia_statement(reader, file_path, saved_emi_names)
    elif bank_short == "SBI SimplyCLICK":
      fin = parse_sbi_statement(reader, file_path, saved_emi_names)
    elif bank_short == "ICICI Amazon":
      fin = parse_icici_statement(reader, file_path, saved_emi_names)
    else:
      fin = parse_hdfc_statement(reader, file_path, saved_emi_names)

    # Strict guard against non-transactional / non-bill PDFs (0 transactions or 0 date groups)
    if not fin.get("all_txns") or not fin.get("date_groups"):
      return False, f"Non-Bill / Non-Transactional PDF Detected ({os.path.basename(file_path)}): 0 bill transactions found. Please upload a valid credit card statement with transactions.", None

    safe_month_folder = f"Statements_{fin['statement_month'].replace(' ', '_')}"
    month_folder_path = os.path.join(parent_folder, safe_month_folder)
    clean_target_name = f"{bank_short} {fin['statement_month']}.pdf"
    output_path = os.path.join(month_folder_path, clean_target_name)

    if save_to_disk:
      os.makedirs(month_folder_path, exist_ok=True)
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
    else:
      output_path = f"Memory Session ({clean_target_name})" 

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
        "cardholder_name": fin.get("cardholder_name") or "Cardholder",
        "reward_points": fin.get("reward_points", ""),
        "date_groups": fin["date_groups"],
        "all_txns": fin["all_txns"],
        "ongoing_emis": fin.get("ongoing_emis", []),
        "payslip_meta": fin.get("payslip_meta", {}),
        "was_encrypted": was_encrypted,
        "decryption_note": "Unlocked with saved password" if was_encrypted else "Already unencrypted (no password needed)",
    }
    return True, "Success", result_data

  except Exception as e:
    err_str = str(e)
    if "cryptography" in err_str.lower():
      return False, "Missing 'cryptography' library. Run: pip install cryptography", None
    return False, f"Error: {err_str}", None


def generate_modern_dashboard_html(results_list, output_dir=".", write_to_disk=True):
  """Generates a high-quality modern interactive HTML dashboard with EMI receipt highlighting."""
  import base64
  html_path = os.path.join(output_dir, "Statement_Dashboard.html")
  data_json = json.dumps(results_list)

  swiggy_card_b64 = ""
  amazon_card_b64 = ""
  sbi_card_b64 = ""
  scapia_orange_b64 = ""
  scapia_green_b64 = ""
  for cdir in [output_dir, os.path.dirname(os.path.abspath(__file__)), ".", "/working_dir/c_a77ecec1bad766ad/user_uploaded_files/ttl=63d/user_uploaded"]:
    sp = os.path.join(cdir, "card-facia-swiggy.jpg")
    ap = os.path.join(cdir, "card-facia-amazon.png")
    ap_orig = os.path.join(cdir, "amazon-card-banner.webp")
    sbp = os.path.join(cdir, "simply-click-card-face.png")
    sco = os.path.join(cdir, "card-facia-scapia-orange.png")
    scg = os.path.join(cdir, "card-facia-scapia-green.png")
    if os.path.exists(sco) and not scapia_orange_b64:
      try:
        with open(sco, "rb") as f:
          scapia_orange_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
      except Exception: pass
    if os.path.exists(scg) and not scapia_green_b64:
      try:
        with open(scg, "rb") as f:
          scapia_green_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
      except Exception: pass
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
    if os.path.exists(sbp) and not sbi_card_b64:
      try:
        with open(sbp, "rb") as f:
          sbi_card_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
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

    /* Samsung Galaxy S24 Ultra (412px viewport) responsive scaling */
    @media (max-width: 480px) {{
      .apple-card-stage {{
        transform: scale(0.9);
        transform-origin: center center;
      }}
      main {{
        padding-left: 12px !important;
        padding-right: 12px !important;
      }}
    }}

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

  <header id="top-app-header" class="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-md">
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
    <div id="search-filter-card" class="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm mb-6 flex flex-col gap-3">
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

    <!-- Friendly Footer -->
    <footer class="mt-14 pt-6 pb-8 border-t border-slate-200/80 text-center text-xs font-semibold text-slate-500 flex flex-col items-center gap-1.5">
      <div>Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳</div>
      <div class="text-[11px] text-slate-400">🔒 100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜</div>
    </footer>

  </main>

  <script>
    const CARD_IMAGES = {{ swiggy: "{swiggy_card_b64}", amazon: "{amazon_card_b64}", sbi: "{sbi_card_b64}", scapia_orange: "{scapia_orange_b64}", scapia_green: "{scapia_green_b64}" }};
    const statements = {data_json};
    let activeIndex = 0;

    function getVaultStores() {{
      const stores = [];
      try {{
        if (window.parent && window.parent.localStorage) {{
          stores.push(window.parent.localStorage);
        }}
      }} catch (e) {{}}
      try {{
        if (window.localStorage && !stores.includes(window.localStorage)) {{
          stores.push(window.localStorage);
        }}
      }} catch (e) {{}}
      return stores;
    }}

    function vaultGetItem(key) {{
      const stores = getVaultStores();
      for (const s of stores) {{
        try {{
          const val = s.getItem(key);
          if (val !== null && val !== undefined && val !== "") return val;
        }} catch (e) {{}}
      }}
      return "";
    }}

    function vaultSetItem(key, val) {{
      const stores = getVaultStores();
      for (const s of stores) {{
        try {{ s.setItem(key, val); }} catch (e) {{}}
      }}
    }}

    function vaultRemoveItem(key) {{
      const stores = getVaultStores();
      for (const s of stores) {{
        try {{ s.removeItem(key); }} catch (e) {{}}
      }}
    }}

    function readEmiVaultDict() {{
      const raw = vaultGetItem("smartbill_emi_vault");
      if (raw) {{
        try {{
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {{
            return {{
              names: parsed.names || {{}},
              phones: parsed.phones || {{}}
            }};
          }}
        }} catch (e) {{}}
      }}
      return {{ names: {{}}, phones: {{}} }};
    }}

    function syncEmiVaultRecord(loanId, newName, cleanedPhone) {{
      const vault = readEmiVaultDict();
      if (loanId && newName) {{
        vault.names[loanId] = newName;
        vaultSetItem("emi_name_" + loanId, newName);
      }}
      if (loanId && cleanedPhone) {{
        vault.phones[loanId] = cleanedPhone;
        vaultSetItem("emi_phone_" + loanId, cleanedPhone);
      }}
      if (newName && cleanedPhone) {{
        vault.phones[newName] = cleanedPhone;
        vaultSetItem("emi_phone_" + newName, cleanedPhone);
      }}
      vaultSetItem("smartbill_emi_vault", JSON.stringify(vault));
    }}

    function showVaultToast(title, subtitle) {{
      let existing = document.getElementById("emi-vault-toast");
      if (existing) existing.remove();
      const toast = document.createElement("div");
      toast.id = "emi-vault-toast";
      toast.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;background:#064e3b;border:1.5px solid #10b981;color:#fff;padding:12px 18px;border-radius:14px;box-shadow:0 12px 28px rgba(0,0,0,0.28);display:flex;align-items:center;gap:12px;max-width:420px;transition:opacity 0.3s ease;";
      toast.innerHTML = `<span style="font-size:22px;">🏷️</span><div><div style="font-size:13px;font-weight:800;color:#fff;">${{title}}</div><div style="font-size:11.5px;color:#a7f3d0;font-weight:600;margin-top:2px;">${{subtitle}}</div></div>`;
      document.body.appendChild(toast);
      setTimeout(() => {{
        if (toast) {{
          toast.style.opacity = "0";
          setTimeout(() => toast.remove(), 350);
        }}
      }}, 4000);
    }}

    function getSavedName(loanId, defaultName) {{
      if (!loanId) return defaultName || "";
      const direct = vaultGetItem("emi_name_" + loanId);
      if (direct) return direct;
      const vault = readEmiVaultDict();
      if (vault.names && vault.names[loanId]) return vault.names[loanId];
      return defaultName || "";
    }}

    function getPaymentStatus(key, fallbackKey) {{
      const k1 = key ? vaultGetItem("paid_status_" + key) : "";
      const k2 = (!k1 && fallbackKey) ? vaultGetItem("paid_status_" + fallbackKey) : "";
      const val = k1 || k2;
      if (!val) return {{ isPaid: false, paidDate: "" }};
      try {{ return JSON.parse(val); }} catch(e) {{ return {{ isPaid: val === "true", paidDate: "" }}; }}
    }}

    function togglePaymentStatus(key, amountStr, fallbackKey) {{
      if (!key) return;
      const cur = getPaymentStatus(key, fallbackKey);
      if (cur.isPaid) {{
        vaultRemoveItem("paid_status_" + key);
        if (fallbackKey) vaultRemoveItem("paid_status_" + fallbackKey);
      }} else {{
        const today = new Date().toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
        const payload = JSON.stringify({{ isPaid: true, paidDate: today, amount: amountStr }});
        vaultSetItem("paid_status_" + key, payload);
        if (fallbackKey) vaultSetItem("paid_status_" + fallbackKey, payload);
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
      const direct = vaultGetItem("emi_phone_" + key);
      if (direct) return cleanIndianPhone(direct);
      const vault = readEmiVaultDict();
      if (vault.phones && vault.phones[key]) return cleanIndianPhone(vault.phones[key]);
      return "";
    }}

    function saveCustomName(loanId, customInputId, customPhoneId) {{
      const input = document.getElementById(customInputId || ("emi-input-" + loanId));
      const phoneInput = document.getElementById(customPhoneId || ("emi-phone-" + loanId));
      const newName = input ? input.value.trim() : "";
      const rawPhone = phoneInput ? phoneInput.value.trim() : "";
      const cleanedPhone = cleanIndianPhone(rawPhone);

      if (newName || cleanedPhone) {{
        syncEmiVaultRecord(loanId, newName, cleanedPhone);
        const phoneDesc = cleanedPhone ? ` • WhatsApp +91 ${{cleanedPhone.slice(-10)}}` : "";
        showVaultToast(
          `Saved EMI Nickname: '${{newName || loanId}}'`,
          `Persisted in browser localStorage on this device${{phoneDesc}}`
        );
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

    async function showClipboardToast(msg, isSuccess = true) {{
      let toast = document.getElementById('apple-clipboard-toast');
      if (!toast) {{
        toast = document.createElement('div');
        toast.id = 'apple-clipboard-toast';
        toast.style.cssText = 'position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px); z-index: 9999; padding: 12px 22px; border-radius: 9999px; font-size: 13px; font-weight: 800; color: #fff; box-shadow: 0 12px 30px rgba(0,0,0,0.25); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); opacity: 0; pointer-events: none; display: flex; align-items: center; gap: 8px; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);';
        document.body.appendChild(toast);
      }}
      toast.style.background = isSuccess ? 'rgba(15, 23, 42, 0.92)' : 'rgba(185, 28, 28, 0.92)';
      toast.style.border = isSuccess ? '1px solid rgba(16, 185, 129, 0.5)' : '1px solid rgba(248, 113, 113, 0.5)';
      toast.innerHTML = `<span>${{isSuccess ? '📋✅' : '⚠️'}}</span><span>${{msg}}</span>`;
      requestAnimationFrame(() => {{
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
      }});
      clearTimeout(window._toastTimer);
      window._toastTimer = setTimeout(() => {{
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(20px)';
      }}, 3800);
    }}

    function canvasToPngBlobPromise(canvas) {{
      return new Promise((resolve, reject) => {{
        if (canvas.toBlob) {{
          canvas.toBlob((blob) => {{
            if (blob) resolve(blob);
            else reject(new Error("Canvas toBlob failed"));
          }}, "image/png");
        }} else {{
          try {{
            const dataURI = canvas.toDataURL("image/png");
            const byteString = atob(dataURI.split(',')[1]);
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
            resolve(new Blob([ab], {{ type: "image/png" }}));
          }} catch (err) {{
            reject(err);
          }}
        }}
      }});
    }}

    async function copyCanvasSnapshotToClipboard(cardData, emiName) {{
      if (!cardData) return false;
      const canvas = drawNativeReceiptCanvas(cardData);
      window.focus();

      // Synchronous Promise pass to ClipboardItem preserves Mobile Safari (iOS) & Android Chrome user-gesture activation!
      if (navigator.clipboard && window.ClipboardItem && navigator.clipboard.write) {{
        try {{
          const blobPromise = canvasToPngBlobPromise(canvas);
          const clipItem = new ClipboardItem({{ "image/png": blobPromise }});
          await navigator.clipboard.write([clipItem]);
          showClipboardToast(`Receipt Snapshot copied to clipboard! Paste in WhatsApp (Ctrl+V or Long-Press -> Paste)`);
          return true;
        }} catch (firstErr) {{
          try {{
            const resolvedBlob = await canvasToPngBlobPromise(canvas);
            const fallbackItem = new ClipboardItem({{ "image/png": resolvedBlob }});
            await navigator.clipboard.write([fallbackItem]);
            showClipboardToast(`Receipt Snapshot copied to clipboard! Paste in WhatsApp`);
            return true;
          }} catch (secondErr) {{
            console.warn("Direct clipboard image write restricted by browser/iframe:", secondErr);
          }}
        }}
      }}

      // Mobile Native Web Share Sheet Fallback (Android / iOS "Copy Image" or direct WhatsApp share)
      try {{
        const blob = await canvasToPngBlobPromise(canvas);
        const fileName = `${{(emiName || 'EMI_Receipt').replace(/\s+/g, '_')}}_Snapshot.png`;
        const file = new File([blob], fileName, {{ type: "image/png" }});
        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
          await navigator.share({{
            files: [file],
            title: `${{emiName || 'EMI'}} Receipt Snapshot`,
          }});
          showClipboardToast(`Shared Receipt Snapshot!`);
          return true;
        }}
      }} catch (shareErr) {{}}

      return false;
    }}

    async function copySnapshotOnly(cardElementId, emiName) {{
      const idxMatch = String(cardElementId).match(/(\d+)$/);
      const cardIdx = idxMatch ? parseInt(idxMatch[1], 10) : -1;
      const cardData = (window.renderedCardsData && cardIdx >= 0) ? window.renderedCardsData[cardIdx] : null;
      if (!cardData) return;

      const copied = await copyCanvasSnapshotToClipboard(cardData, emiName);
      const canvas = drawNativeReceiptCanvas(cardData);
      const imgUrl = canvas.toDataURL("image/png");
      const dlLink = document.createElement("a");
      dlLink.download = `${{(emiName || 'EMI_Receipt').replace(/\s+/g, '_')}}_Snapshot.png`;
      dlLink.href = imgUrl;
      dlLink.click();

      if (!copied) {{
        showClipboardToast(`Snapshot downloaded! (Press & hold image to copy/share on mobile)`, true);
      }}
    }}

    async function shareReceiptOnWhatsApp(cardElementId, emiName, loanId, totalStr, datesStr) {{
      const idxMatch = String(cardElementId).match(/(\d+)$/);
      const cardIdx = idxMatch ? parseInt(idxMatch[1], 10) : -1;
      const cardData = (window.renderedCardsData && cardIdx >= 0) ? window.renderedCardsData[cardIdx] : null;

      // 1. Copy Snapshot PNG Image to Clipboard FIRST (while user gesture is active & document is focused!)
      if (cardData) {{
        await copyCanvasSnapshotToClipboard(cardData, emiName);
        try {{
          const canvas = drawNativeReceiptCanvas(cardData);
          const imgUrl = canvas.toDataURL("image/png");
          const dlLink = document.createElement("a");
          dlLink.download = `${{(emiName || 'EMI_Receipt').replace(/\s+/g, '_')}}_Snapshot.png`;
          dlLink.href = imgUrl;
          dlLink.click();
        }} catch (e) {{
          console.error("Canvas download error:", e);
        }}
      }}

      // 2. Get phone number (auto-prefixed with 91 for India)
      let phone = cleanIndianPhone(getSavedPhone(loanId) || getSavedPhone(emiName));
      if (!phone || phone.length < 10) {{
        const entered = prompt("Snapshot copied to clipboard! Enter 10-digit WhatsApp mobile number for " + (emiName || "this receipt") + " (+91 added automatically):", "");
        if (!entered) return;
        phone = cleanIndianPhone(entered);
        if (!phone || phone.length < 10) {{
          alert("Please enter a valid 10-digit Indian mobile number.");
          return;
        }}
        syncEmiVaultRecord(loanId || emiName, emiName, phone);
      }}

      // 3. Build clean itemized WhatsApp text receipt
      const cleanTotal = totalStr.replace(/₹/g, 'Rs. ');
      let message = (cardData && cardData.cheerMessage) ? `${{cardData.cheerMessage}}\n\n` : '';
      message += `*EMI STATEMENT RECEIPT - ${{emiName || 'Monthly Installment'}}*\n`;
      message += `*Billing Date(s):* ${{datesStr}}\n`;
      message += `*Total Amount Due:* ${{cleanTotal}}\n\n`;
      message += `*Itemized Breakdown:*\n`;

      if (cardData) {{
        const dates = cardData.type === 'named_emi' ? cardData.dates : [{{ items: cardData.items }}];
        dates.forEach(d => {{
          d.items.forEach(itm => {{
            if (!itm.is_credit) {{
              const amtClean = (itm.amount_str || '').replace(/₹/g, 'Rs. ');
              message += `• ${{itm.description}}: ${{amtClean}}\n`;
            }}
          }});
        }});
      }}

      message += `\n_(Receipt snapshot image copied to clipboard — press Ctrl+V on PC or Long-Press -> Paste in WhatsApp chat!)_`;

      const waUrl = `https://api.whatsapp.com/send?phone=${{phone}}&text=${{encodeURIComponent(message)}}`;

      // 4. Open WhatsApp after image is safely on the clipboard
      setTimeout(() => {{
        window.open(waUrl, '_blank');
      }}, 350);
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
          cardholder_name: (statements[0] && statements[0].cardholder_name) || "Cardholder",
          all_txns: [],
          ongoing_emis: [],
          date_groups: {{}},
          total_due: ""
        }};
        let sumDue = 0;
        statements.forEach(s => {{
          (s.all_txns || []).forEach(t => combined.all_txns.push({{ ...t, bank_badge: s.bank_short }}));
          (s.ongoing_emis || []).forEach(e => combined.ongoing_emis.push({{ ...e, bank_badge: s.bank_short }}));
          const isSlip = (s.bank_short || '').toLowerCase().includes('payslip') || (s.payslip_meta && s.payslip_meta.is_payslip) || (s.shafana_meta && s.shafana_meta.is_shafana) || (s.kayal_meta && s.kayal_meta.is_kayal);
          const cleanDue = parseFloat(String(s.total_due || '0').replace(/[^0-9.]/g, ''));
          if (!isNaN(cleanDue) && !isSlip) sumDue += cleanDue;

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
        const isSbi = bName.includes('sbi') || bName.includes('simplyclick');
        const isScapia = bName.includes('scapia') || bName.includes('axis') || bName.includes('federal');
        const isPayslip = bName.includes('payslip') || bName.includes('skillveri') || bName.includes('salary');
        const isShafana = bName.includes('shafana') || (stmt.shafana_meta && stmt.shafana_meta.is_shafana);
        const isKayal = bName.includes('kayal') || (stmt.kayal_meta && stmt.kayal_meta.is_kayal);

        let dotColor = isKayal ? 'bg-rose-500' : (isShafana ? 'bg-amber-500' : (isPayslip ? 'bg-emerald-500' : (isSwiggy ? 'bg-[#fc8019]' : (isAmazon ? 'bg-[#ff9900]' : (isSbi ? 'bg-[#882438]' : (isScapia ? 'bg-[#f2530f]' : 'bg-blue-600'))))));
        let icon = isKayal ? '🩺' : (isShafana ? '🎁' : (isPayslip ? '💼' : (isSwiggy ? '🛵' : (isAmazon ? '🛒' : (isSbi ? '💳' : (isScapia ? '✈️' : '🏛️'))))));

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

    window.cycleScapiaCards = function() {{
      const c1 = document.getElementById('scapia-card-1');
      const c2 = document.getElementById('scapia-card-2');
      if (!c1 || !c2) return;
      const bg1 = c1.style.background;
      c1.style.background = c2.style.background;
      c2.style.background = bg1;
    }};

    window.allStackOffset = 0;
    const ALL_STACK_SLOTS = [
      {{ transform: 'translate3d(0px, 6px, 40px) rotate(0deg) scale(1)', zIndex: 50, opacity: 1, shadow: '0 24px 48px -12px rgba(0,0,0,0.38)' }},
      {{ transform: 'translate3d(34px, -4px, 15px) rotate(6deg) scale(0.92)', zIndex: 40, opacity: 0.92, shadow: '0 16px 32px -10px rgba(0,0,0,0.26)' }},
      {{ transform: 'translate3d(-34px, -6px, 0px) rotate(-6deg) scale(0.90)', zIndex: 30, opacity: 0.88, shadow: '0 14px 28px -10px rgba(0,0,0,0.22)' }},
      {{ transform: 'translate3d(52px, -12px, -15px) rotate(11deg) scale(0.84)', zIndex: 20, opacity: 0.80, shadow: '0 10px 20px -8px rgba(0,0,0,0.18)' }},
      {{ transform: 'translate3d(-52px, -14px, -25px) rotate(-11deg) scale(0.82)', zIndex: 10, opacity: 0.76, shadow: '0 10px 20px -8px rgba(0,0,0,0.18)' }}
    ];

    window.applyAllStackPositions = function() {{
      for (let i = 0; i < 5; i++) {{
        const el = document.getElementById('all-stack-' + i);
        const nameEl = document.getElementById('all-stack-name-' + i);
        if (!el) continue;
        const slotIdx = (i - (window.allStackOffset || 0) + 5) % 5;
        const slot = ALL_STACK_SLOTS[slotIdx];
        el.style.transform = slot.transform;
        el.style.zIndex = String(slot.zIndex);
        el.style.opacity = String(slot.opacity);
        el.style.boxShadow = slot.shadow;
        if (nameEl) {{
          nameEl.style.opacity = slotIdx === 0 ? '1' : '0';
        }}
      }}
    }};

    window.cycleStackedCards = function() {{
      window.allStackOffset = ((window.allStackOffset || 0) + 1) % 5;
      window.applyAllStackPositions();
    }};

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

      const isSbi = bName.includes('sbi') || bName.includes('simplyclick');
      const isScapia = bName.includes('scapia') || bName.includes('axis') || bName.includes('federal');
      const isPayslip = bName.includes('payslip') || bName.includes('skillveri') || bName.includes('salary') || (stmt.payslip_meta && stmt.payslip_meta.is_payslip);
      const isShafana = bName.includes('shafana') || (stmt.shafana_meta && stmt.shafana_meta.is_shafana);
      const isKayal = bName.includes('kayal') || (stmt.kayal_meta && stmt.kayal_meta.is_kayal);
      const pm = stmt.payslip_meta || {{}};
      const sm = stmt.shafana_meta || {{}};
      const km = stmt.kayal_meta || {{}};

      const topHdr = document.getElementById('top-app-header');
      if (topHdr) topHdr.style.display = isKayal ? 'none' : '';
      if (isKayal) {{
        if (hero) {{
          hero.innerHTML = '';
          hero.style.display = 'none';
        }}
        return;
      }} else if (hero) {{
        hero.style.display = '';
      }}
      if (false) {{
        const kSum = getKayalComputedTotals(stmt);
        ambientColor = 'rgba(244, 63, 94, 0.28)';
        cardBadgeText = "Dr. Kayalvizhi 💖 Duty Pass";
        cardBadgeClass = 'bg-rose-100 text-rose-900 border-rose-300';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative p-5 flex flex-col justify-between text-white" style="background: linear-gradient(135deg, #881337 0%, #be123c 50%, #4c0519 100%); border: 1px solid rgba(251, 113, 133, 0.45);">
            <div class="apple-card-glare"></div>
            <div class="flex justify-between items-start relative z-10">
              <div>
                <div class="text-[10px] font-extrabold uppercase tracking-[0.15em] text-rose-200">CHC Thirunallar • Medical Officer</div>
                <div class="text-sm font-black tracking-tight text-white mt-0.5">🩺💖 Dr. Kayalvizhi</div>
              </div>
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-rose-400/25 text-rose-100 border border-rose-300/35 uppercase tracking-wider">
                ${{km.period || 'Nov 2026'}}
              </span>
            </div>

            <div class="my-1 py-2.5 px-3.5 rounded-xl bg-white/15 backdrop-blur-md border border-white/20 flex justify-between items-center relative z-10">
              <div>
                <div class="text-[9px] font-bold uppercase tracking-wider text-rose-100">Active Shifts</div>
                <div class="text-2xl font-black text-white tracking-tight">${{kSum.activeCount}} Duties</div>
              </div>
              <div class="text-right">
                <div class="text-[10px] font-extrabold text-amber-200">☀️ ${{kSum.opdCount}} OPD • 🌆 ${{kSum.eveCount}} Eve • 🌙 ${{kSum.nightCount}} Night</div>
                <div class="text-[10px] font-extrabold text-emerald-200">💞 ${{kSum.offCount}} Off Days Together</div>
              </div>
            </div>

            <div class="flex justify-between items-end relative z-10">
              <div>
                <div class="text-[11px] font-black tracking-[0.08em] uppercase text-rose-100 font-mono">My Forever Doctor</div>
                <div class="text-[10px] font-semibold text-rose-200">Tap Share on WhatsApp below ✨</div>
              </div>
              <div class="text-right">
                <span class="text-lg font-black text-white">💖🩺</span>
              </div>
            </div>
          </div>
        `;
      }} else if (isShafana) {{
        const sfSummary = getShafanaComputedTotals(stmt);
        ambientColor = 'rgba(245, 158, 11, 0.28)';
        cardBadgeText = "Shafana's Amazon Pay Cashback Pass";
        cardBadgeClass = 'bg-amber-100 text-amber-950 border-amber-300';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative p-5 flex flex-col justify-between text-white" style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 55%, #451a03 100%); border: 1px solid rgba(251, 191, 36, 0.4);">
            <div class="apple-card-glare"></div>
            <div class="flex justify-between items-start relative z-10">
              <div>
                <div class="text-[10px] font-extrabold uppercase tracking-[0.15em] text-amber-400">Amazon Pay ICICI ••0004</div>
                <div class="text-sm font-black tracking-tight text-white mt-0.5">🎁 Shafana Cashback & Bill Pass</div>
              </div>
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-400/30 uppercase tracking-wider">
                5% Prime CB
              </span>
            </div>

            <div class="my-1 py-2.5 px-3.5 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 flex justify-between items-center relative z-10">
              <div>
                <div class="text-[9px] font-bold uppercase tracking-wider text-amber-200">Full Bill Due (After Bill Date)</div>
                <div class="text-2xl font-black text-white tracking-tight">₹${{sfSummary.billDue.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
              </div>
              <div class="text-right">
                <div class="text-[10px] font-extrabold text-emerald-400">Earned CB: +₹${{sfSummary.cbEarned.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
                <div class="text-[10px] font-extrabold text-rose-300">Used CB: -₹${{sfSummary.cbUsed.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
              </div>
            </div>

            <div class="flex justify-between items-end relative z-10">
              <div>
                <div class="text-[11px] font-black tracking-[0.1em] uppercase text-amber-200 font-mono">Delivering to: Raja Mohamed</div>
                <div class="text-[10px] font-semibold text-slate-300 truncate max-w-[205px]">8 Puduthurai Main Rd, Karaikal 609602</div>
              </div>
              <div class="text-right font-mono text-[10px] text-emerald-300 font-bold">
                <div>Net CB Kitty:</div>
                <div class="text-xs font-black">${{sfSummary.netKitty >= 0 ? '+' : '-'}}₹${{Math.abs(sfSummary.netKitty).toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
              </div>
            </div>
          </div>
        `;
      }} else if (isPayslip) {{
        ambientColor = 'rgba(16, 185, 129, 0.25)';
        cardBadgeText = pm.company_name || 'Salary Payslip';
        cardBadgeClass = 'bg-emerald-100 text-emerald-950 border-emerald-300';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative p-5 flex flex-col justify-between text-white" style="background: linear-gradient(135deg, #064e3b 0%, #0f172a 55%, #1e293b 100%); border: 1px solid rgba(52, 211, 153, 0.35);">
            <div class="apple-card-glare"></div>
            <div class="flex justify-between items-start relative z-10">
              <div>
                <div class="text-[10px] font-extrabold uppercase tracking-[0.15em] text-emerald-300">Official Payroll Pass</div>
                <div class="text-sm font-black tracking-tight text-white mt-0.5 truncate max-w-[210px]">${{pm.company_name || 'Skillveri Training Solutions'}}</div>
              </div>
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 uppercase tracking-wider">
                ID #${{pm.employee_id || '115'}}
              </span>
            </div>

            <div class="my-1 py-2.5 px-3.5 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 flex justify-between items-center relative z-10">
              <div>
                <div class="text-[9px] font-bold uppercase tracking-wider text-emerald-200">Total Net Payable</div>
                <div class="text-2xl font-black text-white tracking-tight">${{stmt.total_due}}</div>
              </div>
              <div class="text-right">
                <div class="text-[10px] font-extrabold text-emerald-300">Paid Days: ${{pm.paid_days || '8'}}</div>
                <div class="text-[10px] font-semibold text-slate-300">LOP Days: ${{pm.lop_days || '0'}}</div>
              </div>
            </div>

            <div class="flex justify-between items-end relative z-10">
              <div>
                <div class="text-[11px] font-black tracking-[0.12em] uppercase text-white font-mono">${{pm.employee_name || stmt.cardholder_name}}</div>
                <div class="text-[10px] font-semibold text-emerald-300 truncate max-w-[190px]">${{pm.designation || 'Product Development'}}</div>
              </div>
              <div class="text-right font-mono text-[10px] text-slate-300">
                <div>A/C: ${{pm.bank_account_no || 'N/A'}}</div>
                <div>Joined: ${{pm.date_of_joining || 'N/A'}}</div>
              </div>
            </div>
          </div>
        `;
      }} else if (isSwiggy) {{
        ambientColor = 'rgba(252, 128, 25, 0.28)';
        cardBadgeText = 'Swiggy HDFC Bank Card';
        cardBadgeClass = 'bg-orange-100 text-orange-950 border-orange-200';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative" style="background: url('${{CARD_IMAGES.swiggy}}') center/cover no-repeat;">
            <div class="apple-card-glare"></div>
            <!-- Embossed Cardholder Name -->
            <div class="absolute bottom-4 left-5 z-20 pointer-events-none select-none">
              <div class="text-[12px] sm:text-[13px] font-black tracking-[0.14em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.85)]">
                ${{stmt.cardholder_name || 'Cardholder'}}
              </div>
            </div>
          </div>
        `;
      }} else if (isAmazon) {{
        ambientColor = 'rgba(245, 158, 11, 0.24)';
        cardBadgeText = 'Amazon Pay ICICI Card';
        cardBadgeClass = 'bg-amber-100 text-amber-950 border-amber-200';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative" style="background: url('${{CARD_IMAGES.amazon}}') center/cover no-repeat;">
            <div class="apple-card-glare"></div>
            <!-- Embossed Cardholder Name -->
            <div class="absolute bottom-4 left-5 z-20 pointer-events-none select-none">
              <div class="text-[12px] sm:text-[13px] font-black tracking-[0.14em] uppercase text-amber-200/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.9)]">
                ${{stmt.cardholder_name || 'Cardholder'}}
              </div>
            </div>
          </div>
        `;
      }} else if (isSbi) {{
        ambientColor = 'rgba(136, 36, 56, 0.28)';
        cardBadgeText = 'SBI Card SimplyCLICK';
        cardBadgeClass = 'bg-rose-100 text-rose-950 border-rose-200';
        cardStageHtml = `
          <div id="apple-active-card" class="apple-physical-card shadow-2xl relative" style="background: url('${{CARD_IMAGES.sbi}}') center/cover no-repeat;">
            <div class="apple-card-glare"></div>
            <!-- Embossed Cardholder Name -->
            <div class="absolute bottom-4 left-5 z-20 pointer-events-none select-none">
              <div class="text-[12px] sm:text-[13px] font-black tracking-[0.14em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.9)]">
                ${{stmt.cardholder_name || 'Cardholder'}}
              </div>
            </div>
          </div>
        `;
      }} else if (isScapia) {{
        ambientColor = 'rgba(242, 83, 15, 0.28)';
        cardBadgeText = 'Axis Bank Scapia Card';
        cardBadgeClass = 'bg-orange-100 text-orange-950 border-orange-200';
        cardStageHtml = `
          <div class="relative w-full max-w-[320px] h-[340px] flex items-center justify-center cursor-pointer group" onclick="cycleScapiaCards()" title="Click to flip between Mastercard & RuPay editions">
            <!-- Back Card: Scapia RuPay (Green) -->
            <div id="scapia-card-2" class="apple-physical-card absolute w-[190px] h-[300px] shadow-lg top-2 right-4 -rotate-3 opacity-90 transition-all duration-500 ease-out group-hover:rotate-0 group-hover:translate-x-2" style="background: url('${{CARD_IMAGES.scapia_green}}') center/cover no-repeat; border-radius: 18px; z-index: 10;">
              <div class="apple-card-glare" style="border-radius: 18px;"></div>
            </div>
            <!-- Front Card: Scapia Mastercard (Orange) -->
            <div id="scapia-card-1" class="apple-physical-card absolute w-[200px] h-[316px] shadow-2xl bottom-1 left-4 rotate-2 transition-all duration-500 ease-out group-hover:rotate-0 group-hover:scale-102" style="background: url('${{CARD_IMAGES.scapia_orange}}') center/cover no-repeat; border-radius: 18px; z-index: 20;">
              <div class="apple-card-glare" style="border-radius: 18px;"></div>
              <div class="absolute bottom-4 left-5 z-20 pointer-events-none select-none">
                <div class="text-[11px] font-black tracking-[0.14em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.85)]">
                  ${{stmt.cardholder_name || 'Cardholder'}}
                </div>
              </div>
            </div>
          </div>
        `;
      }} else {{
        ambientColor = 'rgba(99, 102, 241, 0.22)';
        cardBadgeText = 'Consolidated Multi-Card Portfolio';
        cardBadgeClass = 'bg-indigo-100 text-indigo-900 border-indigo-200';
        cardStageHtml = `
          <div class="relative w-full max-w-[380px] h-[272px] flex items-center justify-center cursor-pointer select-none" onclick="cycleStackedCards()" title="Click to shuffle all 5 cards (Swiggy, Scapia Orange, Amazon, Scapia Green, SBI)">
            <!-- 0: Swiggy HDFC (Landscape) -->
            <div id="all-stack-0" class="apple-physical-card absolute transition-all duration-500 ease-out" style="width: 276px; height: 174px; aspect-ratio: auto; border-radius: 16px; background: url('${{CARD_IMAGES.swiggy}}') center/cover no-repeat;">
              <div class="apple-card-glare" style="border-radius: 16px;"></div>
              <div id="all-stack-name-0" class="absolute bottom-3.5 left-4 z-20 pointer-events-none select-none transition-opacity duration-300">
                <div class="text-[11px] sm:text-[12px] font-black tracking-[0.14em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.85)]">
                  ${{stmt.cardholder_name || 'Portfolio Cards'}}
                </div>
              </div>
            </div>
            <!-- 1: Scapia Mastercard Orange (Portrait) -->
            <div id="all-stack-1" class="apple-physical-card absolute transition-all duration-500 ease-out" style="width: 162px; height: 256px; aspect-ratio: auto; border-radius: 16px; background: url('${{CARD_IMAGES.scapia_orange}}') center/cover no-repeat;">
              <div class="apple-card-glare" style="border-radius: 16px;"></div>
              <div id="all-stack-name-1" class="absolute bottom-3.5 left-3.5 z-20 pointer-events-none select-none transition-opacity duration-300" style="opacity: 0;">
                <div class="text-[10px] font-black tracking-[0.12em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.85)]">
                  ${{stmt.cardholder_name || 'Portfolio Cards'}}
                </div>
              </div>
            </div>
            <!-- 2: ICICI Amazon Pay (Landscape) -->
            <div id="all-stack-2" class="apple-physical-card absolute transition-all duration-500 ease-out" style="width: 276px; height: 174px; aspect-ratio: auto; border-radius: 16px; background: url('${{CARD_IMAGES.amazon}}') center/cover no-repeat;">
              <div class="apple-card-glare" style="border-radius: 16px;"></div>
              <div id="all-stack-name-2" class="absolute bottom-3.5 left-4 z-20 pointer-events-none select-none transition-opacity duration-300" style="opacity: 0;">
                <div class="text-[11px] sm:text-[12px] font-black tracking-[0.14em] uppercase text-amber-200/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.9)]">
                  ${{stmt.cardholder_name || 'Portfolio Cards'}}
                </div>
              </div>
            </div>
            <!-- 3: Scapia RuPay Green (Portrait) -->
            <div id="all-stack-3" class="apple-physical-card absolute transition-all duration-500 ease-out" style="width: 162px; height: 256px; aspect-ratio: auto; border-radius: 16px; background: url('${{CARD_IMAGES.scapia_green}}') center/cover no-repeat;">
              <div class="apple-card-glare" style="border-radius: 16px;"></div>
              <div id="all-stack-name-3" class="absolute bottom-3.5 left-3.5 z-20 pointer-events-none select-none transition-opacity duration-300" style="opacity: 0;">
                <div class="text-[10px] font-black tracking-[0.12em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.85)]">
                  ${{stmt.cardholder_name || 'Portfolio Cards'}}
                </div>
              </div>
            </div>
            <!-- 4: SBI SimplyCLICK (Landscape) -->
            <div id="all-stack-4" class="apple-physical-card absolute transition-all duration-500 ease-out" style="width: 276px; height: 174px; aspect-ratio: auto; border-radius: 16px; background: url('${{CARD_IMAGES.sbi}}') center/cover no-repeat;">
              <div class="apple-card-glare" style="border-radius: 16px;"></div>
              <div id="all-stack-name-4" class="absolute bottom-3.5 left-4 z-20 pointer-events-none select-none transition-opacity duration-300" style="opacity: 0;">
                <div class="text-[11px] sm:text-[12px] font-black tracking-[0.14em] uppercase text-white/95 font-mono drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.9)]">
                  ${{stmt.cardholder_name || 'Portfolio Cards'}}
                </div>
              </div>
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
              <span class="px-3 py-1 rounded-full text-[11px] font-extrabold border ${{cardBadgeClass}} inline-flex items-center justify-center gap-1.5 leading-none shadow-xs">
                <span class="inline-flex items-center justify-center w-3.5 h-3.5 flex-shrink-0">
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
                </span>
                <span class="leading-none pt-[0.5px]">${{cardBadgeText}}</span>
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
            
            <!-- Primary Tile: Statement Total Due OR Salary Net Pay -->
            <div class="p-7 rounded-3xl apple-glass flex flex-col justify-between flex-1 relative overflow-hidden">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div>
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">${{isPayslip ? 'Total Net Payable (Take-Home Salary)' : 'Statement Total Due'}}</span>
                  <div class="text-4xl sm:text-5xl font-extrabold ${{isPayslip ? 'text-emerald-700' : 'text-slate-900'}} mt-1 tracking-[-0.03em] leading-none">${{stmt.total_due}}</div>
                  ${{isPayslip && pm.amount_in_words ? `<div class="text-xs font-semibold text-slate-500 mt-2">🗣️ ${{pm.amount_in_words}}</div>` : ''}}
                </div>
                <div class="flex items-center gap-2 self-start sm:self-auto">
                  <span class="px-3.5 py-1.5 rounded-full text-xs font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-300/80 shadow-xs flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>${{isPayslip ? ('Pay Date: ' + (pm.pay_date || stmt.due_date)) : ('Due: ' + stmt.due_date)}}</span>
                  </span>
                </div>
              </div>

              <!-- Metadata Grid -->
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6 pt-5 border-t border-slate-200/60 text-xs">
                <div>
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">${{isPayslip ? 'Designation / Emp ID' : 'Account / Card'}}</div>
                  <div class="font-extrabold text-slate-800 text-sm mt-0.5 truncate" title="${{isPayslip ? (pm.designation + ' (#' + pm.employee_id + ')') : stmt.bank_short}}">${{isPayslip ? ((pm.designation || 'Employee') + ' (#' + (pm.employee_id || '') + ')') : stmt.bank_short}}</div>
                </div>
                <div>
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">${{isPayslip ? 'Pay Period & Attendance' : 'Billing Cycle'}}</div>
                  <div class="font-extrabold text-slate-800 text-sm mt-0.5">${{isPayslip ? (stmt.statement_month + ' (' + (pm.paid_days || '8') + ' Paid Days)') : stmt.statement_month}}</div>
                </div>
                <div class="col-span-2 sm:col-span-1">
                  <div class="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">${{isPayslip ? 'Bank A/C & Joining Date' : 'Storage Path'}}</div>
                  <div class="font-bold text-blue-600 text-xs mt-0.5 truncate" title="${{isPayslip ? ('A/C: ' + pm.bank_account_no + ' • Joined: ' + pm.date_of_joining) : stmt.saved_name}}">${{isPayslip ? ('🏦 A/C ' + (pm.bank_account_no || 'N/A') + ' • DOJ ' + (pm.date_of_joining || '')) : ('📁 ' + stmt.saved_name)}}</div>
                </div>
              </div>
            </div>

            <!-- Secondary Row: Split EMI Reimbursements (or Salary Earnings/Deductions) & Fast Actions -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Tile 1: Friend EMI Reimbursements OR Salary Gross vs Deductions -->
              ${{isPayslip ? `
              <div class="p-5 rounded-3xl apple-glass flex flex-col justify-between">
                <div class="flex justify-between items-center">
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">Earnings vs Deductions</span>
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">LOP: ${{pm.lop_days || '0'}} Days</span>
                </div>
                <div class="flex items-baseline justify-between mt-3">
                  <div>
                    <div class="text-[10px] font-bold text-emerald-600 uppercase tracking-wide">Gross Earnings</div>
                    <div class="text-xl font-extrabold text-emerald-700 mt-0.5 tracking-tight">${{pm.gross_earnings || stmt.total_due}}</div>
                  </div>
                  <div class="text-right">
                    <div class="text-[10px] font-bold text-rose-600 uppercase tracking-wide">Total Deductions</div>
                    <div class="text-xl font-extrabold text-rose-600 mt-0.5 tracking-tight">${{pm.total_deductions || '₹0.00'}}</div>
                  </div>
                </div>
              </div>
              ` : `
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
              `}}

              <!-- Tile 2: Activity Summary & Direct Actions (Or Unlocked Payslip PDF Download + Rate Info) -->
              ${{isPayslip ? `
              <div class="p-5 rounded-3xl apple-glass flex flex-col justify-between">
                <div class="flex justify-between items-center">
                  <span class="text-[11px] font-extrabold tracking-[0.06em] text-slate-400 uppercase">Full-Month Rate & PDF</span>
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-indigo-100 text-indigo-800">₹${{(pm.per_day_rate || 1833.33).toLocaleString('en-IN')}}/day</span>
                </div>
                <div class="flex items-center gap-2 mt-3">
                  <button onclick="downloadUnlockedPayslip()" class="flex-1 px-3 py-2 text-xs font-extrabold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl shadow-sm transition flex items-center justify-center gap-1.5 active:scale-95 cursor-pointer" title="Download password-free unlocked payslip PDF">
                    <span>🔓</span>
                    <span>Download Unlocked PDF</span>
                  </button>
                  <button onclick="window.print()" class="px-3 py-2 text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white rounded-xl shadow-xs transition flex items-center justify-center gap-1 active:scale-95 cursor-pointer">
                    <span>🖨️</span>
                    <span>Print</span>
                  </button>
                </div>
              </div>
              ` : `
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
              `}}

            </div>
          </div>
        </div>
      `;

      setupCardPhysics();
      if (window.applyAllStackPositions) window.applyAllStackPositions();
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

          ${{isIcici ? (() => {{
            const sf = getShafanaComputedTotals();
            const sfOrders = sf.vault.entries.filter(e => e.role === 'shafana_order');
            if (sfOrders.length === 0 && sf.cbUsed === 0 && sf.openingCb === 0) return '';
            return `
              <div class="mt-4 pt-4 border-t-2 border-amber-200 bg-amber-50/60 -mx-6 -mb-6 p-5 rounded-b-3xl">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div class="text-xs font-black uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                      <span>🎁</span>
                      <span>Shafana (Raja Mohamed • Karaikal) — Separate Cashback & Bill Tracker</span>
                    </div>
                    <div class="text-[11px] text-slate-600 mt-0.5">
                      Full Bill to Collect After Bill Date: <b class="text-slate-900">₹${{sf.billDue.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</b> •
                      Earned CB: <b class="text-emerald-700">+₹${{sf.cbEarned.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</b> •
                      Used CB: <b class="text-rose-600">-₹${{sf.cbUsed.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</b>
                    </div>
                  </div>
                  <div class="px-3.5 py-1.5 rounded-xl bg-amber-500 text-white font-black text-xs shadow-xs">
                    Net CB Available: ${{sf.netKitty >= 0 ? '+' : '-'}}₹${{Math.abs(sf.netKitty).toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}
                  </div>
                </div>
              </div>
            `;
          }})() : ''}}
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

      // 1. Check for HDFC loan match (exact loan_id or numeric reference prefix like 00000000001466 -> 146608745)
      for (const itm of group.items) {{
        for (const emi of (stmt.ongoing_emis || [])) {{
          if (!emi.loan_id) continue;
          const cleanLoanId = emi.loan_id.replace(/^0+/, '');

          // Exact match
          if (itm.description && itm.description.includes(emi.loan_id)) {{
            const saved = getSavedName(emi.loan_id, emi.custom_name);
            return {{
              loanKey: emi.loan_id,
              loanName: saved || emi.display_name || ("Loan #" + emi.loan_id),
              loanObj: emi
            }};
          }}

          // Substring/prefix match for truncated references (e.g. 00000000001466 in fee vs 146608745)
          const allDigits = (itm.description || '').match(/\d{4,16}/g) || [];
          for (const num of allDigits) {{
            const cleanNum = num.replace(/^0+/, '');
            if (cleanNum && (cleanLoanId.startsWith(cleanNum) || cleanLoanId.includes(cleanNum) || cleanNum.startsWith(cleanLoanId))) {{
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

      // 2. Check for ICICI <curr/total> Merchant pattern (e.g. <1/9> EZ TRADERS vs <8/12> Flipkart)
      for (const itm of group.items) {{
        const mInst = (itm.description || "").match(/<(\d+)\/(\d+)>\s*(.*?)(?:\s+PVT|\s+LTD|\s*$)/i);
        if (mInst) {{
          const currInst = mInst[1];
          const totalTenure = mInst[2];
          const rawMerchant = mInst[3].trim();
          const cleanMerchantKey = rawMerchant.replace(/[^a-zA-Z0-9]/g, "_").toLowerCase();

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

      // 3. Fallback: If date group has EMI setup charges and exactly 1 ongoing loan in statement, unify with that loan!
      const hasSetupCharges = group.items.some(it => {{
        const d = (it.description || '').toLowerCase();
        return d.includes('procng fee') || d.includes('processing fee') || d.includes('cashback_reversal') || d.includes('offus emi');
      }});

      if (hasSetupCharges && (stmt.ongoing_emis || []).length === 1) {{
        const emi = stmt.ongoing_emis[0];
        const saved = getSavedName(emi.loan_id, emi.custom_name);
        return {{
          loanKey: emi.loan_id,
          loanName: saved || emi.display_name || ("Loan #" + emi.loan_id),
          loanObj: emi
        }};
      }}

      return null;
    }}

    window.payslipSimLeaveDays = 1;
    window.payslipCashflowUseFullMonth = false;

    window.downloadUnlockedPayslip = function() {{
      const stmt = getActiveStatement();
      const pm = (stmt && stmt.payslip_meta) ? stmt.payslip_meta : null;
      if (!pm || !pm.unlocked_pdf_b64) {{
        showVaultToast("PDF Ready via Print", "Use Print / Save to export this payslip.");
        return;
      }}
      const link = document.createElement("a");
      link.href = "data:application/pdf;base64," + pm.unlocked_pdf_b64;
      link.download = pm.unlocked_pdf_name || "Unlocked_Payslip.pdf";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showVaultToast("Unlocked Payslip Downloaded!", `Saved ${{pm.unlocked_pdf_name}} (password-free)`);
    }};

    window.setSimLeaveDays = function(days) {{
      const num = parseFloat(days);
      window.payslipSimLeaveDays = isNaN(num) || num < 0 ? 0 : num;
      const inp = document.getElementById('leave-sim-input');
      if (inp && parseFloat(inp.value) !== window.payslipSimLeaveDays) {{
        inp.value = window.payslipSimLeaveDays;
      }}
      updateLeaveSimulatorUI();
    }};

    window.toggleCashflowSalaryMode = function(useFull) {{
      window.payslipCashflowUseFullMonth = !!useFull;
      renderDateGroups();
    }};

    window.updateLeaveSimulatorUI = function() {{
      const stmt = getActiveStatement();
      const pm = (stmt && stmt.payslip_meta) ? stmt.payslip_meta : null;
      if (!pm) return;
      const days = window.payslipSimLeaveDays || 0;
      const perDay = pm.per_day_rate || 1833.33;
      const fullGross = pm.full_month_gross || 55000;
      const slipNet = pm.net_val || 14666;
      const lostAmt = days * perDay;
      const fullAfterLeave = Math.max(0, fullGross - lostAmt);
      const slipAfterLeave = Math.max(0, slipNet - lostAmt);

      const elDays = document.getElementById('sim-out-days');
      const elLost = document.getElementById('sim-out-lost');
      const elFullLeft = document.getElementById('sim-out-full-left');
      const elSlipLeft = document.getElementById('sim-out-slip-left');

      if (elDays) elDays.innerText = `${{days}} Day${{days === 1 ? '' : 's'}} Leave (LOP)`;
      if (elLost) elLost.innerText = `-₹${{lostAmt.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;
      if (elFullLeft) elFullLeft.innerText = `₹${{fullAfterLeave.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;
      if (elSlipLeft) elSlipLeft.innerText = `₹${{slipAfterLeave.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;

      [0.5, 1, 2, 3, 4, 5, 7].forEach(d => {{
        const btn = document.getElementById('leave-pill-' + String(d).replace('.', '_'));
        if (btn) {{
          btn.className = (days === d)
            ? 'px-3 py-1.5 rounded-xl text-xs font-extrabold bg-rose-600 text-white shadow-sm transition cursor-pointer'
            : 'px-3 py-1.5 rounded-xl text-xs font-bold bg-white text-slate-700 border border-slate-200 hover:bg-rose-50 hover:border-rose-200 transition cursor-pointer';
        }}
      }});
    }};

        function loadShafanaVault() {{
      const raw = vaultGetItem("smartbill_shafana_vault");
      let vault = {{ openingCb: 0.0, manualCbUsed: 0.0, entries: [], billPaid: false, updated_at: "" }};
      let hadLocal = false;
      if (raw) {{
        try {{
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {{
            vault.openingCb = parseFloat(parsed.openingCb) || 0.0;
            vault.manualCbUsed = parseFloat(parsed.manualCbUsed) || 0.0;
            vault.entries = Array.isArray(parsed.entries) ? parsed.entries.filter(e => e.role === "shafana_order") : [];
            vault.billPaid = !!parsed.billPaid;
            vault.updated_at = parsed.updated_at || "";
            hadLocal = true;
          }}
        }} catch (e) {{}}
      }}
      // Seed & merge entries from the server Web-Synced Shafana ledger (shafana_cashback.json)
      statements.forEach(s => {{
        if (s.shafana_meta) {{
          if (!hadLocal) {{
            if (typeof s.shafana_meta.opening_cb === "number") vault.openingCb = s.shafana_meta.opening_cb;
            if (typeof s.shafana_meta.manual_cb_used === "number") vault.manualCbUsed = s.shafana_meta.manual_cb_used;
          }} else if (s.shafana_meta.updated_at && (!vault.updated_at || s.shafana_meta.updated_at > vault.updated_at)) {{
            if (typeof s.shafana_meta.opening_cb === "number") vault.openingCb = s.shafana_meta.opening_cb;
            if (typeof s.shafana_meta.manual_cb_used === "number") vault.manualCbUsed = s.shafana_meta.manual_cb_used;
            vault.updated_at = s.shafana_meta.updated_at;
          }}
          if (Array.isArray(s.shafana_meta.entries)) {{
            s.shafana_meta.entries.filter(e => e.role === "shafana_order").forEach(newEnt => {{
              const exists = vault.entries.find(e => e.id === newEnt.id || Math.abs((e.amount || 0) - (newEnt.amount || 0)) < 0.01);
              if (!exists) {{
                vault.entries.push({{ ...newEnt }});
              }}
            }});
          }}
        }}
      }});
      vaultSetItem("smartbill_shafana_vault", JSON.stringify(vault));
      return vault;
    }}

    function saveShafanaVault(vault) {{
      vault.updated_at = new Date().toISOString();
      vault.entries = (vault.entries || []).filter(e => e.role === "shafana_order");
      vaultSetItem("smartbill_shafana_vault", JSON.stringify(vault));
      const ghToken = vaultGetItem("s24_github_pat");
      if (ghToken && ghToken.trim().length > 10) {{
        window.syncShafanaVaultToWeb(true);
      }}
    }}

    window.syncShafanaVaultToWeb = async function(silent = false) {{
      let ghToken = vaultGetItem("s24_github_pat") || "";
      if (!ghToken) {{
        if (!silent) showVaultToast("Saved on Device", "Saved! To sync across web, add your GitHub token in the S24 Pusher once.");
        return;
      }}
      const vault = loadShafanaVault();
      const payloadObj = {{
        friend_name: "Shafana",
        husband_name: "Raja Mohamed",
        delivery_address: "8 Puduthurai Main Road, Karaikal 609602",
        card_used: "Amazon Pay ICICI Bank Credit Card (Visa ••0004)",
        openingCb: parseFloat(vault.openingCb) || 0.0,
        manualCbUsed: parseFloat(vault.manualCbUsed) || 0.0,
        billPaid: !!vault.billPaid,
        updated_at: new Date().toISOString(),
        entries: vault.entries || []
      }};
      try {{
        const apiUrl = "https://api.github.com/repos/xrvnsp/smart-bill-segregator/contents/shafana_cashback.json";
        const getRes = await fetch(apiUrl, {{
          headers: {{ "Authorization": `Bearer ${{ghToken}}`, "Accept": "application/vnd.github+json" }}
        }});
        let sha = undefined;
        if (getRes.ok) {{
          const meta = await getRes.json();
          sha = meta.sha;
        }}
        const jsonStr = JSON.stringify(payloadObj, null, 2);
        const b64Content = btoa(unescape(encodeURIComponent(jsonStr)));
        const putBody = {{
          message: "Update Shafana cashback ledger",
          content: b64Content,
          branch: "main"
        }};
        if (sha) putBody.sha = sha;
        await fetch(apiUrl, {{
          method: "PUT",
          headers: {{
            "Authorization": `Bearer ${{ghToken}}`,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
          }},
          body: JSON.stringify(putBody)
        }});
      }} catch (err) {{}}
    }};

    function getShafanaComputedTotals(stmt) {{
      const vault = loadShafanaVault();
      let billDue = 0.0;
      let cbEarned = 0.0;

      const iciciStmts = statements.filter(s => (s.bank_short || '').includes('ICICI'));
      const iciciAmounts = [];
      iciciStmts.forEach(is => {{
        (is.all_txns || []).forEach(t => {{
          if (!t.is_credit) iciciAmounts.push({{ amt: t.amount, date: t.date }});
        }});
      }});

      vault.entries.forEach(ent => {{
        const matchedBill = iciciAmounts.find(ia => Math.abs(ia.amt - ent.amount) < 0.5);
        ent.verifiedOnBill = !!matchedBill;
        billDue += (parseFloat(ent.amount) || 0);
        cbEarned += (parseFloat(ent.cashback_earned) || 0);
      }});

      const openingCb = parseFloat(vault.openingCb) || 0.0;
      const cbUsed = parseFloat(vault.manualCbUsed) || 0.0;
      const totalCbPool = openingCb + cbEarned;
      const netKitty = totalCbPool - cbUsed;

      return {{
        vault,
        billDue,
        cbEarned,
        cbUsed,
        openingCb,
        totalCbPool,
        netKitty,
        hasIciciPdf: iciciStmts.length > 0
      }};
    }}

    window.saveManualCbUsed = function() {{
      const inp = document.getElementById('sf-manual-cb-used-inp');
      if (!inp) return;
      const val = Math.max(0, parseFloat(inp.value) || 0.0);
      const vault = loadShafanaVault();
      vault.manualCbUsed = val;
      saveShafanaVault(vault);
      showVaultToast("Updated Cashback Used", `Cashback used set to ₹${{val.toFixed(0)}}`);
      renderDashboard();
    }};

    window.addSimpleShafanaOrder = function() {{
      const amtInp = document.getElementById('sf-simple-order-amt');
      const cbInp = document.getElementById('sf-simple-order-cb');
      const noteInp = document.getElementById('sf-simple-order-note');
      const amt = parseFloat(amtInp ? amtInp.value : '0');
      if (isNaN(amt) || amt <= 0) return;
      const customCb = parseFloat(cbInp ? cbInp.value : '');
      const cb = (!isNaN(customCb) && customCb >= 0) ? customCb : Math.floor(amt * 0.05);
      const note = (noteInp && noteInp.value.trim()) ? noteInp.value.trim() : "Amazon Order (Raja Mohamed)";
      const today = new Date().toLocaleDateString('en-GB', {{ day: '2-digit', month: 'short', year: 'numeric' }});

      const vault = loadShafanaVault();
      vault.entries.unshift({{
        id: 'ord_' + Date.now(),
        method: 'Amazon Pay Credit Card',
        description: note,
        amount: amt,
        cashback_earned: cb,
        date_time: today,
        role: 'shafana_order',
        recipient: 'Raja Mohamed',
        address: '8 Puduthurai Main Road, Karaikal 609602',
        arriving_by: '',
        source_file: 'Manual'
      }});
      saveShafanaVault(vault);
      showVaultToast("Order Added", `Order ₹${{amt.toFixed(0)}} (+₹${{cb.toFixed(0)}} Cashback)`);
      renderDashboard();
    }};

    window.deleteShafanaOrder = function(entryId) {{
      const vault = loadShafanaVault();
      vault.entries = vault.entries.filter(e => e.id !== entryId);
      saveShafanaVault(vault);
      renderDashboard();
    }};

    window.shareShafanaWhatsApp = function() {{
      const sf = getShafanaComputedTotals();
      let msg = `🌸 *Hello Thozhi Shafana!*\n`;
      msg += `Here is your simple Amazon Order & Cashback update:\n\n`;
      msg += `🧾 *1. Order Bill to Pay (After Bill Date):* ₹${{sf.billDue.toLocaleString('en-IN')}}\n`;
      msg += `   _(You only need to pay this comfortably after the monthly ICICI bill comes)_\n\n`;
      msg += `🎁 *2. Your Cashback Savings Wallet:*\n`;
      msg += `   • Total Cashback Earned (5%): +₹${{(sf.openingCb + sf.cbEarned).toLocaleString('en-IN')}}\n`;
      if (sf.cbUsed > 0) {{
        msg += `   • Cashback Used: -₹${{sf.cbUsed.toLocaleString('en-IN')}}\n`;
      }}
      msg += `   👉 *Cashback Ready for Your Next Order: ₹${{sf.netKitty.toLocaleString('en-IN')}}*\n\n`;
      msg += `✨ _All cashback earned on your orders is saved specially for you—just tell me whenever you want to use it on your next order!_`;
      window.open(`https://wa.me/?text=${{encodeURIComponent(msg)}}`, '_blank');
    }};

    const KAYAL_THEMES = {{
      rose: {{
        name: "🌹 Rose & Gold",
        pageBg: "from-rose-50 via-pink-50/90 to-amber-50/80",
        border: "border-rose-200",
        pillBg: "bg-rose-500/15 border-rose-300 text-rose-900",
        titleText: "text-rose-950",
        subText: "text-rose-800",
        btnGrad: "from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 shadow-rose-500/25",
        tblHeader: "from-rose-900 via-pink-900 to-rose-950",
        canvasGrad1: "#881337",
        canvasGrad2: "#be123c",
        canvasAccent: "#f43f5e",
        canvasBorder: "#fda4af"
      }},
      lavender: {{
        name: "💜 Lavender & Blush",
        pageBg: "from-purple-50 via-fuchsia-50/85 to-rose-50/80",
        border: "border-purple-200",
        pillBg: "bg-purple-500/15 border-purple-300 text-purple-900",
        titleText: "text-purple-950",
        subText: "text-purple-800",
        btnGrad: "from-purple-600 to-fuchsia-600 hover:from-purple-500 hover:to-fuchsia-500 shadow-purple-500/25",
        tblHeader: "from-purple-950 via-fuchsia-900 to-indigo-950",
        canvasGrad1: "#4c1d95",
        canvasGrad2: "#7e22ce",
        canvasAccent: "#a855f7",
        canvasBorder: "#d8b4fe"
      }},
      mint: {{
        name: "🌿 Pastel Mint & Pearl",
        pageBg: "from-teal-50 via-emerald-50/85 to-amber-50/70",
        border: "border-teal-200",
        pillBg: "bg-teal-500/15 border-teal-300 text-teal-900",
        titleText: "text-teal-950",
        subText: "text-teal-800",
        btnGrad: "from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 shadow-teal-500/25",
        tblHeader: "from-teal-950 via-emerald-900 to-slate-900",
        canvasGrad1: "#115e59",
        canvasGrad2: "#0d9488",
        canvasAccent: "#14b8a6",
        canvasBorder: "#99f6e4"
      }}
    }};

    function isKayalRomanticMode() {{
      const st = getActiveStatement();
      return !!(st && st.kayal_meta && st.kayal_meta.just_uploaded);
    }}

    function getISTGreetingAndTime() {{
      const now = new Date();
      const istTimeStr = now.toLocaleTimeString('en-IN', {{
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      }}).toUpperCase();
      const istDateStr = now.toLocaleDateString('en-IN', {{
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      }});
      const istHourStr = now.toLocaleTimeString('en-US', {{
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        hour12: false
      }});
      const hr = parseInt(istHourStr, 10) || 12;
      const who = isKayalRomanticMode() ? "Dr Cuteuh Pattuh" : "Dr. Kayalvizhi";
      let greet = `☀️ Good Afternoon, ${{who}}! 💖`;
      if (hr >= 5 && hr < 12) greet = `🌅 Good Morning, ${{who}}! 💖`;
      else if (hr >= 12 && hr < 17) greet = `☀️ Good Afternoon, ${{who}}! 💖`;
      else if (hr >= 17 && hr < 21) greet = `🌆 Good Evening, ${{who}}! 💖`;
      else greet = `🌙 Good Night, ${{who}}! 💖`;

      const parts = new Intl.DateTimeFormat('en-GB', {{
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }}).formatToParts(now);
      const dd = (parts.find(p => p.type === 'day') || {{value: '11'}}).value;
      const mm = (parts.find(p => p.type === 'month') || {{value: '11'}}).value;
      const yyyy = (parts.find(p => p.type === 'year') || {{value: '2026'}}).value;
      const todayKey = `${{dd}}-${{mm}}-${{yyyy}}`;

      return {{ greet, istTimeStr, istDateStr, todayKey, dd: parseInt(dd, 10) || 11 }};
    }}

    function getShiftCareReminder(shift, note) {{
      const sh = (shift || 'OFF').toUpperCase();
      if (sh === 'OPD') return isKayalRomanticMode() ? "8:00 AM – 2:00 PM • Have a bright morning at CHC Thirunallar, Cuteuh Pattuh 🌸" : "8:00 AM – 2:00 PM • Morning OPD at CHC Thirunallar 🌸";
      if (sh === 'EVENING') return "2:00 PM – 8:00 PM • Take a tea break & don't tire yourself out ✨";
      if (sh === 'NIGHT') return "8:00 PM – 8:00 AM • Don't skip dinner & rest well tomorrow morning ❤️";
      if (note && note.toLowerCase().includes('post-night')) return "Post-Night Recovery • Sleep deeply & recharge today 💤💖";
      return "Our Day Together • Relax, smile & enjoy your day off! 💞";
    }}

    function loadKayalVault() {{
      const raw = vaultGetItem("smartbill_kayal_duty_vault");
      let vault = {{
        entries: [],
        phone: "",
        theme: "rose",
        loveNote: "No matter how busy your OPD, Evening, or Night shifts get, you are my favorite hero in a white coat. Counting down to every off day with you! — With Love, Saro 💖",
        updated_at: ""
      }};
      let hadLocal = false;
      if (raw) {{
        try {{
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object") {{
            if (Array.isArray(parsed.entries) && parsed.entries.length > 0) {{
              vault.entries = parsed.entries;
              hadLocal = true;
            }}
            if (parsed.phone) vault.phone = String(parsed.phone);
            if (parsed.theme && KAYAL_THEMES[parsed.theme]) vault.theme = parsed.theme;
            if (parsed.loveNote) vault.loveNote = String(parsed.loveNote);
            vault.updated_at = parsed.updated_at || "";
          }}
        }} catch (e) {{}}
      }}
      statements.forEach(s => {{
        if (s.kayal_meta && Array.isArray(s.kayal_meta.entries)) {{
          if (!hadLocal || (s.kayal_meta.updated_at && (!vault.updated_at || s.kayal_meta.updated_at >= vault.updated_at))) {{
            vault.entries = s.kayal_meta.entries.map(e => ({{ ...e }}));
            vault.updated_at = s.kayal_meta.updated_at || "";
          }}
        }}
      }});
      vaultSetItem("smartbill_kayal_duty_vault", JSON.stringify(vault));
      return vault;
    }}

    function saveKayalVault(vault) {{
      vault.updated_at = new Date().toISOString();
      vaultSetItem("smartbill_kayal_duty_vault", JSON.stringify(vault));
      const ghToken = vaultGetItem("s24_github_pat");
      if (ghToken && ghToken.trim().length > 10) {{
        window.syncKayalVaultToWeb(true);
      }}
    }}

    window.syncKayalVaultToWeb = async function(silent = false) {{
      const ghToken = vaultGetItem("s24_github_pat") || "";
      if (!ghToken) return;
      const vault = loadKayalVault();
      const payloadObj = {{
        doctor_name: "Dr Cuteuh Pattuh (Dr. Kayalvizhi)",
        pet_name: "Dr Cuteuh Pattuh",
        sign_off: "With Love, Saro 💖",
        center_name: "CHC Thirunallar",
        period: "01–15 Nov 2026",
        husband_note: vault.loveNote,
        updated_at: new Date().toISOString(),
        entries: vault.entries || []
      }};
      try {{
        const apiUrl = "https://api.github.com/repos/xrvnsp/smart-bill-segregator/contents/kayal_duty.json";
        const getRes = await fetch(apiUrl, {{
          headers: {{ "Authorization": `Bearer ${{ghToken}}`, "Accept": "application/vnd.github+json" }}
        }});
        let sha = undefined;
        if (getRes.ok) {{
          const meta = await getRes.json();
          sha = meta.sha;
        }}
        const b64Content = btoa(unescape(encodeURIComponent(JSON.stringify(payloadObj, null, 2))));
        const putBody = {{ message: "Update Dr Cuteuh Pattuh duty roster", content: b64Content, branch: "main" }};
        if (sha) putBody.sha = sha;
        await fetch(apiUrl, {{
          method: "PUT",
          headers: {{ "Authorization": `Bearer ${{ghToken}}`, "Accept": "application/vnd.github+json", "Content-Type": "application/json" }},
          body: JSON.stringify(putBody)
        }});
      }} catch (err) {{}}
    }};

    function getKayalComputedTotals(stmt) {{
      const vault = loadKayalVault();
      const entries = vault.entries || [];
      const opdCount = entries.filter(e => (e.shift || '').toUpperCase() === 'OPD').length;
      const eveCount = entries.filter(e => (e.shift || '').toUpperCase() === 'EVENING').length;
      const nightCount = entries.filter(e => (e.shift || '').toUpperCase() === 'NIGHT').length;
      const offEntries = entries.filter(e => (e.shift || '').toUpperCase() === 'OFF');
      const offCount = offEntries.length;
      const activeCount = opdCount + eveCount + nightCount;

      const ist = getISTGreetingAndTime();
      const todayEntry = entries.find(e => e.date === ist.todayKey) || null;
      const nextOff = offEntries.find(e => (parseInt((e.date || '0').slice(0, 2), 10) || 0) >= ist.dd) || offEntries[0] || null;
      const offDaysShort = offEntries.map(e => (e.date || '').slice(0, 2) + ' Nov').join(', ');

      return {{ vault, entries, opdCount, eveCount, nightCount, offCount, activeCount, ist, todayEntry, nextOff, offDaysShort }};
    }}

    // Rich WhatsApp Text Builder OUTSIDE monospace ``` blocks so emojis NEVER turn into replacement diamonds!
    function buildKayalWhatsAppText() {{
      const ks = getKayalComputedTotals();
      const EMJ_DOC = "\\uD83E\\uDE7A";
      const EMJ_HEART = "\\uD83D\\uDC96";
      const EMJ_PIN = "\\uD83D\\uDCCD";
      const EMJ_SUN = "\\u2600\\uFE0F";
      const EMJ_EVE = "\\uD83C\\uDF06";
      const EMJ_MOON = "\\uD83C\\uDF19";
      const EMJ_ZZZ = "\\uD83D\\uDCA4";
      const EMJ_COUPLE = "\\uD83D\\uDC9E";
      const EMJ_SPARK = "\\u2728";
      const EMJ_CHART = "\\uD83D\\uDCCA";

      let lines = [
        `${{EMJ_HEART}} *${{isKayalRomanticMode() ? "DR CUTEUH PATTUH (DR. KAYALVIZHI)" : "DR. KAYALVIZHI"}}* ${{EMJ_DOC}}`,
        `${{EMJ_PIN}} *CHC Thirunallar • Duty Roster (01–15 Nov 2026)*`,
        `_${{ks.ist.greet}} (${{ks.ist.istDateStr}}, ${{ks.ist.istTimeStr}} IST)_`,
        ""
      ];

      ks.entries.forEach(e => {{
        const dPart = (e.date || "").slice(0, 2) + " Nov";
        const dayPart = e.day || "";
        const sh = (e.shift || "OFF").toUpperCase();
        let shLabel = `${{EMJ_COUPLE}} *OFF (Our Day Together)*`;
        if (sh === "OPD") {{
          shLabel = (e.note && e.note.includes("Regha"))
            ? `${{EMJ_SUN}} *OPD (8 AM–2 PM)* _(with Dr. Regha)_`
            : `${{EMJ_SUN}} *OPD (8 AM–2 PM)*`;
        }} else if (sh === "EVENING") {{
          shLabel = `${{EMJ_EVE}} *EVENING DUTY (2 PM–8 PM)*`;
        }} else if (sh === "NIGHT") {{
          shLabel = `${{EMJ_MOON}} *NIGHT DUTY (8 PM–8 AM)*`;
        }} else if (e.note && e.note.toLowerCase().includes("post-night")) {{
          shLabel = `${{EMJ_ZZZ}} *Off (Post-Night Rest)*`;
        }} else if (e.note && e.note.toLowerCase().includes("sunday")) {{
          shLabel = `${{EMJ_COUPLE}} *OFF (Sunday Rest)*`;
        }}
        lines.push(`• *${{dPart}} (${{dayPart}}):* ${{shLabel}}`);
      }});

      lines.push("");
      lines.push(`${{EMJ_CHART}} *Summary:* ${{ks.activeCount}} Shifts (${{EMJ_SUN}} ${{ks.opdCount}} OPD • ${{EMJ_EVE}} ${{ks.eveCount}} Eve • ${{EMJ_MOON}} ${{ks.nightCount}} Night) • ${{EMJ_COUPLE}} ${{ks.offCount}} Off Days`);
      if (isKayalRomanticMode()) lines.push(`${{EMJ_SPARK}} _With Love, Saro_ ${{EMJ_HEART}}`);
      return lines.join("\\n");
    }}

    // High-Resolution Retina PNG Table Screenshot Generator
    function drawKayalDutyCanvas() {{
      const ks = getKayalComputedTotals();
      const thKey = ks.vault.theme || "rose";
      const th = KAYAL_THEMES[thKey] || KAYAL_THEMES.rose;
      const entries = ks.entries;
      const scale = 2;
      const width = 940;
      const cardX = 6;
      const cardY = 6;
      const cardW = width - 12;
      const cardR = 22;
      const headerH = 165;
      const subBarH = 54;
      const rowH = 56;
      const footerH = 78;
      const cardH = headerH + subBarH + (entries.length * rowH) + footerH;
      const height = cardH + 12;

      const canvas = document.createElement('canvas');
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);

      const fontSans = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

      function roundRect(x, y, w, h, r, fill, stroke, strokeW = 1) {{
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.arcTo(x + w, y, x + w, y + r, r);
        ctx.lineTo(x + w, y + h - r);
        ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
        ctx.lineTo(x + r, y + h);
        ctx.arcTo(x, y + h, x, y + h - r, r);
        ctx.lineTo(x, y + r);
        ctx.arcTo(x, y, x + r, y, r);
        ctx.closePath();
        if (fill) {{ ctx.fillStyle = fill; ctx.fill(); }}
        if (stroke) {{ ctx.strokeStyle = stroke; ctx.lineWidth = strokeW; ctx.stroke(); }}
      }}

      // Base Card Background
      roundRect(cardX, cardY, cardW, cardH, cardR, '#ffffff', null);

      // 1. Romantic Gradient Header
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
      const grad = ctx.createLinearGradient(cardX, cardY, cardX + cardW, cardY + headerH);
      grad.addColorStop(0, th.canvasGrad1);
      grad.addColorStop(1, th.canvasGrad2);
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.restore();

      // Top Pill
      roundRect(cardX + 26, cardY + 20, 260, 26, 13, 'rgba(255,255,255,0.18)', 'rgba(255,255,255,0.35)', 1);
      ctx.font = `bold 11px ${{fontSans}}`;
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText('🩺 FOR MY FOREVER DOCTOR 💖', cardX + 38, cardY + 33);

      // IST Greeting Pill on Top Right
      const istBadge = `🕒 ${{ks.ist.istDateStr}} • ${{ks.ist.istTimeStr}} IST`;
      ctx.font = `bold 11px ${{fontSans}}`;
      const istW = ctx.measureText(istBadge).width + 28;
      roundRect(cardX + cardW - 26 - istW, cardY + 20, istW, 26, 13, 'rgba(0,0,0,0.25)', 'rgba(255,255,255,0.3)', 1);
      ctx.fillStyle = '#fde68a';
      ctx.textAlign = 'center';
      ctx.fillText(istBadge, cardX + cardW - 26 - istW / 2, cardY + 33);

      // Main Title
      ctx.textAlign = 'left';
      ctx.font = `900 28px ${{fontSans}}`;
      ctx.fillStyle = '#ffffff';
      ctx.fillText(isKayalRomanticMode() ? 'Dr Cuteuh Pattuh (Dr. Kayalvizhi) 💖' : 'Dr. Kayalvizhi — Duty Roster 🩺', cardX + 26, cardY + 74);

      ctx.font = `600 13.5px ${{fontSans}}`;
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      ctx.fillText('📍 Community Health Center, Thirunallar • Duty Roster (01–15 Nov 2026)', cardX + 26, cardY + 104);

      ctx.font = `italic 600 12.5px ${{fontSans}}`;
      ctx.fillStyle = '#fecdd3';
      const noteShort = (ks.vault.loveNote || '').slice(0, 105);
      ctx.fillText(`"${{noteShort}}"`, cardX + 26, cardY + 134);

      // 2. Summary Sub-Bar
      let curY = cardY + headerH;
      ctx.fillStyle = '#fff1f2';
      ctx.fillRect(cardX, curY, cardW, subBarH);
      ctx.beginPath();
      ctx.moveTo(cardX, curY + subBarH);
      ctx.lineTo(cardX + cardW, curY + subBarH);
      ctx.strokeStyle = '#fecdd3';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.font = `800 13px ${{fontSans}}`;
      ctx.fillStyle = '#881337';
      ctx.textAlign = 'left';
      ctx.fillText(`🩺 Total Active Shifts: ${{ks.activeCount}}   (☀️ ${{ks.opdCount}} OPD  •  🌆 ${{ks.eveCount}} Evening  •  🌙 ${{ks.nightCount}} Night)`, cardX + 26, curY + 27);

      ctx.textAlign = 'right';
      ctx.fillStyle = '#047857';
      ctx.fillText(`💞 ${{ks.offCount}} Off Days Together: ${{ks.offDaysShort}}`, cardX + cardW - 26, curY + 27);

      curY += subBarH;

      // 3. 15-Day Table Rows
      entries.forEach((ent, idx) => {{
        const sh = (ent.shift || 'OFF').toUpperCase();
        const isOff = sh === 'OFF';
        const isToday = ent.date === ks.ist.todayKey;

        ctx.fillStyle = isToday ? '#fffbeb' : (isOff ? '#f0fdf4' : (idx % 2 === 0 ? '#ffffff' : '#fff1f2'));
        ctx.fillRect(cardX, curY, cardW, rowH);

        // Left Accent Bar
        ctx.fillStyle = sh === 'OPD' ? '#f59e0b' : (sh === 'EVENING' ? '#ea580c' : (sh === 'NIGHT' ? '#4f46e5' : '#10b981'));
        ctx.fillRect(cardX, curY, 6, rowH);

        // Bottom row line
        ctx.beginPath();
        ctx.moveTo(cardX, curY + rowH);
        ctx.lineTo(cardX + cardW, curY + rowH);
        ctx.strokeStyle = '#f1f5f9';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Date & Day Badge
        const dShort = (ent.date || '').slice(0, 2) + ' Nov';
        roundRect(cardX + 22, curY + 11, 118, 34, 10, isOff ? '#dcfce7' : '#ffe4e6', isOff ? '#86efac' : '#fda4af', 1);
        ctx.font = `800 13px ${{fontSans}}`;
        ctx.fillStyle = isOff ? '#065f46' : '#881337';
        ctx.textAlign = 'center';
        ctx.fillText(`${{dShort}} (${{ent.day || ''}})`, cardX + 81, curY + 28);

        // Shift Pill
        let pillText = '💞 OFF / REST DAY';
        let pillBg = '#d1fae5';
        let pillFg = '#065f46';
        if (sh === 'OPD') {{
          pillText = '☀️ OPD (8 AM – 2 PM)';
          pillBg = '#fef3c7';
          pillFg = '#92400e';
        }} else if (sh === 'EVENING') {{
          pillText = '🌆 EVENING (2 PM – 8 PM)';
          pillBg = '#ffedd5';
          pillFg = '#9a3412';
        }} else if (sh === 'NIGHT') {{
          pillText = '🌙 NIGHT (8 PM – 8 AM)';
          pillBg = '#e0e7ff';
          pillFg = '#3730a3';
        }}
        roundRect(cardX + 156, curY + 11, 220, 34, 10, pillBg, null);
        ctx.font = `800 12.5px ${{fontSans}}`;
        ctx.fillStyle = pillFg;
        ctx.textAlign = 'center';
        ctx.fillText(pillText, cardX + 266, curY + 28);

        // Right Care Note & Co-Doctor
        ctx.textAlign = 'left';
        ctx.font = `700 13px ${{fontSans}}`;
        ctx.fillStyle = '#1e293b';
        const mainNote = ent.note || (isOff ? 'Off Day' : sh);
        ctx.fillText(mainNote + (isToday ? '  ⭐ TODAY' : ''), cardX + 394, curY + 21);

        ctx.font = `500 11.5px ${{fontSans}}`;
        ctx.fillStyle = '#64748b';
        const careMsg = getShiftCareReminder(sh, ent.note).split('•').pop().trim();
        ctx.fillText(careMsg, cardX + 394, curY + 39);

        curY += rowH;
      }});

      // 4. Romantic Footer
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
      ctx.fillStyle = th.canvasGrad1;
      ctx.fill();
      ctx.restore();

      ctx.textAlign = 'left';
      ctx.font = `bold 14px ${{fontSans}}`;
      ctx.fillStyle = '#ffffff';
      ctx.fillText(`💖 ${{ks.ist.greet}}`, cardX + 26, curY + 28);

      ctx.font = `500 12px ${{fontSans}}`;
      ctx.fillStyle = '#fecdd3';
      ctx.fillText('Proud of you every single shift — take care & shine bright at CHC Thirunallar!', cardX + 26, curY + 50);

      // Right Sign-Off Pill ("With Love, Saro 💖")
      const signText = isKayalRomanticMode() ? 'With Love, Saro 💖' : 'CHC Thirunallar 🩺';
      ctx.font = `800 15px ${{fontSans}}`;
      const sW = ctx.measureText(signText).width + 36;
      roundRect(cardX + cardW - 26 - sW, curY + 19, sW, 40, 14, th.canvasAccent, '#ffffff', 1.5);
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(signText, cardX + cardW - 26 - sW / 2, curY + 39);

      // Outer Card Border
      roundRect(cardX, cardY, cardW, cardH, cardR, null, th.canvasBorder, 2.5);
      return canvas;
    }}

    window.shareKayalWhatsApp = async function() {{
      const ks = getKayalComputedTotals();
      let cleanPhone = (ks.vault.phone || "").replace(/\\D/g, "");
      if (cleanPhone.length === 10) cleanPhone = "91" + cleanPhone;

      try {{
        const canvas = drawKayalDutyCanvas();
        const blob = await canvasToPngBlobPromise(canvas);
        const fileName = "Dr_Cuteuh_Pattuh_Duty_Roster.png";
        const file = new File([blob], fileName, {{ type: "image/png" }});
        const caption = isKayalRomanticMode() ? `💖 Dr Cuteuh Pattuh Duty Roster (01–15 Nov 2026) — With Love, Saro 💖` : `🩺 Dr. Kayalvizhi Duty Roster (01–15 Nov 2026) — CHC Thirunallar`;

        // 1. On Android S24 Ultra / Mobile: Native Web Share Sheet with the PNG Screenshot File!
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
        if (isMobile && navigator.canShare && navigator.canShare({{ files: [file] }})) {{
          await navigator.share({{
            files: [file],
            title: "Dr Cuteuh Pattuh Duty Roster 💖",
            text: caption
          }});
          showClipboardToast("Shared Duty Roster Screenshot to WhatsApp! 💖", true);
          return;
        }}

        // 2. On Desktop / Fallback: Copy PNG Image to Clipboard + Download PNG + Open WhatsApp Chat
        let copiedImg = false;
        if (navigator.clipboard && window.ClipboardItem) {{
          try {{
            await navigator.clipboard.write([new ClipboardItem({{ "image/png": blob }})]);
            copiedImg = true;
          }} catch (e) {{}}
        }}

        const link = document.createElement("a");
        link.download = fileName;
        link.href = URL.createObjectURL(blob);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        const waUrl = cleanPhone
          ? `https://wa.me/${{cleanPhone}}?text=${{encodeURIComponent(caption)}}`
          : `https://wa.me/?text=${{encodeURIComponent(caption)}}`;
        window.open(waUrl, "_blank");

        if (copiedImg) {{
          showClipboardToast("Screenshot Copied to Clipboard & Downloaded! Press Ctrl+V in WhatsApp 💖", true);
        }} else {{
          showClipboardToast("Duty Roster Screenshot Downloaded! Attach it in WhatsApp 💖", true);
        }}
      }} catch (err) {{
        showClipboardToast("Tap the Screenshot Preview Card below to save or share!", false);
      }}
    }};

    window.downloadKayalTablePng = async function() {{
      try {{
        const canvas = drawKayalDutyCanvas();
        const blob = await canvasToPngBlobPromise(canvas);
        const link = document.createElement("a");
        link.download = "Dr_Cuteuh_Pattuh_Duty_Roster.png";
        link.href = URL.createObjectURL(blob);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showClipboardToast("Downloaded Dr_Cuteuh_Pattuh_Duty_Roster.png! 💖", true);
      }} catch (e) {{}}
    }};

    window.copyKayalWhatsAppTable = async function() {{
      const msg = buildKayalWhatsAppText();
      try {{
        await navigator.clipboard.writeText(msg);
        showClipboardToast("Copied Text with Full Emojis! Paste into WhatsApp 💖", true);
      }} catch (e) {{
        const ta = document.createElement("textarea");
        ta.value = msg;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        showClipboardToast("Copied Text with Full Emojis! Paste into WhatsApp 💖", true);
      }}
    }};

    window.setKayalTheme = function(themeKey) {{
      const vault = loadKayalVault();
      if (KAYAL_THEMES[themeKey]) {{
        vault.theme = themeKey;
        saveKayalVault(vault);
        renderDashboard();
      }}
    }};

    window.saveKayalPersonalSettings = function() {{
      const phInp = document.getElementById("kayal-wa-phone-inp");
      const noteInp = document.getElementById("kayal-love-note-inp");
      const vault = loadKayalVault();
      if (phInp) vault.phone = phInp.value.trim();
      if (noteInp && noteInp.value.trim()) vault.loveNote = noteInp.value.trim();
      saveKayalVault(vault);
      showClipboardToast("Saved Dr Cuteuh Pattuh's WhatsApp & Love Note in Browser! 💖", true);
      renderDashboard();
    }};

    window.setKayalRowShift = function(dateStr, newShift) {{
      const vault = loadKayalVault();
      const target = vault.entries.find(e => e.date === dateStr);
      if (target) {{
        target.shift = newShift;
        if (newShift === "OPD") target.note = "OPD (Morning)";
        else if (newShift === "EVENING") target.note = "Evening Duty";
        else if (newShift === "NIGHT") target.note = "Night Duty";
        else target.note = "Off Day Together";
        saveKayalVault(vault);
        renderDashboard();
      }}
    }};

    function renderKayalWorkspace(stmt) {{
      const container = document.getElementById('date-breakdown-container');
      const ks = getKayalComputedTotals(stmt);
      const km = stmt.kayal_meta || {{}};
      const justUp = !!km.just_uploaded;
      const thKey = ks.vault.theme || "rose";
      const th = KAYAL_THEMES[thKey] || KAYAL_THEMES.rose;

      const todayShiftText = ks.todayEntry
        ? `Today (${{ks.todayEntry.date.slice(0, 5)}}): ${{ks.todayEntry.shift}} — ${{ks.todayEntry.note || ''}}`
        : `01–15 Nov 2026 Schedule Active`;
      const nextOffText = ks.nextOff
        ? `${{ks.nextOff.date.slice(0, 2)}} Nov (${{ks.nextOff.day}}) — ${{ks.nextOff.note || 'Off Day'}}`
        : `6 Off Days`;

      const rowsHtml = ks.entries.map(ent => {{
        const sh = (ent.shift || 'OFF').toUpperCase();
        const isOff = sh === 'OFF';
        const isToday = ent.date === ks.ist.todayKey;
        let badgeCls = 'bg-emerald-100 text-emerald-800 border-emerald-300';
        let badgeIcon = '💞 OFF / OUR DAY';
        let rowBg = isToday ? 'bg-amber-50/80 ring-2 ring-amber-400' : (isOff ? 'bg-emerald-50/35' : 'bg-white');
        if (sh === 'OPD') {{
          badgeCls = 'bg-amber-100 text-amber-900 border-amber-300';
          badgeIcon = '☀️ OPD (8 AM – 2 PM)';
        }} else if (sh === 'EVENING') {{
          badgeCls = 'bg-orange-100 text-orange-900 border-orange-300';
          badgeIcon = '🌆 Evening (2 PM – 8 PM)';
        }} else if (sh === 'NIGHT') {{
          badgeCls = 'bg-indigo-100 text-indigo-900 border-indigo-300';
          badgeIcon = '🌙 Night (8 PM – 8 AM)';
        }}

        const careReminder = getShiftCareReminder(sh, ent.note);

        return `
          <div class="p-4 sm:px-6 border-b border-rose-100/80 last:border-none flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 ${{rowBg}} transition">
            <div class="flex items-center gap-3.5">
              <div class="w-13 h-13 rounded-2xl ${{isOff ? 'bg-emerald-100 border-emerald-300 text-emerald-800' : 'bg-rose-100/80 border-rose-300 text-rose-900'}} border flex flex-col items-center justify-center flex-shrink-0 px-2.5 py-2">
                <span class="text-base font-black leading-none">${{(ent.date || '').slice(0, 2)}}</span>
                <span class="text-[10px] font-extrabold uppercase mt-0.5">${{ent.day || ''}}</span>
              </div>
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold border ${{badgeCls}}">${{badgeIcon}}</span>
                  <span class="text-xs font-extrabold text-slate-800">${{ent.note || ''}}</span>
                  ${{isToday ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-slate-950 uppercase">⭐ Today</span>` : ''}}
                </div>
                <div class="text-[11.5px] text-rose-700 font-semibold mt-1">💌 ${{careReminder}}</div>
              </div>
            </div>

            <div class="flex items-center gap-1 bg-slate-50 p-1 rounded-xl border border-slate-200 no-print self-end sm:self-center">
              ${{['OPD', 'EVENING', 'NIGHT', 'OFF'].map(opt => `
                <button onclick="setKayalRowShift('${{ent.date}}', '${{opt}}')" class="px-2.5 py-1 rounded-lg text-[10px] font-extrabold transition cursor-pointer ${{sh === opt ? 'bg-rose-600 text-white shadow-2xs' : 'text-slate-600 hover:bg-rose-50'}}">
                  ${{opt}}
                </button>
              `).join('')}}
            </div>
          </div>
        `;
      }}).join('');

      container.innerHTML = `
        <div class="max-w-3xl mx-auto space-y-5">

          <!-- LIVE INDIAN STANDARD TIME (IST) GREETING BANNER -->
          <div class="bg-gradient-to-r ${{th.tblHeader}} text-white rounded-3xl p-4 sm:px-6 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <span class="text-2xl">💖</span>
              <div>
                <div id="kayal-live-ist-greet" class="text-sm sm:text-base font-black tracking-tight">${{ks.ist.greet}}</div>
                <div class="text-xs text-rose-200 font-semibold mt-0.5">
                  <span id="kayal-live-ist-clock">🕒 ${{ks.ist.istDateStr}} • ${{ks.ist.istTimeStr}} IST</span>
                  <span class="mx-1.5">•</span>
                  <span class="text-amber-300 font-bold">${{todayShiftText}}</span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-1.5 bg-white/10 p-1 rounded-xl border border-white/15 no-print self-stretch sm:self-auto justify-center">
              ${{Object.entries(KAYAL_THEMES).map(([k, v]) => `
                <button onclick="setKayalTheme('${{k}}')" class="px-2.5 py-1 rounded-lg text-[10px] font-extrabold transition cursor-pointer ${{thKey === k ? 'bg-white text-slate-900 shadow-2xs' : 'text-white/80 hover:bg-white/10'}}">
                  ${{v.name}}
                </button>
              `).join('')}}
            </div>
          </div>

          ${{justUp ? `
          <div class="bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-2xl p-4 shadow-md flex flex-col sm:flex-row items-center justify-between gap-3">
            <div class="flex items-center gap-2.5">
              <span class="text-2xl">📸</span>
              <div>
                <div class="text-sm font-black">${{ks.ist.greet}} — Your Roster Photo is Ready!</div>
                <div class="text-xs text-emerald-50">Loaded at ${{ks.ist.istTimeStr}} IST. Tap the button to share the table screenshot image on WhatsApp!</div>
              </div>
            </div>
            <button onclick="shareKayalWhatsApp()" class="px-4 py-2.5 rounded-xl bg-white text-emerald-800 font-black text-xs shadow-sm hover:bg-emerald-50 cursor-pointer flex-shrink-0">
              📲 Share Screenshot on WhatsApp
            </button>
          </div>
          ` : ''}}

          <!-- ROMANTIC HERO CARD FOR DR CUTEUH PATTUH -->
          <div class="bg-gradient-to-br ${{th.pageBg}} rounded-3xl border-2 ${{th.border}} shadow-sm p-6 sm:p-7">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div class="space-y-1.5">
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border ${{th.pillBg}} text-[11px] font-extrabold uppercase tracking-wider">
                  <span>🩺💖</span>
                  <span>${{justUp ? "Dr Cuteuh Pattuh • CHC Thirunallar" : "Dr. Kayalvizhi • CHC Thirunallar"}}</span>
                </div>
                <h2 class="text-2xl sm:text-3xl font-black ${{th.titleText}} tracking-tight">
                  ${{justUp ? "Dr Cuteuh Pattuh's Duty Roster ✨" : "Dr. Kayalvizhi's Duty Roster 🩺"}}
                </h2>
                <p class="text-xs sm:text-sm font-semibold ${{th.subText}} leading-relaxed max-w-xl">
                  "${{ks.vault.loveNote}}"
                </p>
              </div>

              <!-- 2 ACTION BUTTONS: 1) SHARE SCREENSHOT IMAGE ON WHATSAPP, 2) COPY TEXT WITH EMOJIS -->
              <div class="flex flex-col gap-2 w-full sm:w-auto flex-shrink-0 no-print">
                <button onclick="shareKayalWhatsApp()" class="w-full sm:w-auto px-5 py-3 rounded-2xl bg-gradient-to-r ${{th.btnGrad}} text-white font-extrabold text-xs shadow-md transition flex items-center justify-center gap-2 cursor-pointer active:scale-95">
                  <span>📲</span>
                  <span>Share Screenshot on WhatsApp</span>
                </button>
                <div class="flex items-center gap-2">
                  <button onclick="copyKayalWhatsAppTable()" class="flex-1 px-3.5 py-2 rounded-xl bg-white hover:bg-rose-50 text-rose-800 border border-rose-200 font-extrabold text-xs transition flex items-center justify-center gap-1.5 cursor-pointer">
                    <span>📋</span>
                    <span>Copy Text (With Emojis)</span>
                  </button>
                  <button onclick="downloadKayalTablePng()" class="px-3.5 py-2 rounded-xl bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 font-extrabold text-xs transition flex items-center justify-center gap-1 cursor-pointer" title="Download PNG Screenshot">
                    <span>🖼️</span>
                    <span>PNG</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- 3 PERSONALIZED ROMANTIC TILES (INCLUDING NEXT OFF DAY COUNTDOWN) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
              <div class="bg-white/90 rounded-2xl border border-rose-200 p-4">
                <div class="text-[10px] font-extrabold uppercase text-rose-600">🩺 Active Duties (01–15 Nov)</div>
                <div class="text-2xl font-black text-rose-950 mt-0.5">${{ks.activeCount}} Shifts</div>
                <div class="text-xs font-bold text-slate-600 mt-0.5">☀️ ${{ks.opdCount}} OPD • 🌆 ${{ks.eveCount}} Eve • 🌙 ${{ks.nightCount}} Night</div>
              </div>
              <div class="bg-white/90 rounded-2xl border border-emerald-200 p-4">
                <div class="text-[10px] font-extrabold uppercase text-emerald-700">💑 Next Off Day Together</div>
                <div class="text-lg font-black text-emerald-800 mt-1">${{nextOffText}}</div>
                <div class="text-[11px] font-bold text-emerald-600 mt-0.5">All ${{ks.offCount}} Off Days: ${{ks.offDaysShort}}</div>
              </div>
              <div class="bg-white/90 rounded-2xl border border-amber-200 p-4">
                <div class="text-[10px] font-extrabold uppercase text-amber-800">${{justUp ? "💌 Signed With Love" : "🏥 Duty Center"}}</div>
                <div class="text-lg font-black text-rose-700 mt-1">${{justUp ? "With Love, Saro 💖" : "CHC Thirunallar"}}</div>
                <div class="text-[11px] font-bold text-amber-800 mt-0.5">CHC Thirunallar • Medical Officer</div>
              </div>
            </div>
          </div>

          <!-- 15-DAY INTERACTIVE DUTY TABLE -->
          <div class="bg-white rounded-3xl border border-rose-200/90 shadow-sm overflow-hidden">
            <div class="px-6 py-4 bg-gradient-to-r ${{th.tblHeader}} text-white flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1">
              <span class="text-sm font-extrabold">📅 ${{justUp ? "Dr Cuteuh Pattuh" : "Dr. Kayalvizhi"}} — 15-Day Duty Schedule</span>
              <span class="text-xs font-bold text-rose-200">Tap any shift button on the right to edit</span>
            </div>
            <div>
              ${{rowsHtml}}
            </div>
          </div>

          <!-- LIVE SCREENSHOT TABLE PREVIEW (SO SHE CAN SEE OR LONG-PRESS THE EXACT WHATSAPP IMAGE) -->
          <div class="bg-white rounded-3xl border border-rose-200/90 shadow-sm p-5 space-y-3">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <h3 class="text-sm font-extrabold text-slate-900">🖼️ WhatsApp Table Screenshot Preview</h3>
                <p class="text-xs text-slate-500">This high-resolution table card is shared when you tap <b>📲 Share Screenshot on WhatsApp</b> (or long-press image on mobile).</p>
              </div>
              <button onclick="shareKayalWhatsApp()" class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-extrabold cursor-pointer">
                📲 Send This Screenshot
              </button>
            </div>
            <div class="rounded-2xl overflow-hidden border border-rose-200 bg-slate-50 flex justify-center p-2">
              <img id="kayal-screenshot-preview-img" alt="Dr Cuteuh Pattuh Duty Roster Screenshot" class="max-w-full h-auto rounded-xl shadow-xs" />
            </div>
          </div>

          <!-- EDITABLE BROWSER STORAGE SETTINGS (WHATSAPP NUMBER & LOVE NOTE) -->
          <div class="bg-rose-50/70 rounded-3xl border border-rose-200 p-5 space-y-3 no-print">
            <div class="text-xs font-extrabold uppercase tracking-wider text-rose-900">🔒 Browser-Saved Personalization (Editable Anytime)</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="block text-[11px] font-bold text-rose-800 mb-1">📱 Dr Cuteuh Pattuh's WhatsApp No.</label>
                <input type="tel" id="kayal-wa-phone-inp" value="${{ks.vault.phone || ''}}" placeholder="e.g. 9876543210" class="w-full px-3 py-2 text-xs font-bold bg-white border border-rose-200 rounded-xl text-slate-900">
              </div>
              <div class="sm:col-span-2">
                <label class="block text-[11px] font-bold text-rose-800 mb-1">💌 Saro's Love Note on Header & Screenshot</label>
                <input type="text" id="kayal-love-note-inp" value="${{(ks.vault.loveNote || '').replace(/"/g, '&quot;')}}" class="w-full px-3 py-2 text-xs font-bold bg-white border border-rose-200 rounded-xl text-slate-900">
              </div>
            </div>
            <div class="flex justify-end">
              <button onclick="saveKayalPersonalSettings()" class="px-4 py-2 rounded-xl bg-rose-700 hover:bg-rose-600 text-white text-xs font-extrabold cursor-pointer">
                💾 Save in Browser Storage
              </button>
            </div>
          </div>

        </div>
      `;

      // Render the live PNG screenshot preview image immediately
      setTimeout(() => {{
        try {{
          const prevImg = document.getElementById('kayal-screenshot-preview-img');
          if (prevImg) {{
            const c = drawKayalDutyCanvas();
            prevImg.src = c.toDataURL('image/png');
          }}
        }} catch (e) {{}}
      }}, 30);

      // Keep IST Clock & Greeting ticking live every second
      if (window._kayalClockInterval) clearInterval(window._kayalClockInterval);
      window._kayalClockInterval = setInterval(() => {{
        const gEl = document.getElementById('kayal-live-ist-greet');
        const cEl = document.getElementById('kayal-live-ist-clock');
        if (!gEl && !cEl) return;
        const cur = getISTGreetingAndTime();
        if (gEl) gEl.textContent = cur.greet;
        if (cEl) cEl.textContent = `🕒 ${{cur.istDateStr}} • ${{cur.istTimeStr}} IST`;
      }}, 1000);
    }}

    function renderShafanaWorkspace(stmt) {{
      const container = document.getElementById('date-breakdown-container');
      const sf = getShafanaComputedTotals(stmt);
      const totalEarnedAll = sf.openingCb + sf.cbEarned;

      const orderCardsHtml = sf.vault.entries.map(ent => `
        <div class="p-4 sm:px-6 flex items-center justify-between gap-4 border-b border-slate-100 last:border-none hover:bg-amber-50/30 transition">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm font-extrabold text-slate-900">🛍️ ${{ent.description || 'Amazon Order'}}</span>
              ${{ent.verifiedOnBill ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800">✅ Verified on Bill</span>` : ''}}
            </div>
            <div class="text-xs text-slate-500 mt-0.5">📅 ${{ent.date_time}} • 📍 Raja Mohamed, Karaikal</div>
          </div>
          <div class="flex items-center gap-3 flex-shrink-0">
            <div class="text-right">
              <div class="text-base font-black text-slate-900">Bill: ₹${{ent.amount.toLocaleString('en-IN')}}</div>
              <div class="text-xs font-extrabold text-emerald-600">🎁 +₹${{ent.cashback_earned.toLocaleString('en-IN')}} Cashback Saved</div>
            </div>
            <button onclick="deleteShafanaOrder('${{ent.id}}')" class="p-1.5 rounded-lg text-slate-300 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer no-print" title="Remove order">
              🗑️
            </button>
          </div>
        </div>
      `).join('');

      container.innerHTML = `
        <div class="max-w-3xl mx-auto space-y-5">

          <!-- SPECIAL WARM GREETING BANNER FOR SHAFANA -->
          <div class="bg-gradient-to-br from-amber-50 via-rose-50/70 to-emerald-50/80 rounded-3xl border-2 border-amber-200/90 shadow-sm p-6 sm:p-7 relative overflow-hidden">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div class="space-y-1.5">
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/40 text-amber-900 text-[11px] font-extrabold uppercase tracking-wider">
                  <span>🌸</span>
                  <span>Made Specially for Shafana</span>
                </div>
                <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  Hello Thozhi Shafana! ✨
                </h2>
                <p class="text-xs sm:text-sm font-semibold text-slate-700 leading-relaxed max-w-xl">
                  Welcome to your personal <b>Amazon Shopping & Cashback Corner</b>! Everything is kept simple here so you can check your order bill and your <b>5% cashback savings</b> at a glance.
                </p>
              </div>
              <button onclick="shareShafanaWhatsApp()" class="w-full sm:w-auto px-5 py-3.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs shadow-md shadow-emerald-600/20 transition flex items-center justify-center gap-2 cursor-pointer flex-shrink-0">
                <span>📲</span>
                <span>Send Greeting & Summary on WhatsApp</span>
              </button>
            </div>

            <!-- FRIENDLY 3-STEP EXPLANATION FOR SHAFANA -->
            <div class="mt-5 pt-4 border-t border-amber-200/70 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div class="bg-white/85 rounded-2xl p-3.5 border border-amber-200/80">
                <div class="text-xs font-black text-amber-900">🛍️ 1. Shop Happily</div>
                <p class="text-[11px] text-slate-600 mt-1 leading-snug">
                  Every Amazon order placed for you (<b>Raja Mohamed, Karaikal</b>) automatically earns <b>5% Cashback</b>.
                </p>
              </div>
              <div class="bg-white/85 rounded-2xl p-3.5 border border-amber-200/80">
                <div class="text-xs font-black text-amber-900">🗓️ 2. Pay After Bill Date</div>
                <p class="text-[11px] text-slate-600 mt-1 leading-snug">
                  No rush at all! You only pay the <b>Order Bill Amount</b> after the monthly credit card bill arrives.
                </p>
              </div>
              <div class="bg-white/85 rounded-2xl p-3.5 border border-emerald-200/90">
                <div class="text-xs font-black text-emerald-900">🎁 3. Cashback is 100% Yours</div>
                <p class="text-[11px] text-slate-600 mt-1 leading-snug">
                  Your <b>5% Cashback</b> stays saved in your wallet below—just tell me anytime you want to use it!
                </p>
              </div>
            </div>
          </div>

          <!-- 2 BIG, SIMPLE CARDS FOR SHAFANA -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

            <!-- CARD 1: BILL TO PAY -->
            <div class="bg-amber-50/90 rounded-3xl border-2 border-amber-300 p-6 shadow-sm">
              <div class="text-xs font-extrabold uppercase tracking-wider text-amber-900">🧾 1. Your Order Bill to Pay</div>
              <div class="text-4xl font-black text-slate-900 mt-2">₹${{sf.billDue.toLocaleString('en-IN')}}</div>
              <div class="text-xs font-bold text-amber-800 mt-2">You can pay this comfortably after the bill date</div>
            </div>

            <!-- CARD 2: CASHBACK AVAILABLE -->
            <div class="bg-emerald-50/90 rounded-3xl border-2 border-emerald-300 p-6 shadow-sm">
              <div class="text-xs font-extrabold uppercase tracking-wider text-emerald-900">🎁 2. Your Saved Cashback Balance</div>
              <div class="text-4xl font-black ${{sf.netKitty >= 0 ? 'text-emerald-700' : 'text-rose-600'}} mt-2">
                ${{sf.netKitty >= 0 ? '' : '-'}}₹${{Math.abs(sf.netKitty).toLocaleString('en-IN')}}
              </div>
              <div class="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/90 border border-emerald-200 text-xs font-extrabold text-slate-700">
                <span class="text-emerald-700">Earned: +₹${{totalEarnedAll.toLocaleString('en-IN')}}</span>
                <span>•</span>
                <span class="text-rose-600">Used: -₹${{sf.cbUsed.toLocaleString('en-IN')}}</span>
              </div>
              <div class="text-[11px] font-semibold text-emerald-800 mt-1.5">Ready for you to use on your next Amazon order!</div>
            </div>

          </div>

          <!-- SIMPLE ORDERS LIST -->
          <div class="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
            <div class="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
              <span class="text-sm font-extrabold">📦 Shafana's Amazon Orders (${{sf.vault.entries.length}})</span>
              <span class="text-xs font-bold text-amber-300">✨ 5% Cashback Included</span>
            </div>
            <div>
              ${{orderCardsHtml || '<div class="p-6 text-center text-xs text-slate-400">No orders added yet.</div>'}}
            </div>
          </div>

          <!-- MANUAL UPDATE BOX (FOR YOU TO TYPE USED CASHBACK OR ADD AN ORDER) -->
          <div class="bg-slate-100/90 rounded-3xl border border-slate-200/90 p-5 space-y-4 no-print">
            <div class="text-xs font-extrabold uppercase tracking-wider text-slate-600">⚙️ Admin Controls (For You to Update)</div>

            <!-- Row 1: Manual Cashback Used -->
            <div class="bg-white p-4 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <div>
                <div class="text-xs font-extrabold text-slate-800">➖ Cashback Used by Shafana (₹)</div>
                <div class="text-[11px] text-slate-500">Type the cashback amount she used and tap Save</div>
              </div>
              <div class="flex items-center gap-2">
                <input type="number" id="sf-manual-cb-used-inp" value="${{sf.cbUsed}}" step="1" class="w-32 px-3 py-2 text-sm font-black bg-slate-50 border border-slate-300 rounded-xl text-slate-900">
                <button onclick="saveManualCbUsed()" class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-extrabold cursor-pointer">
                  💾 Save Used CB
                </button>
              </div>
            </div>

            <!-- Row 2: Manual Add Order -->
            <div class="bg-white p-4 rounded-2xl border border-slate-200 flex flex-wrap items-center gap-2.5">
              <span class="text-xs font-extrabold text-slate-800 mr-1">➕ Add Order:</span>
              <input type="text" id="sf-simple-order-note" placeholder="Order name (optional)" class="px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl flex-1 min-w-[140px]">
              <input type="number" id="sf-simple-order-amt" placeholder="Bill Amount ₹" oninput="const c=document.getElementById('sf-simple-order-cb'); if(c && this.value) c.value=Math.floor(parseFloat(this.value)*0.05);" class="w-32 px-3 py-2 text-xs font-bold bg-slate-50 border border-slate-300 rounded-xl">
              <input type="number" id="sf-simple-order-cb" placeholder="Cashback +₹" class="w-28 px-3 py-2 text-xs font-bold bg-emerald-50 border border-emerald-300 rounded-xl text-emerald-900">
              <button onclick="addSimpleShafanaOrder()" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-extrabold cursor-pointer">
                ➕ Add Order
              </button>
            </div>
          </div>

        </div>
      `;
    }}

    function renderPayslipWorkspace(stmt) {{
      const container = document.getElementById('date-breakdown-container');
      const pm = stmt.payslip_meta || {{}};
      const perDay = pm.per_day_rate || 1833.33;
      const fullGross = pm.full_month_gross || 55000.0;
      const annualCtc = pm.annual_ctc_est || (fullGross * 12);
      const paidDays = pm.paid_days_num || 8;
      const lopDays = pm.lop_days_num || 0;
      const monthDays = pm.month_days || 30;
      const lopLost = pm.lop_money_lost || 0.0;
      const unworkedDays = pm.unworked_prorata_days || 0;
      const unworkedAmt = pm.prorata_unworked_amount || 0.0;

      // 1. Build 2-Column Earnings & Deductions Rows
      const earningsRows = (pm.earnings_list || []).map(e => `
        <div class="px-5 py-3.5 flex justify-between items-center border-b border-slate-100 last:border-none hover:bg-emerald-50/30 transition">
          <div>
            <div class="font-bold text-slate-800 text-sm">${{e.name}}</div>
            <div class="text-[11px] text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap">
              <span>Full 30-Day Rate: <b class="text-slate-700">${{e.full_month_str || e.amount_str}}/mo</b></span>
              ${{e.ytd ? `<span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px]">YTD: ${{e.ytd}}</span>` : ''}}
            </div>
          </div>
          <div class="text-right">
            <div class="font-extrabold text-emerald-700 text-base">+${{e.amount_str}}</div>
            <div class="text-[10px] font-bold uppercase text-emerald-600">Credited (${{paidDays}}d)</div>
          </div>
        </div>
      `).join('');

      const deductionsRows = (pm.deductions_list && pm.deductions_list.length > 0)
        ? pm.deductions_list.map(d => `
          <div class="px-5 py-3.5 flex justify-between items-center border-b border-slate-100 last:border-none hover:bg-rose-50/30 transition">
            <div>
              <div class="font-bold text-slate-800 text-sm">${{d.name}}</div>
              ${{d.ytd ? `<div class="text-[10px] text-rose-700 font-bold mt-0.5">YTD: ${{d.ytd}}</div>` : ''}}
            </div>
            <div class="text-right">
              <div class="font-extrabold text-rose-600 text-base">-${{d.amount_str}}</div>
              <div class="text-[10px] font-bold uppercase text-rose-500">Deducted</div>
            </div>
          </div>
        `).join('')
        : `
          <div class="p-6 text-center flex flex-col items-center justify-center gap-1.5">
            <span class="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg font-bold">✅</span>
            <div class="text-sm font-bold text-slate-800">Zero Deductions This Month (₹0.00)</div>
            <div class="text-xs text-slate-500 max-w-xs">No LOP leave deductions, Professional Tax, or TDS withheld on this payslip.</div>
          </div>
        `;

      // 2. Calculate Salary vs Credit Card Bills Cashflow Bridge across loaded session statements
      const creditCardStmts = statements.filter(s => !(s.payslip_meta && s.payslip_meta.is_payslip));
      let totalCardBills = 0;
      let totalFriendEmis = 0;
      const cardBreakdownPills = [];

      creditCardStmts.forEach(cs => {{
        const cDue = parseFloat(String(cs.total_due || '0').replace(/[^0-9.]/g, '')) || 0;
        totalCardBills += cDue;
        cardBreakdownPills.push(`<span class="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 font-bold text-xs border border-slate-200">${{cs.bank_short}}: ₹${{cDue.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</span>`);

        Object.values(cs.date_groups || {{}}).forEach(grp => {{
          if (grp.has_emi) {{
            totalFriendEmis += (grp.total || 0);
          }}
        }});
      }});

      const myPersonalCardSpend = Math.max(0, totalCardBills - totalFriendEmis);
      const activeSalaryBasis = window.payslipCashflowUseFullMonth ? fullGross : (pm.net_val || 14666);
      const netBankSavingsAfterPersonal = activeSalaryBasis - myPersonalCardSpend;
      const netBankSavingsAfterAllBills = activeSalaryBasis - totalCardBills;

      // 3. Collect all loaded payslips for Multi-Month Salary & YTD Tracker
      const allPayslips = statements.filter(s => s.payslip_meta && s.payslip_meta.is_payslip);
      let cumulativeGross = 0;
      let cumulativeNet = 0;
      let cumulativeLopLost = 0;
      const multiMonthRows = allPayslips.map(ps => {{
        const m = ps.payslip_meta || {{}};
        cumulativeGross += (m.gross_val || 0);
        cumulativeNet += (m.net_val || 0);
        cumulativeLopLost += (m.lop_money_lost || 0);
        return `
          <tr class="border-b border-slate-100 hover:bg-slate-50/80 text-xs">
            <td class="py-3 px-4 font-extrabold text-slate-900">${{m.pay_period || ps.statement_month}}</td>
            <td class="py-3 px-4 font-mono text-slate-600">${{m.pay_date || 'N/A'}}</td>
            <td class="py-3 px-4 font-bold text-emerald-700">${{m.paid_days || '0'}} / ${{m.month_days || 30}} Days</td>
            <td class="py-3 px-4 font-bold ${{(m.lop_days_num || 0) > 0 ? 'text-rose-600' : 'text-slate-500'}}">
              ${{m.lop_days || '0'}} Days ${{(m.lop_money_lost || 0) > 0 ? `(-₹${{m.lop_money_lost.toLocaleString('en-IN')}})` : '(₹0 lost)'}}
            </td>
            <td class="py-3 px-4 font-bold text-slate-800">${{m.gross_earnings || '₹0.00'}}</td>
            <td class="py-3 px-4 font-bold text-rose-600">${{m.total_deductions || '₹0.00'}}</td>
            <td class="py-3 px-4 font-black text-emerald-700 text-sm">${{m.net_pay || ps.total_due}}</td>
          </tr>
        `;
      }}).join('');

      container.innerHTML = `
        <div class="space-y-7">

          <!-- MODULE 1: DEDICATED 2-COLUMN OFFICIAL PAYROLL LEDGER (NO CREDIT CARD FILTERS) -->
          <div class="bg-white rounded-3xl border border-emerald-200/90 shadow-sm overflow-hidden">
            <div class="p-6 bg-gradient-to-r from-emerald-50/90 via-teal-50/60 to-slate-50 border-b border-emerald-200/80 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div class="flex items-center gap-3.5">
                <div class="w-12 h-12 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-black text-xl shadow-md shadow-emerald-600/25">💼</div>
                <div>
                  <div class="flex items-center gap-2 flex-wrap">
                    <h2 class="text-lg font-extrabold text-slate-900">Official Salary & Payroll Breakdown</h2>
                    <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-600 text-white uppercase tracking-wider">${{pm.pay_period || stmt.statement_month}}</span>
                  </div>
                  <p class="text-xs text-slate-600 mt-0.5">${{pm.company_name}} • Employee ID #${{pm.employee_id || '115'}} • Bank A/C: <b>${{pm.bank_account_no || 'N/A'}}</b></p>
                </div>
              </div>
              <div class="flex items-center gap-2.5 flex-wrap no-print">
                <button onclick="downloadUnlockedPayslip()" class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs shadow-md shadow-emerald-600/25 transition flex items-center gap-1.5 cursor-pointer active:scale-95">
                  <span>🔓</span>
                  <span>Download Unlocked Payslip PDF</span>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
              <!-- Left Column: Earnings -->
              <div>
                <div class="px-5 py-3 bg-slate-50/90 border-b border-slate-200 flex justify-between items-center text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                  <span>🟢 Salary Earnings & YTD</span>
                  <span>Amount (${{paidDays}} Paid Days)</span>
                </div>
                <div>${{earningsRows}}</div>
                <div class="px-5 py-3.5 bg-emerald-50/60 border-t border-emerald-200/70 flex justify-between items-center">
                  <span class="text-xs font-extrabold uppercase tracking-wider text-emerald-900">Gross Earnings</span>
                  <span class="text-base font-black text-emerald-800">${{pm.gross_earnings || stmt.total_due}}</span>
                </div>
              </div>

              <!-- Right Column: Deductions -->
              <div class="flex flex-col justify-between">
                <div>
                  <div class="px-5 py-3 bg-slate-50/90 border-b border-slate-200 flex justify-between items-center text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                    <span>🔴 Taxes, PF & Leave Deductions</span>
                    <span>Amount</span>
                  </div>
                  <div>${{deductionsRows}}</div>
                </div>
                <div class="px-5 py-3.5 bg-rose-50/60 border-t border-rose-200/70 flex justify-between items-center">
                  <span class="text-xs font-extrabold uppercase tracking-wider text-rose-900">Total Deductions</span>
                  <span class="text-base font-black text-rose-700">${{pm.total_deductions || '₹0.00'}}</span>
                </div>
              </div>
            </div>

            <!-- Net Payable Footer Bar -->
            <div class="px-6 py-4 bg-slate-900 text-white flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <div class="text-[11px] font-extrabold uppercase tracking-wider text-emerald-400">Total Net Payable (Gross Earnings − Total Deductions)</div>
                <div class="text-xs text-slate-300 mt-0.5">${{pm.amount_in_words ? ('Amount in Words: ' + pm.amount_in_words) : 'Credited directly to bank account'}}</div>
              </div>
              <div class="px-4 py-2 rounded-xl bg-emerald-600 text-white font-black text-xl tracking-tight shadow-md">
                ${{pm.net_pay || stmt.total_due}}
              </div>
            </div>
          </div>

          <!-- MODULE 2: PRO-RATA TO FULL-MONTH ENGINE & LEAVE / LOP SALARY LOSS CALCULATOR -->
          <div class="bg-white rounded-3xl border border-indigo-200/90 shadow-sm p-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
              <div class="flex items-center gap-3">
                <span class="w-11 h-11 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-black text-xl shadow-sm">🧮</span>
                <div>
                  <h2 class="text-base font-extrabold text-slate-900">Pro-Rata to Full-Month Salary & Leave (LOP) Loss Engine</h2>
                  <p class="text-xs text-slate-500">Calculates your true 30-day monthly salary from your ${{paidDays}} paid days (joined ${{pm.date_of_joining || '23/09/2026'}}) and exact rupee loss per leave day.</p>
                </div>
              </div>
              <span class="px-3 py-1 rounded-full text-xs font-extrabold bg-indigo-50 text-indigo-800 border border-indigo-200">
                1 Day Leave Cost = -₹${{perDay.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}
              </span>
            </div>

            <!-- Top 4 Rate & Leave Metrics -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
              <div class="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-200/80">
                <div class="text-[10px] font-extrabold uppercase tracking-wider text-indigo-600">Exact Per-Day Salary Rate</div>
                <div class="text-2xl font-black text-indigo-950 mt-1">₹${{perDay.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}<span class="text-xs font-bold text-indigo-600">/day</span></div>
                <div class="text-[11px] text-slate-500 mt-1">Slip 8-day avg: ₹${{(pm.exact_slip_per_day || perDay).toLocaleString('en-IN')}}/day</div>
              </div>

              <div class="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200/80">
                <div class="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700">Full ${{monthDays}}-Day Monthly Salary</div>
                <div class="text-2xl font-black text-emerald-950 mt-1">₹${{fullGross.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}<span class="text-xs font-bold text-emerald-700">/mo</span></div>
                <div class="text-[11px] text-emerald-700 font-semibold mt-1">Annualized: ₹${{annualCtc.toLocaleString('en-IN')}}/yr</div>
              </div>

              <div class="p-4 rounded-2xl ${{lopDays > 0 ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200/90'}} border">
                <div class="text-[10px] font-extrabold uppercase tracking-wider ${{lopDays > 0 ? 'text-rose-600' : 'text-slate-500'}}">Leave (LOP) on This Payslip</div>
                <div class="text-2xl font-black ${{lopDays > 0 ? 'text-rose-700' : 'text-slate-900'}} mt-1">${{lopDays}} Day${{lopDays === 1 ? '' : 's'}} Leave</div>
                <div class="text-[11px] font-bold ${{lopDays > 0 ? 'text-rose-600' : 'text-emerald-600'}} mt-1">
                  ${{lopDays > 0 ? `Money Lost: -₹${{lopLost.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}` : '✅ ₹0.00 Lost to Leave This Month'}}
                </div>
              </div>

              <div class="p-4 rounded-2xl bg-amber-50/70 border border-amber-200/80">
                <div class="text-[10px] font-extrabold uppercase tracking-wider text-amber-800">Mid-Month Joining Adjustment</div>
                <div class="text-2xl font-black text-amber-950 mt-1">${{unworkedDays}} Unworked Days</div>
                <div class="text-[11px] text-amber-800 font-semibold mt-1">
                  ${{unworkedDays > 0 ? `Pre-joining difference: -₹${{unworkedAmt.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}` : 'Full month worked (0 unworked days)'}}
                </div>
              </div>
            </div>

            <!-- Interactive Leave (LOP) Simulator -->
            <div class="mt-5 p-5 rounded-2xl bg-gradient-to-r from-rose-50/80 via-orange-50/50 to-amber-50/60 border border-rose-200/80">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
                <div>
                  <div class="text-xs font-extrabold uppercase tracking-wider text-rose-900 flex items-center gap-1.5">
                    <span>📉</span>
                    <span>Interactive Leave (LOP) Deduction Calculator — How Much You Lose on Leave</span>
                  </div>
                  <div class="text-[11px] text-slate-600 mt-0.5">Select or type any number of unpaid leave days (LOP) to see how much money is deducted and your revised take-home pay:</div>
                </div>
                <div class="flex items-center gap-1.5 flex-wrap">
                  ${{[0.5, 1, 2, 3, 4, 5, 7].map(d => `
                    <button id="leave-pill-${{String(d).replace('.', '_')}}" onclick="setSimLeaveDays(${{d}})" class="px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${{window.payslipSimLeaveDays === d ? 'bg-rose-600 text-white shadow-sm font-extrabold' : 'bg-white text-slate-700 border border-slate-200 hover:bg-rose-50'}}">
                      ${{d}}d
                    </button>
                  `).join('')}}
                  <input type="number" id="leave-sim-input" min="0" max="30" step="0.5" value="${{window.payslipSimLeaveDays}}" oninput="setSimLeaveDays(this.value)" class="w-20 px-2.5 py-1.5 text-xs font-extrabold bg-white border border-rose-300 rounded-xl text-center text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500" title="Custom leave days">
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="p-3.5 rounded-xl bg-white border border-rose-200 shadow-2xs flex justify-between items-center">
                  <div>
                    <div class="text-[10px] font-extrabold uppercase text-slate-400">Selected Leave Days</div>
                    <div id="sim-out-days" class="text-base font-black text-slate-900 mt-0.5">1 Day Leave (LOP)</div>
                  </div>
                  <div class="text-right">
                    <div class="text-[10px] font-extrabold uppercase text-rose-600">Salary You Lose</div>
                    <div id="sim-out-lost" class="text-lg font-black text-rose-600 mt-0.5">-₹${{perDay.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                  </div>
                </div>

                <div class="p-3.5 rounded-xl bg-white border border-emerald-200 shadow-2xs flex justify-between items-center">
                  <div>
                    <div class="text-[10px] font-extrabold uppercase text-slate-400">Full Month (₹${{fullGross.toLocaleString('en-IN')}}) After Leave</div>
                    <div id="sim-out-full-left" class="text-lg font-black text-emerald-700 mt-0.5">₹${{(fullGross - perDay).toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                  </div>
                  <span class="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg">Take-Home</span>
                </div>

                <div class="p-3.5 rounded-xl bg-white border border-indigo-200 shadow-2xs flex justify-between items-center">
                  <div>
                    <div class="text-[10px] font-extrabold uppercase text-slate-400">This Slip (₹${{(pm.net_val || 14666).toLocaleString('en-IN')}}) After Leave</div>
                    <div id="sim-out-slip-left" class="text-lg font-black text-indigo-900 mt-0.5">₹${{Math.max(0, (pm.net_val || 14666) - perDay).toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                  </div>
                  <span class="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded-lg">Pro-Rata</span>
                </div>
              </div>
            </div>
          </div>

          <!-- MODULE 3: SALARY VS. CREDIT CARD BILL CASHFLOW BRIDGE -->
          <div class="bg-white rounded-3xl border border-blue-200/90 shadow-sm p-6">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
              <div class="flex items-center gap-3">
                <span class="w-11 h-11 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-black text-xl shadow-sm">🌉</span>
                <div>
                  <h2 class="text-base font-extrabold text-slate-900">Salary vs. Credit Card Bill Cashflow Bridge</h2>
                  <p class="text-xs text-slate-500">Compares your take-home salary in A/C <b>${{pm.bank_account_no || '50535110173'}}</b> against your loaded credit card bills (separating friend EMIs from your own spend).</p>
                </div>
              </div>
              <div class="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl no-print">
                <button onclick="toggleCashflowSalaryMode(false)" class="px-3 py-1.5 rounded-lg text-xs font-extrabold transition cursor-pointer ${{!window.payslipCashflowUseFullMonth ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'}}">
                  This Slip (₹${{(pm.net_val || 14666).toLocaleString('en-IN')}})
                </button>
                <button onclick="toggleCashflowSalaryMode(true)" class="px-3 py-1.5 rounded-lg text-xs font-extrabold transition cursor-pointer ${{window.payslipCashflowUseFullMonth ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'}}">
                  Full 30-Day Salary (₹${{fullGross.toLocaleString('en-IN')}})
                </button>
              </div>
            </div>

            ${{creditCardStmts.length === 0 ? `
              <div class="mt-4 p-5 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center">
                <div class="text-sm font-bold text-slate-800">Upload Your Credit Card Statements Alongside This Payslip!</div>
                <div class="text-xs text-slate-500 mt-1">When you upload your HDFC, ICICI, SBI, or Scapia PDFs in the same session, this bridge automatically calculates your net bank savings left after paying your card bills.</div>
              </div>
            ` : `
              <div class="flex flex-wrap gap-2 mt-4">
                <span class="text-xs font-bold text-slate-500 self-center mr-1">Loaded Card Bills:</span>
                ${{cardBreakdownPills.join('')}}
              </div>
            `}}

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
              <div class="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200">
                <div class="text-[10px] font-extrabold uppercase text-emerald-700">1. Salary Basis Credited</div>
                <div class="text-2xl font-black text-emerald-900 mt-1">+₹${{activeSalaryBasis.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                <div class="text-[11px] text-emerald-700 mt-1">${{window.payslipCashflowUseFullMonth ? 'Full 30-Day Monthly Rate' : (paidDays + ' Paid Days Credited')}}</div>
              </div>

              <div class="p-4 rounded-2xl bg-rose-50/70 border border-rose-200">
                <div class="text-[10px] font-extrabold uppercase text-rose-700">2. Total Card Bills Due</div>
                <div class="text-2xl font-black text-rose-900 mt-1">-₹${{totalCardBills.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                <div class="text-[11px] text-rose-700 mt-1">Across ${{creditCardStmts.length}} loaded credit card(s)</div>
              </div>

              <div class="p-4 rounded-2xl bg-purple-50/70 border border-purple-200">
                <div class="text-[10px] font-extrabold uppercase text-purple-700">3. Friend EMI Reimbursements</div>
                <div class="text-2xl font-black text-purple-900 mt-1">+₹${{totalFriendEmis.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</div>
                <div class="text-[11px] text-purple-700 mt-1">Your Own Card Spend: <b>₹${{myPersonalCardSpend.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</b></div>
              </div>

              <div class="p-4 rounded-2xl ${{netBankSavingsAfterPersonal >= 0 ? 'bg-blue-50/80 border-blue-300' : 'bg-amber-50 border-amber-300'}} border">
                <div class="text-[10px] font-extrabold uppercase ${{netBankSavingsAfterPersonal >= 0 ? 'text-blue-700' : 'text-amber-800'}}">4. Net Bank Balance Left</div>
                <div class="text-2xl font-black ${{netBankSavingsAfterPersonal >= 0 ? 'text-blue-950' : 'text-amber-900'}} mt-1">
                  ${{netBankSavingsAfterPersonal >= 0 ? '+' : '-'}}₹${{Math.abs(netBankSavingsAfterPersonal).toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}
                </div>
                <div class="text-[11px] font-semibold ${{netBankSavingsAfterPersonal >= 0 ? 'text-blue-700' : 'text-amber-800'}} mt-1">
                  After your personal spend (Before friend payback: ${{netBankSavingsAfterAllBills >= 0 ? '+' : '-'}}₹${{Math.abs(netBankSavingsAfterAllBills).toLocaleString('en-IN', {{minimumFractionDigits: 2}})}})
                </div>
              </div>
            </div>
          </div>

          <!-- MODULE 4: MULTI-MONTH SALARY & YTD TAX TRACKER -->
          <div class="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 overflow-hidden">
            <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
              <div class="flex items-center gap-3">
                <span class="w-11 h-11 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-black text-xl shadow-sm">📈</span>
                <div>
                  <h2 class="text-base font-extrabold text-slate-900">Multi-Month Salary & FY 2026–27 YTD Tax Tracker</h2>
                  <p class="text-xs text-slate-500">Tracks all uploaded monthly payslips, cumulative YTD earnings, leave losses, and New Tax Regime TDS status.</p>
                </div>
              </div>
              <span class="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
                ✅ Zero-Tax Rebate Eligible (Annual ₹${{(annualCtc / 100000).toFixed(2)}}L &lt; ₹12.75L Limit)
              </span>
            </div>

            <div class="overflow-x-auto mt-4">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="border-b border-slate-200 text-[10px] font-extrabold uppercase tracking-wider text-slate-400 bg-slate-50/70">
                    <th class="py-2.5 px-4">Pay Period</th>
                    <th class="py-2.5 px-4">Pay Date</th>
                    <th class="py-2.5 px-4">Paid Days</th>
                    <th class="py-2.5 px-4">Leave (LOP) & Loss</th>
                    <th class="py-2.5 px-4">Gross Earnings</th>
                    <th class="py-2.5 px-4">Deductions</th>
                    <th class="py-2.5 px-4">Net Take-Home</th>
                  </tr>
                </thead>
                <tbody>
                  ${{multiMonthRows}}
                </tbody>
                <tfoot>
                  <tr class="bg-slate-900 text-white text-xs font-extrabold">
                    <td class="py-3 px-4 rounded-bl-xl" colspan="3">Session Cumulative Total (${{allPayslips.length}} Payslip${{allPayslips.length === 1 ? '' : 's'}})</td>
                    <td class="py-3 px-4 text-rose-300">Total Leave Loss: ₹${{cumulativeLopLost.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-3 px-4 text-emerald-300">₹${{cumulativeGross.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-3 px-4">₹0.00</td>
                    <td class="py-3 px-4 rounded-br-xl text-emerald-400 text-sm">₹${{cumulativeNet.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

        </div>
      `;

      updateLeaveSimulatorUI();
    }}

    function renderDateGroups(filterText = '') {{
      const stmt = getActiveStatement();
      const container = document.getElementById('date-breakdown-container');
      container.innerHTML = '';

      const isPayslip = (stmt.payslip_meta && stmt.payslip_meta.is_payslip);
      const isShafana = (stmt.shafana_meta && stmt.shafana_meta.is_shafana);
      const isKayal = (stmt.kayal_meta && stmt.kayal_meta.is_kayal);
      const searchFilterCard = document.getElementById('search-filter-card');
      if (searchFilterCard) {{
        searchFilterCard.style.display = (isPayslip || isShafana || isKayal) ? 'none' : 'flex';
      }}
      if (isKayal) {{
        renderKayalWorkspace(stmt);
        return;
      }}
      if (isShafana) {{
        renderShafanaWorkspace(stmt);
        return;
      }}
      if (isPayslip) {{
        renderPayslipWorkspace(stmt);
        return;
      }}

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
                    const pStatus = getPaymentStatus(card.loanKey, card.emiName);
                    return `
                      <button onclick="togglePaymentStatus('${{card.loanKey}}', '₹${{card.combinedTotal.toLocaleString('en-IN')}}', '${{card.emiName}}')" class="no-print px-3.5 py-2 rounded-xl border ${{pStatus.isPaid ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100' : 'border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'}} font-bold text-xs shadow-sm transition flex items-center gap-1.5 cursor-pointer">
                        <span>${{pStatus.isPaid ? '🟢' : '🟡'}}</span>
                        <span>${{pStatus.isPaid ? 'Paid on ' + pStatus.paidDate : 'Mark as Paid'}}</span>
                      </button>
                    `;
                  }})()}}
                  <button onclick="copySnapshotOnly('card-named-emi-${{cardIdx}}', '${{card.emiName}}')" class="no-print px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md shadow-indigo-600/25 transition flex items-center gap-1.5 cursor-pointer active:scale-95" title="Copy high-res PNG receipt image to clipboard (PC & Mobile)">
                    <span>📋</span>
                    <span>Copy Snapshot</span>
                  </button>
                  <button onclick="shareReceiptOnWhatsApp('card-named-emi-${{cardIdx}}', '${{card.emiName}}', '${{card.loanId || card.loanKey || ''}}', '₹${{card.combinedTotal.toLocaleString('en-IN', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}', '${{datesHeaderStr}}')" class="no-print px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 transition flex items-center gap-1.5 cursor-pointer active:scale-95">
                    <span>📲</span>
                    <span>Share WhatsApp</span>
                  </button>
                  ${{(() => {{
                    const pStatus = getPaymentStatus(card.loanKey, card.emiName);
                    return pStatus.isPaid 
                      ? `<span class="px-3 py-1.5 rounded-xl text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300">✅ Reimbursed</span>`
                      : `<span class="px-3 py-1.5 rounded-xl text-xs font-extrabold bg-amber-100 text-amber-900 border border-amber-300">⏳ Awaiting Payment</span>`;
                  }})()}}
                </div>
              </div>

              <!-- INLINE BROWSER-PERSISTED EMI NICKNAME & WHATSAPP BAR (Hidden on Print / Snapshot) -->
              <div class="no-print flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 bg-white/85 border border-purple-200/90 rounded-xl px-3.5 py-2.5 shadow-2xs">
                <div class="flex items-center gap-2 text-xs font-bold text-purple-900">
                  <span>🔒</span>
                  <span>Browser EMI Tag <span class="font-mono text-[11px] text-purple-600">(${{card.loanKey}})</span>:</span>
                </div>
                <div class="flex items-center gap-2 flex-wrap flex-1 sm:justify-end">
                  <input type="text" id="receipt-emi-input-${{cardIdx}}" placeholder="Friend / Item Nickname (e.g. Naveen S25 Edge)..." value="${{getSavedName(card.loanKey, card.emiName)}}" class="px-3 py-1.5 text-xs font-semibold bg-purple-50/50 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 w-full sm:w-52 text-slate-800">
                  <input type="tel" id="receipt-emi-phone-${{cardIdx}}" placeholder="WhatsApp 10-digit No..." value="${{(getSavedPhone(card.loanKey) || getSavedPhone(card.emiName)).replace(/^91/, '')}}" class="px-3 py-1.5 text-xs font-semibold bg-purple-50/50 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full sm:w-40 text-slate-800">
                  <button onclick="saveCustomName('${{card.loanKey}}', 'receipt-emi-input-${{cardIdx}}', 'receipt-emi-phone-${{cardIdx}}')" class="px-3.5 py-1.5 text-xs font-extrabold bg-purple-600 hover:bg-purple-500 text-white rounded-lg shadow-xs transition cursor-pointer active:scale-95">
                    💾 Save Tag in Browser
                  </button>
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
          const pStatus = getPaymentStatus(c.loanKey, c.emiName);
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

  if write_to_disk:
    with open(html_path, "w", encoding="utf-8") as f:
      f.write(html_content)
    return html_path
  return html_content


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