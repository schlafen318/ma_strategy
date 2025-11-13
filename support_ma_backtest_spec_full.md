# Systematic Support-Moving-Average Backtesting & Walk-Forward Testing Specification

This document contains the **full system design** for a systematic
trading framework that learns which moving averages act as support and
then performs **walk-forward out-of-sample testing**.\
Engineers can directly implement this specification.

------------------------------------------------------------------------

# 1. Objective

Build a **backtesting framework** that:

1.  Works on **any security** using daily, weekly, or monthly OHLCV
    data.
2.  Finds the **best moving average (MA) that acted as support** in
    recent history.
3.  Generates **entry signals** when price retraces toward the selected
    MA.
4.  Simulates trades with proper exits, risk management, and slippage.
5.  Supports **walk-forward optimization**, producing a fully
    out-of-sample equity curve.

------------------------------------------------------------------------

# 2. Data Requirements

## 2.1 Required fields

-   `date`
-   `open`
-   `high`
-   `low`
-   `close`
-   `volume` (optional)

Data must be: - Clean (no duplicates) - Chronologically sorted -
Split/dividend adjusted if needed

## 2.2 Timeframes

Accepted inputs: - Daily - Weekly - Monthly

Optional: resample daily → weekly/monthly.

------------------------------------------------------------------------

# 3. Core Concept: Supportive Moving Averages

At each bar ( t ), the system:

1.  Looks back a configurable window (e.g., last 252 bars).
2.  Tests multiple MA lengths (10, 20, 30, 50, 100, 150, 200).
3.  Detects where price historically **touched** an MA and bounced.
4.  Measures forward returns after such touches.
5.  Scores each MA.
6.  Selects the best-scoring MA as the active support MA.
7.  Generates entry signals when today's price interacts with that MA.

------------------------------------------------------------------------

# 4. Configurable Parameters

Everything below must be exposed via a config object or YAML file.

## 4.1 MA configuration

-   `ma_type`: `"SMA"` or `"EMA"`
-   `ma_lengths`: `[10,20,30,50,100,150,200]`
-   `lookback_window_bars`: e.g., 252
-   `support_tolerance_pct`: e.g., 0.005 (0.5%)
-   `entry_tolerance_pct`: e.g., 0.005
-   `min_gap_between_touches_bars`: e.g., 5
-   `min_touches_for_valid_ma`: e.g., 5

## 4.2 Forward returns

Compute returns for multiple horizons: - e.g., `[1,5,20]` bars ahead.

Must ensure no forward-looking leakage: - Only compute forward returns
for bars strictly **before** current bar.

## 4.3 MA scoring

Weights: - win rate (W1) - median return (W2) - max drawdown penalty
(W3)

Definition:

    score = w1 * win_rate
          + w2 * median_return
          - w3 * max_drawdown

## 4.4 Entry conditions

Entry at bar `t` if:

1.  Best MA has valid score.
2.  Price touches MA:
    -   `low_t <= MA_t * (1 + entry_tolerance_pct)`
    -   AND `close_t >= MA_t`
3.  Trend filter (optional):
    -   `MA_t > MA_(t - trend_lookback_bars)`
    -   AND/OR `close_t > long_term_MA`

## 4.5 Exits

Configurable exit conditions:

-   Stop loss:
    -   `stop_loss_pct` OR
    -   `stop_below_ma_pct`
-   Take profit:
    -   `take_profit_R_multiple`
-   Time exit:
    -   `max_holding_bars`
-   MA cross exit:
    -   Exit if `close_t < MA_t * (1 - exit_tolerance_pct)`

## 4.6 Transaction costs

-   `commission_bps`
-   `slippage_bps`

## 4.7 Position sizing

Simplify initially: - Fixed fraction of equity risked per trade. - Or
fixed weight per trade.

------------------------------------------------------------------------

# 5. Algorithmic Flow (Per Bar)

## 5.1 Precomputation

-   Compute all MAs.
-   Compute long-term MA for trend filter (optional).

## 5.2 Support Analysis (Per Bar)

Inside lookback window: 1. Detect touches for each MA. 2. Evaluate
forward returns. 3. Compute win rates, medians, drawdowns. 4. Calculate
score. 5. Select best MA.

## 5.3 Entry logic

Use today's MA scores to generate signals.

## 5.4 Position Management

Update each open position: - P&L - Check exits - Apply
slippage/commission

------------------------------------------------------------------------

# 6. Components & Interfaces

## 6.1 DataLoader

    class DataLoader:
        def get_price_data(symbol, timeframe) -> pd.DataFrame:
            ...

## 6.2 IndicatorEngine

    class IndicatorEngine:
        def compute_mas(df, ma_lengths, ma_type):
            ...

