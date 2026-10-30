# Post-Submission Desktop Implementation Update

## 1. Purpose and Status

This document records changes made to Finance Tracker after the original
Final Year Project report was submitted.

The submitted report is retained unchanged as a historical record of the
academic submission. This document does not replace or officially amend
that submission.

The original report primarily describes the Google Colab prototype.
The current repository contains a subsequently developed local desktop
implementation.

Features and tests described here must not be assumed to have been
included in the original prototype or its reported user acceptance testing.

This is a development record, not an independent security audit or a
new academic evaluation of user outcomes.

---

## 2. Relationship to the Submitted Report

The submitted report discusses personalised recommendations,
knowledge-based recommender systems, case-based reasoning, and
AI-driven financial coaching.

These concepts should be distinguished from the implementation:

- The original Colab code provided transaction summaries, charts,
  budget warnings, and randomly selected financial quotes.
- It did not implement the personalised recommendation engine described
  in some passages of the report.
- The later desktop implementation adds an explicit rule-based,
  knowledge-based recommendation module.
- The desktop module does not implement case-based reasoning,
  machine learning, emotional analysis, or automatic impulse-purchase detection.

Adding the desktop recommendation module later does not retrospectively
establish that the original prototype contained it.

The original user testing does not establish the usability or effectiveness
of features introduced after that testing.

---

## 3. Development Environment and Application Type

The project evolved from:

1. A Python prototype running in Google Colab with ipywidgets.
2. A local Python desktop application using tkinter.

VSCode is the development editor. It is not a web framework, deployment
platform, or application runtime.

The current application:

- Runs locally as a desktop program.
- Stores application data in a local SQLite database.
- Uses matplotlib for charts.
- Uses pandas for tabular data handling and CSV export.
- Uses bcrypt for password hashing.
- Uses python-dateutil for calendar-aware date calculations.

The desktop implementation is not a mobile-native application or a
networked client-server financial service.

---

## 4. Account and Transaction Improvements

The desktop implementation includes:

- Account name and notes editing.
- Balance adjustments recorded as transactions with a reason.
- Transaction editing with corresponding balance adjustments.
- Transaction notes, reference fields, and tags.
- Need/Want classification for expenses.
- Transaction history filtering and keyword search.
- CSV export.

Balance adjustments provide a record of a change, but the application
does not provide an immutable audit trail. Transactions remain editable
and deletable.

Account balances represent values recorded inside the application.
They are not verified against live bank or e-wallet balances.

---

## 5. Category Management

Categories remain shared across relevant forms.

Improvements include:

- Category creation from relevant forms without discarding other inputs.
- Distinct income and expense category labels during deletion.
- Category deletion by unique category ID and user ID.
- Clearer wording for budgets that include all expense categories.

The special budget option, "All Expense Categories", means the budget
counts expenses across categories. It is not an ordinary subscription category.

Existing financial records store category names. Deleting a category
does not automatically remove or rewrite those records.

Category-name changes and inconsistent naming can affect historical
category comparisons.

---

## 6. Calendar-Based Budgeting

Budget calculations now use consistent calendar periods:

| Timeframe | Calendar Period |
|---|---|
| Daily | Today |
| Weekly | Monday through Sunday |
| Monthly | First through last day of the current month |
| Yearly | 1 January through 31 December |

### Calculation Rules

- Date queries use an inclusive start and exclusive end.
- Current spending includes recorded expenses from the period start
  through today.
- Future-dated transactions are excluded from current spending totals.
- Budget progress and View Spending use the same spending query.
- Usage percentages may exceed 100%; only the visual progress-bar fill
  is capped at 100%.

### User-Facing Improvements

- Add Budget previews the current calendar period.
- Budget cards display the current period dynamically.
- Days remaining include today.
- An exactly reached limit is distinguished from an exceeded limit.
- Cards and alerts show actual spending, remaining amounts, and overspend.
- Misleading fixed-midpoint overspend graphics were replaced.
- Optional budget notes describe the budget's purpose.

A budget created partway through a period includes expenses already
recorded in that period. Its limit applies to the whole period and is
not automatically prorated.

Custom-date and pay-cycle budgets are not implemented.

Budget notes are descriptive only. They do not automatically create
transaction-inclusion or exclusion rules.

---

## 7. Shared Recurring and Subscription Scheduling

Subscriptions are treated as specialised recurring expenses.

The Subscriptions and Recurring Transactions screens refer to a shared
schedule rather than independently generating the same payment.

### Processing Behavior

