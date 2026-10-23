#!/usr/bin/env python3
"""전략지원 이슈레이더 정적 사이트 빌더.

data/YYYY-MM-DD/{today,ministry,assembly,news,press,support,focus,people}.json
→ docs/index.html (최신), docs/reports/YYYY-MM-DD.html (날짜별), docs/archive.html
"""
import json, os, html, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA, OUT = ROOT / 'data', ROOT / 'docs'
SITE = 'https://hapupopo.github.io/issue-radder'
FILES = ['today', 'ministry', 'assembly', 'news', 'press', 'support', 'focus', 'people']
WD = '월화수목금토일'
e = lambda s: html.escape(str(s or ''), quote=True)


def d(iso):
    return dt.date.fromisoformat(iso)


def fmt(iso):
    if not iso:
        return ''
    if len(iso) == 7:
        return f"{int(iso[5:7])}월 중"
    x = d(iso)
    return f"{x.month}/{x.day}({WD[x.weekday()]})"


def diff(a, b):
    return (d(b) - d(a)).days if b and len(b) == 10 else None


def ddtxt(n):
    if n is None:
        return ''
    return '오늘' if n == 0 else (f'D-{n}' if n > 0 else '지남')


def load(day):
    return {f: json.load(open(DATA / day / f'{f}.json', encoding='utf-8')) for f in FILES}


def is_today_news(r, day):
    prev = (d(day) - dt.timedelta(days=1)).isoformat()
    return r['date'] == day or (r['date'] == prev and (r.get('time') or '') >= '12:00')


def brief(D, day):
    L = [f"📡 전략지원 이슈레이더 | {fmt(day)}", f'🔗 {SITE}/reports/{day}.html', '', '■ 정부 주요일정']
    for r in [r for r in D['today'] if r.get('rel')][:8]:
        L.append(f"• {(r['time'] + ' ') if r.get('time') else ''}{r['org']} {r['title']} [{r['rel']}]")
    asm = [r for r in D['assembly'] if (n := diff(day, r['date'])) is not None and n > 0 and (n <= 14 or (r.get('must') and n <= 30))]
    if asm:
        L += ['', '■ 국회 주요일정'] + [f"• {fmt(r['date'])} {r['title']} (D-{diff(day, r['date'])})" for r in sorted(asm, key=lambda r: r['date'])]
    due = sorted([r for r in D['support'] if (n := diff(day, r.get('close'))) is not None and 0 <= n <= 45], key=lambda r: r['close'])
    if due:
        L += ['', '■ 마감·기한'] + [f"• {r['name']} ~{fmt(r['close'])} (D-{diff(day, r['close'])})" for r in due]
    tn = sorted([r for r in D['news'] if is_today_news(r, day)], key=lambda r: r['date'] + (r.get('time') or ''), reverse=True)
    if tn:
        L += ['', '■ 주요 관련기사']
        for r in tn:
            L += [f"• {r['title']} ({r['outlet']})", f"  {r['url']}"]
    return '\n'.join(L)


def item(meta, title, url='', sub='', rel='', cls=''):
    m = ''.join(f'<span>{x}</span>' for x in meta if x)
    if rel:
        m += f'<span class="tag rel">{e(rel)}</span>'
    t = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(title)}</a>' if url else e(title)
    s = f'<div class="sub">{e(sub)}</div>' if sub else ''
    return f'<div class="it{" rel" if rel else ""}{(" " + cls) if cls else ""}"><div class="meta">{m}</div><div class="tt">{t}</div>{s}</div>'


def section(id_, title, note, body, extra=''):
    return f'<section class="card" id="{id_}"><h2>{title}{extra}</h2><p class="note">{note}</p><div class="list">{body or "<div class=empty>해당 없음</div>"}</div></section>'


