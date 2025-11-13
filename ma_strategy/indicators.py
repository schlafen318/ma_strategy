"""
Indicator computation engine for moving averages.
"""

import pandas as pd
import numpy as np
from typing import List, Dict


class IndicatorEngine:
    """Compute technical indicators, primarily moving averages"""
    
    @staticmethod
    def compute_mas(
        df: pd.DataFrame,
        ma_lengths: List[int],
        ma_type: str = "SMA"
    ) -> pd.DataFrame:
        """
        Compute multiple moving averages.
        
        Args:
            df: DataFrame with 'close' column
            ma_lengths: List of MA periods (e.g., [10, 20, 50])
            ma_type: "SMA" or "EMA"
            
        Returns:
            DataFrame with added MA columns: ma_10, ma_20, etc.
        """
        df = df.copy()
        close = df['close']
        
        for length in ma_lengths:
            col_name = f'ma_{length}'
            if ma_type == "SMA":
                df[col_name] = close.rolling(window=length, min_periods=1).mean()
            elif ma_type == "EMA":
                df[col_name] = close.ewm(span=length, adjust=False).mean()
            else:
                raise ValueError(f"Unsupported MA type: {ma_type}")
        
        return df
    
    @staticmethod
    def get_ma_value(
        df: pd.DataFrame,
        bar_index: int,
        ma_length: int
    ) -> float:
        """
        Get MA value at specific bar index.
        
        Args:
            df: DataFrame with MA columns
            bar_index: Row index
            ma_length: MA period
            
        Returns:
            MA value or NaN if not available
        """
        col_name = f'ma_{ma_length}'
        if col_name not in df.columns:
            return np.nan
        return df.loc[bar_index, col_name]
    
    @staticmethod
    def compute_long_term_ma(
        df: pd.DataFrame,
        length: int,
        ma_type: str = "SMA"
    ) -> pd.Series:
        """
        Compute a single long-term MA (e.g., for trend filter).
        
        Args:
            df: DataFrame with 'close' column
            length: MA period
            ma_type: "SMA" or "EMA"
            
        Returns:
            Series with MA values
        """
        close = df['close']
        if ma_type == "SMA":
            return close.rolling(window=length, min_periods=1).mean()
        elif ma_type == "EMA":
            return close.ewm(span=length, adjust=False).mean()
        else:
            raise ValueError(f"Unsupported MA type: {ma_type}")


