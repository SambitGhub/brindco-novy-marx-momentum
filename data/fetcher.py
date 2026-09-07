"""
Data fetcher module for Brindco Quant Assignment.
Fetches daily OHLCV from public sources (Yahoo Finance), computes 20-day ADV,
and caches parquet files locally for offline reproducibility.
"""

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from data.universe_manager import get_nifty500_tickers

def fetch_all_data(force_reload=False):
    prices_file = os.path.join(config.DATA_DIR, "prices.parquet")
    volumes_file = os.path.join(config.DATA_DIR, "volumes.parquet")
    adv_file = os.path.join(config.DATA_DIR, "adv20.parquet")
    benchmark_file = os.path.join(config.DATA_DIR, "benchmark.parquet")

    if not force_reload and os.path.exists(prices_file) and os.path.exists(benchmark_file):
        print("Loading cached data from disk...")
        prices = pd.read_parquet(prices_file)
        volumes = pd.read_parquet(volumes_file)
        adv = pd.read_parquet(adv_file)
        benchmark = pd.read_parquet(benchmark_file)
        return prices, volumes, adv, benchmark

    print("Fetching historical data from 2014 to 2026...")
    tickers = get_nifty500_tickers()
    
    # Download benchmark (^NSEI)
    print("Fetching benchmark data (^NSEI)...")
    bench_df = yf.download("^NSEI", start=config.DATA_START_DATE, end="2026-04-01", progress=False)
    if isinstance(bench_df.columns, pd.MultiIndex):
        bench_close = bench_df['Close']['^NSEI'] if '^NSEI' in bench_df['Close'] else bench_df['Close'].iloc[:, 0]
    else:
        bench_close = bench_df['Close']
    bench_series = pd.DataFrame({"NIFTY": bench_close})
    bench_series.index = pd.to_datetime(bench_series.index).tz_localize(None)
    bench_series.to_parquet(benchmark_file)

    # Download universe in batches
    print(f"Fetching data for {len(tickers)} stocks...")
    data = yf.download(tickers, start=config.DATA_START_DATE, end="2026-04-01", group_by='ticker', progress=True, threads=True)

    # Extract Close and Volume
    close_dict = {}
    volume_dict = {}

    for t in tickers:
        try:
            if t in data.columns.levels[0]:
                df_t = data[t]
                if 'Close' in df_t.columns and not df_t['Close'].dropna().empty:
                    close_dict[t] = df_t['Close']
                    volume_dict[t] = df_t['Volume']
        except Exception:
            continue

    prices = pd.DataFrame(close_dict)
    volumes = pd.DataFrame(volume_dict)

    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    volumes.index = pd.to_datetime(volumes.index).tz_localize(None)

    # Forward fill prices to handle non-trading days/trading halts, but limit forward fill to 5 days
    prices = prices.ffill(limit=5)
    
    # Calculate 20-day Traded Value (Turnover) in INR: Close * Volume
    traded_val = prices * volumes
    adv20 = traded_val.rolling(window=20, min_periods=5).mean()

    # Save to disk
    prices.to_parquet(prices_file)
    volumes.to_parquet(volumes_file)
    adv20.to_parquet(adv_file)

    print(f"Data fetch complete. Successfully cached {prices.shape[1]} stocks across {prices.shape[0]} trading days.")
    return prices, volumes, adv20, bench_series

if __name__ == "__main__":
    prices, volumes, adv, bench = fetch_all_data(force_reload=True)
    print("Prices head:")
    print(prices.head(2))
    print("Benchmark head:")
    print(bench.head(2))
