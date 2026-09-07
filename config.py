"""
Configuration file for Brindco Pillar III Case Assignment: 'One Paper, One Strategy'
Candidate: Sambit Ranjan Rout (Chennai Mathematical Institute)
Target: Novy-Marx (2012) Intermediate Momentum in Long-Only Indian Equities
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEMO_DIR = os.path.join(BASE_DIR, "memo")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEMO_DIR, exist_ok=True)

# Random Seed for deterministic reproducibility
RANDOM_SEED = 42

# Timeline Specifications
DATA_START_DATE = "2014-01-01"  # 15 months buffer prior to build window to compute r_{12,7}
BUILD_START_DATE = "2015-04-01"
BUILD_END_DATE = "2023-03-31"
HOLDOUT_START_DATE = "2023-04-01"
HOLDOUT_END_DATE = "2026-03-31"

# Desk Cost Stack (Basis points of one-side notional)
COST_STACK = {
    "delivery": {
        "stt_buy_bps": 10.0,
        "stt_sell_bps": 10.0,
        "stamp_duty_buy_bps": 1.5,
        "stamp_duty_sell_bps": 0.0,
        "exchange_charges_bps": 0.297,  # per side
        "sebi_gst_bps": 0.13,          # per side
        "base_spread_impact_bps": 10.0, # large-cap round trip spread & impact
    },
    "intraday": {
        "stt_buy_bps": 0.0,
        "stt_sell_bps": 2.5,
        "stamp_duty_buy_bps": 0.3,
        "stamp_duty_sell_bps": 0.0,
        "exchange_charges_bps": 0.297,
        "sebi_gst_bps": 0.13,
        "base_spread_impact_bps": 3.0,
    }
}

# Market Impact Model Parameters for Mid/Small Caps
# Impact(bps) = BaseSpread + gamma * sqrt(ParticipationRate)
MARKET_IMPACT_GAMMA = 50.0   # Impact scaling coefficient
PARTICIPATION_CAP = 0.05     # Maximum 5% of 20-day ADV
ASSUMED_AUM_INR = 50_00_00_000  # INR 50 Crores (INR 500 Million) for capacity tests

# Indian Capital Gains Tax Stack
TAX_RATES = {
    "stcg_rate": 0.20,         # 20% on positions held < 12 months (365 days)
    "ltcg_rate": 0.125,        # 12.5% on positions held >= 12 months (above annual exemption)
    "ltcg_exemption_inr": 125_000  # Annual exemption limit (INR 1.25 Lakh)
}

# Risk-Free Rate Proxy (RBI 91-day T-Bill average yield over period ~ 6.0% annualized)
ANNUAL_RISK_FREE_RATE = 0.060

# Strategy Construction Parameters
UNIVERSE_NAME = "NIFTY_500"
BENCHMARK_TICKER = "^CRSLDX"   # NIFTY 500 Index / NIFTY 50 (^NSEI) fallback
REBALANCE_CADENCE = "M"        # Monthly rebalance at month-end
TOP_N_STOCKS = 30              # Top 30 stocks portfolio (or decile ~ 50 stocks)
WEIGHTING_SCHEME = "equal"     # 'equal', 'inv_vol', 'rank_weight'
BUFFER_THRESHOLD = 5           # Rank buffer to reduce turnover
