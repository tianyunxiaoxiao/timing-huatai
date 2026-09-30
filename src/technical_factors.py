"""
华泰 10 因子技术打分择时系统 - 10 大核心技术指标引擎 (Technical Factors Engine)
严格对齐研报图表8与图表9中 5 个维度、10 个指标的公式与买卖信号规则。
"""
from typing import Dict, Tuple
import pandas as pd
import numpy as np

def compute_adx(df: pd.DataFrame, n: int = 20) -> Tuple[pd.Series, pd.Series]:
    """计算 20 日 ADX 趋向指标及方向"""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr_smooth = pd.Series(tr).rolling(n, min_periods=n).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(n, min_periods=n).mean() / (tr_smooth + 1e-8)
    minus_di = 100 * pd.Series(minus_dm).rolling(n, min_periods=n).mean() / (tr_smooth + 1e-8)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8)
    adx = dx.rolling(n, min_periods=n).mean().fillna(0.0)
    direction = np.where(plus_di > minus_di, 1.0, -1.0)
    return adx, pd.Series(direction, index=df.index)

def apply_bollinger_rule(
    series: pd.Series,
    window: int = 20,
    k: float = 1.5,
    reverse: bool = False,
    long_only: bool = False
) -> pd.Series:
    """通道状态维持突破规则"""
    ma = series.rolling(window, min_periods=max(5, window // 4)).mean()
    std = series.rolling(window, min_periods=max(5, window // 4)).std()
    upper = (ma + k * std).values
    lower = (ma - k * std).values
    vals = series.values
    n = len(series)

    sig = np.zeros(n, dtype=float)
    curr = 0.0

    for i in range(n):
        v = vals[i]
        up = upper[i]
        dn = lower[i]

        if np.isnan(v) or np.isnan(up) or np.isnan(dn):
            sig[i] = curr
            continue

        if not reverse:
            # 正向趋势
            if v > up:
                curr = 1.0
            elif v < dn:
                curr = 0.0 if long_only else -1.0
        else:
            # 均值反转: 跌破下轨抄底(+1), 突破上轨过热防守(-1)
            if v < dn:
                curr = 1.0
            elif v > up:
                curr = 0.0 if long_only else -1.0

        sig[i] = curr

    return pd.Series(sig, index=series.index)

def apply_momentum_rule(
    series: pd.Series,
    fast_w: int = 5,
    slow_w: int = 20,
    long_only: bool = False
) -> pd.Series:
    """动量趋势维持规则"""
    fast = series.rolling(fast_w, min_periods=1).mean()
    slow = series.rolling(slow_w, min_periods=max(3, slow_w // 4)).mean()
    diff = (fast - slow).values
    n = len(series)

    sig = np.zeros(n, dtype=float)
    curr = 0.0

    for i in range(n):
        d = diff[i]
        if np.isnan(d):
            sig[i] = curr
            continue
        if d > 0:
            curr = 1.0
        elif d < 0:
            curr = 0.0 if long_only else -1.0
        sig[i] = curr

    return pd.Series(sig, index=series.index)

class HuataiTechnicalEngine:
    """华泰 10 大核心技术指标引擎"""

    def compute_10_factors(self, df_market: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        计算 10 个精选因子的原始值与离散买卖信号 (取值 {-1, 0, 1} 或 NaN)
        """
        df = df_market.copy().sort_values("trade_date").reset_index(drop=True)
        raw = pd.DataFrame(index=df.index)
        sig = pd.DataFrame(index=df.index)
        raw["trade_date"] = df["trade_date"]
        sig["trade_date"] = df["trade_date"]

        close = df["close"]
        to = df["turnover_rate"]

        # =========================================================================
        # 1. 价格维度 (2个)
        # =========================================================================
        # 1.1 20日价格乖离率 (动量)
        ma20_close = close.rolling(20, min_periods=5).mean()
        raw["bias_price_20"] = (close - ma20_close) / ma20_close * 100.0
        sig["bias_price_20"] = apply_momentum_rule(raw["bias_price_20"], fast_w=5, slow_w=20)

        # 1.2 20日布林带 (布林带)
        raw["boll_price_20"] = close
        sig["boll_price_20"] = apply_bollinger_rule(close, window=20, k=2.0)

        # =========================================================================
        # 2. 量能维度 (2个)
        # =========================================================================
        # 2.1 20日换手率乖离率 (布林带)
        ma20_to = to.rolling(20, min_periods=5).mean()
        raw["bias_turnover_20"] = (to - ma20_to) / (ma20_to + 1e-8)
        sig["bias_turnover_20"] = apply_bollinger_rule(raw["bias_turnover_20"], window=20, k=1.0)

        # 2.2 60日换手率乖离率 (布林带)
        ma60_to = to.rolling(60, min_periods=10).mean()
        raw["bias_turnover_60"] = (to - ma60_to) / (ma60_to + 1e-8)
        sig["bias_turnover_60"] = apply_bollinger_rule(raw["bias_turnover_60"], window=20, k=1.0)

        # =========================================================================
        # 3. 趋势维度 (2个)
        # =========================================================================
        # 3.1 20日 ADX (均线)
        adx_val, adx_dir = compute_adx(df, n=20)
        raw["adx_20"] = adx_val
        adx_ma = adx_val.rolling(10, min_periods=3).mean()
        sig["adx_20"] = np.where(adx_val > adx_ma, adx_dir, 0.0)

        # 3.2 20日创新高天数占比 (布林带-仅做多)
        roll_max_20 = close.rolling(20, min_periods=1).max()
        is_high = (close >= roll_max_20 - 1e-4).astype(float)
        raw["high_ratio_20"] = is_high.rolling(20, min_periods=1).mean()
        sig["high_ratio_20"] = apply_bollinger_rule(raw["high_ratio_20"], window=20, k=1.0, long_only=True)

        # =========================================================================
        # 4. 波动维度 (2个)
        # =========================================================================
        # 4.1 60日换手率波动 (布林带-仅做多)
        raw["turnover_vol_60"] = to.rolling(60, min_periods=20).std()
        sig["turnover_vol_60"] = apply_bollinger_rule(raw["turnover_vol_60"], window=20, k=1.2, long_only=True)

        # 4.2 50ETF 期权隐含波动率 (布林带反转)
        valid_opt = df["opt50_iv"].notna()
        raw["opt50_iv"] = df["opt50_iv"].fillna(0.20)
        sig["opt50_iv"] = np.where(valid_opt, apply_bollinger_rule(raw["opt50_iv"], window=20, k=1.2), np.nan)

        # =========================================================================
        # 5. 拥挤维度 (2个)
        # =========================================================================
        # 5.1 成分股涨停家数占比 5日均值 (动量)
        raw["limit_up_ratio_5"] = df["limit_up_ratio_proxy"].rolling(5, min_periods=1).mean()
        sig["limit_up_ratio_5"] = apply_momentum_rule(raw["limit_up_ratio_5"], fast_w=5, slow_w=20)

        # 5.2 50ETF 期权持仓量 PCR 5日均值 (反向布林带)
        pcr_oi = df["opt50_OI_PCR"].fillna(1.0)
        raw["opt50_oi_pcr_ma5"] = pcr_oi.rolling(5, min_periods=1).mean()
        sig["opt50_oi_pcr_ma5"] = np.where(valid_opt, apply_bollinger_rule(raw["opt50_oi_pcr_ma5"], window=20, k=1.2, reverse=True), np.nan)

        return raw, sig
