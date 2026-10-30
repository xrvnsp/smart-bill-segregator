"""Smart Bill Segregator - Streamlit Web Application
Renders the exact, authentic, mobile-and-PC responsive web dashboard.
Auto-loads existing unlocked statements immediately with visible controls and robust PDF upload handling.
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
        border-radius: 16px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        width: 100% !important;
    }
    .uploader-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px 22px;
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
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

# Auto-discover and load existing unlocked statements from disk on first launch
if not st.session_state.statements_data:
    for folder in ["Statements_October_2026", "."]:
        if os.path.exists(folder):
            for fname in sorted(os.listdir(folder)):
                if fname.lower().endswith(".pdf"):
                    fp = os.path.join(folder, fname)
                    suc, _, rd = unlock_statements.process_statement_file(fp, ".")
                    if suc and rd.get("bank_short") and rd["bank_short"] not in st.session_state.statements_data:
                        st.session_state.statements_data[rd["bank_short"]] = rd

# --- Main Page Header & Visible Upload Card ---
with st.container():
    st.markdown("### 💳 Smart Bill Segregator")
    st.caption("Auto-segregates bank statements, friend EMIs, cashback, and regular card spends.")

    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Upload New Statement PDF(s) to Parse & Unlock:",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select HDFC / ICICI bank statement PDFs. They will be decrypted and segregated instantly."
        )

    with info_col:
        st.markdown("**🔑 Configured Passwords:**")
        icici_set = bool(stored_pwds.get("icici"))
        hdfc_set = bool(stored_pwds.get("hdfc"))
        st.markdown(f"- ICICI: {'✅ Configured' if icici_set else '⚠️ Missing'}")
        st.markdown(f"- HDFC: {'✅ Configured' if hdfc_set else '⚠️ Missing'}")
        if not icici_set or not hdfc_set:
            st.caption("Set passwords in the sidebar to auto-unlock encrypted statements.")

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

# --- Active Statements Status Bar ---
if st.session_state.statements_data:
    status_cols = st.columns([4, 1])
    with status_cols[0]:
        badge_html = " ".join([
            f'<span style="background-color: #f1f5f9; color: #334155; padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; border: 1px solid #cbd5e1; margin-right: 8px;">🏛️ {s.get("bank_name", k)} ({len(s.get("date_groups", {}))} date groups)</span>'
            for k, s in st.session_state.statements_data.items()
        ])
        st.markdown(f"<div style='margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'><span style='font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;'>Active Statements:</span> {badge_html}</div>", unsafe_allow_html=True)
    with status_cols[1]:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

# --- Render the Authentic Web Dashboard ---
dashboard_html = None

if st.session_state.statements_data:
    dashboard_path = unlock_statements.generate_modern_dashboard_html(list(st.session_state.statements_data.values()), ".")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        dashboard_html = f.read()
elif os.path.exists("Statement_Dashboard.html"):
    with open("Statement_Dashboard.html", "r", encoding="utf-8") as f:
        dashboard_html = f.read()

if dashboard_html:
    components.html(dashboard_html, height=1450, scrolling=True)
else:
    st.info("👋 Welcome to Smart Bill Segregator! Please upload your HDFC or ICICI bank statement PDF above to view your interactive dashboard.")