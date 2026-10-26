# 💰 Finance Tracker — Personal Budgeting App

A personal finance management system built specifically for 
Generation Z users as a Final Year Project.
Originally prototyped in Google Colab, then migrated and 
significantly improved in VSCode using Python and tkinter.

---

## 📌 About

Managing personal finances is a critical life skill, yet many 
Gen Z users struggle with budgeting due to lack of accessible 
and engaging tools. This app addresses that gap by combining 
essential financial tracking features with motivational elements 
like streaks, badges, and goal tracking.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 💳 Account Management | Track up to 5 financial accounts with balance and notes |
| 📊 Budget Tracking | Set budgets by category and timeframe with real-time alerts |
| 💸 Transactions | Log income and expenses with categories, tags, notes and references |
| 🔁 Recurring Transactions | Auto-fire transactions on login when due date arrives |
| 🔄 Subscriptions | Track recurring charges like Netflix, Spotify etc |
| 🎯 Wishlist | Save up for goals with a dedicated piggy bank tracker |
| 📈 Dashboard | Visualize spending with pie charts and line graphs |
| 🏅 Badges and Streaks | Gamification system to reward consistent app usage |
| ⚙️ Multi-Currency | 20+ currencies supported including USD, MYR, GBP, EUR |
| 📥 CSV Export | Export transaction history to Excel-compatible CSV file |
| 🔒 Secure Login | Passwords hashed with bcrypt — never stored as plain text |

---

## 🛠️ Built With

| Tool | Purpose |
|---|---|
| Python 3.11+ | Core programming language |
| tkinter | Desktop GUI framework |
| SQLite3 | Local database — auto created on first run |
| matplotlib | Charts and data visualization |
| pandas | Data handling and CSV export |
| bcrypt | Secure password hashing |
| python-dateutil | Date calculation for budget periods |

---

## 🚀 How To Run

### Requirements
- Python 3.11 or higher
- Libraries listed in `requirements.txt`

### Step 1 — Clone the repository
```bash
git clone https://github.com/Foundnationz/finance-tracker.git
cd finance-tracker
```

### Step 2 — Install required libraries
```bash
pip install -r requirements.txt
```

### Step 3 — Run the app
```bash
python capstone_project_code.py
```

The database file `budgeting_app.db` will be created automatically
in the same folder on first run. You do not need to create it manually.

---

## 🖥️ Screenshots

### Welcome Screen
![Welcome](assets/screenshots/welcome.png)

### Main Menu
![Main Menu](assets/screenshots/main_menu.png)

### Budget Tracking
![Budgets](assets/screenshots/budgets.png)

### Dashboard
![Dashboard](assets/screenshots/dashboard.png)

### Badges
![Badges](assets/screenshots/badges.png)

---

## 📂 Project Structure

```
finance-tracker/
├── capstone_project_code.py   ← Main application file
├── requirements.txt           ← Python dependencies
├── README.md                  ← This file
├── .gitignore                 ← Git ignore rules
├── docs/                      ← Project report documents
└── assets/
    └── screenshots/           ← App screenshots
```

---

## 🔑 Developer Tools

To access admin utilities such as listing users or 
deleting test accounts, run:

```bash
python capstone_project_code.py --admin
```

To reset the database completely, delete `budgeting_app.db` 
and rerun the app. A fresh database will be created automatically.

---

## 📄 Project Report

Full project report available in the `/docs` folder.

---

## 🔄 Development History

| Version | Environment | Notes |
|---|---|---|
| v1.0 | Google Colab + ipywidgets | Original prototype |
| v2.0 | VSCode + tkinter | Full migration and major improvements |

### Key improvements in v2.0
- Migrated from Google Colab to VSCode desktop app
- Replaced ipywidgets with tkinter for proper desktop GUI
- Added bcrypt password hashing for security
- Added transaction tags, notes and reference fields
- Added edit functionality across all major features
- Added recurring transactions with auto-processing
- Added multi-currency support
- Added CSV export
- Added budget alert popup with real money figures
- Added balance adjustment with full audit trail

---

## 🎓 Academic Context

| Detail | Info |
|---|---|
| Project Type | Final Year Project |
| Target Users | Generation Z (ages 18–26) |
| Methodology | Agile + SDLC |
| Focus Area | Personal Finance Management |