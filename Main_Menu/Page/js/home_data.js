// ----------------------------------------------------------------------
//  home_data.js - the five top brief cards.
//
//  One agent owns the noticeboard read (POST /agents/home_blocks/refresh),
//  so the four "brief" cards share a single fetch: clicking any one of
//  them refreshes all four with ONE call, because that is genuinely what
//  is behind each one. The CARD_ENDPOINTS config still names each card
//  separately, so the day a per-block agent exists, pointing a card at
//  it is a one-line change - no rewrite.
//
//  Honest states throughout (C12): a card whose source answers with
//  nothing usable prints "Data unavailable" rather than keeping a stale
//  number or inventing one, and an empty answer ("nothing airs today")
//  is shown as the fact it is, never as an error.
// ----------------------------------------------------------------------
(function () {
  'use strict';

  // Defined once here; the other home_*.js files read window.INKY_API
  // rather than re-typing the prefix (one place to change it).
  const API = '/api/main_menu';
  window.INKY_API = API;

  // The one agent that reads the noticeboard. POST, because a refresh is
  // a command ("go look again"), not a question about a stable resource.
  const BLOCK_AGENT = {
    endpoint: API + '/agents/home_blocks/refresh',
    method: 'POST',
  };

  // Each card's extract pulls ONLY that card's fields out of the shared
  // block-agent response, so a malformed sibling block can never blank
  // an unrelated card. Response shape:
  //   { state, blocks: { total_assets: {amount, display},
  //     total_liabilities, before_slice_refill,
  //     inky_usage: {cost_display, input_display, output_display},
  //     claude_code_usage: { ... } } }
  const CARD_ENDPOINTS = {
    'assets': {
      wrapperId: 'card-assets',
      endpoint: BLOCK_AGENT.endpoint,
      method: BLOCK_AGENT.method,
      extract: function (data) {
        const block = (data.blocks && data.blocks.total_assets) || {};
        return {
          valueId: 'stat-assets', subId: 'stat-assets-sub',
          value: block.display,
          sub: block.amount === null || block.amount === undefined ? 'not tracked yet' : 'what you own',
          dim: block.amount === null || block.amount === undefined,
        };
      },
    },
    'liabilities': {
      wrapperId: 'card-liabilities',
      endpoint: BLOCK_AGENT.endpoint,
      method: BLOCK_AGENT.method,
      extract: function (data) {
        const block = (data.blocks && data.blocks.total_liabilities) || {};
        return {
          valueId: 'stat-liabilities', subId: 'stat-liabilities-sub',
          value: block.display,
          sub: block.amount === null || block.amount === undefined ? 'not tracked yet' : 'what you owe',
          dim: block.amount === null || block.amount === undefined,
        };
      },
    },
    'before-slice': {
      wrapperId: 'card-before-slice',
      endpoint: BLOCK_AGENT.endpoint,
      method: BLOCK_AGENT.method,
      extract: function (data) {
        const block = (data.blocks && data.blocks.before_slice_refill) || {};
        return {
          valueId: 'stat-before-slice', subId: 'stat-before-slice-sub',
          value: block.display,
          sub: block.amount === null || block.amount === undefined ? 'not tracked yet' : 'bills, debt & SIPs only',
          dim: block.amount === null || block.amount === undefined,
        };
      },
    },
    'model-cost': {
      wrapperId: 'card-model-cost',
      endpoint: BLOCK_AGENT.endpoint,
      method: BLOCK_AGENT.method,
      // The wide card holds two providers side by side, so its extract
      // returns a column list instead of a single value/sub pair.
      extract: function (data) {
        const blocks = data.blocks || {};
        const inky = blocks.inky_usage || {};
        const claude = blocks.claude_code_usage || {};
        return {
          cols: [
            {
              valueId: 'cost-inky', tokensId: 'tokens-inky',
              value: inky.cost_display,
              tokens: (inky.input_display || '—') + ' in / ' + (inky.output_display || '—') + ' out',
            },
            {
              valueId: 'cost-claude', tokensId: 'tokens-claude',
              value: claude.cost_display,
              tokens: (claude.input_display || '—') + ' in / ' + (claude.output_display || '—') + ' out',
            },
          ],
        };
      },
    },
  };

  // The four cards the block agent feeds.
  const BLOCK_KEYS = ['assets', 'liabilities', 'before-slice', 'model-cost'];

  const FETCH_TIMEOUT_MS = 15000;

  // Per-card in-flight flags: a double-click must not stack two fetches
  // and race two writers onto the same DOM nodes.
  const inFlight = {};

  function byId(id) { return document.getElementById(id); }

  // Every fetch goes through here: an AbortController timeout so a hung
  // agent cannot leave a card spinning forever, and a res.ok check so an
  // HTTP failure is treated exactly like a network failure.
  async function fetchJson(endpoint, method) {
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
    try {
      const res = await fetch(endpoint, { method: method || 'GET', signal: controller.signal });
      if (!res.ok) throw new Error('answered ' + res.status);
      return await res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  // Write a successful extract result onto the card. Error classes are
  // cleared here too - a card that failed once and succeeded after must
  // come back looking healthy, not stay stained red.
  function applyResult(key, result) {
    if (result.cols) {
      result.cols.forEach(function (col) {
        const valueEl = byId(col.valueId);
        const tokensEl = byId(col.tokensId);
        if (valueEl) {
          valueEl.textContent = col.value;
          valueEl.classList.remove('error-state');
        }
        if (tokensEl) {
          tokensEl.textContent = col.tokens;
          tokensEl.classList.remove('error-note');
        }
      });
      return;
    }
    const valueEl = byId(result.valueId);
    const subEl = byId(result.subId);
    if (valueEl) {
      // A blank display from the server prints as the dash it already is
      // (house rule: never paper over a missing figure with a guess).
      valueEl.textContent = result.value || '—';
      valueEl.classList.remove('error-state');
      valueEl.classList.toggle('dim', !!result.dim);
    }
    if (subEl) {
      subEl.textContent = result.sub;
      subEl.classList.remove('error-note');
    }
  }
  // Failure is printed, not hidden (C12): the value says plainly that the
  // data is unavailable and a sub-line says briefly why. The card's own
  // extract is probed against an empty payload to find which element ids
  // it owns - one source of truth for where an error lands.
  function renderError(key, reason) {
    const cfg = CARD_ENDPOINTS[key];
    if (!cfg) return;
    let probe;
    try {
      probe = cfg.extract({ blocks: {} });
    } catch (err) {
      return; // best-effort only; never let error rendering throw
    }
    if (probe.cols) {
      probe.cols.forEach(function (col, i) {
        const valueEl = byId(col.valueId);
        const tokensEl = byId(col.tokensId);
        if (valueEl) {
          valueEl.textContent = i === 0 ? 'Data unavailable' : '—';
          valueEl.classList.add('error-state');
          valueEl.classList.remove('dim');
        }
        if (tokensEl) {
          tokensEl.textContent = i === 0 ? reason : '— in / — out';
          tokensEl.classList.add('error-note');
        }
      });
      return;
    }
    const valueEl = byId(probe.valueId);
    const subEl = byId(probe.subId);
    if (valueEl) {
      valueEl.textContent = 'Data unavailable';
      valueEl.classList.add('error-state');
      valueEl.classList.remove('dim');
    }
    if (subEl) {
      subEl.textContent = reason;
      subEl.classList.add('error-note');
    }
  }

  // Refresh ONE card against ITS OWN endpoint. Today the four brief cards
  // all share the block agent, so this path is unused - the per-card
  // shape is kept so that a card getting its own dedicated agent later is
  // a config edit, not a rewrite.
  async function refreshCard(key) {
    const cfg = CARD_ENDPOINTS[key];
    if (!cfg) return;
    const wrapper = byId(cfg.wrapperId);
    if (!wrapper) return;

    // No endpoint, no fetch - saying so IS the feature (C12).
    if (!cfg.endpoint) return;

    if (inFlight[key]) return;
    inFlight[key] = true;
    wrapper.classList.add('loading');

    try {
      const data = await fetchJson(cfg.endpoint, cfg.method);
      // The block agent answers {state:'finished', blocks}; other cards
      // answer their own shape and carry ok instead. Either way, a
      // refusal or an unavailable source goes down the same honest
      // error path, showing the server's own reason where it gave one.
      if (!data || data.ok === false ||
          (data.state && data.state !== 'finished')) {
        renderError(key, (data && data.reason)
          ? String(data.reason)
          : 'the agent did not finish');
        return;
      }
      applyResult(key, cfg.extract(data));
    } catch (err) {
      renderError(key, err && err.name === 'AbortError'
        ? 'the agent took too long'
        : 'the agent could not be reached');
    } finally {
      inFlight[key] = false;
      wrapper.classList.remove('loading');
    }
  }
  // One fetch, four cards. The brief cards all read off the same
  // noticeboard, so hitting the endpoint four times would be four
  // identical agent runs - this does the read once and fans the result
  // out through each card's own extract.
  let blockInFlight = false;
  async function refreshBlockAgent() {
    if (blockInFlight) return;
    blockInFlight = true;

    const wrappers = BLOCK_KEYS
      .map(function (k) { return byId(CARD_ENDPOINTS[k].wrapperId); })
      .filter(Boolean);
    wrappers.forEach(function (w) { w.classList.add('loading'); });

    try {
      const data = await fetchJson(BLOCK_AGENT.endpoint, BLOCK_AGENT.method);
      if (!data || data.state !== 'finished') {
        BLOCK_KEYS.forEach(function (k) { renderError(k, 'the agent did not finish'); });
        return;
      }
      // One bad block must not stop its siblings from rendering.
      BLOCK_KEYS.forEach(function (k) {
        try {
          applyResult(k, CARD_ENDPOINTS[k].extract(data));
        } catch (err) {
          renderError(k, 'the answer was not the expected shape');
        }
      });
      stampAsOf();
    } catch (err) {
      const reason = err && err.name === 'AbortError'
        ? 'the agent took too long'
        : 'the agent could not be reached';
      BLOCK_KEYS.forEach(function (k) { renderError(k, reason); });
    } finally {
      blockInFlight = false;
      wrappers.forEach(function (w) { w.classList.remove('loading'); });
    }
  }

  // Rule 6: a number's age has to be visible. This stamps when the
  // noticeboard was actually READ, not when Finance last computed it -
  // the noticeboard is only as fresh as its last read.
  function stampAsOf() {
    const el = byId('brief-as-of');
    if (!el) return;
    el.textContent = 'AS OF ' +
      new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  // ------------------------------------------------------------------
  //  Wiring
  // ------------------------------------------------------------------
  document.querySelectorAll('[data-refresh]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const kind = btn.dataset.refresh;
      if (kind === 'brief') {
        refreshBlockAgent();
      }
      // 'clock' is deliberately NOT bound here: the inline script already
      // attaches its own instant re-tick handler to that button, and two
      // handlers would just tick twice. If that inline handler is ever
      // removed, this is the line to add back.
    });
  });

  // Initial read on load.
  // NOTE: during the transition the inline script's old refreshHomeBrief
  // may still fire on load and on the same brief buttons. Every writer
  // here is idempotent and guarded against double-fire, so a double
  // fetch is wasteful at worst, never wrong.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refreshBlockAgent);
  } else {
    refreshBlockAgent();
  }
})();