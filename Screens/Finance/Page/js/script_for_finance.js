// =====================================================================
// SCRIPT FOR: FINANCE
// Talks only to this screen's own API (/api/finance/...) - never another
// screen's port, never an import. Split out of the page HTML so a UI
// change is a small file to open.
//
// Every number here is fetched, never invented: a value the backend did
// not send renders as a dash, not a zero (C4).
// =====================================================================

const API = '/api/finance';
const DASH = '—';

async function getJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(path + ' answered ' + res.status);
  return res.json();
}
async function postJson(path, body) {
  const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let data = {};
  try { data = await res.json(); } catch (e) {}
  return data;
}
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function money(m) {
  if (!m || !m.known) return `<span class="dash">${DASH}</span>`;
  return escapeHtml(m.text);
}
// The one Indian-style number formatter for the whole page. Callers add
// their own rupee sign and their own +/- sign, so a negative can never
// print twice-signed. (There used to be a second inr() further down the
// file; a later function declaration silently replaces an earlier one,
// which is exactly how the double-sign bug happened.)
function inr(v) {
  return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

// ─── CLOCK ──────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  const elTime = document.getElementById('clock-time');
  const elDate = document.getElementById('clock-date');
  if (elTime) elTime.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (elDate) elDate.textContent = now.toLocaleDateString([], { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
}
setInterval(tickClock, 1000);

// ─── THE PAGE TRACER ────────────────────────────────────────────────
// Every meaningful click and tab open lands in the trace ledger. This
// used to be a thin tracer defined here; it now lives once, shared by
// every screen, in Look_And_Feel/page_tracer.js - and it captures far
// more around each click (tag, id, text, active tab, session id) than
// this file ever did. The page opts in near the bottom of
// page_for_finance.html with window.INKY_TRACE = {...}.
//
// Code below that traces directly goes through window.traceEvent at
// CALL time, not load time - this file runs before the shared script,
// so an alias captured here would be undefined.
function traceEvent(kind, action, target, detail) {
  if (typeof window.traceEvent === 'function') {
    window.traceEvent(kind, action, target, detail);
  }
}

// ─── TAB SWITCHING ──────────────────────────────────────────────────
const LOADERS = {
  overview: loadOverview, investments: loadInvestments,
  portfolio: loadPortfolio, debt: loadDebt,
};
const LOADED = {};

document.querySelectorAll('.side-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.side-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    document.getElementById('pane-' + tab).classList.add('active');
    if (!LOADED[tab]) { LOADED[tab] = true; LOADERS[tab](); }
  });
});

// ─── SHARED CHART HELPERS — Apache ECharts, vendored locally ────────
// Every chart registers itself here so one hook can redraw them all on
// window resize AND on orientation change: C9's landscape query fires
// on rotation, which does not always raise a `resize` event the same
// way across browsers, so both are listened for explicitly.
const INKY_CHARTS = [];

function makeChart(el, option) {
  if (!el || typeof echarts === 'undefined') return null;
  const chart = echarts.init(el);
  chart.setOption(option);
  INKY_CHARTS.push(chart);
  return chart;
}

function resizeAllCharts() {
  INKY_CHARTS.forEach(c => { try { c.resize(); } catch (err) {} });
}
window.addEventListener('resize', resizeAllCharts);
window.addEventListener('orientationchange', () => setTimeout(resizeAllCharts, 250));

// A chart built inside a pane that was hidden has zero size until its
// pane is shown; re-measure whenever any pane flips active.
const _paneWatcher = new MutationObserver(() => setTimeout(resizeAllCharts, 60));
document.querySelectorAll('.tab-pane, .pf-pane').forEach(p => {
  _paneWatcher.observe(p, { attributes: true, attributeFilter: ['class'] });
});

function bandFor(pct) {
  if (pct === null || pct === undefined) return '';
  if (pct >= 70) return 'good';
  if (pct >= 40) return 'fair';
  return 'poor';
}

