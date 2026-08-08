from __future__ import annotations


def dashboard_html() -> str:
    return """<!doctype html>
<html lang='ko'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>ai-trading 모니터링 대시보드</title>
  <style>
    :root{
      --bg:#06101f; --panel:rgba(15,23,42,.84); --card:rgba(17,24,39,.9); --line:rgba(148,163,184,.15);
      --text:#e5eefc; --muted:#94a3b8; --good:#22c55e; --warn:#f59e0b; --bad:#f87171; --accent:#38bdf8;
      --radius:18px; --shadow:0 22px 70px rgba(2,6,23,.44);
    }
    *{box-sizing:border-box}
    body{
      margin:0; min-height:100vh; color:var(--text); background:
      radial-gradient(circle at top left, rgba(56,189,248,.18), transparent 30%),
      radial-gradient(circle at top right, rgba(34,197,94,.12), transparent 25%),
      linear-gradient(180deg,#020617 0%, #06101f 50%, #0f172a 100%);
      font-family: Inter, Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell{max-width:1440px;margin:0 auto;padding:20px}
    .topbar,.panel,.card{border:1px solid var(--line);background:var(--panel);box-shadow:var(--shadow);backdrop-filter:blur(16px)}
    .topbar{border-radius:22px;padding:16px 18px;display:flex;gap:14px;justify-content:space-between;align-items:center;flex-wrap:wrap}
    .brand h1{margin:0;font-size:26px;letter-spacing:-.03em}
    .brand p{margin:6px 0 0;color:var(--muted);font-size:13px}
    .status-row{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
    .pill{display:inline-flex;gap:7px;align-items:center;padding:9px 12px;border-radius:999px;background:rgba(30,41,59,.9);border:1px solid var(--line);font-size:13px}
    .dot{width:9px;height:9px;border-radius:50%;background:var(--muted)} .dot.ok{background:var(--good)} .dot.bad{background:var(--bad)}
    .tabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
    .tab-btn{padding:10px 14px;border:1px solid var(--line);background:rgba(15,23,42,.8);color:var(--text);border-radius:999px;cursor:pointer}
    .tab-btn.active{background:linear-gradient(135deg,#2563eb,#0ea5e9);border-color:transparent}
    .tabs-shell{margin-top:14px}
    .tab-pane{display:none}.tab-pane.active{display:block}
    .grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(4,minmax(0,1fr))}.two-col{grid-template-columns:1.1fr .9fr}.three-col{grid-template-columns:repeat(3,minmax(0,1fr))}
    .card{border-radius:18px;padding:16px}
    .card h2,.card h3{margin:0 0 10px}.card h2{font-size:16px}.card h3{font-size:14px;color:#cbd5e1}
    .metric{font-size:28px;font-weight:700;letter-spacing:-.03em;margin:0}.metric.good{color:var(--good)} .metric.bad{color:var(--bad)}.sub{margin:5px 0 0;color:var(--muted);font-size:12px}
    .toolbar,.form-grid,.filters{display:flex;gap:10px;flex-wrap:wrap}
    .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.field label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
    .row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;background:rgba(15,23,42,.86);border:1px solid rgba(148,163,184,.14)}
    .field input,.field select,.filters input,.filters select{width:100%;padding:11px 12px;border-radius:12px;border:1px solid rgba(148,163,184,.2);background:rgba(2,6,23,.68);color:var(--text);outline:none}
    .field input:focus,.field select:focus,.filters input:focus,.filters select:focus{border-color:rgba(56,189,248,.7);box-shadow:0 0 0 4px rgba(56,189,248,.12)}
    .btn{padding:11px 14px;border:0;border-radius:12px;cursor:pointer;color:#fff;background:linear-gradient(135deg,#2563eb,#0ea5e9)}
    .btn.good{background:linear-gradient(135deg,#16a34a,#22c55e)} .btn.warn{background:linear-gradient(135deg,#ea580c,#f59e0b)} .btn.ghost{background:transparent;border:1px solid rgba(148,163,184,.22)}
    .split{display:grid;grid-template-columns:1fr 1fr;gap:14px}
    .table-wrap{overflow:auto;border-radius:14px;border:1px solid rgba(148,163,184,.14)}
    table{width:100%;border-collapse:collapse;font-size:13px;min-width:920px;background:rgba(2,6,23,.58)}
    th,td{padding:11px 10px;border-bottom:1px solid rgba(148,163,184,.12);vertical-align:top;text-align:left}
    th{color:#cbd5e1;font-weight:600;position:sticky;top:0;background:rgba(2,6,23,.95)}
    tr:hover td{background:rgba(15,23,42,.5)}
    .tag{display:inline-flex;align-items:center;padding:5px 9px;border-radius:999px;background:rgba(56,189,248,.11);border:1px solid rgba(56,189,248,.18);color:#7dd3fc;font-size:12px}
    .tag.good{background:rgba(34,197,94,.12);color:#86efac;border-color:rgba(34,197,94,.18)} .tag.warn{background:rgba(245,158,11,.12);color:#fbbf24;border-color:rgba(245,158,11,.2)} .tag.bad{background:rgba(248,113,113,.12);color:#fca5a5;border-color:rgba(248,113,113,.2)}
    canvas{width:100%;height:280px;display:block;background:rgba(2,6,23,.55);border-radius:14px;border:1px solid rgba(148,163,184,.14)}
    pre{margin:0;white-space:pre-wrap;word-break:break-word;line-height:1.5;background:rgba(2,6,23,.65);border:1px solid rgba(148,163,184,.14);border-radius:14px;padding:14px;min-height:210px}
    .muted{color:var(--muted)}
    .toast-host{position:fixed;right:16px;bottom:16px;display:grid;gap:10px;z-index:50}
    .toast{min-width:260px;max-width:380px;padding:12px 14px;border-radius:14px;background:rgba(15,23,42,.95);border:1px solid rgba(148,163,184,.18);box-shadow:var(--shadow)}
    .toast strong{display:block;margin-bottom:4px}
    .footer{margin-top:14px;text-align:center;color:var(--muted);font-size:12px}
    @media (max-width: 1180px){.metrics,.three-col,.two-col,.split{grid-template-columns:1fr 1fr}}
    @media (max-width: 760px){.shell{padding:12px}.metrics,.three-col,.two-col,.split,.form-grid{grid-template-columns:1fr}.topbar{align-items:flex-start}}
  </style>
</head>
<body>
  <div class='shell'>
    <section class='topbar'>
      <div class='brand'>
        <h1>ai-trading 모니터링</h1>
        <p>탭 기반 대시보드 · 실시간 차트 · 주문/체결 로그 · KIS 수집기 · 알림</p>
      </div>
      <div class='status-row'>
        <div class='pill'><span id='healthDot' class='dot'></span><span id='healthText'>상태 확인 중</span></div>
        <div class='pill'>버전 <strong id='serviceVersion'>-</strong></div>
        <div class='pill'>업타임 <strong id='uptime'>-</strong></div>
        <div class='pill'>KST <strong id='kstClock'>-</strong></div>
        <div class='pill'>WS <strong id='wsState'>연결 대기</strong></div>
        <div class='pill'>새로고침 <strong id='refreshState'>-</strong></div>
      </div>
    </section>

    <div class='tabs'>
      <button class='tab-btn active' data-tab='overview'>개요</button>
      <button class='tab-btn' data-tab='chart'>차트</button>
      <button class='tab-btn' data-tab='logs'>주문·체결 로그</button>
      <button class='tab-btn' data-tab='portfolio'>보유현황</button>
      <button class='tab-btn' data-tab='collector'>KIS 수집기</button>
      <button class='tab-btn' data-tab='settings'>설정</button>
    </div>

    <div class='tabs-shell'>
      <section class='tab-pane active' id='tab-overview'>
        <div class='grid metrics'>
          <div class='card'><h2>헬스</h2><p class='metric' id='cardHealth'>-</p><p class='sub'>/status 기준</p></div>
          <div class='card'><h2>예측 신호</h2><p class='metric' id='cardSignal'>-</p><p class='sub'>최근 /predict</p></div>
          <div class='card'><h2>주문 수량</h2><p class='metric' id='cardQuantity'>-</p><p class='sub'>최근 /plan</p></div>
          <div class='card'><h2>백테스트 수익률</h2><p class='metric' id='cardReturn'>-</p><p class='sub'>최근 /backtest</p></div>
        </div>

        <div class='grid two-col' style='margin-top:14px;'>
          <section class='card'>
            <h2>입력 패널</h2>
            <div class='toolbar'>
              <button class='btn' type='button' onclick="preset('bull')">상승</button>
              <button class='btn ghost' type='button' onclick="preset('flat')">중립</button>
              <button class='btn warn' type='button' onclick="preset('bear')">하락</button>
              <button class='btn good' type='button' onclick='runPredict()'>예측</button>
              <button class='btn good' type='button' onclick='runPlan()'>주문 계획</button>
              <button class='btn warn' type='button' onclick='runBacktest()'>백테스트</button>
            </div>
            <div class='form-grid' style='margin-top:12px;'>
              <div class='field'><label>종목코드</label><input id='symbol' placeholder='예: 005930.KS'></div>
              <div class='field'><label>현재가</label><input id='price' type='number' value='72000'></div>
              <div class='field'><label>단기 이동평균</label><input id='maShort' type='number' value='71500'></div>
              <div class='field'><label>장기 이동평균</label><input id='maLong' type='number' value='70000'></div>
              <div class='field'><label>RSI</label><input id='rsi' type='number' value='45'></div>
              <div class='field'><label>심리 지표 (-1~1)</label><input id='sentiment' type='number' step='0.1' value='0.4'></div>
              <div class='field'><label>거래량</label><input id='volume' type='number' value='1000000'></div>
              <div class='field'><label>초기자본</label><input id='cash' type='number' value='10000000'></div>
            </div>
            <div class='toolbar' style='margin-top:12px;'>
              <button class='btn ghost' type='button' onclick='refreshAll(true)'>전체 새로고침</button>
              <button class='btn ghost' type='button' onclick='loadLiveSnapshot()'>실데이터 불러오기</button>
            </div>
          </section>

          <section class='card'>
            <h2>상태 요약</h2>
            <div class='split'>
              <div>
                <div class='row'><span>서버</span><span class='tag good' id='tagServer'>정상</span></div>
                <div class='row'><span>API</span><span class='tag' id='tagApi'>대기 중</span></div>
                <div class='row'><span>최근 작업</span><span class='tag warn' id='tagAction'>없음</span></div>
                <div class='row'><span>지연시간</span><span class='tag' id='tagLatency'>-</span></div>
              </div>
              <div>
                <div class='row'><span>수집기</span><span class='tag' id='tagCollector'>-</span></div>
                <div class='row'><span>포트폴리오</span><span class='tag' id='tagPortfolio'>-</span></div>
                <div class='row'><span>자동 새로고침</span><span class='tag good' id='tagAuto'>ON</span></div>
                <div class='row'><span>알림</span><span class='tag' id='tagNotify'>OFF</span></div>
                <div class='row'><span>이벤트</span><span class='tag' id='tagEvents'>0</span></div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section class='tab-pane' id='tab-portfolio'>
        <div class='grid two-col'>
          <section class='card'>
            <div class='toolbar' style='justify-content:space-between;align-items:center;'>
              <div>
                <h2 style='margin:0'>보유현황</h2>
                <div class='muted' style='font-size:12px;margin-top:4px;'>보유종목이 여러 개면 여기서 한 번에 평가금액과 손익을 봅니다.</div>
              </div>
            </div>
            <div class='grid metrics' style='margin-top:12px;grid-template-columns:repeat(4,minmax(0,1fr));'>
              <div class='card' style='padding:14px'><h3>보유종목 수</h3><p class='metric' id='portfolioCount'>-</p></div>
              <div class='card' style='padding:14px'><h3>총 평가금액</h3><p class='metric' id='portfolioMarketValue'>-</p></div>
              <div class='card' style='padding:14px'><h3>평가손익</h3><p class='metric' id='portfolioPnl'>-</p></div>
              <div class='card' style='padding:14px'><h3>손익률</h3><p class='metric' id='portfolioPnlPct'>-</p></div>
            </div>
            <div class='table-wrap' style='margin-top:12px;'>
              <table>
                <thead><tr><th>종목</th><th>명칭</th><th>수량</th><th>평단</th><th>현재가</th><th>평가금액</th><th>평가손익</th><th>손익률</th><th>비고</th></tr></thead>
                <tbody id='portfolioBody'><tr><td colspan='9' class='muted'>보유종목이 없습니다.</td></tr></tbody>
              </table>
            </div>
          </section>
          <section class='card'>
            <div class='toolbar' style='align-items:flex-start;'>
              <div>
                <h2 style='margin-bottom:4px;'>선택 종목 상세</h2>
                <div class='muted' style='font-size:12px;'>현재가·평가손익을 큰 숫자로 보여줍니다.</div>
              </div>
              <span class='tag' id='selectedHoldingTag'>선택 대기</span>
            </div>
            <div class='grid metrics' style='margin-top:12px;grid-template-columns:repeat(2,minmax(0,1fr));'>
              <div class='card' style='padding:14px'><h3>현재가</h3><p class='metric' id='selectedCurrentPrice'>-</p><p class='sub' id='selectedHoldingName'>선택 종목 없음</p></div>
              <div class='card' style='padding:14px'><h3>평가손익</h3><p class='metric' id='selectedUnrealizedPnl'>-</p><p class='sub'>손익 금액</p></div>
              <div class='card' style='padding:14px'><h3>손익률</h3><p class='metric' id='selectedUnrealizedPnlPct'>-</p><p class='sub'>수익률</p></div>
              <div class='card' style='padding:14px'><h3>평가금액</h3><p class='metric' id='selectedMarketValue'>-</p><p class='sub'>보유 평가액</p></div>
            </div>
            <div class='toolbar' style='margin-top:12px;align-items:end;'>
              <div class='field' style='min-width:220px'><label>보유종목 선택</label><select id='portfolioPick'></select></div>
              <div class='toolbar'>
                <button class='btn ghost' type='button' onclick='syncSelectedPortfolio()'>입력패널로 복사</button>
                <button class='btn ghost' type='button' onclick='refreshPortfolio()'>포트폴리오 새로고침</button>
              </div>
            </div>
            <details style='margin-top:12px;'>
              <summary class='tag'>원시 포트폴리오 JSON</summary>
              <pre id='portfolioOutput' style='margin-top:12px;'>포트폴리오 상태를 불러오는 중입니다.</pre>
            </details>
            <h3 style='margin:14px 0 10px;'>보유종목 입력</h3>
            <div class='muted' style='font-size:12px;margin-bottom:10px;'>실제 계좌 연동 전에는 이 화면에서 보유종목을 저장·수정할 수 있습니다.</div>
            <div class='form-grid'>
              <div class='field'><label>종목코드</label><input id='portfolioSymbol' placeholder='예: 005930.KS'></div>
              <div class='field'><label>명칭</label><input id='portfolioName' placeholder='삼성전자'></div>
              <div class='field'><label>수량</label><input id='portfolioQuantity' type='number' min='0' value='0'></div>
              <div class='field'><label>평단</label><input id='portfolioAvgPrice' type='number' min='0' value='0'></div>
              <div class='field'><label>섹터</label><input id='portfolioSector' placeholder='반도체'></div>
              <div class='field'><label>메모</label><input id='portfolioMemo' placeholder='보유 이유 / 비중 메모'></div>
            </div>
            <div class='toolbar' style='margin-top:12px;'>
              <button class='btn good' type='button' onclick='savePortfolioPosition()'>저장</button>
              <button class='btn ghost' type='button' onclick='deletePortfolioPosition()'>삭제</button>
              <button class='btn ghost' type='button' onclick='refreshPortfolio()'>새로고침</button>
            </div>
          </section>
        </div>
      </section>

      <section class='tab-pane' id='tab-chart'>
        <div class='grid two-col'>
          <section class='card'>
            <div class='toolbar' style='justify-content:space-between;align-items:center;'>
              <h2 style='margin:0'>실시간 차트</h2>
              <div class='toolbar'>
                <div class='field' style='min-width:180px'><label>차트 기준</label><select id='chartMetric'><option value='price'>가격</option><option value='confidence'>신뢰도</option><option value='return_pct'>수익률</option></select></div>
                <div class='field' style='min-width:180px'><label>최근 개수</label><select id='chartWindow'><option>20</option><option selected>40</option><option>80</option></select></div>
              </div>
            </div>
            <canvas id='chartCanvas' width='1100' height='320'></canvas>
            <div class='muted' style='margin-top:8px;font-size:12px;'>이벤트 로그 기반의 라인 차트입니다. 수집기/예측/주문/백테스트 활동이 반영됩니다.</div>
          </section>
          <section class='card'>
            <h2>최신 이벤트</h2>
            <pre id='chartSummary'>아직 이벤트가 없습니다.</pre>
          </section>
        </div>
      </section>

      <section class='tab-pane' id='tab-logs'>
        <section class='card'>
          <div class='toolbar' style='justify-content:space-between;align-items:end;'>
            <div>
              <h2 style='margin:0'>주문·체결 로그 테이블</h2>
              <div class='muted' style='font-size:12px;margin-top:4px;'>필터와 검색으로 빠르게 좁혀볼 수 있습니다.</div>
            </div>
            <div class='filters'>
              <div class='field' style='min-width:180px'><label>유형</label><select id='logKind'><option value=''>전체</option><option value='collector'>수집</option><option value='predict'>예측</option><option value='order'>주문</option><option value='fill'>체결/백테스트</option><option value='system'>시스템</option></select></div>
              <div class='field' style='min-width:180px'><label>검색</label><input id='logQuery' placeholder='심볼/메시지 검색'></div>
              <div class='field' style='min-width:180px'><label>수량</label><select id='logLimit'><option>20</option><option selected>50</option><option>100</option></select></div>
            </div>
          </div>
          <div class='table-wrap' style='margin-top:12px;'>
            <table>
              <thead><tr><th>시간(KST)</th><th>유형</th><th>내용</th><th>종목</th><th>신호</th><th>수량</th><th>가격</th><th>신뢰도/수익률</th><th>출처</th></tr></thead>
              <tbody id='logBody'><tr><td colspan='9' class='muted'>대기 중</td></tr></tbody>
            </table>
          </div>
        </section>
      </section>

      <section class='tab-pane' id='tab-collector'>
        <div class='grid two-col'>
          <section class='card'>
            <h2>KIS 실연동 수집기</h2>
            <div class='toolbar'>
              <div class='field' style='min-width:180px'><label>종목</label><input id='collectorSymbol' placeholder='예: 005930.KS'></div>
              <div class='field' style='min-width:180px'><label>상태</label><select id='collectorMode'><option value='auto'>자동</option><option value='mock'>모의</option><option value='live'>실연동</option></select></div>
              <div class='field' style='min-width:180px'><label>갱신</label><select id='collectorRefresh'><option value='off'>수동</option><option value='on' selected>자동 반영</option></select></div>
            </div>
            <div class='toolbar' style='margin-top:12px;'>
              <button class='btn good' type='button' onclick='loadLiveSnapshot()'>시세 불러오기</button>
              <button class='btn ghost' type='button' onclick='refreshAll(true)'>수집기 상태</button>
            </div>
            <details><summary class='tag'>수집기 JSON</summary><pre id='collectorOutput' style='margin-top:12px;'>아직 수집기 상태를 확인하지 않았습니다.</pre></details>
          </section>
          <section class='card'>
            <h2>실연동 안내</h2>
            <pre>실연동은 아래 환경변수로 활성화합니다.

KIS_ENABLE_LIVE=1
KIS_BASE_URL=https://openapivts.koreainvestment.com:29443
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCESS_TOKEN=...

실제 KIS 시세를 받아온 뒤, 로컬에서 이동평균과 RSI를 계산해서 UI와 예측에 반영합니다.</pre>
          </section>
        </div>
      </section>

      <section class='tab-pane' id='tab-settings'>
        <div class='grid two-col'>
          <section class='card'>
            <h2>자동 새로고침 / 알림</h2>
            <div class='toolbar'>
              <label class='pill'><input id='autoRefresh' type='checkbox' checked style='width:auto;margin:0 8px 0 0;'>자동 새로고침</label>
              <label class='pill'><input id='marketAwareRefresh' type='checkbox' checked style='width:auto;margin:0 8px 0 0;'>장중 가변 간격</label>
              <label class='pill'>기준 간격 <input id='refreshEvery' type='number' min='5' value='10' style='width:80px;margin-left:8px'></label>
            </div>
            <div class='toolbar' style='margin-top:12px;'>
              <button class='btn ghost' type='button' onclick='requestNotificationPermission()'>알림 권한 요청</button>
              <button class='btn ghost' type='button' onclick='clearLog()'>로그 비우기</button>
            </div>
          </section>
          <section class='card'>
            <h2>API 상태</h2>
            <details><summary class='tag'>상태 요약 JSON</summary><pre id='statusOutput' style='margin-top:12px;'>대기 중</pre></details>
          </section>
        </div>
      </section>
    </div>

    <div class='footer'>기본 외부 포트는 8010입니다. 탭별로 압축된 화면을 유지하면서도 주요 기능은 즉시 확인할 수 있습니다.</div>
  </div>

  <div class='toast-host' id='toastHost'></div>

  <script>
    const state = { events: [], lastEventIds: new Set(), latestSnapshot: null, portfolio: null, activeTab: 'overview', timer: null, ws: null, wsBackoff: 1500 };
    const kstFormatter = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const timeFormatter = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

    function toNumber(id){ return Number(document.getElementById(id).value); }
    function payload(){
      return {
        symbol: document.getElementById('symbol').value.trim(),
        price: toNumber('price'),
        moving_average_short: toNumber('maShort'),
        moving_average_long: toNumber('maLong'),
        rsi: toNumber('rsi'),
        sentiment: Number(document.getElementById('sentiment').value),
        volume: toNumber('volume'),
      };
    }
    function setMetric(id, value){ document.getElementById(id).textContent = value; }
    function setBadge(id, text, cls=''){ const el = document.getElementById(id); el.textContent = text; el.className = 'tag' + (cls ? ' ' + cls : ''); }
    function setWsState(text, cls=''){ const el = document.getElementById('wsState'); if (!el) return; el.textContent = text; el.className = cls ? 'tag ' + cls : 'tag'; }
    function toast(title, body, kind=''){ const host = document.getElementById('toastHost'); const el = document.createElement('div'); el.className = 'toast'; el.innerHTML = `<strong>${title}</strong><div class='muted'>${body}</div>`; if (kind === 'good') el.style.borderColor = 'rgba(34,197,94,.28)'; if (kind === 'warn') el.style.borderColor = 'rgba(245,158,11,.28)'; host.prepend(el); setTimeout(() => el.remove(), 3500); }
    function maybeNotify(title, body){ if (!document.getElementById('notifyToggle').checked) return; if ('Notification' in window && Notification.permission === 'granted') new Notification(title, { body }); else toast(title, body); }
    function money(value){ return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(Number(value || 0)); }
    function pct(value){ return `${Number(value || 0).toFixed(2)}%`; }
    function refreshLabel(ms){
      const sec = Math.max(1, Math.round(ms / 1000));
      document.getElementById('refreshState').textContent = `${sec}s`;
    }
    function isMarketHoursKst(now = new Date()) {
      const minutes = (now.getUTCHours() * 60 + now.getUTCMinutes() + 9 * 60) % 1440;
      return minutes >= 9 * 60 && minutes < (15 * 60 + 30);
    }
    function getRefreshIntervalMs(){
      const base = Math.max(5, Number(document.getElementById('refreshEvery').value || 10)) * 1000;
      if (!document.getElementById('marketAwareRefresh').checked) return base;
      return isMarketHoursKst() ? Math.min(base, 10000) : Math.max(base, 60000);
    }
    function scheduleRefreshTimer(){
      if (state.timer) clearInterval(state.timer);
      const interval = getRefreshIntervalMs();
      refreshLabel(interval);
      state.timer = setInterval(() => { if (document.getElementById('autoRefresh').checked) refreshAll(false); }, interval);
    }
    function clearLog(){ state.events = []; renderEvents(); drawChart(); toast('로그 비우기', '로컬 화면 로그를 비웠습니다.'); }
    function setActiveTab(tab){ state.activeTab = tab; document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab)); document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`)); }
    document.querySelectorAll('.tab-btn').forEach(btn => btn.addEventListener('click', () => setActiveTab(btn.dataset.tab)));
    function updateClock(){ document.getElementById('kstClock').textContent = kstFormatter.format(new Date()); }
    function preset(kind){
      const map = { bull:{ price:72000, maShort:71500, maLong:70000, rsi:45, sentiment:0.4 }, flat:{ price:180000, maShort:180000, maLong:180000, rsi:55, sentiment:0 }, bear:{ price:110000, maShort:112000, maLong:115000, rsi:78, sentiment:-0.5 } }[kind];
      Object.entries(map).forEach(([k,v]) => document.getElementById(k).value = v);
      maybeNotify('시나리오 입력', kind === 'bull' ? '상승 시나리오' : kind === 'flat' ? '중립 시나리오' : '하락 시나리오');
    }
    async function fetchJson(url, options){
      const started = performance.now();
      const res = await fetch(url, options);
      const elapsed = Math.round(performance.now() - started);
      const text = await res.text();
      let body; try { body = JSON.parse(text); } catch { body = text; }
      if (!res.ok) throw new Error(typeof body === 'string' ? body : JSON.stringify(body));
      return { body, elapsed };
    }
    function upsertEvent(event){
      const key = `${event.ts}|${event.kind}|${event.message}`;
      if (state.lastEventIds.has(key)) return false;
      state.lastEventIds.add(key); state.events.unshift(event); if (state.events.length > 120) state.events.length = 120; return true;
    }
    function applyLiveEvent(event){
      if (!event) return;
      if (event.kind === 'collector' && event.price !== null && event.price !== undefined) {
        document.getElementById('price').value = event.price;
        document.getElementById('maShort').value = event.price;
        document.getElementById('maLong').value = event.price;
        setBadge('tagAction', '실시간 수집', '');
      }
      if (event.kind === 'predict') {
        setMetric('cardSignal', String(event.signal || '-').toUpperCase());
        setBadge('tagAction', '예측 수신', '');
      }
      if (event.kind === 'order') {
        if (typeof event.quantity === 'number') setMetric('cardQuantity', String(event.quantity));
        setBadge('tagAction', '주문 수신', 'good');
      }
      if (event.kind === 'fill') {
        if (typeof event.return_pct === 'number') setMetric('cardReturn', `${event.return_pct}%`);
        setBadge('tagAction', '체결 수신', 'warn');
      }
      if (event.kind === 'system') {
        setBadge('tagAction', '시스템', '');
      }
    }
    function renderSelectedHolding(row){
      const title = document.getElementById('selectedHoldingName');
      const tag = document.getElementById('selectedHoldingTag');
      const currentPrice = document.getElementById('selectedCurrentPrice');
      const pnl = document.getElementById('selectedUnrealizedPnl');
      const pnlPct = document.getElementById('selectedUnrealizedPnlPct');
      const marketValue = document.getElementById('selectedMarketValue');
      if (!row) {
        title.textContent = '선택 종목 없음';
        tag.textContent = '선택 대기';
        currentPrice.textContent = '-';
        pnl.textContent = '-';
        pnlPct.textContent = '-';
        marketValue.textContent = '-';
        return;
      }
      const pnlClass = row.unrealized_pnl >= 0 ? 'good' : 'bad';
      const source = state.portfolio?.source || 'local';
      title.textContent = `${row.name || row.symbol} · ${row.symbol}`;
      tag.textContent = source === 'kis-live' ? '실계좌' : '로컬';
      tag.className = `tag ${source === 'kis-live' ? 'good' : ''}`;
      currentPrice.textContent = money(row.current_price);
      pnl.textContent = `${money(row.unrealized_pnl)}원`;
      pnl.className = `metric ${pnlClass}`;
      pnlPct.textContent = pct(row.unrealized_pnl_pct);
      pnlPct.className = `metric ${pnlClass}`;
      marketValue.textContent = money(row.market_value);
      marketValue.className = 'metric';
    }
    function renderPortfolio(summary){
      state.portfolio = summary;
      setMetric('portfolioCount', String(summary.positions_count ?? 0));
      setMetric('portfolioMarketValue', money(summary.total_market_value ?? 0));
      setMetric('portfolioPnl', `${money(summary.unrealized_pnl ?? 0)}원`);
      setMetric('portfolioPnlPct', pct(summary.unrealized_pnl_pct ?? 0));
      setBadge('tagPortfolio', summary.source === 'kis-live' ? '실계좌' : '로컬', summary.source === 'kis-live' ? 'good' : '');
      document.getElementById('portfolioOutput').textContent = JSON.stringify(summary, null, 2);
      const select = document.getElementById('portfolioPick');
      const rows = summary.positions || [];
      if (!rows.length) {
        select.innerHTML = `<option value=''>보유종목 없음</option>`;
        document.getElementById('portfolioBody').innerHTML = `<tr><td colspan='9' class='muted'>보유종목이 없습니다.</td></tr>`;
        renderSelectedHolding(null);
        return;
      }
      select.innerHTML = rows.map(row => `<option value='${row.symbol}'>${row.name || row.symbol} · ${row.symbol}</option>`).join('');
      const body = rows.map(row => {
        const pnlClass = row.unrealized_pnl >= 0 ? 'good' : 'bad';
        return `<tr data-symbol='${row.symbol}'><td><strong>${row.symbol}</strong></td><td>${row.name || '-'}</td><td>${row.quantity}</td><td>${money(row.avg_price)}</td><td>${money(row.current_price)}</td><td>${money(row.market_value)}</td><td><span class='tag ${pnlClass}'>${money(row.unrealized_pnl)}원</span></td><td><span class='tag ${pnlClass}'>${pct(row.unrealized_pnl_pct)}</span></td><td>${row.memo || row.sector || '-'}</td></tr>`;
      }).join('');
      document.getElementById('portfolioBody').innerHTML = body;
      select.value = select.value && rows.some(row => row.symbol === select.value) ? select.value : rows[0].symbol;
      const selected = rows.find(row => row.symbol === select.value) || rows[0];
      renderSelectedHolding(selected);
      if (!document.getElementById('symbol').value) document.getElementById('symbol').value = selected.symbol;
      if (!document.getElementById('collectorSymbol').value) document.getElementById('collectorSymbol').value = selected.symbol;
    }
    function syncSelectedPortfolio(){
      const pick = document.getElementById('portfolioPick').value;
      if (!pick) { toast('선택 없음', '먼저 보유종목을 선택하세요.', 'warn'); return; }
      document.getElementById('symbol').value = pick;
      document.getElementById('collectorSymbol').value = pick;
      const row = (state.portfolio?.positions || []).find((item) => item.symbol === pick);
      renderSelectedHolding(row || null);
      toast('입력패널 반영', `${pick}로 입력패널을 채웠습니다.`, 'good');
    }
    async function savePortfolioPosition(){
      const payload = {
        symbol: document.getElementById('portfolioSymbol').value.trim(),
        name: document.getElementById('portfolioName').value.trim(),
        quantity: Number(document.getElementById('portfolioQuantity').value),
        avg_price: Number(document.getElementById('portfolioAvgPrice').value),
        sector: document.getElementById('portfolioSector').value.trim(),
        memo: document.getElementById('portfolioMemo').value.trim(),
      };
      const { body } = await fetchJson('/portfolio/positions', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      toast('보유종목 저장', `${body.position.symbol} 저장 완료`, 'good');
      await refreshPortfolio(true);
    }
    async function deletePortfolioPosition(){
      const symbol = document.getElementById('portfolioSymbol').value.trim() || document.getElementById('portfolioPick').value;
      if (!symbol) { toast('삭제 실패', '삭제할 종목코드가 없습니다.', 'warn'); return; }
      const { body } = await fetchJson(`/portfolio/positions/${encodeURIComponent(symbol)}`, { method:'DELETE' });
      toast('보유종목 삭제', body.ok ? `${symbol} 삭제 완료` : `${symbol} 를 찾지 못했습니다.`, body.ok ? 'good' : 'warn');
      await refreshPortfolio(true);
    }
    async function refreshPortfolio(manual=false){
      const { body } = await fetchJson('/portfolio');
      renderPortfolio(body);
      if (manual) toast('포트폴리오', '보유현황을 갱신했습니다.', 'good');
    }
    function renderOverview(status, collector){
      setMetric('cardHealth', status.health || '-');
      setMetric('serviceVersion', status.version || '-');
      setMetric('uptime', status.uptime || '-');
      setMetric('cardSignal', status.last_signal ? String(status.last_signal).toUpperCase() : '-');
      setMetric('cardQuantity', status.last_quantity ?? '-');
      setMetric('cardReturn', status.last_backtest_return ?? '-');
      setMetric('cardHealth', status.health || '-');
      document.getElementById('healthText').textContent = status.health === 'ok' ? '서버 정상' : '서버 확인 필요';
      document.getElementById('healthDot').className = 'dot ' + (status.health === 'ok' ? 'ok' : 'bad');
      setBadge('tagServer', status.health === 'ok' ? '정상' : '오류', status.health === 'ok' ? 'good' : 'bad');
      setBadge('tagApi', status.event_count > 0 ? '활성' : '대기 중', status.event_count > 0 ? 'good' : '');
      setBadge('tagCollector', collector.mode === 'kis-live' && collector.configured ? '실연동' : '모의', collector.mode === 'kis-live' && collector.configured ? 'good' : '');
      setBadge('tagPortfolio', status.portfolio_source === 'kis-live' ? '실계좌' : '로컬', status.portfolio_source === 'kis-live' ? 'good' : '');
      setBadge('tagEvents', String(status.event_count || 0), '');
      document.getElementById('statusOutput').textContent = JSON.stringify(status, null, 2);
      document.getElementById('collectorOutput').textContent = JSON.stringify(collector, null, 2);
    }
    function renderEvents(){
      const kind = document.getElementById('logKind').value;
      const query = document.getElementById('logQuery').value.trim().toLowerCase();
      const limit = Number(document.getElementById('logLimit').value);
      const filtered = state.events.filter(ev => (!kind || ev.kind === kind) && (!query || JSON.stringify(ev).toLowerCase().includes(query))).slice(0, limit);
      const tbody = document.getElementById('logBody');
      if (!filtered.length){ tbody.innerHTML = `<tr><td colspan='9' class='muted'>표시할 로그가 없습니다.</td></tr>`; return; }
      tbody.innerHTML = filtered.map(ev => `
        <tr>
          <td>${timeFormatter.format(new Date(ev.ts))}</td>
          <td><span class='tag ${ev.kind === 'fill' ? 'good' : ev.kind === 'order' ? 'warn' : ''}'>${ev.kind}</span></td>
          <td>${ev.message}</td>
          <td>${ev.symbol || '-'}</td>
          <td>${ev.signal || '-'}</td>
          <td>${ev.quantity ?? '-'}</td>
          <td>${ev.price ?? '-'}</td>
          <td>${ev.confidence ?? ev.return_pct ?? '-'}</td>
          <td>${ev.source || '-'}</td>
        </tr>`).join('');
    }
    function collectSeries(metric){
      return state.events
        .filter(ev => typeof ev[metric] === 'number')
        .slice(0, Number(document.getElementById('chartWindow').value))
        .reverse()
        .map(ev => ({ x: ev.ts, y: Number(ev[metric]), kind: ev.kind, label: ev.message }));
    }
    function drawChart(){
      const canvas = document.getElementById('chartCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const metric = document.getElementById('chartMetric').value;
      const points = collectSeries(metric);
      const w = canvas.width, h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(2,6,23,.55)';
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = 'rgba(148,163,184,.14)';
      for (let i = 0; i <= 5; i++) { const y = 28 + (h - 56) * (i / 5); ctx.beginPath(); ctx.moveTo(18, y); ctx.lineTo(w - 18, y); ctx.stroke(); }
      if (!points.length){ ctx.fillStyle = '#94a3b8'; ctx.font = '16px Inter, sans-serif'; ctx.fillText('표시할 데이터가 없습니다.', 30, 50); document.getElementById('chartSummary').textContent = '아직 이벤트가 없습니다.'; return; }
      const values = points.map(p => p.y);
      const min = Math.min(...values), max = Math.max(...values);
      const pad = (max - min) * 0.15 || 1;
      const lo = min - pad, hi = max + pad;
      const xStep = (w - 72) / Math.max(1, points.length - 1);
      const sy = value => h - 34 - ((value - lo) / (hi - lo)) * (h - 72);
      ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 3; ctx.beginPath();
      points.forEach((p, i) => { const x = 36 + i * xStep, y = sy(p.y); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
      ctx.stroke();
      points.forEach((p, i) => { const x = 36 + i * xStep, y = sy(p.y); ctx.fillStyle = '#e2e8f0'; ctx.beginPath(); ctx.arc(x, y, 3.8, 0, Math.PI * 2); ctx.fill(); });
      ctx.fillStyle = '#cbd5e1'; ctx.font = '13px Inter, sans-serif'; ctx.fillText(`metric=${metric} | min=${min.toFixed(2)} | max=${max.toFixed(2)}`, 26, 18);
      document.getElementById('chartSummary').textContent = JSON.stringify(points.slice(-6).reverse(), null, 2);
    }
    async function refreshAll(manual=false){
      try {
        const [statusRes, collectorRes, eventsRes] = await Promise.all([
          fetchJson('/status'),
          fetchJson('/collector/status'),
          fetchJson(`/events?limit=${document.getElementById('logLimit').value}`)
        ]);
        let portfolioRes;
        try {
          portfolioRes = await fetchJson('/portfolio/live');
        } catch (liveErr) {
          portfolioRes = await fetchJson('/portfolio');
        }
        renderOverview(statusRes.body, collectorRes.body);
        renderPortfolio(portfolioRes.body);
        const newCount = eventsRes.body.filter(ev => upsertEvent(ev)).length;
        renderEvents();
        drawChart();
        setBadge('tagLatency', `${statusRes.elapsed}ms`, '');
        document.getElementById('tagAuto').textContent = document.getElementById('autoRefresh').checked ? 'ON' : 'OFF';
        document.getElementById('tagNotify').textContent = document.getElementById('notifyToggle').checked ? 'ON' : 'OFF';
        refreshLabel(getRefreshIntervalMs());
        if (manual) toast('새로고침', `상태, 포트폴리오, 이벤트를 갱신했습니다. (${newCount}개)`);
      } catch (err) {
        document.getElementById('healthDot').className = 'dot bad';
        document.getElementById('healthText').textContent = '서버 오류';
        setBadge('tagServer', '오류', 'bad');
        toast('새로고침 실패', String(err), 'warn');
      }
    }
    async function connectWebSocket(){
      try {
        if (state.ws) { try { state.ws.close(); } catch {} }
        const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${scheme}://${location.host}/ws/events`);
        state.ws = ws;
        setWsState('연결 중', 'warn');
        ws.onopen = () => { setWsState('연결됨', 'good'); state.wsBackoff = 1500; };
        ws.onmessage = (ev) => {
          try {
            const packet = JSON.parse(ev.data);
            const event = packet.event || packet;
            if (upsertEvent(event)) {
              applyLiveEvent(event);
              renderEvents();
              drawChart();
              setBadge('tagEvents', String(state.events.length), '');
            }
          } catch (err) {
            console.warn('ws parse error', err);
          }
        };
        ws.onerror = () => setWsState('오류', 'bad');
        ws.onclose = () => {
          setWsState('재연결 대기', 'warn');
          window.setTimeout(() => { if (document.body.contains(document.getElementById('wsState'))) connectWebSocket(); }, state.wsBackoff);
          state.wsBackoff = Math.min(state.wsBackoff * 1.5, 8000);
        };
      } catch (err) {
        setWsState('실패', 'bad');
      }
    }
    async function runPredict(){
      const started = performance.now();
      const { body } = await fetchJson('/predict', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload()) });
      setMetric('cardSignal', body.signal.toUpperCase());
      setBadge('tagAction', '예측', '');
      setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
      toast('예측 완료', `${body.signal} / 신뢰도 ${body.confidence}`, body.signal === 'buy' ? 'good' : body.signal === 'sell' ? 'warn' : '');
      await refreshAll();
    }
    async function runPlan(){
      const started = performance.now();
      const { body } = await fetchJson('/plan', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload()) });
      setMetric('cardQuantity', String(body.quantity));
      setBadge('tagAction', '주문 계획', 'good');
      setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
      toast('주문 계획', `${body.signal} / 수량 ${body.quantity}`, body.quantity > 0 ? 'good' : '');
      await refreshAll();
    }
    async function runBacktest(){
      const started = performance.now();
      const snap = payload();
      const { body } = await fetchJson('/backtest', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ initial_cash: Number(document.getElementById('cash').value), snapshots: [ snap, Object.assign({}, snap, { price: Math.max(1, snap.price * 0.98), moving_average_short: snap.moving_average_short * 0.97, moving_average_long: snap.moving_average_long * 1.01, rsi: 75, sentiment: -0.2 }), Object.assign({}, snap, { price: snap.price * 1.03, moving_average_short: snap.moving_average_short * 1.02, moving_average_long: snap.moving_average_long * 0.99, rsi: 48, sentiment: 0.2 }) ] }) });
      setMetric('cardReturn', `${body.return_pct}%`);
      setBadge('tagAction', '백테스트', 'warn');
      setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
      toast('백테스트', `수익률 ${body.return_pct}% / 거래 ${body.trades}건`, body.return_pct >= 0 ? 'good' : 'warn');
      await refreshAll();
    }
    async function loadLiveSnapshot(){
      const symbol = document.getElementById('collectorSymbol').value.trim() || document.getElementById('portfolioPick').value || document.getElementById('symbol').value.trim();
      if (!symbol) { toast('종목 없음', '먼저 종목코드나 보유종목을 선택하세요.', 'warn'); return; }
      try {
        const { body } = await fetchJson(`/market/${encodeURIComponent(symbol)}`);
        document.getElementById('price').value = body.price;
        document.getElementById('maShort').value = body.moving_average_short;
        document.getElementById('maLong').value = body.moving_average_long;
        document.getElementById('rsi').value = body.rsi ?? 50;
        document.getElementById('volume').value = body.volume ?? 0;
        state.latestSnapshot = body;
        toast('실데이터 반영', `${symbol} 시세를 입력 패널에 반영했습니다.`, 'good');
        await refreshAll(true);
      } catch (err) {
        toast('실데이터 실패', String(err), 'warn');
      }
    }
    function requestNotificationPermission(){ if (!('Notification' in window)) return toast('알림', '브라우저가 알림 API를 지원하지 않습니다.'); Notification.requestPermission(); }
    document.getElementById('autoRefresh').addEventListener('change', () => { document.getElementById('tagAuto').textContent = document.getElementById('autoRefresh').checked ? 'ON' : 'OFF'; scheduleRefreshTimer(); });
    document.getElementById('marketAwareRefresh').addEventListener('change', scheduleRefreshTimer);
    document.getElementById('notifyToggle').addEventListener('change', () => { document.getElementById('tagNotify').textContent = document.getElementById('notifyToggle').checked ? 'ON' : 'OFF'; });
    document.getElementById('logKind').addEventListener('change', renderEvents);
    document.getElementById('logQuery').addEventListener('input', renderEvents);
    document.getElementById('logLimit').addEventListener('change', async () => { await refreshAll(true); });
    document.getElementById('chartMetric').addEventListener('change', drawChart);
    document.getElementById('chartWindow').addEventListener('change', drawChart);
    document.getElementById('portfolioPick').addEventListener('change', syncSelectedPortfolio);
    setInterval(updateClock, 1000);
    updateClock();
    refreshAll(true);
    connectWebSocket();
    scheduleRefreshTimer();
    document.getElementById('refreshEvery').addEventListener('change', scheduleRefreshTimer);
    drawChart();
  </script>
</body>
</html>"""
