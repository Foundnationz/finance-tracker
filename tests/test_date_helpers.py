"""Tests for date calculations. No GUI or database is used."""

from datetime import date

import pytest

from capstone_project_code import (
    get_budget_period,
    get_spending_comparison_periods,
    next_subscription_billing_date,
)


@pytest.mark.parametrize(
    "timeframe, reference, expected",
    [
        (
            "Daily",
            date(2026, 8, 22),
            (date(2026, 8, 22), date(2026, 8, 23), 1),
        ),
        (
            "Weekly",
            date(2026, 8, 22),
            (date(2026, 8, 17), date(2026, 8, 24), 2),
        ),
        (
            "Weekly",
            date(2026, 8, 23),
            (date(2026, 8, 17), date(2026, 8, 24), 1),
        ),
        (
            "Monthly",
            date(2026, 8, 22),
            (date(2026, 8, 1), date(2026, 9, 1), 10),
        ),
        (
            "Monthly",
            date(2028, 2, 28),
            (date(2028, 2, 1), date(2028, 3, 1), 2),
        ),
        (
            "Yearly",
            date(2026, 12, 31),
            (date(2026, 1, 1), date(2027, 1, 1), 1),
        ),
    ],
)
def test_budget_periods(timeframe, reference, expected):
    assert get_budget_period(timeframe, reference) == expected


def test_budget_period_rejects_unknown_timeframe():
    with pytest.raises(ValueError):
        get_budget_period("Unsupported", date(2026, 8, 22))


@pytest.mark.parametrize(
    "billing_days, reference, inclusive, expected",
    [
        ("1,15", date(2026, 7, 15), True, date(2026, 7, 15)),
        ("1,15", date(2026, 7, 15), False, date(2026, 8, 1)),
        ("31", date(2026, 4, 1), True, date(2026, 5, 31)),
        ("29", date(2027, 2, 1), True, date(2027, 3, 29)),
        ("29", date(2028, 2, 1), True, date(2028, 2, 29)),
        ("15,15", date(2026, 7, 15), False, date(2026, 8, 15)),
    ],
)
def test_subscription_billing_dates(
    billing_days, reference, inclusive, expected
):
    assert next_subscription_billing_date(
        billing_days,
        reference,
        inclusive=inclusive,
    ) == expected


@pytest.mark.parametrize(
    "billing_days",
    ["", "0", "32", "1,,15", "15,", "abc"],
)
def test_subscription_billing_rejects_invalid_days(billing_days):
    with pytest.raises(ValueError):
        next_subscription_billing_date(
            billing_days,
            date(2026, 8, 1),
        )


def test_current_month_comparison_uses_equal_elapsed_days():
    result = get_spending_comparison_periods(
        2026, 8, reference_date=date(2026, 8, 15)
    )

    assert result["selected_start"] == date(2026, 8, 1)
    assert result["selected_end"] == date(2026, 8, 16)
    assert result["previous_start"] == date(2026, 7, 1)
    assert result["previous_end"] == date(2026, 7, 16)
    assert result["selected_days"] == result["previous_days"] == 15


def test_short_previous_month_limits_current_comparison():
    result = get_spending_comparison_periods(
        2026, 3, reference_date=date(2026, 3, 31)
    )

    assert result["selected_last_day"] == date(2026, 3, 28)
    assert result["previous_last_day"] == date(2026, 2, 28)
    assert result["current_month_cutoff_limited"] is True


def test_completed_month_comparison_uses_full_months():
    result = get_spending_comparison_periods(
        2026, 3, reference_date=date(2026, 4, 10)
    )

    assert result["mode"] == "full_months"
    assert result["selected_days"] == 31
    assert result["previous_days"] == 28
    assert result["equal_day_counts"] is False


def test_january_comparison_crosses_year_boundary():
    result = get_spending_comparison_periods(
        2026, 1, reference_date=date(2026, 1, 5)
    )

    assert result["previous_start"] == date(2025, 12, 1)
    assert result["previous_last_day"] == date(2025, 12, 5)


def test_spending_comparison_rejects_future_month():
    with pytest.raises(ValueError):
        get_spending_comparison_periods(
            2026, 9, reference_date=date(2026, 8, 15)
        )