"""Phase 0 데이터 PoC — 6개 독립 검증 함수."""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _get_close(df: pd.DataFrame) -> pd.Series:
    """yfinance MultiIndex 또는 단일 컬럼 DataFrame 모두에서 Close 추출."""
    return df["Close"].squeeze().dropna()


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

    # 위기 시작일: 최근 90일 내 첫 마삼 (위기 전체 구간의 장중 저가를 보기 위해)
    if latest_masam_date is not None:
        ninety_days_ago = reference_date - pd.Timedelta(days=90)
        recent_masams = masam[masam.index >= ninety_days_ago]
        first_masam_date = recent_masams.index[0] if not recent_masams.empty else latest_masam_date
    else:
        first_masam_date = None
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
        "first_masam_date": first_masam_date,
        "latest_masam_pct": latest_masam_pct,
        "month_count": month_count,
        "prev_year_return": prev_year_return,
        "ath_value": round(ath_value, 2),
        "ath_date": ath_date,
        "current_close": round(current_close, 2),
        "ath_drawdown": ath_drawdown,
    }


def check_rate_env(fred: "Fred" = None) -> dict:
    """
    FRED DFF(연방기금금리 실효치)로 금리환경 판단.
    DFF ≤ 0.25% → ZERO / DFF > 0.25% → NON_ZERO
    """
    if fred is None:
        fred = Fred(api_key=FRED_API_KEY)

    series = fred.get_series("DFF")
    latest = series.dropna().iloc[-1]
    last_date = series.dropna().index[-1].strftime("%Y-%m-%d")

    rate_env = "ZERO" if latest <= 0.25 else "NON_ZERO"

    return {
        "status": "PASS",
        "rate_env": rate_env,
        "dff": round(float(latest), 2),
        "last_updated": last_date,
    }


def check_drawdown(df_ixic: pd.DataFrame = None) -> dict:
    """
    ^IXIC 전고점 대비 현재 하락률.
    main()에서 check_masam과 동일한 df_ixic을 공유해 중복 다운로드 방지.
    """
    if df_ixic is None:
        df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    close = _get_close(df_ixic)
    ath_value = float(close.max())
    ath_date = close.idxmax()
    current_close = float(close.iloc[-1])
    ath_drawdown = round((current_close / ath_value - 1) * 100, 2)

    return {
        "status": "PASS",
        "ath_value": round(ath_value, 2),
        "ath_date": ath_date,
        "current_close": round(current_close, 2),
        "ath_drawdown": ath_drawdown,
    }


_QE_AMBIGUOUS_THRESHOLD = 0.1  # %


def check_qe(fred: "Fred" = None) -> dict:
    """
    FRED WALCL(연준 총자산) 4주 이동평균 기울기로 QE 자동 감지.
    기울기 > +0.1% → QE_ON / 기울기 < -0.1% → QE_OFF / 그 사이 → WARN AMBIGUOUS
    """
    if fred is None:
        fred = Fred(api_key=FRED_API_KEY)

    series = fred.get_series("WALCL").dropna().tail(8)
    last_date = series.index[-1].strftime("%Y-%m-%d")

    ma4 = series.rolling(4).mean().dropna()
    if len(ma4) < 2:
        return {"status": "FAIL", "error": "WALCL 데이터 부족 (4주 MA 산출 불가)"}

    slope_pct = round(float((ma4.iloc[-1] / ma4.iloc[-2] - 1) * 100), 4)

    if slope_pct > _QE_AMBIGUOUS_THRESHOLD:
        qe_active, qe_state, status = True, "QE_ON", "PASS"
    elif slope_pct < -_QE_AMBIGUOUS_THRESHOLD:
        qe_active, qe_state, status = False, "QE_OFF", "PASS"
    else:
        qe_active, qe_state, status = False, "AMBIGUOUS", "WARN"

    return {
        "status": status,
        "qe_active": qe_active,
        "qe_state": qe_state,
        "slope_pct": slope_pct,
        "last_updated": last_date,
        "warn_message": "QE 여부 모호 — 수동 확인 필요" if status == "WARN" else None,
    }


_RS_SAMPLE_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "TSLA", "AVGO", "COST", "ORCL", "AMD", "NFLX",
    "ADBE", "QCOM", "TXN", "AMAT", "INTC", "MU",
    "LRCX", "KLAC", "PANW", "CRWD", "SNPS", "CDNS",
    "MELI", "ASML", "ARM", "SMCI", "PLTR", "COIN",
]


