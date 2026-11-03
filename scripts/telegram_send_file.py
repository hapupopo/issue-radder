#!/usr/bin/env python3
"""이미지(sendPhoto) 또는 PDF 등 파일(sendDocument)을 텔레그램으로 전송.
사용: python3 scripts/telegram_send_file.py <파일경로> [캡션]
TELEGRAM_CHAT_ID 가 쉼표로 여러 개면 모두에게 보냄."""
import json, os, sys, uuid, urllib.request
token = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
# 기본 채널(TELEGRAM_CHAT_ID)에 추가 수신처(TELEGRAM_CHAT_ID_EXTRA, 쉼표로 여러 개)를 더해 모두에게 보낸다
chat = ','.join(x for x in [(os.environ.get('TELEGRAM_CHAT_ID') or '').strip(), (os.environ.get('TELEGRAM_CHAT_ID_EXTRA') or '').strip()] if x)
token = token[3:] if token.lower().startswith('bot') else token
if not token or not chat:
    sys.exit('TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 시크릿이 없습니다.')
path = sys.argv[1]
caption = sys.argv[2] if len(sys.argv) > 2 else ''
if not os.path.exists(path):
    sys.exit(f'{path} 없음')
photo = path.lower().endswith(('.png', '.jpg', '.jpeg'))
method, field = ('sendPhoto', 'photo') if photo else ('sendDocument', 'document')
data = open(path, 'rb').read()
for target in list(dict.fromkeys(x.strip() for x in chat.split(',') if x.strip())):
    b = uuid.uuid4().hex
    parts = []
    for k, v in [('chat_id', target), ('caption', caption)]:
        if v:
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(path)}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + data + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}', data=b''.join(parts),
                                 headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    with urllib.request.urlopen(req) as r:
        res = json.load(r)
        if not res.get('ok'):
            sys.exit(f'전송 실패: {res}')
print(f'sent {path} via {method}')
