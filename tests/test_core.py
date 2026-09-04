import pytest

from pricekit.core import (
    max_drawdown,
    position_size,
    returns,
    sma,
    summarize,
)


class TestSma:
    def test_window_of_one_is_the_series(self):
        assert sma([1, 2, 3], 1) == [1.0, 2.0, 3.0]

    def test_rolling_average(self):
        assert sma([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]

    def test_output_length(self):
        assert len(sma(list(range(10)), 3)) == 8

    @pytest.mark.parametrize("window", [0, -1])
    def test_rejects_nonpositive_window(self, window):
        with pytest.raises(ValueError, match="positive"):
            sma([1, 2, 3], window)

    def test_rejects_oversized_window(self):
        with pytest.raises(ValueError, match="longer"):
            sma([1, 2], 5)


class TestReturns:
    def test_simple_returns(self):
        assert returns([100, 110]) == pytest.approx([0.1])

    def test_negative_return(self):
        assert returns([100, 90]) == pytest.approx([-0.1])

    def test_length_is_one_less(self):
        assert len(returns([1, 2, 3, 4])) == 3

    def test_rejects_short_series(self):
        with pytest.raises(ValueError, match="two prices"):
            returns([100])

    def test_rejects_nonpositive_price(self):
        with pytest.raises(ValueError, match="positive"):
            returns([100, 0])


class TestMaxDrawdown:
    def test_monotonic_rise_has_no_drawdown(self):
        assert max_drawdown([1, 2, 3, 4]) == 0.0

    def test_halving_is_fifty_percent(self):
        assert max_drawdown([100, 50, 75]) == pytest.approx(0.5)

    def test_uses_worst_not_last(self):
        assert max_drawdown([100, 40, 90, 80]) == pytest.approx(0.6)

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            max_drawdown([])


class TestPositionSize:
    def test_basic_sizing(self):
        # 1% of 10000 = 100 risk, 2.00 per share -> 50 shares
        assert position_size(10_000, 0.01, 50.0, 48.0) == 50

    def test_rounds_down(self):
        assert position_size(10_000, 0.01, 50.0, 47.0) == 33

    def test_direction_does_not_matter(self):
        assert position_size(10_000, 0.01, 48.0, 50.0) == 50

    @pytest.mark.parametrize("risk", [0.0, 1.0, 1.5, -0.1])
    def test_rejects_bad_risk(self, risk):
        with pytest.raises(ValueError, match="risk_pct"):
            position_size(10_000, risk, 50.0, 48.0)

    def test_rejects_equal_entry_and_stop(self):
        with pytest.raises(ValueError, match="differ"):
            position_size(10_000, 0.01, 50.0, 50.0)


class TestSummarize:
    def test_report_keys(self):
        stats = summarize([100, 110, 105])
        assert set(stats) == {
            "count",
            "first",
            "last",
            "total_return",
            "best_period",
            "worst_period",
            "max_drawdown",
        }

    def test_total_return(self):
        stats = summarize([100, 110, 121])
        assert stats["total_return"] == pytest.approx(0.21)

    def test_worst_period_is_negative_when_price_falls(self):
        assert summarize([100, 90, 95])["worst_period"] < 0
