"""
测试 10 大核心技术指标引擎 (HuataiTechnicalEngine)
"""
import time, os, sys, psutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import HuataiTimingConfig, TEN_INDICATORS
from data_loader import HuataiDataLoader
from technical_factors import HuataiTechnicalEngine

def test_technical_factors():
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    t0 = time.time()

    loader = HuataiDataLoader()
    df_market = loader.get_index_market_data("000985.XSHG")

    engine = HuataiTechnicalEngine()
    raw_df, sig_df = engine.compute_10_factors(df_market)

    calc_time = time.time() - t0
    mem_after = process.memory_info().rss / (1024 * 1024)

    print("=== HuataiTechnicalEngine Test Results ===")
    print(f"10 Factors calculation time: {calc_time:.3f} s")
    print(f"Memory delta: {mem_after - mem_before:.2f} MB (Peak: {mem_after:.2f} MB)")
    print(f"Raw shape: {raw_df.shape} | Signal shape: {sig_df.shape}")

    # 验证 10 个指标全部在列
    for code, meta in TEN_INDICATORS.items():
        assert code in raw_df.columns, f"Missing raw factor: {code}"
        assert code in sig_df.columns, f"Missing signal factor: {code}"

        valid_vals = sig_df[code].dropna().unique()
        print(f"[{meta['dimension']:2s}] {meta['name']:25s} | Unique signals: {sorted(valid_vals)}")
        for v in valid_vals:
            assert v in [-1.0, 0.0, 1.0], f"Invalid signal: {v} in {code}"

        # 仅做多指标验证没有 -1
        if meta["long_only"]:
            assert -1.0 not in valid_vals, f"Long-only factor {code} should not have -1.0"

    print("ALL 10 TECHNICAL FACTORS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_technical_factors()
