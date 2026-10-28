# 💰 Finance Tracker — Personal Budgeting App

A personal finance management system designed with Generation Z users
in mind and developed as a Final Year Project.

Originally prototyped in Google Colab with ipywidgets, the project was
subsequently developed into a local Python desktop application using
tkinter, with VSCode as the development editor.

---

## 📌 About

Finance Tracker combines everyday financial tracking with motivational
features such as login streaks, achievement badges, and wishlist goals.

Users manually record financial information and manage their accounts,
budgets, transactions, and scheduled expenses through a desktop interface.

This is an academic prototype. It is not a banking application, payment
service, or financial advisory platform.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 💳 Account Management | Track up to five financial accounts, edit names and notes, and record balance adjustments with a reason |
| 📊 Budget Tracking | Create category-based budgets with daily, weekly, monthly, or yearly timeframes, spending breakdowns, notes, and alerts |
| 💸 Transactions | Add, edit, delete, and search income and expenses using categories, tags, notes, references, and Need/Want classification |
| 🔁 Recurring Transactions | Schedule income and expenses with login-based processing, missed-occurrence catch-up, history, and pause/resume controls |
| 🔄 Subscriptions | Manage subscription expenses through the shared recurring engine, including multiple monthly billing days and linked payment history |
| 🎯 Wishlist | Track virtual contributions toward purchase goals independently of account balances |
| 📈 Dashboard | View monthly transaction summaries and income/expense charts |
| 🏅 Badges and Streaks | Recognise usage milestones and consecutive-day logins |
| ⚙️ Currency Display | Select a display currency from 20 options, including USD, MYR, GBP, and EUR; amounts are not converted |
| 📥 CSV Export | Export transaction records to a CSV file |
| 🔒 Password Hashing | Store registered passwords as bcrypt hashes rather than plaintext |

---

## 🔁 How Scheduled Transactions Work

Subscriptions are specialised recurring expenses. The Subscriptions and
Recurring Transactions screens use the same underlying schedule rather
than independently generating expenses.

### Processing

- Active schedules are checked after a successful login.
- Creating a new subscription also triggers a check of the user's due schedules.
- Due occurrences are recorded using their scheduled dates.
- Missed occurrences are caught up when processing next runs.
- The application does not process schedules in the background while closed.
- Recording a scheduled expense updates the account balance stored inside the app.
- The application does not contact a bank, transfer money, or pay a provider.

### Subscription Billing

- Subscriptions support monthly billing days such as `1,15`.
- Duplicate billing-day input is normalised, so `15,1,15` becomes `1,15`.
- Days that do not exist in a month are skipped.
  For example, a schedule for the 31st has no occurrence in April.
- Annual subscription billing is not currently implemented.
- Older subscriptions require explicit account and recording-start-date
  setup before joining the shared scheduler.
- Setting up an older subscription does not immediately generate expenses.
  Due occurrences are checked at the next login.
- A past recording start date can create catch-up expenses. Review the
  confirmation carefully to avoid duplicating manually recorded payments.

### Duplicate Protection and History

- Each processed occurrence is identified by its recurring rule and scheduled date.
- Processed-occurrence records prevent repeated generation of the same occurrence.
- Deleting a generated transaction does not automatically regenerate it.
- History uses stored IDs, so renaming a schedule does not break its links.
- Transactions created before reliable schedule links were introduced may
  remain available only in normal Transaction History.
- History lists show surviving linked transactions, not a complete,
  immutable audit log.
- Users must still avoid creating two schedules for the same real-world payment
  or recording the same expense both manually and automatically.

### Editing, Pausing, and Deleting

- Linked subscription edits update the subscription and shared schedule together.
- Editing schedule settings does not rewrite past transactions or change balances.
- Linked subscription edits are blocked when an occurrence is due today
  or earlier until outstanding dates are resolved.
- Pausing stops automatic processing.
- Resuming requires confirmation of the next scheduled date.
- Pending dates before the confirmed resume date are skipped rather than
  automatically caught up.
- Deleting a linked subscription or its schedule removes both records,
  while preserving past transactions and account balances.
- Past expenses from deleted schedules remain accessible in normal
  Transaction History.

### Processing Errors

If scheduled processing fails during login, the user can still sign in.

The application displays a warning, and uncommitted changes from that
processing attempt are rolled back. Due occurrences may remain pending,
so balances and budget totals may not include them.

Do not manually add replacement expenses without first checking the
processing problem, because this could create duplicate records.

---

## 🛠️ Built With

| Tool | Purpose |
|---|---|
| Python | Core programming language; current development environment uses Python 3.14 |
| tkinter | Desktop graphical interface |
| SQLite | Local database storage |
| matplotlib | Financial charts and visualisation |
| pandas | Tabular data handling and CSV export |
| bcrypt | Password hashing |
| python-dateutil | Date calculations for budgets and recurring schedules |
| VSCode | Development editor |
| Git and GitHub | Version control and repository hosting |

---

## 🚀 How to Run

### Requirements

- Developed and manually tested on Windows using Python 3.14.
- Compatibility with other Python versions and operating systems has not
  yet been fully verified.
- A Python installation with working tkinter support.
- Third-party libraries listed in `requirements.txt`.

**Dependency compatibility note:** installation from `requirements.txt`
still needs verification in a clean Python 3.14 virtual environment.
The application working in an existing development environment does not
guarantee that every pinned dependency will install successfully on a new machine.

### 1. Clone the Repository

```bash
git clone https://github.com/Foundnationz/finance-tracker.git
cd finance-tracker
```

### 2. Create a Virtual Environment

On Windows:

```powershell
python -m venv .venv
```

### 3. Install Dependencies

Use the virtual environment's Python directly; activation is not required:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If installation fails, review the dependency compatibility note above.
Do not assume the environment is ready after a failed installation.