- Active schedules are checked after successful login.
- Creating a new subscription also triggers a check of the user's due schedules.
- Missed occurrences are recorded using their scheduled dates.
- Processing updates the selected account's in-app balance.
- The application does not process schedules while closed.
- It does not transfer money or pay subscription providers.

### Subscription Billing

- Monthly billing days can contain multiple values, such as `1,15`.
- Duplicate day values are normalised.
- Days that do not exist in a month are skipped.
- Annual subscription billing is not implemented.

### Stable History Links

Generated subscription expenses store links to both:

- Their recurring rule.
- Their subscription record.

These links allow renaming without relying on category names or
name-based tags to identify history.

Older transactions without verified links remain accessible in normal
Transaction History but may not appear in dedicated schedule histories.

### Duplicate Protection

A processed-occurrence table identifies occurrences by user,
recurring rule, and scheduled date.

This prevents the same processed occurrence from being generated again
when processing repeats or a next-due date is moved backward.

Deleting a generated transaction does not automatically regenerate that
occurrence.

This protection does not identify two separately created schedules that
represent the same real-world payment. Users must avoid duplicate schedules
and duplicate manual entries.

### Editing and Deletion

- Linked subscription edits update the subscription and schedule together.
- Past transactions are not rewritten by schedule edits.
- Linked subscription editing is blocked when outstanding dates must
  first be resolved.
- Deleting a linked subscription or its schedule removes both linked
  records while preserving past transactions and account balances.

### Pause and Resume

- Paused schedules are excluded from automatic processing.
- Resuming requires confirmation of the next date.
- Pending dates before the confirmed resume date are skipped.
- Resuming itself does not generate a transaction.

### Older Subscription Setup

Older subscriptions require explicit selection of an account and
recording start date before joining the shared scheduler.

Setup does not guess the account or automatically assign historical
unlinked transactions.

Saving setup creates the schedule without immediately generating expenses.
Due occurrences are checked at the next login.

---

## 8. Dashboard Recommendation Module

The desktop Dashboard includes five explainable recommendation features.

The module applies explicit rules to recorded data. It does not learn
from training data or retrieve and adapt previous cases.

### 8.1 Daily Budget Allowance

For a budget with remaining funds:

    Average daily allowance =
    Remaining budget / Remaining days, including today

The displayed allowance is rounded down to two decimal places.

When a limit is reached or exceeded, the module provides spending-review
guidance instead of a positive allowance.

This is a budget-based guide, not an affordability assessment. It does
not reserve funds or subtract every upcoming obligation.

Overlapping budgets represent overlapping views of spending. Their
allowances must not be added together.

### 8.2 Category Spending Comparison

For the current month, the module compares equal numbers of elapsed days
against the previous month.

If the previous month is shorter, the selected-month cutoff is limited
to maintain equal day counts.

Completed months are compared as full calendar months, with different
month lengths disclosed.

The module:

- Examines expense records.
- Highlights up to three category increases.
- Ranks increases by monetary difference.
- Does not calculate a percentage increase when the previous amount is zero.
- Does not interpret increased spending as automatically irresponsible.

### 8.3 Upcoming Scheduled Expenses

The module evaluates active expense schedules for seven calendar days,
including today.

It groups scheduled occurrences by account and compares their total
with the account's current recorded balance.

It excludes scheduled income and pending dates before the window.
Schedule problems and older subscriptions requiring setup produce notices
where detected.

This is not a complete cash-flow forecast or a statement about actual
bank-account funds.

### 8.4 Subscription Cost Review

The module estimates unprocessed subscription expenses scheduled for
the next calendar month using current active schedules and prices.

It supports multiple monthly billing days and the agreed short-month
skipping policy.

It suggests reviewing whether plans still meet the user's needs.
It does not know whether a subscription is used, unused, essential,
or suitable for cancellation.

The review can overlap with the seven-day upcoming-expense section.
Those totals must not be added together.

### 8.5 Needs/Wants Reflection

The module shows:

- Need expenses.
- Want expenses.
- Unclassified expenses.
- Total valid recorded expenses.

The percentage split uses classified expenses only.

Unclassified values are not treated as Wants.

These percentages must not be compared directly with the 50/30/20
income-allocation guideline, because the calculation does not use income,
savings, and debt allocations as its denominator.

### Selected-Period and Current Guidance

The Dashboard separates:

| Insight | Time Basis |
|---|---|
| Category spending comparison | Selected report month |
| Needs/Wants reflection | Selected report month |
| Daily budget allowance | Current date |
| Upcoming scheduled expenses | Current seven-day window |
| Subscription cost review | Next calendar month |

