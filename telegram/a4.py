#!/usr/bin/env python3
"""텔레그램용 'A4 1장 요약' HTML 생성 (이미지는 scripts/render_a4.js 가 만든다).

입력: data/DAY/*.json (+ 선택: data/DAY/a4.json {"key": [{"head": "...", "body": "..."}] } — '오늘의 핵심' 3줄)
출력: telegram/a4/latest.html
사용: python3 telegram/a4.py [YYYY-MM-DD]
"""
import json, sys, html, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build import DATA, FILES, SITE, d, fmt, diff, load, is_today_news  # noqa: E402

e = lambda s: html.escape(str(s or ''), quote=True)
WD = '월화수목금토일'


def cut(s, n):
    s = (s or '').strip()
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def diverse(rows, per):
    """같은 키워드가 한쪽에 몰리지 않도록 키워드별 per건까지만 먼저 고르고, 남는 자리는 나머지로 채운다."""
    cnt, first, rest = {}, [], []
    for r in rows:
        k = r.get('keyword')
        (first if cnt.get(k, 0) < per else rest).append(r)
        cnt[k] = cnt.get(k, 0) + 1
    return first + rest


def latest_day():
    return sorted(p.name for p in DATA.iterdir() if p.is_dir() and all((p / f'{f}.json').exists() for f in FILES))[-1]


