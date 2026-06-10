"""Phase 0 데이터 PoC — 6개 독립 검증 함수."""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")


def _get_close(df: pd.DataFrame) -> pd.Series:
    """yfinance MultiIndex 또는 단일 컬럼 DataFrame 모두에서 Close 추출."""
    if isinstance(df.columns, pd.MultiIndex):
        return df["Close"].squeeze()
    return df["Close"].squeeze()


def check_masam(df_ixic: pd.DataFrame = None) -> dict:
    """
    ^IXIC 마삼(-3% 이상 하락) 감지.

    Args:
        df_ixic: 테스트용 사전 로드 DataFrame. None이면 yfinance에서 2년 다운로드.

    Returns:
        {
            status: PASS | FAIL,
            latest_masam_date: pd.Timestamp | None,
            latest_masam_pct: float | None,
            month_count: int,           # 현재 달력 월 마삼 횟수 (공황 트리거용, 월별 독립)
            prev_year_return: float | None,  # 전년 역년 수익률(%)
            ath_value: float,
            ath_date: pd.Timestamp,
            current_close: float,
            ath_drawdown: float,        # 전고점 대비 하락률(%)
        }
    """
    if df_ixic is None:
        df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    close = _get_close(df_ixic)
    pct = close.pct_change() * 100

    masam = pct[pct <= -3.0]

    latest_masam_date = masam.index[-1] if not masam.empty else None
    latest_masam_pct = round(float(masam.iloc[-1]), 2) if not masam.empty else None

    # 현재 달력 월 마삼 횟수 (월 독립 집계 — 롤링 아님)
    # 데이터의 마지막 날짜를 기준으로 현재 월 판단
    reference_date = close.index[-1]
    month_mask = (masam.index.year == reference_date.year) & (masam.index.month == reference_date.month)
    month_count = int(month_mask.sum())

    # 전년도 역년 수익률
    prev_year = reference_date.year - 1
    prev_data = close[close.index.year == prev_year]
    if len(prev_data) >= 2:
        prev_year_return = round(float((prev_data.iloc[-1] / prev_data.iloc[0] - 1) * 100), 1)
    else:
        prev_year_return = None

    # 전고점 대비 하락률
    ath_value = float(close.max())
    ath_date = close.idxmax()
    current_close = float(close.iloc[-1])
    ath_drawdown = round((current_close / ath_value - 1) * 100, 2)

    return {
        "status": "PASS",
        "latest_masam_date": latest_masam_date,
        "latest_masam_pct": latest_masam_pct,
        "month_count": month_count,
        "prev_year_return": prev_year_return,
        "ath_value": round(ath_value, 2),
        "ath_date": ath_date,
        "current_close": round(current_close, 2),
        "ath_drawdown": ath_drawdown,
    }
