"""
Walk-Forward Testing Engine: Optimizes parameters and tests out-of-sample.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from itertools import product
from ma_strategy.config import StrategyConfig, WalkForwardConfig
from ma_strategy.data_structures import (
    WalkForwardWindowResult, WalkForwardResult, BacktestMetrics
)
from ma_strategy.backtester import Backtester
from ma_strategy.metrics import compute_metrics, compute_sharpe_ratio, compute_cagr


class WalkForwardEngine:
    """Walk-forward optimization and testing"""
    
    def __init__(self, base_config: StrategyConfig):
        self.base_config = base_config
        self.wf_config = base_config.walk_forward
        self._last_train_result = None
    
    def run(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN"
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization and testing.
        
        Args:
            df: Full price DataFrame
            symbol: Symbol identifier
            
        Returns:
            WalkForwardResult with all windows and stitched equity curve
        """
        if not self.wf_config.enabled:
            raise ValueError("Walk-forward is not enabled in config")
        
        windows = []
        all_oos_trades = []
        all_oos_equity_curves = []
        current_equity = 1e6  # Initial equity
        
        # Generate walk-forward windows
        window_starts = self._generate_window_starts(len(df))
        
        for window_id, (train_start, train_end, test_start, test_end) in enumerate(window_starts):
            print(f"Processing window {window_id + 1}/{len(window_starts)}: "
                  f"Train [{train_start}:{train_end}], Test [{test_start}:{test_end}]")
            
            # Reset train result for this window
            self._last_train_result = None
            
            # Step 1: Training phase - optimize parameters
            train_df = df.iloc[train_start:train_end].copy()
            best_params = self._optimize_parameters(train_df, window_id)
            
            # Step 2: Test phase - run backtest with best params on test window
            # CRITICAL: Use full history up to test_end for indicator computation
            # but only trade in test window
            test_df = df.iloc[:test_end].copy()  # Full history for indicators
            
            # Create config with best parameters
            test_config = self._apply_params(self.base_config, best_params)
            backtester = Backtester(test_config)
            
            # Run backtest starting at test_start
            test_result = backtester.run(
                test_df,
                start_trade_index=test_start,
                initial_equity=current_equity,
                symbol=symbol
            )
            
            # Extract test window results
            test_window_df = test_df.iloc[test_start:test_end]
            test_equity_curve = test_result.equity_curve[
                test_result.equity_curve['date'].isin(test_window_df['date'].values)
            ].copy()
            
            # Get train metrics (from optimization)
            train_metrics = self._get_train_metrics()
            
            # Create window result
            window_result = WalkForwardWindowResult(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                best_params=best_params,
                train_metrics=train_metrics,
                test_metrics=test_result.metrics,
                test_trades=test_result.trades,
                test_equity_curve=test_equity_curve
            )
            windows.append(window_result)
            
            # Update equity for next window if continuous
            if self.wf_config.continuous_equity:
                current_equity = test_result.final_equity
            
            # Collect OOS trades and equity
            all_oos_trades.extend(test_result.trades)
            all_oos_equity_curves.append(test_equity_curve)
        
        # Stitch OOS equity curves
        oos_equity_curve = self._stitch_equity_curves(all_oos_equity_curves)
        
        # Compute overall metrics
        overall_metrics = compute_metrics(all_oos_trades, oos_equity_curve, 1e6)
        
        result = WalkForwardResult(
            symbol=symbol,
            windows=windows,
            oos_equity_curve=oos_equity_curve,
            overall_metrics=overall_metrics
        )
        
        return result
    
    def _generate_window_starts(
        self,
        total_bars: int
    ) -> List[tuple[int, int, int, int]]:
        """
        Generate walk-forward window boundaries.
        
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        windows = []
        train_bars = self.wf_config.train_period_bars
        test_bars = self.wf_config.test_period_bars
        step_bars = self.wf_config.step_bars
        
        train_start = 0
        train_end = train_start + train_bars
        test_start = train_end
        test_end = test_start + test_bars
        
        while test_end <= total_bars:
            windows.append((train_start, train_end, test_start, test_end))
            
            # Move window forward
            train_start += step_bars
            train_end = train_start + train_bars
            test_start = train_end
            test_end = test_start + test_bars
        
        return windows
    
    def _optimize_parameters(
        self,
        train_df: pd.DataFrame,
        window_id: int
    ) -> Dict[str, Any]:
        """
        Optimize parameters on training data.
        
        Returns:
            Dictionary of best parameter values
        """
        param_grid = self.wf_config.param_grid
        
        if not param_grid:
            # No optimization, use base config
            return {}
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        best_score = -np.inf
        best_params = {}
        best_result = None
        
        print(f"  Optimizing over {len(combinations)} parameter combinations...")
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # Create config with these parameters
            test_config = self._apply_params(self.base_config, params)
            
            # Run backtest on training data
            backtester = Backtester(test_config)
            result = backtester.run(
                train_df,
                start_trade_index=0,
                initial_equity=1e6,
                symbol="TRAIN"
            )
            
            # Compute objective metric
            score = self._compute_objective_score(result)
            
            if score > best_score:
                best_score = score
                best_params = params
                best_result = result
        
        print(f"  Best params: {best_params} (score: {best_score:.4f})")
        
        # Store best result for later retrieval
        if best_result:
            self._last_train_result = best_result
        
        return best_params
    
    def _apply_params(
        self,
        base_config: StrategyConfig,
        params: Dict[str, Any]
    ) -> StrategyConfig:
        """
        Apply parameter values to config.
        
        Returns:
            New StrategyConfig with parameters applied
        """
        # Create a copy of config dict
        config_dict = base_config.to_dict()
        
        # Apply parameters
        for key, value in params.items():
            # Map parameter names to config paths
            if key == 'support_tolerance_pct':
                config_dict['ma']['support_tolerance_pct'] = value
            elif key == 'entry_tolerance_pct':
                config_dict['ma']['entry_tolerance_pct'] = value
            elif key == 'trend_ma_length':
                config_dict['trend_filter']['trend_ma_length'] = value
            elif key == 'lookback_window_bars':
                config_dict['ma']['lookback_window_bars'] = value
            elif key == 'exit_mode':
                config_dict['exits']['exit_mode'] = value
            # Add more parameter mappings as needed
        
        # Create new config from dict
        return StrategyConfig.from_dict(config_dict)
    
    def _compute_objective_score(self, result: Any) -> float:
        """
        Compute optimization objective score from backtest result.
        
        Returns:
            Score (higher is better)
        """
        objective = self.wf_config.optimization_objective.lower()
        
        if objective == 'sharpe':
            if result.metrics.sharpe_ratio is not None:
                return result.metrics.sharpe_ratio
            return -np.inf
        elif objective == 'cagr':
            if result.metrics.cagr is not None:
                return result.metrics.cagr
            return -np.inf
        elif objective == 'calmar':
            if result.metrics.calmar_ratio is not None:
                return result.metrics.calmar_ratio
            return -np.inf
        else:
            # Default to Sharpe
            if result.metrics.sharpe_ratio is not None:
                return result.metrics.sharpe_ratio
            return -np.inf
    
    def _get_train_metrics(self) -> BacktestMetrics:
        """
        Get training metrics from last optimization.
        """
        if self._last_train_result:
            return self._last_train_result.metrics
        
        # Return placeholder if no result available
        return BacktestMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_return_pct=0.0
        )
    
    def _stitch_equity_curves(
        self,
        equity_curves: List[pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Stitch multiple equity curves into one continuous curve.
        
        Args:
            equity_curves: List of equity curve DataFrames
            
        Returns:
            Single stitched equity curve
        """
        if not equity_curves:
            return pd.DataFrame(columns=['date', 'equity'])
        
        # If continuous equity, we need to scale subsequent curves
        if self.wf_config.continuous_equity:
            stitched = []
            prev_equity = None
            
            for i, curve in enumerate(equity_curves):
                if curve.empty:
                    continue
                
                if i == 0:
                    stitched.append(curve)
                    prev_equity = curve['equity'].iloc[-1]
                else:
                    # Scale this curve to start from previous end
                    first_equity = curve['equity'].iloc[0]
                    scale_factor = prev_equity / first_equity if first_equity > 0 else 1.0
                    scaled_curve = curve.copy()
                    scaled_curve['equity'] = scaled_curve['equity'] * scale_factor
                    stitched.append(scaled_curve)
                    prev_equity = scaled_curve['equity'].iloc[-1]
            
            if stitched:
                result = pd.concat(stitched, ignore_index=True)
                result = result.drop_duplicates(subset=['date']).sort_values('date')
                return result
        
        # Non-continuous: just concatenate
        result = pd.concat(equity_curves, ignore_index=True)
        result = result.drop_duplicates(subset=['date']).sort_values('date')
        return result

