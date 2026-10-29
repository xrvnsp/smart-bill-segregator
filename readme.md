# 💳 Smart Bill Segregator

A modern desktop application and interactive web dashboard for decrypting, analyzing, and segregating password-protected Indian bank credit card statements (**HDFC Bank** & **ICICI Bank / Amazon Pay**).






## ✨ Core Features

* 🔐 **One-Time Local Password Vault**: Configure statement passwords once via an interactive GUI modal. Passwords are saved locally in `passwords.json` and strictly excluded from Git commits via `.gitignore`.
* 🏛️ **Multi-Bank Auto-Segregation**: Automatically detects whether a statement belongs to **HDFC Bank** or **ICICI Bank (Amazon Pay)**, decrypts it, and saves an unlocked copy.
* 📁 **Unified Month Storage**: Consolidates statements for both banks into a standardized folder (e.g., `Statements_October_2026/`).
* 💰 **Exact Bill & Due Date Extraction**: Accurately extracts the real **Total Bill to be Paid**, **Minimum Due**, and **Payment Due Date** directly from statement headers.
* 🏷️ **Unified Named EMI Receipts**: Consolidates multi-date loan setup fees (processing fee, GST, cashback reversals) and monthly installments into a single master card labeled with your custom nickname (e.g. `🏷️ Vasanth LG Tv`, `🏷️ Naveen S25Edge`).
* 🟢 **Payment Status Tracker ("Paid / Pending")**: Mark each friend's receipt as Paid or Pending with a single click (`🟡 Mark as Paid` ↔ `🟢 Paid on Oct 29`), complete with live **Collected vs. Pending** reimbursement KPI totals at the top of the dashboard.
* 🎁 **Cashback & Rewards Accuracy Reconciler**: Audits statement rewards against official bank rules (HDFC 10% Swiggy, 5% partner merchants, and 1% EMI reversals; ICICI 5% Prime and 2% recharges), calculating your **Net Cashback Earned**.
* 🔍 **EMI True Cost & Hidden Charges Calculator**: Audits the true financial cost of each loan by comparing original cash price against total repayments, bank interest charged, processing fees, GST, and true markup percentage.
* 📲 **WhatsApp 1-Click Receipt Sharing**: Enter your contact's 10-digit Indian mobile number (auto-prefixed with `+91`). Clicking **📲 Share WhatsApp** launches a direct chat with an itemized breakdown and an encouraging progress greeting (*"Hi Naveen! Only 8 more to go 😊👍"*).
* 📸 **Native HTML5 2D Canvas Snapshot**: Automatically renders and downloads a pixel-perfect, high-resolution PNG receipt card snapshot with centered badge typography for drag-and-drop sharing.
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

### 3. Launch the Application
Double-click `unlock_statements.pyw` (or `unlock_statements.py`) directly on Windows, or launch from terminal:
```bash
python unlock_statements.py
```
*(The black console window is automatically hidden upon launch on Windows).*

### 4. Configure Statement Passwords
Click the **🔑 Configure Passwords** button in the app to set your statement passwords:
* **ICICI Bank**: First 4 letters of name in lowercase + Date & Month of birth (`DDMM`)
* **HDFC Bank**: First 4 letters of name in UPPERCASE + Date & Month of birth (`DDMM`)

Passwords are saved locally to `passwords.json` on your machine and will be reused automatically on all future imports.

## 📁 Project Structure

```text
├── unlock_statements.py     # Main application (desktop GUI & web dashboard generator)
├── unlock_statements.pyw    # Windowless desktop launcher
├── requirements.txt         # Required Python packages (pypdf, cryptography)
├── passwords.json.example   # Template credential configuration
├── .gitignore               # Strict exclusion of sensitive passwords & PDFs
└── README.md                # Project documentation
```

## 🔒 Security & Privacy

* All PDF unlocking, decryption, and text analysis happen **100% locally on your computer**.
* No financial statements, account numbers, transactions, or passwords are ever transmitted over the network.
* `.gitignore` is pre-configured to strictly exclude `*.pdf`, `passwords.json`, `emi_names.json`, and `Statements_*/` directories from being committed to Git.

## 📄 License
This project is licensed under the MIT License.