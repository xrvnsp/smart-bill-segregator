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

# --- Page Configuration (Must Be First Streamlit Call) ---
st.set_page_config(
    page_title="Smart Bill Segregator",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Responsive Stylesheet: Clean Typography Without Breaking Material Icons ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gloria+Hallelujah&family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800;900&display=swap');

    /* Apply professional font ONLY to text/markdown elements — NEVER override Material Symbols icon spans! */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Crazy comic font for tongue-in-cheek privacy disclaimer */
    .crazy-comic-font {
        font-family: 'Gloria Hallelujah', cursive, sans-serif !important;
        letter-spacing: 0.02em !important;
    }

    /* Header styling: transparent background, compact height, keep native sidebar toggle visible */
    header[data-testid="stHeader"], header {
        background: transparent !important;
        height: 2.75rem !important;
        min-height: 2.75rem !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
        z-index: 999999 !important;
    }
    
    /* Hide ONLY the decorative colored top line, deploy button, and 3-dots menu */
    #MainMenu, 
    [data-testid="stDecoration"], 
    .stAppDeployButton, 
    [data-testid="stAppDeployButton"], 
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* Keep Streamlit's native sidebar toggle clean and visible */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 9999999 !important;
    }

    /* Container padding: tight top margin for zero blank space */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    footer {visibility: hidden;}

    iframe {
        border-radius: 20px;
        box-shadow: 0 4px 25px -3px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        width: 100% !important;
    }

    /* Sidebar 5-second persistent toast */
    .sidebar-toast-5s {
        animation: toastFade5s 5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes toastFade5s {
        0% { opacity: 0; transform: translateY(-6px); }
        8% { opacity: 1; transform: translateY(0); }
        84% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-6px); }
    }

    /* Mobile adjustments */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 0.25rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Private Session Passwords & Browser-Persisted EMI Nicknames ---
if "session_passwords" not in st.session_state:
    st.session_state.session_passwords = {"icici": "", "hdfc": "", "sbi": "", "scapia": "", "payslip": "", "sheets_webhook_url": ""}
if "emi_nicknames" not in st.session_state:
    st.session_state.emi_nicknames = {}
