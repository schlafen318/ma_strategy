"""
Example usage with Alpha Vantage API.
"""

import os
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester
from ma_strategy.walk_forward import WalkForwardEngine


def example_alpha_vantage_simple():
    """Example: Fetch data from Alpha Vantage and run simple backtest"""
    print("=" * 60)
    print("Example: Alpha Vantage - Simple Backtest")
    print("=" * 60)
    
    # Get API key from environment or set it here
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("Warning: ALPHA_VANTAGE_API_KEY not set in environment.")
        print("You can get a free API key from: https://www.alphavantage.co/support/#api-key")
        api_key = input("Enter your Alpha Vantage API key (or press Enter to skip): ").strip()
        if not api_key:
            print("Skipping Alpha Vantage example.")
            return
    
    # Load config
    config = StrategyConfig.from_yaml('config_example.yaml')
    config.walk_forward.enabled = False  # Disable for simple backtest
    
    # Fetch data from Alpha Vantage
    symbol = 'AAPL'  # Apple stock
    print(f"\nFetching daily data for {symbol} from Alpha Vantage...")
    
    try:
        df = DataLoader.get_price_data(
            symbol,
            symbol=symbol,
            from_alpha_vantage=True,
            timeframe='daily',
            api_key=api_key
        )
        
        print(f"Fetched {len(df)} bars")
        print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        
        # Run backtest
        print("\nRunning backtest...")
        backtester = Backtester(config)
        result = backtester.run(
            df,
            start_trade_index=config.ma.lookback_window_bars,
            initial_equity=1e6,
            symbol=symbol
        )
        
        # Print results
        print(f"\nBacktest Results for {symbol}")
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
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def example_alpha_vantage_direct():
    """Example: Using AlphaVantageLoader directly"""
    print("\n" + "=" * 60)
    print("Example: Alpha Vantage - Direct Usage")
    print("=" * 60)
    
    from ma_strategy.alpha_vantage_loader import AlphaVantageLoader
    
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("Warning: ALPHA_VANTAGE_API_KEY not set in environment.")
        return
    
    # Create loader
    loader = AlphaVantageLoader(api_key=api_key)
    
    # Fetch different timeframes
    symbols = ['SPY', 'QQQ', 'AAPL']
    
    for symbol in symbols:
        try:
            print(f"\nFetching daily data for {symbol}...")
            df = loader.get_daily_data(symbol, outputsize='full', adjusted=True)
            print(f"  Fetched {len(df)} bars")
            print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
            print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")


def example_alpha_vantage_weekly():
    """Example: Fetch weekly data"""
    print("\n" + "=" * 60)
    print("Example: Alpha Vantage - Weekly Data")
    print("=" * 60)
    
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("Warning: ALPHA_VANTAGE_API_KEY not set in environment.")
        return
    
    symbol = 'SPY'
    print(f"\nFetching weekly data for {symbol}...")
    
    try:
        df = DataLoader.get_price_data(
            symbol,
            symbol=symbol,
            from_alpha_vantage=True,
            timeframe='weekly',
            api_key=api_key
        )
        
        print(f"Fetched {len(df)} weekly bars")
        print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"\nFirst 5 rows:")
        print(df.head())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Alpha Vantage Examples")
    print("=" * 60)
    print("\nNote: You need an Alpha Vantage API key.")
    print("Get one for free at: https://www.alphavantage.co/support/#api-key")
    print("Set it as environment variable: ALPHA_VANTAGE_API_KEY")
    print("\n" + "=" * 60)
    
    try:
        example_alpha_vantage_simple()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError in example: {e}")
        import traceback
        traceback.print_exc()
    
    # Uncomment to run additional examples:
    # example_alpha_vantage_direct()
    # example_alpha_vantage_weekly()

