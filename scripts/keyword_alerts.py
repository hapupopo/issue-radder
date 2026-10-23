#!/usr/bin/env python3
"""키워드 기사 알림: Google 뉴스 RSS에서 새 기사를 찾아 텔레그램 채널로 보낸다.
- alerts/keywords.txt 의 키워드별 검색(최근 1일)
- .state/seen.json 으로 이미 보낸 기사 중복 방지(Actions 캐시에 보관)
- 첫 실행은 기존 기사를 '본 것'으로만 기록하고 보내지 않음(폭탄 방지)"""
import json, os, sys, html, re, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
chat = (os.environ.get('TELEGRAM_CHAT_ID') or '').strip()
token = token[3:] if token.lower().startswith('bot') else token
MAX_PER_RUN, MAX_AGE_H = 15, 6
STATE = '.state/seen.json'
KST = timezone(timedelta(hours=9))

def keywords():
    out = []
    for line in open('alerts/keywords.txt', encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        inc = [p for p in parts if not p.startswith('-')]
        exc = [p[1:] for p in parts if p.startswith('-') and len(p) > 1]
        out.append((' '.join(inc), inc, exc))
    return out

def fetch(q):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q + ' when:1d', 'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'})
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (issue-radder alerts)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    for it in root.iter('item'):
        title = (it.findtext('title') or '').strip()
        src = (it.findtext('source') or '').strip()
        if src and title.endswith(' - ' + src):
            title = title[: -len(src) - 3]
        try:
            ts = parsedate_to_datetime(it.findtext('pubDate'))
        except Exception:
            ts = datetime.now(timezone.utc)
        yield {'title': title, 'source': src, 'link': (it.findtext('link') or '').strip(), 'guid': (it.findtext('guid') or it.findtext('link') or title), 'ts': ts}

def norm(t):
    return re.sub(r'[\W_]+', '', t).lower()

def send(text):
  for target in [x.strip() for x in chat.split(',') if x.strip()]:
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
        data=json.dumps({'chat_id': target, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        if not json.load(r).get('ok'):
            raise RuntimeError('telegram send failed')

def main():
    first = not os.path.exists(STATE)
    seen = {} if first else json.load(open(STATE, encoding='utf-8'))
    now = datetime.now(timezone.utc)
    new = []
    for label, inc, exc in keywords():
        try:
            items = list(fetch(' '.join(inc) + ''.join(f' -{x}' for x in exc)))
        except Exception as e:
            print(f'[{label}] 검색 실패: {e}'); continue
        for a in items:
            key, tkey = a['guid'], norm(a['title'])
            if key in seen or tkey in seen:
                continue
            seen[key] = seen[tkey] = now.isoformat()
            if any(x in a['title'] for x in exc):
                continue
            if not first and now - a['ts'] <= timedelta(hours=MAX_AGE_H):
                new.append((label, a))
        time.sleep(1)
    cutoff = (now - timedelta(days=7)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    os.makedirs('.state', exist_ok=True)
    json.dump(seen, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False)
    if first:
        print(f'첫 실행: 기존 기사 {len(seen)}건을 기록만 했습니다(전송 안 함).'); return
    if not new:
        print('새 기사 없음'); return
    if not token or not chat:
        sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다.')
    new.sort(key=lambda x: x[1]['ts'])
    for label, a in new[:MAX_PER_RUN]:
        t = a['ts'].astimezone(KST).strftime('%m/%d %H:%M')
        send(f"🔔 <b>[{html.escape(label)}]</b> {html.escape(a['title'])}\n{html.escape(a['source'])} · {t} · <a href=\"{html.escape(a['link'], quote=True)}\">기사보기</a>")
        time.sleep(1.2)
    if len(new) > MAX_PER_RUN:
        send(f"…외 {len(new) - MAX_PER_RUN}건은 생략했습니다.")
    print(f'sent {min(len(new), MAX_PER_RUN)} / {len(new)}')

if __name__ == '__main__':
    main()
