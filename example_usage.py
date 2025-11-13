"""
Example usage of the MA Strategy backtesting system.
"""

import pandas as pd
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester
from ma_strategy.walk_forward import WalkForwardEngine


def example_simple_backtest():
    """Example: Simple backtest without walk-forward"""
    print("=" * 60)
    print("Example 1: Simple Backtest")
    print("=" * 60)
    
    # Load config
    config = StrategyConfig.from_yaml('config_example.yaml')
    
    # Disable walk-forward for simple backtest
    config.walk_forward.enabled = False
    
    # Load data (example - you would load your actual data)
    # df = DataLoader.get_price_data('path/to/your/data.csv', symbol='SPY')
    
    # For demonstration, create sample data
    dates = pd.date_range('2020-01-01', periods=1000, freq='D')
    import numpy as np
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(1000) * 0.5)
    df = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.randn(1000) * 0.1,
        'high': prices + np.abs(np.random.randn(1000) * 0.2),
        'low': prices - np.abs(np.random.randn(1000) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 1000)
    })
    
    # Run backtest
    backtester = Backtester(config)
    result = backtester.run(df, start_trade_index=252, initial_equity=1e6, symbol='EXAMPLE')
    
    # Print results
    print(f"\nBacktest Results for {result.symbol}")
    print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
    print(f"Initial Equity: ${result.initial_equity:,.2f}")
    print(f"Final Equity: ${result.final_equity:,.2f}")
    print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
    print(f"Total Trades: {result.metrics.total_trades}")
    print(f"Win Rate: {result.metrics.win_rate:.2%}")
    print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}" if result.metrics.sharpe_ratio else "Sharpe Ratio: N/A")
    print(f"Max Drawdown: {result.metrics.max_drawdown_pct:.2f}%")
    print(f"CAGR: {result.metrics.cagr:.2f}%" if result.metrics.cagr else "CAGR: N/A")
    
    return result


def example_walk_forward():
    """Example: Walk-forward optimization and testing"""
    print("\n" + "=" * 60)
    print("Example 2: Walk-Forward Testing")
    print("=" * 60)
    
    # Load config
    config = StrategyConfig.from_yaml('config_example.yaml')
    
    # Load data (example - you would load your actual data)
    # df = DataLoader.get_price_data('path/to/your/data.csv', symbol='SPY')
    
    # For demonstration, create sample data
    dates = pd.date_range('2015-01-01', periods=2000, freq='D')
    import numpy as np
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(2000) * 0.5)
    df = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.randn(2000) * 0.1,
        'high': prices + np.abs(np.random.randn(2000) * 0.2),
        'low': prices - np.abs(np.random.randn(2000) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 2000)
    })
    
    # Run walk-forward
    wf_engine = WalkForwardEngine(config)
    result = wf_engine.run(df, symbol='EXAMPLE')
    
    # Print results
    print(f"\nWalk-Forward Results for {result.symbol}")
    print(f"Number of Windows: {len(result.windows)}")
    print(f"\nOverall Out-of-Sample Metrics:")
    print(f"Total Trades: {result.overall_metrics.total_trades}")
    print(f"Win Rate: {result.overall_metrics.win_rate:.2%}")
    print(f"Total Return: {result.overall_metrics.total_return_pct:.2f}%")
    print(f"Sharpe Ratio: {result.overall_metrics.sharpe_ratio:.2f}" if result.overall_metrics.sharpe_ratio else "Sharpe Ratio: N/A")
    print(f"Max Drawdown: {result.overall_metrics.max_drawdown_pct:.2f}%")
    print(f"CAGR: {result.overall_metrics.cagr:.2f}%" if result.overall_metrics.cagr else "CAGR: N/A")
    
    # Print per-window summary
    print(f"\nPer-Window Summary:")
    for window in result.windows[:5]:  # Show first 5 windows
        print(f"  Window {window.window_id}: "
              f"Test Sharpe={window.test_metrics.sharpe_ratio:.2f}" if window.test_metrics.sharpe_ratio else f"  Window {window.window_id}: Test Sharpe=N/A",
              f", Trades={window.test_metrics.total_trades}, "
              f"Return={window.test_metrics.total_return_pct:.2f}%")
    
    return result


def example_custom_config():
    """Example: Create config programmatically"""
    print("\n" + "=" * 60)
    print("Example 3: Custom Configuration")
    print("=" * 60)
    
    # Create config from scratch
    config = StrategyConfig()
    
    # Customize MA settings
    config.ma.type = "EMA"
    config.ma.lengths = [20, 50, 100, 200]
    config.ma.lookback_window_bars = 126
    
    # Customize exits
    config.exits.exit_mode = "combo"
    config.exits.stop_loss_pct = 0.05
    config.exits.take_profit_R_multiple = 3.0
    
    # Disable walk-forward for simple backtest
    config.walk_forward.enabled = False
    
    print("Custom configuration created:")
    print(f"  MA Type: {config.ma.type}")
    print(f"  MA Lengths: {config.ma.lengths}")
    print(f"  Stop Loss: {config.exits.stop_loss_pct:.1%}")
    print(f"  Take Profit R-Multiple: {config.exits.take_profit_R_multiple}")
    
    return config


if __name__ == "__main__":
    # Run examples
    try:
        result1 = example_simple_backtest()
    except Exception as e:
        print(f"Error in simple backtest: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        result2 = example_walk_forward()
    except Exception as e:
        print(f"Error in walk-forward: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        config = example_custom_config()
    except Exception as e:
        print(f"Error in custom config: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


