// =====================================================================
// THE PAGE TRACER - shared by every screen.
// Every meaningful click lands in the trace ledger
// (Shared_By_All_Screens/Trace_Ledger/traces_<date>.jsonl) via this
// screen's own /trace endpoint, so the nightly local-model reflection
// sees what you actually looked at and clicked - with enough context
// around each event that a model can learn from it, not just count it.
//
// A page opts in with ONE line before this script tag:
//     <script>window.INKY_TRACE = { actor: 'models', api: '/api/models' };</script>
// No config line, no tracing - stay silent rather than guess.
//
// WHAT counts as an event (v2, ADR-085 - the ledger became something a
// model learns from, so each event carries intent, not raw DOM noise):
//   clicks        buttons, links, tabs, selects, submit inputs, summary
//                 - labelled by data-trace="human purpose" when a page
//                 provides it, falling back to visible text
//   tab switches  recorded as from_tab -> to_tab, not just the arrival
//   field changes select/input changes record WHICH field changed and
//                 nothing else. Values are never traced - a password or
//                 a half-typed note is the page's business, not the log's
//   api calls     every fetch this page makes (except /trace itself and
//                 /dev polls) as one row with status and duration
//   errors        window error events, truncated, as kind "error"
//   page open     one row per load: where from, what viewport
//
// Events are batched (5 events or 2 seconds) and flushed on pagehide via
// navigator.sendBeacon, so closing a tab quickly still records the last
// few clicks. Fire-and-forget throughout: a failed trace never blocks,
// retries forever, or alerts; the ledger's rule is that it must not
// break the thing it observes.
// =====================================================================
(function () {
  'use strict';

  var cfg = window.INKY_TRACE || {};
  var API = cfg.api || '';
  if (!API) { return; }

  var loadedAt = Date.now();
  // One id per page load, so the nightly reflection can tell "one person
  // clicking forty things" apart from "forty separate visits".
  var sessionId = Math.random().toString(36).slice(2, 10);
  var queue = [];
  var flushTimer = null;

  function sendOne(event) {
    try {
      var body = JSON.stringify(event);
      // sendBeacon sends a bare string as text/plain, and the server's
      // Body(...) parameter needs application/json to parse it - a Blob
      // is the only way to give a beacon its own content type. Getting
      // this wrong means sendBeacon reports "queued" (true) while the
      // server 422s every single one - a failure invisible from here,
      // only visible by the ledger never gaining a row.
      if (navigator.sendBeacon) {
        var blob = new Blob([body], { type: 'application/json' });
        if (navigator.sendBeacon(API + '/trace', blob)) { return; }
      }
      fetch(API + '/trace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        keepalive: true,
      }).catch(function () {});
    } catch (e) { /* tracing must never break the page */ }
  }

  function flush() {
    var pending = queue;
    queue = [];
    if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; }
    for (var i = 0; i < pending.length; i++) { sendOne(pending[i]); }
  }

  function scheduleFlush() {
    if (!flushTimer) { flushTimer = setTimeout(flush, 2000); }
    if (queue.length >= 5) { flush(); }
  }

  function traceEvent(kind, action, target, detail, outcome, durationMs) {
    try {
      queue.push({
        // Every page declares its own actor in window.INKY_TRACE - without
        // this, every human click on every screen landed under the same
        // generic "you", and the Log tab's actor filter couldn't tell
        // Finance clicks from Learning clicks. 'you' stays as the fallback
        // for a page that opts in without naming itself.
        actor: cfg.actor || 'you',
        kind: kind, action: action, target: target || '',
        detail: detail || {}, outcome: outcome || 'ok',
        duration_ms: (typeof durationMs === 'number') ? durationMs : undefined,
      });
      scheduleFlush();
    } catch (e) { /* tracing must never break the page */ }
  }
  window.traceEvent = traceEvent;   // pages trace their own moments too

  // The tab currently showing, if this page uses tabs. Gives every click
  // on the page its surrounding context ("while looking at Overview").
  function activeTabName() {
    var active = document.querySelector('.tab-btn.active, .side-tab.active');
    return active ? (active.dataset.tab || active.textContent.trim()) : '';
  }

  function baseDetail(el) {
    var detail = {};
    try {
      detail.url = location.pathname;
      detail.sid = sessionId;
      detail.ms_since_load = Date.now() - loadedAt;
      var visible = activeTabName();
      if (visible) { detail.viewing_tab = visible; }
      if (el && el.tagName) {
        detail.tag = el.tagName.toLowerCase();
        if (el.id) { detail.id = el.id; }
        var cls = (el.className && typeof el.className === 'string')
          ? el.className.trim().split(/\s+/).slice(0, 3).join(' ') : '';
        if (cls) { detail.cls = cls; }
        var text = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
        if (text) { detail.text = text; }
        if (el.dataset.tab) { detail.tab = el.dataset.tab; }
        if (el.tagName === 'A' && el.getAttribute('href')) {
          detail.href = el.getAttribute('href').slice(0, 80);
        }
      }
    } catch (e) { /* a partial description beats a crashed listener */ }
    return detail;
  }

  // data-trace="save agent card" says WHY the element exists. A trace
  // that reads like speech teaches a model; "btn-primary" does not.
  function labelFor(el) {
    var purpose = el.closest('[data-trace]');
    if (purpose) { return purpose.getAttribute('data-trace'); }
    return (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40)
      || el.id || el.tagName.toLowerCase();
  }

  document.addEventListener('click', function (e) {
    var el = e.target.closest('button, a, [data-tab], [role="button"], select, input[type="submit"], summary');
    if (!el) { return; }
    var action = 'click';
    var target = labelFor(el);
    var detail = baseDetail(el);
    if (el.dataset.tab) {
      action = 'open_tab';
      target = el.dataset.tab;
      // Where the person came FROM is half of the story a model needs.
      var previous = detail.viewing_tab && detail.viewing_tab !== target
        ? detail.viewing_tab : '';
      if (previous) { detail.from_tab = previous; }
    }
    traceEvent('click', action, target, detail);
  }, true);

  // A changed field is a decision worth recording - but only WHICH
  // field, never what was typed or chosen into it.
  document.addEventListener('change', function (e) {
    try {
      var el = e.target;
      if (!el || !el.matches ||
          !el.matches('select, input:not([type="password"]), textarea')) {
        return;
      }
      var detail = baseDetail(el);
      var purpose = el.closest('[data-trace]');
      detail.field = el.name || el.id ||
        (purpose ? purpose.getAttribute('data-trace') : '') ||
        el.tagName.toLowerCase();
      traceEvent('click', 'changed_field', detail.field, detail);
    } catch (err) { /* never break the page over a log line */ }
  }, true);

  // One row per app API call, with its outcome and how long it took.
  // Skips the tracer's own endpoint and dev polls - those are plumbing,
  // not behaviour, and tracing them would loop forever.
  if (window.fetch) {
    var originalFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      var startedAt = Date.now();
      var path = '';
      try { path = (typeof input === 'string') ? input : input.url; }
      catch (e) { path = ''; }
      var promise = originalFetch(input, init);
      try {
        var skip = !path || path.indexOf('/trace') !== -1 ||
                   path.indexOf('/dev/') !== -1;
        if (!skip) {
          promise.then(function (res) {
            traceEvent('api',
                       ((init && init.method) || 'GET') + ' ' + path,
                       String(path).split('/').pop(), baseDetail(null),
                       res.status < 400 ? 'ok' : 'fail',
                       Date.now() - startedAt);
          }).catch(function () {
            traceEvent('api', 'FETCH ' + path, String(path).split('/').pop(),
                       baseDetail(null), 'fail', Date.now() - startedAt);
          });
        }
      } catch (e) { /* the real call already went out fine */ }
      return promise;
    };
  }

  // A crashed interaction is the most instructive event of all.
  window.addEventListener('error', function (e) {
    try {
      traceEvent('error', 'page_error', location.pathname, {
        message: String(e.message || '').slice(0, 120),
        source: e.filename ? String(e.filename).split('/').pop() : '',
        line: e.lineno || undefined,
        sid: sessionId,
      });
    } catch (err) { /* never break the page */ }
  });

  // One row per page load: which screen opened, where from. This is what
  // lets the reflection tell a busy day from an abandoned one.
  window.addEventListener('load', function () {
    traceEvent('view', 'open_page', location.pathname, {
      url: location.pathname, sid: sessionId,
      referrer: document.referrer ? document.referrer.slice(0, 80) : '',
      viewport: window.innerWidth + 'x' + window.innerHeight,
    });
  });

  // Closing or hiding the tab must not eat the last few events.
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { flush(); }
  });
})();
