import pytest

from pricekit.cli import load_prices, main, render_markdown


@pytest.fixture
def price_csv(tmp_path):
    path = tmp_path / "demo.csv"
    path.write_text("day,close\n1,100.0\n2,110.0\n3,99.0\n")
    return path


def test_load_prices(price_csv):
    assert load_prices(price_csv) == [100.0, 110.0, 99.0]


def test_load_prices_rejects_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("day,open\n1,100.0\n")
    with pytest.raises(ValueError, match="close"):
        load_prices(bad)


def test_render_markdown_is_a_table():
    report = render_markdown("demo", {
        "count": 3.0, "first": 100.0, "last": 99.0,
        "total_return": -0.01, "best_period": 0.1,
        "worst_period": -0.1, "max_drawdown": 0.1,
    })
    assert report.startswith("## Summary for demo")
    assert "| Max drawdown |" in report


def test_main_writes_file(price_csv, tmp_path, capsys):
    out = tmp_path / "reports" / "demo.md"
    assert main([str(price_csv), "-o", str(out)]) == 0
    assert out.exists()
    assert "Summary for demo" in out.read_text()


def test_main_prints_to_stdout(price_csv, capsys):
    assert main([str(price_csv)]) == 0
    assert "Max drawdown" in capsys.readouterr().out


def test_main_returns_error_code_for_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv")]) == 1
    assert "error:" in capsys.readouterr().err
