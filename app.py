"""Smart Bill Segregator - Streamlit Web Application
Renders the exact, authentic, mobile-and-PC responsive web dashboard.
Strict Zero-Disk Security Architecture:
  - Uploaded PDFs are processed 100% in RAM (io.BytesIO) and NEVER written to disk.
  - Decrypted PDFs are NEVER saved to 'Statements_*' or 'temp_uploaded_statements' folders on the server.
  - Dashboard HTML is generated strictly in RAM per browser session.
  - Passwords are stored strictly in the user's client browser localStorage (never on the server).
"""

import io
import os
import sys
import time
import json
import base64
import shutil
import subprocess
import importlib
from datetime import datetime, timezone, timedelta
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
import unlock_statements

# Force reload of unlock_statements on every run so Streamlit Cloud never caches an older version in sys.modules
importlib.reload(unlock_statements)

def get_git_last_updated_info():
    """Returns the latest Git commit timestamp (in IST), short hash, and commit message."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%ct|%h|%s"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2
        ).strip()
        if out and "|" in out:
            parts = out.split("|", 2)
            ts = int(parts[0].strip())
            short_hash = parts[1].strip()
            subject = parts[2].strip() if len(parts) > 2 else "Updated"
            dt_ist = datetime.fromtimestamp(ts, tz=ist_tz)
            return {
                "time_str": dt_ist.strftime("%d %b %Y, %I:%M %p IST"),
                "hash": short_hash,
                "msg": subject
            }
    except Exception:
        pass

    # Fallback to latest file modification time in IST if git CLI is unavailable
    try:
        latest_mtime = max(
            os.path.getmtime(os.path.join(repo_dir, f))
            for f in ["app.py", "unlock_statements.py"]
            if os.path.exists(os.path.join(repo_dir, f))
        )
        dt_ist = datetime.fromtimestamp(latest_mtime, tz=ist_tz)
        return {
            "time_str": dt_ist.strftime("%d %b %Y, %I:%M %p IST"),
            "hash": "local",
            "msg": "File system sync"
        }
    except Exception:
        now_ist = datetime.now(tz=ist_tz)
        return {
            "time_str": now_ist.strftime("%d %b %Y, %I:%M %p IST"),
            "hash": "live",
            "msg": "Active session"
        }

# --- Automatic Cleanup of Any Legacy Server Disk Artifacts ---
for _legacy_dir in ["Statements_October_2026", "temp_uploaded_statements"]:
    if os.path.exists(_legacy_dir):
        try:
            shutil.rmtree(_legacy_dir, ignore_errors=True)
        except Exception:
            pass

# --- Page Configuration (Collapsed Sidebar for Clean Native App Experience) ---
st.set_page_config(
    page_title="Smart Bill Segregator",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize Session State ---
if "session_passwords" not in st.session_state:
    st.session_state.session_passwords = {"icici": "", "hdfc": "", "sbi": "", "scapia": "", "payslip": "", "sheets_webhook_url": "", "gemini_api_key": ""}
if "emi_nicknames" not in st.session_state:
    st.session_state.emi_nicknames = {}
if "emi_phones" not in st.session_state:
    st.session_state.emi_phones = {}
if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []
if "show_ai_chat" not in st.session_state:
    st.session_state.show_ai_chat = False
if "show_shafana_tracker" not in st.session_state:
    st.session_state.show_shafana_tracker = False
if "show_kayal_roster" not in st.session_state:
    st.session_state.show_kayal_roster = False
if "active_special_view" not in st.session_state:
    st.session_state.active_special_view = None
if "active_nav" not in st.session_state:
    st.session_state.active_nav = "statements"
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "light"
if "statements_data" not in st.session_state:
    st.session_state.statements_data = {}

is_dark = (st.session_state.ui_theme == "dark")

# --- Apple / Fintech Adaptive Stylesheet (Dark & Light Mode) ---
bg_main = "#090d16" if is_dark else "#f8fafc"
bg_surface = "#111827" if is_dark else "#ffffff"
bg_elevated = "#1e293b" if is_dark else "#ffffff"
border_subtle = "rgba(148, 163, 184, 0.22)" if is_dark else "#cbd5e1"
text_primary = "#f8fafc" if is_dark else "#0f172a"
text_secondary = "#94a3b8" if is_dark else "#475569"
accent_primary = "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)"
accent_border = "#4f46e5"
accent_text = "#ffffff"
btn_sec_bg = "#1e293b" if is_dark else "#ffffff"
btn_sec_border = "#334155" if is_dark else "#cbd5e1"
btn_sec_text = "#f8fafc" if is_dark else "#0f172a"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

    .stApp, [data-testid="stAppViewContainer"], .main {{
        background-color: {bg_main} !important;
        color: {text_primary} !important;
    }}

    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: {text_primary} !important;
    }}

    /* Hide bulky left sidebar & Streamlit chrome completely */
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    #MainMenu,
    [data-testid="stDecoration"],
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    [data-testid="stStatusWidget"],
    header[data-testid="stHeader"],
    header,
    footer {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }}

    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        max-width: 1240px !important;
        margin: 0 auto !important;
    }}

    /* Apple-style buttons with explicit child text colors so Light Mode never has black-on-black */
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        letter-spacing: -0.01em !important;
        padding: 0.52rem 0.9rem !important;
        transition: transform 100ms ease-out, background-color 150ms ease, border-color 150ms ease, box-shadow 150ms ease !important;
    }}
    .stButton > button:active, .stDownloadButton > button:active {{
        transform: scale(0.97) !important;
    }}
    .stButton > button[kind="secondary"], .stDownloadButton > button {{
        background: {btn_sec_bg} !important;
        color: {btn_sec_text} !important;
        border: 1.5px solid {btn_sec_border} !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }}
    .stButton > button[kind="secondary"] *, .stDownloadButton > button * {{
        color: {btn_sec_text} !important;
    }}
    .stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover {{
        border-color: #6366f1 !important;
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button {{
        background: {accent_primary} !important;
        color: #ffffff !important;
        border: 1.5px solid {accent_border} !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.28) !important;
    }}
    .stButton > button[kind="primary"] *, .stFormSubmitButton > button * {{
        color: #ffffff !important;
    }}

    /* Sleek File Uploader Dropzone with High-Contrast Button & Helper Text in Both Modes */
    [data-testid="stFileUploader"] {{
        background: {bg_surface} !important;
        border: 1.5px solid {border_subtle} !important;
        border-radius: 16px !important;
        padding: 12px 16px !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
    }}
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] label p {{
        color: {text_primary} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background: {bg_main} !important;
        border: 1.5px dashed {border_subtle} !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
    }}
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] * {{
        color: {text_secondary} !important;
        opacity: 1 !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 6px 16px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25) !important;
    }}
    [data-testid="stFileUploaderDropzone"] button * {{
        color: #ffffff !important;
    }}

    /* Uploaded file pills inside file uploader */
    [data-testid="stFileUploaderFile"] {{
        background: {bg_elevated} !important;
        border: 1px solid {border_subtle} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stFileUploaderFile"] * {{
        color: {text_primary} !important;
    }}

    /* Inputs, Chat Messages & Expanders */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {{
        background: {bg_elevated} !important;
        color: {text_primary} !important;
        border: 1.5px solid {border_subtle} !important;
        border-radius: 10px !important;
        font-size: 13px !important;
    }}
    [data-testid="stChatMessage"] {{
        background: {bg_surface} !important;
        border: 1px solid {border_subtle} !important;
        border-radius: 14px !important;
        padding: 10px 14px !important;
    }}
    [data-testid="stChatMessage"] * {{
        color: {text_primary} !important;
    }}
    [data-testid="stExpander"] {{
        background: {bg_surface} !important;
        border: 1px solid {border_subtle} !important;
        border-radius: 16px !important;
        overflow: hidden !important;
    }}

    iframe {{
        border-radius: 20px;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.18);
        border: 1px solid {border_subtle};
        width: 100% !important;
    }}

    @media (max-width: 640px) {{
        .block-container {{
            padding-top: 0.6rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)

def get_ist_kayal_greeting():
    """Returns time-of-day romantic greeting for Dr Cuteuh Pattuh in Indian Standard Time (IST)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(tz=ist_tz)
    hr = now_ist.hour
    if 5 <= hr < 12:
        g = "🌅 Good Morning, Dr Cuteuh Pattuh! 💖"
    elif 12 <= hr < 17:
        g = "☀️ Good Afternoon, Dr Cuteuh Pattuh! 💖"
    elif 17 <= hr < 21:
        g = "🌆 Good Evening, Dr Cuteuh Pattuh! 💖"
    else:
        g = "🌙 Good Night, Dr Cuteuh Pattuh! 💖"
    return g, now_ist.strftime("%d %b %Y, %I:%M %p IST")

@st.cache_resource
def _cached_kayal_store(_mtime):
    """Cross-session shared store for Dr. Kayalvizhi's duty roster, auto-invalidated when kayal_duty.json updates."""
    return unlock_statements.load_kayal_web_roster()

def get_shared_kayal_store():
    mtime = os.path.getmtime(unlock_statements.KAYAL_WEB_FILE) if os.path.exists(unlock_statements.KAYAL_WEB_FILE) else 0
    return _cached_kayal_store(mtime)

