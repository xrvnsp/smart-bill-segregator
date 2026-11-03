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
import streamlit as st
import streamlit.components.v1 as components
import unlock_statements

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

# --- Responsive Stylesheet: Restored Native Sidebar Toggle, Zero Gap & 5s Toast ---
st.markdown("""
<style>
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

    /* Force Streamlit's native sidebar toggle (collapsedControl & collapseButton) to be ALWAYS visible & clickable */
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] button,
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    header [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 9999999 !important;
        pointer-events: auto !important;
    }

    /* Style the native collapsedControl button with a clean Apple-style pill appearance */
    [data-testid="collapsedControl"] {
        background: rgba(255, 255, 255, 0.94) !important;
        backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(203, 213, 225, 0.85) !important;
        border-radius: 12px !important;
        padding: 4px 10px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08) !important;
        color: #0f172a !important;
        cursor: pointer !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        margin-left: 0.5rem !important;
        margin-top: 0.25rem !important;
    }
    [data-testid="collapsedControl"]:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.14) !important;
    }

    /* Dark mode styling for native collapsedControl */
    @media (prefers-color-scheme: dark) {
        [data-testid="collapsedControl"] {
            background: rgba(30, 41, 59, 0.94) !important;
            border-color: rgba(71, 85, 105, 0.9) !important;
            color: #f8fafc !important;
        }
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

    /* Sidebar 5-second persistent toast (Never shrinks height, only fades opacity) */
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

# --- Initialize Private Session Passwords (Supports HDFC, ICICI, SBI & Scapia Axis) ---
if "session_passwords" not in st.session_state:
    st.session_state.session_passwords = {"icici": "", "hdfc": "", "sbi": "", "scapia": "", "sheets_webhook_url": ""}

# --- Device-Local Browser Storage Bridge (Client-Side localStorage) ---
bridge_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_storage_bridge")
storage_bridge = components.declare_component("local_storage_bridge", path=bridge_dir)

# Handle pending save or clear commands for browser localStorage
pending_save = st.session_state.pop("pending_save_vault", None)
pending_clear = st.session_state.pop("pending_clear_vault", None)

# Run the invisible client-side bridge in the user's browser (height=0)
client_vault = storage_bridge(
    save_passwords=pending_save,
    clear_passwords=pending_clear,
    key="browser_vault_bridge"
)

# Restore saved passwords from browser localStorage on this device
if client_vault and isinstance(client_vault, dict):
    restored_keys = []
    for b_key, b_name in [("hdfc", "HDFC Bank"), ("icici", "ICICI Bank"), ("sbi", "SBI SimplyCLICK"), ("scapia", "Scapia Axis")]:
        if not st.session_state.session_passwords.get(b_key) and client_vault.get(b_key) and client_vault[b_key].strip():
            st.session_state.session_passwords[b_key] = client_vault[b_key].strip()
            restored_keys.append(b_name)
    if not st.session_state.session_passwords.get("sheets_webhook_url") and client_vault.get("sheets_webhook_url"):
        st.session_state.session_passwords["sheets_webhook_url"] = client_vault["sheets_webhook_url"].strip()

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 💳 Smart Bill Segregator")
    st.caption("Auto-segregate statements, friend EMIs, cashback, and regular expenses.")

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
            st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
            st.session_state["pending_save_vault"] = {
                "scapia": scapia_val.strip(),
                "icici": icici_val.strip(),
                "hdfc": hdfc_val.strip(),
                "sbi": sbi_val.strip(),
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
            st.session_state.session_passwords = {"scapia": "", "icici": "", "hdfc": "", "sbi": "", "sheets_webhook_url": ""}
            st.session_state["pending_clear_vault"] = True
            st.session_state["sidebar_toast_until"] = time.time() + 5.0
            st.session_state["sidebar_toast_notice"] = {
                "type": "info",
                "title": "Passwords Cleared",
                "desc": "Wiped from this device's browser vault."
            }
            st.rerun()

        # 5-Second Persistent Toast in Sidebar (Rock-solid background box that never collapses)
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

    st.link_button(
        "📋 Copy Google Sheet Template",
        unlock_statements.GOOGLE_SHEET_TEMPLATE_URL,
        use_container_width=True
    )
    st.markdown("---")
    st.caption("🔒 100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜")

# --- Session State for Uploaded Statements ---
if "statements_data" not in st.session_state:
    st.session_state.statements_data = {}

# --- Main Page Header (Zero Gap & Clean Presentation) ---
st.markdown("<div style='margin-top: 0px; margin-bottom: 4px;'><h1 style='font-size: 26px; font-weight: 800; color: inherit; margin: 0; letter-spacing: -0.02em;'>💳 Smart Bill Segregator</h1></div>", unsafe_allow_html=True)
st.caption("Auto-segregates bank statements, friend EMIs, cashback, and regular card spends.")

with st.container():
    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Upload Statement PDF(s) to Unlock & Analyze (100% In-Memory):",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select Axis Bank (Scapia), HDFC, ICICI, or SBI SimplyCLICK bank statement PDFs. Processed strictly in RAM and never saved to server disk."
        )

    with info_col:
        # Visual Vault Notification Card
        active_vault_list = []
        if st.session_state.session_passwords.get("scapia"): active_vault_list.append("Scapia")
        if st.session_state.session_passwords.get("hdfc"): active_vault_list.append("HDFC")
        if st.session_state.session_passwords.get("icici"): active_vault_list.append("ICICI")
        if st.session_state.session_passwords.get("sbi"): active_vault_list.append("SBI")

        if active_vault_list:
            st.markdown(f"""
            <div style="background: rgba(240, 253, 244, 0.95); border: 1px solid #86efac; border-radius: 14px; padding: 10px 14px; margin-bottom: 6px; box-shadow: 0 2px 8px rgba(22,101,52,0.06);">
                <div style="font-size: 12px; font-weight: 800; color: #166534; display: flex; align-items: center; gap: 6px;">
                    <span>🟢</span><span>Vault Active: {', '.join(active_vault_list)}</span>
                </div>
                <div style="font-size: 11px; color: #15803d; margin-top: 3px; font-weight: 600;">
                    Statements unlock automatically on this device!
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
                    Click <b>&gt;</b> top-left or configure below.
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
            if st.button("💾 Save to This Device", use_container_width=True, type="primary", key="q_btn_save"):
                st.session_state.session_passwords["scapia"] = q_scapia.strip()
                st.session_state.session_passwords["icici"] = q_icici.strip()
                st.session_state.session_passwords["hdfc"] = q_hdfc.strip()
                st.session_state.session_passwords["sbi"] = q_sbi.strip()
                st.session_state["pending_save_vault"] = {
                    "scapia": q_scapia.strip(),
                    "icici": q_icici.strip(),
                    "hdfc": q_hdfc.strip(),
                    "sbi": q_sbi.strip(),
                    "sheets_webhook_url": st.session_state.session_passwords.get("sheets_webhook_url", "")
                }
                st.session_state["sidebar_toast_until"] = time.time() + 5.0
                st.session_state["sidebar_toast_notice"] = {
                    "type": "success",
                    "title": "Passwords Saved Locally!",
                    "desc": "Stored in browser vault for this device."
                }
                st.rerun()

# --- Process Uploaded Files Strictly in RAM (Zero Disk Writes!) ---
if uploaded_files:
    for up_file in uploaded_files:
        pdf_bytes_io = io.BytesIO(up_file.getvalue())
        
        success, msg, rdata = unlock_statements.process_statement_file(
            up_file.name,
            base_downloads_dir=".",
            custom_passwords=st.session_state.session_passwords,
            file_obj=pdf_bytes_io,
            save_to_disk=False
        )
        if success:
            st.session_state.statements_data[rdata["bank_short"]] = rdata
            st.success(f"✅ Unlocked in memory: {up_file.name} ({rdata.get('bank_name')}) — {len(rdata.get('date_groups', {}))} date groups found")
        else:
            st.error(f"⚠️ {up_file.name}: {msg}")
            if "password" in msg.lower():
                with st.form(key=f"pwd_unlock_{up_file.name}"):
                    fname_low = up_file.name.lower()
                    if "scapia" in fname_low or "axis" in fname_low: def_idx = 0
                    elif "hdfc" in fname_low or "swiggy" in fname_low: def_idx = 1
                    elif "icici" in fname_low or "amazon" in fname_low: def_idx = 2
                    else: def_idx = 3

                    st.markdown(f"**Unlock `{up_file.name}`:**")
                    selected_bank = st.radio(
                        "Statement Bank Format:",
                        ["Axis Bank (Scapia)", "HDFC Bank (Swiggy)", "ICICI Bank (Amazon Pay)", "SBI Card (SimplyCLICK)"],
                        index=def_idx,
                        horizontal=True,
                        key=f"bank_choice_{up_file.name}"
                    )
                    if "Scapia" in selected_bank or "Axis" in selected_bank:
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

# --- 3D Portrait Card Shuffling Showcase (Two Scapia Editions in Portrait) ---
def get_card_shuffle_html():
    scapia_orange_b64 = unlock_statements.get_card_b64("card-facia-scapia-orange.png")
    scapia_green_b64 = unlock_statements.get_card_b64("card-facia-scapia-green.png")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif; }}
    body {{ background: transparent; display: flex; justify-content: center; align-items: flex-start; padding: 8px 6px; overflow: hidden; }}
    
    .showcase-card {{
      width: 100%;
      max-width: 860px;
      background: rgba(255, 255, 255, 0.90);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid rgba(226, 232, 240, 0.88);
      border-radius: 26px;
      padding: 22px 18px 24px 18px;
      text-align: center;
      box-shadow: 0 12px 35px -8px rgba(0, 0, 0, 0.06);
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 0 auto;
    }}

    .headline-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 9999px;
      background: #fff7ed;
      border: 1px solid #fed7aa;
      color: #c2410c;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 8px;
    }}

    .title {{
      font-size: 21px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.02em;
      margin-bottom: 4px;
    }}

    .subtitle {{
      font-size: 13px;
      color: #64748b;
      max-width: 580px;
      line-height: 1.45;
      margin-bottom: 10px;
    }}

    /* 3D Portrait Physical Card Stage with Perspective */
    .card-stage-wrap {{
      perspective: 1200px;
      perspective-origin: center center;
      width: 100%;
      max-width: 320px;
      height: 330px;
      position: relative;
      margin: 4px auto 14px auto;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
    }}

    .physical-card-portrait {{
      width: 198px;
      height: 312px;
      border-radius: 18px;
      position: absolute;
      transform-style: preserve-3d;
      will-change: transform, opacity;
      user-select: none;
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.32);
      transition: transform 0.6s cubic-bezier(0.34, 1.3, 0.64, 1), opacity 0.4s ease, box-shadow 0.4s ease;
      background-size: cover !important;
      background-position: center !important;
      background-repeat: no-repeat !important;
    }}

    .physical-card-portrait::after {{
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 18px;
      border: 1px solid rgba(255, 255, 255, 0.25);
      pointer-events: none;
    }}

    .card-glare {{
      position: absolute;
      inset: 0;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.05) 50%, rgba(0,0,0,0.15) 100%);
      pointer-events: none;
    }}

    .embossed-name {{
      position: absolute;
      bottom: 14px;
      left: 16px;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-family: monospace;
      color: rgba(255,255,255,0.95);
      text-shadow: 0 1.5px 2px rgba(0,0,0,0.85);
      pointer-events: none;
    }}

    /* Card Background Artworks */
    #card-scapia-orange {{
      background-image: url('{scapia_orange_b64}');
      animation: shufflePortrait1 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}
    #card-scapia-green {{
      background-image: url('{scapia_green_b64}');
      animation: shufflePortrait2 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}

    /* Hover pauses animation so user can inspect card */
    .card-stage-wrap:hover .physical-card-portrait {{
      animation-play-state: paused;
    }}

    /* Continuous 3D Portrait Shuffling Cycle (Two Scapia Cards) */
    @keyframes shufflePortrait1 {{
      0%, 40% {{ transform: translate3d(0, 0, 35px) scale(1) rotate(0deg); z-index: 20; opacity: 1; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4); }}
      50%, 90% {{ transform: translate3d(36px, -15px, -35px) scale(0.92) rotate(4.5deg); z-index: 10; opacity: 0.85; box-shadow: 0 14px 28px -8px rgba(0, 0, 0, 0.25); }}
      100% {{ transform: translate3d(0, 0, 35px) scale(1) rotate(0deg); z-index: 20; opacity: 1; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4); }}
    }}

    @keyframes shufflePortrait2 {{
      0%, 40% {{ transform: translate3d(36px, -15px, -35px) scale(0.92) rotate(4.5deg); z-index: 10; opacity: 0.85; box-shadow: 0 14px 28px -8px rgba(0, 0, 0, 0.25); }}
      50%, 90% {{ transform: translate3d(0, 0, 35px) scale(1) rotate(0deg); z-index: 20; opacity: 1; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4); }}
      100% {{ transform: translate3d(36px, -15px, -35px) scale(0.92) rotate(4.5deg); z-index: 10; opacity: 0.85; box-shadow: 0 14px 28px -8px rgba(0, 0, 0, 0.25); }}
    }}

    .cards-badges-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 8px;
      margin-top: 4px;
      margin-bottom: 12px;
    }}

    .card-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 800;
      border: 1px solid rgba(226, 232, 240, 0.8);
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      cursor: pointer;
      transition: transform 0.2s ease;
    }}
    .card-badge:hover {{ transform: scale(1.04); }}

    .badge-scapia-orange {{ color: #ea580c; border-color: #fed7aa; background: #fff7ed; }}
    .badge-scapia-green {{ color: #16a34a; border-color: #bbf7d0; background: #f0fdf4; }}
    .badge-all-banks {{ color: #475569; border-color: #cbd5e1; background: #f8fafc; }}

    .privacy-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 14px;
      border-radius: 9999px;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
      font-size: 11px;
      font-weight: 700;
      line-height: 1.4;
    }}

    /* Mobile responsive card scaling */
    @media (max-width: 640px) {{
      .physical-card-portrait {{
        width: 175px;
        height: 276px;
      }}
      .card-stage-wrap {{
        height: 295px;
        max-width: 280px;
      }}
    }}
  </style>
</head>
<body>
  <div class="showcase-card">
    <div class="headline-pill">
      <span>✈️</span>
      <span>Axis Bank Scapia Editions (Portrait)</span>
    </div>
    <h2 class="title">No Statement Loaded in This Session</h2>
    <p class="subtitle">
      Upload your <b>Axis Bank (Scapia)</b>, <b>HDFC Bank (Swiggy)</b>, <b>ICICI Bank (Amazon Pay)</b>, or <b>SBI Card (SimplyCLICK)</b> statement PDF above to view your interactive Apple-style dashboard, friend EMI receipts, and cashback reconciliation.
    </p>

    <!-- 3D Portrait Card Shuffling Stage (Tap to flip) -->
    <div id="card-stage" class="card-stage-wrap" onclick="flipScapiaCards()" title="Hover to inspect • Tap to flip cards">
      <!-- Card 1: Scapia Mastercard (Orange) -->
      <div id="card-scapia-orange" class="physical-card-portrait">
        <div class="card-glare"></div>
        <div class="embossed-name">SCAPIA MASTERCARD</div>
      </div>
      <!-- Card 2: Scapia RuPay (Green) -->
      <div id="card-scapia-green" class="physical-card-portrait">
        <div class="card-glare"></div>
        <div class="embossed-name" style="color: #dcfce7;">SCAPIA RUPAY</div>
      </div>
    </div>

    <!-- Supported Card Pills -->
    <div class="cards-badges-row">
      <span class="card-badge badge-scapia-orange" onclick="flipScapiaCards()"><span>✈️</span><span>Scapia Mastercard (0% Forex & 10% Coins)</span></span>
      <span class="card-badge badge-scapia-green" onclick="flipScapiaCards()"><span>🛍️</span><span>Scapia RuPay (UPI on Credit & Lounges)</span></span>
      <span class="card-badge badge-all-banks"><span>🏛️</span><span>Auto-Detects: Swiggy HDFC • Amazon Pay ICICI • SBI SimplyCLICK</span></span>
    </div>

    <div class="privacy-pill">
      <span>🔒</span>
      <span>100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜</span>
    </div>
  </div>

  <script>
    function flipScapiaCards() {{
      const c1 = document.getElementById('card-scapia-orange');
      const c2 = document.getElementById('card-scapia-green');
      if (!c1 || !c2) return;
      const anim1 = c1.style.animation;
      const anim2 = c2.style.animation;
      c1.style.animation = anim2 || 'shufflePortrait2 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite';
      c2.style.animation = anim1 || 'shufflePortrait1 6s cubic-bezier(0.34, 1.25, 0.64, 1) infinite';
    }}
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
    # Clean Initial State: 3D Portrait Shuffling Showcase (Height 620 to ensure zero card clipping)
    components.html(get_card_shuffle_html(), height=620, scrolling=False)

# --- Friendly Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 24px; padding: 14px 12px; border-top: 1px solid rgba(226, 232, 240, 0.3); color: #64748b; font-size: 13px; font-weight: 600;">
    Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
</div>
""", unsafe_allow_html=True)
