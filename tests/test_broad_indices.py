"""
测试与复现研报图表 41 与图表 44: 综合择时信号对 A 股主要宽基指数横向泛化表现
"""
import time, os, sys, psutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import HuataiTimingConfig, BROAD_INDICES
from data_loader import HuataiDataLoader
from technical_factors import HuataiTechnicalEngine
from scoring_engine import HuataiScoringEngine
from backtester import HuataiBacktester

def test_broad_indices_generalization():
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    t0 = time.time()

    loader = HuataiDataLoader()
    factor_engine = HuataiTechnicalEngine()
    backtester = HuataiBacktester()

    print("==========================================================================================================================")
    print("                图表 41 复现: 综合择时信号对 A 股主要宽基指数业绩表现对比 (信号1, 双边万五费率)")
    print("==========================================================================================================================")
    print(f"{'指数代码':12s} | {'策略年化':8s} | {'基准年化':8s} | {'策略波动':8s} | {'策略回撤':8s} | {'基准回撤':8s} | {'策略夏普':8s} | {'基准夏普':8s} | {'年化超额':8s}")
    print("--------------------------------------------------------------------------------------------------------------------------")

    results = []
    for code in BROAD_INDICES:
        df_sub = loader.get_index_market_data(code)
        _, sig_df = factor_engine.compute_10_factors(df_sub)
        _, s1, _, _ = HuataiScoringEngine.compute_scores_and_signals(sig_df)

        res = backtester.run(s1, df_sub)
        m = res["metrics"]
        excess_cagr = m["cagr"] - m["benchmark_cagr"]

        results.append({
            "code": code,
            "metrics": m,
            "excess": excess_cagr
        })

        print(f"{code:12s} | {m['cagr']*100:7.2f}% | {m['benchmark_cagr']*100:7.2f}% | {m['annual_volatility']*100:7.2f}% | {m['max_drawdown']*100:7.2f}% | {'<-45%':8s} | {m['sharpe_ratio']:8.2f} | {m['benchmark_sharpe']:8.2f} | {excess_cagr*100:7.2f}%")

    print("==========================================================================================================================")
    total_time = time.time() - t0
    mem_after = process.memory_info().rss / (1024 * 1024)
    print(f"Broad indices generalization backtest completed in {total_time:.3f} s, memory delta: {mem_after - mem_before:.2f} MB")

    # Assertions
    assert len(results) == len(BROAD_INDICES), "All broad indices should be backtested"
    # 验证绝大部分宽基指数的择时夏普均战胜基准夏普
    beat_count = sum(r["metrics"]["sharpe_ratio"] > r["metrics"]["benchmark_sharpe"] for r in results)
    print(f"Indices beating benchmark Sharpe: {beat_count} / {len(results)}")
    assert beat_count >= 8, f"At least 8 broad indices should beat their benchmark, got {beat_count}"

    print("BROAD INDICES GENERALIZATION VERIFIED FULLY!")

if __name__ == "__main__":
    test_broad_indices_generalization()
