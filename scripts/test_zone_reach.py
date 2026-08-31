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


def update(prev_low, prev_high, close, step, allin=0, hist_max=None):
    """반환: (new_low, new_high, zone_reach). fetch_eod.py의 _update_ticker와 동일 로직.
    리셋 판정은 구간 "번호" 비교가 아니라 표에 적힌 목표 구간의 실제 가격 도달 여부로 함
    (zone_idx는 zone1 문턱만 넘으면 전부 0구간으로 뭉뚱그려서, 기준가 자체엔 못 미쳤는데도
    리셋되는 버그가 있었음 — 2026-08-04 확인).
    base(구간/회복목표가 기준)는 어제까지의 직전고점(prev_high, 그대로 고정)으로 계산 —
    오늘 신고가(new_high)를 기준으로 계산하면 회복 목표가가 가격을 따라 계속 올라가는
    "움직이는 표적"이 되어 영영 도달 불가능해지는 버그가 있었음(2026-08-29 확인).
    new_peak만으로는 (prev_zone==0 AND base가 prev_high일 때)만 리셋(무해) —
    prev_zone==1(2구간 하락에 못 미친 상태)에서 직전 고점을 살짝 넘는 신고가만으로
    완전 리셋되던 버그, 그리고 종가가 잠깐 allin 밑으로 눌려 base가 allin으로
    바뀐 틈에 since-윈도우 히스토리의 과거 진짜 고점이 "무해한 신고가"로 오인돼
    리셋되던 버그(2026-08-29 2차 확인) 둘 다 수정. allin=0(기본값)이면 항상
    base=prev_high(기존 테스트 케이스들과 동일하게 동작). is_reset이 아니면
    직전고점 자체도 갱신하지 않고 고정. hist_max는 since-윈도우 원시 히스토리의 실제 최고
    종가(fetch_eod.py의 since_series.max()) — old_high가 얼려있는 동안에도(활성 하락
    사이클 중) 과거에 이미 찍힌 더 높은 종가가 그대로 남아있을 수 있어, 단순
    max(old_high, close)로는 이 케이스를 재현할 수 없음(2026-08-29 2차 확인)."""
    old_high = prev_high
    new_high = hist_max if hist_max is not None else max(old_high, close)
    new_peak = new_high > old_high
    used_prev_high = allin <= 0 or close >= allin
    base = old_high if used_prev_high else allin
    prev_zone = zone_idx(prev_low, base, step)
    target_zone = prev_zone - 2
    recovery_price = base * (1 - step * target_zone)
    reached_recovery = prev_zone >= 2 and close >= recovery_price
    is_reset = reached_recovery or (new_peak and prev_zone == 0 and used_prev_high)
    new_low = close if is_reset else (min(prev_low, close) if prev_low else close)
    high = new_high if is_reset else old_high
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

    # 실제 세션 리그레션(2026-08-29, NVDA): 직전고점 225.3에서 저점 208.48(1구간, 2구간 문턱
    # -10%엔 못 미침)까지 하락 후 227.98로 반등 — 옛 직전고점(225.3)은 넘었지만 2구간 회복은
    # 구조적으로 불가능(prev_zone=1<2)한 상태이므로 저점도 직전고점도 안 바뀌어야 함(매뉴얼:
    # 재매수는 "막바지 2구간 상승"만 트리거, 신고가 경신이 아님). 직전고점까지 227.98로
    # 갱신해버리면 회복 목표가(base*1.05)도 같이 밀려 올라가 영영 재매수가 불가능해짐
    low, high, zr = update(prev_low=208.48, prev_high=225.3, close=227.98, step=0.05)
    assert low == 208.48, f"1구간 하락 중 신고가만으로는 저점 유지 기대, 실제 low={low}"
    assert high == 225.3, f"활성 하락 사이클 중엔 직전고점도 고정 기대, 실제 high={high}"

    # 실제 세션 리그레션(2026-08-29 2차, NVDA): 직전고점 225.3(얼려있음)·저점 208.48(1구간)·
    # 올인가 219.22인 상태에서, 종가가 하루 217.55로 올인가 밑으로 눌림 — base가
    # allin(219.22)으로 바뀌면서 prev_zone이 0으로 재계산되고, since-윈도우 히스토리의 실제
    # 과거 고점(227.98, 8/27 종가 — old_high는 얼려있어 225.3이지만 원시 히스토리엔 그대로
    # 남아있음)이 new_peak으로 잡혀 "무해한 리셋"으로 오인되던 버그. base가 allin일 땐
    # new_peak 단독 리셋을 허용하면 안 됨 — 저점·직전고점 모두 그대로 유지돼야 함
    low, high, zr = update(
        prev_low=208.48, prev_high=225.3, close=217.55, step=0.05,
        allin=219.22, hist_max=227.98,
    )
    assert low == 208.48, f"allin 밑 눌림 중 저점 유지 기대, 실제 low={low}"
    assert high == 225.3, f"allin 밑 눌림 중 직전고점 유지 기대, 실제 high={high}"

    print("OK — all zone_reach cases passed")


