"""
Main entry point for the MA strategy system.
"""

import sys
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester
from ma_strategy.walk_forward import WalkForwardEngine


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m ma_strategy <config_file> [data_file|symbol] [symbol] [--alpha-vantage]")
        print("Examples:")
        print("  python -m ma_strategy config_example.yaml data.csv SPY")
        print("  python -m ma_strategy config_example.yaml SPY --alpha-vantage")
        print("  python -m ma_strategy config_example.yaml AAPL --alpha-vantage daily")
        sys.exit(1)
    
    config_path = sys.argv[1]
    data_path = sys.argv[2] if len(sys.argv) > 2 else None
    symbol = sys.argv[3] if len(sys.argv) > 3 and '--alpha-vantage' not in sys.argv else None
    use_alpha_vantage = '--alpha-vantage' in sys.argv
    
    # If using Alpha Vantage, data_path is the symbol
    if use_alpha_vantage:
        if not data_path:
            print("Error: Symbol required when using --alpha-vantage")
            sys.exit(1)
        symbol = data_path
        timeframe = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '--alpha-vantage' else 'daily'
        if timeframe == '--alpha-vantage':
            timeframe = 'daily'
    elif not symbol and data_path:
        # Try to infer symbol from filename or use data_path as symbol
        import os
        if os.path.exists(data_path):
            # It's a file, try to get symbol from filename or use default
            base_name = os.path.splitext(os.path.basename(data_path))[0]
            symbol = base_name.upper() if len(base_name) <= 5 else "UNKNOWN"
        else:
            symbol = data_path.upper()
    
    # Load configuration
    try:
        config = StrategyConfig.from_yaml(config_path)
        print(f"Loaded configuration from {config_path}")
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Load data
    if data_path or symbol:
        try:
            if use_alpha_vantage:
                print(f"Fetching data from Alpha Vantage for {symbol} ({timeframe})...")
                df = DataLoader.get_price_data(
                    symbol,
                    symbol=symbol,
                    from_alpha_vantage=True,
                    timeframe=timeframe
                )
            else:
                df = DataLoader.get_price_data(data_path, symbol=symbol)
            print(f"Loaded {len(df)} bars of data for {symbol}")
            if len(df) > 0:
                print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("No data file or symbol provided. Exiting.")
        sys.exit(1)
    
    # Run backtest or walk-forward
    if config.walk_forward.enabled:
        print("\nRunning walk-forward optimization...")
        wf_engine = WalkForwardEngine(config)
        result = wf_engine.run(df, symbol=symbol)
        
        print(f"\n{'='*60}")
        print(f"Walk-Forward Results for {symbol}")
        print(f"{'='*60}")
        print(f"Windows: {len(result.windows)}")
        print(f"Total OOS Trades: {result.overall_metrics.total_trades}")
        print(f"OOS Win Rate: {result.overall_metrics.win_rate:.2%}")
        print(f"OOS Total Return: {result.overall_metrics.total_return_pct:.2f}%")
        if result.overall_metrics.sharpe_ratio:
            print(f"OOS Sharpe Ratio: {result.overall_metrics.sharpe_ratio:.2f}")
        if result.overall_metrics.cagr:
            print(f"OOS CAGR: {result.overall_metrics.cagr:.2f}%")
        print(f"OOS Max Drawdown: {result.overall_metrics.max_drawdown_pct:.2f}%")
    else:
        print("\nRunning simple backtest...")
        backtester = Backtester(config)
        result = backtester.run(
            df,
            start_trade_index=config.ma.lookback_window_bars,
            initial_equity=1e6,
            symbol=symbol
        )
        
        print(f"\n{'='*60}")
        print(f"Backtest Results for {symbol}")
        print(f"{'='*60}")
        print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
        print(f"Initial Equity: ${result.initial_equity:,.2f}")
        print(f"Final Equity: ${result.final_equity:,.2f}")
        print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
        print(f"Total Trades: {result.metrics.total_trades}")
        print(f"Win Rate: {result.metrics.win_rate:.2%}")
        if result.metrics.sharpe_ratio:
            print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
        if result.metrics.cagr:
            print(f"CAGR: {result.metrics.cagr:.2f}%")
        print(f"Max Drawdown: {result.metrics.max_drawdown_pct:.2f}%")


if __name__ == "__main__":
    main()


