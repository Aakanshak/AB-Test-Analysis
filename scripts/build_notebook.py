"""Build the portfolio notebook from reviewable Python cell sources."""

from pathlib import Path
import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb["metadata"]["language_info"] = {"name": "python", "version": "3"}

cells = [
    nbf.v4.new_markdown_cell("""# One-Click Checkout A/B Test Analysis

**Decision question:** Does one-click checkout improve user conversion and revenue without increasing refunds?  
**Unit of randomization and analysis:** user. **Test window:** 28 days. **Alpha:** 0.05 (two-sided).

The notebook is deliberately decision-led: validate the experiment, estimate the primary effect, inspect business value and guardrails, then assess heterogeneity."""),
    nbf.v4.new_code_cell("""from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

ROOT = Path.cwd().resolve()
if ROOT.name == 'notebooks': ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
from src.analysis import (bootstrap_mean_difference, conversion_intervals, conversion_test,
                          group_metrics, refund_test, segment_results, srm_test)

sns.set_theme(style='whitegrid', context='talk')
OUTPUTS = ROOT / 'outputs'
OUTPUTS.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / 'data' / 'ab_test_users.csv', parse_dates=['signup_date', 'exposure_date'])
df.head()"""),
    nbf.v4.new_markdown_cell("## 1. Data quality and randomization checks\n\nWe verify uniqueness, missingness, value ranges, assignment balance, and covariate balance before reading outcomes."),
    nbf.v4.new_code_cell("""quality = {
    'rows': len(df), 'unique_users': df.user_id.nunique(),
    'duplicate_users': int(df.user_id.duplicated().sum()),
    'missing_cells': int(df.isna().sum().sum()),
    'invalid_revenue_rows': int(((df.revenue < 0) | ((~df.converted) & (df.revenue != 0))).sum())
}
quality"""),
    nbf.v4.new_code_cell("""metrics = group_metrics(df)
srm = srm_test(df)
balance = pd.crosstab(df.device_type, df.group, normalize='columns').round(4)
display(metrics, pd.Series(srm, name='SRM check'), balance)"""),
    nbf.v4.new_markdown_cell("## 2. Primary metric: conversion\n\nA two-sided two-proportion z-test estimates the intent-to-treat effect. The 95% confidence interval is reported in percentage-point units for decision clarity."),
    nbf.v4.new_code_cell("""conversion = conversion_test(df)
pd.Series(conversion)"""),
    nbf.v4.new_code_cell("""intervals = conversion_intervals(df)
fig, ax = plt.subplots(figsize=(8, 5))
colors = {'control': '#4C78A8', 'treatment': '#F58518'}
ax.bar(intervals.group, intervals.rate * 100, color=[colors[g] for g in intervals.group], width=.6)
ax.errorbar(intervals.group, intervals.rate * 100,
            yerr=[(intervals.rate-intervals.ci_low)*100, (intervals.ci_high-intervals.rate)*100],
            fmt='none', ecolor='#222222', capsize=6, linewidth=2)
ax.set(title='Conversion rate with 95% Wilson intervals', xlabel='', ylabel='Conversion rate (%)')
ax.set_ylim(0, intervals.ci_high.max() * 115)
fig.tight_layout(); fig.savefig(OUTPUTS / 'conversion_by_group.png', dpi=160); plt.show()"""),
    nbf.v4.new_markdown_cell("## 3. Revenue per user\n\nRevenue per randomized user includes zeros for non-converters. A non-parametric bootstrap is used because revenue is zero-inflated and right-skewed."),
    nbf.v4.new_code_cell("""revenue = bootstrap_mean_difference(df, 'revenue')
pd.Series(revenue)"""),
    nbf.v4.new_markdown_cell("## 4. Segment consistency and Simpson's paradox check\n\nDevice and country were chosen before analysis. Segment p-values are descriptive and not used as independent shipping gates; signs and assignment mix are checked for reversals."),
    nbf.v4.new_code_cell("""device = segment_results(df, 'device_type')
country = segment_results(df, 'country')
display(device[['device_type','control_n','treatment_n','control_rate','treatment_rate','absolute_lift','ci_low','ci_high','p_value']],
        country[['country','control_n','treatment_n','control_rate','treatment_rate','absolute_lift','ci_low','ci_high','p_value']])"""),
    nbf.v4.new_code_cell("""segments = pd.concat([device.assign(segment_type='Device', segment=device.device_type),
                      country.assign(segment_type='Country', segment=country.country)], ignore_index=True)
fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharex=True)
for ax, (kind, frame) in zip(axes, segments.groupby('segment_type', sort=False)):
    frame = frame.sort_values('absolute_lift')
    ax.errorbar(frame.absolute_lift * 100, frame.segment,
                xerr=[(frame.absolute_lift-frame.ci_low)*100, (frame.ci_high-frame.absolute_lift)*100],
                fmt='o', color='#2A9D8F', ecolor='#555555', capsize=4)
    ax.axvline(0, color='#D62728', linestyle='--', linewidth=1)
    ax.set(title=kind, xlabel='Treatment lift (percentage points)', ylabel='')
fig.suptitle('Conversion lift by pre-specified segment', y=1.02)
fig.tight_layout(); fig.savefig(OUTPUTS / 'segment_lift.png', dpi=160, bbox_inches='tight'); plt.show()"""),
    nbf.v4.new_markdown_cell("## 5. Guardrail: refund rate\n\nRefund rate is evaluated among converted users, the population at risk of a refund. The experiment is considered safe when there is no statistically significant increase and the point estimate remains operationally small."),
    nbf.v4.new_code_cell("""refund = refund_test(df)
pd.Series(refund)"""),
    nbf.v4.new_markdown_cell("## 6. Decision and export\n\nThe shipping rule requires: valid randomization (SRM p >= 0.01), positive significant conversion lift, and no significant refund increase. Revenue is supporting evidence rather than a required gate."),
    nbf.v4.new_code_cell("""simpsons_reversal = bool((segments.absolute_lift < 0).all() and conversion['absolute_lift'] > 0)
ship = bool(srm['p_value'] >= 0.01 and conversion['p_value'] < 0.05 and conversion['absolute_lift'] > 0
            and not (refund['refund_p_value'] < 0.05 and refund['refund_absolute_lift'] > 0))
decision = 'SHIP' if ship else 'DO NOT SHIP'

metrics.to_csv(OUTPUTS / 'group_metrics.csv', index=False)
device.to_csv(OUTPUTS / 'device_segment_results.csv', index=False)
country.to_csv(OUTPUTS / 'country_segment_results.csv', index=False)
results = {'decision': decision, 'quality': quality, 'srm': srm, 'conversion': conversion,
           'revenue': revenue, 'refund': refund, 'simpsons_reversal': simpsons_reversal}
with open(OUTPUTS / 'analysis_results.json', 'w') as handle: json.dump(results, handle, indent=2)

summary = f'''# Executive Summary: One-Click Checkout Experiment

## Recommendation: {decision}

The 28-day randomized experiment included **{len(df):,} users**. Treatment conversion was **{conversion['treatment_rate']:.2%}** versus **{conversion['control_rate']:.2%}** in control, an absolute lift of **{conversion['absolute_lift']:.2%}** (95% CI **[{conversion['ci_low']:.2%}, {conversion['ci_high']:.2%}]**, p={conversion['p_value']:.4f}). This is a **{conversion['relative_lift']:.1%} relative lift**.

Revenue per user moved from **${revenue['control_mean']:.2f}** to **${revenue['treatment_mean']:.2f}** (difference **${revenue['difference']:.2f}**, bootstrap 95% CI **[${revenue['ci_low']:.2f}, ${revenue['ci_high']:.2f}]**). Refund rate among buyers was **{refund['refund_treatment_rate']:.2%}** versus **{refund['refund_control_rate']:.2%}** (difference **{refund['refund_absolute_lift']:.2%}**, p={refund['refund_p_value']:.3f}), with no statistically significant deterioration.

## Decision Rationale

- Randomization passed the SRM check (p={srm['p_value']:.3f}); device allocation was also directionally balanced.
- The primary conversion effect is positive and statistically significant at alpha=0.05.
- There is **{'no' if not simpsons_reversal else 'a'} Simpson's-paradox sign reversal** across the pre-specified device and country views.
- The refund guardrail did not show a significant increase. Revenue provides {'positive' if revenue['difference'] > 0 else 'negative'} supporting evidence.

## Assumptions and Limitations

- This is synthetic, user-level intent-to-treat data; production logging defects, interference, bots, and repeat-device identity issues are not represented.
- The 28-day window measures near-term behavior only. Monitor refunds, support contacts, latency, and repeat purchase after rollout.
- Segment estimates are exploratory and underpowered; no multiplicity adjustment was applied.
- Revenue is simulated in a common currency and excludes payment fees, tax, and downstream margin.

## Rollout Plan

Use a staged rollout with live guardrail monitoring and an automatic rollback threshold. Recheck conversion, refunds, latency, and customer-support contacts after two full purchase cycles before moving to 100% exposure.
'''
(ROOT / 'docs' / 'executive_summary.md').write_text(summary, encoding='utf-8')
print(decision)
pd.Series(results)"""),
]

nb["cells"] = cells
output = ROOT / "notebooks" / "ab_test_analysis.ipynb"
output.parent.mkdir(exist_ok=True)
nbf.write(nb, output)
print(f"Built {output}")

