"""
Configuration management for the MA strategy system.
"""

import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class MAConfig:
    """Moving Average configuration"""
    type: str = "SMA"  # "SMA" or "EMA"
    lengths: List[int] = field(default_factory=lambda: [10, 20, 30, 50, 100, 150, 200])
    lookback_window_bars: int = 252
    support_tolerance_pct: float = 0.005
    entry_tolerance_pct: float = 0.005
    min_gap_between_touches_bars: int = 5
    min_touches_for_valid_ma: int = 5
    forward_return_horizons: List[int] = field(default_factory=lambda: [1, 5, 20])
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        "win_rate": 0.4,
        "median_return": 0.4,
        "max_drawdown": 0.2
    })


@dataclass
class TrendFilterConfig:
    """Trend filter configuration"""
    enabled: bool = True
    trend_ma_length: int = 100
    trend_lookback_bars: int = 20


@dataclass
class EntryConfig:
    """Entry signal configuration"""
    allow_multiple_positions: bool = False


@dataclass
class ExitConfig:
    """Exit configuration"""
    exit_mode: str = "combo"  # "ma_cross", "combo"
    stop_loss_pct: Optional[float] = 0.07
    stop_below_ma_pct: Optional[float] = 0.02
    take_profit_R_multiple: Optional[float] = 2.0
    max_holding_bars: Optional[int] = 60
    exit_tolerance_pct: float = 0.005


@dataclass
class RiskConfig:
    """Risk management configuration"""
    risk_per_trade_pct_of_equity: float = 0.01


@dataclass
class CostsConfig:
    """Transaction costs configuration"""
    commission_bps: float = 1.0
    slippage_bps: float = 2.0


@dataclass
class WalkForwardConfig:
    """Walk-forward testing configuration"""
    enabled: bool = True
    train_period_bars: int = 756
    test_period_bars: int = 252
    step_bars: int = 252
    continuous_equity: bool = True
    optimization_objective: str = "sharpe"  # "sharpe", "cagr", "calmar"
    param_grid: Dict[str, List[Any]] = field(default_factory=dict)


@dataclass
class DataConfig:
    """Data configuration"""
    timeframe: str = "daily"  # "daily", "weekly", "monthly"


@dataclass
class StrategyConfig:
    """Complete strategy configuration"""
    data: DataConfig = field(default_factory=DataConfig)
    ma: MAConfig = field(default_factory=MAConfig)
    trend_filter: TrendFilterConfig = field(default_factory=TrendFilterConfig)
    entries: EntryConfig = field(default_factory=EntryConfig)
    exits: ExitConfig = field(default_factory=ExitConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    costs: CostsConfig = field(default_factory=CostsConfig)
    walk_forward: WalkForwardConfig = field(default_factory=WalkForwardConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'StrategyConfig':
        """Load configuration from YAML file"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        if 'data' in data:
            config.data = DataConfig(**data['data'])
        
        if 'ma' in data:
            ma_data = data['ma']
            config.ma = MAConfig(
                type=ma_data.get('type', 'SMA'),
                lengths=ma_data.get('lengths', [10, 20, 30, 50, 100, 150, 200]),
                lookback_window_bars=ma_data.get('lookback_window_bars', 252),
                support_tolerance_pct=ma_data.get('support_tolerance_pct', 0.005),
                entry_tolerance_pct=ma_data.get('entry_tolerance_pct', 0.005),
                min_gap_between_touches_bars=ma_data.get('min_gap_between_touches_bars', 5),
                min_touches_for_valid_ma=ma_data.get('min_touches_for_valid_ma', 5),
                forward_return_horizons=ma_data.get('forward_return_horizons', [1, 5, 20]),
                score_weights=ma_data.get('score_weights', {
                    "win_rate": 0.4,
                    "median_return": 0.4,
                    "max_drawdown": 0.2
                })
            )
        
        if 'trend_filter' in data:
            config.trend_filter = TrendFilterConfig(**data['trend_filter'])
        
        if 'entries' in data:
            config.entries = EntryConfig(**data['entries'])
        
        if 'exits' in data:
            config.exits = ExitConfig(**data['exits'])
        
        if 'risk' in data:
            config.risk = RiskConfig(**data['risk'])
        
        if 'costs' in data:
            config.costs = CostsConfig(**data['costs'])
        
        if 'walk_forward' in data:
            wf_data = data['walk_forward']
            config.walk_forward = WalkForwardConfig(
                enabled=wf_data.get('enabled', True),
                train_period_bars=wf_data.get('train_period_bars', 756),
                test_period_bars=wf_data.get('test_period_bars', 252),
                step_bars=wf_data.get('step_bars', 252),
                continuous_equity=wf_data.get('continuous_equity', True),
                optimization_objective=wf_data.get('optimization_objective', 'sharpe'),
                param_grid=wf_data.get('param_grid', {})
            )
        
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'data': {
                'timeframe': self.data.timeframe
            },
            'ma': {
                'type': self.ma.type,
                'lengths': self.ma.lengths,
                'lookback_window_bars': self.ma.lookback_window_bars,
                'support_tolerance_pct': self.ma.support_tolerance_pct,
                'entry_tolerance_pct': self.ma.entry_tolerance_pct,
                'min_gap_between_touches_bars': self.ma.min_gap_between_touches_bars,
                'min_touches_for_valid_ma': self.ma.min_touches_for_valid_ma,
                'forward_return_horizons': self.ma.forward_return_horizons,
                'score_weights': self.ma.score_weights
            },
            'trend_filter': {
                'enabled': self.trend_filter.enabled,
                'trend_ma_length': self.trend_filter.trend_ma_length,
                'trend_lookback_bars': self.trend_filter.trend_lookback_bars
            },
            'entries': {
                'allow_multiple_positions': self.entries.allow_multiple_positions
            },
            'exits': {
                'exit_mode': self.exits.exit_mode,
                'stop_loss_pct': self.exits.stop_loss_pct,
                'stop_below_ma_pct': self.exits.stop_below_ma_pct,
                'take_profit_R_multiple': self.exits.take_profit_R_multiple,
                'max_holding_bars': self.exits.max_holding_bars,
                'exit_tolerance_pct': self.exits.exit_tolerance_pct
            },
            'risk': {
                'risk_per_trade_pct_of_equity': self.risk.risk_per_trade_pct_of_equity
            },
            'costs': {
                'commission_bps': self.costs.commission_bps,
                'slippage_bps': self.costs.slippage_bps
            },
            'walk_forward': {
                'enabled': self.walk_forward.enabled,
                'train_period_bars': self.walk_forward.train_period_bars,
                'test_period_bars': self.walk_forward.test_period_bars,
                'step_bars': self.walk_forward.step_bars,
                'continuous_equity': self.walk_forward.continuous_equity,
                'optimization_objective': self.walk_forward.optimization_objective,
                'param_grid': self.walk_forward.param_grid
            }
        }


