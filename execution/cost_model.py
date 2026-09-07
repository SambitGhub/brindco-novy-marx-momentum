"""
Brindco Execution Cost Model.
Implemented the exact desk cost stack for Indian Cash Equities (Delivery & Intraday),
along with a non-linear square-root market impact model for Mid/Small caps.
"""

import numpy as np
import pandas as pd
import config

class BrindcoCostModel:
    def __init__(self, mode="delivery", gamma=config.MARKET_IMPACT_GAMMA, participation_cap=config.PARTICIPATION_CAP):
        self.mode = mode
        self.gamma = gamma
        self.participation_cap = participation_cap
        self.cost_params = config.COST_STACK[mode]

    def compute_trade_cost(self, notional, side, adv20=None):
        """
        Computes the all-in execution cost in INR for a given trade.
        
        Parameters:
        - notional: float, trade value in INR (> 0)
        - side: str, 'buy' or 'sell'
        - adv20: float, 20-day Average Daily Volume in INR (optional)
        
        Returns:
        - cost_inr: float, total execution friction in INR
        - cost_bps: float, total cost expressed in basis points
        """
        if notional <= 0:
            return 0.0, 0.0

        p = self.cost_params
        # Statutory & Exchange charges (in bps)
        if side.lower() == 'buy':
            statutory_bps = (
                p["stt_buy_bps"] + 
                p["stamp_duty_buy_bps"] + 
                p["exchange_charges_bps"] + 
                p["sebi_gst_bps"]
            )
        else:
            statutory_bps = (
                p["stt_sell_bps"] + 
                p["stamp_duty_sell_bps"] + 
                p["exchange_charges_bps"] + 
                p["sebi_gst_bps"]
            )

        # Base bid-ask half-spread
        spread_bps = p["base_spread_impact_bps"] / 2.0

        # Market Impact calculation
        impact_bps = 0.0
        if adv20 is not None and adv20 > 0:
            participation = notional / adv20
            # Apply participation cap warning/penalty if > cap
            effective_part = min(participation, self.participation_cap)
            impact_bps = self.gamma * np.sqrt(effective_part)
            if participation > self.participation_cap:
                # Quadratic penalty beyond participation cap to reflect illiquidity choke
                excess = participation - self.participation_cap
                impact_bps += self.gamma * 2.0 * (excess ** 2)

        total_bps = statutory_bps + spread_bps + impact_bps
        cost_inr = notional * (total_bps / 10000.0)
        return cost_inr, total_bps

    def round_trip_cost_summary(self, adv20=None, trade_size=10_00_000):
        """
        Returns estimated one-way and round-trip cost in basis points.
        """
        buy_cost, buy_bps = self.compute_trade_cost(trade_size, 'buy', adv20)
        sell_cost, sell_bps = self.compute_trade_cost(trade_size, 'sell', adv20)
        round_trip_bps = buy_bps + sell_bps
        return {
            "buy_bps": buy_bps,
            "sell_bps": sell_bps,
            "round_trip_bps": round_trip_bps
        }