def _calc_rs_pct(prices: pd.DataFrame, spy: pd.Series) -> dict:
    """
    RS_raw = 0.5·r20 + 0.3·r60 + 0.2·r120 (각 종목 vs SPY 초과수익률)
    RS_pct = 샘플 내 percentile rank (0~100)
    """
    spy = spy.dropna()
    rs_raw = {}
    for ticker in prices.columns:
        s = prices[ticker].dropna()
        if len(s) < 121:
            continue
        r20 = float(s.iloc[-1] / s.iloc[-20] - 1) - float(spy.iloc[-1] / spy.iloc[-20] - 1)
        r60 = float(s.iloc[-1] / s.iloc[-60] - 1) - float(spy.iloc[-1] / spy.iloc[-60] - 1)
        r120 = float(s.iloc[-1] / s.iloc[-120] - 1) - float(spy.iloc[-1] / spy.iloc[-120] - 1)
        rs_raw[ticker] = 0.5 * r20 + 0.3 * r60 + 0.2 * r120

    if not rs_raw:
        return {}

    values = list(rs_raw.values())
    rs_pct = {
        t: round(float(np.searchsorted(sorted(values), v) / len(values) * 100), 1)
        for t, v in rs_raw.items()
    }
    return rs_pct


def check_rs_percentile(prices: pd.DataFrame = None, spy: pd.Series = None) -> dict:
    """
    샘플 30종목으로 MA50 RS percentile 계산 로직 검증.
    실제 서비스에서는 S&P500+NDX 전체 롤링 캐시 사용 (Phase 1).
    """
    import time

    start = time.time()

    if prices is None or spy is None:
        raw = yf.download(
            _RS_SAMPLE_TICKERS + ["SPY"],
            period="7mo",
            auto_adjust=True,
            progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            close_df = raw["Close"]
        else:
            close_df = raw

        spy = close_df["SPY"]
        prices = close_df.drop(columns=["SPY"])

    rs_pcts = _calc_rs_pct(prices, spy)

    if not rs_pcts:
        return {"status": "FAIL", "error": "RS 계산 가능한 종목 없음 (데이터 부족)"}

    sorted_items = sorted(rs_pcts.items(), key=lambda x: x[1], reverse=True)
    top3 = [{"ticker": t, "rs_pct": v} for t, v in sorted_items[:3]]
    bottom3 = [{"ticker": t, "rs_pct": v} for t, v in sorted_items[-3:]]

    elapsed = round(time.time() - start, 1)

    return {
        "status": "PASS",
        "top3": top3,
        "bottom3": bottom3,
        "total_tickers": len(rs_pcts),
        "elapsed_sec": elapsed,
    }


def check_pmi_source(gemini_key: str = None) -> dict:
    """
    Gemini Google Search grounding으로 최신 ISM 제조업 PMI 조회.
    FRED NAPM 시리즈가 더 이상 존재하지 않아 Gemini 웹검색으로 대체.
    """
    import re
    from google import genai
    from google.genai.types import Tool, GenerateContentConfig, GoogleSearch

    key = gemini_key or GEMINI_API_KEY
    if not key:
        return {
            "status": "WARN",
            "pmi_value": None,
            "release_month": None,
            "warn_message": "GEMINI_API_KEY 미설정 → 수동입력 폴백",
        }

    try:
        client = genai.Client(api_key=key)
        today = pd.Timestamp.today()
        prompt = (
            f"오늘은 {today.strftime('%Y년 %m월 %d일')}입니다. "
            "가장 최신 ISM 제조업 PMI(Manufacturing PMI) 수치를 검색해서 알려주세요. "
            "반드시 아래 형식으로만 답하세요:\n"
            "PMI: [숫자]\n발표월: [YYYY-MM]"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=GenerateContentConfig(
                tools=[Tool(google_search=GoogleSearch())]
            ),
        )
        text = response.text
        pmi_match = re.search(r"PMI:\s*([\d.]+)", text)
        month_match = re.search(r"발표월:\s*(\d{4}-\d{2})", text)

        if not pmi_match:
            return {
                "status": "WARN",
                "pmi_value": None,
                "release_month": None,
                "warn_message": f"Gemini 응답 파싱 실패 → 수동입력 폴백: {text[:80]}",
            }

        pmi_value = float(pmi_match.group(1))
        release_month = month_match.group(1) if month_match else "미확인"

        if not 30 <= pmi_value <= 70:
            return {
                "status": "WARN",
                "pmi_value": pmi_value,
                "release_month": release_month,
                "warn_message": f"PMI 범위 이상({pmi_value}) — 수동 확인 필요",
            }

        return {
            "status": "PASS",
            "pmi_value": pmi_value,
            "release_month": release_month,
            "warn_message": None,
        }
    except Exception as e:
        return {
            "status": "WARN",
            "pmi_value": None,
            "release_month": None,
            "warn_message": f"Gemini PMI 조회 실패({e}) → 수동입력 폴백",
        }


def _print_result(name: str, result: dict) -> None:
    status = result.get("status", "FAIL")
    label = f"[{status}]"
    print(f"{label} {name}")

    if status == "FAIL":
        print(f"       오류: {result.get('error', '알 수 없음')}")
        return

    if name == "^IXIC 마삼 감지":
        masam_date = result["latest_masam_date"]
        masam_str = f"{masam_date.date()} ({result['latest_masam_pct']}%)" if masam_date else "없음"
        print(f"       최근 마삼: {masam_str}")
        print(f"       이번 달 마삼: {result['month_count']}회")
        prev = result["prev_year_return"]
        print(f"       전년 역년 수익률: {prev}%" if prev is not None else "       전년 역년 수익률: 데이터 없음")
        print(f"       전고점 대비: {result['ath_drawdown']}%  (전고점: {result['ath_date'].date()} {result['ath_value']:,.2f})")

    elif name == "금리환경":
        print(f"       DFF: {result['dff']}% → {result['rate_env']}  ({result['last_updated']})")

    elif name == "전고점 대비 하락":
        print(f"       전고점: {result['ath_date'].date()} {result['ath_value']:,.2f}")
        print(f"       현재: {result['current_close']:,.2f}  하락률: {result['ath_drawdown']}%")

    elif name == "WALCL QE 자동감지":
        msg = f"기울기 {result['slope_pct']}% → {result['qe_state']}"
        if result.get("warn_message"):
            msg += f"  ⚠ {result['warn_message']}"
        print(f"       {msg}  ({result['last_updated']})")

    elif name == "MA50 RS percentile":
        top = result.get("top3", [])
        top_str = "  ".join(f"{r['ticker']}={r['rs_pct']}" for r in top)
        print(f"       상위 3: {top_str}")
        print(f"       종목 수: {result['total_tickers']}  처리시간: {result['elapsed_sec']}s")

    elif name == "PMI 소스":
        if result.get("warn_message"):
            print(f"       {result['warn_message']}")
        else:
            print(f"       ISM 제조업 PMI: {result['pmi_value']}  ({result['release_month']})")


def main() -> None:
    print("=" * 60)
    print("MA3 MOMENTUM — Phase 0 데이터 PoC")
    print(f"실행일시: {pd.Timestamp.today().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # ^IXIC 데이터를 한 번만 다운로드해 두 함수가 공유
    print("^IXIC 데이터 다운로드 중...")
    df_ixic = yf.download("^IXIC", period="2y", auto_adjust=True, progress=False)

    # FRED 클라이언트 공유
    fred = Fred(api_key=FRED_API_KEY)

    checks = [
        ("^IXIC 마삼 감지",       lambda: check_masam(df_ixic=df_ixic)),
        ("금리환경",               lambda: check_rate_env(fred=fred)),
        ("전고점 대비 하락",       lambda: check_drawdown(df_ixic=df_ixic)),
        ("WALCL QE 자동감지",     lambda: check_qe(fred=fred)),
        ("MA50 RS percentile",    check_rs_percentile),
        ("PMI 소스",               check_pmi_source),
    ]

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    for name, fn in checks:
        try:
            result = fn()
        except Exception as e:
            result = {"status": "FAIL", "error": str(e)}

        _print_result(name, result)
        counts[result.get("status", "FAIL")] += 1
        print()

    print("=" * 60)
    print(f"결과: PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}")
    phase1_ok = counts["FAIL"] == 0 and counts["PASS"] >= 4
    print("Phase 1 진입 가능 ✓" if phase1_ok else "⚠ FAIL 항목 확인 후 Phase 1 진입")
    print("=" * 60)


if __name__ == "__main__":
    main()
