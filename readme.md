# 💳 Smart Bill Segregator

A modern desktop application, interactive web dashboard, and mobile-friendly Streamlit web app for decrypting, analyzing, and segregating password-protected Indian bank credit card statements (**HDFC Bank** & **ICICI Bank / Amazon Pay**).

## ✨ Core Features

* 🔐 **One-Time Local Password Vault**: Configure statement passwords once via an interactive GUI modal. Passwords are saved locally in `passwords.json` and strictly excluded from Git commits via `.gitignore`.

* 🏛️ **Multi-Bank Auto-Segregation**: Automatically detects whether a statement belongs to **HDFC Bank** or **ICICI Bank (Amazon Pay)**, decrypts it, and saves an unlocked copy.

* 📁 **Unified Month Storage**: Consolidates statements for both banks into a standardized folder (e.g., `Statements_October_2026/`).

* 💰 **Exact Bill & Due Date Extraction**: Accurately extracts the real **Total Bill to be Paid**, **Minimum Due**, and **Payment Due Date** directly from statement headers.

* 🏷️ **Unified Named EMI Receipts**: Consolidates multi-date loan setup fees (processing fee, GST, cashback reversals) and monthly installments into distinct standalone cards labeled with your custom nickname (e.g. `🏷️ Vasanth LG Tv`, `🏷️ Naveen S25Edge`).

* 🟢 **Payment Status Tracker ("Paid / Pending")**: Mark each friend's receipt as Paid or Pending with a single click (`🟡 Mark as Paid` ↔ `🟢 Paid on Oct 29`), complete with live **Collected vs. Pending** reimbursement KPI totals.

* 🎁 **Cashback & Rewards Accuracy Reconciler**: Audits statement rewards against official bank rules (HDFC 10% Swiggy, 5% partner merchants, and 1% EMI reversals; ICICI 5% Prime and 2% recharges), calculating your **Net Cashback Earned**.

* 🔍 **EMI True Cost & Hidden Charges Calculator**: Audits the true financial cost of each loan by comparing original cash price against total repayments, bank interest charged, processing fees, GST, and true markup percentage.

* 📊 **Continuous Multi-Month Google Sheets Sync**: Connect to a master Google Sheet template that maintains all past, present, and future months for both cards in one place. Includes a **☁️ Sync to Google Sheets** button that appends billing cycles and friend reimbursements automatically via an Apps Script Web App without requiring Google Cloud API keys.

* 📲 **WhatsApp 1-Click Receipt Sharing & Clipboard Image Copy**: Enter your contact's 10-digit Indian mobile number (auto-prefixed with `+91`). Clicking **📲 Share WhatsApp** copies the high-resolution receipt image directly to your clipboard (ready for instant `Ctrl + V` pasting into WhatsApp), copies the text breakdown, and downloads the PNG card.

* 📸 **Native HTML5 2D Canvas Snapshot**: Automatically renders and downloads a pixel-perfect, high-resolution PNG receipt card snapshot with evenly spread 3-column KPI tiles and color-matched tax inheritance highlighting.

* 🌐 **Mobile & PC Streamlit Web App (`app.py`)**: Run an interactive web application accessible on both desktop PCs and mobile smartphones via local Wi-Fi or deployable for free on Streamlit Community Cloud.

* 📱 **Android App & PWA Ready**: Install directly on any Android smartphone with 1-click via PWA ("Add to Home screen"), compile a native `.apk` using the provided Android Studio project in `android/`, or run locally using Pydroid 3 / Termux.

* 📅 **Date-Wise Subtotal Segregation**: Groups non-loan transactions chronologically and calculates accurate daily charge subtotals.

* 🖨️ **Print & Save to PDF**: Browser print stylesheets preserve exact background colors (`#faf5ff`), purple receipt headers, and badge styling.

* 🗑️ **1-Click Persistent Month Deletion**: Delete unlocked statement folders and generated files with a single click and confirmation dialog.

* 🪟 **Windowless Execution (`.pyw` & `.py`)**: Automatically hides the black command prompt console window on Windows upon launch.

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/xrvnsp/smart-bill-segregator.git
cd smart-bill-segregator
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Choose How to Run

#### Option A: Streamlit Web App (Mobile & PC) — *Recommended*

Double-click `run_streamlit.bat` directly on Windows, or launch from terminal:

