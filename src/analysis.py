"""Reusable analysis functions used by the portfolio notebook."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_confint, proportions_ztest


def group_metrics(data: pd.DataFrame) -> pd.DataFrame:
    """Return decision metrics at the randomized user level."""
    return (
        data.groupby("group", observed=True)
        .agg(users=("user_id", "nunique"), conversions=("converted", "sum"), conversion_rate=("converted", "mean"), revenue_per_user=("revenue", "mean"))
        .reset_index()
    )


def srm_test(data: pd.DataFrame) -> dict[str, float]:
    """Chi-square goodness-of-fit test against the planned 50/50 allocation."""
    observed = data["group"].value_counts().reindex(["control", "treatment"]).to_numpy()
    statistic, p_value = stats.chisquare(observed, f_exp=np.repeat(observed.sum() / 2, 2))
    return {"chi_square": float(statistic), "p_value": float(p_value)}


def conversion_test(data: pd.DataFrame) -> dict[str, float]:
    """Two-sided two-proportion z-test and 95% CI for treatment minus control."""
    summary = data.groupby("group")["converted"].agg(["sum", "count"])
    counts = summary.loc[["treatment", "control"], "sum"].to_numpy()
    nobs = summary.loc[["treatment", "control"], "count"].to_numpy()
    statistic, p_value = proportions_ztest(counts, nobs, alternative="two-sided")
    low, high = confint_proportions_2indep(counts[0], nobs[0], counts[1], nobs[1], method="wald")
    rates = counts / nobs
    return {
        "control_rate": float(rates[1]), "treatment_rate": float(rates[0]),
        "absolute_lift": float(rates[0] - rates[1]), "relative_lift": float(rates[0] / rates[1] - 1),
        "z_statistic": float(statistic), "p_value": float(p_value), "ci_low": float(low), "ci_high": float(high),
    }


def bootstrap_mean_difference(data: pd.DataFrame, column: str, iterations: int = 5_000, seed: int = 42) -> dict[str, float]:
    """Bootstrap treatment-minus-control mean difference using vectorized resampling."""
    rng = np.random.default_rng(seed)
    control = data.loc[data.group == "control", column].to_numpy()
    treatment = data.loc[data.group == "treatment", column].to_numpy()
    batch_size = 250
    differences = []
    for start in range(0, iterations, batch_size):
        size = min(batch_size, iterations - start)
        control_means = rng.choice(control, (size, len(control)), replace=True).mean(axis=1)
        treatment_means = rng.choice(treatment, (size, len(treatment)), replace=True).mean(axis=1)
        differences.extend(treatment_means - control_means)
    differences = np.asarray(differences)
    observed = treatment.mean() - control.mean()
    # Add-one correction avoids reporting p=0 from a finite Monte Carlo sample.
    lower_tail = ((differences <= 0).sum() + 1) / (iterations + 1)
    upper_tail = ((differences >= 0).sum() + 1) / (iterations + 1)
    p_value = min(1.0, 2 * min(lower_tail, upper_tail))
    return {"control_mean": float(control.mean()), "treatment_mean": float(treatment.mean()), "difference": float(observed), "ci_low": float(np.quantile(differences, 0.025)), "ci_high": float(np.quantile(differences, 0.975)), "p_value": float(p_value)}


def segment_results(data: pd.DataFrame, segment: str) -> pd.DataFrame:
    """Compute conversion lift and a z-test within each pre-specified segment."""
    rows = []
    for value, frame in data.groupby(segment, observed=True):
        result = conversion_test(frame)
        rows.append({segment: value, "control_n": int((frame.group == "control").sum()), "treatment_n": int((frame.group == "treatment").sum()), **result})
    return pd.DataFrame(rows).sort_values(segment).reset_index(drop=True)


def refund_test(data: pd.DataFrame) -> dict[str, float]:
    """Compare refund rates among converted users; non-buyers are not at risk."""
    buyers = data[data.converted].copy()
    result = conversion_test(buyers.rename(columns={"converted": "purchase", "refund_rate": "converted"}))
    return {f"refund_{key}": value for key, value in result.items()}


def conversion_intervals(data: pd.DataFrame) -> pd.DataFrame:
    """Wilson confidence intervals for each experiment arm."""
    rows = []
    for group, frame in data.groupby("group", observed=True):
        successes, total = int(frame.converted.sum()), len(frame)
        low, high = proportion_confint(successes, total, method="wilson")
        rows.append({"group": group, "rate": successes / total, "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)
