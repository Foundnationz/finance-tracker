"""Authenticated account-deletion tests using temporary databases."""

import sqlite3

import pytest


@pytest.fixture
def deletion_users(temporary_app, monkeypatch):
    app = temporary_app
    password = "DeleteTest*123"
    password_hash = app.hash_password(password)

    with app.get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO users (username, email, password)
               VALUES (?, ?, ?)""",
            ("deleteuser", "delete@example.com", password_hash),
        )
        user_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO users (username, email, password)
               VALUES (?, ?, ?)""",
            ("keepuser", "keep@example.com", password_hash),
        )
        other_id = cursor.lastrowid

        cursor = conn.execute(
            """INSERT INTO accounts (user_id, account_name, balance)
               VALUES (?, 'Delete Account', 100)""",
            (user_id,),
        )
        account_id = cursor.lastrowid

        conn.execute(
            """INSERT INTO accounts (user_id, account_name, balance)
               VALUES (?, 'Keep Account', 200)""",
            (other_id,),
        )

        cursor = conn.execute(
            """INSERT INTO budgets
               (user_id, budget_name, timeframe, start_date,
                end_date, category, amount)
               VALUES (?, 'Delete Budget', 'Monthly',
                       '2026-08-01', '2026-09-01', 'Testing', 50)""",
            (user_id,),
        )
        budget_id = cursor.lastrowid

        conn.execute(
            """INSERT INTO budget_monthly_history
               (user_id, budget_id, effective_month, amount, category)
               VALUES (?, ?, '2026-08-01', 50, 'Testing')""",
            (user_id, budget_id),
        )

        cursor = conn.execute(
            """INSERT INTO transactions
               (user_id, account_id, type, category, amount, date, time)
               VALUES (?, ?, 'expense', 'Testing', 10,
                       '2026-08-10', '12:00')""",
            (user_id, account_id),
        )
        transaction_id = cursor.lastrowid

        conn.execute(
            """INSERT INTO tags (transaction_id, user_id, tag_name)
               VALUES (?, ?, 'test')""",
            (transaction_id, user_id),
        )

        conn.execute(
            "INSERT INTO settings (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()

        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    monkeypatch.setattr(app, "current_user", user)

    return app, user_id, other_id, password


def test_correct_password_deletes_only_active_user(deletion_users):
    app, user_id, other_id, password = deletion_users

    assert app.delete_current_user_data(user_id, password) is True

    with app.get_db() as conn:
        assert conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (user_id,)
        ).fetchone() is None

        assert conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (other_id,)
        ).fetchone() is not None

        other_balance = conn.execute(
            "SELECT balance FROM accounts WHERE user_id = ?",
            (other_id,),
        ).fetchone()[0]
        assert other_balance == 200

        for table in app.USER_DATA_DELETE_ORDER:
            count = conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE user_id = ?',
                (user_id,),
            ).fetchone()[0]
            assert count == 0, table

        assert conn.execute(
            """SELECT COUNT(*) FROM budget_monthly_history
               WHERE user_id = ?""",
            (user_id,),
        ).fetchone()[0] == 0

        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_wrong_password_preserves_data(deletion_users):
    app, user_id, _, _ = deletion_users

    with pytest.raises(ValueError, match="password is incorrect"):
        app.delete_current_user_data(user_id, "WrongPass*123")

    with app.get_db() as conn:
        assert conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (user_id,)
        ).fetchone() is not None

        assert conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0] == 1


def test_cannot_delete_another_user(deletion_users):
    app, _, other_id, password = deletion_users

    with pytest.raises(ValueError, match="active session"):
        app.delete_current_user_data(other_id, password)

    with app.get_db() as conn:
        assert conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (other_id,)
        ).fetchone() is not None


def test_database_failure_rolls_back_cleanup(deletion_users):
    app, user_id, _, password = deletion_users

    with app.get_db() as conn:
        # Force failure at the final user deletion, after earlier
        # cleanup statements have already run.
        conn.execute(
            """CREATE TRIGGER prevent_test_user_delete
               BEFORE DELETE ON users
               BEGIN
                   SELECT RAISE(ABORT, 'simulated deletion failure');
               END"""
        )
        conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        app.delete_current_user_data(user_id, password)

    with app.get_db() as conn:
        assert conn.execute(
            "SELECT 1 FROM users WHERE id = ?", (user_id,)
        ).fetchone() is not None

        assert conn.execute(
            "SELECT COUNT(*) FROM tags WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0] == 1

        assert conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0] == 1

        assert conn.execute(
            """SELECT COUNT(*) FROM budget_monthly_history
               WHERE user_id = ?""",
            (user_id,),
        ).fetchone()[0] == 1