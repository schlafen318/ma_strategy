"""
Alpha Vantage API data loader for fetching stock price data.
"""

import pandas as pd
import numpy as np
from typing import Optional
import os
import time
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
from ma_strategy.data_loader import DataLoader


class AlphaVantageLoader:
    """Load price data from Alpha Vantage API"""
    
    # API call limits (free tier: 5 calls/min, 500 calls/day)
    CALL_DELAY_SECONDS = 12  # Wait 12 seconds between calls to stay under limit
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage loader.
        
        Args:
            api_key: Alpha Vantage API key. If None, reads from ALPHA_VANTAGE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Alpha Vantage API key required. "
                "Set ALPHA_VANTAGE_API_KEY environment variable or pass api_key parameter."
            )
        
        self.ts = TimeSeries(key=self.api_key, output_format='pandas')
        self.last_call_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.CALL_DELAY_SECONDS:
            sleep_time = self.CALL_DELAY_SECONDS - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def get_daily_data(
        self,
        symbol: str,
        outputsize: str = 'full',
        adjusted: bool = False
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'SPY')
            outputsize: 'compact' (last 100 data points) or 'full' (up to 20 years)
            adjusted: If True, returns adjusted prices (default: True)
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        self._rate_limit()
        
        try:
            if adjusted:
                try:
                    data, meta_data = self.ts.get_daily_adjusted(symbol=symbol, outputsize=outputsize)
                except ValueError as e:
                    if "premium" in str(e).lower():
                        # Fallback to non-adjusted if premium endpoint not available
                        print(f"  Note: Adjusted prices not available (premium endpoint). Using non-adjusted prices.")
                        adjusted = False
                        data, meta_data = self.ts.get_daily(symbol=symbol, outputsize=outputsize)
                    else:
                        raise
                # Alpha Vantage returns adjusted close as '5. adjusted close'
                # We'll use adjusted close for close, and adjust OHLC proportionally
                if '5. adjusted close' in data.columns:
                    adj_close = data['5. adjusted close']
                    close = data['4. close']
                    adj_factor = adj_close / close
                    
                    # Create DataFrame with date as index first, then reset
                    df = pd.DataFrame({
                        'open': data['1. open'] * adj_factor,
                        'high': data['2. high'] * adj_factor,
                        'low': data['3. low'] * adj_factor,
                        'close': adj_close,
                        'volume': data['6. volume']
                    }, index=data.index)
                else:
                    # Fallback if adjusted close not available
                    df = pd.DataFrame({
                        'open': data['1. open'],
                        'high': data['2. high'],
                        'low': data['3. low'],
                        'close': data['4. close'],
                        'volume': data['5. volume'] if '5. volume' in data.columns else data.get('6. volume', 0)
                    }, index=data.index)
            else:
                data, meta_data = self.ts.get_daily(symbol=symbol, outputsize=outputsize)
                df = pd.DataFrame({
                    'open': data['1. open'],
                    'high': data['2. high'],
                    'low': data['3. low'],
                    'close': data['4. close'],
                    'volume': data['5. volume']
                }, index=data.index)
            
            # Reset index to get date as column
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            else:
                df = df.reset_index()
                if len(df.columns) > 0:
                    df.rename(columns={df.columns[0]: 'date'}, inplace=True)
                else:
                    raise ValueError("Could not determine date column from Alpha Vantage data")
            
            # Ensure date is datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Sort chronologically (oldest first)
            df = df.sort_values('date').reset_index(drop=True)
            
            # Validate and clean using DataLoader
            df = DataLoader._validate_and_clean(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error fetching data for {symbol}: {str(e)}")
    
    def get_weekly_data(
        self,
        symbol: str,
        adjusted: bool = False
    ) -> pd.DataFrame:
        """
        Get weekly OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol
            adjusted: If True, returns adjusted prices
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        self._rate_limit()
        
        try:
            if adjusted:
                try:
                    data, meta_data = self.ts.get_weekly_adjusted(symbol=symbol)
                except ValueError as e:
                    if "premium" in str(e).lower():
                        print(f"  Note: Adjusted prices not available (premium endpoint). Using non-adjusted prices.")
                        adjusted = False
                        data, meta_data = self.ts.get_weekly(symbol=symbol)
                    else:
                        raise
            else:
                data, meta_data = self.ts.get_weekly(symbol=symbol)
            
            # Process similar to daily
            if adjusted and '5. adjusted close' in data.columns:
                adj_close = data['5. adjusted close']
                close = data['4. close']
                adj_factor = adj_close / close
                
                df = pd.DataFrame({
                    'open': data['1. open'] * adj_factor,
                    'high': data['2. high'] * adj_factor,
                    'low': data['3. low'] * adj_factor,
                    'close': adj_close,
                    'volume': data['6. volume']
                }, index=data.index)
            else:
                df = pd.DataFrame({
                    'open': data['1. open'],
                    'high': data['2. high'],
                    'low': data['3. low'],
                    'close': data['4. close'],
                    'volume': data['5. volume'] if '5. volume' in data.columns else data.get('6. volume', 0)
                }, index=data.index)
            
            # Reset index to get date as column
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            else:
                df = df.reset_index()
                if len(df.columns) > 0:
                    df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            df = DataLoader._validate_and_clean(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error fetching weekly data for {symbol}: {str(e)}")
    
    def get_monthly_data(
        self,
        symbol: str,
        adjusted: bool = False
    ) -> pd.DataFrame:
        """
        Get monthly OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol
            adjusted: If True, returns adjusted prices
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        self._rate_limit()
        
        try:
            if adjusted:
                try:
                    data, meta_data = self.ts.get_monthly_adjusted(symbol=symbol)
                except ValueError as e:
                    if "premium" in str(e).lower():
                        print(f"  Note: Adjusted prices not available (premium endpoint). Using non-adjusted prices.")
                        adjusted = False
                        data, meta_data = self.ts.get_monthly(symbol=symbol)
                    else:
                        raise
            else:
                data, meta_data = self.ts.get_monthly(symbol=symbol)
            
            # Process similar to daily
            if adjusted and '5. adjusted close' in data.columns:
                adj_close = data['5. adjusted close']
                close = data['4. close']
                adj_factor = adj_close / close
                
                df = pd.DataFrame({
                    'open': data['1. open'] * adj_factor,
                    'high': data['2. high'] * adj_factor,
                    'low': data['3. low'] * adj_factor,
                    'close': adj_close,
                    'volume': data['6. volume']
                }, index=data.index)
            else:
                df = pd.DataFrame({
                    'open': data['1. open'],
                    'high': data['2. high'],
                    'low': data['3. low'],
                    'close': data['4. close'],
                    'volume': data['5. volume'] if '5. volume' in data.columns else data.get('6. volume', 0)
                }, index=data.index)
            
            # Reset index to get date as column
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            else:
                df = df.reset_index()
                if len(df.columns) > 0:
                    df.rename(columns={df.columns[0]: 'date'}, inplace=True)
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            df = DataLoader._validate_and_clean(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error fetching monthly data for {symbol}: {str(e)}")
    
    def get_data(
        self,
        symbol: str,
        timeframe: str = 'daily',
        outputsize: str = 'full',
        adjusted: bool = False
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol with specified timeframe.
        
        Args:
            symbol: Stock symbol
            timeframe: 'daily', 'weekly', or 'monthly'
            outputsize: For daily only: 'compact' or 'full'
            adjusted: If True, returns adjusted prices
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        timeframe = timeframe.lower()
        
        if timeframe == 'daily':
            return self.get_daily_data(symbol, outputsize=outputsize, adjusted=adjusted)
        elif timeframe == 'weekly':
            return self.get_weekly_data(symbol, adjusted=adjusted)
        elif timeframe == 'monthly':
            return self.get_monthly_data(symbol, adjusted=adjusted)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Use 'daily', 'weekly', or 'monthly'")

