"""
Novy-Marx (2012) Signal Calculation Engine.
Calculates intermediate momentum (r_12_7), recent momentum (r_6_2),
standard momentum (r_12_2), and short-term reversal (r_1_0) at monthly rebalance dates.
"""

import pandas as pd
import numpy as np

def compute_monthly_returns_and_prices(daily_prices):
    """
    Resample daily prices to month-end prices.
    Uses last available trading day of each month.
    """
    monthly_prices = daily_prices.resample('ME').last()
    # Drop months with all NaN
    monthly_prices = monthly_prices.dropna(how='all')
    monthly_returns = monthly_prices.pct_change()
    return monthly_prices, monthly_returns

def compute_novy_marx_signals(monthly_prices):
    """
    Computes Novy-Marx (2012) signals at each month-end t:
    - r_12_7: Intermediate momentum = P_{t-6} / P_{t-12} - 1 (returns from month t-12 to t-6)
    - r_6_2:  Recent momentum       = P_{t-1} / P_{t-6} - 1  (returns from month t-6 to t-1)
    - r_12_2: Standard momentum     = P_{t-1} / P_{t-12} - 1 (returns from month t-12 to t-1)
    - r_1_0:  Short-term reversal   = P_t / P_{t-1} - 1      (returns from month t-1 to t)
    
    Zero lookahead bias guaranteed: at time t, P_t is the latest close.
    """
    # Lagged price matrices
    p_t = monthly_prices
    p_t_minus_1 = monthly_prices.shift(1)
    p_t_minus_6 = monthly_prices.shift(6)
    p_t_minus_12 = monthly_prices.shift(12)

    r_12_7 = (p_t_minus_6 / p_t_minus_12) - 1.0
    r_6_2 = (p_t_minus_1 / p_t_minus_6) - 1.0
    r_12_2 = (p_t_minus_1 / p_t_minus_12) - 1.0
    r_1_0 = (p_t / p_t_minus_1) - 1.0

    return {
        "r_12_7": r_12_7,
        "r_6_2": r_6_2,
        "r_12_2": r_12_2,
        "r_1_0": r_1_0,
        "monthly_prices": monthly_prices
    }

def cross_sectional_rank(signal_df, min_stocks=50):
    """
    Computes cross-sectional percentile ranks [0, 1] for each date.
    Higher rank = stronger signal.
    """
    ranks = signal_df.rank(axis=1, pct=True, ascending=True)
    # Mask dates where valid stock count < min_stocks
    valid_counts = signal_df.notna().sum(axis=1)
    ranks = ranks.where(valid_counts >= min_stocks, np.nan)
    return ranks

def cross_sectional_zscore(signal_df, winsorize_std=3.0):
    """
    Computes cross-sectional z-score with winsorization.
    """
    mean = signal_df.mean(axis=1)
    std = signal_df.std(axis=1)
    z = signal_df.sub(mean, axis=0).div(std, axis=0)
    if winsorize_std is not None:
        z = z.clip(lower=-winsorize_std, upper=winsorize_std)
    return z