if "emi_phones" not in st.session_state:
    st.session_state.emi_phones = {}

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

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 💳 Smart Bill Segregator")
    st.caption("Auto-segregate statements, friend EMIs, cashback, and regular expenses.")

    git_info = get_git_last_updated_info()
    safe_git_msg = html_lib.escape(git_info["msg"])
    safe_git_hash = html_lib.escape(git_info["hash"])
    st.markdown(f"""
    <div style="
        background: #f0f9ff;
        border: 1.5px solid #38bdf8;
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.08);
    ">
        <div style="font-size: 11px; font-weight: 800; color: #0369a1; text-transform: uppercase; letter-spacing: 0.04em; display: flex; align-items: center; gap: 5px;">
            <span>🕒</span><span>Website Last Updated (Git)</span>
        </div>
        <div style="font-size: 12.5px; font-weight: 800; color: #0f172a; margin-top: 4px;">
            {git_info["time_str"]}
        </div>
        <div style="font-size: 11px; font-weight: 600; color: #334155; margin-top: 3px; line-height: 1.35; word-break: break-word;">
            <span style="background: #e0f2fe; color: #0369a1; padding: 1px 5px; border-radius: 4px; font-family: monospace; font-weight: 700;">#{safe_git_hash}</span> {safe_git_msg}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔑 Device Stored Passwords", expanded=True):
        st.caption("🔒 Stored strictly in your browser's local storage on this device. Never saved on any server.")
        
        scapia_val = st.text_input(
            "Scapia Axis Password",
            value=st.session_state.session_passwords.get("scapia", ""),
            type="password",
            help="UPPERCASE name (4) + DDMM (e.g. ROHI2512)",
            key="input_scapia_pwd"
        )
        hdfc_val = st.text_input(
            "HDFC Password",
            value=st.session_state.session_passwords.get("hdfc", ""),
            type="password",
            help="UPPERCASE name (4) + DDMM (e.g. ROHI2512)",
            key="input_hdfc_pwd"
        )
        icici_val = st.text_input(
            "ICICI Password",
            value=st.session_state.session_passwords.get("icici", ""),
            type="password",
            help="Lowercase name (4) + DDMM (e.g. rohi2512)",
            key="input_icici_pwd"
        )
        sbi_val = st.text_input(
            "SBI SimplyCLICK Password",
            value=st.session_state.session_passwords.get("sbi", ""),
            type="password",
            help="Date of birth in DDMMYYYY + Last 4 digits of card (e.g. 150819954321)",
            key="input_sbi_pwd"
        )
        payslip_val = st.text_input(
            "Salary Payslip Password",
            value=st.session_state.session_passwords.get("payslip", ""),
            type="password",
            help="Employee No + PAN last 4 digits (e.g. 115000A or 1234000A)",
            key="input_payslip_pwd"
        )
        webhook_val = st.text_input(
            "Google Sheets Web App URL",
            value=st.session_state.session_passwords.get("sheets_webhook_url", ""),
            key="input_webhook_url"
        )

        # Stacked full-width buttons so text is 100% readable without truncation!
        if st.button("💾 Save Passwords on This Device", use_container_width=True, type="primary"):
            st.session_state.session_passwords["scapia"] = scapia_val.strip()
            st.session_state.session_passwords["icici"] = icici_val.strip()
            st.session_state.session_passwords["hdfc"] = hdfc_val.strip()
            st.session_state.session_passwords["sbi"] = sbi_val.strip()
            st.session_state.session_passwords["payslip"] = payslip_val.strip()
            st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
            st.session_state["pending_save_vault"] = {
                "scapia": scapia_val.strip(),
                "icici": icici_val.strip(),
                "hdfc": hdfc_val.strip(),
                "sbi": sbi_val.strip(),
                "payslip": payslip_val.strip(),
                "sheets_webhook_url": webhook_val.strip()
            }
            st.session_state["sidebar_toast_until"] = time.time() + 5.0
            st.session_state["sidebar_toast_notice"] = {
                "type": "success",
                "title": "Passwords Saved Locally!",
                "desc": "Saved in this browser vault for 1-click auto-unlock."
            }
            st.rerun()

        if st.button("🗑️ Forget Saved Passwords", use_container_width=True, help="Clear saved passwords from this browser"):
            forget_browser_passwords()
            st.rerun()

        # 5-Second Persistent Toast in Sidebar
        now_time = time.time()
        if "sidebar_toast_until" in st.session_state:
            if now_time < st.session_state["sidebar_toast_until"]:
                rem_sec = max(0.5, st.session_state["sidebar_toast_until"] - now_time)
                s_notice = st.session_state.get("sidebar_toast_notice", {
                    "title": "Passwords Saved Locally!",
                    "desc": "Saved in this browser vault for 1-click auto-unlock."
                })
                st.markdown(f"""
                <div id="sidebar-toast-box" class="sidebar-toast-5s" style="
                    background: #064e3b;
                    border: 1.5px solid #10b981;
                    border-radius: 12px;
                    padding: 12px 14px;
                    margin-top: 10px;
                    margin-bottom: 8px;
                    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                ">
                    <span style="font-size: 20px; line-height: 1;">🔒</span>
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-size: 12px; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">{s_notice['title']}</div>
                        <div style="font-size: 11px; color: #a7f3d0; font-weight: 600; margin-top: 2px; line-height: 1.35;">{s_notice['desc']}</div>
                    </div>
                </div>
                <script>
                    setTimeout(function() {{
                        var el = document.getElementById('sidebar-toast-box');
                        if (el) {{
                            el.style.display = 'none';
                        }}
                    }}, {int(rem_sec * 1000)});
                </script>
                """, unsafe_allow_html=True)
            else:
                st.session_state.pop("sidebar_toast_until", None)
                st.session_state.pop("sidebar_toast_notice", None)

    with st.expander("🏷️ Browser-Saved EMI Nicknames", expanded=bool(st.session_state.emi_nicknames)):
        st.caption("🔒 Remembered in your browser's `localStorage` on this device across sessions.")
        if st.session_state.emi_nicknames:
            for lid, lname in list(st.session_state.emi_nicknames.items()):
                lphone = st.session_state.emi_phones.get(lid) or st.session_state.emi_phones.get(lname, "")
                phone_badge = f" • 📱 +{lphone}" if lphone else ""
                st.markdown(
                    f"<div style='background:rgba(245,243,255,0.95);border:1px solid #c4b5fd;border-radius:10px;padding:7px 10px;margin-bottom:6px;font-size:11.5px;color:#2e1065;'>"
                    f"<b>🏷️ {html_lib.escape(lname)}</b> <span style='font-family:monospace;color:#6d28d9;font-size:10.5px;'>({html_lib.escape(lid)}){html_lib.escape(phone_badge)}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.caption("No EMI nicknames saved yet. Add one below or click **💾 Save Tag in Browser** directly on any purple EMI receipt card!")

        emi_loan_key = st.text_input(
            "Loan ID / EMI Key",
            placeholder="e.g. 146608745 or 28/09/2026_44370.00",
            key="side_emi_key"
        )
        emi_friend_name = st.text_input(
            "Friend / Item Nickname",
            placeholder="e.g. Naveen S25 Edge",
            key="side_emi_name"
        )
        emi_friend_phone = st.text_input(
            "Friend WhatsApp No. (Optional)",
            placeholder="10-digit mobile (e.g. 9876543210)",
            key="side_emi_phone"
        )
        if st.button("💾 Save EMI Nickname in Browser", use_container_width=True, key="btn_save_emi_side"):
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
                st.session_state["sidebar_toast_until"] = time.time() + 5.0
                st.session_state["sidebar_toast_notice"] = {
                    "type": "success",
                    "title": f"Saved EMI Tag: {n_clean}",
                    "desc": "Stored in browser localStorage on this device."
                }
                st.rerun()

        if st.session_state.emi_nicknames:
            if st.button("🗑️ Clear Saved EMI Nicknames", use_container_width=True, key="btn_clear_emi_side"):
                st.session_state.emi_nicknames = {}
                st.session_state.emi_phones = {}
                st.session_state["pending_clear_emi_vault"] = True
                st.session_state["emi_vault_cleared_until"] = time.time() + 4.0
                st.session_state["sidebar_toast_until"] = time.time() + 5.0
                st.session_state["sidebar_toast_notice"] = {
                    "type": "info",
                    "title": "EMI Nicknames Cleared",
                    "desc": "Wiped from this device browser vault."
                }
                st.rerun()

    st.link_button(
        "📋 Copy Google Sheet Template",
        unlock_statements.GOOGLE_SHEET_TEMPLATE_URL,
        use_container_width=True
    )
    st.markdown("---")
    
    # Comic Disclaimer with Crazy Hand-Drawn Font in Sidebar
    st.markdown("""
    <div class="crazy-comic-font" style="
        background: #f0fdf4;
        border: 1.5px dashed #4ade80;
        border-radius: 14px;
        padding: 10px 12px;
        font-size: 13px;
        color: #15803d;
        line-height: 1.45;
        transform: rotate(-0.5deg);
        box-shadow: 0 2px 8px rgba(34, 197, 94, 0.1);
    ">
        🔒 100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜
    </div>
    """, unsafe_allow_html=True)

# --- Session State for Uploaded Statements ---
if "statements_data" not in st.session_state:
    st.session_state.statements_data = {}

# --- Main Page Header (Zero Gap & Professional Presentation) ---
st.markdown("<div style='margin-top: 0px; margin-bottom: 4px;'><h1 style='font-size: 26px; font-weight: 800; color: inherit; margin: 0; letter-spacing: -0.02em;'>💳 Smart Bill Segregator</h1></div>", unsafe_allow_html=True)
st.caption("Automatic statement analysis, installment segregation, and cashback audit.")

with st.container():
    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Select Statement PDF(s) to Decrypt & Analyze (In-Memory Session):",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload your Axis Bank (Scapia), HDFC, ICICI, or SBI SimplyCLICK e-statement PDFs. Decrypted strictly in RAM and never stored on any server."
        )

    with info_col:
        # Visual Vault Notification Card
        active_vault_list = []
        if st.session_state.session_passwords.get("scapia"): active_vault_list.append("Scapia")
        if st.session_state.session_passwords.get("hdfc"): active_vault_list.append("HDFC")
        if st.session_state.session_passwords.get("icici"): active_vault_list.append("ICICI")
        if st.session_state.session_passwords.get("sbi"): active_vault_list.append("SBI")
        if st.session_state.session_passwords.get("payslip"): active_vault_list.append("Payslip")

        emi_saved_count = len(st.session_state.emi_nicknames)
        emi_count_text = f" • 🏷️ {emi_saved_count} EMI Tag(s)" if emi_saved_count > 0 else ""
        if active_vault_list:
            st.markdown(f"""
            <div style="background: rgba(240, 253, 244, 0.95); border: 1px solid #86efac; border-radius: 14px; padding: 10px 14px; margin-bottom: 6px; box-shadow: 0 2px 8px rgba(22,101,52,0.06);">
                <div style="font-size: 12px; font-weight: 800; color: #166534; display: flex; align-items: center; gap: 6px;">
                    <span>🟢</span><span>Vault Active: {', '.join(active_vault_list)}{emi_count_text}</span>
                </div>
                <div style="font-size: 11px; color: #15803d; margin-top: 3px; font-weight: 600;">
                    Statements & EMI nicknames load automatically on this device!
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: rgba(248, 250, 252, 0.95); border: 1px solid #cbd5e1; border-radius: 14px; padding: 10px 14px; margin-bottom: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: #475569; display: flex; align-items: center; gap: 6px;">
                    <span>⚪</span><span>No Device Passwords Saved</span>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 3px;">
                    Open the sidebar top-left or configure below.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # In-Page Quick Password Manager (Native Streamlit Expander)
        with st.expander("🔑 Quick Device Passwords", expanded=False):
            st.caption("🔒 Stored in your client browser on this device. Never saved on any server.")
            q_scapia = st.text_input(
                "Scapia Axis Password",
                value=st.session_state.session_passwords.get("scapia", ""),
                type="password",
                help="UPPERCASE name (4) + DDMM",
                key="q_inp_scapia"
            )
            q_hdfc = st.text_input(
                "HDFC Password",
                value=st.session_state.session_passwords.get("hdfc", ""),
                type="password",
                help="UPPERCASE name (4) + DDMM",
                key="q_inp_hdfc"
            )
            q_icici = st.text_input(
                "ICICI Password",
                value=st.session_state.session_passwords.get("icici", ""),
                type="password",
                help="Lowercase name (4) + DDMM",
                key="q_inp_icici"
            )
            q_sbi = st.text_input(
                "SBI Password",
                value=st.session_state.session_passwords.get("sbi", ""),
                type="password",
                help="DDMMYYYY + Last 4 digits",
                key="q_inp_sbi"
            )
            q_payslip = st.text_input(
                "Salary Payslip Password",
                value=st.session_state.session_passwords.get("payslip", ""),
                type="password",
                help="Employee No + PAN last 4 digits (e.g. 115000A)",
                key="q_inp_payslip"
            )
            q_btn_col1, q_btn_col2 = st.columns(2)
            with q_btn_col1:
                if st.button("💾 Save Passwords", use_container_width=True, type="primary", key="q_btn_save"):
                    st.session_state.session_passwords["scapia"] = q_scapia.strip()
                    st.session_state.session_passwords["icici"] = q_icici.strip()
                    st.session_state.session_passwords["hdfc"] = q_hdfc.strip()
                    st.session_state.session_passwords["sbi"] = q_sbi.strip()
                    st.session_state.session_passwords["payslip"] = q_payslip.strip()
                    st.session_state["pending_save_vault"] = {
                        "scapia": q_scapia.strip(),
                        "icici": q_icici.strip(),
                        "hdfc": q_hdfc.strip(),
                        "sbi": q_sbi.strip(),
                        "payslip": q_payslip.strip(),
                        "sheets_webhook_url": st.session_state.session_passwords.get("sheets_webhook_url", "")
                    }
                    st.session_state["sidebar_toast_until"] = time.time() + 5.0
                    st.session_state["sidebar_toast_notice"] = {
                        "type": "success",
                        "title": "Passwords Saved Locally!",
                        "desc": "Stored in browser vault for this device."
                    }
                    st.rerun()
            with q_btn_col2:
                if st.button("🗑️ Forget Passwords", use_container_width=True, key="q_btn_forget"):
                    forget_browser_passwords()
                    st.rerun()

# --- Process Uploaded Files Strictly in RAM (Zero Disk Writes!) ---
st.session_state.statements_data = {}
if uploaded_files:
    for up_file in uploaded_files:
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
                rdata.get("bank_short") not in ("Scapia Axis", "SBI SimplyCLICK", "ICICI Amazon", "HDFC", "Salary Payslip")
                or rdata.get("bank_name") == "Bank Statement"
                or not rdata.get("date_groups")
                or not rdata.get("all_txns")
            ):
                success = False
                msg = f"Non-Bill / Non-Transactional PDF Detected ({up_file.name}): 0 bill transactions found. Please upload a valid Axis Bank (Scapia), HDFC, ICICI, SBI credit card statement, or Salary Payslip."
                rdata = None

        if success and rdata:
            slot_key = f"{rdata['bank_short']}_{rdata.get('statement_month', up_file.name)}"
            st.session_state.statements_data[slot_key] = rdata
            if rdata.get("payslip_meta", {}).get("is_payslip"):
                pm = rdata["payslip_meta"]
                st.success(f"✅ Salary Payslip Loaded: {up_file.name} ({pm.get('pay_period')}) — Net Pay {pm.get('net_pay')} • Full 30-Day Rate: ₹{pm.get('full_month_gross', 0):,.2f}/mo (₹{pm.get('per_day_rate', 0):,.2f}/day)")
            else:
                st.success(f"✅ Unlocked in memory: {up_file.name} ({rdata.get('bank_name')}) — {len(rdata.get('date_groups', {}))} date groups found")
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
                        ["Axis Bank (Scapia)", "HDFC Bank (Swiggy)", "ICICI Bank (Amazon Pay)", "SBI Card (SimplyCLICK)", "Salary Payslip (Skillveri)"],
                        index=def_idx,
                        horizontal=True,
                        key=f"bank_choice_{up_file.name}"
                    )
                    if "Payslip" in selected_bank or "Skillveri" in selected_bank:
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
                    if st.form_submit_button("🔓 Unlock & Save in Browser", use_container_width=True):
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

