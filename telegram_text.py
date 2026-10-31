#!/usr/bin/env python3
"""텔레그램 공유 텍스트 2종 생성(사이트와 별도 관리).

① telegram/latest-schedule.txt : '[금일(M/D) 정부, 국회 주요일정]'
② telegram/latest-brief.txt    : 오늘의 브리핑(🔗 전체보기 링크 포함)

이 텍스트는 공개 사이트(docs/)에 넣지 않는다. 서식을 고칠 때는 이 파일만 고친다.
단독 실행: python3 telegram_text.py [YYYY-MM-DD]  (build.py 가 자동 호출)
"""
import json, sys
from build import ROOT, DATA, SITE, d, fmt, diff, load, is_today_news, FILES

TG = ROOT / 'telegram'


def brief(D, day):
    L = [f"📡 전략지원 이슈레이더 | {fmt(day)}", f'🔗 {SITE}/reports/{day}.html', '', '■ 정부 주요일정']
    for r in [r for r in D['today'] if r.get('rel')][:8]:
        L.append(f"• {(r['time'] + ' ') if r.get('time') else ''}{r['org']} {r['title']} [{r['rel']}]")
    if L[-1] == '■ 정부 주요일정':
        L.append('• 당사 관련 공개 일정 없음')
    cjw = sorted([r for r in D['ministry'] if r.get('cj') and r['date'] >= day], key=lambda r: (r['date'], r.get('time') or '99'))
    if cjw:
        L += ['', '■ 이번 주 CJ그룹 관련 정부일정'] + [f"• {fmt(r['date'])} {(r['time'] + ' ') if r.get('time') else ''}{r['org']} {r['title']} [{r['cj']}]" for r in cjw]
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


def officials():
    p = ROOT / 'config' / 'officials.json'
    return json.load(open(p, encoding='utf-8')) if p.exists() else {}


def schedule_text(day):
    """텔레그램 공유용 '금일 정부, 국회 주요일정' 본문.
    data/DAY/govsched.json: [{sec: 대통령|총리|국회|부처, org, who, time, title, place}]
    대통령·총리·국회는 전부, 부처는 농식품부 장관 전부 + 다른 부처는 당사·그룹 관련만(수집 단계에서 선별)."""
    p = DATA / day / 'govsched.json'
    if not p.exists():
        return ''
    rows = json.load(open(p, encoding='utf-8'))
    off = officials()
    x = d(day)
    L = [f"[금일({x.month}/{x.day}) 정부, 국회 주요일정]"]
    tkey = lambda r: (r.get('time') or '99:99')
    def paren(r):
        inner = ' '.join(v for v in [r.get('time'), r.get('place')] if v)
        return f"{r['title']}({inner})" if inner else r['title']
    for sec in ['대통령', '총리']:
        items = sorted([r for r in rows if r['sec'] == sec], key=tkey)
        L += ['', f"▲ {off.get(sec, sec)}"] + ([paren(r) for r in items] or ['통상업무'])
    asm = sorted([r for r in rows if r['sec'] == '국회'], key=tkey)
    if asm:
        head = '국회 국정감사' if all('국정감사' in r['title'] or '국감' in r['title'] for r in asm) else '국회'
        L += ['', f"▲ {head}"] + [paren(r) for r in asm]
    heads = []
    for r in [r for r in rows if r['sec'] == '부처']:
        k = (r['org'], r.get('who') or '장관')
        if k not in heads:
            heads.append(k)
    heads.sort(key=lambda k: (k[0] != '농식품부', k[1] != '장관'))
    if ('농식품부', '장관') not in heads:
        heads.insert(0, ('농식품부', '장관'))
    for org, who in heads:
        items = sorted([r for r in rows if r['sec'] == '부처' and r['org'] == org and (r.get('who') or '장관') == who], key=tkey)
        name = off.get(f'{org} {who}') or f'{org} {who}'
        lines = [' '.join(v for v in [r.get('time'), r['title'] + (f"({r['place']})" if r.get('place') else '')] if v) for r in items]
        L += ['', f"▲ {name}"] + (lines or ['공개 일정 없음'])
    return '\n'.join(L)



def main(day=None):
    if not day:
        day = sorted(p.name for p in DATA.iterdir() if p.is_dir() and all((p / f'{f}.json').exists() for f in FILES))[-1]
    TG.mkdir(exist_ok=True)
    (TG / 'latest-brief.txt').write_text(brief(load(day), day) + '\n', encoding='utf-8')
    st = schedule_text(day)
    (TG / 'latest-schedule.txt').write_text(st + '\n' if st else '', encoding='utf-8')
    print('telegram texts for', day)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