def update_allin(prev_low, prev_high, allin, close, step):
    """fetch_eod.py의 _update_ticker 중 allin(올인 지점 기준가) 갱신 로직만 분리 재현.
    new_peak(단순 신고가)만으로는 allin을 건드리면 안 되고, reached_recovery(2구간 하락 후
    실제 재매수)일 때만 갱신해야 함 — 아니면 신고가 찍을 때마다 prev_high와 allin이 같은
    값으로 붕괴해 '직전 고점'/'올인 지점' 두 탭이 항상 동일하게 표시되는 버그가 생김
    (2026-08-06 확인)."""
    old_high = prev_high
    new_high = max(old_high, close)
    new_peak = new_high > old_high
    base = old_high
    prev_zone = zone_idx(prev_low, base, step)
    target_zone = prev_zone - 2
    recovery_price = base * (1 - step * target_zone)
    reached_recovery = prev_zone >= 2 and close >= recovery_price
    new_allin = close if reached_recovery else allin
    is_reset = reached_recovery or (new_peak and prev_zone == 0)
    high = new_high if is_reset else old_high
    return new_allin, high


def test_allin_vs_prev_high():
    # NVDA 시나리오: 진입가 195.55, 직전고점 212.5에서 219.22로 신고가 경신(2구간 하락 없이
    # 그냥 전고 돌파) → prev_high는 219.22로 갱신되지만, allin은 195.55 그대로 유지돼야 함
    allin, high = update_allin(prev_low=212.5, prev_high=212.5, allin=195.55, close=219.22, step=0.05)
    assert high == 219.22, f"직전고점 갱신 기대, 실제 {high}"
    assert allin == 195.55, f"단순 신고가로는 올인 기준가 유지 기대, 실제 {allin}"

    # 반대로 2구간 하락(저점 190.01, base 212.5) 후 목표구간가(212.5) 이상 회복 → 진짜 재매수,
    # allin이 회복 종가로 갱신돼야 함
    allin, high = update_allin(prev_low=190.01, prev_high=212.5, allin=195.55, close=212.5, step=0.05)
    assert allin == 212.5, f"재매수 리셋 기대, 실제 allin={allin}"

    print("OK — allin vs prev_high divergence passed")


def update_since(prev_low, prev_high, allin, since, close, step, today):
    """entry['since'] 리셋 로직만 분리 재현. reached_recovery 때 since를 오늘로 리셋해야
    prev_high가 재매수 이전 히스토리를 계속 끌고 오지 않음 (2026-08-10 확인)."""
    old_high = prev_high
    new_high = max(old_high, close)
    new_peak = new_high > old_high
    base = old_high
    prev_zone = zone_idx(prev_low, base, step)
    target_zone = prev_zone - 2
    recovery_price = base * (1 - step * target_zone)
    reached_recovery = prev_zone >= 2 and close >= recovery_price
    is_reset = reached_recovery or (new_peak and prev_zone == 0)
    high = new_high if is_reset else old_high
    if reached_recovery:
        allin = close
        since = today
        high = close
    return allin, high, since


def test_since_reset_on_recovery():
    # 재매수(reached_recovery) 발생 시 since가 오늘로 리셋되어, prev_high가 재매수 이전의
    # 옛 전고점을 더 이상 반영하지 않아야 함. 안 그러면 재매수 직후에도 prevHigh(옛 전고점)가
    # 새 allin(재매수가)보다 훨씬 높게 남아 프론트 자동전환(prevHigh > allin)이 곧장
    # "직전 고점"으로 넘어가버려 사실상 매 사이클 무력화됨 (2026-08-10 확인)
    allin, high, since = update_since(
        prev_low=190.01, prev_high=212.5, allin=195.55, since='2026-07-06',
        close=212.5, step=0.05, today='2026-08-15',
    )
    assert allin == 212.5
    assert high == 212.5, f"재매수 시점에 prev_high도 재매수가로 리셋 기대, 실제 {high}"
    assert since == '2026-08-15', f"since 리셋 기대, 실제 {since}"
    # 재매수 직후: 아직 신고가 안 찍었으므로 prevHigh == allin (직전고점 아님, 올인지점이어야 함)
    assert not (high > allin), "재매수 직후엔 prevHigh가 allin을 넘으면 안 됨(자동전환 무력화 재발)"

    print("OK — since reset on recovery passed")


def update_ever_rank1(gap_pct, rank2_ever_rank1):
    """fetch_eod.py의 ever_rank1 리셋 로직과 동일: 격차가 10%를 다시 넘으면 2등주의
    '1등 해본 적 있음' 이력을 초기화한다(2026-08-27 확인 — 영구 마킹이면 예전에 잠깐
    1등이었던 종목이 한참 뒤 격차만 우연히 좁혀져도 1:1 배분에 잘못 잡힘)."""
    if gap_pct > 10.0:
        return False
    return rank2_ever_rank1


def test_ever_rank1_resets_when_gap_exceeds_10pct():
    # 과거에 1등이었던 이력이 있어도, 격차가 10%를 넘어서면 그 이력은 리셋되어야 함
    assert update_ever_rank1(gap_pct=12.3, rank2_ever_rank1=True) is False
    # 격차가 10% 이내로 유지되는 동안은 이력이 보존되어야 함
    assert update_ever_rank1(gap_pct=9.9, rank2_ever_rank1=True) is True
    # 애초에 1등이었던 적 없으면 격차가 좁혀져도 계속 False
    assert update_ever_rank1(gap_pct=9.9, rank2_ever_rank1=False) is False

    print("OK — ever_rank1 reset on gap > 10% passed")


if __name__ == "__main__":
    test()
    test_allin_vs_prev_high()
    test_since_reset_on_recovery()
    test_ever_rank1_resets_when_gap_exceeds_10pct()