// ══════════════════════════════════════════════════════════════════
//  OVERVIEW
// ══════════════════════════════════════════════════════════════════
async function loadOverview() {
  loadHealthScore();

  let command, moneyData;
  try {
    [command, moneyData] = await Promise.all([getJson(API + '/command'), getJson(API + '/money')]);
  } catch (err) {
    document.getElementById('overview-cards').innerHTML =
      `<div class="empty-note">could not reach the Finance server: ${escapeHtml(err.message)}</div>`;
    return;
  }

  // The old top-of-page red/green gate banner is gone (2026-08-24).
  // Nothing about the gates changed: renderGates below still draws
  // every G1-G4 state - including which gate blocks and why - in its
  // own panel. The banner was a duplicate, alarming restatement.

  // Temporary, at the owner's request (2026-08-22, "for now" until the
  // 5th Sept pay cycle): the headline number on this card is
  // before_slice_refill, not surplus - it is NOT renamed to "surplus"
  // and the real surplus stays visible in the sub-line, so this stays
  // honest even while the emphasis is swapped. The gates below still
  // evaluate on the real surplus (command.surplus) - only this card's
  // display changed.
  const bigFigure = moneyData.before_slice_refill;
  const bigClass = bigFigure.known && bigFigure.raw < 0 ? 'negative' : 'positive';
  document.getElementById('kpi-surplus').innerHTML = `
    <i class="ph ph-coins kpi-icon"></i>
    <div class="kpi-label">Spending money this month</div>
    <div class="kpi-value ${bigClass}">${money(bigFigure)}</div>
    <div class="kpi-sub">before Slice refill · real surplus ${money(command.surplus)} · deployable ${money(command.deployable)}</div>`;

  document.getElementById('kpi-buffer').innerHTML = `
    <i class="ph ph-vault kpi-icon"></i>
    <div class="kpi-label">Emergency buffer</div>
    <div class="kpi-value">${money(command.buffer.fund)}</div>
    <div class="kpi-sub">tier reached: ${escapeHtml(command.buffer.tier_reached ?? DASH)}</div>
    ${bufferFillBar(command.buffer)}`;

  document.getElementById('kpi-portfolio').innerHTML = `
    <i class="ph ph-chart-pie-slice kpi-icon"></i>
    <div class="kpi-label">Portfolio total</div>
    <div><div class="kpi-value">${money(command.portfolio_total)}</div>
    <div class="kpi-sub">owned by Investments, read over the noticeboard</div></div>`;

  renderGates(command.gates, command.buffer);
  renderCountdowns(command.countdowns);

  const rows = moneyData.lines.map((l, i) => {
    const neg = l.amount.known && l.amount.raw < 0;
    return `<div class="money-row">
      <i class="${iconFor(l.label)}"></i>
      <span class="m-label">${escapeHtml(l.label)}</span>
      <span class="m-value ${neg ? 'negative' : ''}">${money(l.amount)}</span>
      <span class="sparkline-cell"></span>
    </div>`;
  }).join('');
  const totalNeg = moneyData.surplus.known && moneyData.surplus.raw < 0;
  // A second, separate figure - bills, debt & SIPs only, before the
  // Slice refill. Shown below surplus, its own row, never added into
  // the total above: it answers a different question, not a correction.
  const beforeSlice = moneyData.before_slice_refill;
  document.getElementById('money-list').innerHTML = rows + `
    <div class="money-row total">
      <i class="ph ph-calculator"></i>
      <span class="m-label"><b>Surplus</b></span>
      <span class="m-value ${totalNeg ? 'negative' : ''}">${money(moneyData.surplus)}</span>
      <span class="sparkline-cell"></span>
    </div>
    <div class="money-row" style="opacity:.8">
      <i class="ph ph-credit-card"></i>
      <span class="m-label">Before Slice refill <span class="kpi-sub">(bills, debt &amp; SIPs only)</span></span>
      <span class="m-value">${money(beforeSlice)}</span>
      <span class="sparkline-cell"></span>
    </div>`;

  // A real donut where the old decorative mini-pie ring sat: the
  // money-weighted asset split out of the stored portfolio review.
  // (The old ring's percentage was abs(total)/1000 - a shape with no
  // meaning behind it. This one plots only what the review computed.)
  const mainArea = document.querySelector('#pane-overview .area-main');
  if (mainArea && !document.getElementById('overview-allocation')) {
    mainArea.insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad" id="overview-allocation">
        <div class="panel-title"><i class="ph ph-chart-donut"></i>What the portfolio holds
          <span class="kpi-sub" style="margin-left:auto">money-weighted asset split · stored portfolio review</span></div>
        <div class="alloc-wrap">
          <div id="overview-alloc-chart" class="echart-box echart-box-sm"></div>
          <div id="overview-alloc-legend" class="split-legend"></div>
        </div>
      </div>`);
    renderAllocationDonut();
  }
}

// The Overview asset-split donut: equity / debt / cash / unknown, each
// slice exactly what build_the_portfolio_review measured. "Unknown" is
// drawn as its own grey slice, never hidden - a gap you can see is a
// gap that gets filled.
function renderAllocationDonut() {
  getJson(API + '/portfolio-analysis/review').then(r => {
    if (!r.ok || !r.has_data) return;
    const LABELS = { equity_pct: 'Equity', debt_pct: 'Debt', cash_pct: 'Cash', unknown: 'Unknown' };
    const COLORS = { Equity: '#46c98f', Debt: '#93a5f7', Cash: '#ecb44d', Unknown: '#8a97b5' };
    const parts = ((r.asset_allocation || {}).parts || [])
      .map(p => ({ name: LABELS[p.name] || p.name, value: p.percent_of_portfolio }))
      .filter(p => p.value > 0);
    if (!parts.length) return;
    makeChart(document.getElementById('overview-alloc-chart'), {
      tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
      series: [{
        type: 'pie', radius: ['52%', '78%'],
        itemStyle: { borderColor: '#111b31', borderWidth: 2 },
        label: { show: false }, data: parts.map(p => ({ ...p, itemStyle: { color: COLORS[p.name] || '#8a97b5' } })),
      }],
    });
    document.getElementById('overview-alloc-legend').innerHTML = parts.map(p =>
      `<span class="split-key"><span class="split-swatch" style="background:${COLORS[p.name] || '#8a97b5'}"></span>${escapeHtml(p.name)} <b>${p.value}%</b></span>`).join('');
  }).catch(() => {});
}

// A real fill bar for the emergency buffer: fund vs the tier amount
// itself (next_tier_target, sent already-formatted by the server - see
// the note in server_for_finance.py). Never invents a percentage for a
// tier that has been fully cleared (T2), and never divides by an
// unknown target.
function bufferFillBar(buffer) {
  const fund = buffer.fund, target = buffer.next_tier_target;
  if (!fund || !fund.known) return '';
  if (!target || !target.known) {
    return buffer.tier_reached === 'T2'
      ? `<div class="cd-progress"><span style="width:100%"></span></div>
         <div class="kpi-sub">full unlock reached</div>` : '';
  }
  const pct = target.raw > 0 ? Math.max(0, Math.min(100, (fund.raw / target.raw) * 100)) : 0;
  return `
    <div class="cd-progress"><span style="width:${pct.toFixed(1)}%"></span></div>
    <div class="kpi-sub">${money(fund)} of ${money(target)} toward ${escapeHtml(buffer.next_tier || '')} (${pct.toFixed(0)}%) · ${money(buffer.distance)} left</div>`;
}

function iconFor(label) {
  const l = label.toLowerCase();
  if (l.includes('income')) return 'ph ph-bank';
  if (l.includes('fixed')) return 'ph ph-receipt';
  if (l.includes('debt')) return 'ph ph-hand-coins';
  if (l.includes('sip')) return 'ph ph-plant';
  if (l.includes('slice') || l.includes('revolving')) return 'ph ph-credit-card';
  return 'ph ph-arrows-left-right';
}


function renderGates(gates, buffer) {
  const tips = {
    G1: 'Is there any money left over at all? Zero counts as failure - nothing to invest either way.',
    G2: 'Is the emergency fund big enough? A tiered buffer check before anything new goes in.',
    G3: 'Have you borrowed against your investments? Debt drawn blocks new deployment.',
    G4: 'Is the amount you want to put in too big? Only judged against a named figure.',
  };

  // A gate the chain never reached (state === 'not_reached') can still
  // carry a `preview`: what it would say if it ran on its own, right
  // now (gates.preview() on the backend). When that preview passes,
  // show it as green-with-a-! "in transition" instead of a flat grey
  // dash - it is NOT a real pass (the chain still stopped earlier and
  // nothing here is actually unblocked), just a more honest way of
  // saying "this one is fine, it's the others holding things up."
  //
  // G2 gets its own treatment on top of that, added 2026-08-22 at the
  // owner's request: a tiered gate that is still short of its target is
  // not the same *kind* of thing as G1/G3/G4 failing outright - it is
  // gradually filling up, and a flat red FAIL reads as more final than
  // that really is. So a failing G2 with real tier data gets an amber
  // "IN PROGRESS X%" badge and its own fill bar instead of red FAIL.
  // This changes nothing about what actually blocks: `blocked_at` and
  // `deployable` are untouched, still computed the same way, still G2
  // for real until the buffer genuinely reaches the tier. Softer paint,
  // same wall.
  document.getElementById('gates-list').innerHTML = gates.map(g => {
    const wouldPass = g.state === 'not_reached' && g.preview && g.preview.passed;
    const isBufferGate = g.gate === 'G2' && g.state === 'fail' && buffer &&
      buffer.fund && buffer.fund.known && buffer.next_tier_target && buffer.next_tier_target.known;

    let badgeClass = wouldPass ? 'would_pass' : g.state;
    let badgeLabel = wouldPass
      ? `${escapeHtml(g.gate)} <span class="transition-mark" aria-hidden="true">!</span>`
      : `${escapeHtml(g.gate)} ${escapeHtml(g.state.replace('_', ' ').toUpperCase())}`;
    let tipText = wouldPass
      ? `In transition - not actually evaluated, because the chain stopped at an earlier gate. ` +
        `If it ran on its own right now: ${g.preview.reason}`
      : (tips[g.gate] || g.reason || '');
    let bar = '';

    if (isBufferGate) {
      const pct = Math.max(0, Math.min(100,
        (buffer.fund.raw / buffer.next_tier_target.raw) * 100));
      badgeClass = 'in_progress';
      badgeLabel = `${escapeHtml(g.gate)} IN PROGRESS ${pct.toFixed(0)}%`;
      tipText = `Still blocking new investing - the buffer genuinely has not ` +
        `reached ${escapeHtml(buffer.next_tier || 'the next tier')} yet. ` +
        `${money(buffer.fund)} of ${money(buffer.next_tier_target)} saved, ` +
        `${money(buffer.distance)} left. Not a fail state that stays fixed - ` +
        `it fills as the emergency fund grows.`;
      bar = `<div class="gate-fill"><span style="width:${pct.toFixed(1)}%"></span></div>`;
    }

    return `<div class="gate-row">
      <span class="gate-badge ${badgeClass}" ${wouldPass ? 'title="in transition - see below"' : ''}>${badgeLabel}</span>
      <span>${escapeHtml(g.reason || '')}${bar}</span>
      <span class="gate-tip">${escapeHtml(tipText)}</span>
    </div>`;
  }).join('');
}

function renderCountdowns(cd) {
  // Progress is only drawn when a ledger gives a real baseline. With no
  // recorded payments there is no honest percent - the striped bar says
  // "not enough recorded yet" instead of inventing one.
  const personal = cd.personal_debt;
  const loan = cd.education_loan;
  document.getElementById('countdown-personal').innerHTML = `
    <i class="ph ph-money cd-icon"></i>
    <div style="flex:1;min-width:0">
      <div class="cd-label">Personal debt clears</div>
      <div class="cd-date">${escapeHtml(personal.clears || DASH)}</div>
      <div class="cd-sub">${personal.months_left ?? DASH} months · surplus steps ${money(personal.surplus_before)} → ${money(personal.surplus_after)}</div>
      <div class="cd-progress unknown" title="no payment history recorded yet"></div>
    </div>`;
  document.getElementById('countdown-loan').innerHTML = `
    <i class="ph ph-graduation-cap cd-icon"></i>
    <div style="flex:1;min-width:0">
      <div class="cd-label">Education loan payoff</div>
      <div class="cd-date">${escapeHtml(loan.clears || DASH)}</div>
      <div class="cd-sub">${loan.months_left ?? DASH} months · ${money(loan.interest_remaining)} interest remaining</div>
      <div class="cd-progress unknown" title="no amortisation history recorded yet"></div>
    </div>`;
}

async function loadHealthScore() {
  const el = document.getElementById('overview-score');
  let data;
  try {
    data = await getJson(API + '/health-score');
  } catch (err) {
    el.innerHTML = `<div class="empty-note">could not work out the health score: ${escapeHtml(err.message)}</div>`;
    return;
  }
  if (data.score === null) {
    el.innerHTML = `<div class="empty-note">Not enough is recorded yet to score anything. Nothing is guessed to fill the gap.</div>`;
    return;
  }

  const bars = data.categories.map(c => {
    const known = c.pct !== null && c.pct !== undefined;
    return `<div class="score-row">
      <span class="score-row-name">${escapeHtml(c.name)}</span>
      <span class="score-row-value ${known ? '' : 'unknown'}">${known ? c.pct + '%' : DASH}</span>
      <span class="score-track ${known ? '' : 'unknown'}">
        ${known ? `<span class="score-fill ${bandFor(c.pct)}" style="width:0%" data-width="${Math.max(0, Math.min(100, c.pct))}%"></span>` : ''}
      </span>
    </div>`;
  }).join('');

  el.innerHTML = `
    <div class="glass-panel raised panel-pad">
      <div class="panel-title"><i class="ph ph-heartbeat"></i>Financial health</div>
      <div class="score-wrap">
        <div id="health-gauge" class="echart-gauge" aria-label="health score gauge"></div>
        <div class="score-bars">
          ${bars}
          <div class="gauge-caption">${escapeHtml(data.signal)}</div>
        </div>
      </div>
    </div>`;

  // ECharts gauge, same gradient ring as the old SVG, animated to the
  // real score by the library's own valueAnimation.
  if (typeof echarts !== 'undefined') {
    makeChart(document.getElementById('health-gauge'), {
      series: [{
        type: 'gauge', startAngle: 90, endAngle: -270, radius: '95%',
        pointer: { show: false },
        progress: {
          show: true, overlap: false, roundCap: true, width: 13,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#6fd3c0' }, { offset: 1, color: '#9b8cf2' }]),
          },
        },
        axisLine: { roundCap: true, lineStyle: { width: 13, color: [[1, 'rgba(231,237,248,0.12)']] } },
        splitLine: { show: false }, axisTick: { show: false }, axisLabel: { show: false },
        detail: {
          valueAnimation: true, offsetCenter: [0, '-6%'], fontSize: 30, fontWeight: 700,
          color: '#e7edf8', formatter: v => Number(v).toFixed(1),
        },
        title: { offsetCenter: [0, '34%'], fontSize: 11, color: '#6d7f9b', formatter: '/ 100' },
        data: [{ value: Math.max(0, Math.min(100, data.score)) }],
      }],
    });
  }
  setTimeout(() => {
    document.querySelectorAll('#overview-score .score-fill[data-width]')
      .forEach(b => { b.style.width = b.dataset.width; });
  }, 120);
}


// ══════════════════════════════════════════════════════════════════
//  INVESTMENTS - snapshot editor + NAV ledger + XIRR + ask-AI
// ══════════════════════════════════════════════════════════════════
async function loadInvestments() {
  const el = document.getElementById('investments-body');
  let data, navs = { has_data: false, rows: [] }, xirr = { has_data: false, holdings: [], skipped: [] };
  try {
    [data, navs, xirr] = await Promise.all([
      getJson(API + '/investments'),
      getJson(API + '/investments/nav-ledger'),
      getJson(API + '/investments/xirr').catch(() => xirr),
    ]);
  } catch (err) {
    el.innerHTML = `<div class="empty-note">could not load: ${escapeHtml(err.message)}</div>`;
    return;
  }

  // Both per-fund sources join onto the snapshot BY THE FUND - the NAV
  // ledger by AMFI code, XIRR by scheme name - so one table carries what
  // used to be three stacked panels.
  const navByCode = {};
  navs.rows.forEach(r => { navByCode[r.amfi_code] = r; });
  const xirrByName = {};
  (xirr.holdings || []).forEach(h => { xirrByName[h.name] = h; });

  let snapshotBlock;
  if (!data.has_snapshot) {
    snapshotBlock = `<div class="empty-note">${escapeHtml(data.snapshot_note)}</div>`;
  } else {
    // Merged view: mutual funds first, then ETF/equity held directly.
    // Each group is announced by a separator row so a direct holding is
    // visible as direct, and every row keeps its identifier (AMFI code)
    // on the line with it - the same book, one table, two labelled
    // sections.
    const mfHoldings = data.snapshot_holdings.filter(h => h.category === 'mutual_fund');
    const eqHoldings = data.snapshot_holdings.filter(h => h.category !== 'mutual_fund');

    const rowHtml = h => {
      const nav = h.amfi_code ? navByCode[h.amfi_code] : null;
      let navCell;
      if (nav) {
        navCell = `${escapeHtml(String(nav.nav))} <div class="kpi-sub">as of ${escapeHtml(nav.nav_date)}</div>`
          + (nav.state === 'fresh'
            ? `<span class="badge-fresh">fresh ${nav.age_days}d</span>`
            : `<span class="badge-stale">stale ${nav.age_days ?? '?'}d</span>`);
      } else {
        navCell = `${DASH} <div class="kpi-sub">${h.amfi_code ? 'no NAV on file' : 'not tracked yet'}</div>`;
      }
      const x = xirrByName[h.scheme_name];
      const xirrCell = x
        ? `<span class="${x.xirr_pct >= 0 ? 'positive' : 'negative'}">${x.xirr_pct}%</span><div class="kpi-sub">${x.transactions} txns</div>`
        : `${DASH}<div class="kpi-sub">needs txns</div>`;
      return `
      <tr data-scheme="${escapeHtml(h.scheme_name)}" data-code="${escapeHtml(h.amfi_code)}">
        <td class="label-cell">${escapeHtml(h.scheme_name)}
          <div class="kpi-sub">${h.category === 'mutual_fund' ? 'mutual fund' : escapeHtml(h.category)} ${h.amfi_code ? '&middot; id ' + escapeHtml(h.amfi_code) : ''}</div>
        </td>
        <td>${money(h.invested)}</td>
        <td><input type="number" class="edit-field" data-field="current" value="${h.current.raw ?? ''}" step="0.01"></td>
        <td class="${h.pl_abs.raw >= 0 ? 'positive' : 'negative'}">${money(h.pl_abs)} (${h.pl_pct ?? DASH}%)</td>
        <td class="nowrap-cell">${navCell}</td>
        <td class="nowrap-cell">${xirrCell}</td>
        <td><input type="text" class="edit-field" data-field="units" value="${h.units ?? ''}" placeholder="${DASH}" style="width:90px"></td>
        <td>
          <div class="row-btns">
            <button class="mini-btn analysis-btn">analysis</button>
            <button class="mini-btn save-holding">save</button>
            <button class="mini-btn refuse delete-holding">delete</button>
          </div>
        </td>
      </tr>`;
    };

    // Group separators: mutual funds first, then ETF/equity held
    // directly - the merged view marker, visible before the first row.
    const groupRow = (label, n) => n ? `<tr class="holdings-group-row"><td colspan="8">${label} — ${n}</td></tr>` : '';
    const rows =
      groupRow('Mutual funds', mfHoldings.length) +
      mfHoldings.map(rowHtml).join('') +
      groupRow('ETF &amp; equity — held directly', eqHoldings.length) +
      eqHoldings.map(rowHtml).join('');

    snapshotBlock = `
      <div class="kpi-row">
        <div class="glass-panel kpi-card"><i class="ph ph-trend-down kpi-icon"></i><div class="kpi-label">Invested</div><div class="kpi-value">${money(data.snapshot_total_invested)}</div></div>
        <div class="glass-panel kpi-card"><i class="ph ph-trend-up kpi-icon"></i><div class="kpi-label">Current value</div><div class="kpi-value">${money(data.snapshot_total_current)}</div></div>
        <div class="glass-panel kpi-card"><i class="ph ph-scales kpi-icon"></i><div class="kpi-label">Gain / loss</div><div class="kpi-value ${data.snapshot_total_pl.raw >= 0 ? 'positive' : 'negative'}">${money(data.snapshot_total_pl)}</div></div>
      </div>
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-wallet"></i>Holdings snapshot &mdash; merged view: ${mfHoldings.length} mutual fund${mfHoldings.length === 1 ? '' : 's'} + ${eqHoldings.length} ETF/equity &mdash; edit current value or units, then Save
          <span style="margin-left:auto;display:flex;gap:6px">
            <button class="mini-btn" id="analysis-refresh-btn">pull fund data now</button>
            <button class="mini-btn" id="nav-refresh-btn">update NAVs now</button>
          </span>
        </div>
        <div class="scroll-x"><table class="data-table">
          <thead><tr><th>scheme</th><th>invested</th><th>current</th><th>gain/loss</th><th>NAV</th><th>XIRR</th><th>units</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
      </div>`;
  }
  renderInvestmentsTail(el, snapshotBlock);
}


function renderInvestmentsTail(el, snapshotBlock) {
  el.innerHTML = `${snapshotBlock}
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-plus-circle"></i>Add a holding</div>
      <div class="add-holding-row">
        <input type="text" id="add-name" placeholder="Scheme name">
        <input type="text" id="add-code" placeholder="AMFI code / ISIN (optional)">
        <input type="text" id="add-category" placeholder="mutual_fund / etf / other" value="mutual_fund">
        <input type="number" id="add-invested" placeholder="Invested" step="0.01">
        <input type="number" id="add-current" placeholder="Current value" step="0.01">
        <button class="mini-btn" id="add-holding-btn">add</button>
      </div>
    </div>
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-chats-circle"></i>Ask INKY about your holdings</div>
      <div class="ask-strip">
        <input type="text" id="invest-ask-input" placeholder="e.g. which fund is doing worst, and by how much?" maxlength="300">
        <button class="mini-btn" id="invest-ask-btn">ASK</button>
      </div>
      <div class="ask-answer" id="invest-ask-answer"></div>
    </div>`;

  wireHoldingEditors();
  wireAskStrip('invest-ask-btn', 'invest-ask-input', 'invest-ask-answer', '/investments/ask');
  document.getElementById('nav-refresh-btn').addEventListener('click', async () => {
    const btn = document.getElementById('nav-refresh-btn');
    btn.textContent = 'fetching…'; btn.disabled = true;
    try { await postJson(API + '/investments/nav-ledger/update', {}); loadInvestments(); }
    finally { btn.textContent = 'update NAVs now'; btn.disabled = false; }
  });
  document.getElementById('analysis-refresh-btn').addEventListener('click', async () => {
    const btn = document.getElementById('analysis-refresh-btn');
    btn.textContent = 'pulling…'; btn.disabled = true;
    try { await postJson(API + '/investments/fund-analysis/refresh', {}); loadInvestments(); }
    finally { btn.textContent = 'pull fund data now'; btn.disabled = false; }
  });
}

function wireAskStrip(btnId, inputId, answerId, endpoint) {
  const btn = document.getElementById(btnId);
  const input = document.getElementById(inputId);
  const answer = document.getElementById(answerId);
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) return;
    btn.textContent = 'thinking…'; btn.disabled = true;
    answer.classList.add('show'); answer.textContent = 'asking the router…';
    try {
      const result = await postJson(API + endpoint, { message: text });
      answer.textContent = result.ok
        ? result.reply
        : (result.reason || result.problem || result.note || 'That could not be answered.');
    } catch (err) {
      answer.textContent = 'could not ask: ' + err.message;
    } finally {
      btn.textContent = 'ASK'; btn.disabled = false;
    }
  });
  input.addEventListener('keydown', e => { if (e.key === 'Enter') btn.click(); });
}


function wireHoldingEditors() {
  document.querySelectorAll('.save-holding').forEach(btn => btn.addEventListener('click', async () => {
    const tr = btn.closest('tr');
    const changes = {};
    tr.querySelectorAll('.edit-field').forEach(input => {
      const v = input.value.trim();
      changes[input.dataset.field] = v === '' ? null : (input.type === 'number' ? Number(v) : v);
    });
    const body = { scheme_name: tr.dataset.scheme, amfi_code: tr.dataset.code, ...changes };
    const res = await fetch(API + '/investments/holdings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    if (res.ok) loadInvestments();
    else alert('could not save that holding');
  }));

  document.querySelectorAll('.delete-holding').forEach(btn => btn.addEventListener('click', async () => {
    const tr = btn.closest('tr');
    if (!confirm(`Delete ${tr.dataset.scheme}?`)) return;
    const url = API + '/investments/holdings?scheme_name=' + encodeURIComponent(tr.dataset.scheme) +
      '&amfi_code=' + encodeURIComponent(tr.dataset.code);
    const res = await fetch(url, { method: 'DELETE' });
    if (res.ok) loadInvestments();
    else alert('could not delete that holding');
  }));

  const addBtn = document.getElementById('add-holding-btn');
  if (addBtn) addBtn.addEventListener('click', async () => {
    const body = {
      scheme_name: document.getElementById('add-name').value.trim(),
      amfi_code: document.getElementById('add-code').value.trim(),
      category: document.getElementById('add-category').value.trim() || 'mutual_fund',
      invested: Number(document.getElementById('add-invested').value),
      current: Number(document.getElementById('add-current').value),
    };
    if (!body.scheme_name || !body.invested || !body.current) {
      alert('name, invested and current are all required');
      return;
    }
    const res = await fetch(API + '/investments/holdings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const data = await res.json();
    if (res.ok) loadInvestments();
    else alert(data.problem || 'could not add that holding');
  });
}

// ══════════════════════════════════════════════════════════════════
//  PORTFOLIO ANALYSIS - concentration bar, overlap, sectors, ask-AI
// ══════════════════════════════════════════════════════════════════
async function loadPortfolio() {
  const el = document.getElementById('portfolio-body');
  el.innerHTML = '<div class="empty-note">reading the whole portfolio…</div>';
  let data;
  try { data = await getJson(API + '/portfolio-analysis/review'); }
  catch (err) { el.innerHTML = `<div class="empty-note">could not load: ${escapeHtml(err.message)}</div>`; return; }

  // Market extras (IPO calendar, G-Sec notes, price ledger) decorate the
  // tab - if that endpoint cannot be reached, its panels simply do not
  // draw and the analysis itself is untouched.
  let extras = null;
  try { extras = await getJson(API + '/market/extras'); } catch (err) { extras = null; }

  if (!data.ok || !data.has_data) {
    el.innerHTML = `<div class="empty-note">${escapeHtml(data.note || 'Nothing is recorded yet to review.')}</div>`;
    return;
  }
  // renderReview now builds the whole tab, sub-tabs and ask strip
  // included - there is nothing left to append after it.
  renderReview(el, data, extras);
}



const OBS_BADGE = { flag: '<span class="badge-stale">flag</span>',
                    watch: '<span class="badge-fresh">watch</span>',
                    info: '' };

/* One stacked bar + legend for a money-weighted split (asset class,
   market cap). The unknown slice is striped, never blank - an honest
   gap is visible, not invisible. */
function splitBar(parts) {
  const FILLS = {
    equity: 'linear-gradient(90deg,#57c79a,#3f9e77)',
    debt:   'linear-gradient(90deg,#7ba7e8,#4f7fd4)',
    cash:   'linear-gradient(90deg,#e3c25a,#c9a227)',
    large:  'linear-gradient(90deg,#57c79a,#3f9e77)',
    mid:    'linear-gradient(90deg,#e8b45a,#d99a2b)',
    small:  'linear-gradient(90deg,#e08a6a,#c95f3d)',
    unknown: 'repeating-linear-gradient(45deg,#b9b9c9 0 6px,#d8d8e4 6px 12px)',
  };
  const segs = parts.filter(p => p.pct > 0).map(p => `
      <span class="split-seg ${p.cls === 'unknown' ? 'split-unknown' : ''}"
            style="width:${Math.min(100, p.pct)}%;background:${FILLS[p.cls] || FILLS.unknown}"
            title="${escapeHtml(p.label)}: ${p.pct}%"></span>`).join('');
  const legend = parts.filter(p => p.pct > 0 || p.cls === 'unknown').map(p => `
      <span class="split-key"><span class="split-swatch ${p.cls === 'unknown' ? 'split-unknown' : ''}" style="${p.cls === 'unknown' ? '' : 'background:' + (FILLS[p.cls] || FILLS.unknown)}"></span>${escapeHtml(p.label)} <b>${p.pct}%</b></span>`).join('');
  return `<div class="split-bar">${segs}</div><div class="split-legend">${legend}</div>`;
}

/* Five short panes behind one pill row - the whole-portfolio review
   used to be a single endless scroll, which read like reference
   documentation instead of a dashboard. Which pane is open survives
   between visits in localStorage, same rule as the fund modal. */
const PF_TABS = [
  { id: 'dash',    label: 'Dashboard',          icon: 'ph-gauge' },
  { id: 'splits',  label: 'Splits & scorecard', icon: 'ph-chart-pie-slice' },
  { id: 'overlap', label: 'Overlap',            icon: 'ph-intersect' },
  { id: 'flags',   label: 'Reviewer flags',     icon: 'ph-flag' },
  { id: 'method',  label: 'Professional read',  icon: 'ph-book-open' },
];

function renderReview(el, r, extras) {
  const t = r.totals;
  const look = r.look_through || {};
  const asset = r.asset_allocation || {};
  const caps = r.market_cap_split || {};
  const sectors = (r.sector_allocation && r.sector_allocation.sectors) || [];
  const score = (r.scorecard && r.scorecard.rows) || [];
  const pairs = (r.overlap && r.overlap.pairs) || [];
  const xirr = r.portfolio_xirr || {};
  const obs = (r.observations || [])
    .sort((a, b) => ({flag: 0, watch: 1, info: 2}[a.level] - {flag: 0, watch: 1, info: 2}[b.level]));
  const flagCount = obs.filter(o => o.level === 'flag').length;

  // ── Hero numbers + the sub-tab skeleton ───────────────────────────
  el.innerHTML = `
    <div class="kpi-row pf-hero">
      <div class="glass-panel kpi-card"><i class="ph ph-wallet kpi-icon"></i><div class="kpi-label">Portfolio value</div><div class="kpi-value">₹${t.current.toLocaleString('en-IN')}</div><div class="kpi-sub">${t.how_many_holdings} holdings · built ${escapeHtml(r.built_on)}</div></div>
      <div class="glass-panel kpi-card"><i class="ph ph-trend-up kpi-icon"></i><div class="kpi-label">Gain / loss</div><div class="kpi-value ${t.pl_abs >= 0 ? 'positive' : 'negative'}">${t.pl_abs >= 0 ? '+' : '&minus;'}₹${inr(Math.abs(t.pl_abs))}</div><div class="kpi-sub">${t.pl_pct ?? DASH}% on ₹${t.invested.toLocaleString('en-IN')} invested</div></div>
      <div class="glass-panel kpi-card"><i class="ph ph-buildings kpi-icon"></i><div class="kpi-label">Companies behind the funds</div><div class="kpi-value">${look.has_data ? look.companies_you_own : DASH}</div><div class="kpi-sub">after opening every fund up</div></div>
      <div class="glass-panel kpi-card"><i class="ph ph-cube-transparent kpi-icon"></i><div class="kpi-label">Effective no. of stocks</div><div class="kpi-value">${look.has_data ? look.effective_number_of_stocks : DASH}</div><div class="kpi-sub">1 ÷ HHI${look.has_data ? ' (' + look.hhi + ')' : ''} - the bets it behaves like</div></div>
      ${xirr.has_data ? `<div class="glass-panel kpi-card"><i class="ph ph-percent kpi-icon"></i><div class="kpi-label">Overall portfolio XIRR</div><div class="kpi-value ${xirr.xirr_pct >= 0 ? 'positive' : 'negative'}">${xirr.xirr_pct ?? DASH}${xirr.xirr_pct != null ? '%' : ''}</div><div class="kpi-sub">money-weighted, all ${xirr.cashflows_counted ?? DASH} cashflows since ${escapeHtml(xirr.first_cashflow || DASH)}</div></div>` : ''}
    </div>
    <div class="pf-subnav" role="tablist">
      ${PF_TABS.map(tb => `
        <button class="pf-subtab" data-pf="${tb.id}" role="tab">
          <i class="ph ph-${tb.icon}"></i>${tb.label}
          ${tb.id === 'flags' && flagCount ? `<span class="pf-count">${flagCount}</span>` : ''}
        </button>`).join('')}
    </div>
    ${PF_TABS.map((tb, i) => `<div class="pf-pane${i === 0 ? ' active' : ''}" id="pf-pane-${tb.id}"></div>`).join('')}`;

  const pane = id => el.querySelector('#pf-pane-' + id);

  // ── DASHBOARD pane ────────────────────────────────────────────────
  // ── Concentration ─────────────────────────────────────────────────
  pane('dash').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-gauge"></i>Concentration — how much rides on ten names
        ${r.settings_verified_by_a_person === false ? '<span class="kpi-sub" style="margin-left:auto">thresholds unverified · benchmark ' + escapeHtml(r.benchmark) + '</span>' : ''}</div>
      ${look.has_data ? `
        <div class="concentration-track"><span class="concentration-fill" style="width:${Math.min(100, look.top_ten_percent)}%"></span></div>
        <div class="kpi-sub" style="margin-top:6px"><b>${look.top_ten_percent}%</b> of analysed value sits in the top 10 companies (under ~25% is spread wide; over ~40% is one bet wearing a diversification costume). Biggest single bet: <b>${escapeHtml(look.biggest_single_bet.stock)}</b> at ${look.biggest_single_bet.percent_of_everything}%.</div>`
        : `<div class="empty-note">${escapeHtml(look.note || 'Look-through needs published portfolios.')}</div>`}
    </div>`);

  // ── DASHBOARD pane (continued): asset class + market cap ──────────
  pane('dash').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-chart-pie-slice"></i>Asset allocation — money-weighted across every analysed fund</div>
      ${asset.has_data ? splitBar(asset.parts.map(p => ({
          label: p.name.replace(/_pct$/, ''),
          pct: p.percent_of_portfolio,
          cls: p.name === 'equity_pct' ? 'equity' : p.name === 'debt_pct' ? 'debt' : p.name === 'cash_pct' ? 'cash' : 'unknown' })))
        : `<div class="empty-note">${escapeHtml(asset.note || 'Needs published portfolios - run the daily pull.')}</div>`}
      ${asset.has_data && asset.unknown_percent > 0 ? `<div class="kpi-sub">${asset.unknown_percent}% of the portfolio is not yet analysed and sits in the unknown slice - named below, never hidden.</div>` : ''}
    </div>
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-buildings"></i>Market cap split — Large / Mid / Small</div>
      ${caps.has_data ? splitBar(caps.parts.map(p => ({
          label: p.name.replace(/_pct$/, ''),
          pct: p.percent_of_portfolio,
          cls: p.name === 'large_cap_pct' ? 'large' : p.name === 'mid_cap_pct' ? 'mid' : p.name === 'small_cap_pct' ? 'small' : 'unknown' })))
        : `<div class="empty-note">Needs published portfolios.</div>`}
    </div>`);

  // ── DASHBOARD pane (continued): allocation drift vs targets ───────
  // Actual asset-class weight against its target, one bar per class.
  // The tick marks where the target sits; a class without a target
  // prints dashes, never zeros. A band is a measuring stick - the
  // panel never says what to buy or sell (C5).
  const drift = r.allocation_drift;
  if (drift && drift.has_data) {
    const driftRows = (drift.rows || []).map(d => {
      const hasTarget = d.target_pct !== null && d.target_pct !== undefined;
      const hasDrift = d.drift_pp !== null && d.drift_pp !== undefined;
      const unknown = d.asset_class === 'unknown';
      return `
        <div class="drift-row">
          <span class="drift-name" title="${escapeHtml(d.asset_class)}">${escapeHtml(d.asset_class)}</span>
          <span class="drift-track">
            <span class="drift-fill${unknown ? ' striped' : ''}" style="width:${Math.max(0, Math.min(100, d.actual_pct ?? 0))}%"></span>
            ${hasTarget ? `<span class="drift-target" style="left:${Math.min(100, d.target_pct)}%" title="target ${d.target_pct}%"></span>` : ''}
          </span>
          <span class="drift-num">act <b>${d.actual_pct ?? DASH}%</b></span>
          <span class="drift-num">tgt <b>${hasTarget ? d.target_pct + '%' : DASH}</b></span>
          <span class="drift-num ${hasDrift ? (d.drift_pp >= 0 ? 'positive' : 'negative') : ''}">${hasDrift ? (d.drift_pp > 0 ? '+' : '') + d.drift_pp + 'pp' : DASH}</span>
          ${d.past_flag_line ? '<span class="badge-stale">past band</span>' : ''}
        </div>`;
    }).join('');
    pane('dash').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-arrows-out-line-horizontal"></i>Allocation vs target — how far each class has drifted
          ${drift.unverified_badge ? `<span class="badge-stale" style="margin-left:auto">${escapeHtml(drift.unverified_badge)} targets</span>` : ''}</div>
        ${driftRows || `<div class="empty-note">${DASH} no drift rows computed yet.</div>`}
        <div class="method-note">Bar = actual weight · tick = target · drift in percentage points. Flag line at ${escapeHtml(String(drift.flag_threshold_pp ?? DASH))}pp.
        ${(drift.classes_past_flag_line || []).length ? `Outside it: ${escapeHtml(drift.classes_past_flag_line.join(', '))}.` : ''}
        Targets are unverified until their owner confirms them; a band is never an instruction to trade (C5).</div>
      </div>`);
  }

  // ── SPLITS & SCORECARD pane ───────────────────────────────────────
  // Sector spread, now led by a coverage strip: how much of the
  // analysed value actually carries a sector. The remainder is striped,
  // never blank - an honest gap is visible, not invisible.
  const sa = r.sector_allocation || {};
  if (sa.has_data) {
    const coverage = sa.classified_coverage_pct;
    const knownCoverage = coverage !== null && coverage !== undefined;
    const remainder = knownCoverage ? Math.max(0, 100 - coverage) : null;
    pane('splits').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-stack"></i>Sector spread — money-weighted
          ${sa.verified_by_a_person === false ? '<span class="badge-stale" style="margin-left:auto">[UNVERIFIED] sector map</span>' : ''}</div>
        ${knownCoverage ? `
        <div class="split-bar">
          <span class="split-seg" style="width:${Math.min(100, coverage)}%;background:linear-gradient(90deg,#57c79a,#3f9e77)" title="classified: ${coverage}% of the analysed value"></span>
          <span class="split-seg" style="width:${remainder}%;background:repeating-linear-gradient(45deg,#b9b9c9 0 6px,#d8d8e4 6px 12px)" title="not yet classified: ${remainder}%"></span>
        </div>
        <div class="split-legend">
          <span class="split-key"><span class="split-swatch" style="background:linear-gradient(90deg,#57c79a,#3f9e77)"></span>classified <b>${coverage}%</b></span>
          <span class="split-key"><span class="split-swatch" style="background:repeating-linear-gradient(45deg,#b9b9c9 0 6px,#d8d8e4 6px 12px)"></span>not yet classified <b>${remainder}%</b></span>
        </div>
        <div class="kpi-sub" style="margin-top:4px">Sector coverage: ${coverage}% of the ₹${inr(sa.analysed_value ?? 0)} analysed value matched a sector${sa.verified_by_a_person === false ? ' [UNVERIFIED]' : ''}.</div>`
        : `<div class="empty-note">${DASH} no coverage computed yet - the sector map has no classified share to show.</div>`}
        ${sectors.length ? sectors.slice(0, 12).map(s => `
          <div class="score-row">
            <span class="score-row-name">${escapeHtml(s.name)}</span>
            <span class="score-row-value">${pct(s.percent_of_portfolio)}</span>
            <span class="score-track"><span class="score-fill ${s.percent_of_portfolio > 30 ? 'poor' : 'fair'}" style="width:${Math.max(0, Math.min(100, s.percent_of_portfolio || 0))}%"></span></span>
          </div>`).join('')
        : '<div class="empty-note">No sector data yet.</div>'}
      </div>`);

  // ── The look-through table: the companies you really own ──────────
  // Direct equity/ETF holdings sit inside the same list now - the
  // symbol shows when a tax-lot identifier exists for it, and a held
  // row is badged "direct" with its category beside it.
  if (look.has_data) {
    const symByScheme = {};
    ((r.direct_tax_lots && r.direct_tax_lots.holdings) || []).forEach(h => {
      if (h.scheme_name && h.transaction_identifier) symByScheme[h.scheme_name] = h.transaction_identifier;
    });
    const companyRows = (look.companies || []).slice(0, 15).map(c => {
      const symbol = c.held_directly ? symByScheme[c.stock] : null;
      return `
      <tr><td class="label-cell">${escapeHtml(c.stock)}
            ${c.held_directly ? '<span class="badge-fresh">direct</span>' : ''}
            ${c.bucket ? `<span class="cat-badge">${escapeHtml(c.bucket)}</span>` : ''}
            ${symbol ? `<div class="kpi-sub">${escapeHtml(symbol)}</div>` : ''}</td>
          <td>₹${inr(c.money)}</td>
          <td>${pct(c.percent_of_everything)}</td></tr>`;
    }).join('');
    pane('splits').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-list-magnifying-glass"></i>What you actually own — top 15 companies across all funds
          <span class="kpi-sub" style="margin-left:auto">direct equity/ETF rows are badged</span></div>
        <div class="scroll-x"><table class="data-table"><thead><tr><th>company</th><th>money</th><th>% of analysed value</th></tr></thead><tbody>${companyRows}</tbody></table></div>
      </div>`);
  }

  // ── Tax-lot ages: how long each open FIFO purchase has been held ──
  // Ages and rates are both unverified until a person checks them, so
  // every panel here carries the badge. Informational only (C5).
  const lots = r.direct_tax_lots;
  if (lots && lots.has_data && (lots.holdings || []).length) {
    const lotBadge = (lots.rates_and_rules && lots.rates_and_rules.badge) || '[UNVERIFIED]';
    const ltDays = lots.rates_and_rules ? lots.rates_and_rules.holding_period_long_term_days : null;
    const lotRows = lots.holdings.map(h => ((h.lots || []).length
      ? h.lots.map(l => `
        <tr>
          <td class="label-cell">${escapeHtml(h.scheme_name || DASH)}${h.transaction_identifier ? `<div class="kpi-sub">${escapeHtml(h.transaction_identifier)}</div>` : ''}</td>
          <td>${l.buy_date ? escapeHtml(l.buy_date) : DASH}</td>
          <td>${l.units_still_open ?? DASH}</td>
          <td>${l.cost_per_unit !== null && l.cost_per_unit !== undefined ? '₹' + inr(l.cost_per_unit) : DASH}</td>
          <td>${l.days_held ?? DASH}${l.days_held != null ? 'd' : ''}</td>
          <td>${l.long_term ? '<span class="badge-fresh">long-term</span>' : '<span class="badge-stale">short-term</span>'}</td>
        </tr>`).join('')
      : `<tr><td class="label-cell">${escapeHtml(h.scheme_name || DASH)}</td><td>${DASH}</td><td>${DASH}</td><td>${DASH}</td><td>${DASH}</td><td>${DASH}</td></tr>`)
    ).join('');
    pane('splits').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-hourglass"></i>Tax-lot ages — how long each open purchase has been held
          <span class="badge-stale" style="margin-left:auto">${escapeHtml(lotBadge)}</span></div>
        <div class="scroll-x"><table class="data-table">
          <thead><tr><th>holding</th><th>buy date</th><th>units open</th><th>cost/unit</th><th>age</th><th>term</th></tr></thead>
          <tbody>${lotRows}</tbody>
        </table></div>
        <div class="method-note">${escapeHtml(lots.note || '')}${ltDays ? ` Long-term means ${ltDays} days or more. Rates quoted: STCG ${lots.rates_and_rules.stcg_rate_pct ?? DASH}% · LTCG ${lots.rates_and_rules.ltcg_rate_pct ?? DASH}% above ₹${inr(lots.rates_and_rules.ltcg_exemption_rs ?? 0)} exemption.` : ''}</div>
      </div>`);
  }

  // ── The fund scorecard: one row per holding, investor's columns ───
  if (score.length) {
    const scoreRows = score.map(f => `
      <tr>
        <td class="label-cell">${escapeHtml(f.scheme_name)}
          <div class="kpi-sub">${escapeHtml(f.category)}${f.has_holdings ? '' : ' · not analysed yet'}</div></td>
        <td>${f.current == null ? DASH : '₹' + f.current.toLocaleString('en-IN')}</td>
        <td class="${(f.pl_pct || 0) >= 0 ? 'positive' : 'negative'}">${f.pl_pct ?? DASH}%</td>
        <td>${f.xirr_pct ?? DASH}${f.xirr_pct !== null ? '%' : ''}</td>
        <td>${num(f.expense_ratio)}</td>
        <td>${num(f.beta)}</td>
        <td class="${(f.alpha_pct || 0) >= 0 ? 'positive' : 'negative'}">${f.alpha_pct === null || f.alpha_pct === undefined ? DASH : f.alpha_pct + '%'}</td>
        <td>${num(f.sharpe)}</td>
        <td>${num(f.sortino)}</td>
        <td>${f.return_1y_pct === null || f.return_1y_pct === undefined ? DASH : f.return_1y_pct + '%'}</td>
      </tr>`).join('');
    pane('splits').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-table"></i>Fund scorecard
          <span class="kpi-sub" style="margin-left:auto">behaviour vs ${escapeHtml(r.scorecard.benchmark)} · XIRR is your own money-weighted return</span></div>
        <div class="scroll-x"><table class="data-table">
          <thead><tr><th>scheme</th><th>value</th><th>P/L</th><th>XIRR</th><th>exp%</th><th>beta</th><th>alpha</th><th>sharpe</th><th>sortino</th><th>1y ret</th></tr></thead>
          <tbody>${scoreRows}</tbody>
        </table></div>
      </div>`);
  }

  // ── OVERLAP pane ──────────────────────────────────────────────────
  const pairRows = pairs.map(p => `
    <tr><td class="label-cell">${escapeHtml(p.first_fund)} × ${escapeHtml(p.second_fund)}</td>
        <td>${p.overlap_percent}%</td>
        <td class="label-cell">${escapeHtml(p.in_plain_words)}</td></tr>`).join('');
  pane('overlap').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-intersect"></i>Fund-to-fund overlap — are two of your funds the same fund?</div>
      ${pairs.length ? `
      <div class="scroll-x"><table class="data-table"><thead><tr><th>pair</th><th>overlap</th><th>in plain words</th></tr></thead><tbody>${pairRows}</tbody></table></div>
      <div class="method-note">Overlap is the share of holdings two funds have in common, weight for weight. The common
      reading band starts around 40% - above it, two scheme names are behaving like one bet. It is a fact about
      duplication, not an instruction to sell anything (C5).</div>`
      : `<div class="empty-note">No overlapping pairs computed yet - this needs published portfolios for at least two equity funds.</div>`}
    </div>`);

  // ── FLAGS pane: every observation, worst first ────────────────────
  if (obs.length) {
    pane('flags').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-flag"></i>What a reviewer would flag first
          <span class="kpi-sub" style="margin-left:auto">facts against published norms - never advice</span></div>
        ${obs.map(o => `
          <div class="money-row">
            <i class="ph ph-${o.level === 'flag' ? 'warning' : o.level === 'watch' ? 'eye' : 'info'}"></i>
            <span class="m-label">${OBS_BADGE[o.level] || ''} ${escapeHtml(o.text)}</span>
            <span class="sparkline-cell kpi-sub">${escapeHtml(o.basis)}</span>
          </div>`).join('')}
      </div>`);
  }

  // ── METHOD pane: the method behind every number ───────────────────
  pane('method').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-book-open"></i>How a professional reads this — the method behind every number</div>
      <div class="scroll-x"><table class="data-table">
        <thead><tr><th>metric</th><th>what it says</th><th>the norm it is read against</th><th>practised by</th></tr></thead>
        <tbody>
          <tr><td>look-through / X-ray</td><td>funds opened up into the companies you really own</td><td>single stock &gt;10% flag; top-10 &gt;25% watch / &gt;40% flag</td><td>Morningstar, Value Research</td></tr>
          <tr><td>HHI · effective N</td><td>concentration: how many equal bets you behave like</td><td>regulators' HHI bands (&lt;1500 spread · &gt;2500 concentrated)</td><td>antitrust regulators; X-ray tools</td></tr>
          <tr><td>pair overlap</td><td>are two funds the same fund?</td><td>&ge;40% shared weight = duplication band</td><td>Value Research overlap</td></tr>
          <tr><td>Sharpe</td><td>reward per unit of total risk</td><td>higher is better; compare within category</td><td>standard (Sharpe 1966)</td></tr>
          <tr><td>Sortino</td><td>like Sharpe but only downside volatility hurts</td><td>higher is better for loss-averse reading</td><td>standard (Sortino)</td></tr>
          <tr><td>Jensen's alpha</td><td>return beyond what beta explains</td><td>persistent negative alpha = manager not adding</td><td>standard CAPM practice</td></tr>
          <tr><td>information ratio</td><td>consistency of beating the benchmark</td><td>&gt;0.5 good, ~1 excellent</td><td>active-manager evaluation</td></tr>
          <tr><td>max drawdown</td><td>worst peak-to-trough fall in the window</td><td>read beside recovery time</td><td>standard risk practice</td></tr>
          <tr><td>XIRR</td><td>your own money-weighted return</td><td>the only return that is truly yours</td><td>every professional report</td></tr>
        </tbody>
      </table></div>
      <div class="kpi-sub" style="margin-top:6px">Full definitions and sources: Documentation/Guide_To_Portfolio_Analysis_Method.md</div>
    </div>`);

  // ── METHOD pane (continued): monitoring playbook ──────────────────
  pane('method').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-calendar-check"></i>Monitoring playbook — what a reviewer checks, and when</div>
      <div class="money-row"><i class="ph ph-calendar-dot"></i><span class="m-label"><b>Monthly</b> — re-pull portfolios (disclosures are monthly), diff sector/market-cap splits against last month.</span></div>
      <div class="money-row"><i class="ph ph-calendar"></i><span class="m-label"><b>Quarterly</b> — rolling 1y consistency vs benchmark; expense drift; fund-manager changes; AUM bloat in mid/small-cap funds.</span></div>
      <div class="money-row"><i class="ph ph-calculator"></i><span class="m-label"><b>Annually / life events</b> — map holdings to goals and horizons; rebalancing-band check (common rule: ±5% absolute or ±20% relative drift [UNVERIFIED]); tax-lot review before FY end.</span></div>
      <div class="money-row"><i class="ph ph-bell"></i><span class="m-label"><b>Triggers worth watching</b> — NAV stale &gt;7 days; a fund's r² collapses (style drift); alpha negative 4 quarters running; overlap crosses 40%; blended expense crosses 1%/yr.</span></div>
      <div class="kpi-sub" style="margin-top:6px">Each trigger can become a gate function returning (passed, reason) - the decision always stays with you (C5).</div>
    </div>`);

  // ── METHOD pane (continued): international landscape ──────────────
  pane('method').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-globe-hemisphere-west"></i>International diversification — the landscape an Indian investor can look at
        <span class="badge-stale" style="margin-left:auto">education · not advice</span></div>
      <div class="money-row"><i class="ph ph-pie-chart"></i><span class="m-label">India is roughly ~2% of world equity market cap [UNVERIFIED - check MSCI ACWI] - a 100% India portfolio carries a large home-bias tilt vs global weights.</span></div>
      <div class="money-row"><i class="ph ph-flag-usa"></i><span class="m-label"><b>US indices</b> — S&amp;P 500 / Nasdaq-100 feeder funds (you already hold one Nasdaq-100 fund); broadest single-market depth.</span></div>
      <div class="money-row"><i class="ph ph-earth"></i><span class="m-label"><b>Developed markets ex-US</b> — Europe/Japan/global-discovery funds; different rate cycles and currency exposure.</span></div>
      <div class="money-row"><i class="ph ph-chart-line-up"></i><span class="m-label"><b>EM ex-India</b> — global emerging-market funds; complements rather than repeats an India book.</span></div>
      <div class="money-row"><i class="ph ph-coins"></i><span class="m-label"><b>Direct foreign shares</b> — possible under LRS ($250k/yr per individual [UNVERIFIED - confirm current RBI/TCS rules]); higher complexity and tax paperwork.</span></div>
      <div class="money-row"><i class="ph ph-lock-key"></i><span class="m-label"><b>Industry-wide cap</b> — Indian MFs' overseas investing is bounded by an RBI/SEBI limit ($7bn, $1bn ETF sub-limit, Feb 2022 [UNVERIFIED]) that has periodically closed subscriptions - check live status before assuming any scheme is open.</span></div>
      <div class="money-row"><i class="ph ph-receipt"></i><span class="m-label"><b>Tax note</b> — treatment of international funds has changed with finance acts; verify against incometax.gov.in before relying on any figure.</span></div>
    </div>`);

  // ── Market extras: IPO calendar mini-panel (+ honest gaps) ────────
  // Reads /market/extras, which assembles Saved_Records files. If the
  // endpoint never answered, this panel does not draw at all - the
  // analysis above never depends on it.
  if (extras) {
    const ipo = extras.ipo_calendar || {};
    const ipoRow = i => `
      <div class="ipo-row">
        <span class="ipo-name">${escapeHtml(i.name || DASH)}
          ${i.symbol ? `<span class="kpi-sub">${escapeHtml(i.symbol)}</span>` : ''}
          ${i.is_sme ? '<span class="cat-badge">SME</span>' : ''}</span>
        <span class="ipo-dates">${(i.open_date || i.expected_open_date) ? escapeHtml(i.open_date || i.expected_open_date) + (i.close_date ? ' → ' + escapeHtml(i.close_date) : '') : DASH}</span>
        <span class="ipo-band">${(i.price_band_min !== null && i.price_band_min !== undefined) || (i.price_band_max !== null && i.price_band_max !== undefined) ? `₹${inr(i.price_band_min ?? i.price_band_max)}–${inr(i.price_band_max ?? i.price_band_min)}` : DASH}</span>
      </div>`;
    const ipoSection = (title, rows, emptyNote) => `
      <div class="ipo-section">
        <div class="kpi-label">${title}</div>
        ${rows.length ? rows.map(ipoRow).join('') : `<div class="empty-note">${DASH} ${escapeHtml(emptyNote)}</div>`}
      </div>`;
    const ledg = extras.equity_price_ledger_summary || {};
    const gsec = extras.gsec_notes || {};
    pane('dash').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-calendar-plus"></i>IPO calendar — open &amp; upcoming
          ${ipo.verified_by_a_person === false ? '<span class="badge-stale" style="margin-left:auto">[UNVERIFIED]</span>' : ''}</div>
        ${ipo.has_data ? `
          ${ipoSection('Open now', ipo.open || [], 'nothing is open right now')}
          ${ipoSection('Upcoming', ipo.upcoming || [], 'no upcoming issue on file')}`
        : `<div class="empty-note">${escapeHtml(ipo.note || 'No IPO calendar on file yet.')}</div>`}
        ${ledg.has_data ? `<div class="kpi-sub" style="margin-top:10px">Equity price ledger: ${ledg.how_many} close${ledg.how_many === 1 ? '' : 's'} on file${(ledg.rows && ledg.rows.length && ledg.rows[ledg.rows.length - 1].date) ? `, newest ${escapeHtml(ledg.rows[ledg.rows.length - 1].date)}` : ''}.</div>`
        : (ledg.note ? `<div class="empty-note">Equity price ledger: ${DASH}</div>` : '')}
        ${gsec.has_data === false && gsec.note ? `<div class="kpi-sub">G-Sec yield notes: not built yet.</div>` : ''}
      </div>`);
  }

  // ── DASHBOARD pane, last: what needs attention first, then ask ────
  const topObs = obs.filter(o => o.level !== 'info').slice(0, 3);
  if (topObs.length) {
    pane('dash').insertAdjacentHTML('beforeend', `
      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-warning"></i>Needs attention first
          <span class="kpi-sub" style="margin-left:auto">the ${topObs.length} highest-level flag${topObs.length === 1 ? '' : 's'} · all ${obs.length} in Reviewer flags</span></div>
        ${topObs.map(o => `
          <div class="money-row">
            <i class="ph ph-${o.level === 'flag' ? 'warning' : 'eye'}"></i>
            <span class="m-label">${OBS_BADGE[o.level] || ''} ${escapeHtml(o.text)}</span>
          </div>`).join('')}
      </div>`);
  }
  pane('dash').insertAdjacentHTML('beforeend', `
    <div class="glass-panel panel-pad">
      <div class="panel-title"><i class="ph ph-chats-circle"></i>Ask INKY about this analysis</div>
      <div class="ask-strip">
        <input type="text" id="port-ask-input" placeholder="e.g. which two funds overlap the most, and should I care?" maxlength="300">
        <button class="mini-btn" id="port-ask-btn">ASK</button>
      </div>
      <div class="ask-answer" id="port-ask-answer"></div>
    </div>`);

  wireAskStrip('port-ask-btn', 'port-ask-input', 'port-ask-answer', '/portfolio-analysis/ask');

  // ── Sub-tab wiring: one active pill, remembered between visits ────
  function setPfTab(id) {
    el.querySelectorAll('.pf-subtab').forEach(b =>
      b.classList.toggle('active', b.dataset.pf === id));
    PF_TABS.forEach(tb => {
      const p = el.querySelector('#pf-pane-' + tb.id);
      if (p) p.classList.toggle('active', tb.id === id);
    });
    try { localStorage.setItem('inky-pf-tab', id); } catch (e) { /* private mode */ }
  }
  el.querySelectorAll('.pf-subtab').forEach(btn =>
    btn.addEventListener('click', () => setPfTab(btn.dataset.pf)));
  let saved = null;
  try { saved = localStorage.getItem('inky-pf-tab'); } catch (e) {}
  if (saved && PF_TABS.some(tb => tb.id === saved)) setPfTab(saved);
}


