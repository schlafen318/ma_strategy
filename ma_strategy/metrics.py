"""
Performance metrics computation.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from ma_strategy.data_structures import BacktestMetrics, Trade


def compute_metrics(
    trades: List[Trade],
    equity_curve: pd.DataFrame,
    initial_equity: float
) -> BacktestMetrics:
    """
    Compute comprehensive backtest metrics.
    
    Args:
        trades: List of completed trades
        equity_curve: DataFrame with 'date' and 'equity' columns
        initial_equity: Starting equity
        
    Returns:
        BacktestMetrics object
    """
    if not trades:
        return BacktestMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_return_pct=0.0
        )
    
    # Basic trade statistics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.pnl > 0)
    losing_trades = sum(1 for t in trades if t.pnl < 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    
    # P&L statistics
    total_pnl = sum(t.pnl for t in trades)
    total_return_pct = (total_pnl / initial_equity) * 100 if initial_equity > 0 else 0.0
    
    # Win/loss statistics
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [abs(t.pnl) for t in trades if t.pnl < 0]
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    profit_factor = (sum(wins) / sum(losses)) if losses and sum(losses) > 0 else 0.0
    
    # Holding period
    avg_holding_bars = np.mean([t.holding_bars for t in trades]) if trades else 0.0
    
    # Drawdown
    equity_values = equity_curve['equity'].values
    running_max = np.maximum.accumulate(equity_values)
    drawdown = (equity_values - running_max) / running_max
    max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
    max_drawdown_pct = max_drawdown * 100
    
    # Sharpe ratio
    if len(equity_curve) > 1:
        returns = equity_curve['equity'].pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = None
    else:
        sharpe_ratio = None
    
    # Sortino ratio (downside deviation)
    if len(equity_curve) > 1:
        returns = equity_curve['equity'].pct_change().dropna()
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = (returns.mean() / downside_returns.std()) * np.sqrt(252)
        else:
            sortino_ratio = None
    else:
        sortino_ratio = None
    
    # CAGR
    if len(equity_curve) > 1:
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        days = (end_date - start_date).days
        years = days / 365.25 if days > 0 else 1.0
        
        final_equity = equity_curve['equity'].iloc[-1]
        if initial_equity > 0 and years > 0:
            cagr = ((final_equity / initial_equity) ** (1 / years) - 1) * 100
        else:
            cagr = None
    else:
        cagr = None
    
    # Calmar ratio
    if cagr is not None and max_drawdown_pct > 0:
        calmar_ratio = cagr / max_drawdown_pct
    else:
        calmar_ratio = None
    
    return BacktestMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        total_pnl=total_pnl,
        total_return_pct=total_return_pct,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        avg_holding_bars=avg_holding_bars,
        cagr=cagr,
        calmar_ratio=calmar_ratio
    )


def compute_sharpe_ratio(equity_curve: pd.DataFrame) -> Optional[float]:
    """Compute Sharpe ratio from equity curve"""
    if len(equity_curve) < 2:
        return None
    
    returns = equity_curve['equity'].pct_change().dropna()
    if len(returns) == 0 or returns.std() == 0:
        return None
    
    return (returns.mean() / returns.std()) * np.sqrt(252)


def compute_cagr(equity_curve: pd.DataFrame, initial_equity: float) -> Optional[float]:
    """Compute CAGR from equity curve"""
    if len(equity_curve) < 2 or initial_equity <= 0:
        return None
    
    start_date = equity_curve['date'].iloc[0]
    end_date = equity_curve['date'].iloc[-1]
    days = (end_date - start_date).days
    years = days / 365.25 if days > 0 else None
    
    if years is None or years <= 0:
        return None
    
    final_equity = equity_curve['equity'].iloc[-1]
    return ((final_equity / initial_equity) ** (1 / years) - 1) * 100