def update_shared_kayal_store(new_roster, gh_token=""):
    """Updates the shared server store, writes kayal_duty.json, and optionally pushes to GitHub."""
    store = get_shared_kayal_store()
    store.clear()
    store.update(new_roster)
    unlock_statements.save_kayal_web_roster(store)
    token = _get_github_token(gh_token)
    if token:
        try:
            import urllib.request
            api_url = "https://api.github.com/repos/xrvnsp/smart-bill-segregator/contents/kayal_duty.json"
            req_get = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "SmartBillSegregator"})
            sha = None
            try:
                with urllib.request.urlopen(req_get, timeout=4) as resp:
                    sha = json.loads(resp.read().decode("utf-8")).get("sha")
            except Exception:
                pass
            content_b64 = base64.b64encode(json.dumps(store, indent=2, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            body = {"message": "Sync Dr. Kayalvizhi duty roster", "content": content_b64, "branch": "main"}
            if sha:
                body["sha"] = sha
            req_put = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode("utf-8"),
                method="PUT",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "SmartBillSegregator"}
            )
            urllib.request.urlopen(req_put, timeout=5)
        except Exception:
            pass
    return store

@st.cache_resource
def get_shared_shafana_store():
    """Cross-session shared in-memory & disk store ONLY for Shafana's non-sensitive cashback ledger."""
    return unlock_statements.load_shafana_web_ledger()

def _get_github_token(explicit=""):
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        if "GITHUB_TOKEN" in st.secrets and str(st.secrets["GITHUB_TOKEN"]).strip():
            return str(st.secrets["GITHUB_TOKEN"]).strip()
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "").strip()

def sync_bill_names_to_github(meta_obj=None, commit_msg="Sync bill_names.json from Streamlit"):
    token = _get_github_token()
    if not token:
        return
    if meta_obj is None:
        meta_obj = unlock_statements.load_bill_names_web()
    try:
        import urllib.request
        api_url = "https://api.github.com/repos/xrvnsp/smart-bill-segregator/contents/bill_names.json"
        req_get = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "SmartBillSegregator"})
        sha = None
        try:
            with urllib.request.urlopen(req_get, timeout=4) as resp:
                sha = json.loads(resp.read().decode("utf-8")).get("sha")
        except Exception:
            pass
        content_b64 = base64.b64encode(json.dumps(meta_obj, indent=2, ensure_ascii=False).encode("utf-8")).decode("utf-8")
        body = {"message": commit_msg, "content": content_b64, "branch": "main"}
        if sha:
            body["sha"] = sha
        req_put = urllib.request.Request(
            api_url,
            data=json.dumps(body).encode("utf-8"),
            method="PUT",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "SmartBillSegregator"}
        )
        urllib.request.urlopen(req_put, timeout=5)
    except Exception:
        pass

def update_shared_shafana_store(new_ledger, gh_token=""):
    """Updates the shared server store, writes shafana_cashback.json, and optionally pushes to GitHub."""
    store = get_shared_shafana_store()
    store.clear()
    store.update(new_ledger)
    unlock_statements.save_shafana_web_ledger(store)
    token = _get_github_token(gh_token)
    if token:
        try:
            import urllib.request
            api_url = "https://api.github.com/repos/xrvnsp/smart-bill-segregator/contents/shafana_cashback.json"
            req_get = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "SmartBillSegregator"})
            sha = None
            try:
                with urllib.request.urlopen(req_get, timeout=4) as resp:
                    meta = json.loads(resp.read().decode("utf-8"))
                    sha = meta.get("sha")
            except Exception:
                pass
            content_b64 = base64.b64encode(json.dumps(store, indent=2, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            body = {"message": "Sync Shafana cashback ledger across web", "content": content_b64, "branch": "main"}
            if sha:
                body["sha"] = sha
            req_put = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode("utf-8"),
                method="PUT",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "SmartBillSegregator"}
            )
            urllib.request.urlopen(req_put, timeout=5)
        except Exception:
            pass
    return store

def forget_browser_passwords():
    st.session_state.session_passwords = {"scapia": "", "icici": "", "hdfc": "", "sbi": "", "payslip": "", "sheets_webhook_url": ""}
    for k in ["input_scapia_pwd", "input_hdfc_pwd", "input_icici_pwd", "input_sbi_pwd", "input_payslip_pwd", "input_webhook_url",
              "q_inp_scapia", "q_inp_hdfc", "q_inp_icici", "q_inp_sbi", "q_inp_payslip"]:
        st.session_state[k] = ""
    st.session_state["pending_clear_vault"] = True
    st.session_state["vault_cleared_until"] = time.time() + 4.0
    st.session_state["sidebar_toast_until"] = time.time() + 5.0
    st.session_state["sidebar_toast_notice"] = {
        "type": "info",
        "title": "Passwords Cleared",
        "desc": "Wiped from this device browser vault."
    }

# --- Device-Local Browser Storage Bridge (Client-Side localStorage) ---
bridge_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_storage_bridge")
storage_bridge = components.declare_component("local_storage_bridge", path=bridge_dir)

# Handle pending save or clear commands for browser localStorage
pending_save = st.session_state.pop("pending_save_vault", None)
pending_clear = st.session_state.pop("pending_clear_vault", None)
pending_save_emi = st.session_state.pop("pending_save_emi_vault", None)
pending_clear_emi = st.session_state.pop("pending_clear_emi_vault", None)

# Run the invisible client-side bridge in the user's browser (height=0)
client_vault = storage_bridge(
    save_passwords=pending_save,
    clear_passwords=pending_clear,
    save_emi_vault=pending_save_emi,
    clear_emi_vault=pending_clear_emi,
    key="browser_vault_bridge"
)

now_ts = time.time()
is_clearing = pending_clear or (now_ts < st.session_state.get("vault_cleared_until", 0))
is_clearing_emi = pending_clear_emi or (now_ts < st.session_state.get("emi_vault_cleared_until", 0))

# If client_vault passwords are verified empty by browser component, release the clearing lock
if not client_vault or (isinstance(client_vault, dict) and not any(str(client_vault.get(k, "")).strip() for k in ["scapia", "hdfc", "icici", "sbi", "payslip", "sheets_webhook_url"])):
    st.session_state.pop("vault_cleared_until", None)

# Restore saved passwords & EMI nicknames from browser localStorage
if client_vault and isinstance(client_vault, dict):
    if not is_clearing:
        restored_keys = []
        for b_key, b_name in [("hdfc", "HDFC Bank"), ("icici", "ICICI Bank"), ("sbi", "SBI SimplyCLICK"), ("scapia", "Scapia Axis"), ("payslip", "Salary Payslip")]:
            if not st.session_state.session_passwords.get(b_key) and client_vault.get(b_key) and str(client_vault[b_key]).strip():
                st.session_state.session_passwords[b_key] = str(client_vault[b_key]).strip()
                restored_keys.append(b_name)
        if not st.session_state.session_passwords.get("sheets_webhook_url") and client_vault.get("sheets_webhook_url"):
            st.session_state.session_passwords["sheets_webhook_url"] = str(client_vault["sheets_webhook_url"]).strip()
        if not st.session_state.session_passwords.get("gemini_api_key") and client_vault.get("gemini_api_key"):
            st.session_state.session_passwords["gemini_api_key"] = str(client_vault["gemini_api_key"]).strip()

    if not is_clearing_emi:
        vault_emi_names = client_vault.get("emi_names")
        if isinstance(vault_emi_names, dict):
            for k, v in vault_emi_names.items():
                if k and v and str(v).strip():
                    st.session_state.emi_nicknames[str(k).strip()] = str(v).strip()
        vault_emi_phones = client_vault.get("emi_phones")
        if isinstance(vault_emi_phones, dict):
            for k, v in vault_emi_phones.items():
                if k and v and str(v).strip():
                    st.session_state.emi_phones[str(k).strip()] = str(v).strip()
        vault_bn = client_vault.get("bill_names")
        vault_pc = client_vault.get("paid_cards")
        if isinstance(vault_bn, dict) or isinstance(vault_pc, dict):
            meta_bn_sync = unlock_statements.load_bill_names_web()
            changed_bn = False
            if isinstance(vault_bn, dict):
                for k, v in vault_bn.items():
                    if k and v and meta_bn_sync.setdefault("bill_names", {}).get(k) != v:
                        meta_bn_sync["bill_names"][k] = v
                        changed_bn = True
            if isinstance(vault_pc, dict):
                for k, v in vault_pc.items():
                    if k and meta_bn_sync.setdefault("paid_cards", {}).get(k) != v:
                        meta_bn_sync["paid_cards"][k] = v
                        changed_bn = True
            if changed_bn:
                unlock_statements.save_bill_names_web(meta_bn_sync)


def _get_gemini_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets and str(st.secrets["GEMINI_API_KEY"]).strip():
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    env_k = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_k:
        return env_k
    return st.session_state.session_passwords.get("gemini_api_key", "").strip()

def _is_card_paid(paid_cards_dict, *keys):
    for k in keys:
        if not k:
            continue
        val = paid_cards_dict.get(k)
        if isinstance(val, dict) and val.get("isPaid"):
            return True, val.get("paidDate", "")
        if val is True or val == "true":
            return True, ""
    return False, ""