// ══════════════════════════════════════════════════════════════════
//  DEBT & LIABILITIES - two sub-tabs behind one pill row, mirroring
//  PF_TABS on Portfolio Analysis: "Loans" (the two tracked loans,
//  payoff comparison, amortisation chart, ledger rows flagged as debt)
//  and "Net Worth & Liabilities" (assets, the balance-sheet KPIs, other
//  liabilities, pledge/missing notices). Same data endpoints as before
//  (/debt and /liabilities) - this was a real-estate fix, not a
//  re-architecture. Which pane is open survives in localStorage.
// ══════════════════════════════════════════════════════════════════
const DEBT_TABS = [
  { id: 'loans',    label: 'Loans',                   icon: 'ph-hand-coins' },
  { id: 'networth', label: 'Net Worth & Liabilities', icon: 'ph-scales' },
];

// The education loan's monthly amortisation, now actually drawn: one
// stacked bar per payment (principal vs interest) and the outstanding
// balance as a line over them. Pure arithmetic off /api/finance/debt's
// schedule - descriptive, never advice (C5).
function drawLoanSchedule(rows) {
  const box = document.getElementById('loan-schedule-chart');
  if (!box) return;
  if (!rows || rows.length < 2) {
    box.innerHTML = '<div class="empty-note">No amortisation schedule was returned for this loan.</div>';
    return;
  }
  makeChart(box, {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#6d7f9b' } },
      valueFormatter: v => '₹' + inr(v),
    },
    legend: { data: ['principal part', 'interest part', 'balance left'], top: 0, textStyle: { fontSize: 11, color: '#9db0cb' } },
    grid: { left: 8, right: 8, top: 30, bottom: 42, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map(r => r.date),
      axisLabel: { fontSize: 10, fontFamily: 'monospace', color: '#9db0cb', interval: Math.max(0, Math.floor(rows.length / 6)) },
    },
    yAxis: [
      { type: 'value', axisLabel: { fontSize: 10, fontFamily: 'monospace', color: '#9db0cb', formatter: v => inr(v) }, splitLine: { lineStyle: { color: 'rgba(231,237,248,0.07)' } } },
      { type: 'value', show: false },
    ],
    series: [
      { name: 'principal part', type: 'bar', stack: 'emi', itemStyle: { color: '#46c98f' }, data: rows.map(r => r.principal_component) },
      { name: 'interest part', type: 'bar', stack: 'emi', itemStyle: { color: '#f37373' }, data: rows.map(r => r.interest_component) },
      { name: 'balance left', type: 'line', yAxisIndex: 1, symbol: 'none', lineStyle: { width: 2.5, color: '#93a5f7' }, itemStyle: { color: '#93a5f7' }, data: rows.map(r => r.outstanding) },
    ],
  });
}

