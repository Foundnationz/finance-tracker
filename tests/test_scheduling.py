"""Scheduling tests using isolated temporary databases."""

from datetime import datetime, timedelta

import pytest


def create_test_account(app):
    """Creates a fictional user and an account with a balance of 100."""
    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO users (username, email, password)
               VALUES (?, ?, ?)""",
            (
                "testuser",
                "test@example.com",
                "test-only-placeholder",
            ),
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO accounts
               (user_id, account_name, balance)
               VALUES (?, ?, ?)""",
            (user_id, "Test Account", 100),
        )
        account_id = cursor.lastrowid

        conn.commit()

    return user_id, account_id


def create_daily_rule(app, user_id, account_id, due_date, active=1):
    """Creates an ordinary daily expense rule."""
    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO recurring_transactions
               (user_id, account_id, type, category, amount,
                frequency, next_due_date, name, is_active)
               VALUES (?, ?, 'expense', 'Testing', 5,
                       'Daily', ?, 'Daily Test Expense', ?)""",
            (user_id, account_id, due_date.isoformat(), active),
        )
        rule_id = cursor.lastrowid
        conn.commit()

    return rule_id


def test_recurring_expense_is_recorded_once(temporary_app):
    app = temporary_app
    today = datetime.today().date()
    user_id, account_id = create_test_account(app)

    rule_id = create_daily_rule(
        app, user_id, account_id, today
    )

    app.process_recurring_transactions(user_id)
    app.process_recurring_transactions(user_id)

    with app.get_db() as conn:
        transactions = conn.execute(
            """SELECT amount, date, recurring_rule_id
               FROM transactions
               WHERE user_id = ?""",
            (user_id,),
        ).fetchall()

        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

        next_due = conn.execute(
            """SELECT next_due_date
               FROM recurring_transactions
               WHERE id = ?""",
            (rule_id,),
        ).fetchone()[0]

        marker_count = conn.execute(
            """SELECT COUNT(*)
               FROM processed_schedule_occurrences
               WHERE user_id = ? AND recurring_rule_id = ?""",
            (user_id, rule_id),
        ).fetchone()[0]

    assert transactions == [(5, today.isoformat(), rule_id)]
    assert balance == pytest.approx(95)
    assert next_due == (today + timedelta(days=1)).isoformat()
    assert marker_count == 1


def test_deleted_occurrence_is_not_regenerated(temporary_app):
    app = temporary_app
    today = datetime.today().date()
    user_id, account_id = create_test_account(app)

    rule_id = create_daily_rule(
        app, user_id, account_id, today
    )

    app.process_recurring_transactions(user_id)

    with app.get_db() as conn:
        transaction_id = conn.execute(
            """SELECT id FROM transactions
               WHERE user_id = ? AND recurring_rule_id = ?""",
            (user_id, rule_id),
        ).fetchone()[0]

        # Simulate the existing expense-deletion workflow:
        # reverse its balance effect and remove tags before the transaction.
        conn.execute(
            "UPDATE accounts SET balance = balance + 5 WHERE id = ?",
            (account_id,),
        )
        conn.execute(
            "DELETE FROM tags WHERE transaction_id = ?",
            (transaction_id,),
        )
        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (transaction_id,),
        )

        # Deliberately rewind the schedule to the processed date.
        conn.execute(
            """UPDATE recurring_transactions
               SET next_due_date = ?
               WHERE id = ?""",
            (today.isoformat(), rule_id),
        )
        conn.commit()

    app.create_db()
    app.process_recurring_transactions(user_id)

    with app.get_db() as conn:
        transaction_count = conn.execute(
            """SELECT COUNT(*) FROM transactions
               WHERE recurring_rule_id = ?""",
            (rule_id,),
        ).fetchone()[0]

        marker_count = conn.execute(
            """SELECT COUNT(*) FROM processed_schedule_occurrences
               WHERE user_id = ? AND recurring_rule_id = ?""",
            (user_id, rule_id),
        ).fetchone()[0]

        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

    assert transaction_count == 0
    assert marker_count == 1
    assert balance == pytest.approx(100)


def test_subscription_catch_up_preserves_history_links(temporary_app):
    app = temporary_app
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    user_id, account_id = create_test_account(app)

    billing_days = ",".join(
        str(day) for day in sorted({yesterday.day, today.day})
    )

    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO recurring_transactions
               (user_id, account_id, type, category, amount,
                frequency, next_due_date, name, schedule_kind,
                monthly_charge_days, schedule_start_date,
                notes, necessity)
               VALUES (?, ?, 'expense', 'Testing', 5,
                       'Monthly', ?, 'Test Subscription',
                       'subscription', ?, ?, 'Test plan', 'want')""",
            (
                user_id,
                account_id,
                yesterday.isoformat(),
                billing_days,
                yesterday.isoformat(),
            ),
        )
        rule_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO subscriptions
               (user_id, subscription_name, category, amount,
                charge_dates, recurring_rule_id)
               VALUES (?, 'Test Subscription', 'Testing', 5, ?, ?)""",
            (user_id, billing_days, rule_id),
        )
        subscription_id = cursor.lastrowid
        conn.commit()

    app.process_recurring_transactions(user_id)
    app.process_recurring_transactions(user_id)

    with app.get_db() as conn:
        transactions = conn.execute(
            """SELECT date, amount, recurring_rule_id,
                      subscription_id, notes, necessity
               FROM transactions
               WHERE user_id = ?
               ORDER BY date""",
            (user_id,),
        ).fetchall()

        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

        marker_count = conn.execute(
            """SELECT COUNT(*) FROM processed_schedule_occurrences
               WHERE user_id = ? AND recurring_rule_id = ?""",
            (user_id, rule_id),
        ).fetchone()[0]

    expected_notes = "Subscription: Test Subscription | Test plan"

    assert transactions == [
        (
            yesterday.isoformat(),
            5,
            rule_id,
            subscription_id,
            expected_notes,
            "want",
        ),
        (
            today.isoformat(),
            5,
            rule_id,
            subscription_id,
            expected_notes,
            "want",
        ),
    ]
    assert balance == pytest.approx(90)
    assert marker_count == 2


def test_paused_schedule_does_not_generate_transactions(temporary_app):
    app = temporary_app
    today = datetime.today().date()
    user_id, account_id = create_test_account(app)

    rule_id = create_daily_rule(
        app, user_id, account_id, today, active=0
    )

    app.process_recurring_transactions(user_id)

    with app.get_db() as conn:
        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        marker_count = conn.execute(
            """SELECT COUNT(*) FROM processed_schedule_occurrences
               WHERE recurring_rule_id = ?""",
            (rule_id,),
        ).fetchone()[0]

        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

    assert transaction_count == 0
    assert marker_count == 0
    assert balance == pytest.approx(100)