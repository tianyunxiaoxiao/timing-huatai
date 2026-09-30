"""
华泰 10 因子技术打分择时系统 - 回测引擎 (Huatai Backtester)
严格对齐研报第 7 页回测框架:
  1. 日频收盘价调仓: T 日收盘信号, 使用 T+1 日收盘价调仓
  2. 信号规则: 多空双边交易, +1做多, -1做空, 0中性
  3. 费用设置: 双边 0.05% 费率, 扣费后真实净值结算
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

try:
    from .config import HuataiTimingConfig
    from .metrics import HuataiMetricsCalculator
except ImportError:
    from config import HuataiTimingConfig
    from metrics import HuataiMetricsCalculator

class HuataiBacktester:
    """华泰择时回测引擎"""

    def __init__(self, config: Optional[HuataiTimingConfig] = None):
        self.config = config or HuataiTimingConfig()

    def run(
        self,
        signals: pd.Series,
        df_market: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        输入目标信号序列与行情宽表，执行严格的次日撮合回测
        """
        df = df_market.copy().sort_values("trade_date").reset_index(drop=True)
        dates = df["trade_date"].values
        prices = df["close"].values
        returns = df["pct_change"].fillna(0.0).values
        n = len(df)

        target_sig = signals.reindex(df.index).fillna(0.0).values

        actual_w = np.zeros(n, dtype=float)
        turnover = np.zeros(n, dtype=float)
        costs = np.zeros(n, dtype=float)
        net_returns = np.zeros(n, dtype=float)
        portfolio_equity = np.ones(n, dtype=float)
        benchmark_equity = np.ones(n, dtype=float)

        fee_rate = self.config.fee_rate
        curr_holding = 0.0

        for t in range(1, n):
            # T-1 日发信号，T 日收盘前以该目标调仓执行
            desire_w = target_sig[t - 1]
            dw = abs(desire_w - curr_holding)
            cost = dw * fee_rate
            curr_holding = desire_w

            actual_w[t] = curr_holding
            turnover[t] = dw
            costs[t] = cost

            # T 日持仓收益扣除手续费
            r_bench = returns[t]
            r_net = curr_holding * r_bench - cost
            net_returns[t] = r_net

            portfolio_equity[t] = portfolio_equity[t - 1] * (1.0 + r_net)
            benchmark_equity[t] = benchmark_equity[t - 1] * (1.0 + r_bench)

        records = pd.DataFrame({
            "trade_date": dates,
            "close": prices,
            "benchmark_return": returns,
            "target_signal": target_sig,
            "actual_weight": actual_w,
            "turnover": turnover,
            "cost": costs,
            "net_return": net_returns,
            "portfolio_equity": portfolio_equity,
            "benchmark_equity": benchmark_equity
        })
        records["drawdown"] = (portfolio_equity - np.maximum.accumulate(portfolio_equity)) / np.maximum.accumulate(portfolio_equity)

        # 全量统计指标
        metrics = HuataiMetricsCalculator.calculate_full_performance(records, self.config.risk_free_rate)

        return {
            "records": records,
            "metrics": metrics
        }
