#!/usr/bin/env python3
"""텔레그램용 '카드뉴스' 4장 HTML 생성 — A4 1장 대신 휴대폰에서 넘겨 보는 형태.

카드 ① 오늘의 핵심 ② 오늘 주요일정 | 이번 주 주요일정 ③ 집중이슈 ④ 오늘의 주요기사 + 링크 안내
항목 고르는 기준은 telegram/a4.py 와 같다(같은 데이터·같은 우선순위).
출력: telegram/cards/card-1.html … card-4.html  (PNG 는 scripts/render_cards.js)
사용: python3 telegram/cards.py [YYYY-MM-DD]
"""
import json, re, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'telegram'))
from build import DATA, SITE, d, fmt, load, in_window  # noqa: E402
from a4 import e, cut, diverse, prefer_major, is_major, _norm, same_event, is_past, latest_day, WD  # noqa: E402


def label(kw):
    """이미지에는 회사명을 쓰지 않는다(외부 유출 대비, 2026-11-23 KIM): 'CJ제일제당' 분류 → '당사 이슈'."""
    return '당사 이슈' if kw and 'CJ' in kw else kw


def pick(day):
    D = load(day)
    x = d(day)
    rank = {'유의': 0, '기회': 1, '관찰': 2}
    kp = DATA / day / 'a4.json'
    cfg = json.load(open(kp, encoding='utf-8')) if kp.exists() else {}
    key, skip = cfg.get('key', []), set(cfg.get('exclude', []))
    nmap = {r['url']: r for r in D['news'] if r.get('url')}
    D['focus'] = [dict(r, date=nmap[r['url']]['date'], time=nmap[r['url']].get('time')) if r.get('url') in nmap else r for r in D['focus']]
    focus = [r for r in D['focus'] if r.get('date') and in_window(r, day) and not is_past(r, day) and r.get('id') not in skip]
    if not key:
        key = [{'head': r['title'], 'body': cut(r.get('summary'), 60)} for r in diverse(sorted(focus, key=lambda r: (rank.get(r['signal'], 9), -d(r['date']).toordinal())), 1)[:3]]

    cat_rank = {'대통령': 0, '총리': 1, '국회': 2, '부처': 3}
    today = sorted(D['today'], key=lambda r: (cat_rank.get(r.get('cat'), 4), r.get('time') or '99:99'))

    end = (x + dt.timedelta(days=6)).isoformat()
    wk = [dict(r, who=r['org'], src='m') for r in D['ministry'] if day < r['date'] <= end]
    wk += [dict(r, who='국회', src='a') for r in D['assembly'] if day < r['date'] <= end]
    wk = [r for r in wk if not any(same_event(r['title'], t['title']) for t in D['today'])]
    prio = lambda r: (0 if (r.get('cj') or r.get('must')) else 1 if r['src'] == 'a' else 2 if r['who'] == '농식품부' else 3)
    sel = []
    for r in sorted(wk, key=lambda r: (prio(r), r['date'], r.get('time') or '99')):
        if not any(p['date'] == r['date'] and same_event(p['title'], r['title']) for p in sel):
            sel.append(r)
    wk = sorted(sel[:8], key=lambda r: (r['date'], r.get('time') or '99'))

    fx = diverse(sorted(focus, key=lambda r: (r['date'] != day, rank.get(r['signal'], 9), -d(r['date']).toordinal())), 2)
    # 주요매체 우선(2026-11-24 KIM): 출처가 주요매체인 집중이슈를 먼저, 모자라면 나머지로 채운다(순서는 원래 우선순위).
    def src(r):
        if r.get('url') in nmap:
            return nmap[r['url']].get('outlet', '')
        m = re.search(r'\(([^()]*)\)\s*$', r.get('summary') or '')
        return m.group(1) if m else ''
    mj = [r for r in fx if is_major({'outlet': src(r)})]
    keep = mj[:5] + [r for r in fx if r not in mj][:max(0, 5 - len(mj))]
    fx = [r for r in fx if r in keep]
    shown = {r.get('url') for r in fx} | {_norm(r['title']) for r in fx} | {_norm(k.get('head')) for k in key[:3]}
    news = sorted([r for r in D['news'] if in_window(r, day) and r.get('id') not in skip and r.get('url') not in shown and _norm(r['title']) not in shown],
                  key=lambda r: (r['date'] == day, r['date'] + (r.get('time') or '')), reverse=True)
    news = prefer_major(news, 6)
    return dict(key=key[:3], today=today, week=wk, focus=fx, news=news)


def page(day, n, total, title, body, dark=False):
    x = d(day)
    date_txt = f'{x.month}월 {x.day}일 ({WD[x.weekday()]})'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>이슈레이더 카드 {n}</title><style>{CSS}</style></head>
