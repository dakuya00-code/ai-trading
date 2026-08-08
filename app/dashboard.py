from __future__ import annotations

from textwrap import dedent


def dashboard_html() -> str:
    return dedent('''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>ai-trading 모니터링 대시보드</title>
      <style>
        :root {
          --bg: #06101f;
          --panel: rgba(15, 23, 42, 0.84);
          --card: rgba(17, 24, 39, 0.88);
          --line: rgba(148, 163, 184, 0.16);
          --text: #e5eefc;
          --muted: #94a3b8;
          --accent: #38bdf8;
          --good: #22c55e;
          --warn: #f59e0b;
          --bad: #f87171;
          --shadow: 0 24px 80px rgba(2, 6, 23, 0.45);
          --radius: 22px;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          color: var(--text);
          font-family: Inter, Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background:
            radial-gradient(circle at top left, rgba(56,189,248,.22), transparent 30%),
            radial-gradient(circle at top right, rgba(34,197,94,.14), transparent 25%),
            linear-gradient(180deg, #020617 0%, #06101f 48%, #0f172a 100%);
        }
        .shell { max-width: 1460px; margin: 0 auto; padding: 24px; }
        .topbar {
          display: flex; justify-content: space-between; gap: 16px; align-items: center;
          padding: 20px 24px; border-radius: var(--radius); background: var(--panel); border: 1px solid var(--line);
          box-shadow: var(--shadow); backdrop-filter: blur(18px);
        }
        h1 { margin: 0; font-size: 30px; letter-spacing: -0.03em; }
        .sub { margin-top: 8px; color: var(--muted); }
        .top-right { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }
        .pill {
          display: inline-flex; gap: 8px; align-items: center; padding: 10px 14px;
          border-radius: 999px; background: rgba(30,41,59,.86); border: 1px solid var(--line);
          font-size: 13px;
        }
        .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--muted); }
        .dot.ok { background: var(--good); }
        .dot.bad { background: var(--bad); }
        .grid { display: grid; gap: 18px; margin-top: 18px; }
        .cards-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .cards-3 { grid-template-columns: 1.1fr 1fr 1fr; }
        .results { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .card {
          background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
          box-shadow: var(--shadow); padding: 20px; backdrop-filter: blur(16px);
        }
        .card h2 { margin: 0 0 14px; font-size: 16px; }
        .metric { margin: 0; font-size: 30px; font-weight: 700; letter-spacing: -0.03em; }
        .muted { color: var(--muted); }
        .metric-sub { margin-top: 6px; color: var(--muted); font-size: 13px; }
        .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
        label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
        input {
          width: 100%; padding: 12px 13px; border-radius: 14px; border: 1px solid rgba(148,163,184,.22);
          background: rgba(2,6,23,.72); color: var(--text); outline: none;
        }
        input:focus { border-color: rgba(56,189,248,.72); box-shadow: 0 0 0 4px rgba(56,189,248,.12); }
        .button-row, .actions { display: flex; flex-wrap: wrap; gap: 10px; }
        .button-row { margin-bottom: 14px; }
        .btn {
          padding: 12px 16px; border: 0; border-radius: 14px; cursor: pointer; color: #fff;
          background: linear-gradient(135deg, #2563eb, #0ea5e9);
        }
        .btn.secondary { background: rgba(30,41,59,.92); border: 1px solid rgba(148,163,184,.16); }
        .btn.ghost { background: transparent; border: 1px solid rgba(148,163,184,.22); color: var(--text); }
        .btn.good { background: linear-gradient(135deg, #16a34a, #22c55e); }
        .btn.warn { background: linear-gradient(135deg, #ea580c, #f59e0b); }
        .mini { padding: 9px 12px; font-size: 13px; }
        pre {
          margin: 0; min-height: 230px; white-space: pre-wrap; word-break: break-word; line-height: 1.55;
          background: rgba(2,6,23,.84); border: 1px solid rgba(148,163,184,.16); border-radius: 18px;
          padding: 16px; color: #dbeafe;
        }
        .row {
          display: flex; justify-content: space-between; gap: 10px; align-items: center;
          padding: 11px 13px; border-radius: 14px; background: rgba(15,23,42,.88); border: 1px solid rgba(148,163,184,.14);
        }
        .list { display: grid; gap: 10px; }
        .tag {
          padding: 6px 10px; border-radius: 999px; font-size: 12px;
          background: rgba(56,189,248,.12); color: #7dd3fc; border: 1px solid rgba(56,189,248,.2);
        }
        .tag.good { background: rgba(34,197,94,.12); color: #86efac; border-color: rgba(34,197,94,.22); }
        .tag.warn { background: rgba(245,158,11,.12); color: #fbbf24; border-color: rgba(245,158,11,.22); }
        .tag.bad { background: rgba(248,113,113,.12); color: #fca5a5; border-color: rgba(248,113,113,.22); }
        .footer { text-align: center; margin: 18px 0 0; color: var(--muted); font-size: 12px; }
        @media (max-width: 1180px) { .cards-4, .cards-3, .results { grid-template-columns: 1fr 1fr; } }
        @media (max-width: 760px) {
          .shell { padding: 14px; }
          .topbar { flex-direction: column; align-items: flex-start; }
          .cards-4, .cards-3, .results, .form-grid { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <main class="shell">
        <section class="topbar">
          <div>
            <h1>ai-trading 모니터링 대시보드</h1>
            <div class="sub">신호 분석, 주문 계획, 백테스트, 서버 상태를 한 화면에서 확인합니다.</div>
          </div>
          <div class="top-right">
            <div class="pill"><span id="healthDot" class="dot"></span><span id="healthText">상태 확인 중</span></div>
            <div class="pill">버전 <strong id="serviceVersion">-</strong></div>
            <div class="pill">업타임 <strong id="uptime">-</strong></div>
            <div class="pill">KST <strong id="kstClock">-</strong></div>
          </div>
        </section>

        <section class="grid cards-4">
          <div class="card"><h2>헬스</h2><p class="metric" id="cardHealth">-</p><p class="metric-sub">/status 기준</p></div>
          <div class="card"><h2>예측 신호</h2><p class="metric" id="cardSignal">-</p><p class="metric-sub">/predict 결과</p></div>
          <div class="card"><h2>주문 수량</h2><p class="metric" id="cardQuantity">-</p><p class="metric-sub">/plan 결과</p></div>
          <div class="card"><h2>백테스트 수익률</h2><p class="metric" id="cardReturn">-</p><p class="metric-sub">/backtest 결과</p></div>
        </section>

        <section class="grid cards-3">
          <div class="card">
            <h2>입력 패널</h2>
            <div class="button-row">
              <button class="btn mini" type="button" onclick="preset('bull')">상승 시나리오</button>
              <button class="btn secondary mini" type="button" onclick="preset('flat')">중립 시나리오</button>
              <button class="btn warn mini" type="button" onclick="preset('bear')">하락 시나리오</button>
            </div>
            <div class="form-grid">
              <div><label>종목코드</label><input id="symbol" value="005930.KS" /></div>
              <div><label>현재가</label><input id="price" type="number" value="72000" /></div>
              <div><label>단기 이동평균</label><input id="maShort" type="number" value="71500" /></div>
              <div><label>장기 이동평균</label><input id="maLong" type="number" value="70000" /></div>
              <div><label>RSI</label><input id="rsi" type="number" value="45" /></div>
              <div><label>심리 지표 (-1~1)</label><input id="sentiment" type="number" step="0.1" value="0.4" /></div>
              <div><label>거래량</label><input id="volume" type="number" value="1000000" /></div>
              <div><label>초기자본</label><input id="cash" type="number" value="10000000" /></div>
            </div>
            <div class="actions" style="margin-top:14px;">
              <button class="btn" type="button" onclick="runPredict()">예측 실행</button>
              <button class="btn good" type="button" onclick="runPlan()">주문 계획</button>
              <button class="btn warn" type="button" onclick="runBacktest()">백테스트</button>
              <button class="btn ghost" type="button" onclick="refreshStatus()">상태 새로고침</button>
            </div>
            <div class="muted" style="margin-top:12px; font-size:13px;">모니터링 기준: 신호 → 주문 계획 → 백테스트 → 서버 상태</div>
          </div>

          <div class="card">
            <h2>실행 로그</h2>
            <div class="list" id="activityLog"></div>
          </div>

          <div class="card">
            <h2>상태 요약</h2>
            <div class="list">
              <div class="row"><span>서버</span><span class="tag good" id="tagServer">정상</span></div>
              <div class="row"><span>API</span><span class="tag" id="tagApi">대기 중</span></div>
              <div class="row"><span>최근 작업</span><span class="tag warn" id="tagAction">없음</span></div>
              <div class="row"><span>마지막 응답</span><span class="tag" id="tagLatency">-</span></div>
            </div>
          </div>
        </section>

        <section class="grid results" style="margin-top:18px;">
          <div class="card"><h2>예측 결과</h2><pre id="predictOutput">아직 실행 전입니다.</pre></div>
          <div class="card"><h2>주문 계획</h2><pre id="planOutput">아직 실행 전입니다.</pre></div>
          <div class="card"><h2>백테스트 결과</h2><pre id="backtestOutput">아직 실행 전입니다.</pre></div>
        </section>

        <div class="footer">기본 외부 포트는 8010입니다. 운영 환경에서는 포트만 바꿔도 UI와 API를 함께 확인할 수 있습니다.</div>
      </main>

      <script>
        const state = { lastStatus: null };
        const kstFormatter = new Intl.DateTimeFormat('ko-KR', {
          timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        });
        function toNumber(id) { return Number(document.getElementById(id).value); }
        function payload() {
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
        function setJSON(id, obj) { document.getElementById(id).textContent = JSON.stringify(obj, null, 2); }
        function setMetric(id, value) { document.getElementById(id).textContent = value; }
        function setBadge(id, text, cls) {
          const el = document.getElementById(id);
          el.textContent = text;
          el.className = 'tag' + (cls ? ' ' + cls : '');
        }
        function updateClock() { document.getElementById('kstClock').textContent = kstFormatter.format(new Date()); }
        function log(message, tag='정보') {
          const time = kstFormatter.format(new Date());
          const row = document.createElement('div');
          row.className = 'row';
          row.innerHTML = `<span>${time}</span><span>${message}</span><span class="tag">${tag}</span>`;
          const logBox = document.getElementById('activityLog');
          logBox.prepend(row);
          while (logBox.children.length > 6) logBox.removeChild(logBox.lastChild);
        }
        function preset(kind) {
          const map = {
            bull: { price: 72000, maShort: 71500, maLong: 70000, rsi: 45, sentiment: 0.4 },
            flat: { price: 180000, maShort: 180000, maLong: 180000, rsi: 55, sentiment: 0.0 },
            bear: { price: 110000, maShort: 112000, maLong: 115000, rsi: 78, sentiment: -0.5 },
          }[kind];
          Object.entries(map).forEach(([k, v]) => document.getElementById(k).value = v);
          log(kind === 'bull' ? '상승 시나리오 입력' : kind === 'flat' ? '중립 시나리오 입력' : '하락 시나리오 입력');
        }
        async function fetchJson(url, options) {
          const started = performance.now();
          const res = await fetch(url, options);
          const elapsed = Math.round(performance.now() - started);
          const text = await res.text();
          let body;
          try { body = JSON.parse(text); } catch { body = text; }
          if (!res.ok) throw new Error(typeof body === 'string' ? body : JSON.stringify(body));
          return { body, elapsed };
        }
        async function refreshStatus() {
          try {
            const { body, elapsed } = await fetchJson('/status');
            state.lastStatus = body;
            setMetric('cardHealth', body.health);
            setMetric('serviceVersion', body.version);
            setMetric('uptime', body.uptime);
            setMetric('healthText', '서버 정상');
            document.getElementById('healthDot').className = 'dot ok';
            setBadge('tagServer', '정상', 'good');
            setBadge('tagApi', '활성', 'good');
            setBadge('tagLatency', `${elapsed}ms`, '');
            if (body.last_backtest_return) setMetric('cardReturn', body.last_backtest_return);
          } catch (err) {
            document.getElementById('healthDot').className = 'dot bad';
            setMetric('healthText', '서버 오류');
            setBadge('tagServer', '오류', 'bad');
            setBadge('tagApi', '비활성', 'bad');
            log('상태 확인 실패', '오류');
          }
        }
        async function runPredict() {
          const started = performance.now();
          const { body } = await fetchJson('/predict', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload())
          });
          setJSON('predictOutput', body);
          setMetric('cardSignal', body.signal.toUpperCase());
          setBadge('tagAction', '예측', '');
          setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
          log(`예측 완료: ${body.signal} / 신뢰도 ${body.confidence}`, '예측');
        }
        async function runPlan() {
          const started = performance.now();
          const { body } = await fetchJson('/plan', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload())
          });
          setJSON('planOutput', body);
          setMetric('cardQuantity', String(body.quantity));
          setBadge('tagAction', '주문 계획', 'good');
          setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
          log(`주문 계획 완료: ${body.signal} / 수량 ${body.quantity}`, '주문');
        }
        async function runBacktest() {
          const started = performance.now();
          const snap = payload();
          const { body } = await fetchJson('/backtest', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              initial_cash: Number(document.getElementById('cash').value),
              snapshots: [
                snap,
                Object.assign({}, snap, { price: Math.max(1, snap.price * 0.98), moving_average_short: snap.moving_average_short * 0.97, moving_average_long: snap.moving_average_long * 1.01, rsi: 75, sentiment: -0.2 }),
                Object.assign({}, snap, { price: snap.price * 1.03, moving_average_short: snap.moving_average_short * 1.02, moving_average_long: snap.moving_average_long * 0.99, rsi: 48, sentiment: 0.2 })
              ]
            })
          });
          setJSON('backtestOutput', body);
          setMetric('cardReturn', `${body.return_pct}%`);
          setBadge('tagAction', '백테스트', 'warn');
          setBadge('tagLatency', `${Math.round(performance.now() - started)}ms`, '');
          log(`백테스트 완료: 수익률 ${body.return_pct}%`, '백테스트');
          if (state.lastStatus) state.lastStatus.last_backtest_return = `${body.return_pct}%`;
        }
        updateClock();
        refreshStatus();
        setInterval(updateClock, 1000);
        setInterval(refreshStatus, 15000);
        log('대시보드 로드 완료', '시작');
      </script>
    </body>
    </html>
    ''').strip()
