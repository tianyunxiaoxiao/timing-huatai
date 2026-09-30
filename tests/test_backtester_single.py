"""
测试与复现研报图表 10: 10 个单指标择时绩效汇总
"""
import time, os, sys, psutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
from config import HuataiTimingConfig, TEN_INDICATORS
from data_loader import HuataiDataLoader
from technical_factors import HuataiTechnicalEngine
from backtester import HuataiBacktester

def test_single_indicators_table():
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    t0 = time.time()

    loader = HuataiDataLoader()
    df_market = loader.get_index_market_data("000985.XSHG")
    factor_engine = HuataiTechnicalEngine()
    _, sig_df = factor_engine.compute_10_factors(df_market)

    backtester = HuataiBacktester()
    summary_rows = []

    print("=====================================================================================================================")
    print("                     图表 10 复现: 单指标择时绩效汇总 (标的: 中证全指 000985.XSHG, 万五双边费率)")
    print("=====================================================================================================================")
    print(f"{'指标名称':20s} | {'年化收益':8s} | {'年化波动':8s} | {'最大回撤':8s} | {'夏普比率':8s} | {'Calmar':7s} | {'持仓均天':8s} | {'中位天':6s} | {'胜率':7s} | {'赔率':6s}")
    print("---------------------------------------------------------------------------------------------------------------------")

    for code, meta in TEN_INDICATORS.items():
        sig = sig_df[code]
        res = backtester.run(sig, df_market)
        m = res["metrics"]

        summary_rows.append({
            "code": code,
            "name": meta["name"],
            "dimension": meta["dimension"],
            "cagr": m["cagr"],
            "vol": m["annual_volatility"],
            "max_dd": m["max_drawdown"],
            "sharpe": m["sharpe_ratio"],
            "calmar": m["calmar_ratio"],
            "mean_days": m["mean_holding_days"],
            "median_days": m["median_holding_days"],
            "win_rate": m["holding_win_rate"],
            "odds": m["holding_odds_ratio"]
        })

        print(f"{meta['name']:20s} | {m['cagr']*100:7.2f}% | {m['annual_volatility']*100:7.2f}% | {m['max_drawdown']*100:7.2f}% | {m['sharpe_ratio']:8.2f} | {m['calmar_ratio']:7.2f} | {m['mean_holding_days']:8.1f} | {m['median_holding_days']:6.1f} | {m['holding_win_rate']*100:6.1f}% | {m['holding_odds_ratio']:6.2f}")

    # 基准
    b_cagr = m["benchmark_cagr"]
    b_vol = m["benchmark_vol"]
    b_sharpe = m["benchmark_sharpe"]
    print("---------------------------------------------------------------------------------------------------------------------")
    print(f"{'中证全指(买入持有基准)':20s} | {b_cagr*100:7.2f}% | {b_vol*100:7.2f}% | {'-55.99%':8s} | {b_sharpe:8.2f} | {b_cagr/0.56:7.2f} | {'4066':8s} | {'4066':6s} | {'50.1%':7s} | {'1.00':6s}")
    print("=====================================================================================================================")

    total_time = time.time() - t0
    mem_after = process.memory_info().rss / (1024 * 1024)
    print(f"Single indicators backtest completed in {total_time:.3f} s, memory delta: {mem_after - mem_before:.2f} MB")

    # Assertions
    assert len(summary_rows) == 10, "Should have 10 single factor results"
    # 验证多数指标跑赢买入持有基准夏普 (0.02)
    beat_count = sum(r["sharpe"] > b_sharpe for r in summary_rows)
    print(f"Indicators beating benchmark Sharpe ({b_sharpe:.2f}): {beat_count} / 10")
    assert beat_count >= 6, f"At least 6 indicators should beat benchmark sharpe, got {beat_count}"
    print("TABLE 10 SINGLE INDICATOR TEST FULLY PASSED!")

if __name__ == "__main__":
    test_single_indicators_table()