def _save_statement_summary_to_bill_names(slot_key, rdata):
    if not rdata or (rdata.get("shafana_meta") or {}).get("is_shafana") or (rdata.get("kayal_meta") or {}).get("is_kayal") or (rdata.get("payslip_meta") or {}).get("is_payslip"):
        return
    bn = unlock_statements.load_bill_names_web()
    b_short = rdata.get("bank_short", "")
    s_month = rdata.get("statement_month", "")
    if not b_short:
        return
    sum_key = re.sub(r"[^a-zA-Z0-9_]", "_", f"{b_short}_{s_month}")
    emis_out = []
    for e in rdata.get("ongoing_emis", []):
        lid = str(e.get("loan_id", ""))
        ename = st.session_state.emi_nicknames.get(lid) or bn.get("bill_names", {}).get(lid) or e.get("custom_name") or lid
        emis_out.append({
            "loan_id": lid,
            "name": ename,
            "total_amount": e.get("total_amount", ""),
            "monthly_emi": e.get("monthly_emi", ""),
            "balance_tenure": e.get("balance_tenure", "")
        })
    date_cards_out = []
    for dt_str, grp in (rdata.get("date_groups") or {}).items():
        tot = float(grp.get("total", 0.0) or 0.0)
        if tot <= 0:
            continue
        d_key = re.sub(r"[^a-zA-Z0-9_]", "_", f"date_{b_short}_{s_month}_{dt_str}")
        items_desc = [f"{it.get('description', '')} (₹{float(it.get('amount', 0)):,.2f})" for it in (grp.get("items") or []) if not it.get("is_credit")]
        date_cards_out.append({
            "date": dt_str,
            "bill_key": d_key,
            "total": tot,
            "items": items_desc[:6]
        })
    summary_obj = {
        "bank_short": b_short,
        "statement_month": s_month,
        "total_due": rdata.get("total_due", ""),
        "due_date": rdata.get("due_date", ""),
        "ongoing_emis": emis_out,
        "date_cards": date_cards_out
    }
    if bn.setdefault("statement_summaries", {}).get(sum_key) != summary_obj:
        bn["statement_summaries"][sum_key] = summary_obj
        unlock_statements.save_bill_names_web(bn)
        sync_bill_names_to_github(bn, commit_msg=f"Auto-sync {b_short} {s_month} summary")

def _build_compact_ai_context():
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(tz=ist_tz).strftime("%d %b %Y, %I:%M %p IST (%A)")

    # 1. Dr. Kayalvizhi Duty Roster (Full Daily Lineup + Relief Combinations)
    ky = get_shared_kayal_store()
    ky_lines = []
    for e in ky.get("entries", []):
        opd_d = e.get("opd_doctors", "")
        eve_d = e.get("evening_doctors", "")
        ngt_d = e.get("night_doctors", "")
        rel_from = e.get("kayal_relieves", "-")
        rel_by = e.get("kayal_relieved_by", "-")
        extra_roster = ""
        if opd_d or eve_d or ngt_d:
            extra_roster = f" | Roster [OPD: {opd_d}; Eve: {eve_d}; Night: {ngt_d}] | Kayal Relieves: {rel_from} | Relieved By: {rel_by}"
        ky_lines.append(f"- {e.get('date')} ({e.get('day')}): Kayal={e.get('shift')} ({e.get('note', '')}){extra_roster}")

    wk_lines = []
    for wk in ky.get("weekly_doctor_summary", []):
        drs = ", ".join(f"{d['name']}: {d['total']} (OPD {d['opd']}, Rel {d['rel']}, Eve {d['eve']}, Night {d['night']})" for d in wk.get("doctors", []))
        wk_lines.append(f"  * {wk.get('week')}: {drs}")

    combo_lines = []
    rc = ky.get("relief_combinations") or {}
    if rc:
        if rc.get("who_relieves_kayal_most"):
            combo_lines.append("  * Who Relieves Dr. Kayalvizhi Most (Across Her 15 Shifts):")
            for item in rc["who_relieves_kayal_most"]:
                combo_lines.append(f"    - {item['doctor']}: {item['count']} times ({'; '.join(item.get('dates', []))})")
        if rc.get("whom_kayal_relieves_most"):
            combo_lines.append("  * Whom Dr. Kayalvizhi Relieves Most:")
            for item in rc["whom_kayal_relieves_most"]:
                combo_lines.append(f"    - {item['doctor']}: {item['count']} times ({'; '.join(item.get('dates', []))})")
        if rc.get("joint_opd_with_kayal"):
            combo_lines.append("  * Joint OPD Shifts Together:")
            for item in rc["joint_opd_with_kayal"]:
                combo_lines.append(f"    - {item['doctor']}: {item['count']} times ({'; '.join(item.get('dates', []))})")
        if rc.get("overall_combo_ranking"):
            combo_lines.append("  * Overall Highest Doctor Combo with Dr. Kayalvizhi:")
            for item in rc["overall_combo_ranking"]:
                combo_lines.append(f"    - {item['combo']}: {item['total_interactions']} total interactions ({item['breakdown']})")

    # 2. Shafana Cashback
    sf = get_shared_shafana_store()
    sf_orders = [e for e in sf.get("entries", []) if e.get("role") == "shafana_order"]
    sf_bill = sum(float(e.get("amount", 0)) for e in sf_orders)
    sf_earned = float(sf.get("openingCb", 0) or 0) + sum(float(e.get("cashback_earned", 0)) for e in sf_orders)
    sf_used = float(sf.get("manualCbUsed", 0) or 0)
    sf_left = sf_earned - sf_used

    # 3. Saved SmartEMI Plans, Fold Tags & Bill Names/Paid Status
    bn = unlock_statements.load_bill_names_web()
    custom_names_map = dict(bn.get("bill_names") or {})
    custom_names_map.update(st.session_state.emi_nicknames)
    paid_cards_map = dict(bn.get("paid_cards") or {})

    emi_plan_lines = [
        f"- Loan #{p.get('loan_id')} ({custom_names_map.get(str(p.get('loan_id')), p.get('plan_name'))}): ₹{p.get('amount', 0):,.2f}, {p.get('tenure_months')} mos, fee ₹{p.get('processing_fee', 0):,.0f}"
        for p in bn.get("emi_plans", [])
    ]
    fold_lines = [
        f"- {ft.get('date')}: Card **{ft.get('card_last4')} ({ft.get('bank_short', 'ICICI Amazon')}) ₹{ft.get('amount', 0):,.0f} ({ft.get('paid_to')}) -> Note: {ft.get('note')}"
        for ft in bn.get("fold_tags", [])[:15]
    ]

    # 4. Credit Card Statements & Date-Wise Paid/Unpaid Bills (Live Session + Persisted Summaries)
    stmt_lines = []
    seen_banks = set()
    for k_st, rdata in st.session_state.statements_data.items():
        if (rdata.get("shafana_meta") or {}).get("is_shafana") or (rdata.get("kayal_meta") or {}).get("is_kayal"):
            continue
        b_short = rdata.get("bank_short", "")
        s_month = rdata.get("statement_month", "")
        seen_banks.add(f"{b_short}_{s_month}")
        emis = rdata.get("ongoing_emis", [])
        emi_parts = []
        for e in emis:
            lid = str(e.get("loan_id", ""))
            ename = custom_names_map.get(lid) or e.get("custom_name") or lid
            is_p, p_dt = _is_card_paid(paid_cards_map, lid, ename)
            status_lbl = f"PAID {p_dt}".strip() if is_p else "UNPAID"
            emi_parts.append(f"{ename} (Loan {lid}): {e.get('total_amount')}, Monthly EMI {e.get('monthly_emi', '-')}, {e.get('balance_tenure')} [{status_lbl}]")
        card_parts = []
        for dt_str, g in (rdata.get("date_groups") or {}).items():
            tot = float(g.get("total", 0) or 0)
            if tot <= 0:
                continue
            d_key = re.sub(r"[^a-zA-Z0-9_]", "_", f"date_{b_short}_{s_month}_{dt_str}")
            c_name = custom_names_map.get(d_key, "")
            is_p, p_dt = _is_card_paid(paid_cards_map, d_key, c_name)
            status_lbl = f"PAID {p_dt}".strip() if is_p else "UNPAID"
            it_str = ", ".join(f"{it.get('description', '')} ₹{float(it.get('amount', 0)):,.2f}" for it in (g.get("items") or []) if not it.get("is_credit"))
            lbl_str = f" [{c_name}]" if c_name else ""
            card_parts.append(f"  - {dt_str}{lbl_str}: ₹{tot:,.2f} [{status_lbl}] — {it_str}")
        stmt_lines.append(
            f"* {b_short} ({s_month}): Total Due {rdata.get('total_due')}, Due Date {rdata.get('due_date')}\n"
            + (f"  Ongoing EMIs: {'; '.join(emi_parts)}\n" if emi_parts else "")
            + ("  Date-Wise Bill Cards:\n" + "\n".join(card_parts) if card_parts else "")
        )

    for s_key, s_obj in (bn.get("statement_summaries") or {}).items():
        b_short = s_obj.get("bank_short", "")
        s_month = s_obj.get("statement_month", "")
        if f"{b_short}_{s_month}" in seen_banks:
            continue
        emi_parts = []
        for e in s_obj.get("ongoing_emis", []):
            lid = str(e.get("loan_id", ""))
            ename = custom_names_map.get(lid) or e.get("name") or lid
            is_p, p_dt = _is_card_paid(paid_cards_map, lid, ename)
            status_lbl = f"PAID {p_dt}".strip() if is_p else "UNPAID"
            emi_parts.append(f"{ename} (Loan {lid}): {e.get('total_amount')}, Monthly EMI {e.get('monthly_emi', '-')}, {e.get('balance_tenure')} [{status_lbl}]")
        card_parts = []
        for dc in s_obj.get("date_cards", []):
            d_key = dc.get("bill_key", "")
            fb_key = dc.get("fallback_key", "")
            c_name = custom_names_map.get(d_key) or custom_names_map.get(fb_key) or dc.get("custom_name", "")
            is_p, p_dt = _is_card_paid(paid_cards_map, d_key, fb_key, c_name)
            status_lbl = f"PAID {p_dt}".strip() if is_p else "UNPAID"
            lbl_str = f" [{c_name}]" if c_name else ""
            it_str = ", ".join(dc.get("items") or [])
            card_parts.append(f"  - {dc.get('date')}{lbl_str}: ₹{float(dc.get('total', 0)):,.2f} [{status_lbl}] — {it_str}")
        stmt_lines.append(
            f"* {b_short} ({s_month}): Total Due {s_obj.get('total_due')}, Due Date {s_obj.get('due_date')}\n"
            + (f"  Ongoing EMIs: {'; '.join(emi_parts)}\n" if emi_parts else "")
            + ("  Date-Wise Bill Cards:\n" + "\n".join(card_parts) if card_parts else "")
        )

    return (
        f"Current IST Time: {now_ist}\n\n"
        f"[DR. KAYALVIZHI DUTY ROSTER ({ky.get('center_name', 'CHC Thirunallar')}, {ky.get('period', '')})]\n"
        + "\n".join(ky_lines) + "\n"
        + ("Weekly Doctor Totals:\n" + "\n".join(wk_lines) + "\n" if wk_lines else "")
        + ("Doctor Relief & Combination Analysis:\n" + "\n".join(combo_lines) + "\n" if combo_lines else "")
        + f"\n[SHAFANA CASHBACK]\nBill Due: ₹{sf_bill:,.2f}, Earned: ₹{sf_earned:,.2f}, Used: ₹{sf_used:,.2f}, Left: ₹{sf_left:,.2f}\n"
        + ("\n[SAVED SMARTEMI PLANS]\n" + "\n".join(emi_plan_lines) + "\n" if emi_plan_lines else "")
        + ("\n[SAVED FOLD TAGS]\n" + "\n".join(fold_lines) + "\n" if fold_lines else "")
        + ("\n[CREDIT CARD STATEMENTS, EMIS & DATE-WISE PAID/UNPAID BILLS]\n" + "\n".join(stmt_lines) if stmt_lines else "\n[CREDIT CARD STATEMENTS]\nNone available.")
    )