function debtSubnav(active) {
  return `<div class="pf-subnav" role="tablist">
    ${DEBT_TABS.map(t => `
      <button class="pf-subtab ${t.id === active ? 'active' : ''}" data-debt="${t.id}" role="tab">
        <i class="ph ph-${t.icon}"></i>${escapeHtml(t.label)}
      </button>`).join('')}
  </div>`;
}

async function loadDebt() {
  const el = document.getElementById('debt-body');
  let debtData, liab;
  try { [debtData, liab] = await Promise.all([getJson(API + '/debt'), getJson(API + '/liabilities')]); }
  catch (err) { el.innerHTML = `<div class="empty-note">could not load: ${escapeHtml(err.message)}</div>`; return; }

  // The one hard line on this tab: borrowed money vs every other
  // obligation. It is drawn by DEBT_CATEGORIES in
  // track_assets_and_liabilities.py, not by prose here.
  let balanceSheet = '<div class="glass-panel panel-pad"><div class="empty-note">no liabilities ledger yet</div></div>';
  let debtRows = '<tr><td colspan="4" class="empty-note">the liabilities ledger has not loaded</td></tr>';
  let otherRows = debtRows;
  if (!liab.has_data) {
    balanceSheet = `
      <div class="glass-panel panel-pad"><div class="empty-note">${escapeHtml(liab.note)}</div></div>`;
  } else {
    const split = liab.debt_split || {};
    const debts = (liab.liabilities || []).filter(r => r.is_debt);
    const others = (liab.liabilities || []).filter(r => !r.is_debt);
    const missingValues = (split.borrowed_missing_a_value || 0) + (split.other_missing_a_value || 0)
      + (liab.net_worth.assets_missing_a_value || 0);
    const catChip = c => `<span class="fa-tag ${c === 'secured_loan' ? 'amber' : c === 'consumer_credit' || c === 'credit_card' ? 'red' : 'blue'}">${escapeHtml(String(c).replace(/_/g, ' '))}</span>`;
    const owedRow = r => `
      <tr>
        <td class="label-cell">${escapeHtml(r.name)}${r.notes ? `<div class="kpi-sub">${escapeHtml(r.notes)}</div>` : ''}</td>
        <td>${catChip(r.category)}</td>
        <td class="nowrap-cell">${r.monthly_amount == null ? '<span class="value-needed">EMI?</span>' : money(r.monthly_amount)}</td>
        <td class="nowrap-cell">${r.value == null ? '<span class="value-needed">outstanding?</span>' : money(r.value)}</td>
      </tr>`;

    const debtRows = debts.map(owedRow).join('') || '<tr><td colspan="4" class="empty-note">none recorded beyond the two loans above</td></tr>';
    const otherRows = others.map(owedRow).join('') || '<tr><td colspan="4" class="empty-note">none recorded</td></tr>';
    const assetRows = (liab.assets || []).map(r => `
      <tr><td class="label-cell">${escapeHtml(r.name)}${r.notes ? `<div class="kpi-sub">${escapeHtml(r.notes)}</div>` : ''}</td>
          <td>${catChip(r.category)}</td>
          <td class="nowrap-cell">${r.value == null ? '<span class="value-needed">value?</span>' : money(r.value)}</td></tr>`).join('')
      || '<tr><td colspan="3" class="empty-note">none recorded</td></tr>';

    // A pledge is an honest-use restriction on an asset you still own:
    // the pledged units sit inside the portfolio AND secure this loan.
    const pledges = debts.filter(r => r.category === 'secured_loan');
    const pledgeNames = pledges.map(p => escapeHtml(p.name)).join(', ').replace(/, ([^,]*)$/, ' and $1');

    balanceSheet = `
      <div class="kpi-row kpi-four">
        <div class="glass-panel kpi-card"><i class="ph ph-scales kpi-icon"></i><div class="kpi-label">Net worth</div><div class="kpi-value ${liab.net_worth.value.raw < 0 ? 'negative' : 'positive'}">${money(liab.net_worth.value)}</div><div class="kpi-sub">${liab.net_worth.complete ? 'assets minus everything owed' : `incomplete - ${missingValues} value${missingValues === 1 ? '' : 's'} still blank`}</div></div>
        <div class="glass-panel kpi-card"><i class="ph ph-hand-coins kpi-icon"></i><div class="kpi-label">Debt - borrowed</div><div class="kpi-value negative">${money(split.borrowed_total)}</div><div class="kpi-sub">loans, secured loans, EMI/card credit${split.borrowed_missing_a_value ? ` · ${split.borrowed_missing_a_value} awaiting figures` : ''}</div></div>
        <div class="glass-panel kpi-card"><i class="ph ph-file-text kpi-icon"></i><div class="kpi-label">Other liabilities</div><div class="kpi-value">${money(split.other_total)}</div><div class="kpi-sub">obligations that are not borrowed money</div></div>
        <div class="glass-panel kpi-card"><i class="ph ph-calendar-blank kpi-icon"></i><div class="kpi-label">Recurring per month</div><div class="kpi-value">${money(liab.monthly_recurring_liabilities)}</div><div class="kpi-sub">informational - never auto-added to surplus</div></div>
      </div>

      ${pledges.length ? `
      <div class="debt-band">
        <i class="ph ph-lock-key"></i>
        <span><b>Pledged collateral.</b> The mutual funds behind ${pledgeNames} ${pledges.length === 1 ? 'is' : 'are'} encumbered
        until the loan is repaid - they still show in Investments, but they are not freely sellable while pledged.</span>
      </div>` : ''}

      ${missingValues ? `
      <div class="debt-band">
        <i class="ph ph-pencil-simple"></i>
        <span><b>${missingValues} row${missingValues === 1 ? '' : 's'} waiting on your figures.</b> A blank stays blank - it never pretends to be zero.
        What to fill, and where it comes from: <b>Reference_Data/Human_Checklists/What_To_Fill_In.txt</b>, item 15.</span>
      </div>` : ''}

      <div class="split-two-col">
        <div class="glass-panel panel-pad">
          <div class="panel-title"><i class="ph ph-hand-coins"></i>Debt — money borrowed
            <span class="kpi-sub" style="margin-left:auto">every row here is owed borrowed money</span></div>
          <div class="scroll-x"><table class="data-table"><thead><tr><th>name</th><th>kind</th><th>monthly</th><th>outstanding</th></tr></thead><tbody>${debtRows}</tbody></table></div>
        </div>
        <div class="glass-panel panel-pad">
          <div class="panel-title"><i class="ph ph-file-text"></i>Other liabilities — owed, not borrowed
            <span class="kpi-sub" style="margin-left:auto">premiums, subscriptions, obligations</span></div>
          <div class="scroll-x"><table class="data-table"><thead><tr><th>name</th><th>kind</th><th>monthly</th><th>amount</th></tr></thead><tbody>${otherRows}</tbody></table></div>
        </div>
      </div>

      <div class="glass-panel panel-pad"><div class="panel-title"><i class="ph ph-trend-up"></i>Assets — what I own
        <span class="kpi-sub" style="margin-left:auto">including salary-deducted savings such as EPF</span></div>
        <div class="scroll-x"><table class="data-table"><thead><tr><th>name</th><th>kind</th><th>value</th></tr></thead><tbody>${assetRows}</tbody></table></div>
      </div>

      <div class="method-note">Where the line comes from: <b>debt</b> is an obligation to pay <i>borrowed</i> money - loans,
      secured loans (collateralised, like a loan against pledged mutual funds), consumer credit and card balances.
      <b>Liability</b> is the wider accounting idea - value expected to be delivered in the future to satisfy a present
      obligation arising from past events - which covers the right-hand table too: insurance premiums due, subscriptions
      due, money owed. All debt is a liability; only borrowed money is debt. Definitions checked 2026-08-23 against
      Wikipedia "Debt" ("obligation to pay borrowed money") and Wikipedia "Liability (financial accounting)"
      ("a quantity of value that a financial entity owes"). General definitions, not legal advice.</div>`;
  }

  const active = localStorage.getItem('inky_debt_tab') || 'loans';
  el.innerHTML = `
    ${debtSubnav(active)}
    <div class="pf-pane ${active === 'loans' ? 'active' : ''}" id="debt-pane-loans">
      <div class="section-title">Loans the surplus formula already tracks</div>
      <div class="kpi-row">
        <div class="glass-panel kpi-card">
          <i class="ph ph-money kpi-icon"></i>
          <div class="kpi-label">Personal debt</div>
          <div class="kpi-value">${money(debtData.personal_debt.remaining)}</div>
          <div class="kpi-sub">${money(debtData.personal_debt.monthly)}/mo · clears ${escapeHtml(debtData.personal_debt.clears || DASH)}</div>
        </div>
        <div class="glass-panel kpi-card">
          <i class="ph ph-graduation-cap kpi-icon"></i>
          <div class="kpi-label">Education loan</div>
          <div class="kpi-value">${money(debtData.education_loan.outstanding)}</div>
          <div class="kpi-sub">${escapeHtml(String(debtData.education_loan.rate_pct))}% · EMI ${money(debtData.education_loan.emi)} · payoff ${escapeHtml(debtData.education_loan.payoff_now)}</div>
        </div>
      </div>

      <div class="glass-panel panel-pad">
        <div class="panel-title"><i class="ph ph-chart-bar"></i>Education loan — every payment to payoff
          <span class="kpi-sub" style="margin-left:auto">hover a month for its principal / interest split</span></div>
        <div id="loan-schedule-chart" class="echart-box"></div>
        <div class="kpi-sub">Green: how much of each EMI kills principal. Red: what borrowing costs that month.
          Blue line: balance still owed. Descriptive only - whether to pay extra stays your call (C5).</div>
      </div>

      <div class="split-two-col">
        <div class="glass-panel panel-pad">
          <div class="panel-title"><i class="ph ph-hand-coins"></i>Debt — money borrowed
            <span class="kpi-sub" style="margin-left:auto">every row here is owed borrowed money</span></div>
          <div class="scroll-x"><table class="data-table"><thead><tr><th>name</th><th>kind</th><th>monthly</th><th>outstanding</th></tr></thead><tbody>${debtRows}</tbody></table></div>
        </div>
        <div class="glass-panel panel-pad">
          <div class="panel-title"><i class="ph ph-file-text"></i>Other liabilities — owed, not borrowed
            <span class="kpi-sub" style="margin-left:auto">premiums, subscriptions, obligations</span></div>
          <div class="scroll-x"><table class="data-table"><thead><tr><th>name</th><th>kind</th><th>monthly</th><th>amount</th></tr></thead><tbody>${otherRows}</tbody></table></div>
        </div>
      </div>
    </div>

    <div class="pf-pane ${active === 'networth' ? 'active' : ''}" id="debt-pane-networth">
      <div class="section-title">The wider balance sheet</div>
      ${balanceSheet}
    </div>`;

  // Sub-tab switching, same pattern as PF_TABS.
  el.querySelectorAll('.pf-subtab[data-debt]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.debt;
      localStorage.setItem('inky_debt_tab', id);
      el.querySelectorAll('.pf-subtab[data-debt]').forEach(b => b.classList.toggle('active', b === btn));
      el.querySelectorAll('.pf-pane').forEach(p => p.classList.toggle('active', p.id === 'debt-pane-' + id));
    });
  });

  drawLoanSchedule(debtData.education_loan.schedule || []);
}

