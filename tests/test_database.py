"""Database setup tests using isolated temporary databases."""

from pathlib import Path

import pytest
import sqlite3


def test_database_is_created_in_temporary_folder(temporary_app, tmp_path):
    app = temporary_app

    actual_path = Path(app.db_path).resolve()
    expected_path = (tmp_path / "test_budgeting_app.db").resolve()

    assert actual_path == expected_path
    assert actual_path.is_file()


def test_database_setup_can_run_repeatedly(temporary_app):
    app = temporary_app

    # The fixture already called create_db() once.
    app.create_db()

    with app.get_db() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_required_tables_exist(temporary_app):
    app = temporary_app

    expected_tables = {
        "users",
        "accounts",
        "budgets",
        "transactions",
        "categories",
        "subscriptions",
        "wishlist",
        "settings",
        "tags",
        "recurring_transactions",
        "badges",
        "processed_schedule_occurrences",
        "budget_monthly_history",
    }

    with app.get_db() as conn:
        actual_tables = {
            row[0]
            for row in conn.execute(
                """SELECT name
                   FROM sqlite_master
                   WHERE type = 'table'"""
            ).fetchall()
        }

    assert expected_tables.issubset(actual_tables)


def test_required_transaction_columns_exist(temporary_app):
    app = temporary_app

    expected_columns = {
        "notes",
        "reference",
        "necessity",
        "recurring_rule_id",
        "subscription_id",
    }

    with app.get_db() as conn:
        actual_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(transactions)"
            ).fetchall()
        }

    assert expected_columns.issubset(actual_columns)


def test_foreign_keys_are_enabled(temporary_app):
    app = temporary_app

    with app.get_db() as conn:
        enabled = conn.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

        assert enabled == 1

        # A financial account cannot reference a nonexistent user.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO accounts
                   (user_id, account_name, balance)
                   VALUES (?, ?, ?)""",
                (999999, "Invalid Test Account", 100),
            )

        conn.rollback()


def test_repeated_setup_preserves_existing_records(temporary_app):
    app = temporary_app

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

        conn.execute(
            """INSERT INTO accounts
               (user_id, account_name, balance)
               VALUES (?, ?, ?)""",
            (user_id, "Test Account", 123.45),
        )
        conn.commit()

    app.create_db()

    with app.get_db() as conn:
        account = conn.execute(
            """SELECT account_name, balance
               FROM accounts
               WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

    assert account is not None
    assert account[0] == "Test Account"
    assert account[1] == pytest.approx(123.45)