"""
Portfolio Allocator and Position Sizer.
Implements Long-Only Top-Decile / Top-N allocation, Inverse-Volatility weighting,
and rank-buffering guardrails to control turnover.
"""

import numpy as np
import pandas as pd
import config

class PortfolioAllocator:
    def __init__(self, top_n=config.TOP_N_STOCKS, weighting=config.WEIGHTING_SCHEME, buffer_n=config.BUFFER_THRESHOLD):
        self.top_n = top_n
        self.weighting = weighting
        self.buffer_n = buffer_n

    def select_portfolio(self, signal_series, prev_portfolio=None, daily_returns=None, date=None):
        """
        Selects target portfolio weights given cross-sectional signal at date t.
        
        Parameters:
        - signal_series: pd.Series of signal values (r_{12,7}) indexed by ticker.
        - prev_portfolio: dict or pd.Series of current holdings {ticker: weight}.
        - daily_returns: pd.DataFrame of historical daily returns up to date t (for vol weighting).
        - date: pd.Timestamp
        
        Returns:
        - target_weights: pd.Series of target weights summing to 1.0.
        """
        # Drop NaN signals
        valid_signals = signal_series.dropna()
        if len(valid_signals) < self.top_n:
            # Fallback if universe is too small
            n_select = len(valid_signals)
            selected = valid_signals.nlargest(n_select).index.tolist()
        else:
            sorted_tickers = valid_signals.sort_values(ascending=False).index.tolist()
            
            if prev_portfolio is None or len(prev_portfolio) == 0:
                selected = sorted_tickers[:self.top_n]
            else:
                # Apply buffer rule: keep existing holdings if within top_n + buffer_n
                buffer_cutoff = self.top_n + self.buffer_n
                buffer_pool = set(sorted_tickers[:buffer_cutoff])
                
                selected = []
                # Keep eligible current holdings
                for t in prev_portfolio.keys():
                    if t in buffer_pool and t in sorted_tickers:
                        selected.append(t)
                        if len(selected) >= self.top_n:
                            break
                
                # Fill remaining slots from the highest ranked new entrants
                for t in sorted_tickers:
                    if len(selected) >= self.top_n:
                        break
                    if t not in selected:
                        selected.append(t)

        if not selected:
            return pd.Series(dtype=float)

        # Weighting
        if self.weighting == "equal":
            weights = pd.Series(1.0 / len(selected), index=selected)
        elif self.weighting == "inv_vol" and daily_returns is not None and date is not None:
            # Compute 60-day historical realized volatility
            hist_ret = daily_returns.loc[:date].tail(60)[selected]
            vols = hist_ret.std() * np.sqrt(252)
            vols = vols.replace(0, np.nan).fillna(vols.median())
            inv_vols = 1.0 / vols
            weights = inv_vols / inv_vols.sum()
        else:
            weights = pd.Series(1.0 / len(selected), index=selected)

        return weights
