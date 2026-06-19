"""
Web Push 발송 스크립트 — EOD 배치 후 트리거 감지 시 실행
환경변수: VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, GITHUB_PAT
"""
import json
import os
import sys
import base64
import urllib.request
from datetime import date

REPO   = 'JubroPark/ma3-momentum'
PATH   = 'app/public/data/push_subscriptions.json'
DATA   = 'app/public/data'


def gh_get(path: str) -> dict:
    url = f'https://api.github.com/repos/{REPO}/contents/{path}?ref=main'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {os.environ["GITHUB_PAT"]}',
        'Accept': 'application/vnd.github+json',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    content = base64.b64decode(data['content']).decode('utf-8')
    return json.loads(content)


def load_subscriptions() -> list:
    try:
        return gh_get(PATH)
    except Exception as e:
        print(f'  구독자 로드 실패: {e}')
        return []


def send_notification(sub: dict, payload: dict, vapid_private: str, vapid_public: str):
    from pywebpush import webpush, WebPushException
    try:
        webpush(
            subscription_info=sub,
            data=json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims={'sub': 'mailto:noreply@ma3momentum.app'},
        )
        return True
    except WebPushException as e:
        code = e.response.status_code if e.response else 0
        if code in (404, 410):
            print(f'    만료된 구독 (endpoint 삭제 필요): {sub["endpoint"][:40]}...')
        else:
            print(f'    발송 실패 ({code}): {e}')
        return False


def build_alerts(masam: dict) -> list:
    """알림 대상 이벤트 추출"""
    alerts = []
    mode = masam.get('mode', 'NORMAL')
    masam_data = masam.get('masam', {})
    today = date.today().isoformat()
    as_of = masam.get('as_of', '')

    # 오늘 날짜 데이터가 아니면 스킵
    if as_of != today:
        return []

    # 마삼 발생 (이번 달 카운트 증가 = 오늘 마삼)
    month_count = masam_data.get('month_count', 0)
    last_masam = masam_data.get('last_masam_date', '')
    if last_masam == today and month_count >= 1:
        alerts.append({
            'title': f'🚨 마삼 발생 — {month_count}회 (이번 달)',
            'body': f'나스닥 -3% 이상 하락 감지. 모드: {mode}',
            'tag': 'masam',
            'url': '/app.html',
            'requireInteraction': True,
        })

    # 모드 전환 알림
    prev_mode = masam.get('_prev_mode')  # 이전 배치에서 저장한 값 (선택)
    if prev_mode and prev_mode != mode:
        labels = {'CRISIS': '⚠️ 위기 모드', 'PANIC': '🔴 공황 모드', 'NORMAL': '✅ 평상시 복귀'}
        alerts.append({
            'title': labels.get(mode, mode),
            'body': f'마삼룰 모드가 {prev_mode} → {mode}으로 전환됐습니다.',
            'tag': 'mode-change',
            'url': '/app.html',
        })

    # 올인 트리거 (오늘 처음으로 충족)
    conditions = masam.get('all_in_conditions', [])
    newly_met = [c for c in conditions if c.get('met') and c.get('grade') == '강']
    if mode in ('CRISIS', 'PANIC') and newly_met:
        labels = [c['label'] for c in newly_met]
        alerts.append({
            'title': '🟢 올인 트리거 감지',
            'body': '충족: ' + ', '.join(labels),
            'tag': 'all-in',
            'url': '/app.html',
            'requireInteraction': True,
        })

    return alerts


def main():
    vapid_private = os.environ.get('VAPID_PRIVATE_KEY', '')
    vapid_public  = os.environ.get('VAPID_PUBLIC_KEY', '')
    if not vapid_private or not vapid_public:
        sys.exit('[오류] VAPID 키가 설정되지 않았습니다')

    print(f'\n[Push 발송] {date.today()}')

    subs = load_subscriptions()
    if not subs:
        print('  구독자 없음 — 스킵')
        return

    masam = gh_get('app/public/data/masam.json')
    alerts = build_alerts(masam)

    if not alerts:
        print('  발송할 알림 없음')
        return

    print(f'  알림 {len(alerts)}건 × 구독자 {len(subs)}명')
    for alert in alerts:
        print(f'  [{alert["tag"]}] {alert["title"]}')
        sent = 0
        for sub in subs:
            if send_notification(sub, alert, vapid_private, vapid_public):
                sent += 1
        print(f'    → {sent}/{len(subs)} 발송 완료')

    print('✓ Push 발송 완료')


if __name__ == '__main__':
    main()
