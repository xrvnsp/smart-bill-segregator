def get_card_shuffle_html():
    swiggy_b64 = unlock_statements.get_card_b64("card-facia-swiggy.jpg")
    amazon_b64 = unlock_statements.get_card_b64("card-facia-amazon.png")
    sbi_b64 = unlock_statements.get_card_b64("simply-click-card-face.png")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif; }}
    body {{ background: transparent; display: flex; justify-content: center; align-items: center; padding: 6px; }}
    
    .showcase-card {{
      width: 100%;
      max-width: 860px;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid rgba(226, 232, 240, 0.85);
      border-radius: 28px;
      padding: 32px 20px;
      text-align: center;
      box-shadow: 0 12px 35px -8px rgba(0, 0, 0, 0.05);
      display: flex;
      flex-direction: column;
      align-items: center;
    }}

    .headline-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 9999px;
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #334155;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 10px;
    }}

    .title {{
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }}

    .subtitle {{
      font-size: 13px;
      color: #64748b;
      max-width: 560px;
      line-height: 1.5;
      margin-bottom: 16px;
    }}

    /* 3D Physical Card Shuffling Stage */
    .card-stage-wrap {{
      perspective: 1200px;
      perspective-origin: center center;
      width: 350px;
      height: 225px;
      position: relative;
      margin: 10px auto 24px auto;
    }}

    .physical-card {{
      width: 320px;
      height: 202px;
      border-radius: 16px;
      position: absolute;
      top: 0;
      left: 15px;
      transform-style: preserve-3d;
      will-change: transform, opacity;
      cursor: pointer;
      user-select: none;
      box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.28);
      transition: transform 0.4s cubic-bezier(0.34, 1.3, 0.64, 1), box-shadow 0.3s ease;
      background-size: cover !important;
      background-position: center !important;
      background-repeat: no-repeat !important;
    }}

    .physical-card::after {{
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.25);
      pointer-events: none;
    }}

    .card-glare {{
      position: absolute;
      inset: 0;
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0.05) 50%, rgba(0,0,0,0.15) 100%);
      pointer-events: none;
    }}

    .embossed-name {{
      position: absolute;
      bottom: 14px;
      left: 18px;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      font-family: monospace;
      color: rgba(255,255,255,0.95);
      text-shadow: 0 1.5px 2px rgba(0,0,0,0.85);
      pointer-events: none;
    }}

    /* Card Shuffling 3D Loop Animation (9s total, 3s per card phase) */
    .card-swiggy {{
      background-image: url('{swiggy_b64}');
      animation: shuffleSwiggy 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}
    .card-amazon {{
      background-image: url('{amazon_b64}');
      animation: shuffleAmazon 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}
    .card-sbi {{
      background-image: url('{sbi_b64}');
      animation: shuffleSbi 9s cubic-bezier(0.34, 1.25, 0.64, 1) infinite;
    }}

    .card-stage-wrap:hover .physical-card {{
      animation-play-state: paused;
    }}

    @keyframes shuffleSwiggy {{
      0%, 28% {{
        transform: translate3d(0, 0, 40px) scale(1) rotate(0deg);
        z-index: 30;
        opacity: 1;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
      }}
      33%, 61% {{
        transform: translate3d(45px, -15px, 0px) scale(0.92) rotate(4deg);
        z-index: 20;
        opacity: 0.88;
        box-shadow: 0 16px 32px -10px rgba(0, 0, 0, 0.22);
      }}
      66%, 95% {{
        transform: translate3d(-40px, -22px, -40px) scale(0.85) rotate(-5deg);
        z-index: 10;
        opacity: 0.72;
        box-shadow: 0 10px 20px -8px rgba(0, 0, 0, 0.18);
      }}
      100% {{
        transform: translate3d(0, 0, 40px) scale(1) rotate(0deg);
        z-index: 30;
        opacity: 1;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
      }}
    }}

    @keyframes shuffleAmazon {{
      0%, 28% {{
        transform: translate3d(45px, -15px, 0px) scale(0.92) rotate(4deg);
        z-index: 20;
        opacity: 0.88;
        box-shadow: 0 16px 32px -10px rgba(0, 0, 0, 0.22);
      }}
      33%, 61% {{
        transform: translate3d(-40px, -22px, -40px) scale(0.85) rotate(-5deg);
        z-index: 10;
        opacity: 0.72;
        box-shadow: 0 10px 20px -8px rgba(0, 0, 0, 0.18);
      }}
      66%, 95% {{
        transform: translate3d(0, 0, 40px) scale(1) rotate(0deg);
        z-index: 30;
        opacity: 1;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
      }}
      100% {{
        transform: translate3d(45px, -15px, 0px) scale(0.92) rotate(4deg);
        z-index: 20;
        opacity: 0.88;
        box-shadow: 0 16px 32px -10px rgba(0, 0, 0, 0.22);
      }}
    }}

    @keyframes shuffleSbi {{
      0%, 28% {{
        transform: translate3d(-40px, -22px, -40px) scale(0.85) rotate(-5deg);
        z-index: 10;
        opacity: 0.72;
        box-shadow: 0 10px 20px -8px rgba(0, 0, 0, 0.18);
      }}
      33%, 61% {{
        transform: translate3d(0, 0, 40px) scale(1) rotate(0deg);
        z-index: 30;
        opacity: 1;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
      }}
      66%, 95% {{
        transform: translate3d(45px, -15px, 0px) scale(0.92) rotate(4deg);
        z-index: 20;
        opacity: 0.88;
        box-shadow: 0 16px 32px -10px rgba(0, 0, 0, 0.22);
      }}
      100% {{
        transform: translate3d(-40px, -22px, -40px) scale(0.85) rotate(-5deg);
        z-index: 10;
        opacity: 0.72;
        box-shadow: 0 10px 20px -8px rgba(0, 0, 0, 0.18);
      }}
    }}

    .cards-badges-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
      margin-top: 4px;
      margin-bottom: 20px;
    }}

    .card-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid rgba(226, 232, 240, 0.8);
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    .badge-hdfc {{ color: #c2410c; border-color: #fed7aa; background: #fff7ed; }}
    .badge-icici {{ color: #b45309; border-color: #fde68a; background: #fefce8; }}
    .badge-sbi {{ color: #882438; border-color: #fecdd3; background: #fff1f2; }}

    .privacy-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 9999px;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
      font-size: 12px;
      font-weight: 700;
      line-height: 1.4;
    }}
  </style>
</head>
<body>
  <div class="showcase-card">
    <div class="headline-pill">
      <span>🔀</span>
      <span>3 Credit Cards Supported & Auto-Detected</span>
    </div>
    <h2 class="title">No Statement Loaded in This Session</h2>
    <p class="subtitle">
      Upload your <b>HDFC Bank (Swiggy)</b>, <b>ICICI Bank (Amazon Pay)</b>, or <b>SBI Card (SimplyCLICK)</b> statement PDF above to view your interactive Apple-style dashboard, friend EMI receipts, and cashback reconciliation.
    </p>

    <!-- 3D Card Shuffling Animation Stage -->
    <div class="card-stage-wrap" title="Hover to pause • 3 cards cycling in 3D perspective">
      <!-- Card 1: HDFC Swiggy -->
      <div class="physical-card card-swiggy">
        <div class="card-glare"></div>
        <div class="embossed-name">SWIGGY HDFC</div>
      </div>
      <!-- Card 2: ICICI Amazon Pay -->
      <div class="physical-card card-amazon">
        <div class="card-glare"></div>
        <div class="embossed-name" style="color: #fde68a;">AMAZON PAY ICICI</div>
      </div>
      <!-- Card 3: SBI Card SimplyCLICK -->
      <div class="physical-card card-sbi">
        <div class="card-glare"></div>
        <div class="embossed-name">SBI SIMPLYCLICK</div>
      </div>
    </div>

    <!-- Supported Card Pills -->
    <div class="cards-badges-row">
      <span class="card-badge badge-hdfc"><span>🛵</span><span>Swiggy HDFC Bank</span></span>
      <span class="card-badge badge-icici"><span>🛒</span><span>Amazon Pay ICICI</span></span>
      <span class="card-badge badge-sbi"><span>💳</span><span>SBI Card SimplyCLICK</span></span>
    </div>

    <div class="privacy-pill">
      <span>🔒</span>
      <span>100% Zero-Disk Privacy: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜</span>
    </div>
  </div>
</body>
</html>"""

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

# --- Responsive Stylesheet: Tight Header Spacing & Zero Blank Gaps ---
st.markdown("""
<style>
    /* Make Streamlit header flow naturally without floating over content or creating huge voids */
    [data-testid="stHeader"], header {
        position: relative !important;
        background: transparent !important;
        height: 2.25rem !important;
    }
    .block-container {
        padding-top: 0.5rem !important;
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

# --- Initialize Private Session Passwords (Supports HDFC, ICICI & SBI SimplyCLICK) ---
if "session_passwords" not in st.session_state:
    st.session_state.session_passwords = {"icici": "", "hdfc": "", "sbi": "", "sheets_webhook_url": ""}

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
    if not st.session_state.session_passwords.get("sbi") and client_vault.get("sbi"):
        st.session_state.session_passwords["sbi"] = client_vault["sbi"]
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
            help="Lowercase name (4) + DDMM (e.g. sara3105)",
            key="input_icici_pwd"
        )
        hdfc_val = st.text_input(
            "HDFC Password",
            value=st.session_state.session_passwords.get("hdfc", ""),
            type="password",
            help="UPPERCASE name (4) + DDMM (e.g. SARA3105)",
            key="input_hdfc_pwd"
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
            st.session_state.session_passwords["icici"] = icici_val.strip()
            st.session_state.session_passwords["hdfc"] = hdfc_val.strip()
            st.session_state.session_passwords["sbi"] = sbi_val.strip()
            st.session_state.session_passwords["sheets_webhook_url"] = webhook_val.strip()
            st.session_state["pending_save_vault"] = {
                "icici": icici_val.strip(),
                "hdfc": hdfc_val.strip(),
                "sbi": sbi_val.strip(),
                "sheets_webhook_url": webhook_val.strip()
            }
            st.success("Passwords saved to this browser!")
            st.rerun()

        if st.button("🗑️ Forget Saved Passwords", use_container_width=True, help="Clear saved passwords from this browser"):
            st.session_state.session_passwords = {"icici": "", "hdfc": "", "sbi": "", "sheets_webhook_url": ""}
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

# --- Main Page Header & Visible Upload Card (Tight Spacing Under Toolbar) ---
st.markdown("<div style='margin-bottom: 4px;'><h1 style='font-size: 28px; font-weight: 800; color: inherit; margin: 0; letter-spacing: -0.02em;'>💳 Smart Bill Segregator</h1></div>", unsafe_allow_html=True)
st.caption("Auto-segregates bank statements, friend EMIs, cashback, and regular card spends.")

with st.container():
    up_col, info_col = st.columns([3, 1])

    with up_col:
        uploaded_files = st.file_uploader(
            "📁 Upload Statement PDF(s) to Unlock & Analyze (100% In-Memory):",
            type=["pdf"],
            accept_multiple_files=True,
            help="Drag and drop or select HDFC, ICICI, or SBI SimplyCLICK bank statement PDFs. Processed strictly in RAM and never saved to server disk."
        )

    with info_col:
        st.markdown("**🔑 Device Password Status:**")
        icici_set = bool(st.session_state.session_passwords.get("icici"))
        hdfc_set = bool(st.session_state.session_passwords.get("hdfc"))
        sbi_set = bool(st.session_state.session_passwords.get("sbi"))
        st.markdown(f"- ICICI: {'🟢 Active' if icici_set else '⚪ Not Set'}")
        st.markdown(f"- HDFC: {'🟢 Active' if hdfc_set else '⚪ Not Set'}")
        st.markdown(f"- SBI SimplyCLICK: {'🟢 Active' if sbi_set else '⚪ Not Set'}")
        if not icici_set or not hdfc_set or not sbi_set:
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
                    fname_low = up_file.name.lower()
                    def_idx = 0 if ("sbi" in fname_low or "simply" in fname_low) else (1 if ("hdfc" in fname_low or "swiggy" in fname_low) else (2 if ("icici" in fname_low or "amazon" in fname_low) else 0))
                    st.markdown(f"**Unlock `{up_file.name}`:**")
                    selected_bank = st.radio(
                        "Statement Bank Format:",
                        ["SBI Card (SimplyCLICK)", "HDFC Bank (Swiggy)", "ICICI Bank (Amazon Pay)"],
                        index=def_idx,
                        horizontal=True,
                        key=f"bank_choice_{up_file.name}"
                    )
                    if "SBI" in selected_bank:
                        hint_desc = "Date of Birth in DDMMYYYY + Last 4 digits of card (e.g. 150819954321)"
                        bank_key = "sbi"
                    elif "HDFC" in selected_bank:
                        hint_desc = "First 4 letters of name in UPPERCASE + DDMM (e.g. SARA3105)"
                        bank_key = "hdfc"
                    else:
                        hint_desc = "First 4 letters of name in lowercase + DDMM (e.g. sara3105)"
                        bank_key = "icici"

                    st.caption(f"🔑 Password pattern: **{hint_desc}**")
                    inline_pwd = st.text_input(f"Enter {selected_bank} password:", type="password", key=f"inp_{up_file.name}")
                    if st.form_submit_button("🔓 Unlock & Save in Browser", use_container_width=True):
                        if inline_pwd.strip():
                            st.session_state.session_passwords[bank_key] = inline_pwd.strip()
                            st.session_state["pending_save_vault"] = dict(st.session_state.session_passwords)
                            st.success(f"Password for {selected_bank} saved to browser! Unlocking...")
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
    # Clean Initial State with Default 3D Card Shuffling Animation Showcase!
    components.html(get_card_shuffle_html(), height=570, scrolling=False)

# --- Friendly Footer ---
st.markdown("""
<div style="text-align: center; margin-top: 36px; padding: 18px 16px; border-top: 1px solid rgba(226, 232, 240, 0.3); color: #64748b; font-size: 13px; font-weight: 600;">
    Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳
</div>
""", unsafe_allow_html=True)
