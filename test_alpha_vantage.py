"""
Test Alpha Vantage integration with provided API key.
"""

import os
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester

# API key provided by user
API_KEY = "VT0RO0SAME6YV9PC"

def test_alpha_vantage_fetch():
    """Test fetching data from Alpha Vantage"""
    print("=" * 60)
    print("Testing Alpha Vantage Data Fetching")
    print("=" * 60)
    
    # Test symbols
    symbols = ['AAPL', 'SPY', 'MSFT']
    
    for symbol in symbols:
        try:
            print(f"\nFetching daily data for {symbol}...")
            df = DataLoader.get_price_data(
                symbol,
                symbol=symbol,
                from_alpha_vantage=True,
                timeframe='daily',
                api_key=API_KEY
            )
            
            print(f"  Success! Fetched {len(df)} bars")
            print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
            print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")
            print(f"  First close: ${df['close'].iloc[0]:.2f}")
            
            # Show first few rows
            print(f"\n  First 3 rows:")
            print(df[['date', 'open', 'high', 'low', 'close', 'volume']].head(3).to_string(index=False))
            
            return df  # Return first successful fetch for further testing
            
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    return None


def test_backtest_with_alpha_vantage():
    """Test running a backtest with Alpha Vantage data"""
    print("\n" + "=" * 60)
    print("Testing Backtest with Alpha Vantage Data")
    print("=" * 60)
    
    try:
        # Fetch data
        print("\nFetching data for AAPL...")
        df = DataLoader.get_price_data(
            'AAPL',
            symbol='AAPL',
            from_alpha_vantage=True,
            timeframe='daily',
            api_key=API_KEY
        )
        
        print(f"Fetched {len(df)} bars")
        
        # Load config
        try:
            config = StrategyConfig.from_yaml('config_example.yaml')
        except:
            # Use default config if file doesn't exist
            config = StrategyConfig()
        
        config.walk_forward.enabled = False
        
        # Run backtest
        print("\nRunning backtest...")
        backtester = Backtester(config)
        result = backtester.run(
            df,
            start_trade_index=config.ma.lookback_window_bars,
            initial_equity=1e6,
            symbol='AAPL'
        )
        
        # Print results
        print(f"\n{'='*60}")
        print(f"Backtest Results for AAPL")
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
        
        if result.metrics.total_trades > 0:
            print(f"\nTrade Statistics:")
            print(f"  Average Win: ${result.metrics.avg_win:,.2f}")
            print(f"  Average Loss: ${result.metrics.avg_loss:,.2f}")
            print(f"  Profit Factor: {result.metrics.profit_factor:.2f}")
            print(f"  Average Holding Period: {result.metrics.avg_holding_bars:.1f} bars")
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Alpha Vantage Integration Test")
    print("Using API key: VT0RO0SAME6YV9PC")
    print("\nNote: This script uses a hardcoded API key for testing.")
    print("For production, use environment variables: export ALPHA_VANTAGE_API_KEY=your_key")
    print("=" * 60)
    
    # Test 1: Fetch data
    df = test_alpha_vantage_fetch()
    
    # Test 2: Run backtest if data fetch succeeded
    if df is not None:
        result = test_backtest_with_alpha_vantage()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

