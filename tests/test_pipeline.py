"""
Unit tests for Brindco Quant Pipeline.
Validates zero lookahead bias, statutory cost calculations, and FIFO tax engine.
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config
from execution.cost_model import BrindcoCostModel
from execution.tax_engine import IndianTaxEngine
from signals.novy_marx_signals import compute_novy_marx_signals

def test_cost_model_baseline():
    cm = BrindcoCostModel(mode="delivery")
    summary = cm.round_trip_cost_summary(trade_size=1_000_000)
    # STT buy(10) + sell(10) + stamp(1.5) + exch(0.297*2) + sebi(0.13*2) + spread(10) = 32.354 bps
    assert 32.0 <= summary["round_trip_bps"] <= 33.0

def test_tax_engine_stcg_vs_ltcg():
    te = IndianTaxEngine()
    
    # 1. Buy 100 shares of ABC at INR 100 on 2020-01-01
    te.add_buy_lot("ABC", "2020-01-01", 100, 100.0, buy_cost=0.0)
    
    # 2. Sell 50 shares on 2020-06-01 (< 365 days) at INR 150 -> Gain = 50 * 50 = 2500 -> STCG tax @ 20% = 500
    net_cash, tax, stcg, ltcg = te.process_sell("ABC", "2020-06-01", 50, 150.0, sell_cost=0.0)
    assert stcg == 2500.0
    assert ltcg == 0.0
    assert tax == 500.0
    assert net_cash == (7500.0 - 500.0)
    
    # 3. Sell remaining 50 shares on 2021-06-01 (>= 365 days) at INR 200 -> Gain = 50 * 100 = 5000 (LTCG under 1.25L exemption -> Tax = 0)
    net_cash2, tax2, stcg2, ltcg2 = te.process_sell("ABC", "2021-06-01", 50, 200.0, sell_cost=0.0)
    assert stcg2 == 0.0
    assert ltcg2 == 5000.0
    assert tax2 == 0.0
    assert net_cash2 == 10000.0

def test_novy_marx_lag_indexing():
    dates = pd.date_range("2020-01-31", periods=24, freq="ME")
    # Synthetic prices increasing linearly
    prices = pd.DataFrame({"A": np.linspace(100, 200, 24)}, index=dates)
    
    signals = compute_novy_marx_signals(prices)
    r_12_7 = signals["r_12_7"]
    
    # At index 12 (month 13), r_12_7 should be P[6] / P[0] - 1
    p = prices["A"].values
    expected_r12_7 = (p[6] / p[0]) - 1.0
    actual_r12_7 = r_12_7["A"].iloc[12]
    np.testing.assert_almost_equal(actual_r12_7, expected_r12_7, decimal=5)
