# 💳 Smart Bill Segregator

An Apple-inspired interactive web dashboard, Streamlit web application ([smartbills.streamlit.app](https://smartbills.streamlit.app)), and offline utility for decrypting, segregating, and reconciling password-protected Indian credit card statements (**Axis Bank Scapia**, **HDFC Bank Swiggy**, **ICICI Bank Amazon Pay**, and **SBI Card SimplyCLICK**).

> 🔒 **100% Zero-Disk Privacy**: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜

---

## ✨ Core Highlights

* 🏛️ **4 Major Credit Card Statement Formats Auto-Detected**:
  * **Axis Bank (Scapia)**: 0% forex markup travel credit card, Scapia Coins reward balance, payments/credits, and dual portrait editions (**Orange Mastercard** & **Green RuPay**).
  * **HDFC Bank (Swiggy)**: Food delivery, dining 10% cashback audit, processing fees & GST reconciliation.
  * **ICICI Bank (Amazon Pay)**: 5% unlimited shopping rewards, loan amortization & statement breakdown.
  * **SBI Card (SimplyCLICK)**: 10X reward point balances, payments/credits, no-payment-due detection, and online spends tracking.

* 📱 **Dual Mobile & PC Responsive Build**:
  * **PC Desktop**: High-resolution wide dashboard, multi-card comparison, 3-column KPI tiles, and side-by-side transaction tables.
  * **Mobile Touch**: 100% fluid touch layout, full-width cards without horizontal overflow, mobile-optimized headers, and tap-friendly buttons.
  * **PWA & Android Support**: Progressive Web App with `manifest.json` and `sw.js` for "Add to Home Screen", plus an Android Studio WebView wrapper in `android/` for native APK builds.

* 🔀 **Interactive 3D Portrait Physical Card Shuffling**:
  * **Dual Portrait Editions**: Features the official **Scapia Mastercard** (Orange) and **Scapia RuPay** (Green) cards cycling in authentic portrait 3D orientation.
  * **Hover & Tap to Flip**: Hovering pauses the animation, and tapping either card smoothly flips between the Mastercard and RuPay editions.
  * **Pristine Presentation**: Generous viewport height buffer ensuring zero card clipping on both mobile and PC.

* 🔒 **Device-Local Browser Password Vault with Instant Notifications**:
  * Passwords live strictly in your device's browser `localStorage` via a zero-height client bridge (`local_storage_bridge`).
  * 5-second persistent sidebar toast notifications inform you when saved passwords are stored or updated.
  * Includes an in-page **🔑 Quick Device Passwords** expander on the main screen for instant access on mobile.
  * Zero credentials or passwords ever touch server storage.

* 🏷️ **Unified Named Friend EMI Receipts**:
  * Consolidates multi-date loan setup charges (processing fees, 18% IGST/CGST/SGST, and cashback reversals) into individual friend cards (e.g., `🏷️ Naveen S25Edge`, `🏷️ Vasanth LG Tv`).
  * Calculates tax parent-child relationships with visual arrows (`↳ 18% IGST on Interest`).

* 📸 **1-Click Snapshot & Clipboard Image Copy (Mobile & PC)**:
  * Generates high-resolution PNG receipt snapshots with 1 click.
  * Copies directly to the OS clipboard for instant `Ctrl + V` pasting into WhatsApp, Slack, or email.

* 📊 **Google Sheets Webhook Sync**:
  * Optionally connect your personal Google Sheet Web App URL to append monthly summaries and friend EMI splits automatically.

---

## 🔑 Statement Password Patterns

Save your passwords once in the sidebar (**💾 Save Passwords on This Device**) or in the in-page Quick Vault so your browser automatically unlocks statements on upload:

| Card / Bank | Password Pattern | Example |
| :--- | :--- | :--- |
| **Axis Bank (Scapia)** | First 4 letters of Name (**UPPERCASE**) + `DDMM` of Birth | `ROHI2512` |
| **HDFC Bank (Swiggy)** | First 4 letters of Name (**UPPERCASE**) + `DDMM` of Birth | `ROHI2512` |
| **ICICI Bank (Amazon Pay)** | First 4 letters of Name (**lowercase**) + `DDMM` of Birth | `rohi2512` |
| **SBI Card (SimplyCLICK)** | Date of Birth (**DDMMYYYY**) + **Last 4 digits** of Primary Card | `150819954321` |

---

## 🚀 Quick Start

### 1. Run the Streamlit Web App (Recommended for Mobile & PC)

Double-click `run_streamlit.bat` on Windows, or run in terminal:

```bash
pip install -r requirements.txt
streamlit run app.py
```

* **Local PC & Mobile Wi-Fi**: Opens at `http://localhost:8501` (or your local IP on mobile browser).
* **Live Cloud Deployment**: Accessible at [smartbills.streamlit.app](https://smartbills.streamlit.app).

### 2. Run with Zero-Dependency Local Web Server

Double-click `run_web_server.bat` or run:

```bash
python web_server.py
```

### 3. Run the Windows Desktop GUI

Double-click `unlock_statements.pyw` for windowless desktop mode, or run:

```bash
python unlock_statements.py
```

---

## 📁 Repository Structure

```
├── app.py                     # Streamlit web app (3D portrait Scapia shuffle, zero-disk RAM architecture)
├── local_storage_bridge/      # Custom component bridging browser localStorage securely with Streamlit
├── unlock_statements.py       # Core parser (Scapia Axis, HDFC, ICICI, SBI), Apple Design HTML & desktop GUI
├── unlock_statements.pyw      # Windowless desktop launcher for Windows
├── web_server.py              # Lightweight local HTTP server for PC & mobile Wi-Fi access
├── card-facia-scapia-orange.png # Official Axis Scapia Mastercard portrait artwork (transparent cutouts)
├── card-facia-scapia-green.png  # Official Axis Scapia RuPay portrait artwork (transparent cutouts)
├── card-facia-swiggy.jpg      # Official HDFC Swiggy card artwork
├── card-facia-amazon.png      # Official Amazon Pay ICICI card artwork
├── simply-click-card-face.png # Official SBI SimplyCLICK card artwork
├── run_streamlit.bat          # 1-click Windows launcher for Streamlit
├── run_web_server.bat         # 1-click Windows launcher for local web server
├── copy_and_push_to_git.bat   # 1-click deployment & GitHub push script (excluded in .gitignore)
├── android/                   # Native Android WebView wrapper project for building mobile APK
├── manifest.json              # PWA Web App Manifest for mobile home screen installation
├── sw.js                      # Service worker for offline caching & PWA
├── requirements.txt           # Python dependencies (pypdf, cryptography, streamlit)
├── passwords.json.example     # Template for offline desktop configuration
├── .gitignore                 # Strict gitignore blocking all PDFs, credentials, and local scripts
└── README.md                  # Project documentation
```

---

## 🛡️ Security & Privacy Guardrails

1. **100% Zero-Disk Execution**: Uploaded statements are decrypted in memory (`io.BytesIO`) and purged as soon as the session closes.
2. **Client-Only Storage**: Stored passwords never cross the network to any backend server.
3. **No Accidental Leaks**: The `.gitignore` prevents `*.pdf`, `passwords.json`, `emi_names.json`, and `copy_and_push_to_git.bat` from ever being pushed to public repositories.

---

Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