// ══════════════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════════════
// The Chat tab was removed 2026-08-24. Contextual asking survives in
// the two "Ask INKY" strips (Investments and Portfolio Analysis), both
// served by POST /investments/ask and /portfolio-analysis/ask.
// ══════════════════════════════════════════════════════════════════
//  FUND ANALYSIS MODAL - the button on each fund row
//  Every figure is fetched from /investments/fund-analysis/<code>,
//  which serves the stored daily profile. A value the analysis does
//  not have renders as a dash, never a zero.
// ══════════════════════════════════════════════════════════════════
const RATIO_HELP = {
  pe: "Weighted average of the P/E of the stocks the fund holds - the share price against each company's earnings. High P/E often means the market expects growth; low may mean cheap or troubled.",
  pb: 'Weighted average of the P/B of the holdings - price against book value. A low P/B can mean undervalued, or problems in the fundamentals.',
  beta: 'How much the fund swings with the market. Above 1 = more volatile than the index; below 1 = calmer.',
  alpha: 'Return the manager added beyond what the market move alone explains. 1 means it beat its beta-adjusted benchmark by 1%.',
  sharpe: 'Return against total risk. 1-3 or above means the fund paid well for the risk it took.',
  sortino: 'Like Sharpe, but only the down days count as risk. Above 2 is considered good.',
  volatility: 'How widely daily returns spread out over a year, annualised.',
  max_drawdown: 'The worst peak-to-trough fall in the window. What a bad stretch actually felt like.',
  return_1y: 'Total return over the window, annualised from daily NAVs.',
  r_squared: 'How much of the fund\u2019s movement the benchmark explains, 0 to 1. Near 1: an index-like fund and beta says a lot. Near 0: the manager dances to their own tune and beta explains little.',
};

