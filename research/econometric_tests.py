"""
Econometric Testing & Statistical Rigor Module.
Runs Fama-MacBeth (1973) cross-sectional regressions with Newey-West (1987) HAC standard errors,
computes factor spanning regressions, and generates the mandatory Section 4.4 Arithmetic Table.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import config

def run_fama_macbeth(monthly_prices, signals, start_date=config.BUILD_START_DATE, end_date=config.BUILD_END_DATE):
    """
    Runs monthly Fama-MacBeth cross-sectional regressions:
    R_{i, t+1} = \gamma_0 + \gamma_1 * r_{12,7} + \gamma_2 * r_{6,2} + \gamma_3 * r_{1,0} + e
    
    Tests whether intermediate momentum (r_{12,7}) subsumes recent momentum (r_{6,2}) in Indian equities.
    """
    fwd_returns = (monthly_prices.shift(-1) / monthly_prices) - 1.0
    
    r_12_7 = signals["r_12_7"]
    r_6_2 = signals["r_6_2"]
    r_12_2 = signals["r_12_2"]
    r_1_0 = signals["r_1_0"]

    dates = monthly_prices.loc[start_date:end_date].index[:-1]
    
    records_univ = []  # Univariate r_12_7
    records_multi = [] # Multivariate r_12_7 + r_6_2 + r_1_0
    records_std = []   # Standard r_12_2

    for d in dates:
        y = fwd_returns.loc[d]
        x_12_7 = r_12_7.loc[d]
        x_6_2 = r_6_2.loc[d]
        x_12_2 = r_12_2.loc[d]
        x_1_0 = r_1_0.loc[d]

        # Filter valid observations
        df_d = pd.DataFrame({
            "y": y,
            "r_12_7": x_12_7,
            "r_6_2": x_6_2,
            "r_12_2": x_12_2,
            "r_1_0": x_1_0
        }).dropna()

        # Winsorize extremes at 1st and 99th percentiles
        for col in df_d.columns:
            low, high = df_d[col].quantile(0.01), df_d[col].quantile(0.99)
            df_d[col] = df_d[col].clip(low, high)

        if len(df_d) >= 50:
            # 1. Univariate r_12_7
            X_u = sm.add_constant(df_d["r_12_7"])
            res_u = sm.OLS(df_d["y"], X_u).fit()
            records_univ.append({"date": d, "const": res_u.params.iloc[0], "gamma_12_7": res_u.params.iloc[1]})

            # 2. Standard r_12_2
            X_s = sm.add_constant(df_d["r_12_2"])
            res_s = sm.OLS(df_d["y"], X_s).fit()
            records_std.append({"date": d, "const": res_s.params.iloc[0], "gamma_12_2": res_s.params.iloc[1]})

            # 3. Multivariate Novy-Marx Model
            X_m = sm.add_constant(df_d[["r_12_7", "r_6_2", "r_1_0"]])
            res_m = sm.OLS(df_d["y"], X_m).fit()
            records_multi.append({
                "date": d,
                "const": res_m.params.iloc[0],
                "gamma_12_7": res_m.params["r_12_7"],
                "gamma_6_2": res_m.params["r_6_2"],
                "gamma_1_0": res_m.params["r_1_0"]
            })

    def summarize_gammas(df_gammas, name):
        summary = {}
        for col in df_gammas.columns:
            if col == "date":
                continue
            series = df_gammas[col].dropna()
            mean = series.mean()
            # Newey-West HAC t-stat
            ols_const = sm.OLS(series, np.ones(len(series))).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
            t_stat = ols_const.tvalues.iloc[0]
            p_val = ols_const.pvalues.iloc[0]
            summary[f"{col}_mean_%"] = mean * 100.0
            summary[f"{col}_tstat"] = t_stat
            summary[f"{col}_pval"] = p_val
        return summary

    df_u = pd.DataFrame(records_univ)
    df_s = pd.DataFrame(records_std)
    df_m = pd.DataFrame(records_multi)

    return {
        "univariate_12_7": summarize_gammas(df_u, "Univariate r_12_7"),
        "standard_12_2": summarize_gammas(df_s, "Standard r_12_2"),
        "multivariate_novy_marx": summarize_gammas(df_m, "Multivariate Novy-Marx")
    }

def compute_mandatory_arithmetic_table(turnover_series, cost_model, gross_cagr, bench_cagr, hurdle_alpha=0.03):
    """
    Generates the mandatory Section 4.4 table required by Brindco:
    1. Rebalance cadence & Realized annual turnover as fraction of book value
    2. Cost per round trip at modelled participation rate
    3. Annualised cost drag implied by that turnover
    4. Gross annual edge strategy must clear vs actual gross edge
    """
    # Average monthly turnover
    avg_monthly_turnover = turnover_series["turnover"].mean()
    annual_turnover = avg_monthly_turnover * 12.0

    # Cost per round trip (bps)
    summary_costs = cost_model.round_trip_cost_summary()
    round_trip_bps = summary_costs["round_trip_bps"]
    cost_per_round_trip_pct = round_trip_bps / 10000.0

    # Annualized cost drag = Annual Turnover * Round Trip Cost
    annual_cost_drag_pct = annual_turnover * cost_per_round_trip_pct
    annual_cost_drag_bps = annual_cost_drag_pct * 10000.0

    # Edge analysis
    actual_gross_edge = gross_cagr - bench_cagr
    required_gross_edge = annual_cost_drag_pct + hurdle_alpha
    clears_hurdle = actual_gross_edge >= required_gross_edge

    table_data = [
        {"Metric": "Rebalance Cadence", "Value": "Monthly (Month-End)"},
        {"Metric": "Realised Annual Turnover (fraction of book)", "Value": f"{annual_turnover:.2f}x ({annual_turnover*100:.1f}%)"},
        {"Metric": "Cost per Round Trip (modelled)", "Value": f"{round_trip_bps:.2f} bps ({cost_per_round_trip_pct*100:.4f}%)"},
        {"Metric": "Annualised Cost Drag", "Value": f"{annual_cost_drag_bps:.2f} bps/yr ({annual_cost_drag_pct*100:.2f}%)"},
        {"Metric": "Benchmark CAGR", "Value": f"{bench_cagr*100:.2f}%"},
        {"Metric": "Gross Strategy CAGR", "Value": f"{gross_cagr*100:.2f}%"},
        {"Metric": "Realised Gross Edge over Benchmark", "Value": f"{actual_gross_edge*100:.2f}%"},
        {"Metric": "Gross Edge Required to Clear Hurdle (Drag + 3% Net Alpha)", "Value": f"{required_gross_edge*100:.2f}%"},
        {"Metric": "Clears Required Hurdle?", "Value": "YES" if clears_hurdle else "NO"}
    ]
    return pd.DataFrame(table_data)