def render(day, D, days):
    b = lambda s: f'<b>{e(s)}</b>'
    tag = lambda s, c='': f'<span class="tag {c}">{e(s)}</span>'
    today_rows = D['today']
    prev = (d(day) - dt.timedelta(days=1)).isoformat()
    week_ago = (d(day) - dt.timedelta(days=7)).isoformat()
    news7 = sorted([r for r in D['news'] if r['date'] >= week_ago], key=lambda r: r['date'] + (r.get('time') or ''), reverse=True)
    today_news = [r for r in news7 if is_today_news(r, day)]
    due = [r for r in D['support'] if (n := diff(day, r.get('close'))) is not None and 0 <= n <= 14]

    s_today = ''.join(item([b(r['org']), e(r.get('time')), e(r.get('place'))], r['title'], r.get('url'), r.get('note'), r.get('rel')) for r in today_rows)

    mins, cur = '', None
    for r in sorted(D['ministry'], key=lambda r: (r['date'], r.get('time') or '99'), reverse=False)[::-1]:
        if r['date'] != cur:
            cur = r['date']; mins += f'<div class="day">{fmt(cur)}{" · 오늘" if cur == day else ""}</div>'
        mins += item([b(r['org']), e(r.get('time'))], r['title'], r.get('url'), r.get('why'), r.get('rel'), 'past' if r['date'] < day else '')

    asm = sorted(D['assembly'], key=lambda r: r['date'] + ('-31' if len(r['date']) == 7 else ''))
    up = [r for r in asm if (diff(day, r['date']) is None or diff(day, r['date']) >= 0)]
    past = [r for r in asm if r not in up][::-1]
    s_asm = ''.join(item([b(fmt(r['date'])), f'<span class="dd">{ddtxt(diff(day, r["date"]))}</span>', tag(r['type'])], r['title'], r.get('url'), r.get('detail'), r.get('rel'), 'past' if r in past else '') for r in up + past)

    s_news = ''.join(item([b(fmt(r['date']) + (' ' + r['time'] if r.get('time') else '')), e(r['outlet']), tag(r['scope']), e(r['issue'])], r['title'], r['url'], cls='today' if r in today_news else '') for r in news7)

    s_press = ''.join(item([b(r['org']), fmt(r['date'])], r['title'], r['url'], r.get('why')) for r in sorted(D['press'], key=lambda r: r['date'], reverse=True))

    def st(r):
        n, o = diff(day, r.get('close')), diff(day, r.get('open'))
        if n is not None and n < 0: return '마감'
        if o is not None and o > 0: return '예정'
        if not r.get('close') and r.get('open') and len(r['open']) == 7: return '예정'
        if not r.get('close') and not r.get('open'): return '확인 필요'
        return '진행·접수'
    order = {'진행·접수': 0, '예정': 1, '확인 필요': 2, '마감': 3}
    sup = sorted(D['support'], key=lambda r: (order[st(r)], diff(day, r.get('close')) if diff(day, r.get('close')) is not None else 9999))
    s_sup = ''
    for r in sup:
        n = diff(day, r.get('close'))
        per = (fmt(r.get('open')) + (' ~ ' + fmt(r['close']) if r.get('close') else '')).strip()
        dd = f'<span class="dd hot">{ddtxt(n)}</span>' if st(r) == '진행·접수' and n is not None and n <= 60 else ''
        s_sup += item([tag(st(r), 'opp' if st(r) == '진행·접수' else ''), b(r['type']), dd, e(per)], r['name'], r.get('url'), r['agency'] + (' · ' + r['note'] if r.get('note') else ''), r.get('rel'), 'past' if st(r) == '마감' else '')

    rank = {'유의': 0, '기회': 1, '관찰': 2}
    sig = {'유의': 'risk', '기회': 'opp', '관찰': ''}
    s_focus = ''.join(item([tag(r['signal'], sig.get(r['signal'], '')), b(r['keyword']), e(r['kind']), fmt(r.get('date'))], r['title'], r.get('url'), r.get('summary'))
                      for r in sorted(D['focus'], key=lambda r: (rank.get(r['signal'], 9), -(d(r['date']).toordinal() if r.get('date') else 0))))
    s_people = ''.join(item([tag(r['kind'], 'risk' if r['kind'] == '부고' else ''), b(r['org']), fmt(r['date'])], r['detail'], r.get('url')) for r in sorted(D['people'], key=lambda r: r['date'], reverse=True))

    br = brief(D, day)
    i = days.index(day)
    newer = days[i - 1] if i > 0 else None
    older = days[i + 1] if i + 1 < len(days) else None
    pager = (f'<a href="{newer}.html">← {fmt(newer)}</a>' if newer else '<span></span>') + '<a href="../archive.html">전체 리포트</a>' + (f'<a href="{older}.html">{fmt(older)} →</a>' if older else '<span></span>')

    kpi = [('오늘 당사 관련 일정', sum(1 for r in today_rows if r.get('rel')), '#today'),
           ('마감·기한 D-14 이내', len(due), '#support'),
           ('오늘 주요 관련기사', len(today_news), '#news'),
           ('최근 7일 기사', len(news7), '#news')]
    kpis = ''.join(f'<a class="card kpi" href="{h}"><div class="lab">{l}</div><div class="big">{v}</div></a>' for l, v, h in kpi)

    body = f'''
<header><h1>전략지원 이슈레이더</h1><div class="asof">{fmt(day)} 데일리 리포트 · 정부·국회·언론 공개자료</div></header>
<div class="kpis">{kpis}</div>
<nav class="jump"><a href="#brief">공유</a><a href="#today">금일 일정</a><a href="#ministry">부처 일정</a><a href="#assembly">국회동향</a><a href="#news">주요기사</a><a href="#press">보도자료</a><a href="#support">지원사업·R&amp;D</a><a href="#focus">집중이슈</a><a href="#people">인사·부고</a><a href="../archive.html">지난 리포트</a></nav>
<section class="card" id="brief"><h2>오늘의 브리핑 <span class="n">텔레그램 공유용</span></h2><pre id="bt">{e(br)}</pre>
<div class="btns"><button class="btn primary" id="share">공유하기</button><button class="btn" id="copy">복사</button></div></section>
{section('today', '금일 정부·국회 주요일정', '대통령·총리는 전체, 부처는 당사·그룹 관련만. 노란 선은 당사 연결 이슈.', s_today)}
{section('ministry', '정부 부처별 주요일정', '이투데이 경제·사회부처 주간 일정 중 당사 관련 항목 요약.', mins)}
{section('assembly', '국회동향', '국감 · 예결위 · 정기국회 · 국회 주최 행사 · 관련 세미나.', s_asm)}
{section('news', '주요기사 모니터링', '최근 7일. 굵은 테두리는 오늘 기사(전일 12시 이후 석간 포함).', s_news)}
{section('press', '정부기관 보도자료', '대한민국 정책브리핑 등 당사 직접 관련 자료.', s_press)}
{section('support', '지원사업 · R&amp;D 일정', "접수·마감 순. '예정'은 전년 일정 기준 추정.", s_sup)}
{section('focus', '키워드 집중이슈', '식품물가 · 생분해/PHA · 정부 R&amp;D · 가공식품 수출 · 육상김 · 김 수출 · CJ제일제당', s_focus)}
{section('people', '주요 인사 · 부고', '관련 부처·상임위.', s_people)}
<nav class="pager">{pager}</nav>
<p class="foot">공개자료를 자동 수집·요약한 내부 참고용 리포트입니다. 원문 링크로 사실을 확인하세요.</p>'''
    return page(f'이슈레이더 {fmt(day)}', body, depth=1)