function pct(v) { return (v === null || v === undefined) ? `<span class="dash">${DASH}</span>` : escapeHtml(String(v)) + '%'; }
function num(v) { return (v === null || v === undefined) ? `<span class="dash">${DASH}</span>` : escapeHtml(String(v)); }

// ── the four tabs, and remembering where the person left them ──
// The active tab lives in localStorage, so closing the modal and
// opening another fund puts you back on the tab you were reading -
// "which tab was active" survives between views, funds and visits.
const FA_TABS = [
  { id: 'overview', label: 'Performance & Overview' },
  { id: 'holdings', label: 'Portfolio Holdings' },
  { id: 'splits',   label: 'Holdings Analysis & Splits' },
  { id: 'ratios',   label: 'Advanced Ratios' },
];
const FA_TAB_STORAGE_KEY = 'inky.fund-analysis.active-tab';
let faProfile = null;          // the profile on show right now

function faActiveTab() {
  const saved = localStorage.getItem(FA_TAB_STORAGE_KEY);
  return FA_TABS.some(t => t.id === saved) ? saved : 'overview';
}

function setFaTab(id) {
  if (!FA_TABS.some(t => t.id === id)) id = 'overview';
  localStorage.setItem(FA_TAB_STORAGE_KEY, id);
  const overlay = document.getElementById('fund-analysis-overlay');
  if (!overlay) return;
  overlay.querySelectorAll('.fa-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === id));
  // Renderers draw INTO #fa-body. Handing them the whole overlay (the
  // old behaviour) let a renderer's innerHTML wipe the header, the pill
  // tags, the tab bar and the close button off the modal.
  // Charts die with their tab: dispose before the HTML is replaced.
  const body = overlay.querySelector('#fa-body');
  const render = FA_RENDERERS[id];
  if (render && body) { disposeFaCharts(); render(body); }
}

function ensureAnalysisOverlay() {
  let overlay = document.getElementById('fund-analysis-overlay');
  if (overlay) return overlay;
  overlay = document.createElement('div');
  overlay.id = 'fund-analysis-overlay';
  overlay.innerHTML = `
    <div class="fa-backdrop"></div>
    <div class="fa-modal">
      <div class="fa-head">
        <div class="fa-title-row">
          <div class="fa-title-wrap">
            <div class="fa-title" id="fa-title">…</div>
            <div class="fa-tags" id="fa-tags"></div>
            <div class="kpi-sub" id="fa-sub"></div>
          </div>
          <span class="fa-head-actions">
            <button class="mini-btn" id="fa-repull">re-pull today</button>
            <button class="fa-close" id="fa-close" title="close" aria-label="close"><i class="ph ph-x"></i></button>
          </span>
        </div>
      </div>
      <div class="fa-tabbar" role="tablist">
        ${FA_TABS.map(t => `
          <button class="fa-tab" data-tab="${t.id}" role="tab">
            <span>${escapeHtml(t.label)}</span><span class="fa-tab-ind"></span>
          </button>`).join('')}
      </div>
      <div class="fa-body" id="fa-body"></div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.querySelector('.fa-backdrop').addEventListener('click', closeFundAnalysis);
  overlay.querySelector('#fa-close').addEventListener('click', closeFundAnalysis);
  overlay.querySelectorAll('.fa-tab').forEach(btn =>
    btn.addEventListener('click', () => setFaTab(btn.dataset.tab)));
  overlay.querySelector('#fa-repull').addEventListener('click', async () => {
    const btn = overlay.querySelector('#fa-repull');
    btn.textContent = 'pulling…'; btn.disabled = true;
    try { await postJson(API + '/investments/fund-analysis/refresh', {}); } catch (e) {}
    btn.textContent = 're-pull today'; btn.disabled = false;
    // A forced re-pull only lands if today's pull had not run yet; either
    // way, re-read whatever the newest stored profile now says.
    getJson(API + '/investments/fund-analysis/' + encodeURIComponent(overlay.dataset.code))
      .then(data => { faProfile = data; renderFaHeader(data); setFaTab(faActiveTab()); })
      .catch(() => {});
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeFundAnalysis(); });
  return overlay;
}

function closeFundAnalysis() {
  const overlay = document.getElementById('fund-analysis-overlay');
  if (overlay) overlay.classList.remove('show');
}

// Modal charts live and die with their tab render: every setFaTab wipes
// #fa-body's HTML, so any chart drawn there is disposed first rather
// than left listening on a detached node.
const FA_CHARTS = [];

function faMakeChart(el, option) {
  const chart = makeChart(el, option);
  if (chart) FA_CHARTS.push(chart);
  return chart;
}

function disposeFaCharts() {
  while (FA_CHARTS.length) {
    const chart = FA_CHARTS.pop();
    const i = INKY_CHARTS.indexOf(chart);
    if (i >= 0) INKY_CHARTS.splice(i, 1);
    try { chart.dispose(); } catch (err) {}
  }
}

// mfapi.in writes day-first dates (dd-mm-yyyy); ledgers write ISO.
// Both parse here, or the point is skipped by the caller.
function navPointDate(raw) {
  const m = /^(\d{1,2})-(\d{1,2})-(\d{4})$/.exec(String(raw));
  if (m) return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  return new Date(raw);
}

function dashHtml() { return `<span class="dash">${DASH}</span>`; }
function pctv(v) { return (v === null || v === undefined) ? dashHtml() : escapeHtml(String(v)) + '%'; }

// Donut queue: renderFaSplits composes one HTML string, so the three
// ECharts donuts are queued here while building it and initialised
// right after the string lands in the DOM (initFaDonuts).
let _faDonutQueue = [];

function initFaDonuts() {
  _faDonutQueue.forEach(({ id, known }) => {
    faMakeChart(document.getElementById(id), {
      tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
      series: [{
        type: 'pie', radius: ['60%', '82%'],
        itemStyle: { borderColor: '#111b31', borderWidth: 2 },
        label: { show: false }, silent: false,
        data: known.map(s => ({ name: s.label, value: s.value, itemStyle: { color: s.color } })),
      }],
    });
  });
  _faDonutQueue = [];
}

// ── THE NAV CHART — Groww-style ──────────────────────────────────────
// Hover shows the exact NAV on a day; scroll/pinch zooms, the slider
// pans, and the preset pills slice the same series client-side (option
// (a) from the plan). Every point the backend stored is drawn - there
// is no downsampling left anywhere in the chain.
const NAV_RANGES = [
  ['1M', 30], ['3M', 91], ['6M', 182], ['1Y', 365], ['3Y', 1095], ['5Y', 1825], ['MAX', null],
];

const DAY_MS = 86400000;

// Points sorted oldest-first, bad rows skipped - gaps stay gaps.
function cleanNavPoints(points) {
  return (points || [])
    .filter(p => p && p.nav > 0 && !isNaN(navPointDate(p.date)))
    .map(p => ({ t: navPointDate(p.date).getTime(), nav: Number(p.nav), date: String(p.date) }))
    .sort((a, b) => a.t - b.t);
}

function navActiveRange() {
  const saved = localStorage.getItem('fa_nav_range');
  return NAV_RANGES.some(r => r[0] === saved) ? saved : '1Y';
}

function navChartSection(points) {
  const clean = cleanNavPoints(points);
  if (clean.length < 2) {
    return `<div class="empty-note">Not enough NAV history stored to draw a line yet - re-pull and try again.</div>`;
  }
  const active = navActiveRange();
  const last = clean[clean.length - 1].t;
  const pills = NAV_RANGES.map(([label, days]) => {
    let enough = true;
    if (days !== null) {
      enough = clean.filter(p => p.t >= last - days * DAY_MS).length >= 2;
    }
    return `<button class="range-pill ${label === active ? 'active' : ''}" data-range="${label}"
      ${enough ? '' : 'disabled title="not enough stored history for this window yet"'}>${label}</button>`;
  }).join('');
  return `
    <div class="nav-range-row" role="tablist">${pills}</div>
    <div id="fa-nav-chart" class="echart-box"></div>
    <div class="kpi-sub">hover for a day's exact NAV &middot; scroll or pinch to zoom &middot; drag the slider to pan
      &middot; ${escapeHtml(clean[0].date)} → ${escapeHtml(clean[clean.length - 1].date)} &middot; ${clean.length} real NAV days, none invented</div>`;
}

function drawNavChart(points) {
  const box = document.getElementById('fa-nav-chart');
  if (!box) return;
  const clean = cleanNavPoints(points);
  if (clean.length < 2) return;
  const def = NAV_RANGES.find(r => r[0] === navActiveRange());
  let shown = clean;
  if (def[1] !== null) {
    const cutoff = clean[clean.length - 1].t - def[1] * DAY_MS;
    shown = clean.filter(p => p.t >= cutoff);
    if (shown.length < 2) shown = clean;
  }
  faMakeChart(box, {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: '#1e2959' } },
      valueFormatter: v => '₹' + inr(v),
      extraCssText: 'font-variant-numeric: tabular-nums;',
    },
    grid: { left: 10, right: 10, top: 16, bottom: 58, containLabel: true },
    xAxis: {
      type: 'time',
      axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value', scale: true,
      axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', formatter: v => '₹' + inr(v) },
      splitLine: { lineStyle: { color: 'rgba(231,237,248,0.07)' } },
    },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 10 }],
    series: [{
      name: 'NAV', type: 'line', showSymbol: false,
      data: shown.map(p => [p.t, p.nav]),
      lineStyle: { color: '#46c98f', width: 2 },
      itemStyle: { color: '#46c98f' },
      areaStyle: { color: 'rgba(70,201,143,0.14)' },
    }],
  });
}

// Two more views of the same stored NAV series - the inputs the ratios
// tab already reduces to single numbers, drawn over time instead:
// the drawdown curve (distance below the running peak) and the rolling
// one-year annualised return. Descriptive only, never advice (C5).
function drawdownAndRollingCharts(container, d) {
  const host = container.querySelector('#fa-derived-charts');
  if (!host) return;
  const clean = cleanNavPoints(d.nav_history && d.nav_history.points);
  if (clean.length < 60) {
    host.innerHTML = `<div class="empty-note">The drawdown and rolling-return curves need more NAV history than this fund has stored (${clean.length} day${clean.length === 1 ? '' : 's'} so far). They appear as the daily pull accumulates real history.</div>`;
    return;
  }
  host.innerHTML = `
    <div class="panel-title"><i class="ph ph-arrow-down-right"></i>Drawdown curve</div>
    <div id="fa-dd-chart" class="echart-box echart-box-mid"></div>
    <div class="kpi-sub">How far below the highest NAV so far the fund sat each day, %. The deepest point is exactly the max-drawdown figure above.</div>
    <div class="panel-title" style="margin-top:14px"><i class="ph ph-path"></i>Rolling one-year return</div>
    <div id="fa-roll-chart" class="echart-box echart-box-mid"></div>
    <div class="kpi-sub">Annualised return over every trailing year the history covers, % - the shape of what actually happened, not a forecast.</div>`;

  let peak = -Infinity;
  const ddData = clean.map(p => {
    peak = Math.max(peak, p.nav);
    return [p.t, Math.round(((p.nav / peak) - 1) * 10000) / 100];
  });
  faMakeChart(host.querySelector('#fa-dd-chart'), {
    tooltip: { trigger: 'axis', valueFormatter: v => v + '%', extraCssText: 'font-variant-numeric: tabular-nums;' },
    grid: { left: 10, right: 10, top: 12, bottom: 24, containLabel: true },
    xAxis: { type: 'time', axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', hideOverlap: true } },
    yAxis: { type: 'value', max: 0, axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(231,237,248,0.07)' } } },
    series: [{
      type: 'line', showSymbol: false, data: ddData,
      lineStyle: { color: '#f37373', width: 1.5 },
      itemStyle: { color: '#f37373' },
      areaStyle: { color: 'rgba(243,115,115,0.15)' },
    }],
  });

  const rollData = [];
  let j = 0;
  for (let i = 1; i < clean.length; i++) {
    while (j < i && clean[i].t - clean[j].t > DAY_MS * 365) j++;
    const spanMs = clean[i].t - clean[j].t;
    if (spanMs >= DAY_MS * 365 * 0.97) {
      const years = spanMs / (DAY_MS * 365);
      rollData.push([clean[i].t, Math.round((Math.pow(clean[i].nav / clean[j].nav, 1 / years) - 1) * 10000) / 100]);
    }
  }
  if (rollData.length >= 2) {
    faMakeChart(host.querySelector('#fa-roll-chart'), {
      tooltip: { trigger: 'axis', valueFormatter: v => v + '%', extraCssText: 'font-variant-numeric: tabular-nums;' },
      grid: { left: 10, right: 10, top: 12, bottom: 24, containLabel: true },
      xAxis: { type: 'time', axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', hideOverlap: true } },
      yAxis: { type: 'value', scale: true, axisLabel: { fontFamily: 'monospace', fontSize: 10, color: '#9db0cb', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(231,237,248,0.07)' } } },
      series: [{
        type: 'line', showSymbol: false, data: rollData,
        lineStyle: { color: '#9b8cf2', width: 2 },
        itemStyle: { color: '#9b8cf2' },
        areaStyle: { color: 'rgba(155,140,242,0.10)' },
      }],
    });
  } else {
    const rollBox = host.querySelector('#fa-roll-chart');
    if (rollBox) rollBox.innerHTML = '<div class="empty-note">Not enough history yet for even one full trailing year.</div>';
  }
}

// ── pill tags under the fund name, derived from the analysis only ──
function fundTags(d) {
  const tags = [];
  const split = d.asset_split || {};
  const eq = split.equity_pct ?? 0;
  tags.push({
    text: eq >= 60 ? 'Equity' : (eq >= 25 ? 'Hybrid' : 'Debt / Cash'),
    cls: eq >= 60 ? '' : (eq >= 25 ? 'amber' : 'blue'),
  });
  const caps = d.market_cap_split || {};
  const ranked = [
    ['Large Cap', caps.large_cap_pct], ['Mid Cap', caps.mid_cap_pct],
    ['Small Cap', caps.small_cap_pct],
  ].filter(e => e[1] !== null && e[1] !== undefined)
   .sort((a, b) => b[1] - a[1]);
  if (ranked.length && ranked[0][1] > 0) {
    tags.push({ text: ranked[0][0], cls: 'blue' });
  }
  const vol = (d.performance || {}).volatility_pct;
  if (vol !== null && vol !== undefined) {
    const risk = vol < 10 ? ['Moderate Risk', 'green']
      : vol < 18 ? ['High Risk', 'amber'] : ['Very High Risk', 'red'];
    tags.push({ text: risk[0], cls: risk[1],
                title: `derived from ${vol}% annualised volatility` });
  }
  return tags.map(t =>
    `<span class="fa-tag ${t.cls}"${t.title ? ` title="${escapeHtml(t.title)}"` : ''}>${escapeHtml(t.text)}</span>`).join('');
}

function renderFaHeader(data) {
  const overlay = document.getElementById('fund-analysis-overlay');
  overlay.querySelector('#fa-title').textContent =
    data.scheme_name || overlay.dataset.code;
  overlay.querySelector('#fa-tags').innerHTML = data.has_data ? fundTags(data) : '';
  overlay.querySelector('#fa-sub').innerHTML =
    `portfolio as of ${escapeHtml(data.as_of || '?')}` +
    ` · pulled ${escapeHtml(data.fetched_on || '?')}` +
    ` · benchmark ${escapeHtml((data.benchmark && data.benchmark.name) || '?')}` +
    (data.settings_verified_by_a_person === false ? ' · <span class="badge-stale">unverified settings</span>' : '');
}

function ratioInfoCard(key, label, value, extra) {
  return `<div class="fa-ratio">
    <div class="fa-ratio-value">${value}</div>
    <div class="fa-ratio-label">${escapeHtml(label)}
      <i class="ph ph-info fa-info-i" title="${escapeHtml(RATIO_HELP[key] || '')}"></i></div>
    <div class="kpi-sub">${RATIO_HELP[key] || ''}${extra ? '<br>' + extra : ''}</div>
  </div>`;
}

function doughnutSection(title, icon, segments, note) {
  const known = segments.filter(s => s.value !== null && s.value !== undefined);
  const total = known.reduce((s, x) => s + x.value, 0);
  const legend = known.map(s => `
    <span class="fa-legend-item"><span class="fa-dot" style="background:${s.color}"></span>
      ${escapeHtml(s.label)} <b>${pct(s.value)}</b></span>`).join('');
  const drawable = known.length > 0 && total > 0;
  let donutHtml;
  if (drawable) {
    const id = 'fa-donut-' + _faDonutQueue.length;
    _faDonutQueue.push({ id, known });
    donutHtml = `<div id="${id}" class="echart-donut"></div>
      <div class="fa-donut-center"><b>${total.toFixed(2)}%</b><span>of assets explained</span></div>`;
  } else {
    donutHtml = `<div class="empty-note">nothing published here yet</div>`;
  }
  return `
    <div class="fa-section">
      <div class="panel-title"><i class="ph ${icon}"></i>${escapeHtml(title)}</div>
      <div class="fa-split">
        <div class="fa-donut">${donutHtml}</div>
        <div class="fa-legend fa-legend-col">${legend}</div>
      </div>
      ${note ? `<div class="kpi-sub">${note}</div>` : ''}
    </div>`;
}

function openFundAnalysis(code, name) {
  if (!code) { alert('this fund has no AMFI code, so it cannot be analysed'); return; }
  const overlay = ensureAnalysisOverlay();
  overlay.classList.add('show');
  overlay.dataset.code = code;
  // Drop the previous fund's profile first: if this fetch fails, the tab
  // renderers must show the honest "could not load" state, never the
  // last fund's numbers under a new fund's name.
  faProfile = null;
  overlay.querySelector('#fa-title').textContent = name || code;
  overlay.querySelector('#fa-tags').innerHTML = '';
  overlay.querySelector('#fa-sub').textContent = 'fetching its stored daily profile…';
  overlay.querySelector('#fa-body').innerHTML = '<div class="empty-note">fetching…</div>';
  traceEvent('click', 'open_fund_analysis', code);
  // The tab bar comes back exactly where the person last left it -
  // whichever fund they open next.
  setFaTab(faActiveTab());

  getJson(API + '/investments/fund-analysis/' + encodeURIComponent(code))
    .then(data => {
      if (!data.ok && !data.has_data) {
        overlay.querySelector('#fa-sub').textContent = '';
        overlay.querySelector('#fa-body').innerHTML =
          `<div class="empty-note">${escapeHtml(data.note || 'No published portfolio could be fetched for this fund right now. Its sources are volunteer-run; try the re-pull button later.')}</div>`;
        return;
      }
      faProfile = data;
      renderFaHeader(data);
      setFaTab(faActiveTab());
    })
    .catch(err => {
      overlay.querySelector('#fa-body').innerHTML =
        `<div class="empty-note">could not load: ${escapeHtml(err.message)}</div>`;
    });
}

// ══════════════════════════════════════════════════════════════════
//  THE FOUR TABS - one aspect of the fund each, so the window stays
//  clean. Every figure comes off the stored daily profile; anything
//  the free sources do not publish renders as a dash with its reason.
// ══════════════════════════════════════════════════════════════════

// ── TAB 1 · Fund performance & overview ──
function renderFaOverview(el) {
  const d = faProfile || {};
  const perf = d.performance || {};
  const ret = perf.return_1y_pct;
  const windowLabel = perf.has_data
    ? (perf.shared_days >= 300 ? '1Y annualised'
       : `${perf.shared_days} days annualised, to ${perf.last_day}`)
    : '';
  const headline = (ret === null || ret === undefined)
    ? dashHtml()
    : `<span class="${ret >= 0 ? 'positive' : 'negative'}">${ret >= 0 ? '+' : ''}${escapeHtml(String(ret))}%</span>`;


  // My investment summary - the real row out of the holdings snapshot,
  // or an honest note if this fund is not held. The return itself is
  // display-layer arithmetic on the two figures the backend sent.
  const mine = d.my_investment || {};
  const invRaw = mine.invested && mine.invested.known ? mine.invested.raw : null;
  const curRaw = mine.current && mine.current.known ? mine.current.raw : null;
  let summaryBlock;
  if (!mine.has_position || invRaw === null || curRaw === null) {
    summaryBlock = `<div class="empty-note">This fund is not in your holdings snapshot yet - add it on the Investments tab and your invested value, returns and current value will appear here.</div>`;
  } else {
    const pl = curRaw - invRaw;
    const plPct = invRaw > 0 ? (pl / invRaw) * 100 : null;
    summaryBlock = `
      <div class="fa-cards">
        <div class="fa-card"><div class="kpi-label">Invested value</div>
          <div class="fa-card-value">&#8377;${inr(invRaw)}</div>
          ${mine.units ? `<div class="kpi-sub">${escapeHtml(String(mine.units))} units</div>` : ''}</div>
        <div class="fa-card"><div class="kpi-label">Total returns</div>
          <div class="fa-card-value ${pl >= 0 ? 'positive' : 'negative'}">${pl >= 0 ? '+' : '&minus;'}&#8377;${inr(Math.abs(pl))}${plPct !== null ? ` (${pl >= 0 ? '+' : '&minus;'}${Math.abs(plPct).toFixed(2)}%)` : ''}</div></div>
        <div class="fa-card"><div class="kpi-label">Current value</div>
          <div class="fa-card-value">&#8377;${inr(curRaw)}</div></div>
      </div>`;
  }

  // Key fund metrics - a dash with its reason wherever no free source
  // publishes the figure. Fetched or absent, never invented.
  const metrics = [
    ['NAV',
     (d.latest_nav !== null && d.latest_nav !== undefined) ? `&#8377;${inr(d.latest_nav)}` : dashHtml(),
     d.latest_nav_date ? `as of ${escapeHtml(String(d.latest_nav_date))}` : 'no NAV history stored yet'],
    ['Min SIP', dashHtml(), 'no free source publishes minimum SIP amounts'],
    ['Fund size (AUM)', dashHtml(), 'no free source publishes AUM for this scheme'],
    ['Expense ratio',
     (d.expense_ratio !== null && d.expense_ratio !== undefined)
       ? escapeHtml(String(d.expense_ratio)) + '%' : dashHtml(),
     'of assets, per year'],
    ['Rating', dashHtml(), 'no free rating feed - nothing invented here'],
  ];

  el.innerHTML = `
    <div class="fa-perf-row">
      <div class="fa-perf">${headline}</div>
      <div class="kpi-sub">${escapeHtml(windowLabel)}</div>
    </div>
    ${navChartSection((d.nav_history && d.nav_history.points) || [])}
    <div class="fa-section">
      <div class="panel-title"><i class="ph ph-user"></i>My investment summary</div>
      ${summaryBlock}
    </div>
    <div class="fa-section">
      <div class="panel-title"><i class="ph ph-list-checkmarks"></i>Key fund metrics</div>
      <div class="fa-ratio-grid">
        ${metrics.map(([label, value, sub]) => `
          <div class="fa-ratio">
            <div class="fa-ratio-value">${value}</div>
            <div class="fa-ratio-label">${escapeHtml(label)}</div>
            <div class="kpi-sub">${sub}</div>
          </div>`).join('')}
      </div>
    </div>`;

  // Range pills and the first draw of the interactive NAV chart.
  const points = (d.nav_history && d.nav_history.points) || [];
  el.querySelectorAll('.range-pill').forEach(btn => btn.addEventListener('click', () => {
    localStorage.setItem('fa_nav_range', btn.dataset.range);
    el.querySelectorAll('.range-pill').forEach(b => b.classList.toggle('active', b === btn));
    drawNavChart(points);
  }));
  drawNavChart(points);
}
// ── TAB 2 · Portfolio holdings list ──
function renderFaHoldings(el) {
  const ledger = (faProfile && faProfile.holdings_ledger) || [];
  el.innerHTML = `
    <input type="search" class="fa-search" placeholder="search company or sector&hellip;" aria-label="search holdings">
    ${ledger.length ? `
    <div class="scroll-x"><table class="data-table">
      <thead><tr><th>Company name</th><th>Sector</th><th>Asset class</th><th>% holding</th></tr></thead>
      <tbody>
        ${ledger.map(h => `
          <tr><td class="label-cell">${escapeHtml(h.name)}</td>
          <td>${escapeHtml(h.sector)}</td>
          <td>${escapeHtml(h.instrument)}</td>
          <td>${pct(h.assets_pct)}</td></tr>`).join('')}
      </tbody>
    </table></div>
    <div class="kpi-sub">${ledger.length} published holdings, portfolio as of ${escapeHtml((faProfile && faProfile.as_of) || '?')}</div>`
    : '<div class="empty-note">The published portfolio listed no holdings.</div>'}`;
  const input = el.querySelector('.fa-search');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    el.querySelectorAll('tbody tr').forEach(tr => {
      tr.style.display = (!q || tr.textContent.toLowerCase().includes(q)) ? '' : 'none';
    });
  });
}
// ── TAB 3 · Holdings analysis & splits - three doughnuts ──
const SECTOR_COLORS = ['#9b8cf2', '#7fb2f0', '#57c79a', '#e9c46a', '#e07b39',
                       '#ef8d8d', '#5fb8c9', '#c98bd9', '#b5cc74', '#8a97b5'];

