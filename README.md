# Brindco Assignment

**Candidate:** Sambit Ranjan Rout  
**Affiliation:** Chennai Mathematical Institute
**Selected Paper:** **Novy-Marx, R. (2012). *Is Momentum Really Momentum?*** *Journal of Financial Economics*, 103(3), 429–453.

---

## 1. Executive Summary & Key Findings

This repository contains the complete, reproducible research pipeline translating **Novy-Marx (2012)** intermediate momentum ($r_{12,7}$) into a **long-only, cash-only, fully paid Indian equity mandate** (NIFTY 500 universe) evaluated across an 8-year Build Window (2015–2023) and a single-run 3-year Holdout Window (2023–2026).

### Key Takeaways:
1. **Econometric Inversion vs US Literature:** Cross-sectional Fama-MacBeth regressions with Newey-West standard errors reveal that **recent momentum ($r_{6,2}$, $\gamma = +1.59\%$, $t = 2.90$) strongly dominates intermediate momentum ($r_{12,7}$, $\gamma = +0.43\%$, $t = 0.68$) in Indian equities**. Indian momentum is faster-moving and subject to rapid factor decay.
2. **Cost Floor Survival:** The strategy clears the desk's statutory cost floor comfortably (32.35 bps round-trip + 3.75x turnover = 121.2 bps annual drag vs +14.55% gross alpha).
3. **The Post-Tax Strategy Killer:** While execution costs are manageable, **Indian Short-Term Capital Gains Tax (STCG @ 20%) is the decisive friction**. With average holding periods of 3.2 months, continuous monthly gain realization extracts **13.56% annualized in compounded returns**, eliminating net alpha in the Build Window (Net Post-Tax CAGR: 9.17% vs Benchmark 9.97%).
4. **Out-of-Sample Holdout (2023–2026):** In a strong bull regime, extreme gross alpha (+26.38%) enabled the strategy to survive post-tax (19.02% Net Post-Tax CAGR vs 7.53% Benchmark), though carrying a high systematic beta ($\beta = 1.34$).

---

## 2. Repository Structure

```
brindco_novy_marx_momentum/
├── README.md                     
├── requirements.txt            
├── config.py                     
├── run_pipeline.py      
├── data/
│   ├── universe_manager.py   
│   └── fetcher.py            
├── signals/
│   └── novy_marx_signals.py
├── portfolio/
│   └── allocator.py 
├── execution/
│   ├── cost_model.py        
│   └── tax_engine.py       
├── backtest/
│   ├── engine.py               
│   └── metrics.py          
├── research/
│   └── econometric_tests.py     
└── output/
    ├── summary_build.csv        
    ├── summary_holdout.csv   
    ├── arithmetic_table.csv  
    ├── fig1_build_performance_drawdown.png 
    ├── fig2_holdout_validation.png        
    └── fig3_turnover_comparison.png      
```

---

## 3. Reproduction Instructions

To reproduce all results, tables, and figures from scratch:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Execute the entire pipeline end-to-end
python run_pipeline.py
```

---

## 4. Arithmetic Table

| Metric | Value / Specification | Desk Commentary |
| :--- | :--- | :--- |
| **Rebalance Cadence** | Monthly (Month-End) | Aligns with desk common spine |
| **Realised Annual Turnover** | **3.75x (374.6% of book)** | ~31.2% book churned per month |
| **Cost per Round Trip (modelled)** | **32.35 bps** | STT (20), Stamp (1.5), Exch/SEBI (0.85), Spread (10) |
| **Annualised Cost Drag** | **121.20 bps / year (1.21%)** | Annual Turnover × Round-Trip Friction |
| **Benchmark CAGR (NIFTY)** | 9.97% (Vol: 17.15%) | Buy-and-hold over Build Window (2015–2023) |
| **Gross Strategy CAGR** | **24.52% (Vol: 23.07%)** | Gross return before friction & taxes |
| **Realised Gross Edge** | **+14.55% / year** | Gross CAGR minus Benchmark CAGR |
| **Gross Edge Required to Clear Hurdle** | **4.21% / year** | 1.21% cost drag + 3.00% net alpha hurdle |
| **Clears Required Cost Hurdle?** | **YES (Survives Cost Floor)** | Exceeds hurdle by +10.34% annualized |

---

## 5. Declarations & Compliance

* **Data Sources (Rule 6.1):** Historical daily quotes sourced from Yahoo Finance NSE archives (`.NS`), adjusted for splits and bonus issues. NIFTY 500 historical reconstitutions mapped from NSE historical index circulars. Survivorship bias mathematically bounded below $\le 0.48\%$ annualized.
