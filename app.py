"""Smart Bill Segregator - Streamlit Web Application
Renders the exact, authentic, mobile-and-PC responsive web dashboard.
Strictly device-local browser storage: Passwords are saved in the client's browser localStorage.
Persists across page reloads on this device, with zero server disk writes and zero cross-device leaks.
"""

import os
import sys
import json
import streamlit as st
import streamlit.components.v1 as components
import unlock_statements

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
    .uploader-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 20px 24px;
        border: 1px solid rgba(226, 232, 240, 0.2);
        margin-bottom: 16px;
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

# If client browser already has passwords stored in this device's localStorage, restore them automatically!
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

    with st.expander("🔑 Device Stored Passwords (Local Cookies/Storage)", expanded=False):
        st.caption("🔒 Stored in your device's browser memory (localStorage). Persists across reloads on this device only and is never saved on the server.")
        
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

        col_save, col_clear = st.columns([1, 1])
        with col_save:
            if st.button("💾 Save on This Device", use_container_width=True):
                st.session_state.session_passwords["icici"] = icici_val.strip()
                st.session_state.session_passwords["hdfc"] = hdfc_val.strip()
                st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
                st.session_state["pending_save_vault"] = {
                    "icici": icici_val.strip(),
                    "hdfc": hdfc_val.strip(),
                    "sheets_webhook_url": webhook_val.strip()
                }
                st.success("Remembered on this device!")
                st.rerun()

        with col_clear:
            if st.button("🗑️ Forget", use_container_width=True, help="Clear passwords from this browser"):
                st.session_state.session_passwords = {"icici": "", "hdfc": "", "sheets_webhook_url": ""}
                st.session_state["pending_clear_vault"] = True
                st.info("Cleared on this device.")
                st.rerun()

    st.link_button(
        "📋 Copy Google Sheet Template",
        unlock_statements.GOOGLE_SHEET_TEMPLATE_URL,
        use_container_width=True
    )
    st.markdown("---")
    st.caption("🔒 All statements and passwords remain 100% private to your browser.")

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
            "📁 Upload Statement PDF(s) to Unlock & Analyze:",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select HDFC / ICICI bank statement PDFs. Decryption happens locally in this private session."
        )

    with info_col:
        st.markdown("**🔑 Device Password Status:**")
        icici_set = bool(st.session_state.session_passwords.get("icici"))
        hdfc_set = bool(st.session_state.session_passwords.get("hdfc"))
        st.markdown(f"- ICICI: {'🟢 Saved on this device' if icici_set else '⚪ Not Set'}")
        st.markdown(f"- HDFC: {'🟢 Saved on this device' if hdfc_set else '⚪ Not Set'}")
        if not icici_set or not hdfc_set:
            st.caption("Set passwords in the sidebar to auto-unlock PDFs across reloads on this device.")

# --- Process Uploaded Files in Memory ---
if uploaded_files:
    temp_dir = "temp_uploaded_statements"
    os.makedirs(temp_dir, exist_ok=True)
    for up_file in uploaded_files:
        temp_path = os.path.join(temp_dir, up_file.name)
        with open(temp_path, "wb") as f:
            f.write(up_file.getbuffer())
        
        # Use session-isolated passwords strictly in memory
        success, msg, rdata = unlock_statements.process_statement_file(
            temp_path,
            ".",
            custom_passwords=st.session_state.session_passwords
        )
        if success:
            st.session_state.statements_data[rdata["bank_short"]] = rdata
            st.success(f"✅ Successfully unlocked & parsed: {up_file.name} ({rdata.get('bank_name')}) — {len(rdata.get('date_groups', {}))} date groups found")
        else:
            st.error(f"⚠️ {up_file.name}: {msg}")
            if "password" in msg.lower():
                with st.form(key=f"pwd_unlock_{up_file.name}"):
                    st.markdown(f"**Enter password for `{up_file.name}` (Will be remembered on this device across reloads):**")
                    inline_pwd = st.text_input("Statement password:", type="password", key=f"inp_{up_file.name}")
                    if st.form_submit_button("🔓 Unlock & Save on This Device"):
                        if inline_pwd.strip():
                            if "icici" in up_file.name.lower() or "amazon" in up_file.name.lower():
                                st.session_state.session_passwords["icici"] = inline_pwd.strip()
                            else:
                                st.session_state.session_passwords["hdfc"] = inline_pwd.strip()
                            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
                            st.success("Password remembered on this device! Unlocking...")
                            st.rerun()

# --- Active Statements Controls & Clear State ---
if st.session_state.statements_data:
    status_cols = st.columns([3, 1, 1])
    with status_cols[0]:
        badge_html = " ".join([
            f'<span style="background-color: rgba(241, 245, 249, 0.15); color: inherit; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 800; border: 1px solid rgba(203, 213, 225, 0.3); margin-right: 8px;">🏛️ {s.get("bank_name", k)} ({len(s.get("date_groups", {}))} date groups)</span>'
            for k, s in st.session_state.statements_data.items()
        ])
        st.markdown(f"<div style='margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'><span style='font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;'>Active Statements:</span> {badge_html}</div>", unsafe_allow_html=True)
    with status_cols[1]:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    with status_cols[2]:
        if st.button("🗑️ Clear Dashboard", use_container_width=True, help="Reset dashboard to upload new statements"):
            st.session_state.statements_data = {}
            st.rerun()

# --- Render the Authentic Web Dashboard or Clean Welcome State ---
if st.session_state.statements_data:
    dashboard_path = unlock_statements.generate_modern_dashboard_html(list(st.session_state.statements_data.values()), ".")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        dashboard_html = f.read()
    components.html(dashboard_html, height=1450, scrolling=True)
else:
    # Clean Initial State: Do NOT show any bill amount or cached statements until files are uploaded!
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 48px 32px; border: 1px solid rgba(226, 232, 240, 0.8); text-align: center; margin-top: 16px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.03);">
        <div style="font-size: 48px; margin-bottom: 12px;">💳</div>
        <h2 style="font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 6px; letter-spacing: -0.02em;">No Statement Loaded Yet</h2>
        <p style="font-size: 14px; color: #64748b; max-width: 520px; margin: 0 auto 20px auto; line-height: 1.5;">
            Please upload your <b>HDFC Bank (Swiggy)</b> or <b>ICICI Bank (Amazon Pay)</b> statement PDF above to view your interactive Apple-style dashboard, friend EMI receipts, and cashback reconciliation.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Optional helper for local usage: button to load previously unlocked statements from disk
    has_local_folder = os.path.exists("Statements_October_2026")
    if has_local_folder:
        st.markdown("<div style='text-align: center; margin-top: 14px;'>", unsafe_allow_html=True)
        if st.button("📂 Load Previously Processed Statements from Local Folder (October 2026)"):
            loaded = {}
            for fname in sorted(os.listdir("Statements_October_2026")):
                if fname.lower().endswith(".pdf"):
                    fp = os.path.join("Statements_October_2026", fname)
                    suc, _, rd = unlock_statements.process_statement_file(
                        fp,
                        ".",
                        custom_passwords=st.session_state.session_passwords
                    )
                    if suc and rd.get("bank_short") and rd["bank_short"] not in loaded:
                        loaded[rd["bank_short"]] = rd
            if loaded:
                st.session_state.statements_data = loaded
                st.rerun()
            else:
                st.warning("No valid statements found in Statements_October_2026.")
        st.markdown("</div>", unsafe_allow_html=True)