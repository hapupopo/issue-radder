#!/usr/bin/env python3
"""봇이 받은 업데이트에서 채널/그룹/개인 채팅 ID를 종류별로 찾아 출력한다(토큰은 출력하지 않음).
- 채널 글을 봇 대화창으로 '전달'하면 원래 채널 ID를 찾을 수 있다.
- 공개 채널은 입력값(@채널아이디)으로 바로 조회한다."""
import json, os, sys, urllib.request, urllib.error, urllib.parse
token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
want = (os.environ.get('CHANNEL') or '').strip()
if not token:
    sys.exit('TELEGRAM_BOT_TOKEN 시크릿을 먼저 등록하세요.')
if token.lower().startswith('bot'):
    token = token[3:]
def call(m, **q):
    url = f'https://api.telegram.org/bot{token}/{m}' + ('?' + urllib.parse.urlencode(q) if q else '')
    try:
        with urllib.request.urlopen(url) as r: return json.load(r)
    except urllib.error.HTTPError as e: return json.load(e)
me = call('getMe')
if not me.get('ok'):
    sys.exit(f"토큰 오류: {me.get('description')}")
bot_id = me['result']['id']
print(f"봇: @{me['result']['username']}\n")
KIND = {'channel': '채널', 'supergroup': '그룹', 'group': '그룹', 'private': '개인 대화(봇과의 1:1)'}
found = {}
def add(c, how):
    if c and c.get('id') is not None:
        found.setdefault(c['id'], (c.get('type'), c.get('title') or c.get('username') or c.get('first_name') or '', how))

if want:
    if 't.me/' in want: want = '@' + want.rstrip('/').split('/')[-1]
    if not want.startswith('@') and not want.lstrip('-').isdigit(): want = '@' + want
    r = call('getChat', chat_id=want)
    if r.get('ok'): add(r['result'], '입력한 채널 조회')
    else: print(f"입력한 채널({want}) 조회 실패: {r.get('description')} — 비공개 채널이면 아래 '전달' 방법을 쓰세요.\n")

call('deleteWebhook')
for u in call('getUpdates').get('result', []):
    for k in ('channel_post', 'edited_channel_post', 'my_chat_member', 'message', 'edited_message'):
        m = u.get(k) or {}
        add(m.get('chat'), '채널 글' if 'channel' in k else ('봇 권한 변경' if k == 'my_chat_member' else '메시지'))
        add(m.get('forward_from_chat'), '전달된 채널 글')
        add((m.get('forward_origin') or {}).get('chat'), '전달된 채널 글')

chans = {i: v for i, v in found.items() if v[0] == 'channel'}
for i, (t, name, how) in sorted(found.items(), key=lambda x: x[1][0] != 'channel'):
    print(f"[{KIND.get(t, t)}] {name}  →  {i}   ({how})")
print()
if not chans:
    print('채널을 찾지 못했습니다. 아래 중 하나를 한 뒤 다시 실행하세요.')
    print(' ① 채널의 아무 글을 길게 눌러 [전달] → 봇 대화창으로 보내기  (가장 확실)')
    print(' ② 봇을 채널 관리자(메시지 게시 권한)로 추가한 "후에" 채널에 새 글 올리기')
    print(' ③ 공개 채널이면 Run workflow 입력칸에 @채널아이디 입력')
    sys.exit(1)
for i, (t, name, how) in chans.items():
    st = call('getChatMember', chat_id=i, user_id=bot_id)
    status = (st.get('result') or {}).get('status')
    ok = status in ('administrator', 'creator') and (st['result'].get('can_post_messages', True) is not False)
    print(f"채널 '{name}' ID = {i}  → TELEGRAM_CHAT_ID 에 이 숫자를 등록하세요." + ('' if ok else f"\n  ※ 봇이 아직 이 채널 관리자가 아닙니다(상태: {status}). 관리자 추가 + '메시지 게시' 권한을 켜세요."))
