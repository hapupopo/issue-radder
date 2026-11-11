#!/usr/bin/env python3
"""정책브리핑(korea.kr) 보도자료 중 당사 관련 건만 텔레그램 '전략지원 알리미' 채널로 알림.
- 정책브리핑 RSS는 2026.7.1 중단 → 보도자료 목록 화면(https://www.korea.kr/briefing/pressReleaseList.do)의
  제목·요약·부처를 읽어 alerts/press-keywords.txt 키워드로 판별(페이지당 20건, 이미 본 건이 나오면 멈춤)
- .state/press-seen.json 으로 이미 본 보도자료 중복 방지(Actions 캐시 보관, 30일)
- 첫 실행은 기존 보도자료를 '본 것'으로만 기록하고 보내지 않음(폭탄 방지)
- 환경변수 DRY_RUN=yes 이면 전송 없이 결과만 출력(최근 목록 5쪽 매칭 건 미리보기)"""
import json, os, sys, html, re, time, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

LIST_URL = 'https://www.korea.kr/briefing/pressReleaseList.do?pageIndex={}'
MAX_PAGES = 10
KW_FILE = 'alerts/press-keywords.txt'
STATE = '.state/press-seen.json'
MAX_PER_RUN, MAX_AGE_H = 20, 96   # 96시간: 금요일 자료를 월요일 아침에 보낼 수 있게   # MAX_AGE_H: 게시일 기준(목록엔 날짜만 있음)
KST = timezone(timedelta(hours=9))
token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
token = token[3:] if token.lower().startswith('bot') else token
chat = (os.environ.get('TELEGRAM_CHAT_ID') or '').strip()   # 채널만(EXTRA 그룹에는 보내지 않음)
DRY = (os.environ.get('DRY_RUN') or '').lower() in ('yes', 'true', '1')

def squash(t):
    return re.sub(r'\s+', '', t or '').lower()

def load_rules():
    rules, excl = [], []
    for line in open(KW_FILE, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        name, rest = line.split(':', 1)
        terms = [t.strip() for t in rest.split(',') if t.strip()]
        if name.strip() == '제외':
            excl += [squash(t) for t in terms]
        else:
            rules.append((name.strip(), [(t, [squash(p) for p in t.split('+') if p.strip()]) for t in terms]))
    return rules, excl

def has(text, part):
    # 영문 약어(CJ, PHA, EPR 등)는 다른 영단어 일부로 잡히지 않게 경계 확인
    if re.fullmatch(r'[a-z0-9&\-]+', part):
        return re.search(r'(?<![a-z])' + re.escape(part) + r'(?![a-z])', text) is not None
    return part in text

def match(text, rules):
    hits = []
    for name, terms in rules:
        kws = [t for t, parts in terms if all(has(text, p) for p in parts)]
        if kws:
            hits.append((name, kws))
    return hits

def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))
    return re.sub(r'\s+', ' ', s).strip()

ITEM_RE = re.compile(r'<a href="(/briefing/pressReleaseView\.do\?newsId=(\d+)[^"]*)">\s*<span class="text">\s*'
                     r'<strong>(.*?)</strong>\s*<span class="lead">(.*?)</span>\s*<span class="source">\s*'
                     r'<span>([\d.]+)</span>\s*<span>(.*?)</span>', re.S)

def fetch(page):
    req = urllib.request.Request(LIST_URL.format(page), headers={'User-Agent': 'Mozilla/5.0 (issue-radder press alerts)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode('utf-8', 'replace')
    for href, nid, title, lead, date, dept in ITEM_RE.findall(body):
        try:
            ts = datetime.strptime(date, '%Y.%m.%d').replace(tzinfo=KST)
        except ValueError:
            ts = datetime.now(KST)
        yield {'title': strip_tags(title), 'desc': strip_tags(lead)[:3000], 'id': nid,
               'link': f'https://www.korea.kr/briefing/pressReleaseView.do?newsId={nid}',
               'dept': strip_tags(dept), 'ts': ts}

def send(text):
    for target in [x.strip() for x in chat.split(',') if x.strip()]:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({'chat_id': target, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=20) as r:
            if not json.load(r).get('ok'):
                raise RuntimeError('telegram send failed')

def fmt(a, hits):
    t = a['ts'].strftime('%m/%d')
    issues = ' · '.join(n for n, _ in hits)
    kws = ', '.join(dict.fromkeys(k for _, ks in hits for k in ks))
    head = f"📢 <b>[정책브리핑 보도자료]</b> {html.escape(issues)}"
    meta = ' · '.join(x for x in [html.escape(a['dept']), t] if x)
    return (f"{head}\n<b>{html.escape(a['title'])}</b>\n{meta}\n"
            f"키워드: {html.escape(kws)}\n<a href=\"{html.escape(a['link'], quote=True)}\">보도자료 보기</a>")

def main():
    rules, excl = load_rules()
    first = not os.path.exists(STATE)
    seen = {} if (first or DRY) else json.load(open(STATE, encoding='utf-8'))
    items, ids = [], set()
    for page in range(1, MAX_PAGES + 1):
        try:
            got = [a for a in fetch(page) if a['id'] not in ids]
        except Exception as e:
            print(f'{page}쪽 수집 실패: {e}'); break
        ids.update(a['id'] for a in got); items += got
        print(f'{page}쪽: {len(got)}건 ({got[-1]["ts"]:%m/%d} {got[-1]["title"][:30]})' if got else f'{page}쪽: 0건')
        if not got or (seen and all(a['id'] in seen for a in got)):
            break
        time.sleep(1)
    if not items:
        sys.exit('보도자료 목록을 읽지 못했습니다(화면 구조 변경 여부 확인 필요).')
    now = datetime.now(timezone.utc)
    new = []
    for a in items:
        if a['id'] in seen:
            continue
        if not DRY:
            seen[a['id']] = now.isoformat()
        text = squash(a['title'] + ' ' + a['desc'])
        if any(x and x in text for x in excl):
            continue
        hits = match(text, rules)
        if hits and now - a['ts'] <= timedelta(hours=MAX_AGE_H):
            new.append((a, hits))
    if DRY:
        print(f'[미리보기] 수신 {len(items)}건 중 관련 {len(new)}건 (전송 안 함)')
        for a, hits in sorted(new, key=lambda x: int(x[0]['id'])):
            print('-', a['ts'].strftime('%m/%d'), a['dept'], '|', a['title'], '|', hits)
        return
    cutoff = (now - timedelta(days=30)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    os.makedirs('.state', exist_ok=True)
    json.dump(seen, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False)
    if first:
        print(f'첫 실행: 기존 보도자료 {len(seen)}건을 기록만 했습니다(전송 안 함).'); return
    if not new:
        print('새 관련 보도자료 없음'); return
    if not token or not chat:
        sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다.')
    new.sort(key=lambda x: int(x[0]['id']))
    for a, hits in new[:MAX_PER_RUN]:
        send(fmt(a, hits)); time.sleep(1.2)
    if len(new) > MAX_PER_RUN:
        send(f'…관련 보도자료 {len(new) - MAX_PER_RUN}건은 생략했습니다. 정책브리핑에서 확인해 주세요.')
    print(f'sent {min(len(new), MAX_PER_RUN)} / {len(new)}')

if __name__ == '__main__':
    main()
