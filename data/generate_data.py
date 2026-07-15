"""Generate a deterministic user-level dataset for a checkout A/B test."""

from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260715
N_USERS = 50_000
EXPERIMENT_START = pd.Timestamp("2026-04-01")
EXPERIMENT_DAYS = 28


def sigmoid(values: np.ndarray) -> np.ndarray:
    """Convert log-odds to probabilities."""
    return 1 / (1 + np.exp(-values))


def generate_experiment_data() -> pd.DataFrame:
    """Simulate randomized assignment, conversion, revenue, and refunds."""
    rng = np.random.default_rng(SEED)

    # Exact balance makes the intended randomization clear; the notebook still tests SRM.
    groups = np.repeat(["control", "treatment"], N_USERS // 2)
    rng.shuffle(groups)
    devices = rng.choice(["mobile", "desktop", "tablet"], N_USERS, p=[0.58, 0.34, 0.08])
    countries = rng.choice(["US", "UK", "CA", "DE", "AU"], N_USERS, p=[0.46, 0.18, 0.14, 0.13, 0.09])

    signup_age = np.clip(rng.exponential(scale=300, size=N_USERS).astype(int), 0, 1_825)
    signup_dates = EXPERIMENT_START - pd.to_timedelta(signup_age, unit="D")
    exposure_day = rng.integers(0, EXPERIMENT_DAYS, size=N_USERS)
    exposure_dates = EXPERIMENT_START + pd.to_timedelta(exposure_day, unit="D")
    days_since_signup = (exposure_dates - signup_dates).days

    account_maturity = np.log1p(days_since_signup) / np.log(1_826)
    session_lambda = 1.8 + 3.2 * account_maturity
    session_count = np.maximum(1, rng.poisson(session_lambda))

    device_effect = pd.Series(devices).map({"mobile": -0.28, "desktop": 0.18, "tablet": -0.08}).to_numpy()
    country_effect = pd.Series(countries).map({"US": 0.10, "UK": 0.02, "CA": 0.00, "DE": -0.12, "AU": 0.04}).to_numpy()
    # A log-odds treatment effect produces roughly +1.7 percentage points overall.
    treatment_effect = (groups == "treatment") * 0.125
    log_odds = -2.05 + device_effect + country_effect + 0.11 * np.log1p(session_count) + 0.20 * account_maturity + treatment_effect
    conversion_probability = sigmoid(log_odds)
    converted = rng.random(N_USERS) < conversion_probability

    country_multiplier = pd.Series(countries).map({"US": 1.05, "UK": 0.98, "CA": 1.00, "DE": 0.93, "AU": 1.02}).to_numpy()
    order_value = rng.lognormal(mean=4.15, sigma=0.55, size=N_USERS) * country_multiplier
    revenue = np.where(converted, order_value, 0.0).round(2)

    # Refund propensity is intentionally independent of treatment assignment.
    refund_probability = np.clip(0.055 + 0.012 * (devices == "mobile") + 0.006 * (countries == "DE"), 0, 1)
    refunded = converted & (rng.random(N_USERS) < refund_probability)

    return pd.DataFrame(
        {
            "user_id": [f"U{i:06d}" for i in range(1, N_USERS + 1)],
            "group": groups,
            "device_type": devices,
            "country": countries,
            "signup_date": signup_dates,
            "exposure_date": exposure_dates,
            "session_count": session_count,
            "converted": converted,
            "revenue": revenue,
            "days_since_signup": days_since_signup,
            "refund_rate": refunded.astype(int),
        }
    )


if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent / "ab_test_users.csv"
    data = generate_experiment_data()
    data.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(data):,} rows to {output_path}")
