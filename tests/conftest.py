"""Shared test fixtures.

Database tests must request temporary_app before accessing the database.
"""

from pathlib import Path

import pytest

import capstone_project_code as app


@pytest.fixture
def temporary_app(tmp_path, monkeypatch):
    """
    Gives one test an isolated SQLite database.

    - tmp_path is provided by pytest.
    - monkeypatch temporarily redirects the application's db_path.
    - The original path is restored after the test.
    - No application window is opened.
    """
    original_path = Path(app.db_path).resolve()
    test_path = (tmp_path / "test_budgeting_app.db").resolve()

    if test_path == original_path:
        raise RuntimeError(
            "Refusing to run a database test against the normal database."
        )

    # Redirect BEFORE calling any database setup function.
    monkeypatch.setattr(app, "db_path", str(test_path))

    app.create_db()

    yield app