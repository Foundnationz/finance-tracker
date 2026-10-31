# Contributing to Finance Tracker

Thank you for your interest in improving Finance Tracker.

This is an academic desktop prototype originally developed as a joint
Final Year Project by Shawn and Farrel. See the
[Authors and Contributions section](README.md#-authors-and-contributions)
in the README for attribution.

The current repository is maintained by
[Shawn (@Foundnationz)](https://github.com/Foundnationz).

Contributions should prioritise correctness, explainability, privacy,
and maintainability over adding features quickly.

---

## 1. Before Proposing a Change

Please read:

- [README.md](README.md)
- [Post-Submission Desktop Implementation Update](docs/desktop-implementation-update.md)

Check existing issues and pull requests to avoid duplicating work.

For substantial changes—particularly database migrations, financial
calculations, scheduling behavior, or architecture—open an issue for
discussion before implementing the change.

If repository Issues are unavailable, explain the proposal clearly
in a draft pull request.

Acceptance or review of a contribution is not guaranteed.

---

## 2. Reporting Bugs

Include:

- A concise description of the problem.
- Steps to reproduce it.
- Expected behavior.
- Actual behavior.
- Operating system and Python version.
- Relevant package versions.
- A sanitised traceback or screenshot, where useful.

Use fictional information when demonstrating financial workflows.

Do not include:

- Real financial records.
- Personal email addresses or account details.
- Passwords or password hashes.
- Database files or backups.
- Authentication tokens or other credentials.

If a problem involves financial calculations, provide a small fictional
example showing the inputs and expected result.

---

## 3. Security and Privacy Reports

Do not publish sensitive data or exploitable security details in a
public issue.

Check whether GitHub's private vulnerability reporting is enabled
under the repository's Security tab. Use it if available.

If private reporting is unavailable, request a private contact method
without disclosing the vulnerability publicly.

Do not test against another person's financial data or accounts.

This project is not a banking service and should not be treated as
production-ready financial software.

---

## 4. Development Setup

The documented development environment is Windows with Python 3.14.
Other environments may require additional verification.

### Clone your fork

```powershell
git clone https://github.com/YOUR-USERNAME/finance-tracker.git
cd finance-tracker

```

### Create an isolated environment

```powershell
python -m venv .venv
```

### Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Check dependencies

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Tkinter and SQLite are supplied through the Python installation rather
than this project's pip requirements. Confirm that your Python
installation provides working tkinter support.

---

## 5. Use a Temporary Database for Testing

Do not test destructive operations, migrations, or scheduled processing
against your real financial database.

The application's normal launch creates or opens `budgeting_app.db`
beside the application file.

For an isolated GUI session, run this launcher in PowerShell:

```powershell
@'
import tempfile
from pathlib import Path
import capstone_project_code as app

with tempfile.TemporaryDirectory() as folder:
    app.db_path = str(Path(folder) / "test.db")
    app.create_db()
    app.launch_app()
'@ | .\.venv\Scripts\python.exe -
```

Register a fictional user and create demonstration records inside that
session. The temporary database is removed when the application exits
normally and the temporary-directory context is closed.

This launcher relies on:

- Importing the application without starting its main runner.
- Overriding `db_path` before database setup.
- No other code opening the normal database during import.

If you change database configuration or application startup behavior,
update and verify this isolation mechanism too.

Temporary test databases must not be committed.

---

## 6. Financial and Scheduling Changes

Explain and test any change that affects:

- Transaction creation, editing, or deletion.
- Account-balance updates.
- Scheduled-occurrence generation and duplicate prevention.
- Pause/resume or catch-up behavior.
- Budget periods, limits, or historical settings.
- Subscription billing dates.
- Recommendation calculations.

Use explicit date-boundary rules. The current calculations generally
use inclusive start dates and exclusive end dates.

Do not silently:

- Generate financial records from a read-only insight.
- Change past transactions when editing a schedule.
- Guess an account for an older subscription.
- Backfill historical budget limits from current values.
- Treat missing transaction records as proof of zero real spending.
- Treat unclassified expenses as Wants.
- Claim that a recorded expense verifies an actual provider payment.

Document changes to existing behavior and consider migration effects
for existing databases.

Database migrations must preserve user data, handle repeated startup,
and be tested on disposable databases.

---

## 7. Recommendation Features

Recommendations must be explainable and supported by available data.

Where applicable, show:

- The observation.
- The date range.
- The calculation or rule.
- A suggested action.
- Relevant limitations or excluded data.

Do not describe rule-based features as machine learning or case-based
reasoning unless those methods are actually implemented and evaluated.

Do not infer emotions, impulse buying, subscription usage, or affordability
without appropriate supporting data and a clearly justified method.

Increasing spending is not automatically evidence of poor financial behavior.

---

## 8. Checks Before Submitting

Install the application and development dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run the saved automated tests from the repository's main folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Also check syntax and package dependencies:

```powershell
.\.venv\Scripts\python.exe -m py_compile capstone_project_code.py
```

```powershell
.\.venv\Scripts\python.exe -m pip check
```

### Database Test Safety

Database tests must request the `temporary_app` fixture from
`tests/conftest.py` before calling application database functions.

The fixture redirects `db_path` before database setup and restores it
afterward. Do not bypass it or point tests at a real financial database.

Application import must remain free of GUI startup and normal-database
access. If startup or configuration changes, verify test isolation too.

### Coverage and Manual Checks

The saved suite covers selected date, database, scheduling, budget-history,
and recommendation scenarios. It is not complete application coverage.

Manually test affected GUI workflows using temporary data, including:

- Empty and populated screens.
- Invalid input.
- Navigation and screen refresh.
- Resizing and mouse-wheel scrolling.
- Popup opening and closing.
- Chart rendering.
- Confirmation and cancellation behavior.

Add or update regression tests when changing financial calculations,
database behavior, or scheduling rules.

Do not change expected test results merely to make a failure disappear.
Investigate whether the failure reflects a defect or an intentional
behavior change.

A pull request should state which automated and manual checks were run,
their results, and any known gaps.

Do not claim a test passed unless you ran it.

---

## 9. Submitting Changes

1. Fork the repository.
2. Create a branch for one focused change.
3. Make the change and test it.
4. Update relevant documentation.
5. Review the files being committed.
6. Open a pull request explaining the change.

Example branch creation:

```powershell
git switch -c fix/describe-the-fix
```

A pull request should explain:

- What changed and why.
- Related issue, if any.
- Tests performed and their results.
- Database migration implications.
- Known limitations.
- Screenshots for visible interface changes, using fictional data.

Keep unrelated changes in separate pull requests.

Do not reformat the entire application while submitting a small fix.
Large restructuring should be discussed and tested separately.

---

## 10. Files That Must Not Be Committed

Do not commit:

- Local SQLite databases and sidecar files.
- Database backups.
- Real financial exports.
- Virtual environments.
- Python cache files.
- Credentials or private configuration.
- Screenshots containing personal information.

Before committing, inspect:

```powershell
git status
```

```powershell
git diff
```

Adding a file to `.gitignore` does not remove information already tracked
in Git or erase it from repository history.

---

## 11. Documentation and Attribution

Keep documentation aligned with the implemented behavior.

Distinguish:

- Original project proposals.
- Features in the submitted Colab prototype.
- Later desktop additions.
- Development tests.
- Outcomes established through user research.

Do not modify the submitted academic report to imply later work was
part of the original submission. Record subsequent changes in the
desktop implementation update.

Preserve existing contributor attribution.

Disclose substantial AI assistance in the pull request, including what
was generated or adapted and how it was checked. Do not submit sensitive
project or user information to external tools.

---

## 12. Licensing

Check the repository's current license before reusing or contributing code.

These contribution guidelines do not themselves grant a software license
or resolve ownership of the original jointly developed project.

Any license decision should respect the contributors' rights and
applicable university requirements.