# --- Active Statements Controls & Clear State ---
if st.session_state.statements_data:
    status_cols = st.columns([3, 1, 1])
    with status_cols[0]:
        badge_html = " ".join([
            f'<span style="background-color: rgba(241, 245, 249, 0.15); color: inherit; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 800; border: 1px solid rgba(203, 213, 225, 0.3); margin-right: 8px;">🏛️ {s.get("bank_name", k)} ({len(s.get("date_groups", {}))} date groups)</span>'
            for k, s in st.session_state.statements_data.items()
        ])
        st.markdown(f"<div style='margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'><span style='font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;'>Active Session Statements:</span> {badge_html}</div>", unsafe_allow_html=True)
    with status_cols[1]:
        if st.button("🔄 Refresh View", use_container_width=True):
            st.rerun()
    with status_cols[2]:
        if st.button("🗑️ Clear Session", use_container_width=True, help="Wipe loaded statements from memory"):
            st.session_state.statements_data = {}
            st.rerun()

# --- CARDS SUPPORTED SO FAR: Professional Dual Deck Display with Crazy Comic Disclaimer ---
def get_card_shuffle_html():
    # Scapia Dual Travel Editions
    scapia_orange_b64 = unlock_statements.get_card_b64("card-facia-scapia-orange.png")
    scapia_green_b64 = unlock_statements.get_card_b64("card-facia-scapia-green.png")

    # Core Rewards Cards
    swiggy_b64 = unlock_statements.get_card_b64("card-facia-swiggy.jpg")
    amazon_b64 = unlock_statements.get_card_b64("card-facia-amazon.png")
    sbi_b64 = unlock_statements.get_card_b64("simply-click-card-face.png")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link href="https://fonts.googleapis.com/css2?family=Gloria+Hallelujah&family=Inter:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    body {{ background: transparent; display: flex; justify-content: center; align-items: flex-start; padding: 6px 4px 14px 4px; overflow-x: hidden; }}
    
    .showcase-card {{
      width: 100%;
      max-width: 980px;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid rgba(226, 232, 240, 0.95);
      border-radius: 26px;
      padding: 20px 22px 24px 22px;
      text-align: center;
      box-shadow: 0 12px 35px -8px rgba(0, 0, 0, 0.08);
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 0 auto;
    }}

    /* Pixel-aligned Pill Badges with Centered SVG Icons */
    .headline-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      padding: 6px 15px;
      border-radius: 9999px;
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #1e293b;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      line-height: 1;
      margin-bottom: 8px;
    }}

    .pill-icon {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 15px;
      height: 15px;
      flex-shrink: 0;
    }}

    .pill-text {{
      display: inline-block;
      line-height: 1;
      padding-top: 0.5px;
    }}

    .title {{
      font-size: 20px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.025em;
      margin-bottom: 4px;
    }}

    .subtitle {{
      font-size: 12.5px;
      color: #64748b;
      max-width: 680px;
      line-height: 1.45;
      margin-bottom: 14px;
      font-weight: 500;
    }}

    /* Dual Grid Layout: Stretched Equal-Height Side-by-Side on Desktop, Top/Bottom Stack on Mobile */
    .dual-grid {{
      display: grid;
      grid-template-columns: 1fr 1.25fr;
      gap: 18px;
      width: 100%;
      align-items: stretch;
      margin-bottom: 14px;
    }}

    .deck-section {{
      background: rgba(248, 250, 252, 0.85);
      border: 1px solid rgba(226, 232, 240, 0.95);
      border-radius: 20px;
      padding: 16px 14px 18px 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      position: relative;
    }}

    .section-header-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 5px 13px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      line-height: 1;
      margin-bottom: 10px;
    }}
    .pill-travel {{ background: #fff7ed; border: 1px solid #fed7aa; color: #c2410c; }}
    .pill-rewards {{ background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }}

    /* =========================================================
       SCAPIA SECTION: Dual Travel Editions
       ========================================================= */
    .travel-stage {{
      perspective: 1200px;
      perspective-origin: center center;
      width: 100%;
      max-width: 250px;
      height: 265px;
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
      margin: 4px 0;
    }}

    .card-p {{
      width: 164px;
      height: 258px;
      border-radius: 16px;
      position: absolute;
      transform-style: preserve-3d;
      will-change: transform, opacity;
      user-select: none;
      box-shadow: 0 18px 36px -10px rgba(0, 0, 0, 0.32);
      transition: transform 0.6s cubic-bezier(0.34, 1.3, 0.64, 1), opacity 0.4s ease;
      background-size: cover !important;
      background-position: center !important;
      background-repeat: no-repeat !important;
    }}

    .card-p::after, .card-l::after {{
      content: '';
      position: absolute;
      inset: 0;
      border-radius: inherit;
      border: 1px solid rgba(255, 255, 255, 0.25);
      pointer-events: none;
    }}

    .card-glare {{
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.05) 50%, rgba(0,0,0,0.15) 100%);
      pointer-events: none;
    }}

    /* Card 1: Orange Mastercard */
    #card-p1 {{
      background-image: url('{scapia_orange_b64}');
      animation: shufflePortOrange 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}
    /* Card 2: Green RuPay */
    #card-p2 {{
      background-image: url('{scapia_green_b64}');
      animation: shufflePortGreen 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}

    .travel-stage:hover .card-p, .rewards-stage:hover .card-l {{
      animation-play-state: paused;
    }}

    @keyframes shufflePortOrange {{
      0%, 42% {{ transform: translate3d(-6px, 0, 32px) scale(1) rotate(0deg); z-index: 25; opacity: 1; box-shadow: 0 22px 45px -10px rgba(0, 0, 0, 0.38); }}
      50%, 92% {{ transform: translate3d(26px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.85; box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.22); }}
      100% {{ transform: translate3d(-6px, 0, 32px) scale(1) rotate(0deg); z-index: 25; opacity: 1; }}
    }}

    @keyframes shufflePortGreen {{
      0%, 42% {{ transform: translate3d(26px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.85; box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.22); }}
      50%, 92% {{ transform: translate3d(-6px, 0, 32px) scale(1) rotate(0deg); z-index: 25; opacity: 1; box-shadow: 0 22px 45px -10px rgba(0, 0, 0, 0.38); }}
      100% {{ transform: translate3d(26px, -8px, -32px) scale(0.92) rotate(4deg); z-index: 10; opacity: 0.85; }}
    }}

    /* =========================================================
       REWARDS SECTION: Core Cashback Cards (Swiggy, Amazon, SBI)
       ========================================================= */
    .rewards-stage {{
      perspective: 1200px;
      perspective-origin: center center;
      width: 100%;
      max-width: 320px;
      height: 265px;
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
      margin: 4px 0;
    }}

    .card-l {{
      width: 255px;
      height: 160px;
      border-radius: 14px;
      position: absolute;
      transform-style: preserve-3d;
      will-change: transform, opacity;
      user-select: none;
      box-shadow: 0 18px 36px -10px rgba(0, 0, 0, 0.28);
      transition: transform 0.6s cubic-bezier(0.34, 1.3, 0.64, 1), opacity 0.4s ease;
      background-size: cover !important;
      background-position: center !important;
      background-repeat: no-repeat !important;
    }}

    .embossed-l {{
      position: absolute;
      bottom: 10px;
      left: 12px;
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      font-family: monospace;
      color: rgba(255,255,255,0.95);
      text-shadow: 0 1.5px 2px rgba(0,0,0,0.85);
      pointer-events: none;
    }}

    #card-l1 {{ background-image: url('{swiggy_b64}'); animation: shuffleLand1 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    #card-l2 {{ background-image: url('{amazon_b64}'); animation: shuffleLand2 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}
    #card-l3 {{ background-image: url('{sbi_b64}'); animation: shuffleLand3 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite; }}

    @keyframes shuffleLand1 {{
      0%, 28% {{ transform: translate3d(0, 4px, 35px) scale(1) rotate(0deg); z-index: 30; opacity: 1; box-shadow: 0 20px 42px -10px rgba(0, 0, 0, 0.32); }}
      33%, 61% {{ transform: translate3d(30px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.88; }}
      66%, 95% {{ transform: translate3d(-28px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.72; }}
      100% {{ transform: translate3d(0, 4px, 35px) scale(1) rotate(0deg); z-index: 30; opacity: 1; }}
    }}
    @keyframes shuffleLand2 {{
      0%, 28% {{ transform: translate3d(30px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.88; }}
      33%, 61% {{ transform: translate3d(-28px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.72; }}
      66%, 95% {{ transform: translate3d(0, 4px, 35px) scale(1) rotate(0deg); z-index: 30; opacity: 1; }}
      100% {{ transform: translate3d(30px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.88; }}
    }}
    @keyframes shuffleLand3 {{
      0%, 28% {{ transform: translate3d(-28px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.72; }}
      33%, 61% {{ transform: translate3d(0, 4px, 35px) scale(1) rotate(0deg); z-index: 30; opacity: 1; }}
      66%, 95% {{ transform: translate3d(30px, -10px, 0px) scale(0.92) rotate(4deg); z-index: 20; opacity: 0.88; }}
      100% {{ transform: translate3d(-28px, -14px, -35px) scale(0.85) rotate(-5deg); z-index: 10; opacity: 0.72; }}
    }}

    /* Badges & Tags Row */
    .mini-badges {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 6px;
      margin-top: 10px;
    }}
    .mini-badge {{
      font-size: 10.5px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid rgba(203, 213, 225, 0.85);
      color: #334155;
      line-height: 1.2;
    }}

    /* Crazy Comic Font Disclaimer */
    .comic-disclaimer-box {{
      font-family: 'Gloria Hallelujah', cursive, sans-serif !important;
      letter-spacing: 0.025em;
      font-size: 13.5px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 9px 18px;
      border-radius: 9999px;
      background: #f0fdf4;
      border: 1.5px dashed #4ade80;
      color: #15803d;
      margin-top: 4px;
      transform: rotate(-0.5deg);
      box-shadow: 0 2px 8px rgba(34, 197, 94, 0.12);
      transition: transform 0.2s ease;
    }}
    .comic-disclaimer-box:hover {{
      transform: rotate(0.5deg) scale(1.02);
    }}

    /* Mobile Responsive Stacking: TOP = Scapia, BOTTOM = SBI / ICICI / HDFC with Full Padding & Zero Clipping */
    @media (max-width: 859px) {{
      .showcase-card {{
        padding: 18px 14px 24px 14px;
        border-radius: 22px;
      }}
      .dual-grid {{
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 14px;
      }}
      .deck-section-travel {{
        order: 1 !important;
        width: 100%;
        padding: 16px 12px 18px 12px;
      }}
      .deck-section-rewards {{
        order: 2 !important;
        width: 100%;
        padding: 16px 12px 18px 12px;
      }}
      .travel-stage {{
        height: 230px;
        margin: 6px 0 8px 0;
      }}
      .card-p {{
        width: 142px;
        height: 222px;
      }}
      .rewards-stage {{
        height: 176px;
        margin: 8px 0 10px 0;
      }}
      .card-l {{
        width: 224px;
        height: 140px;
      }}
      .comic-disclaimer-box {{
        font-size: 12px;
        padding: 8px 14px;
        border-radius: 16px;
      }}
    }}
  </style>
</head>
<body>
  <div class="showcase-card" id="main-showcase-card">
    <div class="headline-pill">
      <span class="pill-icon">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#2563eb" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
      </span>
      <span class="pill-text">Cards Supported So Far</span>
    </div>
    <h2 class="title">No Statement Loaded in Current Session</h2>
    <p class="subtitle">
      Upload your <b>Axis Bank (Scapia)</b>, <b>HDFC Bank (Swiggy)</b>, <b>ICICI Bank (Amazon Pay)</b>, or <b>SBI Card (SimplyCLICK)</b> monthly e-statement PDF above to securely decrypt, segregate friend EMIs, and reconcile your billing summary.
    </p>

    <!-- Side-by-Side Dual Deck Grid (Top = Scapia Travel, Bottom = Core Rewards on Mobile) -->
    <div class="dual-grid">
      
      <!-- TOP ON MOBILE / LEFT ON DESKTOP: Scapia Travel Editions (Orange & Green) -->
      <div class="deck-section deck-section-travel" onclick="cyclePortraitDeck()" title="Click to flip Scapia editions">
        <span class="section-header-pill pill-travel">
          <span class="pill-icon">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#c2410c" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>
          </span>
          <span class="pill-text">Axis Bank Scapia Editions</span>
        </span>
        <div class="travel-stage" id="travel-stage">
          <div id="card-p1" class="card-p">
            <div class="card-glare"></div>
          </div>
          <div id="card-p2" class="card-p">
            <div class="card-glare"></div>
          </div>
        </div>
        <div class="mini-badges">
          <span class="mini-badge" style="color: #ea580c; border-color: #fed7aa; background: #fff7ed;">Scapia Mastercard (Orange)</span>
          <span class="mini-badge" style="color: #16a34a; border-color: #bbf7d0; background: #f0fdf4;">Scapia RuPay (Green)</span>
        </div>
      </div>

      <!-- BOTTOM ON MOBILE / RIGHT ON DESKTOP: Daily Rewards Cards (Swiggy, Amazon, SBI) -->
      <div class="deck-section deck-section-rewards" onclick="cycleLandscapeDeck()" title="Click to cycle rewards cards">
        <span class="section-header-pill pill-rewards">
          <span class="pill-icon">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#1e40af" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
          </span>
          <span class="pill-text">Daily Rewards & Cashback Cards</span>
        </span>
        <div class="rewards-stage" id="rewards-stage">
          <div id="card-l1" class="card-l">
            <div class="card-glare"></div>
            <div class="embossed-l">SWIGGY HDFC</div>
          </div>
          <div id="card-l2" class="card-l">
            <div class="card-glare"></div>
            <div class="embossed-l" style="color: #fde68a;">AMAZON PAY ICICI</div>
          </div>
          <div id="card-l3" class="card-l">
            <div class="card-glare"></div>
            <div class="embossed-l">SBI SIMPLYCLICK</div>
          </div>
        </div>
        <div class="mini-badges">
          <span class="mini-badge" style="color: #c2410c; background: #fff7ed;">Swiggy HDFC (10% Food)</span>
          <span class="mini-badge" style="color: #b45309; background: #fefce8;">Amazon Pay (5% Shop)</span>
          <span class="mini-badge" style="color: #882438; background: #fff1f2;">SBI SimplyCLICK (10X)</span>
        </div>
      </div>

    </div>

    <!-- Comic Disclaimer with Crazy Hand-Drawn Font -->
    <div class="comic-disclaimer-box">
      <span>🔒</span>
      <span>100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜</span>
    </div>
  </div>

  <script>
    let isFlipped = false;
    function cyclePortraitDeck() {{
      isFlipped = !isFlipped;
      const p1 = document.getElementById('card-p1');
      const p2 = document.getElementById('card-p2');
      if (!p1 || !p2) return;
      p1.style.animation = isFlipped ? 'shufflePortGreen 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite' : 'shufflePortOrange 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite';
      p2.style.animation = isFlipped ? 'shufflePortOrange 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite' : 'shufflePortGreen 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite';
    }}

    function cycleLandscapeDeck() {{
      const l1 = document.getElementById('card-l1');
      const l2 = document.getElementById('card-l2');
      const l3 = document.getElementById('card-l3');
      if (!l1 || !l2 || !l3) return;
      const b1 = l1.style.backgroundImage || getComputedStyle(l1).backgroundImage;
      const b2 = l2.style.backgroundImage || getComputedStyle(l2).backgroundImage;
      const b3 = l3.style.backgroundImage || getComputedStyle(l3).backgroundImage;
      l1.style.backgroundImage = b2;
      l2.style.backgroundImage = b3;
      l3.style.backgroundImage = b1;
    }}

    /* Auto-resize parent Streamlit iframe height so mobile never clips the 2nd section or bottom padding */
    function syncShowcaseHeight() {{
      const card = document.getElementById('main-showcase-card');
      if (!card) return;
      const h = Math.ceil(card.getBoundingClientRect().height) + 26;
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
    setTimeout(syncShowcaseHeight, 900);
  </script>
</body>
</html>"""

# --- Render Web Dashboard Strictly in RAM ---
if st.session_state.statements_data:
    dashboard_html = unlock_statements.generate_modern_dashboard_html(
        list(st.session_state.statements_data.values()),
        output_dir=".",
        write_to_disk=False
    )
    components.html(dashboard_html, height=1450, scrolling=True)
else:
    # Initial height 920 + JS auto-resizer ensures zero clipping on Mobile and tight fit on Desktop
    components.html(get_card_shuffle_html(), height=920, scrolling=False)

# --- Friendly Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 24px; padding: 14px 12px; border-top: 1px solid rgba(226, 232, 240, 0.3); color: #64748b; font-size: 13px; font-weight: 600;">
    Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
</div>
""", unsafe_allow_html=True)
