# One-Click Checkout A/B Test

An end-to-end product experiment analysis for an e-commerce checkout change, framed as an Advanced Business Analyst portfolio case. The project moves from experiment design and synthetic event generation through statistical inference, segmentation, guardrails, and an executive shipping decision.
Live Project:https://aakanshak.github.io/AB-Test-Analysis/
Github Repository:https://github.com/Aakanshak/AB-Test-Analysis

## Review This First

1. [`docs/executive_summary.md`](docs/executive_summary.md) for the decision and business implications.
2. [`notebooks/ab_test_analysis.ipynb`](notebooks/ab_test_analysis.ipynb) for the statistical workflow and visual evidence.
3. [`docs/experiment_design.md`](docs/experiment_design.md) for the pre-analysis logic and power assumptions.
4. [`sql/core_metrics.sql`](sql/core_metrics.sql) for a warehouse implementation of the analytical table.

## Repository Structure

```text
data/        Synthetic user-level data and its generator
docs/        Experiment design and one-page executive summary
notebooks/   Executed analysis notebook
outputs/     Machine-readable results, tables, and charts
scripts/     Notebook builder and power calculation
sql/         BigQuery Standard SQL for the core metrics table
src/         Reusable statistical functions
```

## Run Locally

```powershell
python -m pip install -r requirements.txt
python data/generate_data.py
python scripts/power_analysis.py
python scripts/build_notebook.py
jupyter nbconvert --to notebook --execute notebooks/ab_test_analysis.ipynb --output ab_test_analysis.ipynb --output-dir notebooks --ExecutePreprocessor.timeout=600
python scripts/validate_project.py
```

The pipeline is deterministic: data generation uses a fixed seed, and the bootstrap uses its own fixed seed. Re-running it should reproduce the committed outputs apart from harmless metadata differences.

## Analytical Approach

- Chi-square sample ratio mismatch test against planned 50/50 assignment.
- Two-proportion z-test and 95% confidence interval for conversion.
- Bootstrap confidence interval for zero-inflated revenue per randomized user.
- Pre-specified device and country cuts to assess effect consistency and Simpson's paradox risk.
- Refund-rate guardrail among converted users.

## Important Scope Note

The dataset is synthetic and designed to demonstrate a realistic decision workflow. It is not evidence that one-click checkout will cause the same effect in production. The summary explicitly separates simulated findings from rollout assumptions and monitoring needs.