def make(day):
    D = load(day)
    x = d(day)
    week_ago = (x - dt.timedelta(days=7)).isoformat()
    sig_cls = {'유의': 'y', '기회': 'g', '관찰': 'o'}
    rank = {'유의': 0, '기회': 1, '관찰': 2}

    # 오늘의 핵심: a4.json 이 있으면 그것, 없으면 최근 집중이슈(유의·기회 우선) 3건
    kp = DATA / day / 'a4.json'
    key = json.load(open(kp, encoding='utf-8')).get('key', []) if kp.exists() else []
    focus = [r for r in D['focus'] if r.get('date') and week_ago <= r['date'] <= day]
    if not key:
        pick = diverse(sorted(focus, key=lambda r: (rank.get(r['signal'], 9), -d(r['date']).toordinal())), 1)[:3]
        key = [{'head': r['title'], 'body': cut(r.get('summary'), 60)} for r in pick]
    s_key = ''.join(f'<li><span class="n">{i + 1}</span><span><b>{e(k["head"])}</b>{(" — " + e(k["body"])) if k.get("body") else ""}</span></li>' for i, k in enumerate(key[:3]))

    # 금일 일정
    tkey = lambda r: (r.get('time') or '99:99')
    today = sorted(D['today'], key=tkey)[:8]
    s_today = ''.join(f'<tr><td class="t">{("<b>" + e(r["time"]) + "</b>") if r.get("time") else "종일"}</td><td><span class="who">{e(r["org"])}</span> {e(cut(r["title"], 48))}{(" (" + e(r["place"]) + ")") if r.get("place") else ""}</td></tr>' for r in today)

    # 이번 주 부처 일정(내일~6일 뒤)
    end = (x + dt.timedelta(days=6)).isoformat()
    mins = sorted([r for r in D['ministry'] if day < r['date'] <= end], key=lambda r: (r['date'], r.get('time') or '99'))
    mins = sorted(mins, key=lambda r: (0 if r.get('cj') else 1, r['date'], r.get('time') or '99'))[:7]
    mins = sorted(mins, key=lambda r: (r['date'], r.get('time') or '99'))
    s_min = ''.join(f'<tr><td class="t"><b>{fmt(r["date"])}</b></td><td>{"<span class=cj>CJ</span>" if r.get("cj") else ""}<span class="who">{e(r["org"])}</span> {e(cut(r["title"], 46))}</td></tr>' for r in mins)

    # 국회: 2주 이내 + 필수 30일
    asm = [r for r in D['assembly'] if (n := diff(day, r['date'])) is not None and n > 0 and (n <= 14 or (r.get('must') and n <= 30))]
    asm = sorted(asm, key=lambda r: r['date'])[:7]
    s_asm = ''.join(f'<tr><td class="t"><b>{fmt(r["date"])}</b><span class="dd">D-{diff(day, r["date"])}</span></td><td>{e(cut(r["title"], 40))}{"<span class=must>필수</span>" if r.get("must") else ""}</td></tr>' for r in asm)

    # 집중이슈: 최근 7일, 유의·기회 우선
    fx = diverse(sorted(focus, key=lambda r: (rank.get(r['signal'], 9), -d(r['date']).toordinal())), 2)[:6]
    s_focus = ''.join(f'<div class="iss"><span class="tag {sig_cls.get(r["signal"], "o")}">{e(r["signal"])}</span><b>{e(cut(r["title"], 42))}</b><p>{e(cut(r.get("summary"), 80))}</p></div>' for r in fx)

    # 오늘 기사
    news = sorted([r for r in D['news'] if is_today_news(r, day)], key=lambda r: r['date'] + (r.get('time') or ''), reverse=True)[:5]
    s_news = ''.join(f'<li>{e(cut(r["title"], 52))} <em>{e(r["outlet"])}</em></li>' for r in news) or '<li>오늘 기사 없음</li>'

    # 지원사업·R&D: 마감 남은 것 + 예정
    def nxt(r):
        c, o = r.get('close'), r.get('open')
        if c and len(c) == 10 and c >= day:
            return c, fmt(c)
        if o and o > day[:len(o)]:
            return (o + '-99')[:10], (fmt(o) + (' 예상' if len(o) == 7 else '')).replace('월 중 예상', '월 예상')
        return None
    sup = sorted([(k, r) for r in D['support'] if (k := nxt(r))], key=lambda kr: kr[0][0])[:3]
    s_sup = ''.join(f'<tr><td class="t"><b>{e(k[1])}</b></td><td>{e(cut(r["name"], 44))}</td></tr>' for k, r in sup) or '<tr><td>다가오는 일정 없음</td></tr>'

    date_txt = f'{x.year}. {x.month}. {x.day}.({WD[x.weekday()]})'
    box = lambda t, sub, body, tbl=True: f'<div class="box"><h3>{t} <span>{sub}</span></h3>{"<table>" + body + "</table>" if tbl else body}</div>' if body else ''
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>이슈레이더 A4 {day}</title><style>{CSS}</style></head><body>
<header><h1>전략지원 이슈레이더<small>데일리 1장 요약</small></h1><div class="date"><b>{date_txt}</b>정부·국회·언론 공개자료 기준</div></header>
{f'<section class="key"><h2>오늘의 핵심</h2><ol>{s_key}</ol></section>' if s_key else ''}
<div class="cols"><div class="col">
{box('금일 정부·국회 일정', fmt(day), s_today)}
{box('이번 주 부처 일정', '당사 관련', s_min)}
{box('국회 주요 일정', '<span class="must">필수</span> 꼭 챙길 일정', s_asm)}
</div><div class="col">
{box('집중이슈', '유의 · 기회 · 관찰', s_focus, False)}
{box('오늘의 주요 기사', '전일 12시 이후', '<ul class="news">' + s_news + '</ul>', False)}
{box('지원사업 · R&amp;D', '다가오는 일정', s_sup)}
</div></div>
<footer><span>CJ제일제당 전략지원부문 정책협력팀 · 공개자료를 요약한 내부 참고용 자료입니다.</span><span>전체 리포트 {SITE.replace("https://", "")}</span></footer>
<script>/* A4 한 장에 맞을 때까지 글자 크기를 줄인다 */
(function(){{var s=12.2;var b=document.body;function over(){{return [].some.call(document.querySelectorAll('.col'),function(c){{return c.scrollHeight>c.clientHeight+1}})||b.scrollHeight>1123}}
while(over()&&s>8.5){{s-=0.2;b.style.fontSize=s+'px'}}document.documentElement.dataset.fit=s}})();</script>
</body></html>'''


CSS = '''
@page{size:A4;margin:0}
:root{--fg:#1f1e1b;--mut:#6b6862;--line:#e4e1d8;--warn:#b26b00;--ok:#1d7a46;--cj:#6a3fb5;--navy:#1f2a44}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#fff}
body{width:794px;height:1123px;overflow:hidden;color:var(--fg);font-family:"Noto Sans CJK KR","Noto Sans KR","Pretendard",sans-serif;font-size:12.2px;line-height:1.5;padding:30px 34px 22px;display:flex;flex-direction:column;gap:1em}
header{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2.5px solid var(--navy);padding-bottom:8px}
h1{font-size:22px;font-weight:800;color:var(--navy);letter-spacing:-.5px}h1 small{font-size:12px;font-weight:500;color:var(--mut);margin-left:8px}
.date{text-align:right;font-size:11px;color:var(--mut)}.date b{display:block;font-size:17px;color:var(--fg)}
.key{background:var(--navy);color:#fff;border-radius:8px;padding:.9em 1.2em}
.key h2{font-size:.9em;letter-spacing:1px;opacity:.75;margin-bottom:.4em;font-weight:600}
.key ol{list-style:none;display:flex;flex-direction:column;gap:.4em}
.key li{display:flex;gap:.6em;font-size:1.06em}.key li b{font-weight:700}
.key .n{flex:none;width:1.4em;height:1.4em;border-radius:50%;background:#fff;color:var(--navy);font-weight:800;font-size:.8em;display:flex;align-items:center;justify-content:center;margin-top:.15em}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:1;min-height:0}
.col{display:flex;flex-direction:column;gap:.85em;min-height:0;overflow:hidden}
.box{border:1px solid var(--line);border-radius:8px;padding:.75em .95em}
.box h3{font-size:1.1em;font-weight:800;color:var(--navy);margin-bottom:.4em;display:flex;justify-content:space-between;align-items:baseline}
.box h3>span{font-size:.72em;font-weight:500;color:var(--mut)}
table{width:100%;border-collapse:collapse}td{padding:.38em 0;border-top:1px solid var(--line);vertical-align:top}tr:first-child td{border-top:0}
td.t{width:6.3em;color:var(--mut);font-variant-numeric:tabular-nums;white-space:nowrap;padding-right:.5em}td.t b{color:var(--fg)}
.who{font-weight:700}
.dd{display:inline-block;font-size:.75em;font-weight:700;color:#b3261e;margin-left:.25em}
.must,.cj{display:inline-block;font-size:.72em;font-weight:700;color:#fff;background:var(--warn);border-radius:3px;padding:0 .35em;margin-left:.3em;vertical-align:.1em}
.cj{background:var(--cj);margin:0 .3em 0 0}
.iss{padding:.5em 0;border-top:1px solid var(--line)}.iss:first-of-type{border-top:0}
.tag{display:inline-block;font-size:.75em;font-weight:700;border-radius:3px;padding:0 .4em;margin-right:.35em;color:#fff;vertical-align:.1em}
.y{background:var(--warn)}.g{background:var(--ok)}.o{background:#8a877f}
.iss b{font-weight:700}.iss p{color:var(--mut);font-size:.9em;margin-top:.1em}
.news li{list-style:none;padding:.38em 0;border-top:1px solid var(--line)}.news li:first-child{border-top:0}.news em{font-style:normal;color:var(--mut);font-size:.8em}
footer{display:flex;justify-content:space-between;font-size:9px;color:var(--mut);border-top:1px solid var(--line);padding-top:6px}
'''


def main(day=None):
    day = day or latest_day()
    out = ROOT / 'telegram' / 'a4'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'latest.html').write_text(make(day), encoding='utf-8')
    print('a4 html for', day)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
