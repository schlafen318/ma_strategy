"""
Data loader for OHLCV price data.
"""

import pandas as pd
from typing import Optional, Union
import numpy as np
import os


class DataLoader:
    """Load and validate OHLCV price data"""
    
    REQUIRED_COLUMNS = ['date', 'open', 'high', 'low', 'close']
    OPTIONAL_COLUMNS = ['volume']
    
    @staticmethod
    def get_price_data(
        data: Union[str, pd.DataFrame],
        symbol: Optional[str] = None,
        from_alpha_vantage: bool = False,
        timeframe: str = 'daily',
        api_key: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load price data from file path, DataFrame, or Alpha Vantage API.
        
        Args:
            data: File path (CSV), pandas DataFrame, or symbol string if from_alpha_vantage=True
            symbol: Optional symbol identifier (required if from_alpha_vantage=True)
            from_alpha_vantage: If True, fetch data from Alpha Vantage API
            timeframe: For Alpha Vantage: 'daily', 'weekly', or 'monthly'
            api_key: Alpha Vantage API key (or use ALPHA_VANTAGE_API_KEY env var)
            
        Returns:
            DataFrame with required columns and validated data
        """
        if from_alpha_vantage:
            if not symbol and isinstance(data, str):
                symbol = data
            if not symbol:
                raise ValueError("Symbol required when fetching from Alpha Vantage")
            
            from ma_strategy.alpha_vantage_loader import AlphaVantageLoader
            loader = AlphaVantageLoader(api_key=api_key)
            df = loader.get_data(symbol=symbol, timeframe=timeframe)
        elif isinstance(data, str):
            # Assume it's a file path
            df = pd.read_csv(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Validate and clean
        df = DataLoader._validate_and_clean(df)
        
        if symbol:
            df['symbol'] = symbol
        
        return df
    
    @staticmethod
    def _validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean price data.
        
        Ensures:
        - Required columns exist
        - No duplicates
        - Chronologically sorted
        - No missing values in OHLC
        - Valid price relationships (high >= low, etc.)
        """
        # Check required columns
        missing = [col for col in DataLoader.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Ensure date column exists and is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            if 'date' not in df.columns:
                df['date'] = df.index
        else:
            raise ValueError("No date column or datetime index found")
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['date']).copy()
        
        # Sort chronologically
        df = df.sort_values('date').reset_index(drop=True)
        
        # Validate price data
        for col in ['open', 'high', 'low', 'close']:
            if df[col].isna().any():
                raise ValueError(f"Missing values in {col} column")
            if (df[col] <= 0).any():
                raise ValueError(f"Non-positive values in {col} column")
        
        # Validate price relationships
        invalid = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )
        if invalid.any():
            invalid_count = invalid.sum()
            raise ValueError(
                f"Invalid price relationships in {invalid_count} rows. "
                "High must be >= Low, Open, Close. Low must be <= Open, Close."
            )
        
        return df
    
    @staticmethod
    def resample_timeframe(
        df: pd.DataFrame,
        target_timeframe: str
    ) -> pd.DataFrame:
        """
        Resample daily data to weekly or monthly.
        
        Args:
            df: Daily OHLCV DataFrame
            target_timeframe: 'weekly' or 'monthly'
            
        Returns:
            Resampled DataFrame
        """
        if target_timeframe == 'daily':
            return df
        
        df = df.set_index('date')
        
        if target_timeframe == 'weekly':
            resampled = df.resample('W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum' if 'volume' in df.columns else 'sum'
            })
        elif target_timeframe == 'monthly':
            resampled = df.resample('M').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum' if 'volume' in df.columns else 'sum'
            })
        else:
            raise ValueError(f"Unsupported timeframe: {target_timeframe}")
        
        resampled = resampled.reset_index()
        resampled = resampled.dropna(subset=['open', 'high', 'low', 'close'])
        
        return resampled


