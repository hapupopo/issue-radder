#!/usr/bin/env python3
"""봇이 받은 최근 메시지에서 채팅 ID를 찾아 Actions 로그에 출력한다(토큰은 출력하지 않음)."""
import json, os, sys, urllib.request, urllib.error
token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
if not token:
    sys.exit('TELEGRAM_BOT_TOKEN 시크릿을 먼저 등록하세요.')
if token.lower().startswith('bot'):
    token = token[3:]
def call(m):
    try:
        with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/{m}') as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)
me = call('getMe')
if not me.get('ok'):
    sys.exit(f"토큰이 올바르지 않습니다: {me.get('description')} — BotFather가 준 토큰 전체(숫자:문자)를 공백 없이 다시 등록하세요.")
print(f"봇 확인: @{me['result']['username']}")
call('deleteWebhook')
up = call('getUpdates')
chats = {}
for u in up.get('result', []):
    for k in ('message', 'channel_post', 'my_chat_member', 'edited_message'):
        c = (u.get(k) or {}).get('chat')
        if c:
            chats[c['id']] = c.get('title') or c.get('username') or c.get('first_name') or ''
if not chats:
    print('아직 받은 메시지가 없습니다. 봇에게(또는 봇이 있는 단톡방에서) "/start" 를 보낸 뒤 다시 실행하세요.')
    print('단톡방이면 "/start@봇아이디" 처럼 봇을 지정해서 보내야 합니다.')
    sys.exit(1)
print('찾은 채팅 (이 숫자를 TELEGRAM_CHAT_ID 시크릿에 등록):')
for i, t in chats.items():
    print(f'  {i}  {t}')
