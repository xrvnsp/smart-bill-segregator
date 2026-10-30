# 💳 Smart Bill Segregator

An Apple-inspired interactive web dashboard, Streamlit web app ([smartbills.streamlit.app](https://smartbills.streamlit.app)), and desktop tool for decrypting, analyzing, and segregating password-protected Indian bank credit card statements (**HDFC Bank Swiggy** & **ICICI Bank Amazon Pay**).

> 🔒 **100% Zero-Disk Privacy**: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜

## ✨ Core Features

* 🍎 **Apple Design System UI & 3D Interactive Cards**: Built with frosted glass surfaces (`backdrop-filter: blur(24px)`), optical typography, capsule segmented controls, and interactive 3D physical credit cards (Swiggy HDFC & Amazon Pay ICICI) with pointer-tracked tilt and specular glare.

* 🔒 **Zero-Disk In-Memory Architecture**: Uploaded PDFs are decrypted and parsed 100% in RAM (`io.BytesIO`) within your isolated browser session. Zero files or statements are ever written to server storage.

* 🍪 **Device-Local Browser Password Vault**: Passwords are saved strictly in your own device's browser `localStorage` (`local_storage_bridge`) so they persist across reloads on your machine without ever touching a server disk or leaking across devices.

* 🏷️ **Unified Named Friend EMI Receipts**: Consolidates multi-date loan setup charges (processing fees, IGST/CGST/SGST, and cashback reversals) and monthly installments into standalone cards labeled with your friend's nickname (e.g., `🏷️ Naveen S25Edge`, `🏷️ Vasanth LG Tv`).

* 🎨 **Automated Tax Inheritance & Arrow Linking**: Automatically computes 18% GST relationships and links tax rows directly beneath their parent Interest (Indigo theme) or Processing Fee (Amber theme) with calculated descriptions (`↳ 18% IGST on Interest`).

* 📲 **1-Click WhatsApp Receipt Sharing & Clipboard Image Copy**: Generates a high-resolution HTML5 2D Canvas receipt snapshot with evenly spread 3-column KPI tiles, copies the PNG image directly to your clipboard for instant `Ctrl + V` pasting in WhatsApp, and pre-fills the itemized message.

* 🟢 **Payment Status Tracker ("Paid / Pending")**: Toggle each friend's installment receipt between Paid and Pending with live **Collected vs. Pending** reimbursement totals.

* 🌐 **Consolidated Multi-Bank View & Category Filters**: Merge multiple credit card statements chronologically or filter with one click between **🔘 All Activity**, **🏷️ EMI Receipts Only**, **💳 Regular Card Spends**, and **⚡ Pre-EMI & Credits**.

* 🎁 **Cashback & Rewards Reconciler**: Audits earned cashback against bank EMI conversion reversals to show your true net cashback.

* 📊 **Google Sheets Multi-Month Sync**: Optionally connect your own Google Sheet Web App URL to log monthly summaries and friend EMI splits.

## 🚀 Quick Start

### 1. Clone the Repository

```
git clone https://github.com/xrvnsp/smart-bill-segregator.git
cd smart-bill-segregator


```

### 2. Install Dependencies

```
pip install -r requirements.txt


```

### 3. Run the App

#### Option A: Streamlit Web App (PC & Mobile) — *Recommended*

Double-click `run_streamlit.bat` on Windows, or run:

```
streamlit run app.py


```

* **Local PC**: Opens at `http://localhost:8501`.

* **Live Cloud App**: Try it directly at <https://smartbills.streamlit.app>.

#### Option B: Zero-Dependency Local Web Server

Double-click `run_web_server.bat` or run:

```
python web_server.py


```

#### Option C: Desktop GUI Launcher (Windows)

```
python unlock_statements.py


```

## 🔑 Statement Password Formats

Save your passwords once in the sidebar (**💾 Save Passwords on This Device**) so your browser remembers them across reloads:

* **ICICI Bank (Amazon Pay)**: First 4 letters of your name in **lowercase** + `DDMM` of birth (e.g., `sara3105`).

* **HDFC Bank (Swiggy)**: First 4 letters of your name in **UPPERCASE** + `DDMM` of birth (e.g., `SARA3105`).

## 📁 Project Structure

```
├── app.py                   # Streamlit web app (100% in-RAM processing & device-local storage)
├── local_storage_bridge/    # Custom component bridging browser localStorage with Streamlit
├── unlock_statements.py     # Core statement parser, Apple Design HTML generator & desktop GUI
├── unlock_statements.pyw    # Windowless desktop launcher for Windows
├── web_server.py            # Lightweight local HTTP server for PC & mobile Wi-Fi access
├── card-facia-swiggy.jpg    # Official HDFC Swiggy card artwork
├── card-facia-amazon.png    # Official Amazon Pay ICICI card artwork
├── run_streamlit.bat        # 1-click Windows launcher for Streamlit
├── run_web_server.bat       # 1-click Windows launcher for local web server
├── copy_and_push_to_git.bat # 1-click script to sync files to Drive H: & push to GitHub
├── android/                 # Native Android WebView wrapper project
├── manifest.json            # PWA manifest for mobile home screen installation
├── sw.js                    # Service worker for PWA support
├── requirements.txt         # Python dependencies (pypdf, cryptography, streamlit)
├── passwords.json.example   # Example template for offline desktop configuration
├── .gitignore               # Blocks all PDFs, credentials, and personal artifacts from Git
└── README.md                # Project documentation


```

## 🔒 Security & Privacy

* **100% Zero-Disk Privacy**: Statements are processed in RAM & never stored on the server — also I don't have money to buy a server 😜

* **Client-Only Password Persistence**: Your statement passwords live exclusively in your device's browser `localStorage` and are never written to any server file.

* **Strict Git Exclusions**: `.gitignore` blocks `*.pdf`, `passwords.json`, `emi_names.json`, and `Statement_Dashboard.html` from ever being committed.

## ❤️ Footer

**Made with ❤️ for friends — because splitting EMIs shouldn't ruin friendships (or give you a migraine) 🍕💳**