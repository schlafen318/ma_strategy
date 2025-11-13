"""
Data structures for signals, trades, and results.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd


@dataclass
class Signal:
    """Trading signal"""
    bar_index: int
    date: datetime
    price: float
    ma_value: float
    ma_length: int
    signal_type: str  # "entry" or "exit"
    reason: str


@dataclass
class Trade:
    """Completed trade"""
    entry_bar: int
    exit_bar: int
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    commission_entry: float
    commission_exit: float
    slippage_entry: float
    slippage_exit: float
    exit_reason: str
    holding_bars: int
    ma_length: Optional[int] = None


@dataclass
class Position:
    """Open position"""
    entry_bar: int
    entry_date: datetime
    entry_price: float
    shares: float
    ma_length: Optional[int] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    initial_risk: float = 0.0  # Dollar amount risked


@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_pct: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    avg_holding_bars: float = 0.0
    cagr: Optional[float] = None
    calmar_ratio: Optional[float] = None


@dataclass
class BacktestResult:
    """Complete backtest result"""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_equity: float
    final_equity: float
    trades: List[Trade]
    equity_curve: pd.DataFrame  # date, equity columns
    metrics: BacktestMetrics
    config: Any  # StrategyConfig


@dataclass
class WalkForwardWindowResult:
    """Result for a single walk-forward window"""
    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    best_params: Dict[str, Any]
    train_metrics: BacktestMetrics
    test_metrics: BacktestMetrics
    test_trades: List[Trade]
    test_equity_curve: pd.DataFrame


@dataclass
class WalkForwardResult:
    """Complete walk-forward result"""
    symbol: str
    windows: List[WalkForwardWindowResult]
    oos_equity_curve: pd.DataFrame
    overall_metrics: BacktestMetrics


