"""Fail fast when generated portfolio artifacts violate core design assumptions."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
data = pd.read_csv(ROOT / "data" / "ab_test_users.csv")
results = json.loads((ROOT / "outputs" / "analysis_results.json").read_text(encoding="utf-8"))

required_columns = {
    "user_id", "group", "device_type", "country", "signup_date", "session_count",
    "converted", "revenue", "days_since_signup", "refund_rate",
}
assert len(data) == 50_000
assert data.user_id.nunique() == 50_000
assert required_columns.issubset(data.columns)
assert data.isna().sum().sum() == 0
assert set(data.group) == {"control", "treatment"}
assert data.groupby("group").size().to_dict() == {"control": 25_000, "treatment": 25_000}
assert 0.015 <= results["conversion"]["absolute_lift"] <= 0.020
assert results["refund"]["refund_p_value"] >= 0.05
assert results["srm"]["p_value"] >= 0.01
assert (ROOT / "notebooks" / "ab_test_analysis.ipynb").exists()
assert (ROOT / "docs" / "executive_summary.md").exists()
print("Validation passed: dataset, effect range, guardrail, SRM, and deliverables.")
