"""
Support Analyzer: Detects MA touches and scores moving averages.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from ma_strategy.config import StrategyConfig


class SupportAnalyzer:
    """Analyze which MAs act as support and score them"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.ma_config = config.ma
    
    def compute_support_scores(
        self,
        df: pd.DataFrame,
        current_bar: int,
        lookback_end: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Compute support scores for all MAs at current bar.
        
        Args:
            df: DataFrame with price data and MA columns
            current_bar: Current bar index (exclusive - don't use this bar)
            lookback_end: Optional end of lookback window (defaults to current_bar)
            
        Returns:
            DataFrame with columns: ma_length, score, win_rate, median_return, max_drawdown, num_touches
        """
        if lookback_end is None:
            lookback_end = current_bar
        
        # Determine lookback window
        lookback_start = max(0, lookback_end - self.ma_config.lookback_window_bars)
        analysis_window = df.iloc[lookback_start:lookback_end].copy()
        
        if len(analysis_window) < self.ma_config.min_touches_for_valid_ma:
            # Return empty scores if insufficient data
            return pd.DataFrame(columns=['ma_length', 'score', 'win_rate', 
                                       'median_return', 'max_drawdown', 'num_touches'])
        
        scores = []
        
        for ma_length in self.ma_config.lengths:
            ma_col = f'ma_{ma_length}'
            if ma_col not in df.columns:
                continue
            
            # Extract MA values for analysis window
            ma_values = analysis_window[ma_col].values
            prices_low = analysis_window['low'].values
            prices_high = analysis_window['high'].values
            prices_close = analysis_window['close'].values
            
            # Detect touches and compute forward returns
            touch_indices, forward_returns = self._detect_touches_and_returns(
                ma_values, prices_low, prices_high, prices_close,
                analysis_window.index.values,
                current_bar
            )
            
            if len(touch_indices) < self.ma_config.min_touches_for_valid_ma:
                scores.append({
                    'ma_length': ma_length,
                    'score': -np.inf,
                    'win_rate': 0.0,
                    'median_return': 0.0,
                    'max_drawdown': 1.0,
                    'num_touches': len(touch_indices)
                })
                continue
            
            # Compute metrics
            win_rate = self._compute_win_rate(forward_returns)
            median_return = np.median(forward_returns) if len(forward_returns) > 0 else 0.0
            max_drawdown = self._compute_max_drawdown(forward_returns)
            
            # Compute score
            weights = self.ma_config.score_weights
            score = (
                weights.get('win_rate', 0.4) * win_rate +
                weights.get('median_return', 0.4) * median_return -
                weights.get('max_drawdown', 0.2) * max_drawdown
            )
            
            scores.append({
                'ma_length': ma_length,
                'score': score,
                'win_rate': win_rate,
                'median_return': median_return,
                'max_drawdown': max_drawdown,
                'num_touches': len(touch_indices)
            })
        
        return pd.DataFrame(scores)
    
    def _detect_touches_and_returns(
        self,
        ma_values: np.ndarray,
        prices_low: np.ndarray,
        prices_high: np.ndarray,
        prices_close: np.ndarray,
        window_indices: np.ndarray,
        current_bar: int
    ) -> Tuple[List[int], List[float]]:
        """
        Detect MA touches and compute forward returns.
        
        CRITICAL: Only compute forward returns for touches that occur
        strictly before current_bar to avoid leakage.
        
        Returns:
            Tuple of (touch_indices_in_window, forward_returns)
        """
        touch_indices = []
        forward_returns = []
        tolerance = self.ma_config.support_tolerance_pct
        
        # Use the primary forward return horizon for scoring
        primary_horizon = self.ma_config.forward_return_horizons[0] if \
            self.ma_config.forward_return_horizons else 5
        
        last_touch_idx = -self.ma_config.min_gap_between_touches_bars - 1
        
        for i in range(len(ma_values)):
            if np.isnan(ma_values[i]):
                continue
            
            # Check if price touched MA (low came within tolerance)
            ma_val = ma_values[i]
            low_touched = prices_low[i] <= ma_val * (1 + tolerance)
            close_above = prices_close[i] >= ma_val
            
            if low_touched and close_above:
                # Check minimum gap between touches
                if i - last_touch_idx >= self.ma_config.min_gap_between_touches_bars:
                    # Get absolute index in full dataframe
                    abs_idx = window_indices[i]
                    
                    # CRITICAL: Only compute forward return if we have future data
                    # AND the touch occurred before current_bar
                    if abs_idx + primary_horizon < current_bar:
                        touch_indices.append(abs_idx)
                        last_touch_idx = i
                        
                        # Compute forward return
                        # We need to access the full dataframe for forward returns
                        # This will be handled by the caller with proper bounds checking
                        pass
        
        # Now compute forward returns using the full dataframe
        # This is done separately to ensure we have access to future prices
        return touch_indices, forward_returns
    
    def compute_support_scores_with_returns(
        self,
        df: pd.DataFrame,
        current_bar: int,
        lookback_end: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Compute support scores with proper forward return calculation.
        This version ensures no leakage by checking bounds.
        """
        if lookback_end is None:
            lookback_end = current_bar
        
        lookback_start = max(0, lookback_end - self.ma_config.lookback_window_bars)
        analysis_window = df.iloc[lookback_start:lookback_end].copy()
        
        if len(analysis_window) < self.ma_config.min_touches_for_valid_ma:
            return pd.DataFrame(columns=['ma_length', 'score', 'win_rate', 
                                       'median_return', 'max_drawdown', 'num_touches'])
        
        scores = []
        primary_horizon = self.ma_config.forward_return_horizons[0] if \
            self.ma_config.forward_return_horizons else 5
        
        for ma_length in self.ma_config.lengths:
            ma_col = f'ma_{ma_length}'
            if ma_col not in df.columns:
                continue
            
            ma_values = analysis_window[ma_col].values
            prices_low = analysis_window['low'].values
            prices_high = analysis_window['high'].values
            prices_close = analysis_window['close'].values
            window_indices = analysis_window.index.values
            
            touch_indices = []
            forward_returns = []
            tolerance = self.ma_config.support_tolerance_pct
            last_touch_idx = -self.ma_config.min_gap_between_touches_bars - 1
            
            # Detect touches
            for i in range(len(ma_values)):
                if np.isnan(ma_values[i]):
                    continue
                
                ma_val = ma_values[i]
                low_touched = prices_low[i] <= ma_val * (1 + tolerance)
                close_above = prices_close[i] >= ma_val
                
                if low_touched and close_above:
                    if i - last_touch_idx >= self.ma_config.min_gap_between_touches_bars:
                        abs_idx = window_indices[i]
                        
                        # CRITICAL: Ensure we can compute forward return without leakage
                        if abs_idx + primary_horizon < current_bar:
                            # Compute forward return
                            entry_price = prices_close[i]  # Use close price at touch
                            exit_idx = abs_idx + primary_horizon
                            
                            if exit_idx < len(df):
                                exit_price = df.loc[exit_idx, 'close']
                                forward_return = (exit_price - entry_price) / entry_price
                                touch_indices.append(abs_idx)
                                forward_returns.append(forward_return)
                                last_touch_idx = i
            
            if len(touch_indices) < self.ma_config.min_touches_for_valid_ma:
                scores.append({
                    'ma_length': ma_length,
                    'score': -np.inf,
                    'win_rate': 0.0,
                    'median_return': 0.0,
                    'max_drawdown': 1.0,
                    'num_touches': len(touch_indices)
                })
                continue
            
            # Compute metrics
            win_rate = self._compute_win_rate(forward_returns)
            median_return = np.median(forward_returns) if len(forward_returns) > 0 else 0.0
            max_drawdown = self._compute_max_drawdown(forward_returns)
            
            # Compute score
            weights = self.ma_config.score_weights
            score = (
                weights.get('win_rate', 0.4) * win_rate +
                weights.get('median_return', 0.4) * median_return -
                weights.get('max_drawdown', 0.2) * max_drawdown
            )
            
            scores.append({
                'ma_length': ma_length,
                'score': score,
                'win_rate': win_rate,
                'median_return': median_return,
                'max_drawdown': max_drawdown,
                'num_touches': len(touch_indices)
            })
        
        return pd.DataFrame(scores)
    
    def get_best_ma(
        self,
        scores_df: pd.DataFrame
    ) -> Optional[int]:
        """
        Get the best MA length from scores.
        
        Returns:
            MA length or None if no valid MA
        """
        if scores_df.empty:
            return None
        
        # Filter out invalid scores
        valid = scores_df[scores_df['score'] > -np.inf]
        if valid.empty:
            return None
        
        best = valid.loc[valid['score'].idxmax()]
        return int(best['ma_length'])
    
    @staticmethod
    def _compute_win_rate(returns: List[float]) -> float:
        """Compute win rate (fraction of positive returns)"""
        if not returns:
            return 0.0
        return sum(1 for r in returns if r > 0) / len(returns)
    
    @staticmethod
    def _compute_max_drawdown(returns: List[float]) -> float:
        """
        Compute maximum drawdown from returns.
        Drawdown is measured as the worst cumulative decline.
        """
        if not returns:
            return 1.0
        
        cumulative = np.cumprod(1 + np.array(returns))
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return abs(np.min(drawdown)) if len(drawdown) > 0 else 1.0


