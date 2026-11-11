# 💳 Smart Bill Segregator

An Apple-inspired interactive web dashboard, Streamlit web application ([smartbills.streamlit.app](https://smartbills.streamlit.app)), and offline utility for decrypting, segregating, and reconciling password-protected Indian credit card statements (**Axis Bank Scapia**, **HDFC Bank Swiggy**, **ICICI Bank Amazon Pay**, **SBI Card SimplyCLICK**), **Salary Payslips**, **Shafana's Amazon Cashback Tracker**, and **Dr. Kayalvizhi's Personalized Duty Roster**.

> 🔒 **100% Zero-Disk Privacy**: Statements & passwords are processed strictly in RAM & browser `localStorage` — never stored on the server.

## ✨ Core Highlights

* 🏛️ **4 Major Credit Card Statement Formats Auto-Detected**:
  * **Axis Bank (Scapia)**: 0% forex markup travel credit card, Scapia Coins reward balance, payments/credits, and dual editions (**Orange Mastercard** & **Green RuPay**).
  * **HDFC Bank (Swiggy)**: Food delivery, dining 10% cashback audit, processing fees & GST reconciliation.
  * **ICICI Bank (Amazon Pay)**: 5% unlimited shopping rewards, loan amortization & statement breakdown.
  * **SBI Card (SimplyCLICK)**: 10X reward point balances, payments/credits, no-payment-due detection, and online spends tracking.

* 💼 **Salary Payslip & Leave Impact Simulator**:
  * Dedicated payroll layout (auto-unlocks using `Employee No + PAN last 4 digits`) with **1-Click Unlocked PDF Download**.
  * Pro-rata to full-month (`30-day`) salary & per-day rate engine, **Leave / LOP Impact Simulator**, and **Salary vs. Credit Card Cashflow Bridge**.

* 🎁 **Shafana's Amazon Cashback Tracker (`shafana_cashback.json` Web Sync)**:
  * Accessible anytime via a permanent **1-tap button** on the main screen (no file upload required).
  * Simple 2-card view showing **Total Bill to Pay** (after ICICI bill date) and **Cashback Balance Left**, with manual **Cashback Used (`₹`)** input and automatic cross-verification when the ICICI statement arrives.
  * Syncs only Shafana's cashback ledger across devices while keeping bank credentials 100% local.

* 🩺💖 **Dr. Kayalvizhi's Personalized Duty Roster (`kayal_duty.json`)**:
  * Dedicated **1-tap button** on the main screen (`CHC Thirunallar • 01–15 Nov 2026`) with **3 selectable themes** (**🌹 Rose & Gold**, **💜 Lavender & Blush**, **🌿 Pastel Mint & Pearl**), **Next Off Day Together** countdown, and shift care reminders.
  * Uploading any duty roster photo (with EXIF auto-rotation & 2× OCR upscaling) unlocks the personalized romantic mode (**Dr Cuteuh Pattuh**, **With Love, Saro 💖**, and live **Indian Standard Time** greeting).
  * **📲 Share Screenshot on WhatsApp**: Generates a high-resolution Retina PNG table card for the native Android Share Sheet (or clipboard on PC).
  * **📋 Copy Text (With Emojis)**: Copies clean WhatsApp-formatted text with full-color emojis (`☀️ 🌆 🌙 💤 💞`).

* 📱 **Full-Width Upload & 4-Card Responsive Bar**:
  * Full-width uploader across the top with 4 evenly distributed cards below (**Vault Active**, **Shafana's Cashback**, **Dr. Kayalvizhi**, and **Quick Device Passwords**), tuned for both desktop and **Samsung Galaxy S24 Ultra**.

* 🚀 **S24 Ultra 1-Tap GitHub Pusher (`Push_To_GitHub_S24_Ultra.html`)**:
  * Self-contained mobile web tool that embeds all updated project files and pushes directly to GitHub `main` via the GitHub API from your phone browser.

## 🔑 Password Patterns (Stored Strictly in Browser `localStorage`)

| Card / Document | Password Pattern | Example |
| :--- | :--- | :--- |
| **Axis Bank (Scapia)** | First 4 letters of Name (**UPPERCASE**) + `DDMM` | `ROHI2512` |
| **HDFC Bank (Swiggy)** | First 4 letters of Name (**UPPERCASE**) + `DDMM` | `ROHI2512` |
| **ICICI Bank (Amazon Pay)** | First 4 letters of Name (**lowercase**) + `DDMM` | `rohi2512` |
| **SBI Card (SimplyCLICK)** | Date of Birth (**DDMMYYYY**) + **Last 4 digits** of Card | `150819954321` |
| **Salary Payslip** | **Employee No** + **PAN last 4 digits** | `115000A` |

## 🚀 Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

* **Live Cloud Deployment**: [smartbills.streamlit.app](https://smartbills.streamlit.app)
* **Local Web Server**: `python web_server.py` (or `run_web_server.bat`)
* **Windows Desktop GUI**: `python unlock_statements.py` (or `unlock_statements.pyw`)

## 📁 Repository Structure

```text
├── app.py                       # Streamlit web app (full-width upload, 4-card bar, RAM processing)
├── unlock_statements.py         # Core parsers (Cards, Payslip, Shafana, Dr. Kayalvizhi) & HTML dashboard
├── unlock_statements.pyw        # Windowless desktop launcher for Windows
├── shafana_cashback.json        # Web-synced non-sensitive cashback ledger for Shafana
├── kayal_duty.json              # Web-synced duty roster for Dr. Kayalvizhi (CHC Thirunallar)
├── Push_To_GitHub_S24_Ultra.html# 1-Tap GitHub API pusher for Samsung Galaxy S24 Ultra
├── push_from_android.sh         # Termux 1-tap Git push script for Android
├── rebuild_all.py               # Auto-updates S24 Ultra Pusher commit message & rebuilds ZIP archive
├── local_storage_bridge/        # Zero-height client localStorage bridge for Streamlit
├── requirements.txt             # Python dependencies (pypdf, pytesseract, Pillow, streamlit, etc.)
├── packages.txt                 # System packages for Streamlit Cloud (tesseract-ocr)
└── README.md                    # Project documentation
```

Made with ❤️ for friends & family — because splitting bills and tracking shifts shouldn't give you a migraine 🍕💳🩺