## 6.3 SupportAnalyzer

    class SupportAnalyzer:
        def compute_support_scores(df, config) -> pd.DataFrame:
            ...

## 6.4 StrategyEngine

    class SupportMAStrategy:
        def generate_signals(df, config) -> list[Signal]:
            ...

## 6.5 Backtester

    class Backtester:
        def run(df, config, start_trade_index=0, initial_equity=1e6):
            ...

------------------------------------------------------------------------

# 7. Walk-Forward Testing (Critical)

## 7.1 Purpose

Avoid lookahead bias and overfitting by:

1.  Splitting data into **training** and **testing** windows.
2.  Optimizing parameters only using training data.
3.  Applying parameters only to the subsequent test period.
4.  Stitching all test windows together into one continuous, fully OOS
    equity curve.

## 7.2 Config

    walk_forward:
      enabled: true
      train_period_bars: 756
      test_period_bars: 252
      step_bars: 252
      continuous_equity: true
      optimization_objective: "sharpe"
      param_grid:
        support_tolerance_pct: [0.003, 0.005, 0.01]
        entry_tolerance_pct: [0.003, 0.005, 0.01]
        trend_ma_length: [50, 100, 200]
        lookback_window_bars: [126, 252, 504]
        exit_mode: ["ma_cross", "combo"]

------------------------------------------------------------------------

# 8. Walk-Forward Algorithm

For each walk-forward window:

------------------------------------------------------------------------

## Step 1 --- Training Phase

1.  Slice training window.
2.  For each parameter set:
    -   Generate signals within training window.
    -   Backtest trades.
    -   Compute Sharpe / CAGR / DD per config.
3.  Select best parameter set for that window.

------------------------------------------------------------------------

## Step 2 --- Out-of-Sample Trading

Use full history **up to the end of test window** to compute indicators.

Then:

    Backtester.run(
        df_segment,
        cfg = best_params,
        start_trade_index = test_start,
        initial_equity = equity_from_prev_window
    )

Extract: - test equity curve - test trades - per-window metrics

------------------------------------------------------------------------

# 9. Stitched Equity Curve

If `continuous_equity = true`: - Equity flows from one window into the
next.

We obtain: - Global out-of-sample equity curve - Fully walk-forward,
realistic, no leakage

------------------------------------------------------------------------

# 10. No-Leakage Requirements (Mandatory)

1.  Parameter selection uses **only training data**.
2.  Strategy can use historical data ≤ current bar (including training +
    earlier test bars).
3.  Forward returns for support scoring must never cross into:
    -   current bar
    -   future bars
    -   test window during training
4.  Backtester must only place trades from `start_trade_index` forward.

------------------------------------------------------------------------

# 11. Output Objects

    class WalkForwardWindowResult:
        window_id
        train_start
        train_end
        test_start
        test_end
        best_params
        train_metrics
        test_metrics
        test_trades
        test_equity_curve

    class WalkForwardResult:
        symbol
        windows   # list of WalkForwardWindowResult
        oos_equity_curve
        overall_metrics

------------------------------------------------------------------------

# 12. Minimal YAML Config Example

    data:
      timeframe: daily

    ma:
      type: SMA
      lengths: [10,20,30,50,100,150,200]
      lookback_window_bars: 252
      support_tolerance_pct: 0.005
      entry_tolerance_pct: 0.005
      min_gap_between_touches_bars: 5
      min_touches_for_valid_ma: 5

    trend_filter:
      enabled: true
      trend_ma_length: 100
      trend_lookback_bars: 20

    entries:
      allow_multiple_positions: false

    exits:
      exit_mode: combo
      stop_loss_pct: 0.07
      stop_below_ma_pct: 0.02
      take_profit_R_multiple: 2.0
      max_holding_bars: 60
      exit_tolerance_pct: 0.005

    risk:
      risk_per_trade_pct_of_equity: 0.01

    costs:
      commission_bps: 1.0
      slippage_bps: 2.0

    walk_forward:
      enabled: true
      train_period_bars: 756
      test_period_bars: 252
      step_bars: 252
      continuous_equity: true
      optimization_objective: sharpe
      param_grid:
        support_tolerance_pct: [0.003,0.005]
        trend_ma_length: [50,100]

------------------------------------------------------------------------

# 13. Implementation Notes for Engineers

-   Use vectorized operations where possible.
-   MA scoring can be loop-based initially.
-   Ensure strict non-leakage in support scoring.
-   Allow pluggable components (e.g., cost model, indicator engine).
-   Ensure reproducibility via controlled random seeds.
-   Generate:
    -   Trade logs
    -   Per-window OOS results
    -   Global OOS equity curve
    -   Parameter heatmaps per window

------------------------------------------------------------------------

# End of Document
