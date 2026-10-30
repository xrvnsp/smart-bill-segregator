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
import json
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

# --- Page Configuration ---
st.set_page_config(
    page_title="Smart Bill Segregator",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Responsive Stylesheet: Prevents Header Clipping & Theme Adaptation ---
st.markdown("""
<style>
    /* Prevent Streamlit header from obscuring title and content */
    [data-testid="stHeader"], header {
        background: transparent !important;
    }
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    iframe {
        border-radius: 20px;
        box-shadow: 0 4px 25px -3px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Private Session Passwords ---
if "session_passwords" not in st.session_state:
    st.session_state.session_passwords = {"icici": "", "hdfc": "", "sheets_webhook_url": ""}

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

# If client browser already has passwords stored in this device's localStorage, restore them automatically
if client_vault and isinstance(client_vault, dict):
    if not st.session_state.session_passwords.get("icici") and client_vault.get("icici"):
        st.session_state.session_passwords["icici"] = client_vault["icici"]
    if not st.session_state.session_passwords.get("hdfc") and client_vault.get("hdfc"):
        st.session_state.session_passwords["hdfc"] = client_vault["hdfc"]
    if not st.session_state.session_passwords.get("sheets_webhook_url") and client_vault.get("sheets_webhook_url"):
        st.session_state.session_passwords["sheets_webhook_url"] = client_vault["sheets_webhook_url"]

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 💳 Smart Bill Segregator")
    st.caption("Auto-segregate statements, friend EMIs, cashback, and regular expenses.")

    with st.expander("🔑 Device Stored Passwords", expanded=True):
        st.caption("🔒 Stored strictly in your browser's local storage on this device. Never saved on any server.")
        
        icici_val = st.text_input(
            "ICICI Password",
            value=st.session_state.session_passwords.get("icici", ""),
            type="password",
            help="Lowercase name (4) + DDMM",
            key="input_icici_pwd"
        )
        hdfc_val = st.text_input(
            "HDFC Password",
            value=st.session_state.session_passwords.get("hdfc", ""),
            type="password",
            help="UPPERCASE name (4) + DDMM",
            key="input_hdfc_pwd"
        )
        webhook_val = st.text_input(
            "Google Sheets Web App URL",
            value=st.session_state.session_passwords.get("sheets_webhook_url", ""),
            key="input_webhook_url"
        )

        # Stacked full-width buttons so text is 100% readable without truncation!
        if st.button("💾 Save Passwords on This Device", use_container_width=True, type="primary"):
            st.session_state.session_passwords["icici"] = icici_val.strip()
            st.session_state.session_passwords["hdfc"] = hdfc_val.strip()
            st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
            st.session_state["pending_save_vault"] = {
                "icici": icici_val.strip(),
                "hdfc": hdfc_val.strip(),
                "sheets_webhook_url": webhook_val.strip()
            }
            st.success("Passwords saved to this browser!")
            st.rerun()

        if st.button("🗑️ Forget Saved Passwords", use_container_width=True, help="Clear saved passwords from this browser"):
            st.session_state.session_passwords = {"icici": "", "hdfc": "", "sheets_webhook_url": ""}
            st.session_state["pending_clear_vault"] = True
            st.info("Cleared passwords from this browser.")
            st.rerun()

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

# --- Main Page Header & Visible Upload Card ---
st.markdown("<div style='margin-bottom: 8px;'><h1 style='font-size: 28px; font-weight: 800; color: inherit; margin: 0; letter-spacing: -0.02em;'>💳 Smart Bill Segregator</h1></div>", unsafe_allow_html=True)
st.caption("Auto-segregates bank statements, friend EMIs, cashback, and regular card spends.")

with st.container():
    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Upload Statement PDF(s) to Unlock & Analyze (100% In-Memory):",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select HDFC / ICICI bank statement PDFs. Processed strictly in RAM and never saved to server disk."
        )

    with info_col:
        st.markdown("**🔑 Device Password Status:**")
        icici_set = bool(st.session_state.session_passwords.get("icici"))
        hdfc_set = bool(st.session_state.session_passwords.get("hdfc"))
        st.markdown(f"- ICICI: {'🟢 Saved in Browser' if icici_set else '⚪ Not Set'}")
        st.markdown(f"- HDFC: {'🟢 Saved in Browser' if hdfc_set else '⚪ Not Set'}")
        if not icici_set or not hdfc_set:
            st.caption("Save passwords in the sidebar to auto-unlock PDFs on this device.")

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
                    st.markdown(f"**Enter password for `{up_file.name}` (Saved only in your browser):**")
                    inline_pwd = st.text_input("Statement password:", type="password", key=f"inp_{up_file.name}")
                    if st.form_submit_button("🔓 Unlock & Save in Browser", use_container_width=True):
                        if inline_pwd.strip():
                            if "icici" in up_file.name.lower() or "amazon" in up_file.name.lower():
                                st.session_state.session_passwords["icici"] = inline_pwd.strip()
                            else:
                                st.session_state.session_passwords["hdfc"] = inline_pwd.strip()
                            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
                            st.success("Password saved to browser! Unlocking...")
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

# --- Render the Authentic Web Dashboard Strictly in RAM ---
if st.session_state.statements_data:
    dashboard_html = unlock_statements.generate_modern_dashboard_html(
        list(st.session_state.statements_data.values()),
        output_dir=".",
        write_to_disk=False
    )
    components.html(dashboard_html, height=1450, scrolling=True)
else:
    # Clean Initial State: Zero cached files or disk loaders!
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 48px 32px; border: 1px solid rgba(226, 232, 240, 0.8); text-align: center; margin-top: 16px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.03);">
        <div style="font-size: 48px; margin-bottom: 12px;">💳</div>
        <h2 style="font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 6px; letter-spacing: -0.02em;">No Statement Loaded in This Session</h2>
        <p style="font-size: 14px; color: #64748b; max-width: 520px; margin: 0 auto 12px auto; line-height: 1.5;">
            Upload your <b>HDFC Bank (Swiggy)</b> or <b>ICICI Bank (Amazon Pay)</b> statement PDF above to view your interactive Apple-style dashboard, friend EMI receipts, and cashback reconciliation.
        </p>
        <div style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 9999px; background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; font-size: 12px; font-weight: 700;">
            <span>🔒</span>
            <span>100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Friendly Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 36px; padding: 18px 16px; border-top: 1px solid rgba(226, 232, 240, 0.5); color: #64748b; font-size: 13px; font-weight: 600;">
    Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
</div>
""", unsafe_allow_html=True)