CSS = '''
:root{--bg:#f7f6f2;--panel:#fff;--fg:#1f1e1b;--muted:#6b6862;--line:#e4e1d8;--warn:#b26b00;--bad:#b3261e;--ok:#1d7a46;--r:10px}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#1b1a18;--panel:#24231f;--fg:#ecebe6;--muted:#a7a49c;--line:#3a3833;--warn:#e0a03a;--bad:#ef7a70;--ok:#5cc28a}}
:root[data-theme=dark]{--bg:#1b1a18;--panel:#24231f;--fg:#ecebe6;--muted:#a7a49c;--line:#3a3833;--warn:#e0a03a;--bad:#ef7a70;--ok:#5cc28a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:"Pretendard",-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:15px;line-height:1.5;-webkit-text-size-adjust:100%}
.wrap{max-width:720px;margin:0 auto;padding:16px 16px 56px;display:flex;flex-direction:column;gap:12px}
h1{font-family:"Noto Serif KR",Georgia,serif;font-weight:500;font-size:24px;margin:0}.asof{font-size:12px;color:var(--muted)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:14px;min-width:0}
.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}@media(min-width:600px){.kpis{grid-template-columns:repeat(4,1fr)}}
.kpi{padding:10px 14px;text-decoration:none;color:inherit}.kpi .lab{font-size:12px;color:var(--muted)}.kpi .big{font-family:Georgia,serif;font-size:26px;font-variant-numeric:tabular-nums}
nav.jump{position:sticky;top:0;z-index:3;background:var(--bg);display:flex;gap:6px;overflow-x:auto;padding:8px 0;border-bottom:1px solid var(--line);scrollbar-width:none}nav.jump::-webkit-scrollbar{display:none}
nav.jump a{flex:none;font-size:12px;padding:4px 12px;border:1px solid var(--line);border-radius:999px;color:var(--fg);text-decoration:none}
section{scroll-margin-top:52px}h2{font-size:16px;font-weight:600;margin:0}h2 .n{font-size:12px;color:var(--muted);font-weight:400;margin-left:6px}
.note{font-size:12px;color:var(--muted);margin:4px 0 8px}
.it{padding:10px 0 10px 10px;border-top:1px solid var(--line);border-left:3px solid transparent}.it:first-child{border-top:0}.it.rel{border-left-color:var(--warn)}.it.past{opacity:.55}.it.today{border-left-color:var(--fg)}
.meta{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;font-variant-numeric:tabular-nums}.meta b{color:var(--fg);font-weight:600}
.tt{margin-top:2px}.tt a{color:var(--fg);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}.sub{font-size:12.5px;color:var(--muted);margin-top:2px}
.tag{display:inline-block;font-size:11.5px;padding:0 7px;border-radius:999px;border:1px solid var(--line);color:var(--fg)}.tag.rel{border-color:var(--warn);color:var(--warn)}.tag.risk{border-color:var(--bad);color:var(--bad)}.tag.opp{border-color:var(--ok);color:var(--ok)}
.dd{font-weight:600}.dd.hot{color:var(--bad)}.day{font-size:12px;font-weight:600;padding:10px 0 2px;border-top:1px solid var(--line)}.day:first-child{border-top:0;padding-top:0}
pre{white-space:pre-wrap;word-break:break-all;font-family:inherit;font-size:12.5px;line-height:1.6;margin:8px 0 0;max-height:300px;overflow:auto;padding:10px;background:var(--bg);border:1px solid var(--line);border-radius:var(--r)}
.btns{display:flex;gap:8px;margin-top:8px}.btn{flex:1;font:inherit;font-size:13px;padding:10px;border-radius:var(--r);border:1px solid var(--line);background:var(--bg);color:var(--fg)}.btn.primary{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.pager{display:flex;justify-content:space-between;font-size:13px}.pager a{color:var(--fg)}.foot{font-size:12px;color:var(--muted)}.empty{font-size:13px;color:var(--muted);padding:8px 0}
.arch a{display:flex;justify-content:space-between;padding:12px 0;border-top:1px solid var(--line);color:var(--fg);text-decoration:none}.arch a:first-child{border-top:0}
'''
JS = '''<script>
(function(){var t=document.getElementById('bt');if(!t)return;var txt=t.textContent;
function done(b,m,o){b.textContent=m;setTimeout(function(){b.textContent=o},2000)}
document.getElementById('copy').onclick=function(){var b=this;(navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject()).then(function(){done(b,'복사됨','복사')},function(){var r=document.createRange();r.selectNodeContents(t);var s=getSelection();s.removeAllRanges();s.addRange(r);try{document.execCommand('copy');done(b,'복사됨','복사')}catch(e){done(b,'길게 눌러 복사','복사')}})};
document.getElementById('share').onclick=function(){var b=this;if(navigator.share){navigator.share({title:'전략지원 이슈레이더',text:txt}).catch(function(){});return}
location.href='https://t.me/share/url?url='+encodeURIComponent(location.href)+'&text='+encodeURIComponent(txt)};})();
</script>'''


