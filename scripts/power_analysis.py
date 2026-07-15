"""Reproduce the experiment's two-proportion power calculation."""

import math
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


CONTROL_RATE = 0.13
TREATMENT_RATE = 0.145
ALPHA = 0.05
POWER = 0.80

effect_size = proportion_effectsize(TREATMENT_RATE, CONTROL_RATE)
per_arm = math.ceil(NormalIndPower().solve_power(effect_size=effect_size, power=POWER, alpha=ALPHA, ratio=1, alternative="two-sided"))
total_with_buffer = math.ceil((2 * per_arm) / 0.90)
print(f"Required per arm: {per_arm:,}")
print(f"Total with 10% buffer: {total_with_buffer:,}")

