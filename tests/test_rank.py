"""Tests for src.rank — the training streak."""

from datetime import date

from src import rank

TODAY = date(2026, 8, 3)


def d(day: int) -> date:
    return date(2026, 8, day)


class TestStreak:
    def test_consecutive_runs(self):
        runs = {d(1), d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 3

    def test_prescribed_rest_does_not_break_it(self):
        runs = {d(1), d(3)}
        rest = {d(2)}
        assert rank.streak(runs, rest, TODAY, since=d(1)) == 3

    def test_unscheduled_skip_breaks_it(self):
        runs = {d(1), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 1

    def test_today_counts_when_already_run(self):
        runs = {d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 2

    def test_today_not_yet_run_does_not_break_it(self):
        """Today is still in progress — the streak is measured to yesterday."""
        runs = {d(1), d(2)}
        assert rank.streak(runs, set(), TODAY, since=d(1)) == 2

    def test_stops_at_since_date(self):
        """Runs before the first prescription are history, not streak."""
        runs = {d(1), d(2), d(3)}
        assert rank.streak(runs, set(), TODAY, since=d(2)) == 2

    def test_zero_before_any_prescription(self):
        assert rank.streak({d(1), d(2)}, set(), TODAY, since=None) == 0

    def test_zero_when_nothing_recent(self):
        assert rank.streak({date(2026, 7, 1)}, set(), TODAY, since=d(1)) == 0
