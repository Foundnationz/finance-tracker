# Database Schema

This reference was generated from a fresh temporary SQLite
database created by the current application's `create_db()` function.

It contains schema definitions only, not user or financial records.
The normal `budgeting_app.db` was not opened by this generator.

## Scope and Interpretation

- The definitions represent the fresh-database result after startup migrations.
- They are reference documentation, not a standalone migration script.
- Older databases may differ if their migrations have not completed.
- Application validation rules are not all enforced by SQL constraints.
- A column named `user_id` or another ID does not necessarily imply
  a declared foreign key; inspect the definitions below.
- The connection helper enables SQLite foreign-key enforcement.
- Money fields currently use the application's existing numeric schema;
  this document does not claim exact-money accounting.
- Update this reference after changing tables, columns, constraints, or indexes.

## Tables

### `accounts`

```sql
CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_name TEXT NOT NULL,
                balance REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `badges`

```sql
CREATE TABLE badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                badge_name TEXT NOT NULL,
                badge_description TEXT,
                date_awarded TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `budget_monthly_history`

```sql
CREATE TABLE budget_monthly_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                budget_id INTEGER NOT NULL,
                effective_month TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,

                UNIQUE (budget_id, effective_month),

                CHECK (
                    length(effective_month) = 10
                    AND effective_month GLOB
                        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-01'
                    AND substr(effective_month, 6, 2)
                        BETWEEN '01' AND '12'
                ),

                FOREIGN KEY(user_id)
                    REFERENCES users(id),

                FOREIGN KEY(budget_id)
                    REFERENCES budgets(id)
                    ON DELETE CASCADE
            );
```

### `budgets`

```sql
CREATE TABLE budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                budget_name TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                category TEXT,
                amount REAL NOT NULL,
                spent REAL DEFAULT 0, notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `categories`

```sql
CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(user_id, type, name),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `processed_schedule_occurrences`

```sql
CREATE TABLE processed_schedule_occurrences (
                user_id INTEGER NOT NULL,
                recurring_rule_id INTEGER NOT NULL,
                scheduled_date TEXT NOT NULL,
                PRIMARY KEY (
                    user_id,
                    recurring_rule_id,
                    scheduled_date
                )
            );
```

### `recurring_transactions`

```sql
CREATE TABLE recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                next_due_date TEXT NOT NULL,
                last_processed TEXT,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1, "notes" TEXT DEFAULT '', "tags" TEXT DEFAULT '', "necessity" TEXT DEFAULT 'unset', "schedule_kind" TEXT NOT NULL DEFAULT 'recurring', "monthly_charge_days" TEXT, "schedule_start_date" TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            );
```

### `settings`

```sql
CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                currency_symbol TEXT DEFAULT '$',
                currency_name TEXT DEFAULT 'USD',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `subscriptions`

```sql
CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_name TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                charge_dates TEXT NOT NULL, "notes" TEXT DEFAULT '', "necessity" TEXT DEFAULT 'unset', "recurring_rule_id" INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `tags`

```sql
CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                user_id INTEGER,
                tag_name TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

### `transactions`

```sql
CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL, "notes" TEXT DEFAULT '', "reference" TEXT DEFAULT '', "necessity" TEXT DEFAULT 'unset', recurring_rule_id INTEGER, subscription_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            );
```

### `users`

```sql
CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                last_login_date TEXT,
                streak_count INTEGER DEFAULT 0
            );
```

### `wishlist`

```sql
CREATE TABLE wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT NOT NULL,
                price REAL NOT NULL,
                notes TEXT,
                link TEXT,
                progress REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

## Explicit Indexes

SQLite's automatically generated indexes for primary-key and
unique constraints are omitted from this list. Those constraints
remain visible in the table definitions.

### `idx_budget_history_lookup`

Table: `budget_monthly_history`

```sql
CREATE INDEX idx_budget_history_lookup
               ON budget_monthly_history
                  (user_id, budget_id, effective_month);
```

### `idx_subscriptions_recurring_rule_unique`

Table: `subscriptions`

```sql
CREATE UNIQUE INDEX idx_subscriptions_recurring_rule_unique
               ON subscriptions (recurring_rule_id)
               WHERE recurring_rule_id IS NOT NULL;
```

### `idx_transactions_recurring_rule`

Table: `transactions`

```sql
CREATE INDEX idx_transactions_recurring_rule
               ON transactions (user_id, recurring_rule_id);
```

### `idx_transactions_subscription`

Table: `transactions`

```sql
CREATE INDEX idx_transactions_subscription
               ON transactions (user_id, subscription_id);
```
