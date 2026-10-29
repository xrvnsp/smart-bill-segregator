# 💳 Bank Statement Analyzer & Unlocker

A modern desktop application and interactive web dashboard for decrypting, analyzing, and segregating password-protected Indian bank credit card statements (**HDFC Bank** & **ICICI Amazon Pay**).






## ✨ Features

- 🔐 **One-Time Local Password Store**: Configure your ICICI and HDFC statement passwords once via an interactive GUI modal. Credentials are saved locally in `passwords.json` and automatically excluded from Git commits via `.gitignore`.
- 🏛️ **Multi-Bank Auto-Segregation**: Automatically detects whether a statement belongs to **HDFC Bank** or **ICICI Bank (Amazon Pay)**, decrypts it, and saves an unlocked copy.
- 📁 **Unified Month Storage**: Consolidates statements for both banks into a single standardized folder (e.g. `Statements_October_2026/`).
- 💰 **Exact Bill & Due Date Extraction**: Accurately extracts the real **Total Bill to be Paid**, **Minimum Due**, and **Payment Due Date** directly from statement headers.
- 🏷️ **Unified Named EMI Receipts**: Automatically groups multi-date loan setup fees (processing fee, GST, cashback reversals) and monthly installments into a single master card labeled with your custom nickname (e.g. `🏷️ Vasanth LG Tv`, `🏷️ Naveen S25Edge`).
- 📅 **Date-Wise Subtotal Segregation**: Groups non-loan transactions by date and calculates accurate daily charge subtotals.
- 📊 **Ongoing EMI / Loan Tracker**: Automatically tracks active loan tenures, remaining principals, and monthly installments with editable nicknames that persist in `emi_names.json`.
- 🖨️ **Print & Save to PDF**: Browser print stylesheets preserve exact background colors, purple EMI receipt headers, and pill tags.
- 🗑️ **1-Click Persistent Month Deletion**: Delete unlocked statement folders and generated files with a single click and confirmation dialog.
- 🪟 **Windowless Execution (`.pyw`)**: Launches directly as a native desktop app on Windows without opening a background terminal console.

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/bank-statement-analyzer.git
cd bank-statement-analyzer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Double-click `unlock_statements.pyw` directly on Windows, or launch from terminal:
```bash
python unlock_statements.pyw
```
*(Using `.pyw` opens the desktop app cleanly without launching a background terminal console.)*

### 4. Configure Statement Passwords
Click the **🔑 Configure Passwords** button in the app to set your statement passwords:
- **ICICI Bank**: First 4 letters of name in lowercase + Date & Month of birth (`DDMM`)
- **HDFC Bank**: First 4 letters of name in UPPERCASE + Date & Month of birth (`DDMM`)

Passwords are saved locally to `passwords.json` on your machine and will be reused automatically on all future imports.

## 📁 Project Structure

```text
├── unlock_statements.pyw    # Main application (desktop GUI & web dashboard generator)
├── requirements.txt         # Required Python packages (pypdf, cryptography)
├── passwords.json.example   # Template credential configuration
├── .gitignore               # Strict exclusion of sensitive passwords & PDFs
└── README.md                # Project documentation
```

## 🔒 Security & Privacy

- All PDF unlocking, decryption, and text analysis happen **100% locally on your computer**.
- No financial statements, account numbers, transactions, or passwords are ever transmitted over the network.
- `.gitignore` is pre-configured to strictly exclude `*.pdf`, `passwords.json`, `emi_names.json`, and `Statements_*/` directories from being committed to Git.

## 📄 License
This project is licensed under the MIT License.
