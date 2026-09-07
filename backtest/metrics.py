"""
Performance and Risk Analytics Module.
Computes institutional performance metrics, factor regressions (CAPM alpha & beta),
drawdowns, turnover statistics, and the mandatory Brindco arithmetic table.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import config

def compute_cagr(nav_series):
    if len(nav_series) < 2:
        return 0.0
    start_val = nav_series.iloc[0]
    end_val = nav_series.iloc[-1]
    days = (nav_series.index[-1] - nav_series.index[0]).days
    if days <= 0 or start_val <= 0:
        return 0.0
    years = days / 365.25
    return (end_val / start_val) ** (1.0 / years) - 1.0

def compute_volatility(ret_series, periods_per_year=12):
    return ret_series.std() * np.sqrt(periods_per_year)

def compute_sharpe(ret_series, rf_annual=config.ANNUAL_RISK_FREE_RATE, periods_per_year=12):
    rf_period = (1.0 + rf_annual) ** (1.0 / periods_per_year) - 1.0
    excess_ret = ret_series - rf_period
    vol = ret_series.std()
    if vol == 0 or np.isnan(vol):
        return 0.0
    return (excess_ret.mean() / vol) * np.sqrt(periods_per_year)

def compute_sortino(ret_series, rf_annual=config.ANNUAL_RISK_FREE_RATE, periods_per_year=12):
    rf_period = (1.0 + rf_annual) ** (1.0 / periods_per_year) - 1.0
    excess_ret = ret_series - rf_period
    downside = ret_series[ret_series < rf_period] - rf_period
    downside_dev = np.sqrt(np.mean(downside**2)) if len(downside) > 0 else 1e-6
    if downside_dev == 0 or np.isnan(downside_dev):
        return 0.0
    return (excess_ret.mean() / downside_dev) * np.sqrt(periods_per_year)

def compute_drawdowns(nav_series):
    peak = nav_series.cummax()
    dd = (nav_series - peak) / peak
    max_dd = dd.min()
    return dd, max_dd

def compute_capm_alpha_beta(strat_ret, bench_ret, rf_annual=config.ANNUAL_RISK_FREE_RATE, periods_per_year=12):
    """
    Computes CAPM Alpha (annualized) and Beta against Benchmark.
    """
    rf_period = (1.0 + rf_annual) ** (1.0 / periods_per_year) - 1.0
    df = pd.DataFrame({"strat": strat_ret, "bench": bench_ret}).dropna()
    y = df["strat"] - rf_period
    x = sm.add_constant(df["bench"] - rf_period)
    model = sm.OLS(y, x).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
    
    alpha_monthly = model.params.iloc[0]
    alpha_annual = (1.0 + alpha_monthly) ** periods_per_year - 1.0
    beta = model.params.iloc[1]
    t_alpha = model.tvalues.iloc[0]
    p_alpha = model.pvalues.iloc[0]
    r2 = model.rsquared

    return {
        "alpha_annual": alpha_annual,
        "beta": beta,
        "t_alpha": t_alpha,
        "p_alpha": p_alpha,
        "r2": r2
    }

def generate_summary_table(nav_dict, bench_nav, rf_annual=config.ANNUAL_RISK_FREE_RATE):
    """
    Generates a consolidated metrics summary table across variants.
    """
    results = []
    for name, nav in nav_dict.items():
        ret = nav.pct_change().dropna()
        cagr = compute_cagr(nav)
        vol = compute_volatility(ret)
        sharpe = compute_sharpe(ret, rf_annual)
        sortino = compute_sortino(ret, rf_annual)
        _, mdd = compute_drawdowns(nav)
        
        bench_ret = bench_nav.pct_change().dropna().reindex(ret.index).dropna()
        matched_ret = ret.reindex(bench_ret.index).dropna()
        capm = compute_capm_alpha_beta(matched_ret, bench_ret, rf_annual)

        results.append({
            "Strategy": name,
            "CAGR": cagr,
            "Volatility": vol,
            "Sharpe (Rf=6%)": sharpe,
            "Sortino": sortino,
            "Max Drawdown": mdd,
            "CAPM Beta": capm["beta"],
            "Annual Alpha": capm["alpha_annual"],
            "Alpha t-stat": capm["t_alpha"]
        })
    return pd.DataFrame(results)
