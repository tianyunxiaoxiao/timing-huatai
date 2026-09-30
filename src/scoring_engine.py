"""
华泰 10 因子技术打分择时系统 - 综合技术打分与双版本信号生成器 (Scoring Engine)
实现:
  1. 信号 1 (全量 10 因子): 等权均值打分, 阈值 +-0.33 转换为多/平/空
  2. 信号 2 (精简 6 因子): 剔除量价, 等权均值打分, 阈值 0 转换为多/空
"""
from typing import Dict, Tuple
import pandas as pd
import numpy as np

try:
    from .config import TEN_INDICATORS, SIX_INDICATORS
except ImportError:
    from config import TEN_INDICATORS, SIX_INDICATORS

class HuataiScoringEngine:
    """华泰技术打分引擎"""

    @staticmethod
    def compute_scores_and_signals(sig_df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        输入 10 因子信号矩阵，输出:
          1. score_1: 信号 1 连续得分 in [-1, +1]
          2. signal_1: 信号 1 离散持仓 {-1, 0, 1}
          3. score_2: 信号 2 连续得分 in [-1, +1]
          4. signal_2: 信号 2 离散持仓 {-1, 0, 1}
        """
        ten_cols = list(TEN_INDICATORS.keys())
        six_cols = SIX_INDICATORS

        # 1. 信号 1: 10 因子等权均值 (自适应跳过期权未上市前 NaN)
        score_1 = sig_df[ten_cols].mean(axis=1, skipna=True).clip(-1.0, 1.0)
        # 阈值 +-0.33 规则
        signal_1 = np.where(score_1 > 0.33, 1.0, np.where(score_1 < -0.33, -1.0, 0.0))
        signal_1_series = pd.Series(signal_1, index=sig_df.index)

        # 2. 信号 2: 剔除量价, 6 因子等权均值
        score_2 = sig_df[six_cols].mean(axis=1, skipna=True).clip(-1.0, 1.0)
        # 阈值 0 规则
        signal_2 = np.where(score_2 > 1e-6, 1.0, np.where(score_2 < -1e-6, -1.0, 0.0))
        signal_2_series = pd.Series(signal_2, index=sig_df.index)

        return score_1, signal_1_series, score_2, signal_2_series
