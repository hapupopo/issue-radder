#!/usr/bin/env python3
"""이미지 여러 장을 앨범 한 묶음(sendMediaGroup, 2~10장)으로 텔레그램에 전송.
사용: python3 scripts/telegram_send_album.py <이미지1> <이미지2> ...
수신처 규칙(TELEGRAM_CHAT_ID / _EXTRA / ONLY_MAIN / ONLY_EXTRA)은 telegram_send_file.py 와 같다."""
import json, os, sys, uuid, urllib.request
token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
chat = ','.join(x for x in [(os.environ.get('TELEGRAM_CHAT_ID') or '').strip(), (os.environ.get('TELEGRAM_CHAT_ID_EXTRA') or '').strip()] if x)
token = token[3:] if token.lower().startswith('bot') else token
if (os.environ.get('TELEGRAM_ONLY_MAIN') or '').lower() == 'yes':
    chat = (os.environ.get('TELEGRAM_CHAT_ID') or '').strip()
if (os.environ.get('TELEGRAM_ONLY_EXTRA') or '').lower() == 'yes':
    chat = (os.environ.get('TELEGRAM_CHAT_ID_EXTRA') or '').strip()
if not token or not chat:
    sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다.')
paths = sys.argv[1:]
if not 2 <= len(paths) <= 10 or not all(os.path.exists(p) for p in paths):
    sys.exit(f'이미지 2~10장이 필요합니다: {paths}')
files = [(f'p{i}', os.path.basename(p), open(p, 'rb').read()) for i, p in enumerate(paths)]
media = json.dumps([{'type': 'photo', 'media': f'attach://{k}'} for k, _, _ in files])
for target in list(dict.fromkeys(x.strip() for x in chat.split(',') if x.strip())):
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in [('chat_id', target), ('media', media)]]
    for k, name, data in files:
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode() + data + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMediaGroup', data=b''.join(parts),
                                 headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req) as r:
        res = json.load(r)
        if not res.get('ok'):
            sys.exit(f'전송 실패: {res}')
print(f'sent album of {len(paths)} via sendMediaGroup')
