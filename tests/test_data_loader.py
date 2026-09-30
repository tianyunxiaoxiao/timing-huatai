"""
测试 HuataiDataLoader 数据加载与宽基指数支持
"""
import time, os, sys, psutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import HuataiTimingConfig, BROAD_INDICES
from data_loader import HuataiDataLoader

def test_data_loader():
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    t0 = time.time()

    loader = HuataiDataLoader()
    loader.load_cache()
    load_time = time.time() - t0

    print("=== HuataiDataLoader Test Results ===")
    print(f"Data loading time: {load_time:.3f} s")

    # 测试中证全指
    t1 = time.time()
    df_all_a = loader.get_index_market_data("000985.XSHG")
    align_time = time.time() - t1
    print(f"000985.XSHG aligned: {df_all_a.shape} in {align_time:.3f} s")

    assert not df_all_a.empty, "DataFrame should not be empty"
    assert len(df_all_a) > 3000, f"Expected >3000 bars, got {len(df_all_a)}"
    for col in ["trade_date", "close", "turnover_rate", "opt50_OI_PCR", "opt50_iv", "limit_up_ratio_proxy"]:
        assert col in df_all_a.columns, f"Missing column: {col}"

    # 测试全量 11 个主流宽基指数的无缝载入
    for code in BROAD_INDICES:
        df_sub = loader.get_index_market_data(code)
        print(f"Index {code:12s} loaded: {len(df_sub):4d} bars | Close range: [{df_sub['close'].min():.1f}, {df_sub['close'].max():.1f}]")
        assert len(df_sub) > 1000, f"Index {code} has too few bars: {len(df_sub)}"

    mem_after = process.memory_info().rss / (1024 * 1024)
    print(f"Memory delta: {mem_after - mem_before:.2f} MB (Peak: {mem_after:.2f} MB)")
    print("ALL 11 BROAD INDICES VERIFIED IN DATA LOADER!")

if __name__ == "__main__":
    test_data_loader()
