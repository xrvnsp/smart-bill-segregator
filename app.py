"""Smart Bill Segregator - Streamlit Web Application
Renders the exact, authentic, mobile-and-PC responsive web dashboard.
Upload-first workflow: No statement data or bill amount is displayed until you upload a PDF or choose to load saved statements.
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

# --- Responsive Stylesheet ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    iframe {
        border-radius: 20px;
        box-shadow: 0 4px 25px -3px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        width: 100% !important;
    }
    .uploader-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 20px 24px;
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)

# Load stored credentials
stored_pwds = unlock_statements.load_stored_passwords(".")

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 💳 Smart Bill Segregator")
    st.caption("Auto-segregate statements, friend EMIs, cashback, and regular expenses.")

    with st.expander("🔑 Bank Passwords & Sync Settings", expanded=False):
        icici_input = st.text_input("ICICI Password", value=stored_pwds.get("icici", ""), type="password", help="Lowercase name (4) + DDMM")
        hdfc_input = st.text_input("HDFC Password", value=stored_pwds.get("hdfc", ""), type="password", help="UPPERCASE name (4) + DDMM")
        webhook_input = st.text_input("Google Sheets Web App URL", value=stored_pwds.get("sheets_webhook_url", ""))
        if st.button("💾 Save Settings", use_container_width=True):
            unlock_statements.save_stored_passwords(hdfc_input, icici_input, webhook_input, ".")
            st.success("Passwords saved locally!")
            st.rerun()

    st.link_button(
        "📋 Copy Google Sheet Template",
        unlock_statements.GOOGLE_SHEET_TEMPLATE_URL,
        use_container_width=True
    )
    st.markdown("---")
    st.caption("🔒 All statements are unlocked 100% locally on your computer.")

# --- Session State Management ---
if "statements_data" not in st.session_state:
    st.session_state.statements_data = {}

# --- Main Page Header & Visible Upload Card ---
st.markdown("### 💳 Smart Bill Segregator")
st.caption("Auto-segregates bank statements, friend EMIs, cashback, and regular card spends.")

with st.container():
    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Upload Statement PDF(s) to Unlock & Analyze:",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select HDFC / ICICI bank statement PDFs. Decryption happens locally."
        )

    with info_col:
        st.markdown("**🔑 Passwords Status:**")
        icici_set = bool(stored_pwds.get("icici"))
        hdfc_set = bool(stored_pwds.get("hdfc"))
        st.markdown(f"- ICICI: {'✅ Configured' if icici_set else '⚠️ Missing'}")
        st.markdown(f"- HDFC: {'✅ Configured' if hdfc_set else '⚠️ Missing'}")
        if not icici_set or not hdfc_set:
            st.caption("Configure passwords in the sidebar to decrypt password-locked PDFs.")

# --- Process Uploaded Files ---
if uploaded_files:
    temp_dir = "temp_uploaded_statements"
    os.makedirs(temp_dir, exist_ok=True)
    for up_file in uploaded_files:
        temp_path = os.path.join(temp_dir, up_file.name)
        with open(temp_path, "wb") as f:
            f.write(up_file.getbuffer())
        success, msg, rdata = unlock_statements.process_statement_file(temp_path, ".")
        if success:
            st.session_state.statements_data[rdata["bank_short"]] = rdata
            st.success(f"✅ Successfully unlocked & parsed: {up_file.name} ({rdata.get('bank_name')}) — {len(rdata.get('date_groups', {}))} date groups found")
        else:
            st.error(f"⚠️ {up_file.name}: {msg}")
            if "password" in msg.lower():
                with st.form(key=f"pwd_unlock_{up_file.name}"):
                    st.markdown(f"**Unlock `{up_file.name}` directly:**")
                    inline_pwd = st.text_input("Enter statement password:", type="password", key=f"inp_{up_file.name}")
                    if st.form_submit_button("🔓 Save Password & Unlock PDF"):
                        if inline_pwd.strip():
                            if "icici" in up_file.name.lower() or "amazon" in up_file.name.lower():
                                unlock_statements.save_stored_passwords(stored_pwds.get("hdfc", ""), inline_pwd.strip(), stored_pwds.get("sheets_webhook_url", ""), ".")
                            else:
                                unlock_statements.save_stored_passwords(inline_pwd.strip(), stored_pwds.get("icici", ""), stored_pwds.get("sheets_webhook_url", ""), ".")
                            st.success("Password saved! Refreshing...")
                            st.rerun()

# --- Active Statements Controls & Clear State ---
if st.session_state.statements_data:
    status_cols = st.columns([3, 1, 1])
    with status_cols[0]:
        badge_html = " ".join([
            f'<span style="background-color: #f1f5f9; color: #334155; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 800; border: 1px solid #cbd5e1; margin-right: 8px;">🏛️ {s.get("bank_name", k)} ({len(s.get("date_groups", {}))} date groups)</span>'
            for k, s in st.session_state.statements_data.items()
        ])
        st.markdown(f"<div style='margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'><span style='font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;'>Active Statements:</span> {badge_html}</div>", unsafe_allow_html=True)
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
    <div style="background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 24px; padding: 48px 32px; border: 1px solid #e2e8f0; text-align: center; margin-top: 16px; box-shadow: 0 10px 30px -5px rgba(0,0,0,0.03);">
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
                    suc, _, rd = unlock_statements.process_statement_file(fp, ".")
                    if suc and rd.get("bank_short") and rd["bank_short"] not in loaded:
                        loaded[rd["bank_short"]] = rd
            if loaded:
                st.session_state.statements_data = loaded
                st.rerun()
            else:
                st.warning("No valid statements found in Statements_October_2026.")
        st.markdown("</div>", unsafe_allow_html=True)