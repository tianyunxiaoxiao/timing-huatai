"""
华泰 10 因子技术打分择时系统 - 数据加载器 (Data Loader)
负责加载指定宽基指数的日K量价、换手率、期权指标与微观代理数据。
支持对任意 A 股主流宽基指数生成标准宽表。
"""
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

try:
    from .config import HuataiTimingConfig, DATA_DIR
except ImportError:
    from config import HuataiTimingConfig, DATA_DIR

class HuataiDataLoader:
    """华泰择时数据加载器"""

    def __init__(self, config: Optional[HuataiTimingConfig] = None):
        self.config = config or HuataiTimingConfig()
        self.data_dir = Path(self.config.data_dir)
        self._raw_indices: Optional[pd.DataFrame] = None
        self._raw_indicators: Optional[pd.DataFrame] = None
        self._raw_options_50: Optional[pd.DataFrame] = None

    def load_cache(self) -> "HuataiDataLoader":
        """预热本地数据缓存"""
        p_index = self.data_dir / "index" / "index_daily_bars.parquet"
        if p_index.exists():
            df = pd.read_parquet(p_index)
            if "date" in df.index.names:
                df = df.reset_index()
            df["date"] = pd.to_datetime(df["date"])
            self._raw_indices = df

        p_ind = self.data_dir / "index" / "index_indicator.parquet"
        if p_ind.exists():
            df = pd.read_parquet(p_ind)
            if "trade_date" in df.index.names:
                df = df.reset_index()
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            self._raw_indicators = df

        p_opt50 = self.data_dir / "options" / "option_indicators_50ETF.parquet"
        if p_opt50.exists():
            df = pd.read_parquet(p_opt50)
            df["date"] = pd.to_datetime(df["date"])
            self._raw_options_50 = df

        return self

    def get_index_market_data(self, index_code: str = "000985.XSHG") -> pd.DataFrame:
        """
        获取指定指数从 start_date 到 end_date 的标准化量价与衍生指标宽表
        """
        if self._raw_indices is None:
            self.load_cache()

        df_idx = self._raw_indices[self._raw_indices["order_book_id"] == index_code].copy()
        if df_idx.empty:
            raise ValueError(f"Index code {index_code} not found in database!")

        df_idx = df_idx.sort_values("date").reset_index(drop=True)
        df_idx = df_idx.rename(columns={"date": "trade_date"})
        df_idx = df_idx[(df_idx["trade_date"] >= pd.to_datetime(self.config.start_date)) &
                        (df_idx["trade_date"] <= pd.to_datetime(self.config.end_date))].reset_index(drop=True)

        df_idx["pct_change"] = df_idx["close"].pct_change()

        # 换手率计算: 成交额 / 自由流通市值
        if self._raw_indicators is not None:
            ind = self._raw_indicators[self._raw_indicators["order_book_id"] == index_code].copy()
            if not ind.empty:
                ind = ind[["trade_date", "free_circulation_market_value"]].drop_duplicates("trade_date")
                df_idx = pd.merge(df_idx, ind, on="trade_date", how="left")
                df_idx["turnover_rate"] = np.where(
                    df_idx["free_circulation_market_value"] > 0,
                    df_idx["total_turnover"] / df_idx["free_circulation_market_value"],
                    0.015
                )
            else:
                df_idx["turnover_rate"] = 0.015
        else:
            df_idx["turnover_rate"] = 0.015

        # 合并 50ETF 期权持仓 PCR 与 隐含波动率 IV (近月主力月份)
        if self._raw_options_50 is not None:
            opt = self._raw_options_50.copy().rename(columns={"date": "trade_date"})
            # 主力近月去重
            opt_dedup = opt.sort_values(["trade_date", "maturity"]).groupby("trade_date").first().reset_index()
            opt_sub = opt_dedup[["trade_date", "OI_PCR", "iv_025_dela"]].copy()
            opt_sub = opt_sub.rename(columns={"OI_PCR": "opt50_OI_PCR", "iv_025_dela": "opt50_iv"})
            df_idx = pd.merge(df_idx, opt_sub, on="trade_date", how="left")
        else:
            df_idx["opt50_OI_PCR"] = np.nan
            df_idx["opt50_iv"] = np.nan

        # 涨停占比代理 (基于全市场指数收益与换手波动率)
        norm_r = (df_idx["pct_change"] - df_idx["pct_change"].rolling(60).mean()) / (df_idx["pct_change"].rolling(60).std() + 1e-8)
        norm_v = (df_idx["turnover_rate"] - df_idx["turnover_rate"].rolling(60).mean()) / (df_idx["turnover_rate"].rolling(60).std() + 1e-8)
        limit_up_proxy = 0.015 + 0.025 * np.maximum(0, norm_r) + 0.015 * np.maximum(0, norm_v)
        df_idx["limit_up_ratio_proxy"] = np.clip(limit_up_proxy, 0.001, 0.12)

        return df_idx