### 4. Run the Application

```powershell
.\.venv\Scripts\python.exe capstone_project_code.py
```

The application creates `budgeting_app.db` automatically in the same
folder as the Python application file on first run.

You do not need to create the database manually.

---

## 🖥️ Screenshots

Screenshots should use demonstration data rather than real personal or
financial information. Screenshots may lag behind interface changes.

### Welcome Screen

![Welcome Screen](assets/screenshots/welcome.png)

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

```text
finance-tracker/
├── capstone_project_code.py   # Main desktop application
├── requirements.txt           # Third-party Python dependencies
├── README.md                  # Project overview and instructions
├── .gitignore                 # Files excluded from version control
├── docs/                      # Academic project report
└── assets/
    └── screenshots/           # Demonstration screenshots
```

The local database and virtual environment are runtime/development files.
They should not be committed to the repository.

---

## 🔑 Developer Utilities and Local Data

The source includes developer helpers for listing registered users and
deleting test users.

User deletion requires confirmation and permanently removes the selected
user's associated records. These helpers are maintenance utilities,
not a secured administrative dashboard.

Do not run deletion utilities against real data without a backup.

### Database Safety

- `budgeting_app.db` contains local user and financial data.
- Keep the database, SQLite sidecar files, backups, and real financial
  exports out of version control.
- Password hashing does not encrypt the SQLite database or its financial records.
- Anyone who can access the database file may be able to read its contents.
- Close the application before making a simple file-copy backup.
- To start fresh, close the app and move the database to a secure backup
  location before rerunning. A new database will be created automatically.
- Moving or deleting the database does not remove copies already present
  in Git history, backups, or cloud storage.

### Recommended Local-Only Files

Your `.gitignore` should exclude local files such as:

```gitignore
# Local SQLite databases and sidecar files
*.db
*.db-journal
*.db-wal
*.db-shm

# Virtual environments
.venv/
venv/
env/

# Python caches
__pycache__/
*.py[cod]
```

Backups and exports containing real information should also be stored
outside the repository or explicitly ignored.

Adding a file to `.gitignore` does not stop tracking a file that was
already committed. Removing sensitive information from Git history
requires separate action.

---

## 🧪 Testing

Development checks have included temporary-database tests and manual
GUI workflow checks covering:

- Fresh database creation and repeated setup.
- Subscription creation and shared-schedule linking.
- Scheduled expense recording and account-balance updates.
- Repeated-login duplicate prevention.
- Missed-occurrence catch-up.
- Multiple monthly billing days and leap-year date handling.
- Separation of subscription payment history from unrelated category expenses.
- Linked subscription editing without rewriting past transactions.
- Pause/resume confirmation and next-date selection.
- Deletion from either linked screen while preserving past transactions.
- Explicit setup of older, unlinked subscriptions.
- User-data deletion in dependency order.
- Login warnings when scheduled processing fails.

These checks provide evidence for the tested scenarios.
They do not establish that the application is free of bugs,
production-ready, or suitable for regulated financial services.

A complete automated test suite and clean-environment installation
verification remain areas for improvement.

---

## ⚠️ Current Limitations

- Financial information is entered manually; there is no live bank or
  e-wallet integration.
- Scheduled processing requires application activity and is not a
  background payment service.
- Subscription scheduling currently uses monthly billing-day patterns,
  not annual subscription plans.
- Currency selection changes display settings without exchange-rate conversion.
- Wishlist funding is a virtual goal tracker and does not reserve or
  transfer money from financial accounts.
- Password hashing protects passwords differently from database encryption;
  financial records are not encrypted by this mechanism.
- Transactions are editable and deletable, so the application does not
  provide an immutable financial audit trail.
- Rule-based scheduling, budget alerts, and random educational quotes
  are not AI-powered financial coaching.
- Compatibility, accessibility, large-data performance, and security
  require further evaluation.
- The current codebase remains primarily a single application file.
  Further modularisation would improve maintainability.

---

## 📄 Project Report

The academic project report is available in the [`docs/`](docs/) folder.

The report primarily documents the original Google Colab prototype.
The current desktop implementation includes subsequent changes described
in this README.

Some original proposals and research ambitions—such as banking integration,
AI coaching, and advanced financial education—are not implemented in the
current desktop application.

---

## 🔄 Development History

The labels below describe project development stages; they do not
necessarily correspond to published GitHub releases.

| Stage | Environment | Description |
|---|---|---|
| v1.0 | Google Colab + ipywidgets | Original academic prototype |
| v2.0 | Local Python desktop app + tkinter | Developed using VSCode, with GUI migration and functional improvements |

### Desktop Implementation Improvements

- Replaced notebook widgets with a tkinter desktop interface.
- Added bcrypt password hashing.
- Expanded transaction records with tags, notes, references, and Need/Want.
- Added editing across major management sections.
- Added recurring income and expense processing.
- Unified subscription scheduling with the recurring engine.
- Added ID-linked recurring and subscription history.
- Added processed-occurrence tracking for duplicate protection.
- Added explicit schedule setup for older subscriptions.
- Added confirmed pause/resume dates.
- Added clearer schedule-processing failure warnings.
- Added selectable currency display without exchange-rate conversion.
- Added CSV export.
- Added budget spending breakdowns and clearer monetary alerts.
- Added budget notes and shared category creation.
- Added balance adjustments recorded as transactions with a reason.
- Improved developer user-data cleanup.

---

## 🎓 Academic Context

| Detail | Information |
|---|---|
| Project Type | Final Year Project |
| Intended Audience | Generation Z users |
| Methodology | Agile-inspired iterative development within an SDLC framework |
| Focus Area | Personal Finance Management |
| Current Application Type | Local desktop prototype |