<body class="{'dark' if dark else ''}"><div class="card">
<header><span class="brand">전략지원 이슈레이더</span><span class="date">{date_txt}</span></header>
<h1>{title}</h1>
<main>{body}</main>
<footer><span>전략지원 · 공개자료 요약</span><span class="pg"><b>{n}</b> / {total}{' &nbsp;넘겨 보기 →' if n < total else ''}</span></footer>
</div>
<script>/* 카드 한 장에 맞을 때까지 글자 크기를 줄인다 */
(function(){{var m=document.querySelector('main'),s=parseFloat(getComputedStyle(document.body).fontSize);
while(m.scrollHeight>m.clientHeight+1&&s>18){{s-=1;document.body.style.fontSize=s+'px'}}document.documentElement.dataset.fit=s}})();</script>
</body></html>'''


def make(day):
    P = pick(day)
    sig = {'유의': 'y', '기회': 'g', '관찰': 'o'}
    total = 4

    # ① 오늘의 핵심
    c1 = '<ol class="key">' + ''.join(
        f'<li><span class="n">{i + 1}</span><div><b>{e(k["head"])}</b><p>{e(k.get("body"))}</p></div></li>'
        for i, k in enumerate(P['key'])) + '</ol>'
    # 표지 아래: 다음 카드 안내(무엇이 몇 건 있는지)
    c1 += ('<div class="toc"><h2>이어서 보기</h2>'
           f'<p><span>2</span>주요 일정 <em>오늘 {len(P["today"][:9])}건 · 이번 주 {len(P["week"])}건</em></p>'
           f'<p><span>3</span>집중이슈 <em>{len(P["focus"])}건</em></p>'
           f'<p><span>4</span>오늘의 주요기사 <em>{len(P["news"])}건</em></p></div>')

    # ② 오늘 주요일정 | 이번 주 주요일정
    def trow(r):
        return (f'<li><span class="t">{e(r["time"]) if r.get("time") else "종일"}</span>'
                f'<div><span class="who">{e(r["org"])}</span>{e(cut(r["title"], 40))}'
                f'{("<em>" + e(r["place"]) + "</em>") if r.get("place") else ""}</div></li>')

    def wrow(r):
        dd = d(r['date'])
        return (f'<li><span class="t">{dd.month}/{dd.day}<small>{WD[dd.weekday()]}</small></span>'
                f'<div>{"<span class=cj>그룹사</span>" if r.get("cj") else ""}{"<span class=must>필수</span>" if r.get("must") else ""}'
                f'<span class="who">{e(r["who"])}</span>{e(cut(r["title"], 40))}</div></li>')
    c2 = (f'<div class="two"><section><h2>오늘</h2><ul class="sch">{"".join(trow(r) for r in P["today"][:9])}</ul></section>'
          f'<section><h2>이번 주</h2><ul class="sch">{"".join(wrow(r) for r in P["week"]) or "<li>예정된 주요 일정 없음</li>"}</ul></section></div>')

    # ③ 집중이슈
    c3 = '<ul class="iss">' + ''.join(
        f'<li><div class="h"><span class="tag {sig.get(r["signal"], "o")}">{e(r["signal"])}</span><span class="kw">{e(label(r["keyword"]))}</span></div>'
        f'<b>{e(cut(r["title"], 44))}</b><p>{e(cut(r.get("summary"), 74))}</p></li>' for r in P['focus']) + '</ul>'

    # ④ 오늘의 주요기사 + 링크 안내
    c4 = ('<ul class="news">' + ''.join(f'<li><b>{e(cut(r["title"], 50))}</b><em>{e(r["outlet"])}</em></li>' for r in P['news'])
          + '</ul><div class="cta"><span class="ic">→</span><div><b>자세한 내용은 함께 보내드린<br>링크를 참조하세요</b>'
            '<p>기사 원문 링크 · 지원사업·R&amp;D 일정 · 인사·부고까지 리포트 전체를 볼 수 있습니다.</p></div></div>')

    return [page(day, 1, total, '오늘의 핵심', c1, dark=True),
            page(day, 2, total, '주요 일정', c2),
            page(day, 3, total, '집중이슈', c3),
            page(day, 4, total, '오늘의 주요기사', c4)]


CSS = '''
:root{--fg:#1f1e1b;--mut:#6b6862;--line:#e4e1d8;--bg:#faf8f3;--navy:#1f2a44;--warn:#b26b00;--ok:#1d7a46;--cj:#6a3fb5;--accent:#e8a33d}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif;font-size:31px;line-height:1.45;color:var(--fg);background:var(--bg);letter-spacing:-.3px}
.card{width:1080px;height:1350px;padding:64px 72px 48px;display:flex;flex-direction:column}
header{display:flex;justify-content:space-between;align-items:center;font-size:26px;color:var(--mut);font-weight:600}
.brand{color:var(--navy);font-weight:800}
h1{font-size:72px;font-weight:900;color:var(--navy);letter-spacing:-2px;margin:34px 0 34px;line-height:1.15}
h1::after{content:"";display:block;width:88px;height:9px;background:var(--accent);border-radius:5px;margin-top:22px}
main{flex:1;min-height:0;overflow:hidden}
footer{display:flex;justify-content:space-between;font-size:22px;color:var(--mut);border-top:2px solid var(--line);padding-top:20px;margin-top:18px}
.pg b{color:var(--navy)}
/* 다크(표지) */
body.dark{background:var(--navy);color:#fff}
.dark header,.dark footer{color:rgba(255,255,255,.65)}.dark .brand,.dark .pg b{color:#fff}.dark footer{border-color:rgba(255,255,255,.18)}
.dark h1{color:#fff;font-size:88px}
.key{list-style:none;display:flex;flex-direction:column;gap:1.25em;margin-top:.4em}
.key li{display:flex;gap:.7em}
.key .n{flex:none;width:1.75em;height:1.75em;border-radius:50%;background:var(--accent);color:var(--navy);font-weight:900;display:flex;align-items:center;justify-content:center;font-size:1.05em}
.key b{display:block;font-size:1.45em;font-weight:800;line-height:1.3}
.key p{color:rgba(255,255,255,.75);margin-top:.3em;font-size:1.05em}
.dark main{display:flex;flex-direction:column}
.toc{margin-top:auto;border-top:2px solid rgba(255,255,255,.18);padding-top:.9em}
.toc h2{font-size:.8em;font-weight:700;color:var(--accent);letter-spacing:1px;margin-bottom:.4em}
.toc p{font-size:.95em;font-weight:700;padding:.2em 0;display:flex;align-items:center;gap:.6em}
.toc span{width:1.5em;height:1.5em;border-radius:8px;border:2px solid rgba(255,255,255,.4);display:inline-flex;align-items:center;justify-content:center;font-size:.75em}
.toc em{font-style:normal;font-weight:400;color:rgba(255,255,255,.65);font-size:.85em}
/* 일정 */
.two{display:grid;grid-template-columns:1fr 1fr;gap:40px;height:100%;font-size:.84em}
.two h2{font-size:1.15em;font-weight:800;color:#fff;background:var(--navy);border-radius:10px;padding:.25em .7em;margin-bottom:.5em;display:inline-block}
.two section+section h2{background:var(--accent);color:var(--navy)}
.sch{list-style:none}
.sch li{display:flex;gap:.6em;padding:.5em 0;border-top:2px solid var(--line)}.sch li:first-child{border-top:0}
.sch .t{flex:none;width:3.4em;font-weight:800;color:var(--navy);font-variant-numeric:tabular-nums}
.sch .t small{font-size:.7em;color:var(--mut);margin-left:.2em;font-weight:600}
.sch .who{display:block;font-size:.78em;font-weight:700;color:var(--mut)}
.sch em{display:block;font-style:normal;font-size:.78em;color:var(--mut)}
.must,.cj{display:inline-block;font-size:.66em;font-weight:800;color:#fff;background:var(--warn);border-radius:6px;padding:0 .4em;margin-right:.35em;vertical-align:.15em}
.cj{background:var(--cj)}
/* 집중이슈 */
.iss{list-style:none;display:flex;flex-direction:column;gap:.75em}
.iss li{background:#fff;border:2px solid var(--line);border-radius:18px;padding:.6em .8em}
.iss .h{display:flex;gap:.5em;align-items:center;margin-bottom:.15em}
.tag{font-size:.72em;font-weight:800;color:#fff;border-radius:6px;padding:.05em .5em}
.y{background:var(--warn)}.g{background:var(--ok)}.o{background:#8a877f}
.kw{font-size:.72em;color:var(--mut);font-weight:700}
.iss b{display:block;font-weight:800;line-height:1.3}
.iss p{font-size:.8em;color:var(--mut);margin-top:.2em}
/* 기사 + CTA */
.news{list-style:none;counter-reset:n}
.news li{padding:.45em 0 .45em 1.6em;border-top:2px solid var(--line);position:relative;counter-increment:n}.news li:first-child{border-top:0}
.news li::before{content:counter(n);position:absolute;left:0;top:.45em;font-weight:900;color:var(--accent)}
.news b{font-weight:700;line-height:1.3}.news em{display:block;font-style:normal;color:var(--mut);font-size:.72em;margin-top:.1em}
.cta{display:flex;gap:36px;align-items:center;background:var(--navy);color:#fff;border-radius:24px;padding:30px 34px;margin-top:26px}
.cta .ic{flex:none;width:110px;height:110px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:64px;font-weight:900;color:var(--navy)}
.cta b{font-size:40px;font-weight:900;display:block;line-height:1.25}
.cta p{font-size:23px;color:rgba(255,255,255,.75);margin:.5em 0}
.cta .url{font-size:21px;color:var(--accent);font-weight:700;word-break:break-all}
'''


def main(day=None):
    day = day or latest_day()
    out = ROOT / 'telegram' / 'cards'
    out.mkdir(parents=True, exist_ok=True)
    for i, h in enumerate(make(day), 1):
        (out / f'card-{i}.html').write_text(h, encoding='utf-8')
    print('cards html for', day)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
