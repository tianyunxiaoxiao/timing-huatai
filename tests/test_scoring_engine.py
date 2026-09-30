"""
测试华泰综合打分引擎 (HuataiScoringEngine)
"""
import time, os, sys, psutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import HuataiDataLoader
from technical_factors import HuataiTechnicalEngine
from scoring_engine import HuataiScoringEngine

def test_scoring_engine():
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    t0 = time.time()

    loader = HuataiDataLoader()
    df_market = loader.get_index_market_data("000985.XSHG")
    factor_engine = HuataiTechnicalEngine()
    _, sig_df = factor_engine.compute_10_factors(df_market)

    sc1, s1, sc2, s2 = HuataiScoringEngine.compute_scores_and_signals(sig_df)

    calc_time = time.time() - t0
    mem_after = process.memory_info().rss / (1024 * 1024)

    print("=== HuataiScoringEngine Test Results ===")
    print(f"Scoring time: {calc_time:.3f} s")
    print(f"Memory delta: {mem_after - mem_before:.2f} MB (Peak: {mem_after:.2f} MB)")

    print(f"Score 1 (10 factors) | Min: {sc1.min():.3f}, Max: {sc1.max():.3f}, Mean: {sc1.mean():.3f}")
    print(f"Signal 1 (thresh 0.33)| Longs: {(s1 == 1.0).sum()}, Neutrals: {(s1 == 0.0).sum()}, Shorts: {(s1 == -1.0).sum()}")
    print(f"Score 2 (6 factors)  | Min: {sc2.min():.3f}, Max: {sc2.max():.3f}, Mean: {sc2.mean():.3f}")
    print(f"Signal 2 (thresh 0)   | Longs: {(s2 == 1.0).sum()}, Neutrals: {(s2 == 0.0).sum()}, Shorts: {(s2 == -1.0).sum()}")

    # 验证信号取值
    assert set(s1.unique()).issubset({-1.0, 0.0, 1.0}), "Signal 1 values invalid"
    assert set(s2.unique()).issubset({-1.0, 0.0, 1.0}), "Signal 2 values invalid"

    # 信号 1 应该有显著的观望期 (中性 0 占比较大)
    neutral_ratio = (s1 == 0.0).mean()
    print(f"Signal 1 Neutral Ratio: {neutral_ratio*100:.1f}% (Expected ~40-60%)")
    assert 0.30 <= neutral_ratio <= 0.70, "Signal 1 should have ~30-70% neutral observation days"

    print("SCORING ENGINE TESTS PASSED FULLY!")

if __name__ == "__main__":
    test_scoring_engine()