```bash
streamlit run app.py
```

* **On your PC**: Opens automatically in your browser at `http://localhost:8501`.
* **On your Phone**: Connect your phone to the same Wi-Fi network and open the `Network URL: http://<your-pc-ip>:8501` displayed in the terminal!
* **Cloud Hosting**: Deploy directly on [Streamlit Community Cloud](https://share.streamlit.io) for a permanent, public HTTPS link accessible from any phone worldwide.

#### Option B: Desktop GUI Launcher (Windows)

Double-click `unlock_statements.pyw` (or `unlock_statements.py`) on Windows:

```bash
python unlock_statements.py
```

*(The black console window is automatically hidden upon launch on Windows).*

### 4. Configure Statement Passwords & Sheets Sync

Click the **🔑 Configure Passwords & Sync** button in the desktop app (or sidebar in the Streamlit app) to configure your settings:

* **ICICI Bank**: First 4 letters of name in lowercase + Date & Month of birth (`DDMM`)
* **HDFC Bank**: First 4 letters of name in UPPERCASE + Date & Month of birth (`DDMM`)
* **Google Sheets Web App URL (Optional)**: Paste your deployed Google Apps Script URL to enable 1-click cloud sync.

All credentials and webhook URLs are stored locally in `passwords.json` and are strictly ignored by `.gitignore`.

### 5. (Optional) Connect to Master Google Sheet

1. **Get the Template**: Open and click **[Make a Copy of the Official Multi-Month Google Sheet Template](https://docs.google.com/spreadsheets/d/1j2xafoAYKAp_fnfomK59HDsXGArd_-gMKpwWnDesDAc/copy)**.
2. **Deploy Apps Script Webhook**: In your copied sheet, open **Extensions** > **Apps Script**, paste the webhook code, and deploy as a Web App (Access: *Anyone*).
3. **Save Web App URL**: In the app settings, paste the copied Web App URL, and click **💾 Save Settings**.
4. **1-Click Sync**: Whenever you decrypt your monthly statements, click **☁️ Sync to Google Sheets** to append the cycle directly to your master sheet!

## 📱 Android App Usage

You can use Smart Bill Segregator on your Android device in 3 ways (see `android/README_ANDROID.md` for full details):

1. **Streamlit Web App**: Run `streamlit run app.py` on your computer and open the Network URL on your phone browser, or host for free on Streamlit Community Cloud.
2. **Progressive Web App (PWA)**: Open `Statement_Dashboard.html` in Chrome/Brave on your phone and tap **"Add to Home screen"** / **"Install app"** for a standalone, full-screen mobile app experience.
3. **Native Android APK (`.apk`)**: Open the `android/` project folder in **Android Studio** and click **Build APK** to generate an installable `app-debug.apk`.
4. **Python on Android (Pydroid 3 / Termux)**: Run `python unlock_statements.py` directly on your Android phone using Pydroid 3 from Google Play Store or Termux.

## 📁 Project Structure

```text
├── app.py                   # Streamlit web app (fully responsive for mobile and desktop PC)
├── run_streamlit.bat        # 1-click Streamlit web app launcher for Windows
├── unlock_statements.py     # Main application (desktop GUI & web dashboard generator)
├── unlock_statements.pyw    # Windowless desktop launcher
├── Statement_Dashboard.html # Standalone interactive HTML5 dashboard & receipt generator
├── android/                 # Turnkey Android Studio project (MainActivity.kt, AndroidManifest.xml)
├── manifest.json            # Web App manifest for 1-click Android PWA installation
├── sw.js                    # Service worker for offline caching on Android
├── requirements.txt         # Required Python packages (pypdf, cryptography, streamlit)
├── passwords.json.example   # Template credential & webhook configuration
├── .gitignore               # Strict exclusion of sensitive passwords & PDFs
└── README.md                # Project documentation
```

## 🔒 Security & Privacy

* All PDF unlocking, decryption, and text analysis happen **100% locally on your computer / device**.
* No financial statements, account numbers, transactions, or passwords are ever transmitted over the network.
* `.gitignore` is pre-configured to strictly exclude `*.pdf`, `passwords.json`, `emi_names.json`, and `Statements_*/` directories from being committed to Git.

## 📄 License

This project is licensed under the MIT License.