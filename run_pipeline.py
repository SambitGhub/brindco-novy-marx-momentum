"""
Master Pipeline Runner for Brindco Assignment
Candidate: Sambit Ranjan Rout (Chennai Mathematical Institute)
Paper: Novy-Marx, R. (2012) 'Is Momentum Really Momentum?'
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from data.fetcher import fetch_all_data
from backtest.engine import BacktestEngine
from backtest.metrics import (
    compute_cagr, compute_volatility, compute_sharpe, 
    compute_sortino, compute_drawdowns, compute_capm_alpha_beta,
    generate_summary_table
)
from research.econometric_tests import run_fama_macbeth, compute_mandatory_arithmetic_table
from execution.cost_model import BrindcoCostModel

# Set styling
sns.set_theme(style="whitegrid")
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

def main():
    print("=" * 80)
    print(" BRINDCO QUANT DESK — CASE SUBMISSION: ONE PAPER, ONE STRATEGY")
    print(" Candidate: Sambit Ranjan Rout (Chennai Mathematical Institute)")
    print(" Strategy: Novy-Marx (2012) Intermediate Momentum under Indian Cash Constraints")
    print("=" * 80)

    # 1. Load Data
    prices, volumes, adv20, bench = fetch_all_data(force_reload=False)
    bench_nav = bench["NIFTY"]

    engine = BacktestEngine(prices, adv20=adv20, benchmark=bench_nav)

    # 2. Econometric Testing (Fama-MacBeth Regressions in Build Window)
    print("\n[1/5] Running Fama-MacBeth Cross-Sectional Regressions (2015-2023)...")
    fm_results = run_fama_macbeth(engine.m_prices, engine.signals, 
                                  start_date=config.BUILD_START_DATE, 
                                  end_date=config.BUILD_END_DATE)
    
    print("\n--- Fama-MacBeth Premia in Indian Equities (Build Window) ---")
    print("Univariate r_12_7:", fm_results["univariate_12_7"])
    print("Standard r_12_2:  ", fm_results["standard_12_2"])
    print("Multivariate Novy-Marx Model:")
    for k, v in fm_results["multivariate_novy_marx"].items():
        print(f"  {k}: {v:.4f}")

    # 3. Build Window Backtests (2015-04-01 to 2023-03-31)
    print("\n[2/5] Running Strategy Variants across Build Window (2015-2023)...")
    
    # A. Novy-Marx Intermediate Momentum (r_12_7) - Equal Weighted
    res_r12_7_ew = engine.run_strategy("r_12_7", start_date=config.BUILD_START_DATE, 
                                       end_date=config.BUILD_END_DATE, top_n=30, weighting="equal")
    
    # B. Novy-Marx Intermediate Momentum (r_12_7) - Inverse Vol Weighted
    res_r12_7_ivw = engine.run_strategy("r_12_7", start_date=config.BUILD_START_DATE, 
                                        end_date=config.BUILD_END_DATE, top_n=30, weighting="inv_vol")
    
    # C. Standard Momentum (r_12_2) - Equal Weighted
    res_r12_2_ew = engine.run_strategy("r_12_2", start_date=config.BUILD_START_DATE, 
                                       end_date=config.BUILD_END_DATE, top_n=30, weighting="equal")
    
    # D. Recent Momentum (r_6_2) - Equal Weighted
    res_r6_2_ew = engine.run_strategy("r_6_2", start_date=config.BUILD_START_DATE, 
                                      end_date=config.BUILD_END_DATE, top_n=30, weighting="equal")

    # Benchmark aligned to build window
    bench_build = bench_nav.loc[config.BUILD_START_DATE:config.BUILD_END_DATE]
    bench_build_m = bench_build.resample('ME').last()
    bench_build_norm = bench_build_m / bench_build_m.iloc[0] * 10_000_000.0

    # Summary table for Build Window
    build_nav_dict = {
        "Novy-Marx r(12,7) EW [Gross]": res_r12_7_ew["nav"]["Gross"],
        "Novy-Marx r(12,7) EW [Net Costs]": res_r12_7_ew["nav"]["Net_Costs"],
        "Novy-Marx r(12,7) EW [Net Tax & Costs]": res_r12_7_ew["nav"]["Net_Taxes"],
        "Novy-Marx r(12,7) IVW [Net Tax & Costs]": res_r12_7_ivw["nav"]["Net_Taxes"],
        "Standard r(12,2) EW [Net Tax & Costs]": res_r12_2_ew["nav"]["Net_Taxes"],
        "Recent r(6,2) EW [Net Tax & Costs]": res_r6_2_ew["nav"]["Net_Taxes"],
        "NIFTY Benchmark": bench_build_norm
    }
    
    summary_build = generate_summary_table(build_nav_dict, bench_build_norm)
    print("\n--- Build Window (2015-2023) Performance Summary ---")
    print(summary_build.to_string(index=False))

    # 4. Mandatory Section 4.4 Table
    print("\n[3/5] Computing Section 4.4 Mandatory Arithmetic Table...")
    cost_model = BrindcoCostModel(mode="delivery")
    gross_cagr = compute_cagr(res_r12_7_ew["nav"]["Gross"])
    bench_cagr = compute_cagr(bench_build_norm)
    
    sec4_table = compute_mandatory_arithmetic_table(
        res_r12_7_ew["turnover"], cost_model, gross_cagr, bench_cagr
    )
    print("\n--- Mandatory Arithmetic Table (§4.4) ---")
    print(sec4_table.to_string(index=False))

    # 5. Holdout Window Backtest (2023-04-01 to 2026-03-31) — Run ONCE
    print("\n[4/5] Evaluating Holdout Window (2023-2026) — Strictly Single Run...")
    res_holdout_r12_7 = engine.run_strategy("r_12_7", start_date=config.HOLDOUT_START_DATE, 
                                            end_date=config.HOLDOUT_END_DATE, top_n=30, weighting="equal")
    res_holdout_r12_2 = engine.run_strategy("r_12_2", start_date=config.HOLDOUT_START_DATE, 
                                            end_date=config.HOLDOUT_END_DATE, top_n=30, weighting="equal")
    
    bench_holdout = bench_nav.loc[config.HOLDOUT_START_DATE:config.HOLDOUT_END_DATE]
    bench_holdout_m = bench_holdout.resample('ME').last()
    bench_holdout_norm = bench_holdout_m / bench_holdout_m.iloc[0] * 10_000_000.0

    holdout_nav_dict = {
        "Holdout: Novy-Marx r(12,7) EW [Gross]": res_holdout_r12_7["nav"]["Gross"],
        "Holdout: Novy-Marx r(12,7) EW [Net Costs]": res_holdout_r12_7["nav"]["Net_Costs"],
        "Holdout: Novy-Marx r(12,7) EW [Net Tax & Costs]": res_holdout_r12_7["nav"]["Net_Taxes"],
        "Holdout: Standard r(12,2) EW [Net Tax & Costs]": res_holdout_r12_2["nav"]["Net_Taxes"],
        "Holdout: NIFTY Benchmark": bench_holdout_norm
    }
    summary_holdout = generate_summary_table(holdout_nav_dict, bench_holdout_norm)
    print("\n--- Holdout Window (2023-2026) Performance Summary ---")
    print(summary_holdout.to_string(index=False))

    # 6. Generate Charts & Save Results
    print("\n[5/5] Generating Institutional Figures and Exporting Data...")
    
    # Save CSVs
    summary_build.to_csv(os.path.join(config.OUTPUT_DIR, "summary_build.csv"), index=False)
    summary_holdout.to_csv(os.path.join(config.OUTPUT_DIR, "summary_holdout.csv"), index=False)
    sec4_table.to_csv(os.path.join(config.OUTPUT_DIR, "mandatory_arithmetic_table.csv"), index=False)

    # Plot 1: Cumulative Performance (Build & Holdout)
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=False, gridspec_kw={'height_ratios': [2, 1]})
    
    # Build NAV
    axes[0].plot(res_r12_7_ew["nav"].index, res_r12_7_ew["nav"]["Gross"] / 1e7, label="Novy-Marx r(12,7) Gross", color="#1f77b4", linewidth=2.0)
    axes[0].plot(res_r12_7_ew["nav"].index, res_r12_7_ew["nav"]["Net_Costs"] / 1e7, label="Novy-Marx r(12,7) Net Costs", color="#2ca02c", linewidth=1.8, linestyle="--")
    axes[0].plot(res_r12_7_ew["nav"].index, res_r12_7_ew["nav"]["Net_Taxes"] / 1e7, label="Novy-Marx r(12,7) Net Tax & Costs", color="#d62728", linewidth=2.0)
    axes[0].plot(bench_build_norm.index, bench_build_norm / 1e7, label="NIFTY Benchmark", color="#333333", linewidth=1.5, linestyle=":")
    axes[0].set_title("Build Window (2015–2023): Novy-Marx Intermediate Momentum vs Friction & Benchmark", fontsize=13, fontweight='bold')
    axes[0].set_ylabel("Normalized NAV (Base = 1.0)", fontsize=11)
    axes[0].legend(loc="upper left", frameon=True)

    # Drawdowns
    dd_gross, _ = compute_drawdowns(res_r12_7_ew["nav"]["Gross"])
    dd_net, _ = compute_drawdowns(res_r12_7_ew["nav"]["Net_Taxes"])
    dd_bench, _ = compute_drawdowns(bench_build_norm)

    axes[1].plot(dd_gross.index, dd_gross * 100, label="Strategy Gross DD", color="#1f77b4", linewidth=1.2)
    axes[1].plot(dd_net.index, dd_net * 100, label="Strategy Net DD", color="#d62728", linewidth=1.5)
    axes[1].plot(dd_bench.index, dd_bench * 100, label="Benchmark DD", color="#333333", linewidth=1.2, linestyle=":")
    axes[1].set_title("Historical Drawdown Profile (Build Window)", fontsize=12, fontweight='bold')
    axes[1].set_ylabel("Drawdown (%)", fontsize=11)
    axes[1].legend(loc="lower left", frameon=True)

    plt.tight_layout()
    chart1_path = os.path.join(config.OUTPUT_DIR, "fig1_build_performance_drawdown.png")
    plt.savefig(chart1_path, dpi=300)
    plt.close()

    # Plot 2: Holdout Out-of-Sample Performance
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res_holdout_r12_7["nav"].index, res_holdout_r12_7["nav"]["Gross"] / 1e7, label="Novy-Marx r(12,7) Gross", color="#1f77b4", linewidth=2.0)
    ax.plot(res_holdout_r12_7["nav"].index, res_holdout_r12_7["nav"]["Net_Taxes"] / 1e7, label="Novy-Marx r(12,7) Net Tax & Costs", color="#d62728", linewidth=2.0)
    ax.plot(res_holdout_r12_2["nav"].index, res_holdout_r12_2["nav"]["Net_Taxes"] / 1e7, label="Standard r(12,2) Net Tax & Costs", color="#ff7f0e", linewidth=1.5, linestyle="--")
    ax.plot(bench_holdout_norm.index, bench_holdout_norm / 1e7, label="NIFTY Benchmark", color="#333333", linewidth=1.5, linestyle=":")
    ax.set_title("Holdout Window (2023–2026): Out-of-Sample Validation", fontsize=13, fontweight='bold')
    ax.set_ylabel("Normalized NAV (Base = 1.0)", fontsize=11)
    ax.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    chart2_path = os.path.join(config.OUTPUT_DIR, "fig2_holdout_validation.png")
    plt.savefig(chart2_path, dpi=300)
    plt.close()

    # Plot 3: Turnover & Friction Decomposition
    fig, ax = plt.subplots(figsize=(10, 4.5))
    turnover_r12_7 = res_r12_7_ew["turnover"]["turnover"] * 100
    turnover_r12_2 = res_r12_2_ew["turnover"]["turnover"] * 100
    
    df_to = pd.DataFrame({"Novy-Marx r(12,7)": turnover_r12_7, "Standard r(12,2)": turnover_r12_2})
    df_to.plot(kind="line", ax=ax, linewidth=1.5, alpha=0.85)
    ax.set_title("Monthly Realized Turnover: Intermediate r(12,7) vs Standard r(12,2)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Turnover (% of Book)", fontsize=11)
    ax.legend(frameon=True)
    plt.tight_layout()
    chart3_path = os.path.join(config.OUTPUT_DIR, "fig3_turnover_comparison.png")
    plt.savefig(chart3_path, dpi=300)
    plt.close()

    print(f"\nAll charts and summary artifacts successfully saved to {config.OUTPUT_DIR}.")
    print("=" * 80)

if __name__ == "__main__":
    main()
