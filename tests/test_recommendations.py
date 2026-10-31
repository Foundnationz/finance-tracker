"""Recommendation calculation tests using isolated databases."""

from datetime import date

import pytest


def create_test_account(app):
    """Creates a fictional user and account for calculation fixtures."""
    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO users (username, email, password)
               VALUES (?, ?, ?)""",
            ("testuser", "test@example.com", "test-only-placeholder"),
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO accounts (user_id, account_name, balance)
               VALUES (?, 'Test Account', 100)""",
            (user_id,),
        )
        account_id = cursor.lastrowid
        conn.commit()

    return user_id, account_id


def insert_transaction(
    conn,
    user_id,
    account_id,
    category,
    amount,
    tx_date,
    tx_type="expense",
    necessity="unset",
):
    """Inserts a query fixture without simulating balance accounting."""
    conn.execute(
        """INSERT INTO transactions
           (user_id, account_id, type, category, amount,
            date, time, necessity)
           VALUES (?, ?, ?, ?, ?, ?, '12:00', ?)""",
        (
            user_id,
            account_id,
            tx_type,
            category,
            amount,
            tx_date,
            necessity,
        ),
    )


def test_budget_allowance_excludes_future_expenses(temporary_app):
    app = temporary_app
    user_id, account_id = create_test_account(app)

    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO budgets
               (user_id, budget_name, timeframe, start_date,
                end_date, category, amount)
               VALUES (?, 'Food Budget', 'Monthly',
                       '2026-08-01', '2026-09-01', 'Food', 200)""",
            (user_id,),
        )
        budget_id = cursor.lastrowid

        insert_transaction(
            conn, user_id, account_id,
            "Food", 80, "2026-08-10",
        )

        # Must not count through the reference date of 22 August.
        insert_transaction(
            conn, user_id, account_id,
            "Food", 999, "2026-08-23",
        )

        conn.commit()

    results = app.get_budget_recommendations(
        user_id,
        reference_date=date(2026, 8, 22),
    )
    insight = next(
        item for item in results
        if item["budget_id"] == budget_id
    )

    assert insight["spent"] == pytest.approx(80)
    assert insight["remaining"] == pytest.approx(120)
    assert insight["days_remaining"] == 10
    assert insight["daily_allowance"] == pytest.approx(12)
    assert insight["severity"] == "allowance"

    with app.get_db() as conn:
        balance = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()[0]

        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

    assert balance == pytest.approx(100)
    assert transaction_count == 2


def test_category_comparison_handles_zero_baseline(temporary_app):
    app = temporary_app
    user_id, account_id = create_test_account(app)

    with app.get_db() as conn:
        fixtures = [
            ("Entertainment", 200, "2026-07-10", "expense"),
            ("Entertainment", 300, "2026-08-10", "expense"),
            ("Travel", 50, "2026-08-15", "expense"),

            # Outside the matched comparison ranges.
            ("Entertainment", 900, "2026-07-16", "expense"),
            ("Entertainment", 800, "2026-08-16", "expense"),

            # Income must not contribute to expense comparisons.
            ("Entertainment", 700, "2026-08-10", "income"),
        ]

        for category, amount, tx_date, tx_type in fixtures:
            insert_transaction(
                conn,
                user_id,
                account_id,
                category,
                amount,
                tx_date,
                tx_type=tx_type,
            )

        conn.commit()

    result = app.get_category_spending_recommendations(
        user_id,
        2026,
        8,
        reference_date=date(2026, 8, 15),
    )

    by_category = {
        item["category"]: item
        for item in result["recommendations"]
    }

    entertainment = by_category["Entertainment"]

    assert entertainment["selected_amount"] == pytest.approx(300)
    assert entertainment["previous_amount"] == pytest.approx(200)
    assert entertainment["increase"] == pytest.approx(100)
    assert entertainment["percentage_increase"] == pytest.approx(50)

    travel = by_category["Travel"]

    assert travel["selected_amount"] == pytest.approx(50)
    assert travel["previous_amount"] == pytest.approx(0)
    assert travel["percentage_increase"] is None

    assert result["periods"]["selected_last_day"] == date(2026, 8, 15)
    assert result["periods"]["previous_last_day"] == date(2026, 7, 15)


def test_needs_wants_keeps_unclassified_separate(temporary_app):
    app = temporary_app
    user_id, account_id = create_test_account(app)

    with app.get_db() as conn:
        fixtures = [
            (900, "need", "2026-08-05", "expense"),
            (600, "want", "2026-08-06", "expense"),
            (200, "unset", "2026-08-07", "expense"),

            # Excluded because it is future-dated.
            (999, "want", "2026-08-20", "expense"),

            # Excluded because it is income.
            (500, "unset", "2026-08-05", "income"),
        ]

        for amount, necessity, tx_date, tx_type in fixtures:
            insert_transaction(
                conn,
                user_id,
                account_id,
                "Testing",
                amount,
                tx_date,
                tx_type=tx_type,
                necessity=necessity,
            )

        conn.commit()

    result = app.get_needs_wants_reflection(
        user_id,
        2026,
        8,
        reference_date=date(2026, 8, 15),
    )

    assert result["need_total"] == pytest.approx(900)
    assert result["want_total"] == pytest.approx(600)
    assert result["unclassified_total"] == pytest.approx(200)
    assert result["classified_total"] == pytest.approx(1500)
    assert result["total_expenses"] == pytest.approx(1700)

    assert result["need_percent_of_classified"] == pytest.approx(60)
    assert result["want_percent_of_classified"] == pytest.approx(40)
    assert result["counted_through"] == "2026-08-15"

    # An empty period must not cause division by zero.
    empty = app.get_needs_wants_reflection(
        user_id,
        2026,
        1,
        reference_date=date(2026, 8, 15),
    )

    assert empty["total_expenses"] == 0
    assert empty["need_percent_of_classified"] is None
    assert empty["want_percent_of_classified"] is None