def _ask_gemini_api(user_prompt, api_key):
    import re
    import urllib.request
    import urllib.error
    sys_ctx = (
        "You are a concise, helpful personal assistant inside Saravana's Smart Bill Segregator app. "
        "Answer accurately using ONLY the provided context about Dr. Kayalvizhi's duty roster, Saravana's credit card bills/EMIs, "
        "Shafana's cashback, and saved SmartEMI plans. Keep answers short, clear, and in ₹ for currency.\n\n"
        + _build_compact_ai_context()
    )
    payload = {
        "system_instruction": {"parts": [{"text": sys_ctx}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}
    }

    def _try_model(m_name):
        clean_m = m_name.replace("models/", "").strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_m}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
        cands = res_json.get("candidates") or []
        if cands:
            parts = (cands[0].get("content") or {}).get("parts") or []
            ans = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if not ans:
                ans = "".join(p.get("text", "") for p in parts).strip()
            if ans:
                st.session_state["working_gemini_model"] = clean_m
                return ans
        return None

    candidates = []
    cached_m = st.session_state.get("working_gemini_model")
    if cached_m:
        candidates.append(cached_m)
    for m in (
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
    ):
        if m not in candidates:
            candidates.append(m)

    tried = set()
    last_err = ""
    idx = 0
    while idx < len(candidates):
        model_name = candidates[idx]
        idx += 1
        if not model_name or model_name in tried:
            continue
        tried.add(model_name)
        try:
            ans = _try_model(model_name)
            if ans:
                return True, ans
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {he.code}: {err_body[:220]}"
            # If the API error suggests a specific replacement model (e.g. "use models/gemini-3.5-flash-lite"), try it next
            suggested = re.findall(r"use\s+models/([a-zA-Z0-9._-]+)", err_body)
            for s_mod in suggested:
                if s_mod not in tried and s_mod not in candidates:
                    candidates.insert(idx, s_mod)
        except Exception as ex:
            last_err = str(ex)

    # Dynamic fallback: query /v1beta/models for any available generateContent model on this API key
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        with urllib.request.urlopen(list_url, timeout=10) as lresp:
            m_list = json.loads(lresp.read().decode("utf-8")).get("models") or []
        avail = []
        for m_obj in m_list:
            m_id = (m_obj.get("name") or "").replace("models/", "").strip()
            methods = m_obj.get("supportedGenerationMethods") or []
            if "generateContent" in methods and m_id and m_id not in tried:
                if not any(x in m_id for x in ("tts", "image", "embedding", "imagen", "veo", "aqa", "audio", "robotics", "computer-use")):
                    avail.append(m_id)
        avail.sort(key=lambda x: (0 if "flash" in x else 1, 0 if "3.5" in x or "3" in x else 1, x))
        for m_id in avail[:4]:
            try:
                ans = _try_model(m_id)
                if ans:
                    return True, ans
            except Exception as ex2:
                last_err = str(ex2)
    except Exception:
        pass

    return False, last_err or "No response from Gemini API."

# --- Live Summary Metrics for Header & Segmented Navigation ---
shared_sf = get_shared_shafana_store()
sf_entries = [e for e in shared_sf.get("entries", []) if e.get("role") == "shafana_order"]
sf_open_cb = float(shared_sf.get("openingCb", 0.0) or 0.0)
sf_cb_used = float(shared_sf.get("manualCbUsed", 0.0) or 0.0)
sf_bill_due = sum(float(e.get("amount", 0.0)) for e in sf_entries)
sf_cb_earned = sum(float(e.get("cashback_earned", 0.0)) for e in sf_entries)
sf_net_kitty = sf_open_cb + sf_cb_earned - sf_cb_used

shared_ky = get_shared_kayal_store()
ky_entries = shared_ky.get("entries", [])
ky_active = sum(1 for e in ky_entries if e.get("shift", "OFF").upper() != "OFF")
ky_off = sum(1 for e in ky_entries if e.get("shift", "OFF").upper() == "OFF")

active_vault_list = [
    name for key, name in [("scapia", "Scapia"), ("hdfc", "HDFC"), ("icici", "ICICI"), ("sbi", "SBI"), ("payslip", "Payslip")]
    if st.session_state.session_passwords.get(key)
]
vault_status_text = f"Vault ({len(active_vault_list)})" if active_vault_list else "Vault Empty"
git_info = get_git_last_updated_info()

# --- Sleek Apple / Fintech Top Header Bar ---
hdr_col1, hdr_col2 = st.columns([5.5, 1.1])
with hdr_col1:
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 4px 0 8px 0;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 38px; height: 38px; border-radius: 11px; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);">
                <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
            </div>
            <div>
                <div style="font-size: 20px; font-weight: 800; letter-spacing: -0.025em; color: {text_primary}; line-height: 1.15;">Smart Bill Segregator</div>
                <div style="font-size: 11.5px; font-weight: 500; color: {text_secondary}; margin-top: 2px;">
                    {vault_status_text} &nbsp;·&nbsp; Kayalvizhi: {ky_active} Shifts / {ky_off} Off &nbsp;·&nbsp; Shafana: ₹{sf_bill_due:,.0f} Due (₹{sf_net_kitty:,.0f} CB) &nbsp;·&nbsp; <span style="font-family: monospace;">#{html_lib.escape(git_info['hash'])}</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with hdr_col2:
    theme_btn_label = "Light Mode" if is_dark else "Dark Mode"
    if st.button(theme_btn_label, use_container_width=True, type="secondary", key="btn_toggle_ui_theme"):
        st.session_state.ui_theme = "light" if is_dark else "dark"
        st.rerun()

# --- Single Segmented Top Navigation Bar (5 Clean Tabs) ---
nav_cols = st.columns(5)
nav_items = [
    ("statements", "Statements & EMIs"),
    ("kayal", f"Dr. Kayalvizhi ({ky_active})"),
    ("shafana", f"Shafana (₹{sf_bill_due:,.0f})"),
    ("ai", "Ask Gemini AI"),
    ("settings", f"Vault & Settings ({len(active_vault_list)})")
]
for idx, (nav_key, nav_label) in enumerate(nav_items):
    is_curr = (st.session_state.active_nav == nav_key)
    if nav_cols[idx].button(
        nav_label,
        use_container_width=True,
        type="primary" if is_curr else "secondary",
        key=f"top_seg_nav_{nav_key}"
    ):
        st.session_state.active_nav = nav_key
        if nav_key == "kayal":
            st.session_state.show_kayal_roster = True
            st.session_state.show_shafana_tracker = False
            st.session_state.active_special_view = "kayal"
        elif nav_key == "shafana":
            st.session_state.show_shafana_tracker = True
            st.session_state.show_kayal_roster = False
            st.session_state.active_special_view = "shafana"
        elif nav_key == "statements":
            st.session_state.show_kayal_roster = False
            st.session_state.show_shafana_tracker = False
            st.session_state.active_special_view = None
        elif nav_key == "ai":
            st.session_state.show_ai_chat = True
        st.rerun()

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# --- Compact File Uploader (Visible on Statements, Dr. Kayalvizhi, and Shafana views) ---
if st.session_state.active_nav in ("statements", "kayal", "shafana"):
    uploaded_files = st.file_uploader(
        "Drop Statement PDFs, Fold / Shafana Screenshots, or Dr. Kayalvizhi Duty Roster Photo (Processed strictly in RAM)",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="main_file_uploader"
    )
else:
    uploaded_files = None

