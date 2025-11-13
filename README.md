# Moving Average Support Strategy Backtesting Framework

A comprehensive backtesting framework for systematic trading strategies that identify moving averages acting as support levels, with full walk-forward optimization and out-of-sample testing capabilities.

## Features

- **Support MA Detection**: Automatically identifies which moving averages have historically acted as support
- **Dynamic MA Selection**: Selects the best-performing MA based on historical touch performance
- **Walk-Forward Optimization**: Prevents overfitting through proper train/test window separation
- **Comprehensive Exits**: Multiple exit strategies (stop loss, take profit, time-based, MA cross)
- **Transaction Costs**: Realistic simulation with commissions and slippage
- **Risk Management**: Position sizing based on percentage of equity risked
- **Performance Metrics**: Full suite of metrics (Sharpe, CAGR, Calmar, drawdown, etc.)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Using Alpha Vantage API (Recommended)

Get a free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key) and set it as an environment variable:

```bash
export ALPHA_VANTAGE_API_KEY=your_api_key_here
```

Then fetch data directly:

```python
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester

# Load configuration
config = StrategyConfig.from_yaml('config_example.yaml')
config.walk_forward.enabled = False

# Fetch data from Alpha Vantage
df = DataLoader.get_price_data(
    'AAPL',  # Symbol
    symbol='AAPL',
    from_alpha_vantage=True,
    timeframe='daily'  # 'daily', 'weekly', or 'monthly'
)

# Run backtest
backtester = Backtester(config)
result = backtester.run(df, start_trade_index=252, initial_equity=1e6, symbol='AAPL')

# View results
print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
```

### Simple Backtest with CSV File

```python
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.backtester import Backtester

# Load configuration
config = StrategyConfig.from_yaml('config_example.yaml')
config.walk_forward.enabled = False  # Disable for simple backtest

# Load data (CSV with columns: date, open, high, low, close, volume)
df = DataLoader.get_price_data('path/to/data.csv', symbol='SPY')

# Run backtest
backtester = Backtester(config)
result = backtester.run(df, start_trade_index=252, initial_equity=1e6, symbol='SPY')

# View results
print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
```

### Walk-Forward Testing

```python
from ma_strategy.config import StrategyConfig
from ma_strategy.data_loader import DataLoader
from ma_strategy.walk_forward import WalkForwardEngine

# Load configuration with walk-forward enabled
config = StrategyConfig.from_yaml('config_example.yaml')

# Load data
df = DataLoader.get_price_data('path/to/data.csv', symbol='SPY')

# Run walk-forward optimization
wf_engine = WalkForwardEngine(config)
result = wf_engine.run(df, symbol='SPY')

# View out-of-sample results
print(f"OOS Total Return: {result.overall_metrics.total_return_pct:.2f}%")
print(f"OOS Sharpe Ratio: {result.overall_metrics.sharpe_ratio:.2f}")
```

## Configuration

The system is configured via YAML files. See `config_example.yaml` for a complete example.

### Key Configuration Sections

- **ma**: Moving average settings (type, lengths, lookback window, tolerances)
- **trend_filter**: Optional trend filter to only trade in uptrends
- **entries**: Entry signal configuration
- **exits**: Exit strategy (stop loss, take profit, time-based, MA cross)
- **risk**: Position sizing and risk management
- **costs**: Transaction costs (commissions, slippage)
- **walk_forward**: Walk-forward optimization settings

## Architecture

### Core Components

1. **DataLoader**: Loads and validates OHLCV price data
2. **IndicatorEngine**: Computes moving averages (SMA/EMA)
3. **SupportAnalyzer**: Detects MA touches and scores MAs based on forward returns
4. **SupportMAStrategy**: Generates entry/exit signals
5. **Backtester**: Simulates trading with position management and costs
6. **WalkForwardEngine**: Performs walk-forward optimization and testing

### Data Structures

- **Signal**: Trading signal (entry/exit)
- **Trade**: Completed trade with full details
- **Position**: Open position tracking
- **BacktestResult**: Complete backtest results with metrics
- **WalkForwardResult**: Walk-forward results with per-window and overall metrics

## Algorithm Overview

1. **Support Analysis**: For each bar, look back over a configurable window and:
   - Detect where price touched each MA and bounced
   - Compute forward returns after touches
   - Score each MA based on win rate, median return, and drawdown
   - Select the best-scoring MA

2. **Entry Signals**: Generate entry when:
   - Best MA has valid score
   - Price touches MA (low within tolerance, close above MA)
   - Optional trend filter passes

3. **Exits**: Exit positions based on:
   - Stop loss (percentage or below MA)
   - Take profit (R-multiple)
   - Time-based (max holding period)
   - MA cross (price falls below MA)

4. **Walk-Forward**: For each window:
   - Optimize parameters on training data
   - Test on out-of-sample data
   - Stitch equity curves for continuous OOS performance

## No-Leakage Guarantees

The system ensures no forward-looking bias:

- Parameter optimization uses only training data
- Support scoring uses only historical data up to (but not including) current bar
- Forward returns are computed only for touches that occurred before current bar
- Test windows are strictly out-of-sample

## Data Sources

### Alpha Vantage API

The framework includes built-in support for fetching data from Alpha Vantage:

```python
from ma_strategy.data_loader import DataLoader

# Fetch daily data
df = DataLoader.get_price_data(
    'AAPL',
    symbol='AAPL',
    from_alpha_vantage=True,
    timeframe='daily',
    api_key='your_api_key'  # Optional if set as env var
)

# Fetch weekly or monthly data
df_weekly = DataLoader.get_price_data('SPY', symbol='SPY', from_alpha_vantage=True, timeframe='weekly')
df_monthly = DataLoader.get_price_data('QQQ', symbol='QQQ', from_alpha_vantage=True, timeframe='monthly')
```

**Note**: Alpha Vantage free tier has rate limits (5 calls/minute, 500 calls/day). The loader automatically handles rate limiting.

### CSV Files

Load data from CSV files with columns: `date`, `open`, `high`, `low`, `close`, `volume` (volume optional).

### Command Line with Alpha Vantage

```bash
# Set API key
export ALPHA_VANTAGE_API_KEY=your_key_here

# Run backtest with Alpha Vantage data
python -m ma_strategy config_example.yaml AAPL --alpha-vantage

# Specify timeframe
python -m ma_strategy config_example.yaml SPY --alpha-vantage weekly
```

## Example Usage

See `example_usage.py` for complete examples including:
- Simple backtest
- Walk-forward optimization
- Custom configuration

See `example_alpha_vantage.py` for Alpha Vantage integration examples.

## Requirements

- Python 3.8+
- pandas >= 2.0.0
- numpy >= 1.24.0
- pyyaml >= 6.0
- scipy >= 1.10.0

## License

MIT
