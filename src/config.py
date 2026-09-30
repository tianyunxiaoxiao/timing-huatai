"""
华泰 10 因子技术打分择时系统 - 全局配置模块
严格对齐《华泰证券-金工深度研究：A股择时之技术打分体系（2025-12-26）》
"""
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DATA_DIR = BASE_DIR / "data"
FALLBACK_DATA_DIR = BASE_DIR.parent / "timing_project" / "data"

# 数据路径: 优先环境变量，其次本地 data/ 目录，最后回退至上级工程 data/
env_data_dir = os.environ.get("HUATAI_DATA_DIR")
if env_data_dir:
    DATA_DIR = Path(env_data_dir)
elif LOCAL_DATA_DIR.exists() and any(LOCAL_DATA_DIR.iterdir()):
    DATA_DIR = LOCAL_DATA_DIR
else:
    DATA_DIR = FALLBACK_DATA_DIR

ARTIFACTS_DIR = BASE_DIR / "artifacts"

# 10 大核心指标名称与所属维度 (研报图表8与图表9)
TEN_INDICATORS = {
    # 价格维度 (2个)
    "bias_price_20": {"dimension": "价格", "name": "20日价格乖离率", "strategy": "动量", "long_only": False},
    "boll_price_20": {"dimension": "价格", "name": "20日布林带", "strategy": "布林带", "long_only": False},
    # 量能维度 (2个)
    "bias_turnover_20": {"dimension": "量能", "name": "20日换手率乖离率", "strategy": "布林带", "long_only": False},
    "bias_turnover_60": {"dimension": "量能", "name": "60日换手率乖离率", "strategy": "布林带", "long_only": False},
    # 趋势维度 (2个)
    "adx_20": {"dimension": "趋势", "name": "20日 ADX", "strategy": "均线", "long_only": False},
    "high_ratio_20": {"dimension": "趋势", "name": "20日创新高天数占比", "strategy": "布林带-仅做多", "long_only": True},
    # 波动维度 (2个)
    "turnover_vol_60": {"dimension": "波动", "name": "60日换手率波动", "strategy": "布林带-仅做多", "long_only": True},
    "opt50_iv": {"dimension": "波动", "name": "50ETF期权隐含波动率", "strategy": "布林带", "long_only": False},
    # 拥挤维度 (2个)
    "limit_up_ratio_5": {"dimension": "拥挤", "name": "成分股涨停家数占比5日均值", "strategy": "动量", "long_only": False},
    "opt50_oi_pcr_ma5": {"dimension": "拥挤", "name": "50ETF期权持仓量PCR 5日均值", "strategy": "反向布林带", "long_only": False}
}

# 信号 2 保留的 6 大因子 (剔除量、价，仅保留趋势、波动、拥挤)
SIX_INDICATORS = [
    "adx_20",
    "high_ratio_20",
    "turnover_vol_60",
    "opt50_iv",
    "limit_up_ratio_5",
    "opt50_oi_pcr_ma5"
]

# 研报泛化的主流宽基指数清单 (图表41与图表44)
BROAD_INDICES = [
    "000985.XSHG", # 万得全A (官方中证全指替代)
    "000016.XSHG", # 上证50
    "000300.XSHG", # 沪深300
    "000905.XSHG", # 中证500
    "000906.XSHG", # 中证800
    "000852.XSHG", # 中证1000
    "932000.INDX", # 中证2000
    "000001.XSHG", # 上证指数
    "399001.XSHE", # 深证成指
    "399006.XSHE", # 创业板指
    "000688.XSHG"  # 科创50
]

@dataclass(frozen=True)
class HuataiTimingConfig:
    start_date: date = date(2010, 1, 4)
    end_date: date = date(2026, 9, 29)
    benchmark_id: str = "000985.XSHG"
    fee_rate: float = 0.0005           # 严格研报第7页设置: 交易费率双边 0.05%
    initial_capital: float = 100_000_000.0
    risk_free_rate: float = 0.02       # 年化无风险利率 2.0%
    data_dir: Path = DATA_DIR
    artifacts_dir: Path = ARTIFACTS_DIR
