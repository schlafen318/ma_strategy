"""
Backtester: Simulates trading with position management and costs.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime
from ma_strategy.config import StrategyConfig
from ma_strategy.data_structures import Trade, Position, BacktestResult
from ma_strategy.strategy import SupportMAStrategy
from ma_strategy.indicators import IndicatorEngine
from ma_strategy.metrics import compute_metrics


class Backtester:
    """Backtest the support MA strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy = SupportMAStrategy(config)
    
    def run(
        self,
        df: pd.DataFrame,
        start_trade_index: int = 0,
        initial_equity: float = 1e6,
        symbol: str = "UNKNOWN"
    ) -> BacktestResult:
        """
        Run backtest on price data.
        
        Args:
            df: DataFrame with OHLCV data
            start_trade_index: First bar index to start trading
            initial_equity: Starting equity
            symbol: Symbol identifier
            
        Returns:
            BacktestResult with trades, equity curve, and metrics
        """
        # Precompute indicators
        df = df.copy()
        df = IndicatorEngine.compute_mas(
            df, self.config.ma.lengths, self.config.ma.type
        )
        
        # Generate signals
        df = self.strategy.generate_signals(df, start_index=start_trade_index)
        
        # Initialize tracking
        equity = initial_equity
        positions: List[Position] = []
        trades: List[Trade] = []
        equity_curve = []
        
        # Process each bar
        for i in range(start_trade_index, len(df)):
            current_date = df.loc[i, 'date']
            current_close = df.loc[i, 'close']
            
            # Check for exits on existing positions
            positions_to_close = []
            for pos_idx, position in enumerate(positions):
                should_exit, exit_reason = self.strategy.check_exit_conditions(
                    df, i, position
                )
                
                if should_exit:
                    # Close position
                    trade = self._close_position(
                        df, i, position, exit_reason, current_close
                    )
                    trades.append(trade)
                    equity += trade.pnl
                    positions_to_close.append(pos_idx)
            
            # Remove closed positions (in reverse order to maintain indices)
            for pos_idx in reversed(positions_to_close):
                positions.pop(pos_idx)
            
            # Check for new entries
            if df.loc[i, 'signal'] == 1:
                # Check if we can open new position
                if not self.config.entries.allow_multiple_positions and len(positions) > 0:
                    continue
                
                # Open new position
                position = self._open_position(df, i, equity, current_close)
                if position:
                    positions.append(position)
            
            # Update equity curve
            # Calculate current equity including open positions
            current_equity = equity
            for position in positions:
                # Mark-to-market open positions
                unrealized_pnl = (current_close - position.entry_price) * position.shares
                current_equity += unrealized_pnl
            
            equity_curve.append({
                'date': current_date,
                'equity': current_equity
            })
        
        # Close any remaining positions at end
        final_close = df.loc[len(df) - 1, 'close']
        for position in positions:
            trade = self._close_position(
                df, len(df) - 1, position, 'end_of_data', final_close
            )
            trades.append(trade)
            equity += trade.pnl
        
        # Final equity update
        final_equity = equity
        if equity_curve:
            equity_curve[-1]['equity'] = final_equity
        
        # Create equity curve DataFrame
        equity_df = pd.DataFrame(equity_curve)
        
        # Compute metrics
        metrics = compute_metrics(trades, equity_df, initial_equity)
        
        # Create result
        result = BacktestResult(
            symbol=symbol,
            start_date=df.loc[start_trade_index, 'date'],
            end_date=df.loc[len(df) - 1, 'date'],
            initial_equity=initial_equity,
            final_equity=final_equity,
            trades=trades,
            equity_curve=equity_df,
            metrics=metrics,
            config=self.config
        )
        
        return result
    
    def _open_position(
        self,
        df: pd.DataFrame,
        bar_index: int,
        current_equity: float,
        current_price: float
    ) -> Optional[Position]:
        """
        Open a new position.
        
        Returns:
            Position object or None if position cannot be opened
        """
        ma_length = df.loc[bar_index, 'signal_ma_length']
        if pd.isna(ma_length):
            return None
        
        ma_length = int(ma_length)
        
        # Calculate position size based on risk
        risk_pct = self.config.risk.risk_per_trade_pct_of_equity
        risk_amount = current_equity * risk_pct
        
        # Determine stop loss price for risk calculation
        stop_loss_pct = self.config.exits.stop_loss_pct
        if stop_loss_pct is None:
            stop_loss_pct = 0.02  # Default 2% stop
        
        stop_price = current_price * (1 - stop_loss_pct)
        price_risk = current_price - stop_price
        
        if price_risk <= 0:
            return None
        
        # Calculate shares based on risk
        shares = risk_amount / price_risk
        
        # Apply slippage to entry
        slippage_pct = self.config.costs.slippage_bps / 10000
        entry_price = current_price * (1 + slippage_pct)
        
        # Calculate commission
        commission = (entry_price * shares) * (self.config.costs.commission_bps / 10000)
        
        # Adjust shares to account for commission
        # Simplified: reduce shares slightly to account for commission
        net_entry_value = entry_price * shares + commission
        if net_entry_value > current_equity:
            # Can't afford full position, reduce shares
            shares = (current_equity - commission) / entry_price
        
        # Recalculate stop prices
        stop_loss_price = entry_price * (1 - stop_loss_pct)
        take_profit_price = None
        if self.config.exits.take_profit_R_multiple is not None:
            take_profit_price = entry_price + (entry_price - stop_loss_price) * \
                self.config.exits.take_profit_R_multiple
        
        position = Position(
            entry_bar=bar_index,
            entry_date=df.loc[bar_index, 'date'],
            entry_price=entry_price,
            shares=shares,
            ma_length=ma_length,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            initial_risk=risk_amount
        )
        
        return position
    
    def _close_position(
        self,
        df: pd.DataFrame,
        bar_index: int,
        position: Position,
        exit_reason: str,
        current_price: float
    ) -> Trade:
        """
        Close a position and create a Trade record.
        """
        # Apply slippage to exit
        slippage_pct = self.config.costs.slippage_bps / 10000
        exit_price = current_price * (1 - slippage_pct)
        
        # Calculate commissions
        entry_value = position.entry_price * position.shares
        exit_value = exit_price * position.shares
        commission_entry = entry_value * (self.config.costs.commission_bps / 10000)
        commission_exit = exit_value * (self.config.costs.commission_bps / 10000)
        
        # Calculate P&L
        pnl = (exit_price - position.entry_price) * position.shares - \
              commission_entry - commission_exit
        pnl_pct = (exit_price / position.entry_price - 1) * 100
        
        # Slippage costs (already incorporated in exit_price)
        slippage_entry = (position.entry_price - df.loc[position.entry_bar, 'close']) * \
            position.shares if position.entry_bar < len(df) else 0
        slippage_exit = (df.loc[bar_index, 'close'] - exit_price) * position.shares
        
        holding_bars = bar_index - position.entry_bar
        
        trade = Trade(
            entry_bar=position.entry_bar,
            exit_bar=bar_index,
            entry_date=position.entry_date,
            exit_date=df.loc[bar_index, 'date'],
            entry_price=position.entry_price,
            exit_price=exit_price,
            shares=position.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission_entry=commission_entry,
            commission_exit=commission_exit,
            slippage_entry=slippage_entry,
            slippage_exit=slippage_exit,
            exit_reason=exit_reason,
            holding_bars=holding_bars,
            ma_length=position.ma_length
        )
        
        return trade


