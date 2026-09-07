"""
Institutional Backtesting Engine for Brindco Quant Mandate.
Implements long-only cash rebalancing, turnover tracking, transaction cost deduction,
and FIFO Indian capital gains tax calculation across Build and Holdout windows.
"""

import numpy as np
import pandas as pd
import config
from signals.novy_marx_signals import compute_novy_marx_signals, compute_monthly_returns_and_prices
from portfolio.allocator import PortfolioAllocator
from execution.cost_model import BrindcoCostModel
from execution.tax_engine import IndianTaxEngine

class BacktestEngine:
    def __init__(self, prices, adv20=None, benchmark=None, initial_capital=10_000_000.0):
        self.prices = prices
        self.adv20 = adv20
        self.benchmark = benchmark
        self.initial_capital = initial_capital
        
        # Resample to month-end
        self.m_prices, self.m_returns = compute_monthly_returns_and_prices(prices)
        self.signals = compute_novy_marx_signals(self.m_prices)

    def run_strategy(self, signal_name="r_12_7", start_date=config.BUILD_START_DATE, 
                     end_date=config.BUILD_END_DATE, top_n=config.TOP_N_STOCKS, 
                     weighting=config.WEIGHTING_SCHEME, buffer_n=config.BUFFER_THRESHOLD,
                     mode="delivery"):
        """
        Runs the backtest for a specific signal and date range.
        Returns detailed series: gross_nav, net_cost_nav, net_tax_nav, turnover_series, trade_logs.
        """
        signal_df = self.signals[signal_name]
        allocator = PortfolioAllocator(top_n=top_n, weighting=weighting, buffer_n=buffer_n)
        cost_model = BrindcoCostModel(mode=mode)
        tax_engine = IndianTaxEngine()

        rebal_dates = signal_df.loc[start_date:end_date].index
        if len(rebal_dates) < 2:
            raise ValueError(f"Insufficient rebalance dates in range {start_date} to {end_date}")

        # State tracking
        gross_val = self.initial_capital
        net_cost_val = self.initial_capital
        net_tax_val = self.initial_capital

        gross_nav = [gross_val]
        net_cost_nav = [net_cost_val]
        net_tax_nav = [net_tax_val]
        dates_nav = [rebal_dates[0]]

        current_holdings = {}     # {ticker: {"shares": n, "price": p, "weight": w}}
        current_weights = pd.Series(dtype=float)
        turnover_records = []
        cost_records = []
        tax_records = []

        daily_ret = self.prices.pct_change()

        for i in range(len(rebal_dates) - 1):
            t_curr = rebal_dates[i]
            t_next = rebal_dates[i + 1]

            # Signal snapshot at t_curr
            sig_t = signal_df.loc[t_curr]
            
            # Select target weights
            prev_dict = {t: w for t, w in current_weights.items() if w > 0}
            target_weights = allocator.select_portfolio(sig_t, prev_portfolio=prev_dict, daily_returns=daily_ret, date=t_curr)
            
            # Calculate turnover against drift weights
            all_tickers = list(set(target_weights.index).union(set(current_weights.index)))
            w_target_full = target_weights.reindex(all_tickers, fill_value=0.0)
            w_prev_full = current_weights.reindex(all_tickers, fill_value=0.0)

            turnover = 0.5 * np.abs(w_target_full - w_prev_full).sum()
            turnover_records.append({"date": t_curr, "turnover": turnover})

            # Calculate Rebalance Trades and Costs
            period_cost_inr = 0.0
            period_tax_inr = 0.0

            # 1. Process Sells
            for ticker in all_tickers:
                delta_w = w_target_full[ticker] - w_prev_full[ticker]
                if delta_w < -1e-6:
                    # Selling portion or full position
                    sell_notional = abs(delta_w) * net_cost_val
                    adv_val = self.adv20.loc[:t_curr, ticker].iloc[-1] if (self.adv20 is not None and ticker in self.adv20.columns) else None
                    sell_cost, _ = cost_model.compute_trade_cost(sell_notional, 'sell', adv_val)
                    period_cost_inr += sell_cost

                    # Tax tracking
                    p_curr = self.m_prices.loc[t_curr, ticker]
                    shares_to_sell = sell_notional / p_curr if (p_curr > 0 and not np.isnan(p_curr)) else 0
                    _, tax_due, _, _ = tax_engine.process_sell(ticker, t_curr, shares_to_sell, p_curr, sell_cost)
                    period_tax_inr += tax_due

            # 2. Process Buys
            for ticker in all_tickers:
                delta_w = w_target_full[ticker] - w_prev_full[ticker]
                if delta_w > 1e-6:
                    buy_notional = delta_w * net_cost_val
                    adv_val = self.adv20.loc[:t_curr, ticker].iloc[-1] if (self.adv20 is not None and ticker in self.adv20.columns) else None
                    buy_cost, _ = cost_model.compute_trade_cost(buy_notional, 'buy', adv_val)
                    period_cost_inr += buy_cost

                    p_curr = self.m_prices.loc[t_curr, ticker]
                    shares_to_buy = buy_notional / p_curr if (p_curr > 0 and not np.isnan(p_curr)) else 0
                    tax_engine.add_buy_lot(ticker, t_curr, shares_to_buy, p_curr, buy_cost)

            cost_records.append({"date": t_curr, "cost_inr": period_cost_inr})
            tax_records.append({"date": t_curr, "tax_inr": period_tax_inr})

            # Realized gross return over (t_curr, t_next]
            period_returns = (self.m_prices.loc[t_next] / self.m_prices.loc[t_curr]) - 1.0
            # Clean missing/delisted stocks (treat NaN return as 0 or terminal)
            period_returns = period_returns.reindex(target_weights.index).fillna(0.0)

            gross_period_ret = (target_weights * period_returns).sum()

            # Update NAVs
            gross_val = gross_val * (1.0 + gross_period_ret)
            
            # Net of costs
            net_cost_val = (net_cost_val - period_cost_inr) * (1.0 + gross_period_ret)
            
            # Net of costs and taxes
            net_tax_val = (net_tax_val - period_cost_inr - period_tax_inr) * (1.0 + gross_period_ret)

            gross_nav.append(gross_val)
            net_cost_nav.append(net_cost_val)
            net_tax_nav.append(net_tax_val)
            dates_nav.append(t_next)

            # Drift weights to next period
            end_weights = target_weights * (1.0 + period_returns)
            current_weights = end_weights / end_weights.sum() if end_weights.sum() > 0 else pd.Series(dtype=float)

        nav_df = pd.DataFrame({
            "Gross": gross_nav,
            "Net_Costs": net_cost_nav,
            "Net_Taxes": net_tax_nav
        }, index=pd.to_datetime(dates_nav))

        turnover_df = pd.DataFrame(turnover_records).set_index("date")
        cost_df = pd.DataFrame(cost_records).set_index("date")
        tax_df = pd.DataFrame(tax_records).set_index("date")

        return {
            "nav": nav_df,
            "turnover": turnover_df,
            "costs": cost_df,
            "taxes": tax_df,
            "tax_engine": tax_engine
        }