function renderFaSplits(el) {
  const d = faProfile || {};
  const split = d.asset_split || {};
  const caps = d.market_cap_split || {};
  const sectors = (d.sector_allocation && d.sector_allocation.sectors) || [];
  _faDonutQueue = [];
  el.innerHTML =
    doughnutSection('Equity / Debt / Cash split', 'ph-chart-pie-slice', [
      { label: 'Equity', value: split.equity_pct, color: '#9b8cf2' },
      { label: 'Debt', value: split.debt_pct, color: '#d7a13c' },
      { label: 'Cash (residual)', value: split.cash_pct, color: '#7fb2f0' },
    ], escapeHtml(split._note || ''))
    + doughnutSection('Market Cap Split', 'ph-buildings', [
      { label: 'Large Cap', value: caps.large_cap_pct, color: '#2f9e6e' },
      { label: 'Mid Cap', value: caps.mid_cap_pct, color: '#e9c46a' },
      { label: 'Small Cap', value: caps.small_cap_pct, color: '#e07b39' },
      { label: 'Unknown (could not be sized)', value: caps.unknown_mcap_pct, color: '#8a97b5' },
    ], escapeHtml(caps._note || ''))
    + doughnutSection('Equity sector allocation', 'ph-factory',
      sectors.map((s, i) => ({
        label: s.name, value: s.assets_pct,
        color: SECTOR_COLORS[i % SECTOR_COLORS.length],
      })),
      pct(d.sector_allocation && d.sector_allocation.classified_coverage_pct)
      + ' classified'
      + ((d.sector_allocation && d.sector_allocation.verified_by_a_person === false)
          ? ' &middot; unverified map' : ''));
  initFaDonuts();
}
// ── TAB 4 · Advanced ratios, with the benchmark beside them ──
function renderFaRatios(el) {
  const d = faProfile || {};
  const perf = d.performance || {};
  const val = d.valuations || {};
  const benchName = (d.benchmark && d.benchmark.name) || 'benchmark';
  el.innerHTML = `
    <div class="panel-title"><i class="ph ph-gauge"></i>Advanced ratios
      <i class="ph ph-info fa-info-i" title="Every figure here is worked out from the stored daily pull - this fund's NAV history against the benchmark, day-aligned. Pure arithmetic; no model is involved."></i>
      <span class="kpi-sub" style="margin-left:auto">${perf.has_data ? escapeHtml('over ' + perf.shared_days + ' shared days, to ' + perf.last_day) : ''}</span></div>
    <div class="fa-ratio-grid">
      ${ratioInfoCard('volatility', 'Standard deviation', pctv(perf.volatility_pct), 'annualised')}
      ${ratioInfoCard('sharpe', 'Sharpe ratio', num(perf.sharpe))}
      ${ratioInfoCard('sortino', 'Sortino ratio', num(perf.sortino), perf.sortino_note || '')}
      ${ratioInfoCard('beta', 'Beta', num(perf.beta))}
      ${ratioInfoCard('alpha', 'Alpha', pctv(perf.alpha_pct))}
      ${ratioInfoCard('r_squared', 'R-squared', num(perf.r_squared))}
      ${ratioInfoCard('pe', 'Weighted P/E', num(val.pe), 'covers ' + pct(val.pe_coverage_pct) + ' of assets')}
      ${ratioInfoCard('pb', 'Weighted P/B', num(val.pb), 'covers ' + pct(val.pb_coverage_pct) + ' of assets')}
      ${ratioInfoCard('max_drawdown', 'Max drawdown', pctv(perf.max_drawdown_pct))}
      ${ratioInfoCard('return_1y', 'Return (ann.)', pctv(perf.return_1y_pct))}
    </div>
    ${perf.has_data ? `
    <div class="fa-section">
      <div class="panel-title"><i class="ph ph-scales"></i>This fund against ${escapeHtml(benchName)}</div>
      <div class="scroll-x"><table class="data-table">
        <thead><tr><th>measure</th><th>this fund</th><th>${escapeHtml(benchName)}</th></tr></thead>
        <tbody>
          <tr><td>Annualised return</td><td>${pctv(perf.return_1y_pct)}</td><td>${pctv(perf.benchmark_return_pct)}</td></tr>
          <tr><td>Annualised volatility</td><td>${pctv(perf.volatility_pct)}</td><td>${pctv(perf.benchmark_volatility_pct)}</td></tr>
          <tr><td>Beta</td><td>${num(perf.beta)}</td><td>1.00 by definition</td></tr>
          <tr><td>R-squared</td><td>${num(perf.r_squared)}</td><td>&mdash; how much of this comparison means anything</td></tr>
        </tbody>
      </table></div>
      <div class="kpi-sub">A low R-squared means beta and alpha say little here - the fund does not move with ${escapeHtml(benchName)} enough for those numbers to bite.</div>
    </div>`
    : `<div class="empty-note">${escapeHtml(perf.note || 'Ratios need the fund NAV history to overlap the benchmark for enough days.')}</div>`}
    <div class="fa-section">
      <div class="panel-title"><i class="ph ph-chart-line-up"></i>The history behind these numbers</div>
      <div id="fa-derived-charts"></div>
    </div>
    <div class="fa-section">
      <div class="panel-title"><i class="ph ph-info"></i>Where this came from</div>
      <div class="kpi-sub">Holdings: ${escapeHtml((d.where_from && d.where_from.holdings) || '?')} &middot;
        NAV history: ${escapeHtml((d.where_from && d.where_from.nav_history) || '?')} &middot;
        Company facts: ${escapeHtml((d.where_from && d.where_from.company_facts) || '?')}</div>
      ${(d.notes || []).map(n => `<div class="kpi-sub">&middot; ${escapeHtml(n)}</div>`).join('')}
    </div>`;
  drawdownAndRollingCharts(el, d);
}

const FA_RENDERERS = {
  overview: renderFaOverview,
  holdings: renderFaHoldings,
  splits: renderFaSplits,
  ratios: renderFaRatios,
};

// One delegated listener wires every analysis button, including rows
// that do not exist yet when this file loads.
document.addEventListener('click', e => {
  const btn = e.target.closest('.analysis-btn');
  if (!btn) return;
  const row = btn.closest('[data-scheme]');
  openFundAnalysis(btn.dataset.code || (row && row.dataset.code),
                   btn.dataset.name || (row && row.dataset.scheme));
});

LOADED.overview = true;
tickClock();
loadOverview();


