"""
Support MA Strategy: Generates entry and exit signals.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from datetime import datetime
from ma_strategy.config import StrategyConfig
from ma_strategy.data_structures import Signal
from ma_strategy.support_analyzer import SupportAnalyzer
from ma_strategy.indicators import IndicatorEngine


class SupportMAStrategy:
    """Generate trading signals based on support MA analysis"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.support_analyzer = SupportAnalyzer(config)
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        start_index: int = 0
    ) -> pd.DataFrame:
        """
        Generate entry/exit signals for all bars.
        
        Args:
            df: DataFrame with price data and MA columns
            start_index: First bar index to generate signals from
            
        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()
        
        # Initialize signal columns
        df['signal'] = 0  # 0 = no signal, 1 = entry, -1 = exit
        df['signal_ma_length'] = np.nan
        df['signal_reason'] = ''
        df['ma_score'] = np.nan
        
        # Compute long-term MA for trend filter if enabled
        if self.config.trend_filter.enabled:
            trend_ma = IndicatorEngine.compute_long_term_ma(
                df, self.config.trend_filter.trend_ma_length, self.config.ma.type
            )
            df['trend_ma'] = trend_ma
        
        # Generate signals bar by bar
        for i in range(start_index, len(df)):
            # Compute support scores up to (but not including) current bar
            scores_df = self.support_analyzer.compute_support_scores_with_returns(
                df, current_bar=i
            )
            
            if scores_df.empty:
                continue
            
            best_ma_length = self.support_analyzer.get_best_ma(scores_df)
            if best_ma_length is None:
                continue
            
            # Get best MA score
            best_score = scores_df[scores_df['ma_length'] == best_ma_length]['score'].iloc[0]
            df.loc[i, 'ma_score'] = best_score
            
            # Get MA value at current bar
            ma_col = f'ma_{best_ma_length}'
            if ma_col not in df.columns:
                continue
            
            ma_value = df.loc[i, ma_col]
            if np.isnan(ma_value):
                continue
            
            # Check entry conditions
            if self._check_entry_conditions(df, i, best_ma_length, ma_value):
                df.loc[i, 'signal'] = 1
                df.loc[i, 'signal_ma_length'] = best_ma_length
                df.loc[i, 'signal_reason'] = 'ma_support_touch'
        
        return df
    
    def _check_entry_conditions(
        self,
        df: pd.DataFrame,
        bar_index: int,
        ma_length: int,
        ma_value: float
    ) -> bool:
        """
        Check if entry conditions are met at bar_index.
        
        Entry conditions:
        1. Price touches MA: low <= MA * (1 + tolerance) AND close >= MA
        2. Trend filter (if enabled): MA > MA[t-lookback] AND/OR close > trend_MA
        """
        tolerance = self.config.ma.entry_tolerance_pct
        low = df.loc[bar_index, 'low']
        close = df.loc[bar_index, 'close']
        
        # Condition 1: Price touches MA
        low_touched = low <= ma_value * (1 + tolerance)
        close_above = close >= ma_value
        
        if not (low_touched and close_above):
            return False
        
        # Condition 2: Trend filter (if enabled)
        if self.config.trend_filter.enabled:
            trend_lookback = self.config.trend_filter.trend_lookback_bars
            
            # Check MA slope
            if bar_index >= trend_lookback:
                ma_col = f'ma_{ma_length}'
                ma_current = df.loc[bar_index, ma_col]
                ma_past = df.loc[bar_index - trend_lookback, ma_col]
                
                if not np.isnan(ma_current) and not np.isnan(ma_past):
                    if ma_current <= ma_past:
                        return False
            
            # Check price vs trend MA
            if 'trend_ma' in df.columns:
                trend_ma_value = df.loc[bar_index, 'trend_ma']
                if not np.isnan(trend_ma_value):
                    if close <= trend_ma_value:
                        return False
        
        return True
    
    def check_exit_conditions(
        self,
        df: pd.DataFrame,
        bar_index: int,
        position: 'Position'  # Forward reference
    ) -> Tuple[bool, str]:
        """
        Check if exit conditions are met for a position.
        
        Returns:
            (should_exit, exit_reason)
        """
        exit_config = self.config.exits
        close = df.loc[bar_index, 'close']
        entry_price = position.entry_price
        
        # Stop loss
        if exit_config.stop_loss_pct is not None:
            stop_price = entry_price * (1 - exit_config.stop_loss_pct)
            if close <= stop_price:
                return True, 'stop_loss'
        
        # Stop below MA
        if exit_config.stop_below_ma_pct is not None and position.ma_length:
            ma_col = f'ma_{position.ma_length}'
            if ma_col in df.columns:
                ma_value = df.loc[bar_index, ma_col]
                if not np.isnan(ma_value):
                    stop_price = ma_value * (1 - exit_config.stop_below_ma_pct)
                    if close <= stop_price:
                        return True, 'stop_below_ma'
        
        # Take profit
        if exit_config.take_profit_R_multiple is not None:
            if position.initial_risk > 0:
                risk = position.initial_risk
                target_profit = risk * exit_config.take_profit_R_multiple
                target_price = entry_price + target_profit / position.shares
                if close >= target_price:
                    return True, 'take_profit'
        
        # Time exit
        if exit_config.max_holding_bars is not None:
            holding_bars = bar_index - position.entry_bar
            if holding_bars >= exit_config.max_holding_bars:
                return True, 'max_holding_bars'
        
        # MA cross exit
        if exit_config.exit_mode in ['ma_cross', 'combo']:
            if position.ma_length:
                ma_col = f'ma_{position.ma_length}'
                if ma_col in df.columns:
                    ma_value = df.loc[bar_index, ma_col]
                    if not np.isnan(ma_value):
                        exit_threshold = ma_value * (1 - exit_config.exit_tolerance_pct)
                        if close < exit_threshold:
                            return True, 'ma_cross'
        
        return False, ''

