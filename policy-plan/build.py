"""정책협력팀 업무계획 툴 → GitHub Pages 정적판 생성.
source.html(원본 Claude 아티팩트와 같은 코드) + snapshot.json(기준 데이터)
→ docs/policy-plan/index.html
실행: python3 policy-plan/build.py
"""
import json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / 'docs' / 'policy-plan' / 'index.html'
src = (HERE / 'source.html').read_text(encoding='utf-8')
snap = json.loads((HERE / 'snapshot.json').read_text(encoding='utf-8'))
payload = json.dumps(snap, ensure_ascii=False).replace('</', '<\\/')
head = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="robots" content="noindex,nofollow">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>'
        '</head><body>')
html = head + f'<script>window.PP_SNAPSHOT={payload};</script>\n' + src + '\n</body></html>'
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding='utf-8')
print('wrote', OUT, len(html), 'bytes')