def page(title, body, depth=0):
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#1f1e1b"><title>{e(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">{body}</div>{JS}</body></html>'''


def main():
    days = sorted([p.name for p in DATA.iterdir() if p.is_dir() and all((p / f'{f}.json').exists() for f in FILES)], reverse=True)
    (OUT / 'reports').mkdir(parents=True, exist_ok=True)
    for day in days:
        (OUT / 'reports' / f'{day}.html').write_text(render(day, load(day), days), encoding='utf-8')
    latest = days[0]
    idx = (OUT / 'reports' / f'{latest}.html').read_text(encoding='utf-8').replace('href="../archive.html"', 'href="archive.html"').replace(f'href="{days[1]}.html"' if len(days) > 1 else '\0', f'href="reports/{days[1]}.html"' if len(days) > 1 else '\0')
    (OUT / 'index.html').write_text(idx, encoding='utf-8')
    rows = ''.join(f'<a href="reports/{x}.html"><span>{fmt(x)} 데일리 리포트</span><span>{x}</span></a>' for x in days)
    (OUT / 'archive.html').write_text(page('이슈레이더 지난 리포트', f'<header><h1>지난 리포트</h1><div class="asof">총 {len(days)}건 · <a href="index.html">최신 리포트</a></div></header><div class="card arch">{rows}</div>'), encoding='utf-8')
    (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    (OUT / '.nojekyll').write_text('', encoding='utf-8')
    (OUT / 'latest-brief.txt').write_text(brief(load(latest), latest) + '\n', encoding='utf-8')
    print('built', len(days), 'reports; latest', latest)


if __name__ == '__main__':
    main()
