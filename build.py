#!/usr/bin/env python3
"""전략지원 이슈레이더 정적 사이트 빌더.

data/YYYY-MM-DD/{today,ministry,assembly,news,press,support,focus,people}.json
→ docs/index.html (최신), docs/reports/YYYY-MM-DD.html (날짜별), docs/archive.html
텔레그램 공유 텍스트는 이 사이트에 넣지 않는다 → telegram_text.py 가 telegram/ 에 따로 만든다.
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


def item(meta, title, url='', sub='', rel='', cls=''):
    m = ''.join(f'<span>{x}</span>' for x in meta if x)
    if rel:
        m += f'<span class="tag rel">{e(rel)}</span>'
    t = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(title)}</a>' if url else e(title)
    s = f'<div class="sub">{e(sub)}</div>' if sub else ''
    return f'<div class="it{" rel" if rel else ""}{(" " + cls) if cls else ""}"><div class="meta">{m}</div><div class="tt">{t}</div>{s}</div>'


def section(id_, title, note, body, count=None, open_=True):
    """섹션 전체를 접고 펼 수 있는 카드. 제목 옆에 건수를 보여준다."""
    n = f' <span class="cnt">{count}</span>' if count is not None else ''
    return (f'<section class="card" id="{id_}"><details class="sec"{" open" if open_ else ""}><summary><h2>{title}{n}</h2></summary>'
            f'<p class="note">{note}</p><div class="list">{body or "<div class=empty>해당 없음</div>"}</div></details></section>')


def more(items, label):
    """접힌 '더보기' 묶음. items 가 비면 빈 문자열."""
    if not items:
        return ''
    return f'<details class="more"><summary>{label} {len(items)}건</summary>{"".join(items)}</details>'


def fold(items, n, label='더보기'):
    """앞의 n건만 펼치고 나머지는 접는다."""
    return ''.join(items[:n]) + more(items[n:], label)


def grouped(rows, key, render_one, label_fmt='{k}'):
    """rows 를 key 별로 묶어 각각 접힌 묶음으로 보여준다(건수 많은 순)."""
    g = {}
    for r in rows:
        g.setdefault(key(r) or '기타', []).append(r)
    return ''.join(more([render_one(r) for r in v], label_fmt.format(k=k)) for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])))


def render(day, D, days):
    b = lambda s: f'<b>{e(s)}</b>'
    tag = lambda s, c='': f'<span class="tag {c}">{e(s)}</span>'
    today_rows = D['today']
    week_ago = (d(day) - dt.timedelta(days=7)).isoformat()
    news7 = sorted([r for r in D['news'] if r['date'] >= week_ago], key=lambda r: r['date'] + (r.get('time') or ''), reverse=True)
    today_news = [r for r in news7 if is_today_news(r, day)]
    due = [r for r in D['support'] if (n := diff(day, r.get('close'))) is not None and 0 <= n <= 14]

    # 금일 일정: 보통 짧으므로 전부
    s_today = ''.join(item([b(r['org']), e(r.get('time')), e(r.get('place'))], r['title'], r.get('url'), r.get('note'), r.get('rel')) for r in today_rows)

    # 부처 일정: 오늘 이후는 펼치고, 지난 날짜는 접기
    def min_rows(rows, past):
        out, cur = [], None
        for r in rows:
            if r['date'] != cur:
                cur = r['date']; out.append(f'<div class="day">{fmt(cur)}{" · 오늘" if cur == day else ""}</div>')
            cj = r.get('cj')
            out.append(item(([tag('CJ그룹 · ' + cj, 'cj')] if cj else []) + [b(r['org']), e(r.get('time'))], r['title'], r.get('url'), r.get('why'), '' if cj else r.get('rel'), ('past ' if past else '') + ('cj' if cj else '')))
        return out
    mrows = sorted(D['ministry'], key=lambda r: (r['date'], r.get('time') or '99'))
    m_up = [r for r in mrows if r['date'] >= day]
    m_past = [r for r in mrows if r['date'] < day][::-1]
    mins = (''.join(min_rows(m_up, False)) or '<div class="empty">오늘 이후 등록된 당사 관련 부처 일정 없음</div>') + more(min_rows(m_past, True), '지난 일정')

    # 국회: 2주 이내(+must 30일)는 펼치고, 그 뒤 일정과 지난 일정은 접기
    asm = sorted(D['assembly'], key=lambda r: r['date'] + ('-31' if len(r['date']) == 7 else ''))
    a_item = lambda r, cls='': item([b(fmt(r['date'])), f'<span class="dd">{ddtxt(diff(day, r["date"]))}</span>', tag(r['type'])] + ([tag('필수', 'risk')] if r.get('must') else []), r['title'], r.get('url'), r.get('detail'), r.get('rel'), cls)
    up = [r for r in asm if (diff(day, r['date']) is None or diff(day, r['date']) >= 0)]
    near = [r for r in up if (n := diff(day, r['date'])) is not None and (n <= 14 or (r.get('must') and n <= 30))]
    later = [r for r in up if r not in near]
    past = [r for r in asm if r not in up][::-1]
    s_asm = (''.join(a_item(r) for r in near) or '<div class="empty">2주 안 일정 없음</div>') + more([a_item(r) for r in later], '이후 일정') + more([a_item(r, 'past') for r in past], '지난 일정')

    # 기사: 오늘 기사만 펼치고, 나머지는 이슈별로 접기
    n_item = lambda r, cls='': item([b(fmt(r['date']) + (' ' + r['time'] if r.get('time') else '')), e(r['outlet']), tag(r['scope']), e(r['issue'])], r['title'], r['url'], cls=cls)
    s_news = ((''.join(n_item(r, 'today') for r in today_news) or '<div class="empty">오늘 기사 없음</div>')
              + '<div class="grp">최근 7일 · 이슈별</div>' + grouped([r for r in news7 if r not in today_news], lambda r: r.get('issue'), n_item))

    press = sorted(D['press'], key=lambda r: r['date'], reverse=True)
    s_press = fold([item([b(r['org']), fmt(r['date'])], r['title'], r['url'], r.get('why')) for r in press], 3)

    def st(r):
        n, o = diff(day, r.get('close')), diff(day, r.get('open'))
        if n is not None and n < 0: return '마감'
        if o is not None and o > 0: return '예정'
        if not r.get('close') and r.get('open') and len(r['open']) == 7: return '예정'
        if not r.get('close') and not r.get('open'): return '확인 필요'
        return '진행·접수'
    order = {'진행·접수': 0, '예정': 1, '확인 필요': 2, '마감': 3}
    sup = sorted(D['support'], key=lambda r: (order[st(r)], diff(day, r.get('close')) if diff(day, r.get('close')) is not None else 9999))
    def s_item(r):
        n = diff(day, r.get('close'))
        per = (fmt(r.get('open')) + (' ~ ' + fmt(r['close']) if r.get('close') else '')).strip()
        dd = f'<span class="dd hot">{ddtxt(n)}</span>' if st(r) == '진행·접수' and n is not None and n <= 60 else ''
        return item([tag(st(r), 'opp' if st(r) == '진행·접수' else ''), b(r['type']), dd, e(per)], r['name'], r.get('url'), r['agency'] + (' · ' + r['note'] if r.get('note') else ''), r.get('rel'), 'past' if st(r) == '마감' else '')
    live = [r for r in sup if st(r) in ('진행·접수', '예정')]
    s_sup = fold([s_item(r) for r in live], 4) + more([s_item(r) for r in sup if r not in live], '확인 필요·마감')

    # 집중이슈: 최근 7일 유의·기회 중 최신 5건만 펼치고, 나머지는 키워드별로 접기
    sig = {'유의': 'risk', '기회': 'opp', '관찰': ''}
    f_item = lambda r: item([tag(r['signal'], sig.get(r['signal'], '')), b(r['keyword']), e(r['kind']), fmt(r.get('date'))], r['title'], r.get('url'), r.get('summary'))
    fs = sorted(D['focus'], key=lambda r: r.get('date') or '', reverse=True)
    top = [r for r in fs if r['signal'] in ('유의', '기회') and week_ago <= (r.get('date') or '') <= day][:5]
    s_focus = ''.join(f_item(r) for r in top) + '<div class="grp">키워드별 전체</div>' + grouped([r for r in fs if r not in top], lambda r: r.get('keyword'), f_item)

    ppl = sorted(D['people'], key=lambda r: r['date'], reverse=True)
    s_people = fold([item([tag(r['kind'], 'risk' if r['kind'] == '부고' else ''), b(r['org']), fmt(r['date'])], r['detail'], r.get('url')) for r in ppl], 3)

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
<nav class="jump"><a href="#today">금일 일정</a><a href="#focus">집중이슈</a><a href="#news">주요기사</a><a href="#assembly">국회동향</a><a href="#ministry">부처 일정</a><a href="#support">지원사업·R&amp;D</a><a href="#press">보도자료</a><a href="#people">인사·부고</a><a href="../archive.html">지난 리포트</a></nav>
<p class="legend"><span class="tag risk">유의</span><span class="tag opp">기회</span><span class="tag">관찰</span><span class="tag cj">CJ그룹</span> 회색 '○건' 줄을 누르면 접힌 내용이 펼쳐집니다.</p>
{section('today', '금일 정부·국회 주요일정', '대통령·총리는 전체, 부처는 당사·그룹 관련만. 노란 선은 당사 연결 이슈.', s_today, len(today_rows))}
{section('focus', '키워드 집중이슈', '최근 7일 유의·기회 상위 5건. 나머지는 키워드별로 접어둠.', s_focus, len(D['focus']))}
{section('news', '주요기사 모니터링', '오늘 기사(전일 12시 이후 석간 포함)만 펼침. 최근 7일 기사는 이슈별로 접어둠.', s_news, len(news7))}
{section('assembly', '국회동향', '2주 안 일정(필수 행사는 30일 전부터)만 펼침.', s_asm, len(near))}
{section('ministry', '정부 부처별 주요일정', '이투데이 경제·사회부처 주간 일정 중 당사 관련. 보라색은 CJ그룹 계열사 방문·간담회.', mins, len(m_up))}
{section('support', '지원사업 · R&amp;D 일정', "진행·예정 중 마감 가까운 순. '예정'은 전년 일정 기준 추정.", s_sup, len(live))}
{section('press', '정부기관 보도자료', '대한민국 정책브리핑 등 당사 직접 관련 자료.', s_press, len(press), False)}
{section('people', '주요 인사 · 부고', '관련 부처·상임위.', s_people, len(ppl), False)}
<nav class="pager">{pager}</nav>
<p class="foot">공개자료를 자동 수집·요약한 내부 참고용 리포트입니다. 원문 링크로 사실을 확인하세요.</p>'''
    return page(f'이슈레이더 {fmt(day)}', body, depth=1)


CSS = '''
:root{--bg:#f7f6f2;--panel:#fff;--fg:#1f1e1b;--muted:#6b6862;--line:#e4e1d8;--warn:#b26b00;--bad:#b3261e;--ok:#1d7a46;--cj:#6a3fb5;--cjbg:#f4effb;--r:10px}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#1b1a18;--panel:#24231f;--fg:#ecebe6;--muted:#a7a49c;--line:#3a3833;--warn:#e0a03a;--bad:#ef7a70;--ok:#5cc28a;--cj:#b99af0;--cjbg:#2b2534}}
:root[data-theme=dark]{--bg:#1b1a18;--panel:#24231f;--fg:#ecebe6;--muted:#a7a49c;--line:#3a3833;--warn:#e0a03a;--bad:#ef7a70;--ok:#5cc28a;--cj:#b99af0;--cjbg:#2b2534}
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
.it{padding:10px 0 10px 10px;border-top:1px solid var(--line);border-left:3px solid transparent}.it:first-child{border-top:0}.it.rel{border-left-color:var(--warn)}.it.past{opacity:.55}.it.today{border-left-color:var(--fg)}.it.cj{border-left-color:var(--cj);background:var(--cjbg)}.tag.cj{border-color:var(--cj);color:var(--cj);font-weight:600}
.meta{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;font-variant-numeric:tabular-nums}.meta b{color:var(--fg);font-weight:600}
.tt{margin-top:2px}.tt a{color:var(--fg);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}.sub{font-size:12.5px;color:var(--muted);margin-top:2px}
.tag{display:inline-block;font-size:11.5px;padding:0 7px;border-radius:999px;border:1px solid var(--line);color:var(--fg)}.tag.rel{border-color:var(--warn);color:var(--warn)}.tag.risk{border-color:var(--bad);color:var(--bad)}.tag.opp{border-color:var(--ok);color:var(--ok)}
.dd{font-weight:600}.dd.hot{color:var(--bad)}.day{font-size:12px;font-weight:600;padding:10px 0 2px;border-top:1px solid var(--line)}.day:first-child{border-top:0;padding-top:0}
.pager{display:flex;justify-content:space-between;font-size:13px}.pager a{color:var(--fg)}.foot{font-size:12px;color:var(--muted)}.empty{font-size:13px;color:var(--muted);padding:8px 0}
details.sec>summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between}details.sec>summary::-webkit-details-marker{display:none}
details.sec>summary::after{content:"접기";font-size:12px;color:var(--muted)}details.sec:not([open])>summary::after{content:"펼치기"}
h2 .cnt{font-size:12px;font-weight:600;color:var(--muted);margin-left:4px}
details.more{border-top:1px solid var(--line)}details.more>summary{cursor:pointer;font-size:13px;color:var(--muted);padding:10px 0 10px 10px}details.more[open]>summary{color:var(--fg);font-weight:600}
.grp{font-size:12px;font-weight:600;color:var(--muted);padding:14px 0 2px;border-top:1px solid var(--line)}
.legend{font-size:12px;color:var(--muted);margin:0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.arch a{display:flex;justify-content:space-between;padding:12px 0;border-top:1px solid var(--line);color:var(--fg);text-decoration:none}.arch a:first-child{border-top:0}
'''



def page(title, body, depth=0):
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#1f1e1b"><title>{e(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">{body}</div></body></html>'''


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
    import telegram_text
    telegram_text.main(latest)  # 텔레그램 텍스트는 사이트와 분리, telegram/ 폴더에만 저장
    print('built', len(days), 'reports; latest', latest)


if __name__ == '__main__':
    main()
