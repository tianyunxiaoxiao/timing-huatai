"""
华泰 10 因子技术打分择时系统 - 绩效指标统计模块 (Metrics)
严格实现研报图表 10 与图表 41 全套指标:
  1. 年化收益 (CAGR)
  2. 年化波动
  3. 最大回撤
  4. 夏普比率 (无风险利率 2.0%)
  5. Calmar 比率
  6. 持仓天数均值 (Mean Holding Days)
  7. 持仓天数中位数 (Median Holding Days)
  8. 持仓胜率 (Holding Win Rate)
  9. 持仓赔率 (Odds Ratio)
  10. 分年度收益 (Yearly Returns)
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class HuataiMetricsCalculator:
    """华泰量化指标计算器"""

    @staticmethod
    def calculate_trade_segments(signals: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """
        按同向持仓段 (Holding Segments) 统计持仓天数均值、中位数、胜率与赔率 (对齐图表10)
        """
        sig = signals.fillna(0.0).values
        ret = returns.fillna(0.0).values
        n = len(sig)

        segments = []
        curr_sig = 0.0
        curr_len = 0
        curr_cum_ret = 1.0

        for t in range(n):
            st = sig[t]
            rt = ret[t]

            if st != curr_sig:
                # 结算上一个段
                if curr_sig != 0.0 and curr_len > 0:
                    segments.append({
                        "direction": curr_sig,
                        "days": curr_len,
                        "total_return": curr_cum_ret - 1.0
                    })
                # 开启新段
                curr_sig = st
                curr_len = 1 if st != 0.0 else 0
                curr_cum_ret = (1.0 + curr_sig * rt) if st != 0.0 else 1.0
            else:
                if curr_sig != 0.0:
                    curr_len += 1
                    curr_cum_ret *= (1.0 + curr_sig * rt)

        # 结算最后一段
        if curr_sig != 0.0 and curr_len > 0:
            segments.append({
                "direction": curr_sig,
                "days": curr_len,
                "total_return": curr_cum_ret - 1.0
            })

        if not segments:
            return {
                "mean_holding_days": 0.0,
                "median_holding_days": 0.0,
                "holding_win_rate": 0.0,
                "holding_odds_ratio": 0.0,
                "total_trades": 0
            }

        df_seg = pd.DataFrame(segments)
        mean_days = df_seg["days"].mean()
        median_days = df_seg["days"].median()

        wins = df_seg[df_seg["total_return"] > 0]
        losses = df_seg[df_seg["total_return"] < 0]

        win_rate = len(wins) / len(df_seg)
        avg_win = wins["total_return"].mean() if not wins.empty else 0.0
        avg_loss = abs(losses["total_return"].mean()) if not losses.empty else 1e-4
        odds = avg_win / max(avg_loss, 1e-6)

        return {
            "mean_holding_days": float(mean_days),
            "median_holding_days": float(median_days),
            "holding_win_rate": float(win_rate),
            "holding_odds_ratio": float(odds),
            "total_trades": len(df_seg)
        }

    @staticmethod
    def calculate_full_performance(
        daily_records: pd.DataFrame,
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """计算全套标准绩效指标"""
        df = daily_records.copy()
        net_ret = df["net_return"].values
        bench_ret = df["benchmark_return"].values
        signals = df["actual_weight"]

        n_days = len(df)
        years = n_days / 252.0

        cagr = (df["portfolio_equity"].iloc[-1]) ** (1.0 / max(years, 0.1)) - 1.0
        bench_cagr = (df["benchmark_equity"].iloc[-1]) ** (1.0 / max(years, 0.1)) - 1.0

        ann_vol = np.std(net_ret) * np.sqrt(252)
        bench_vol = np.std(bench_ret) * np.sqrt(252)

        sharpe = (cagr - risk_free_rate) / max(ann_vol, 1e-4)
        bench_sharpe = (bench_cagr - risk_free_rate) / max(bench_vol, 1e-4)

        max_dd = df["drawdown"].min()
        calmar = cagr / max(abs(max_dd), 1e-4)

        # 持仓段统计 (对齐图表10)
        trade_stats = HuataiMetricsCalculator.calculate_trade_segments(signals, df["benchmark_return"])

        # 分年度收益 (对齐图表44)
        df["year"] = pd.to_datetime(df["trade_date"]).dt.year
        yearly_p = df.groupby("year").apply(
            lambda x: (x["portfolio_equity"].iloc[-1] / x["portfolio_equity"].iloc[0] - 1.0),
            include_groups=False
        ).to_dict()

        yearly_b = df.groupby("year").apply(
            lambda x: (x["benchmark_equity"].iloc[-1] / x["benchmark_equity"].iloc[0] - 1.0),
            include_groups=False
        ).to_dict()

        return {
            "cagr": float(cagr),
            "annual_volatility": float(ann_vol),
            "max_drawdown": float(max_dd),
            "sharpe_ratio": float(sharpe),
            "calmar_ratio": float(calmar),
            "mean_holding_days": trade_stats["mean_holding_days"],
            "median_holding_days": trade_stats["median_holding_days"],
            "holding_win_rate": trade_stats["holding_win_rate"],
            "holding_odds_ratio": trade_stats["holding_odds_ratio"],
            "total_trades": trade_stats["total_trades"],
            "benchmark_cagr": float(bench_cagr),
            "benchmark_vol": float(bench_vol),
            "benchmark_sharpe": float(bench_sharpe),
            "yearly_returns": yearly_p,
            "benchmark_yearly_returns": yearly_b
        }
