"""Monthly budget-history regression tests using temporary databases."""

from datetime import date

import pytest


def create_budget_fixture(app):
    """Creates a fictional user, account and monthly budget."""
    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO users (username, email, password)
               VALUES (?, ?, ?)""",
            ("testuser", "test@example.com", "test-only-placeholder"),
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO accounts (user_id, account_name, balance)
               VALUES (?, ?, ?)""",
            (user_id, "Test Account", 100),
        )
        account_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO budgets
               (user_id, budget_name, timeframe, start_date,
                end_date, category, amount)
               VALUES (?, 'History Test', 'Monthly',
                       '2026-08-01', '2026-09-01', 'Food', 700)""",
            (user_id,),
        )
        budget_id = cursor.lastrowid
        conn.commit()

    return user_id, account_id, budget_id


def test_same_month_save_replaces_settings(temporary_app):
    app = temporary_app
    user_id, _, budget_id = create_budget_fixture(app)

    with app.get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        app.record_monthly_budget_settings(
            conn,
            user_id,
            budget_id,
            reference_date=date(2026, 8, 5),
        )

        conn.execute(
            "UPDATE budgets SET amount = 850 WHERE id = ?",
            (budget_id,),
        )

        app.record_monthly_budget_settings(
            conn,
            user_id,
            budget_id,
            reference_date=date(2026, 8, 20),
        )
        conn.commit()

        rows = conn.execute(
            """SELECT effective_month, amount, category
               FROM budget_monthly_history
               WHERE budget_id = ?""",
            (budget_id,),
        ).fetchall()

    assert rows == [("2026-08-01", 850, "Food")]


def test_settings_carry_forward_without_using_future_changes(temporary_app):
    app = temporary_app
    user_id, _, budget_id = create_budget_fixture(app)

    with app.get_db() as conn:
        conn.executemany(
            """INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (user_id, budget_id, "2026-08-01", 700, "Food"),
                (user_id, budget_id, "2026-10-01", 900, "Travel"),
            ],
        )
        conn.commit()

        september = app.get_applicable_monthly_budget_settings(
            conn, user_id, budget_id, "2026-09-01"
        )
        october = app.get_applicable_monthly_budget_settings(
            conn, user_id, budget_id, "2026-10-01"
        )

    assert september["amount"] == 700
    assert september["category"] == "Food"
    assert september["effective_month"] == "2026-08-01"
    assert september["carried_forward"] is True

    assert october["amount"] == 900
    assert october["category"] == "Travel"
    assert october["carried_forward"] is False


def test_unknown_history_does_not_use_current_settings(temporary_app):
    app = temporary_app
    user_id, _, budget_id = create_budget_fixture(app)

    with app.get_db() as conn:
        conn.execute(
            """INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, '2026-08-01', 700, 'Food')""",
            (user_id, budget_id),
        )
        conn.commit()

        july = app.get_applicable_monthly_budget_settings(
            conn, user_id, budget_id, "2026-07-01"
        )

    assert july is None

    with pytest.raises(ValueError, match="unavailable"):
        app.get_budget_month_expenses(
            user_id, budget_id, "2026-07-01"
        )


def test_review_and_drill_down_use_historical_category(temporary_app):
    app = temporary_app
    user_id, account_id, budget_id = create_budget_fixture(app)

    with app.get_db() as conn:
        # Deliberately different current settings.
        conn.execute(
            """UPDATE budgets
               SET category = 'Other', amount = 9999
               WHERE id = ?""",
            (budget_id,),
        )

        conn.executemany(
            """INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (user_id, budget_id, "2026-07-01", 700, "Food"),
                (user_id, budget_id, "2026-08-01", 850, "Travel"),
            ],
        )

        expenses = [
            ("Food", 820, "2026-07-10"),
            ("Travel", 999, "2026-07-10"),
            ("Travel", 900, "2026-08-10"),
            ("Food", 999, "2026-08-10"),
        ]

        for category, amount, tx_date in expenses:
            conn.execute(
                """INSERT INTO transactions
                   (user_id, account_id, type, category,
                    amount, date, time)
                   VALUES (?, ?, 'expense', ?, ?, ?, '12:00')""",
                (user_id, account_id, category, amount, tx_date),
            )

        conn.commit()

    report = app.get_historical_budget_review(
        user_id, reference_date=date(2026, 9, 15)
    )
    review = next(
        item for item in report["reviews"]
        if item["budget_id"] == budget_id
    )
    months = {
        month["period_start"]: month
        for month in review["months"]
    }

    june = months["2026-06-01"]
    assert june["settings_known"] is False
    assert june["spent"] is None

    july = months["2026-07-01"]
    assert july["category"] == "Food"
    assert july["applicable_limit"] == 700
    assert july["spent"] == 820

    august = months["2026-08-01"]
    assert august["category"] == "Travel"
    assert august["applicable_limit"] == 850
    assert august["spent"] == 900

    assert review["months_with_known_settings"] == 2
    assert review["months_above_limit"] == 2
    assert review["review_recommended"] is True

    july_detail = app.get_budget_month_expenses(
        user_id, budget_id, "2026-07-01"
    )
    august_detail = app.get_budget_month_expenses(
        user_id, budget_id, "2026-08-01"
    )

    assert july_detail["total"] == july["spent"]
    assert august_detail["total"] == august["spent"]
    assert july_detail["entry_count"] == 1
    assert august_detail["entry_count"] == 1

    with app.get_db() as conn:
        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

    assert balance == pytest.approx(100)


def test_budget_deletion_removes_history_not_transactions(temporary_app):
    app = temporary_app
    user_id, account_id, budget_id = create_budget_fixture(app)

    with app.get_db() as conn:
        conn.execute(
            """INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, '2026-08-01', 700, 'Food')""",
            (user_id, budget_id),
        )

        conn.execute(
            """INSERT INTO transactions
               (user_id, account_id, type, category, amount, date, time)
               VALUES (?, ?, 'expense', 'Food', 10,
                       '2026-08-10', '12:00')""",
            (user_id, account_id),
        )
        conn.commit()

        conn.execute(
            "DELETE FROM budgets WHERE id = ? AND user_id = ?",
            (budget_id, user_id),
        )
        conn.commit()

        history_count = conn.execute(
            """SELECT COUNT(*) FROM budget_monthly_history
               WHERE budget_id = ?""",
            (budget_id,),
        ).fetchone()[0]

        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

        foreign_key_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    assert history_count == 0
    assert transaction_count == 1
    assert balance == pytest.approx(100)
    assert foreign_key_errors == []