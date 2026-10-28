#!/usr/bin/env python3
"""docs/latest-brief.txt 를 텔레그램으로 전송 (4,000자 단위로 나눠 보냄)."""
import json, os, sys, urllib.request
token, chat = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip(), (os.environ.get('TELEGRAM_CHAT_ID') or '').strip()
token = token[3:] if token.lower().startswith('bot') else token
if not token or not chat:
    sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다.')
import html
path = sys.argv[1] if len(sys.argv) > 1 else 'docs/latest-brief.txt'
raw = open(path, encoding='utf-8').read().strip() if os.path.exists(path) else ''
if not raw:
    print(f'{path} 비어 있음 — 전송 생략'); sys.exit(0)
lines = []
for line in raw.split('\n'):
    if line.startswith('🔗 ') and line[2:].strip().startswith('http'):
        lines.append(f'🔗 <a href="{html.escape(line[2:].strip(), quote=True)}">전체보기</a>')
    else:
        lines.append(html.escape(line, quote=False))
text = '\n'.join(lines)
chunks, cur = [], ''
for line in text.split('\n'):
    if len(cur) + len(line) + 1 > 4000:
        chunks.append(cur); cur = ''
    cur += line + '\n'
chunks.append(cur)
targets = [x.strip() for x in chat.split(',') if x.strip()]
for target in targets:
  for c in chunks:
      req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
          data=json.dumps({'chat_id': target, 'text': c, 'disable_web_page_preview': True, 'parse_mode': 'HTML'}).encode(),
          headers={'Content-Type': 'application/json'})
      with urllib.request.urlopen(req) as r:
          res = json.load(r)
          if not res.get('ok'):
              sys.exit(f'전송 실패: {res}')
print(f'sent {len(chunks)} message(s) to {len(targets)} chat(s)')
