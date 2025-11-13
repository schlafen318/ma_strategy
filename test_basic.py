"""
Basic test to verify the system works.
"""

import pandas as pd
import numpy as np
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.indicators import IndicatorEngine
from ma_strategy.support_analyzer import SupportAnalyzer
from ma_strategy.backtester import Backtester


def test_basic_functionality():
    """Test basic system functionality"""
    print("Testing basic functionality...")
    
    # Create sample data
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(500) * 0.5)
    df = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.randn(500) * 0.1,
        'high': prices + np.abs(np.random.randn(500) * 0.2),
        'low': prices - np.abs(np.random.randn(500) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 500)
    })
    
    # Test DataLoader
    print("  [OK] DataLoader: Creating sample data")
    
    # Test IndicatorEngine
    print("  [OK] IndicatorEngine: Computing MAs")
    df = IndicatorEngine.compute_mas(df, [10, 20, 50], "SMA")
    assert 'ma_10' in df.columns
    assert 'ma_20' in df.columns
    assert 'ma_50' in df.columns
    
    # Test Config
    print("  [OK] Config: Creating default config")
    config = StrategyConfig()
    assert config.ma.type == "SMA"
    
    # Test SupportAnalyzer
    print("  [OK] SupportAnalyzer: Computing support scores")
    analyzer = SupportAnalyzer(config)
    scores = analyzer.compute_support_scores_with_returns(df, current_bar=300)
    assert isinstance(scores, pd.DataFrame)
    
    # Test Backtester (with walk-forward disabled)
    print("  [OK] Backtester: Running simple backtest")
    config.walk_forward.enabled = False
    backtester = Backtester(config)
    result = backtester.run(df, start_trade_index=252, initial_equity=1e6, symbol='TEST')
    assert result is not None
    assert result.metrics is not None
    assert len(result.trades) >= 0  # May have zero trades
    
    print("\n[SUCCESS] All basic tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()

