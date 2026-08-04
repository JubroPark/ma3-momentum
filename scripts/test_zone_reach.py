"""구간 도달 알림 로직 자체 점검 (pytest 불필요, python3 scripts/test_zone_reach.py로 실행).
fetch_eod.py의 _update_ticker와 동일한 구간/리셋 판정 로직을 그대로 재구현해 검증."""


def zone_idx(cur, base, step):
    if not cur or not base:
        return 0
    z = 0
    for i in range(1, 11):
        if cur <= base * (1 - step * i):
            z = i
    return z


def update(prev_low, prev_high, close, step):
    """반환: (new_low, new_high, zone_reach). fetch_eod.py의 _update_ticker와 동일 로직.
    리셋 판정은 구간 "번호" 비교가 아니라 표에 적힌 목표 구간의 실제 가격 도달 여부로 함
    (zone_idx는 zone1 문턱만 넘으면 전부 0구간으로 뭉뚱그려서, 기준가 자체엔 못 미쳤는데도
    리셋되는 버그가 있었음 — 2026-08-04 확인)."""
    new_peak = close > prev_high
    high = max(prev_high, close)
    base = high
    prev_zone = zone_idx(prev_low, base, step)
    target_zone = prev_zone - 2
    recovery_price = base * (1 - step * target_zone)
    reached_recovery = prev_zone >= 2 and close >= recovery_price
    is_reset = reached_recovery or new_peak
    new_low = close if is_reset else (min(prev_low, close) if prev_low else close)
    zone_reach = None
    if not is_reset and new_low < prev_low:
        deepest = zone_idx(new_low, base, step)
        if deepest > prev_zone:
            zone_reach = deepest
    return new_low, high, zone_reach


def test():
    # 실제 세션에서 검증된 NVDA 시나리오: 직전고점 212.5, 저점 190.01 → -25%(5% step) 기준 2구간
    low, high, zr = update(prev_low=212.5, prev_high=212.5, close=190.01, step=0.05)
    assert zr == 2, f"NVDA 2구간 도달 기대, 실제 {zr}"

    # QQQ 시나리오: 직전고점 725.51, 저점 661.73 → -25%(2.5% step) 기준 3구간
    low, high, zr = update(prev_low=725.51, prev_high=725.51, close=661.73, step=0.025)
    assert zr == 3, f"QQQ 3구간 도달 기대, 실제 {zr}"

    # 점진적 하락: 매일 조금씩 더 깊어지면 그때마다만 신규 구간 이벤트
    low, high, zr = update(prev_low=100, prev_high=100, close=96, step=0.05)   # -4%, 아직 0구간
    assert zr is None
    low, high, zr = update(prev_low=low, prev_high=high, close=94, step=0.05)  # -6%, 1구간 신규
    assert zr == 1
    low, high, zr = update(prev_low=low, prev_high=high, close=93, step=0.05)  # -7%, 여전히 1구간(신규 아님)
    assert zr is None

    # 2구간 이상 반등 → 리셋, 반등 자체는 zone_reach 아님
    low, high, zr = update(prev_low=80, prev_high=100, close=95, step=0.05)  # 저점80(4구간)에서 95로 반등
    assert zr is None and low == 95, f"리셋 기대, low={low} zr={zr}"

    # 전고점 신규 경신 → 리셋(저점을 오늘 종가로), zone_reach 없음
    low, high, zr = update(prev_low=90, prev_high=100, close=105, step=0.05)
    assert zr is None and low == 105 and high == 105

    # 실제 세션 리그레션(2026-08-04): 저점 190.01(2구간, 전고점 212.5)에서 206.64로 반등해도
    # 0구간 기준가(212.5) 자체엔 못 미쳤으므로 리셋되면 안 됨 — zone_idx 번호 비교로는
    # 잘못 리셋되던 버그
    low, high, zr = update(prev_low=190.01, prev_high=212.5, close=206.64, step=0.05)
    assert low == 190.01, f"저점 유지 기대, 실제 low={low}"

    # 반대로 종가가 실제 기준가(212.5) 이상으로 회복하면 정상적으로 리셋
    low, high, zr = update(prev_low=190.01, prev_high=212.5, close=212.5, step=0.05)
    assert low == 212.5, f"리셋 기대, 실제 low={low}"

    print("OK — all zone_reach cases passed")


if __name__ == "__main__":
    test()
