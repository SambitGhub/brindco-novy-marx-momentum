"""
Indian Capital Gains Tax Engine (FIFO lot-by-lot tracking).
Calculates Short-Term Capital Gains (STCG @ 20% for < 365 days)
and Long-Term Capital Gains (LTCG @ 12.5% for >= 365 days).
"""

import pandas as pd
import numpy as np
from collections import deque
import config

class TaxLot:
    def __init__(self, ticker, buy_date, shares, buy_price, buy_cost):
        self.ticker = ticker
        self.buy_date = pd.to_datetime(buy_date)
        self.shares = shares
        self.remaining_shares = shares
        self.buy_price = buy_price
        self.buy_cost_per_share = buy_cost / shares if shares > 0 else 0.0

class IndianTaxEngine:
    def __init__(self, stcg_rate=config.TAX_RATES["stcg_rate"], 
                 ltcg_rate=config.TAX_RATES["ltcg_rate"],
                 ltcg_exemption_annual=config.TAX_RATES["ltcg_exemption_inr"]):
        self.stcg_rate = stcg_rate
        self.ltcg_rate = ltcg_rate
        self.ltcg_exemption_annual = ltcg_exemption_annual
        
        # Mapping from ticker -> deque of TaxLots
        self.lots = {}
        
        # Annual tracking of realized gains and taxes
        self.realized_history = []
        self.annual_ltcg_gains = {}

    def add_buy_lot(self, ticker, buy_date, shares, buy_price, buy_cost):
        if ticker not in self.lots:
            self.lots[ticker] = deque()
        self.lots[ticker].append(TaxLot(ticker, buy_date, shares, buy_price, buy_cost))

    def process_sell(self, ticker, sell_date, shares_to_sell, sell_price, sell_cost):
        """
        Depletes lots FIFO and calculates tax liability.
        Returns: net_cash_proceeds, tax_due, stcg_gain, ltcg_gain
        """
        sell_date = pd.to_datetime(sell_date)
        if ticker not in self.lots or not self.lots[ticker]:
            # Edge case: selling without lot record (e.g. initial setup)
            gross_proceeds = shares_to_sell * sell_price
            return gross_proceeds - sell_cost, 0.0, 0.0, 0.0

        needed = shares_to_sell
        gross_proceeds = shares_to_sell * sell_price
        cost_basis = 0.0
        total_stcg_gain = 0.0
        total_ltcg_gain = 0.0
        sell_cost_per_share = sell_cost / shares_to_sell if shares_to_sell > 0 else 0.0

        while needed > 0 and self.lots[ticker]:
            lot = self.lots[ticker][0]
            take = min(needed, lot.remaining_shares)
            
            holding_days = (sell_date - lot.buy_date).days
            lot_cost = take * (lot.buy_price + lot.buy_cost_per_share)
            lot_proceeds = take * (sell_price - sell_cost_per_share)
            lot_gain = lot_proceeds - lot_cost
            
            cost_basis += lot_cost
            
            if holding_days < 365:
                # STCG
                if lot_gain > 0:
                    total_stcg_gain += lot_gain
            else:
                # LTCG
                if lot_gain > 0:
                    total_ltcg_gain += lot_gain

            lot.remaining_shares -= take
            needed -= take
            if lot.remaining_shares <= 1e-6:
                self.lots[ticker].popleft()

        # Compute Tax
        stcg_tax = total_stcg_gain * self.stcg_rate
        
        year = sell_date.year
        if year not in self.annual_ltcg_gains:
            self.annual_ltcg_gains[year] = 0.0
        
        # Apply exemption to LTCG
        prev_ltcg = self.annual_ltcg_gains[year]
        self.annual_ltcg_gains[year] += total_ltcg_gain
        
        taxable_ltcg = max(0.0, min(total_ltcg_gain, (self.annual_ltcg_gains[year] - self.ltcg_exemption_annual))) if self.annual_ltcg_gains[year] > self.ltcg_exemption_annual else 0.0
        ltcg_tax = taxable_ltcg * self.ltcg_rate

        total_tax = stcg_tax + ltcg_tax
        net_cash = gross_proceeds - sell_cost - total_tax

        self.realized_history.append({
            "ticker": ticker,
            "sell_date": sell_date,
            "shares": shares_to_sell,
            "gross_proceeds": gross_proceeds,
            "cost_basis": cost_basis,
            "sell_cost": sell_cost,
            "stcg_gain": total_stcg_gain,
            "ltcg_gain": total_ltcg_gain,
            "stcg_tax": stcg_tax,
            "ltcg_tax": ltcg_tax,
            "total_tax": total_tax,
            "net_cash": net_cash
        })

        return net_cash, total_tax, total_stcg_gain, total_ltcg_gain
