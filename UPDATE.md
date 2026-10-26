# 데일리 업데이트 절차 (예약 작업이 매일 이 문서를 따름)

기준일 = 실행일(Asia/Seoul). 주말·공휴일은 쉬지 않고 돌되, 신규 일정이 없으면 전일 데이터를 이어받아 날짜만 갱신.

## 1. 수집 (WebSearch / WebFetch, 공개자료만)
- **today**: 뉴스핌·뉴스1 '오늘의 정치일정/주요일정', 총리실 일정 게시판(opm.go.kr), 이투데이 부처 주간일정, 당일 국감·상임위 일정.
  대통령·총리는 전체, 부처는 아래 관련 부처·이슈만.
- **ministry**: 이투데이 '[정부 주요 일정] 경제·사회부처 주간 일정'(매주 일요일 게재) 중 당사 관련 항목 + 관련성 한 줄(why).
- **assembly**: 국감(종료 10/30)·상임위·법안소위·예결위·본회의·정기국회, **국회 주최 행사(입법박람회, 국회의장 주최 포럼, 공청회)**, 관련 의원실 세미나. 오늘부터 **4주 앞까지** 수집. 꼭 챙길 일정은 `must: true`.
- **news**: 최근 7일 CJ제일제당·CJ그룹 기사 + **`config/issues.json` 이슈 사전의 모든 검색어**(최근 48시간, 표기 변형 포함)로 찾은 기사. **CJ나 PHA가 언급되지 않아도 이슈 사전에 해당하면 포함**(예: EU 인조잔디 충진재 규제, 학교 인조잔디 현황 기사). 주말·휴일 기사도 빠짐없이 검색. `time`(입력 시각 HH:MM)을 반드시 확인해 기록 — 전일 12시 이후 기사는 '오늘 기사(석간)'로 브리핑에 들어감.
- **press**: 대한민국 정책브리핑(korea.kr) 보도자료 중 당사 직접 관련.
- **support**: 정부 지원사업, R&D 수요조사·공고·예산 일정(open/close, 기관). 추정 일정은 'YYYY-MM' 형식과 note에 '예상'.
- **focus**: `config/issues.json`의 focus_keyword 기준 — 식품물가, 가공식품물가, 생분해/바이오플라스틱(PHA), 당사 관련 정부 R&D, 가공식품 수출, 육상김, 김 수출, CJ제일제당 주요 이슈. 기사·정부발표·규제·법제·타사·국회. signal은 `유의`/`기회`/`관찰` ('위험' 표현 금지).
- **people**: 농식품부·해수부·기후부·산업부·과기정통부·교육부 인사, 농해수위·산자위·기후환노위·과방위·교육위 위원 관련 부고.

관련 부처: 농식품부, 해수부, 기후에너지환경부, 산업통상부, 과기정통부, 교육부, 식약처, 재경부(물가).

## 2. 저장
`data/YYYY-MM-DD/` 에 8개 JSON(today, ministry, assembly, news, press, support, focus, people). 필드는 직전 날짜 폴더와 동일.
- 전일 폴더를 복사해 시작하고, 지난 항목은 유지(assembly·support는 날짜가 지나도 남김), news는 7일 넘은 것 제거.
- **공개 사이트용이므로 내부 대관 메모(질의자료 제공, 참여·미참여 판단, 내부 대응 계획)는 쓰지 않는다.**

## 3. 빌드·배포
```
python3 build.py      # docs/ 재생성
git add -A && git commit -m "report: YYYY-MM-DD" && git push
```
GitHub Pages(main /docs)가 자동 반영.

## 4. 내부 대시보드 갱신
claude.ai 대시보드 '전략지원 이슈레이더'(https://claude.ai/artifact/2TExktSBzDJDWaqx8CVdZ3)의 8개 데이터셋을 같은 JSON으로 교체:
각 파일을 Artifact asset으로 업로드 → ArtifactData로 `datasets/<id>`의 `source.url`·`updated` 갱신.

## 5. 브리핑 전송
완성된 '오늘의 브리핑' 텍스트를 SendUserMessage로 사용자에게 보낸다(텔레그램 붙여넣기용).

## 6. 텔레그램 자동 전송
`build.py`가 `docs/latest-brief.txt`(브리핑 + 리포트 링크)를 만들고, main에 push되면 GitHub Actions(`.github/workflows/telegram.yml`)가 텔레그램으로 보낸다.
필요한 저장소 시크릿: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. 수동 재전송은 Actions 탭에서 'Run workflow'.

## 7. 키워드 기사 알림 (현재 중지됨 — 수동 실행만 가능)
`.github/workflows/keyword-alerts.yml` 이 한국시간 06:00~22:30 사이 30분마다 `alerts/keywords.txt` 키워드로 Google 뉴스를 검색해 새 기사만 채널에 보낸다. 키워드는 그 파일만 고치면 된다.