# --- Process Uploaded Files Strictly in RAM (Zero Disk Writes!) ---
st.session_state.statements_data = {}
if uploaded_files:
    pdf_files = [f for f in uploaded_files if f.name.lower().endswith(".pdf")]
    img_files = [f for f in uploaded_files if not f.name.lower().endswith(".pdf")]

    if img_files:
        roster_imgs = []
        fold_imgs = []
        shafana_imgs = []
        for f in img_files:
            raw_b = f.getvalue()
            if st.session_state.show_kayal_roster or unlock_statements.is_duty_roster_image(raw_b, f.name):
                roster_imgs.append({"name": f.name, "bytes": raw_b})
            elif unlock_statements.is_fold_screenshot(raw_b, f.name):
                fold_imgs.append({"name": f.name, "bytes": raw_b})
            else:
                shafana_imgs.append({"name": f.name, "bytes": raw_b})

        if fold_imgs:
            fl_ok, fl_msg, fl_res = unlock_statements.process_fold_screenshots(fold_imgs)
            if fl_ok and fl_res:
                sync_bill_names_to_github(commit_msg="Auto-sync Fold transaction tag")
                ext_list = fl_res.get("extracted", [])
                for ex in ext_list:
                    st.success(
                        f"🏷️ Fold Tag Saved for Next Statement: Card **{ex.get('card_last4') or 'Card'} • "
                        f"₹{ex.get('amount', 0):,.0f} • {ex.get('date')} • Paid To: {ex.get('paid_to')} • "
                        f"Auto-Name: '{ex.get('note')}'"
                    )
                if fl_res.get("shafana_data"):
                    update_shared_shafana_store(unlock_statements.load_shafana_web_ledger())
                    st.session_state.statements_data["Shafana_Cashback"] = fl_res["shafana_data"]

        if roster_imgs:
            ky_ok, ky_msg, ky_data = unlock_statements.process_kayal_duty_roster(roster_imgs)
            if ky_ok and ky_data:
                update_shared_kayal_store(unlock_statements.load_kayal_web_roster())
                st.session_state.statements_data["Kayal_Duty_Roster"] = ky_data
                st.session_state.active_special_view = "kayal"
                km = ky_data.get("kayal_meta", {})
                ist_greet, ist_now_str = get_ist_kayal_greeting()
                st.toast(f"{ist_greet} ({ist_now_str}) — With Love, Saro 💖", icon="💖")
                st.success(
                    f"{ist_greet} • Loaded at {ist_now_str} — "
                    f"{km.get('active_count', 0)} Active Shifts & {km.get('off_count', 0)} Off Days Together! "
                    f"Tap '📲 Share Screenshot on WhatsApp' below — With Love, Saro 💖"
                )

        if shafana_imgs:
            sf_ok, sf_msg, sf_data = unlock_statements.process_shafana_screenshots(shafana_imgs)
            if sf_ok and sf_data:
                update_shared_shafana_store(unlock_statements.load_shafana_web_ledger())
                st.session_state.statements_data["Shafana_Cashback"] = sf_data
                sm = sf_data.get("shafana_meta", {})
                st.success(
                    f"🎁 Shafana Amazon Cashback Screenshot(s) Loaded ({len(shafana_imgs)} file(s)) — "
                    f"Full Bill to Collect: ₹{sm.get('bill_due_total', 0):,.2f} • "
                    f"Cashback Earned: +₹{sm.get('cb_earned_total', 0):,.2f}"
                )

    for up_file in pdf_files:
        pdf_bytes_io = io.BytesIO(up_file.getvalue())
        
        success, msg, rdata = unlock_statements.process_statement_file(
            up_file.name,
            base_downloads_dir=".",
            custom_passwords=st.session_state.session_passwords,
            file_obj=pdf_bytes_io,
            save_to_disk=False,
            custom_emi_names=st.session_state.emi_nicknames
        )
        if success and rdata:
            if (
                rdata.get("bank_short") not in ("Scapia Axis", "SBI SimplyCLICK", "ICICI Amazon", "HDFC", "Salary Payslip", "EMI Amortization")
                or rdata.get("bank_name") == "Bank Statement"
                or not rdata.get("date_groups")
                or not rdata.get("all_txns")
            ):
                success = False
                msg = f"Non-Bill / Non-Transactional PDF Detected ({up_file.name}): 0 bill transactions found. Please upload a valid Axis Bank (Scapia), HDFC, ICICI, SBI credit card statement, or Salary Payslip."
                rdata = None

        if success and rdata:
            slot_key = f"{rdata['bank_short']}_{rdata.get('statement_month', up_file.name)}"
            if rdata.get("bank_short") == "EMI Amortization":
                sync_bill_names_to_github(commit_msg="Auto-sync SmartEMI Amortization plan")
                am = rdata.get("emi_amort_meta", {})
                lid = am.get("loan_id", "")
                pname = am.get("plan_name", up_file.name)
                st.success(
                    f"💾 Saved SmartEMI Amortization Plan for Future Splits (Not Opened as a Current Bill): "
                    f"Loan #{lid} ({pname}) • ₹{am.get('amount', 0):,.2f} • "
                    f"{am.get('tenure_months', 0)} Months ({am.get('interest_rate', '')}) • "
                    f"Fee ₹{am.get('processing_fee', 0):,.0f}"
                )
                with st.form(key=f"rename_amort_{lid}_{up_file.name}"):
                    rn_col1, rn_col2 = st.columns([3, 1])
                    with rn_col1:
                        new_loan_name = st.text_input(
                            "🏷️ Name this EMI Loan for future monthly statements:",
                            value=st.session_state.emi_nicknames.get(lid, pname),
                            placeholder="e.g. Galaxy watch 8 classic Saravana",
                            key=f"inp_amort_name_{lid}_{up_file.name}"
                        )
                    with rn_col2:
                        st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
                        if st.form_submit_button("💾 Save Loan Name", use_container_width=True):
                            if new_loan_name.strip() and lid:
                                clean_n = new_loan_name.strip()
                                st.session_state.emi_nicknames[lid] = clean_n
                                meta_bn = unlock_statements.load_bill_names_web()
                                meta_bn.setdefault("bill_names", {})[lid] = clean_n
                                for ep in meta_bn.get("emi_plans", []):
                                    if ep.get("loan_id") == lid:
                                        ep["plan_name"] = clean_n
                                unlock_statements.save_bill_names_web(meta_bn)
                                sync_bill_names_to_github(meta_bn, commit_msg=f"Rename Loan #{lid}")
                                st.session_state["pending_save_emi_vault"] = {
                                    "names": dict(st.session_state.emi_nicknames),
                                    "phones": dict(st.session_state.emi_phones)
                                }
                                st.success(f"🏷️ Saved Loan #{lid} as '{clean_n}' for future splits!")
            else:
                st.session_state.statements_data[slot_key] = rdata
                _save_statement_summary_to_bill_names(slot_key, rdata)
                if rdata.get("payslip_meta", {}).get("is_payslip"):
                    pm = rdata["payslip_meta"]
                    st.success(f"Salary Payslip Loaded: {up_file.name} ({pm.get('pay_period')}) — Net Pay {pm.get('net_pay')} • Full 30-Day Rate: ₹{pm.get('full_month_gross', 0):,.2f}/mo (₹{pm.get('per_day_rate', 0):,.2f}/day)")
                else:
                    st.success(f"Unlocked in memory: {up_file.name} ({rdata.get('bank_name')}) — {len(rdata.get('date_groups', {}))} date groups found")
            if rdata.get("unlocked_pdf_b64"):
                try:
                    _pdf_raw = base64.b64decode(rdata["unlocked_pdf_b64"])
                    st.download_button(
                        label=f"Download Unlocked PDF ({up_file.name})",
                        data=_pdf_raw,
                        file_name=f"Unlocked_{up_file.name}",
                        mime="application/pdf",
                        key=f"dl_unlocked_{slot_key}_{up_file.name}",
                        use_container_width=True
                    )
                except Exception:
                    pass
        else:
            st.error(f"⚠️ {up_file.name}: {msg}")
            if "password" in msg.lower():
                with st.form(key=f"pwd_unlock_{up_file.name}"):
                    fname_low = up_file.name.lower()
                    if "scapia" in fname_low or "axis" in fname_low or "federal" in fname_low: def_idx = 0
                    elif "5268" in fname_low or "hdfc" in fname_low or "swiggy" in fname_low: def_idx = 1
                    elif "4315" in fname_low or "icici" in fname_low or "amazon" in fname_low: def_idx = 2
                    elif "payslip" in fname_low or "skillveri" in fname_low or "salary" in fname_low or "tds" in fname_low: def_idx = 4
                    else: def_idx = 3

                    st.markdown(f"**Unlock `{up_file.name}`:**")
                    selected_bank = st.radio(
                        "Statement / Payslip Format:",
                        ["Axis Bank (Scapia)", "HDFC Bank (Swiggy)", "ICICI Bank (Amazon Pay)", "SBI Card (SimplyCLICK)", "Salary Payslip (Skillveri)", "EMI Amortization (SmartEMI)"],
                        index=def_idx,
                        horizontal=True,
                        key=f"bank_choice_{up_file.name}"
                    )
                    if "Amortization" in selected_bank or "SmartEMI" in selected_bank:
                        hint_desc = "First 4 letters of Name in CAPITAL + Last 4 digits of Card (e.g. SARA8844)"
                        bank_key = "emi_amort"
                    elif "Payslip" in selected_bank or "Skillveri" in selected_bank:
                        hint_desc = "Employee No + PAN [last 4 digits] (e.g. 115000A or 1234000A)"
                        bank_key = "payslip"
                    elif "Scapia" in selected_bank or "Axis" in selected_bank:
                        hint_desc = "First 4 letters of name in UPPERCASE + DDMM (e.g. ROHI2512)"
                        bank_key = "scapia"
                    elif "SBI" in selected_bank:
                        hint_desc = "Date of Birth in DDMMYYYY + Last 4 digits of card (e.g. 150819954321)"
                        bank_key = "sbi"
                    elif "HDFC" in selected_bank:
                        hint_desc = "First 4 letters of name in UPPERCASE + DDMM (e.g. ROHI2512)"
                        bank_key = "hdfc"
                    else:
                        hint_desc = "First 4 letters of name in lowercase + DDMM (e.g. rohi2512)"
                        bank_key = "icici"

                    st.caption(f"🔑 Password pattern: **{hint_desc}**")
                    inline_pwd = st.text_input(f"Enter {selected_bank} password:", type="password", key=f"inp_{up_file.name}")
                    if st.form_submit_button("Unlock & Save to Device Vault", use_container_width=True):
                        if inline_pwd.strip():
                            st.session_state.session_passwords[bank_key] = inline_pwd.strip()
                            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
                            st.session_state["sidebar_toast_until"] = time.time() + 5.0
                            st.session_state["sidebar_toast_notice"] = {
                                "type": "success",
                                "title": f"Password Saved for {selected_bank}",
                                "desc": "Stored in browser vault for this device."
                            }
                            st.rerun()

