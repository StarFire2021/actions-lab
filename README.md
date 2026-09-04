# actions-lab

A practice repository for learning GitHub Actions hands on.

`pricekit` is a tiny dependency-free Python package (moving averages, returns,
max drawdown, position sizing) that exists purely to give CI something real to
do: a fast deterministic test suite, a linter, and a CLI that produces a file
worth uploading as an artifact.

## Start here

Read [TUTORIAL.md](TUTORIAL.md). It is a nine-lab walkthrough that goes from a
workflow that does nothing to reusable workflows, approval gates, and a
tag-triggered release. The finished workflow file for each lab is in `labs/`.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                                  # 32 tests
ruff check .
pricekit data/sample_prices.csv         # prints a markdown report
pricekit data/sample_prices.csv -o reports/summary.md
```

## Layout

```
src/pricekit/       the package under test
tests/              pytest suite
data/               deterministic sample price series
labs/               one finished workflow per lab, with comments
TUTORIAL.md         the walkthrough
```

Each file in `labs/` has a header comment saying where to copy it. Nothing in
`labs/` runs on its own — GitHub only reads `.github/workflows/`.
