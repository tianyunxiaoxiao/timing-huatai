"""
华泰 10 因子技术打分择时系统 - 全链路端到端一键执行入口
严格对齐《华泰证券-金工深度研究：A股择时之技术打分体系（2025-12-26）》
"""
import time, os, sys, psutil, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from config import HuataiTimingConfig, TEN_INDICATORS, SIX_INDICATORS, BROAD_INDICES
from data_loader import HuataiDataLoader
from technical_factors import HuataiTechnicalEngine
from scoring_engine import HuataiScoringEngine
from backtester import HuataiBacktester
from reporter import HuataiReporter

def main():
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / (1024 * 1024)
    total_t0 = time.time()

    print("================================================================================")
    print("      HUATAI 10-FACTOR TECHNICAL SCORING TIMING SYSTEM (REPRODUCTION)")
    print("================================================================================")

    # 1. 初始化配置与数据载入
    t0 = time.time()
    config = HuataiTimingConfig()
    loader = HuataiDataLoader(config)
    loader.load_cache()
    df_market = loader.get_index_market_data(config.benchmark_id)
    t_data = time.time() - t0
    print(f"[1/5] Benchmark {config.benchmark_id} loaded: {len(df_market)} bars in {t_data:.3f}s")

    # 2. 计算 10 大核心技术指标
    t0 = time.time()
    factor_engine = HuataiTechnicalEngine()
    raw_factors, sig_factors = factor_engine.compute_10_factors(df_market)
    t_factors = time.time() - t0
    print(f"[2/5] 10 Technical Indicators computed in {t_factors:.3f}s")

    # 3. 运行 10 个单指标择时回测 (图表 10 复现)
    t0 = time.time()
    backtester = HuataiBacktester(config)
    single_rows = []
    for code, meta in TEN_INDICATORS.items():
        res_s = backtester.run(sig_factors[code], df_market)
        m = res_s["metrics"]
        single_rows.append({
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
    t_single = time.time() - t0
    print(f"[3/5] 10 Single Indicators backtested in {t_single:.3f}s (Table 10 done)")

    # 4. 综合打分与信号 1 / 信号 2 回测 (图表 45 复现)
    t0 = time.time()
    sc1, s1, sc2, s2 = HuataiScoringEngine.compute_scores_and_signals(sig_factors)
    res_sig1 = backtester.run(s1, df_market)
    res_sig2 = backtester.run(s2, df_market)

    # 11 大宽基指数横向泛化回测 (图表 41/44 复现)
    broad_rows = []
    for code in BROAD_INDICES:
        df_sub = loader.get_index_market_data(code)
        _, sig_sub = factor_engine.compute_10_factors(df_sub)
        _, s1_sub, _, _ = HuataiScoringEngine.compute_scores_and_signals(sig_sub)
        res_b = backtester.run(s1_sub, df_sub)
        mb = res_b["metrics"]
        broad_rows.append({
            "code": code,
            "metrics": mb,
            "excess": mb["cagr"] - mb["benchmark_cagr"]
        })
    t_comp = time.time() - t0
    print(f"[4/5] Signal 1 & 2 + 11 Broad Indices backtested in {t_comp:.3f}s (Table 41/45 done)")

    # 5. 产物与报告生成
    t0 = time.time()
    run_dir = config.artifacts_dir / "run_latest"
    reporter = HuataiReporter(run_dir)
    charts = reporter.generate_all_charts(single_rows, res_sig1, res_sig2, broad_rows, sc1, df_market)
    report_file = reporter.generate_report(single_rows, res_sig1["metrics"], res_sig2["metrics"], broad_rows)

    # 保存机器底层数据
    sig_factors.to_parquet(run_dir / "technical_10_signals.parquet")
    res_sig1["records"].to_parquet(run_dir / "daily_records_signal1.parquet")
    res_sig2["records"].to_parquet(run_dir / "daily_records_signal2.parquet")

    t_report = time.time() - t0
    print(f"[5/5] 4 High-Res Charts and Markdown Report generated in {t_report:.3f}s")

    total_time = time.time() - total_t0
    mem_end = process.memory_info().rss / (1024 * 1024)
    print("================================================================================")
    print(f"HUATAI 10-FACTOR SYSTEM COMPLETE! Total Time: {total_time:.3f}s | Peak Mem: {mem_end:.2f} MB")
    print(f"Report: {report_file}")
    print("================================================================================")

if __name__ == "__main__":
    main()
