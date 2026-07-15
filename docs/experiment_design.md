# Experiment Design: One-Click Checkout

## Business Context

The current checkout requires customers to confirm shipping, payment, and order details across multiple interactions. Product proposes a one-click path for eligible signed-in users with saved payment and address information. The business goal is to reduce checkout friction while protecting customer trust and order quality.

## Hypothesis and Decision Rule

**Hypothesis:** Exposing eligible users to one-click checkout increases the probability of completing a purchase within 28 days of assignment.

- Null: treatment conversion equals control conversion.
- Alternative: treatment conversion differs from control conversion.
- Ship when the two-sided conversion test is significant at alpha=0.05, the estimate is positive, SRM p >= 0.01, and no guardrail shows a significant adverse movement.
- Revenue per user is supporting evidence because it is noisier and sensitive to a few large orders.

## Metrics

| Role | Metric | Definition |
|---|---|---|
| Primary | User conversion rate | Users with at least one order / randomized users |
| Secondary | Revenue per user | Net revenue / randomized users, including zero values |
| Guardrail | Refund rate | Buyers with at least one refund / converted users |
| Diagnostic | SRM | Chi-square test of observed allocation against 50/50 |

The user is both the randomization and analysis unit. Results follow intent-to-treat: all assigned users remain in their assigned arm.

## Power and Sample Size

The design assumes a 13.0% control conversion rate, a minimum detectable effect of **1.5 percentage points** (13.0% to 14.5%), 80% power, two-sided alpha=0.05, and equal allocation. `statsmodels.stats.power.NormalIndPower` yields **8,269 users per arm**; a 10% allowance for exclusions/logging loss gives a planning target of **18,376 total users**. The simulated 50,000-user sample comfortably exceeds this threshold and can detect smaller effects.

The exact calculation is reproducible in `scripts/power_analysis.py`.

## Duration and Exposure

Run for **28 days**, covering four complete weekly cycles. Each user is assigned once at first eligible exposure. Outcomes are measured for 28 days after exposure; assignment is sticky across devices where identity resolution permits. Do not stop early based on interim p-values.

## Risks and Pre-Launch Checks

- Validate exposure logging, mutually exclusive assignment, payment eligibility, and order deduplication in an A/A test.
- Monitor latency, payment errors, refunds, support contacts, and assignment balance daily.
- Freeze metric definitions and segments before launch. Device and country analyses are heterogeneity diagnostics, not separate claims of efficacy.