# Keep special views synchronized with active_nav
has_icici_loaded = any("icici" in k.lower() for k in st.session_state.statements_data.keys())
if (st.session_state.active_nav == "kayal" or st.session_state.show_kayal_roster) and "Kayal_Duty_Roster" not in st.session_state.statements_data:
    st.session_state.statements_data["Kayal_Duty_Roster"] = unlock_statements.build_kayal_statement_from_roster(get_shared_kayal_store())
if (st.session_state.active_nav == "shafana" or st.session_state.show_shafana_tracker or has_icici_loaded) and "Shafana_Cashback" not in st.session_state.statements_data:
    st.session_state.statements_data["Shafana_Cashback"] = unlock_statements.build_shafana_statement_from_ledger(get_shared_shafana_store())

# ==============================================================================
# VIEW 1: ASK GEMINI AI ASSISTANT
# ==============================================================================
if st.session_state.active_nav == "ai":
    st.markdown(f"""
    <div style="background: {bg_surface}; border: 1px solid {border_subtle}; border-radius: 18px; padding: 18px 20px; margin-bottom: 14px; backdrop-filter: blur(20px) saturate(180%);">
        <div style="font-size: 16px; font-weight: 700; letter-spacing: -0.02em; color: {text_primary};">Gemini AI Assistant</div>
        <div style="font-size: 12.5px; color: {text_secondary}; margin-top: 2px;">Connected to Dr. Kayalvizhi's full CHC Thirunallar roster &amp; relief combinations, ICICI/HDFC paid &amp; unpaid bill cards, ongoing EMIs, and Shafana's cashback ledger.</div>
    </div>
    """, unsafe_allow_html=True)

    gemini_key = _get_gemini_api_key()
    if not gemini_key:
        st.info("Add your Gemini API Key in Streamlit Cloud Secrets (`GEMINI_API_KEY`) or open the **Vault & Settings** tab above.")
    else:
        q_cols = st.columns([1.2, 1.2, 1.1, 0.7])
        quick_prompt = None
        if q_cols[0].button("Kayalvizhi's relief combos & next off", use_container_width=True, key="ai_q1"):
            quick_prompt = "Which doctor relieves Dr. Kayalvizhi the most, what is her highest doctor combo, and when is her next off day?"
        if q_cols[1].button("Unpaid ICICI & HDFC bills", use_container_width=True, key="ai_q2"):
            quick_prompt = "Which bills and EMIs are unpaid in ICICI Amazon and HDFC, and what are their amounts?"
        if q_cols[2].button("Shafana cashback summary", use_container_width=True, key="ai_q3"):
            quick_prompt = "What is Shafana's total bill due and remaining cashback balance?"
        if q_cols[3].button("🗑️ Clear Chatbot", use_container_width=True, type="secondary", key="ai_clr"):
            st.session_state.ai_chat_history = []
            st.rerun()

        for msg in st.session_state.ai_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        typed_prompt = st.chat_input("Ask about Kayalvizhi's duty combos, unpaid ICICI/HDFC bills, EMIs, or Shafana's cashback...", key="gemini_chat_inp")
        final_prompt = quick_prompt or typed_prompt
        if final_prompt:
            st.session_state.ai_chat_history.append({"role": "user", "content": final_prompt})
            with st.spinner("Analyzing ledger & roster context..."):
                ok_ai, ans_ai = _ask_gemini_api(final_prompt, gemini_key)
            reply_txt = ans_ai if ok_ai else f"Gemini API Error: {ans_ai}"
            st.session_state.ai_chat_history.append({"role": "assistant", "content": reply_txt})
            st.rerun()