Current guidance remains independent of a historical report month.

### Interpretation Limits

Recommendations depend on the completeness and accuracy of manually
recorded information.

User-supplied labels, category-name changes, one-off purchases, and
balance adjustments can affect the results.

The module does not establish that a user can afford a purchase,
should cancel a service, or has made an impulsive decision.

---

## 9. Error Handling and Data Maintenance

### Scheduled Processing Errors

A scheduled-processing failure does not automatically turn valid
credentials into a failed login.

The application displays a warning. Uncommitted changes from that
processing attempt are rolled back, and due occurrences may remain pending.

This is specific handling for scheduled processing failures, not a claim
that every possible application error is recovered automatically.

### Developer User Deletion

The developer cleanup helper deletes user data in an explicit dependency
order and commits the cleanup as one database transaction.

The cleanup includes processed schedule occurrences, settings, tags,
transactions, schedules, and other user-owned records.

These utilities are not a secured administrative dashboard.

---

## 10. Testing Performed During Desktop Development

Development checks included temporary-database tests and manual GUI tests.

### Database and Scheduling Checks

- Fresh database creation and repeated setup.
- Column migrations after table creation.
- Linked subscription creation.
- Multiple monthly billing days.
- Short-month and leap-year handling.
- Missed-occurrence catch-up.
- Duplicate prevention after repeated processing and schedule rewind.
- Preservation of processed markers after transaction deletion.
- Stable history links after renaming.
- Linked editing and deletion.
- Pause/resume confirmation.
- Explicit setup of older subscriptions.
- User deletion in dependency order.
- Login warnings for simulated schedule-processing failure.

### Budget and Recommendation Checks

- Calendar-period boundaries.
- Spending-query date cutoffs.
- Category and user separation.
- Agreement between budget cards, alerts, and spending breakdowns.
- Uncapped usage percentages.
- Daily-allowance rounding and final-day behavior.
- Zero-baseline spending comparisons.
- Needs/Wants and unclassified separation.
- Scheduled-expense exclusions and account grouping.
- Next-month subscription-cost calculations.
- Dashboard refresh without duplicated sections.
- Separation of selected-period analysis from current guidance.
- Read-only Dashboard operation, verified against transaction counts
  and account balances.

### Installation Checks

Dependencies were installed in a clean Python 3.14 virtual environment
on Windows.

Checks included:

- `pip check`.
- Required-library imports.
- A temporary-database application smoke test.

### What These Tests Do Not Establish

These checks do not establish:

- Production readiness.
- Complete freedom from defects.
- Regulatory suitability.
- Independent security certification.
- Accessibility compliance.
- Compatibility with every platform.
- Improved financial literacy, savings, or long-term user behaviour.

The desktop recommendation module was not evaluated through the original
prototype's reported user acceptance study.

A maintained automated test suite and broader evaluation remain future work.

---

## 11. Security and Privacy Boundaries

Registered passwords are hashed using bcrypt.

Password hashing does not encrypt the SQLite database or its financial
records. Local file access remains an important security boundary.

The application does not currently provide:

- Live banking or e-wallet integration.
- Multi-factor authentication.
- Encrypted financial database storage through the password-hashing mechanism.
- An immutable transaction audit log.
- A secured multi-user web administration service.

Databases, SQLite sidecar files, backups, and real financial exports
must be kept out of the public repository.

Adding a file to `.gitignore` does not remove information already committed
to Git history.

---

## 12. Remaining Limitations and Future Work

Potential future improvements include:

- A maintained automated test suite.
- Modularising the large application file.
- Further accessibility and cross-platform testing.
- Explicit money storage using integer minor units or an appropriate
  exact-money design.
- Custom-date and pay-cycle budgeting.
- Historical budget-limit versioning.
- Reliable funded-amount storage and target dates for wishlist planning.
- Filtered navigation from recommendations to supporting transactions.
- Consolidated data-quality guidance.
- Broader usability evaluation of the expanded Dashboard.
- Evaluation of whether recommendations produce useful user outcomes.

Machine learning, case-based reasoning, emotional analysis, banking
integration, and automatic impulse-purchase detection remain separate
research or development possibilities—not completed features.

---

## 13. Summary

The post-submission desktop work expands the original prototype with
improved local financial management, shared scheduling, clearer calendar
budgets, and explainable rule-based Dashboard suggestions.

The submitted report remains a historical academic document.
This update records later implementation work without attributing those
features or their tests to the original prototype.