# ==============================================================================
# VIEW 2: VAULT & SETTINGS (IN-PAGE DRAWER REPLACING BULKY LEFT SIDEBAR)
# ==============================================================================
elif st.session_state.active_nav == "settings":
    set_col1, set_col2 = st.columns(2)
    with set_col1:
        st.markdown(f"""
        <div style="background: {bg_surface}; border: 1px solid {border_subtle}; border-radius: 16px; padding: 16px 18px; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: 700; color: {text_primary}; letter-spacing: -0.015em;">Device Password Vault</div>
            <div style="font-size: 12px; color: {text_secondary}; margin-top: 2px;">Stored strictly in your browser's localStorage on this device. Never transmitted to or stored on any server disk.</div>
        </div>
        """, unsafe_allow_html=True)

        scapia_val = st.text_input("Axis Bank (Scapia) Password", value=st.session_state.session_passwords.get("scapia", ""), type="password", help="UPPERCASE name (4) + DDMM", key="input_scapia_pwd")
        hdfc_val = st.text_input("HDFC Bank Password", value=st.session_state.session_passwords.get("hdfc", ""), type="password", help="UPPERCASE name (4) + DDMM or Name(4)+CardLast4 for SmartEMI", key="input_hdfc_pwd")
        icici_val = st.text_input("ICICI Bank Password", value=st.session_state.session_passwords.get("icici", ""), type="password", help="Lowercase name (4) + DDMM", key="input_icici_pwd")
        sbi_val = st.text_input("SBI SimplyCLICK Password", value=st.session_state.session_passwords.get("sbi", ""), type="password", help="DDMMYYYY + Last 4 digits of card", key="input_sbi_pwd")
        payslip_val = st.text_input("Salary Payslip Password", value=st.session_state.session_passwords.get("payslip", ""), type="password", help="Employee No + PAN last 4 digits (e.g. 115000A)", key="input_payslip_pwd")

        v_b1, v_b2 = st.columns(2)
        if v_b1.button("Save Vault on This Device", use_container_width=True, type="primary", key="btn_save_vault_main"):
            st.session_state.session_passwords["scapia"] = scapia_val.strip()
            st.session_state.session_passwords["hdfc"] = hdfc_val.strip()
            st.session_state.session_passwords["icici"] = icici_val.strip()
            st.session_state.session_passwords["sbi"] = sbi_val.strip()
            st.session_state.session_passwords["payslip"] = payslip_val.strip()
            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
            st.success("Passwords saved to browser localStorage on this device.")
            st.rerun()
        if v_b2.button("Clear Saved Passwords", use_container_width=True, type="secondary", key="btn_forget_vault_main"):
            forget_browser_passwords()
            st.rerun()

    with set_col2:
        st.markdown(f"""
        <div style="background: {bg_surface}; border: 1px solid {border_subtle}; border-radius: 16px; padding: 16px 18px; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: 700; color: {text_primary}; letter-spacing: -0.015em;">EMI Nicknames &amp; Cloud Sync</div>
            <div style="font-size: 12px; color: {text_secondary}; margin-top: 2px;">Assign friend names &amp; WhatsApp numbers to EMI loans, or configure Google Sheets &amp; Gemini API keys.</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.emi_nicknames:
            for lid, lname in list(st.session_state.emi_nicknames.items()):
                lphone = st.session_state.emi_phones.get(lid) or st.session_state.emi_phones.get(lname, "")
                phone_badge = f" · +{lphone}" if lphone else ""
                st.markdown(
                    f"<div style='background:{bg_elevated};border:1px solid {border_subtle};border-radius:10px;padding:8px 12px;margin-bottom:6px;font-size:12px;color:{text_primary};display:flex;justify-content:space-between;'>"
                    f"<b>{html_lib.escape(lname)}</b> <span style='font-family:monospace;color:{text_secondary};'>{html_lib.escape(lid)}{html_lib.escape(phone_badge)}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        emi_loan_key = st.text_input("Loan ID / EMI Key", placeholder="e.g. 146608745 or 28/09/2026_44370.00", key="side_emi_key")
        emi_friend_name = st.text_input("Friend / Item Nickname", placeholder="e.g. Naveen S25 Edge", key="side_emi_name")
        emi_friend_phone = st.text_input("Friend WhatsApp No. (Optional)", placeholder="10-digit mobile", key="side_emi_phone")
        e_b1, e_b2 = st.columns(2)
        if e_b1.button("Save EMI Nickname", use_container_width=True, type="primary", key="btn_save_emi_side"):
            if emi_loan_key.strip() and emi_friend_name.strip():
                k_clean = emi_loan_key.strip()
                n_clean = emi_friend_name.strip()
                p_digits = "".join(ch for ch in emi_friend_phone.strip() if ch.isdigit())
                if len(p_digits) == 10:
                    p_digits = "91" + p_digits
                st.session_state.emi_nicknames[k_clean] = n_clean
                if p_digits:
                    st.session_state.emi_phones[k_clean] = p_digits
                    st.session_state.emi_phones[n_clean] = p_digits
                st.session_state["pending_save_emi_vault"] = {
                    "names": dict(st.session_state.emi_nicknames),
                    "phones": dict(st.session_state.emi_phones)
                }
                meta_bn = unlock_statements.load_bill_names_web()
                meta_bn.setdefault("bill_names", {})[k_clean] = n_clean
                unlock_statements.save_bill_names_web(meta_bn)
                sync_bill_names_to_github(meta_bn, commit_msg=f"Save EMI nickname {n_clean}")
                st.rerun()
        if e_b2.button("Clear EMI Nicknames", use_container_width=True, type="secondary", key="btn_clear_emi_side"):
            st.session_state.emi_nicknames = {}
            st.session_state.emi_phones = {}
            st.session_state["pending_clear_emi_vault"] = True
            st.session_state["emi_vault_cleared_until"] = time.time() + 4.0
            st.rerun()

        webhook_val = st.text_input("Google Sheets Web App URL", value=st.session_state.session_passwords.get("sheets_webhook_url", ""), key="input_webhook_url")
        gemini_key_val = st.text_input("Gemini API Key (Optional if set in Streamlit Secrets)", value=st.session_state.session_passwords.get("gemini_api_key", ""), type="password", key="input_gemini_api_key")
        c_b1, c_b2 = st.columns(2)
        if c_b1.button("Save Integration Keys", use_container_width=True, type="secondary", key="btn_save_integrations"):
            st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
            st.session_state.session_passwords["gemini_api_key"] = gemini_key_val.strip()
            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
            st.success("Integration settings saved.")
            st.rerun()
        with c_b2:
            st.link_button("Google Sheet Template", unlock_statements.GOOGLE_SHEET_TEMPLATE_URL, use_container_width=True)

# ==============================================================================
# VIEW 3: SHAFANA CASHBACK QUICK CONTROLS + DASHBOARD
# ==============================================================================
elif st.session_state.active_nav == "shafana":
    sf_col1, sf_col2, sf_col3, sf_col4 = st.columns([1.4, 1, 1.4, 1])
    with sf_col1:
        new_cb_used = st.number_input("Cashback Used by Shafana (₹)", min_value=0.0, value=float(sf_cb_used), step=10.0, key="side_sf_cb_used")
    with sf_col2:
        st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
        if st.button("Update Cashback Used", use_container_width=True, type="primary", key="side_save_cb_used"):
            shared_sf["manualCbUsed"] = float(new_cb_used)
            update_shared_shafana_store(shared_sf)
            st.session_state.statements_data["Shafana_Cashback"] = unlock_statements.build_shafana_statement_from_ledger(get_shared_shafana_store())
            st.rerun()
    with sf_col3:
        q_sf_amt = st.number_input("Add New Order Bill Amount (₹)", min_value=0.0, step=50.0, key="side_sf_amt")
    with sf_col4:
        st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
        if st.button("Add Order (+5% CB)", use_container_width=True, type="secondary", key="side_add_sf_entry"):
            if q_sf_amt > 0:
                import math as _math
                ist_now = datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).strftime("%d %b %Y")
                cb_calc = float(_math.floor(q_sf_amt * 0.05))
                shared_sf.setdefault("entries", []).insert(0, {
                    "id": f"ord_{int(time.time())}_{q_sf_amt:.2f}",
                    "method": "Amazon Pay Credit Card",
                    "description": "Amazon Order — Delivering to Raja Mohamed",
                    "amount": float(q_sf_amt),
                    "cashback_earned": cb_calc,
                    "date_time": ist_now,
                    "role": "shafana_order",
                    "recipient": "Raja Mohamed",
                    "address": "8 Puduthurai Main Road, Karaikal 609602",
                    "arriving_by": "",
                    "source_file": "Manual Entry"
                })
                update_shared_shafana_store(shared_sf)
                st.session_state.statements_data["Shafana_Cashback"] = unlock_statements.build_shafana_statement_from_ledger(get_shared_shafana_store())
                st.rerun()

# --- Active Statements Action Bar (When Statements Are Loaded) ---
if st.session_state.active_nav in ("statements", "kayal", "shafana") and st.session_state.statements_data:
    real_stmts = [k for k, s in st.session_state.statements_data.items() if not (s.get("shafana_meta") or {}).get("is_shafana") and not (s.get("kayal_meta") or {}).get("is_kayal")]
    if real_stmts or st.session_state.active_nav == "statements":
        status_cols = st.columns([3.4, 1.2, 0.9, 0.9])
        with status_cols[0]:
            badge_html = " ".join([
                f'<span style="background: {bg_surface}; color: {text_primary}; padding: 4px 11px; border-radius: 8px; font-size: 11.5px; font-weight: 600; border: 1px solid {border_subtle}; margin-right: 6px;">{s.get("bank_name", k)} ({len(s.get("date_groups", {}))})</span>'
                for k, s in st.session_state.statements_data.items()
            ])
            st.markdown(f"<div style='margin: 6px 0 10px 0; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'><span style='font-size: 11px; font-weight: 700; color: {text_secondary}; text-transform: uppercase; letter-spacing: 0.05em;'>Loaded:</span> {badge_html}</div>", unsafe_allow_html=True)
        with status_cols[1]:
            if st.button("Push to Sheets", use_container_width=True, type="primary", help="Sync loaded bills & friend EMIs to Google Sheets"):
                webhook_url = st.session_state.session_passwords.get("sheets_webhook_url", "").strip()
                if not webhook_url:
                    st.warning("Configure your Google Sheets Web App URL in the Vault & Settings tab first.")
                else:
                    import urllib.request
                    bills, reimbursements = [], []
                    seen_loan_ids = set()
                    for k_st, rdata in st.session_state.statements_data.items():
                        if (rdata.get("shafana_meta") or {}).get("is_shafana") or (rdata.get("kayal_meta") or {}).get("is_kayal"):
                            continue
                        emis = rdata.get("ongoing_emis", [])
                        bills.append({
                            "month": rdata.get("statement_month", ""),
                            "bank": rdata.get("bank_short", ""),
                            "total_due": rdata.get("total_due", ""),
                            "due_date": rdata.get("due_date", ""),
                            "cashback_summary": rdata.get("reward_points", ""),
                            "notes": f"{len(emis)} ongoing EMI(s) tracked"
                        })
                        for emi in emis:
                            lid = str(emi.get("loan_id", ""))
                            if lid:
                                seen_loan_ids.add(lid)
                            ename = st.session_state.emi_nicknames.get(lid) or emi.get("custom_name") or lid
                            reimbursements.append({
                                "month": rdata.get("statement_month", ""),
                                "bank": rdata.get("bank_short", ""),
                                "loan_id": lid,
                                "friend_name": ename,
                                "amount": emi.get("total_amount", ""),
                                "remaining": emi.get("balance_tenure", "-"),
                                "status": "Pending"
                            })
                    for ep in (unlock_statements.load_bill_names_web().get("emi_plans") or []):
                        lid = str(ep.get("loan_id", ""))
                        if lid and lid not in seen_loan_ids:
                            seen_loan_ids.add(lid)
                            pname = st.session_state.emi_nicknames.get(lid) or ep.get("plan_name") or lid
                            sched = ep.get("schedule") or []
                            start_dt = sched[0].get("date", "Upcoming") if sched else "Upcoming"
                            reimbursements.append({
                                "month": start_dt,
                                "bank": ep.get("bank", "HDFC"),
                                "loan_id": lid,
                                "friend_name": pname,
                                "amount": f"₹{float(ep.get('amount', 0)):,.2f}",
                                "remaining": f"{ep.get('tenure_months', len(sched))} Months",
                                "status": "Saved Plan"
                            })
                    try:
                        req = urllib.request.Request(
                            webhook_url,
                            data=json.dumps({"bills": bills, "reimbursements": reimbursements}).encode("utf-8"),
                            headers={"Content-Type": "application/json", "User-Agent": "SmartBillSegregator/1.0"}
                        )
                        with urllib.request.urlopen(req, timeout=12) as resp:
                            st.success(f"Synced {len(bills)} bill(s) & {len(reimbursements)} EMI(s) to Google Sheets.")
                    except Exception as ex_sh:
                        st.error(f"Google Sheets sync failed: {ex_sh}")
        with status_cols[2]:
            if st.button("Refresh", use_container_width=True):
                st.rerun()
        with status_cols[3]:
            if st.button("Clear", use_container_width=True):
                st.session_state.statements_data = {}
                st.session_state.show_shafana_tracker = False
                st.session_state.show_kayal_roster = False
                st.session_state.active_nav = "statements"
                st.rerun()

# --- Sleek Apple / Fintech Empty-State Showcase (Adaptive Dark & Light Mode) ---
def get_card_shuffle_html(dark_mode=True):
    scapia_orange_b64 = unlock_statements.get_card_b64("card-facia-scapia-orange.png")
    scapia_green_b64 = unlock_statements.get_card_b64("card-facia-scapia-green.png")
    swiggy_b64 = unlock_statements.get_card_b64("card-facia-swiggy.jpg")
    amazon_b64 = unlock_statements.get_card_b64("card-facia-amazon.png")
    sbi_b64 = unlock_statements.get_card_b64("simply-click-card-face.png")

    body_bg = "#090d16" if dark_mode else "#f8fafc"
    card_bg = "#111827" if dark_mode else "#ffffff"
    card_border = "#1e293b" if dark_mode else "#e2e8f0"
    sec_bg = "#0f172a" if dark_mode else "#f8fafc"
    t_prim = "#f8fafc" if dark_mode else "#0f172a"
    t_sec = "#94a3b8" if dark_mode else "#475569"
    pill_bg = "#1e293b" if dark_mode else "#f1f5f9"
    pill_border = "#334155" if dark_mode else "#cbd5e1"
    pill_txt = "#f8fafc" if dark_mode else "#0f172a"
    scheme = "dark" if dark_mode else "light"

    return f"""<!-- theme:{scheme} --><!DOCTYPE html>
<html lang="en" style="color-scheme: {scheme};">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
    body {{ background: {body_bg}; color: {t_prim}; display: flex; justify-content: center; align-items: flex-start; padding: 4px 2px 12px 2px; overflow-x: hidden; }}
    .showcase-card {{
      width: 100%;
      max-width: 1180px;
      background: {card_bg};
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid {card_border};
      border-radius: 22px;
      padding: 24px 22px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 0 auto;
    }}
    .headline-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 13px;
      border-radius: 9999px;
      background: {pill_bg};
      border: 1px solid {pill_border};
      color: {pill_txt};
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 10px;
    }}
    .title {{
      font-size: 19px;
      font-weight: 700;
      color: {t_prim};
      letter-spacing: -0.025em;
      margin-bottom: 5px;
    }}
    .subtitle {{
      font-size: 12.5px;
      color: {t_sec};
      max-width: 640px;
      line-height: 1.5;
      margin-bottom: 18px;
      font-weight: 400;
    }}
    .dual-grid {{
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 16px;
      width: 100%;
      align-items: stretch;
      margin-bottom: 14px;
    }}
    .deck-section {{
      background: {sec_bg};
      border: 1px solid {card_border};
      border-radius: 18px;
      padding: 16px 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
    }}
    .section-header-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: {pill_bg};
      border: 1px solid {pill_border};
      color: {pill_txt};
      margin-bottom: 8px;
    }}
    .travel-stage {{
      perspective: 1200px;
      width: 100%;
      max-width: 240px;
      height: 250px;
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
    }}
    .card-p {{
      width: 156px;
      height: 244px;
      border-radius: 14px;
      position: absolute;
      box-shadow: 0 18px 36px -10px rgba(0, 0, 0, 0.35);
      background-size: cover !important;
      background-position: center !important;
    }}
    #card-p1 {{ background-image: url('{scapia_orange_b64}'); animation: shufflePortOrange 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    #card-p2 {{ background-image: url('{scapia_green_b64}'); animation: shufflePortGreen 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    @keyframes shufflePortOrange {{
      0%, 42% {{ transform: translate3d(-6px, 0, 32px) scale(1); z-index: 25; opacity: 1; }}
      50%, 92% {{ transform: translate3d(24px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.82; }}
      100% {{ transform: translate3d(-6px, 0, 32px) scale(1); z-index: 25; opacity: 1; }}
    }}
    @keyframes shufflePortGreen {{
      0%, 42% {{ transform: translate3d(24px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.82; }}
      50%, 92% {{ transform: translate3d(-6px, 0, 32px) scale(1); z-index: 25; opacity: 1; }}
      100% {{ transform: translate3d(24px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.82; }}
    }}
    .rewards-stage {{
      perspective: 1200px;
      width: 100%;
      max-width: 310px;
      height: 250px;
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
    }}
    .card-l {{
      width: 245px;
      height: 154px;
      border-radius: 13px;
      position: absolute;
      box-shadow: 0 18px 36px -10px rgba(0, 0, 0, 0.32);
      background-size: cover !important;
      background-position: center !important;
    }}
    #card-l1 {{ background-image: url('{swiggy_b64}'); animation: shuffleLand1 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    #card-l2 {{ background-image: url('{amazon_b64}'); animation: shuffleLand2 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    #card-l3 {{ background-image: url('{sbi_b64}'); animation: shuffleLand3 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    @keyframes shuffleLand1 {{
      0%, 28% {{ transform: translate3d(0, 4px, 35px) scale(1); z-index: 30; opacity: 1; }}
      33%, 61% {{ transform: translate3d(28px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.86; }}
      66%, 95% {{ transform: translate3d(-26px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.7; }}
      100% {{ transform: translate3d(0, 4px, 35px) scale(1); z-index: 30; opacity: 1; }}
    }}
    @keyframes shuffleLand2 {{
      0%, 28% {{ transform: translate3d(28px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.86; }}
      33%, 61% {{ transform: translate3d(-26px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.7; }}
      66%, 95% {{ transform: translate3d(0, 4px, 35px) scale(1); z-index: 30; opacity: 1; }}
      100% {{ transform: translate3d(28px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.86; }}
    }}
    @keyframes shuffleLand3 {{
      0%, 28% {{ transform: translate3d(-26px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.7; }}
      33%, 61% {{ transform: translate3d(0, 4px, 35px) scale(1); z-index: 30; opacity: 1; }}
      66%, 95% {{ transform: translate3d(28px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.86; }}
      100% {{ transform: translate3d(-26px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.7; }}
    }}
    .mini-badges {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 8px; }}
    .mini-badge {{
      font-size: 10.5px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 8px;
      background: {pill_bg};
      border: 1px solid {pill_border};
      color: {pill_txt};
    }}
    .security-note {{
      font-size: 11.5px;
      font-weight: 500;
      color: {t_sec};
      padding: 8px 16px;
      border-radius: 9999px;
      background: {sec_bg};
      border: 1px solid {card_border};
      margin-top: 4px;
    }}
    @media (max-width: 859px) {{
      .dual-grid {{ display: flex; flex-direction: column; gap: 14px; }}
      .travel-stage {{ height: 220px; }}
      .card-p {{ width: 138px; height: 214px; }}
      .rewards-stage {{ height: 170px; }}
      .card-l {{ width: 215px; height: 135px; }}
    }}
  </style>
</head>
<body>
  <div class="showcase-card" id="main-showcase-card">
    <div class="headline-pill">Supported Instruments</div>
    <h2 class="title">Ready for Statement Decryption &amp; EMI Audit</h2>
    <p class="subtitle">
      Drop your <b>Axis Bank Scapia</b>, <b>HDFC Swiggy</b>, <b>ICICI Amazon Pay</b>, <b>SBI SimplyCLICK</b>, <b>SmartEMI Schedule</b>, or <b>Duty Roster</b> above to segregate installments and track date-wise payments.
    </p>
    <div class="dual-grid">
      <div class="deck-section">
        <span class="section-header-pill">Axis Bank Scapia</span>
        <div class="travel-stage">
          <div id="card-p1" class="card-p"></div>
          <div id="card-p2" class="card-p"></div>
        </div>
        <div class="mini-badges">
          <span class="mini-badge">Scapia Mastercard</span>
          <span class="mini-badge">Scapia RuPay</span>
        </div>
      </div>
      <div class="deck-section">
        <span class="section-header-pill">Cashback &amp; Rewards</span>
        <div class="rewards-stage">
          <div id="card-l1" class="card-l"></div>
          <div id="card-l2" class="card-l"></div>
          <div id="card-l3" class="card-l"></div>
        </div>
        <div class="mini-badges">
          <span class="mini-badge">Swiggy HDFC</span>
          <span class="mini-badge">Amazon Pay ICICI</span>
          <span class="mini-badge">SBI SimplyCLICK</span>
        </div>
      </div>
    </div>
    <div class="security-note">
      🔒 Zero-Disk Architecture · Statements are decrypted strictly in volatile RAM and never stored on server storage.
    </div>
    <div style="margin-top: 10px; font-size: 12.5px; font-weight: 600; color: {t_sec};">
      Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
    </div>
  </div>
  <script>
    function syncShowcaseHeight() {{
      const card = document.getElementById('main-showcase-card');
      if (!card) return;
      const h = Math.ceil(card.getBoundingClientRect().height) + 28;
      try {{
        if (window.frameElement) {{
          window.frameElement.style.height = h + 'px';
          window.frameElement.height = String(h);
        }}
      }} catch (e) {{}}
    }}
    window.addEventListener('load', syncShowcaseHeight);
    window.addEventListener('resize', syncShowcaseHeight);
    setTimeout(syncShowcaseHeight, 100);
    setTimeout(syncShowcaseHeight, 400);
  </script>
</body>
</html>"""

# --- Render Main View Content ---
if st.session_state.active_nav in ("statements", "kayal", "shafana"):
    if st.session_state.statements_data:
        ordered_items = list(st.session_state.statements_data.items())
        if st.session_state.active_nav == "kayal" or st.session_state.get("active_special_view") == "kayal":
            ordered_items.sort(key=lambda kv: 0 if kv[0] == "Kayal_Duty_Roster" else 1)
        elif st.session_state.active_nav == "shafana" or st.session_state.get("active_special_view") == "shafana":
            ordered_items.sort(key=lambda kv: 0 if kv[0] == "Shafana_Cashback" else 1)
        dashboard_html = unlock_statements.generate_modern_dashboard_html(
            [v for _, v in ordered_items],
            output_dir=".",
            write_to_disk=False,
            github_token=_get_github_token()
        )
        components.html(dashboard_html, height=1450, scrolling=True)
    else:
        components.html(get_card_shuffle_html(dark_mode=is_dark), height=770 if is_dark else 771, scrolling=False)

# --- Friendly Footer ---
st.markdown(f"""
<div style="text-align: center; max-width: 720px; margin: 22px auto 0 auto; padding: 14px 18px 48px 18px; border-top: 1px solid {border_subtle}; color: {text_secondary}; font-size: 13px; font-weight: 600; line-height: 1.55;">
    Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
</div>
""", unsafe_allow_html=True)
