// =====================================================================
// SCRIPT FOR: Learning
// =====================================================================
// Rebuilt 2026-08 as one IIFE. Talks only to this screen's own API
// (/api/learning/...) - never another screen's port, never an import.
// Every server string passes through esc(); every POST re-fetches the
// data it touched (no optimistic lies); skeletons show during fetches;
// all motion respects prefers-reduced-motion.
(function () {
  'use strict';

  var API = '/api/learning';
  var DASH = '—';
  var REDUCE = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // â”€â”€ tiny helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
  }

  async function json(url, opts) {
    var res = await fetch(url, opts);
    var data = {};
    try { data = await res.json(); } catch (e) { /* non-JSON body */ }
    if (!res.ok) {
      throw new Error((data && data.problem) ? data.problem : url + ' answered ' + res.status);
    }
    return data;
  }
  function getJson(url) { return json(url); }
  function post(path, body) {
    return json(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
  }

  function toast(msg, kind) {
    var stack = $('#toast-stack');
    var el = document.createElement('div');
    el.className = 'toast' + (kind ? ' ' + kind : '');
    el.textContent = msg;
    stack.appendChild(el);
    requestAnimationFrame(function () { el.classList.add('show'); });
    setTimeout(function () {
      el.classList.remove('show');
      setTimeout(function () { el.remove(); }, 300);
    }, 2600);
  }

  // â”€â”€ modal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  var scrim = $('#modal-scrim'), modalBox = $('#modal-box');

  function openModal(html) {
    modalBox.innerHTML = html;
    scrim.hidden = false;
    requestAnimationFrame(function () { scrim.classList.add('open'); });
  }
  function closeModal() {
    scrim.classList.remove('open');
    setTimeout(function () { scrim.hidden = true; modalBox.innerHTML = ''; }, REDUCE ? 0 : 210);
  }
  scrim.addEventListener('click', function (e) { if (e.target === scrim) closeModal(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !scrim.hidden) closeModal();
  });

  // reads a modal's fields into an object by id
  function formValues(ids) {
    var out = {};
    ids.forEach(function (id) {
      var el = $('#' + id, modalBox);
      out[id] = el ? el.value.trim() : '';
    });
    return out;
  }

  function skeleton(el, blocks) {
    var html = '';
    for (var i = 0; i < (blocks || 3); i++) {
      html += '<div class="skel" style="height:' + (46 + (i % 2) * 18) + 'px;margin-bottom:10px"></div>';
    }
    el.innerHTML = html;
  }

  // rAF count-up for a number; instant under reduced motion
  function countUp(el, target, suffix) {
    suffix = suffix || '';
    if (REDUCE) { el.textContent = String(target) + suffix; return; }
    var t0 = null, dur = 800;
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      p = 1 - Math.pow(1 - p, 3); // easeOutCubic
      el.textContent = Math.round(target * p) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // set a circular SVG fill (r=42 -> circumference â‰ˆ 263.9)
  var RING_C = 264;
  function setRing(circleEl, fraction) {
    fraction = Math.max(0, Math.min(1, fraction || 0));
    var offset = RING_C * (1 - fraction);
    if (REDUCE) { circleEl.style.strokeDashoffset = offset; return; }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { circleEl.style.strokeDashoffset = offset; });
    });
  }

  // ════════════════════════════════════════════════════════════════
  //  STATE
  // ════════════════════════════════════════════════════════════════
  var S = {
    tab: 'today',
    planSub: 'topics',
    today: null,
    topics: null,
    weeks: null,
    planLoose: null,
    modulesBoard: null,
    study: null,
    cards: null,
    runningSession: null,   // the freshest known running session, set by
                             // /today, /study/start and /study/stop alike -
                             // Plan starts a session but does not live on
                             // the Today tab, so this is the one place
                             // every reader knows to check.
    reviewIndex: 0
  };

  function liveRunningSession() {
    return S.runningSession || (S.today || {}).running_session
        || (S.study || {}).running_session || null;
  }
  var LOADED = {};
  var elapsedTimer = null;   // ticks the running session clock(s)
  var elapsedBase = { seconds: 0, at: 0 }; // server value + when we fetched it

  function stopElapsedTimer() {
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  }
  function startElapsedTicker() {
    stopElapsedTimer();
    function paint() {
      var secs = Math.floor(elapsedBase.seconds + (Date.now() - elapsedBase.at) / 1000);
      var mm = Math.floor(secs / 60), ss = secs % 60;
      var txt = (mm < 10 ? '0' : '') + mm + ':' + (ss < 10 ? '0' : '') + ss;
      $all('[data-elapsed]').forEach(function (el) { el.textContent = txt; });
      $all('[data-elapsed-min]').forEach(function (el) { el.textContent = mm + ' min'; });
    }
    if (!REDUCE) { elapsedTimer = setInterval(paint, 1000); }
    paint();
  }

  // ════════════════════════════════════════════════════════════════
  //  NAV - icon rail with a sliding pill
  // ════════════════════════════════════════════════════════════════
  var rail = $('#rail'), railPill = $('#rail-pill');

  function moveRailPill() {
    var btn = $('.rail-item.active', rail);
    if (!btn) return;
    var x = btn.offsetLeft - rail.clientLeft;
    var y = btn.offsetTop - rail.clientTop;
    var horizontal = window.matchMedia('(max-width: 820px)').matches;
    if (horizontal) {
      railPill.style.height = btn.offsetHeight + 'px';
      railPill.style.width = btn.offsetWidth + 'px';
      railPill.style.transform = 'translate(' + x + 'px,' + y + 'px)';
    } else {
      railPill.style.width = '';
      railPill.style.height = btn.offsetHeight + 'px';
      railPill.style.transform = 'translate(0px,' + y + 'px)';
    }
  }

  var LOADERS = { today: loadToday, plan: loadPlan, recall: loadRecall };

  $all('.rail-item').forEach(function (btn) {
    btn.addEventListener('click', function () { goToTab(btn.dataset.tab); });
  });

  function goToTab(tab) {
    S.tab = tab;
    $all('.rail-item').forEach(function (b) { b.classList.toggle('active', b.dataset.tab === tab); });
    $all('.tab-pane').forEach(function (p) { p.classList.toggle('active', p.id === 'pane-' + tab); });
    moveRailPill();
    LOADERS[tab]();
  }

  window.addEventListener('resize', function () {
    moveRailPill();
    moveThumb('plan');
  });

  // ── sub-nav segmented pills with sliding thumb ─────────────────────
  function moveThumb(kind) {
    var nav = $('#' + kind + '-subnav');
    var thumb = $('#' + kind + '-thumb');
    var btn = $('button.active', nav);
    if (!btn) return;
    thumb.style.width = btn.offsetWidth + 'px';
    thumb.style.transform = 'translate(' + (btn.offsetLeft - nav.offsetLeft) + 'px,0)';
  }

  $('#plan-subnav').addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-sub]');
    if (!btn || btn.dataset.sub === S.planSub) return;
    S.planSub = btn.dataset.sub;
    $all('button', this).forEach(function (b) { b.classList.toggle('active', b === btn); });
    moveThumb('plan');
    renderPlan();
  });

  // ════════════════════════════════════════════════════════════════
  //  TAB 1 - TODAY (bento grid)
  // ════════════════════════════════════════════════════════════════
  async function loadToday() {
    var el = $('#today-bento');
    skeleton(el, 5);
    var d;
    try {
      d = await getJson(API + '/today');
      // the heatmap lives on /study (it always has); a failure here must
      // never block the rest of Today from showing.
      getJson(API + '/study').then(function (s) { S.study = s; renderHeatmap((s || {}).heatmap || {}); }).catch(function () {});
    }
    catch (err) {
      el.innerHTML = '<div class="empty-note bad">Could not reach ' + esc(API) + '/today — ' + esc(err.message) + '</div>';
      return;
    }
    S.today = d;
    S.runningSession = d.running_session || null;
    renderToday();

    // recall badge on the rail = cards due + notes due
    var dueTotal = (d.due_cards || 0);
    var badge = $('#badge-recall');
    if (dueTotal > 0) { badge.textContent = String(dueTotal); badge.hidden = false; }
    else { badge.hidden = true; }
  }

  function todayRowCell(kind, value) {
    if (!value) return '<div class="track-cell ' + kind + ' none">nothing planned</div>';
    return '<div class="track-cell ' + kind + '">' + esc(value) + '</div>';
  }

  function checkRowHtml(key, name, done) {
    return ''
    + '<div class="check-row' + (done ? ' done' : '') + '" data-action="checklist" data-key="' + key + '"'
    +   ' role="checkbox" aria-checked="' + (done ? 'true' : 'false') + '" tabindex="0">'
    +   '<span class="tick-box"><svg viewBox="0 0 14 14"><path d="M2.5 7.5 L5.8 10.5 L11.5 3.5"/></svg></span>'
    +   '<span class="check-name">' + name + '</span>'
    + '</div>';
  }

  // ── a planned day's timed blocks ───────────────────────────────────
  // One reading of the same data in three places: the proportional bar,
  // the short list on Today, and the full list with bullets in a modal.
  // Nothing here computes anything about the day - it only draws what
  // the week plan already says.

  // "0:00-0:25" -> 25. Returns 0 when the clock is not a range, which
  // is what makes the bar fall back to equal widths instead of guessing.
  function chunkMinutes(clock) {
    var m = String(clock || '').match(/(\d+):(\d\d)\D+(\d+):(\d\d)/);
    if (!m) return 0;
    var from = (+m[1]) * 60 + (+m[2]);
    var to = (+m[3]) * 60 + (+m[4]);
    return to > from ? to - from : 0;
  }

  function chunkBarHtml(chunks) {
    if (!chunks || !chunks.length) return '';
    var total = 0;
    chunks.forEach(function (c) { total += chunkMinutes(c.clock); });
    var segs = chunks.map(function (c) {
      var mins = chunkMinutes(c.clock);
      var flex = total ? (mins || 1) : 1;
      return '<span class="cseg ' + esc(c.kind || 'study') + '" style="flex:' + flex + '"'
        + ' title="' + esc((c.clock ? c.clock + ' - ' : '') + (c.title || '')) + '">'
        + (mins ? '<em class="mono">' + mins + 'm</em>' : '') + '</span>';
    }).join('<span class="cseg brk"></span>');
    return '<div class="chunkbar" role="img" aria-label="the shape of the day">' + segs + '</div>'
      + (total ? '<div class="chunkbar-total mono">planned ' + Math.floor(total / 60) + 'h '
                 + (total % 60) + 'm across ' + chunks.length + ' blocks</div>' : '');
  }

  function chunkBadge(kind) {
    if (kind === 'lab') return '<span class="chunk-badge lab">hands-on</span>';
    if (kind === 'recall') return '<span class="chunk-badge recall">recall card</span>';
    return '';
  }

  function chunkListHtml(chunks, withPoints) {
    if (!chunks || !chunks.length) return '';
    return '<ol class="chunklist' + (withPoints ? '' : ' compact') + '">'
      + chunks.map(function (c) {
        return '<li class="chunk-item ' + esc(c.kind || 'study') + '">'
          + '<span class="chunk-clock mono">' + esc(c.clock || '') + '</span>'
          + '<div class="chunk-body">'
          +   '<div class="chunk-title">' + esc(c.title || '') + chunkBadge(c.kind) + '</div>'
          +   (withPoints && (c.points || []).length
              ? '<ul class="chunk-points">' + c.points.map(function (pt) {
                  return '<li>' + esc(pt) + '</li>'; }).join('') + '</ul>'
              : '')
          + '</div>'
          + '</li>';
      }).join('') + '</ol>';
  }

  function eveningHtml(evening, withPoints) {
    if (!evening || !evening.title) return '';
    return '<div class="evening-block">'
      + '<div class="evening-label mono">Evening &middot; Track B &middot; 60 min</div>'
      + '<div class="evening-title">' + esc(evening.title) + '</div>'
      + (withPoints && (evening.points || []).length
         ? '<ul class="chunk-points">' + evening.points.map(function (pt) {
             return '<li>' + esc(pt) + '</li>'; }).join('') + '</ul>'
         : '')
      + '</div>';
  }

  // The kinds a day can be. A day that is not a study day says so
  // plainly rather than showing an empty chunk list.
  function dayKindNote(kind) {
    if (kind === 'off') return 'Off by the contract - no lessons, no cards, no review.';
    if (kind === 'consolidation') return 'Consolidation - review, the Sunday test, corrections, next week\u2019s plan.';
    if (kind === 'prep') return 'Preparation day - set the lab up, no lesson.';
    if (kind === 'buffer') return 'Buffer - re-teach anything rated Again, or interview prep.';
    return '';
  }

  function renderToday() {
    var d = S.today;
    if (!d) return;
    var st = d.streak || {};
    var cl = d.checklist || {};
    var rs = d.running_session || null;

    // running session clock baseline
    if (rs) {
      elapsedBase.seconds = (rs.elapsed_minutes || 0) * 60;
      elapsedBase.at = Date.now();
      startElapsedTicker();
    } else {
      stopElapsedTimer();
    }

    // today's schedule - replaces the old weekly-budget gauge
    var sch = d.schedule || {};
    var recent = d.recent_activity || [];

    var html = ''

    // 1 · hero streak ring + the real activity that fed it
    + '<div class="card cell-hero">'
    +   '<div class="streak-ring">'
    +     '<svg viewBox="0 0 96 96" aria-hidden="true">'
    +       '<circle class="ring-track" cx="48" cy="48" r="42"></circle>'
    +       '<circle class="ring-fill" id="today-ring" cx="48" cy="48" r="42"></circle>'
    +     '</svg>'
    +     '<div class="ring-num"><span id="ring-count">0</span>'
    +       '<span style="font-size:0.55rem;color:var(--muted);font-weight:600">days</span></div>'
    +   '</div>'
    +   '<div class="hero-side">'
    +     '<div><div class="card-label">Progress</div>'
    +       '<div style="font-size:0.92rem;font-weight:600">Day streak</div>'
    +       '<div class="card-sub">' + (st.last_studied ? 'last studied ' + esc(st.last_studied) : 'never studied yet')
    +         '. Updates the moment a session is stopped.</div></div>'
    +       '<div class="hero-activity">'
    +         (recent.length
    ? recent.map(function (s, i) {
        return '<div class="activity-row' + (i === 0 ? ' newest' : '') + '">'
        + '<span class="activity-min mono">' + esc(String(s.minutes)) + '&prime;</span>'
        + '<span class="activity-topic">' + esc(s.topic) + '</span>'
        + '<span class="activity-date mono">' + esc(s.date) + '</span>'
        + '</div>';
      }).join('')
    : '<div class="activity-empty">No blocks yet - stop your first session and it lands here.</div>')
    +       '</div>'
    +   '</div>'
    + '</div>'

    // 2 · today's study schedule (replaces weekly budget)
    + '<div class="card cell-budget">'
    +   '<div class="card-label">Today&rsquo;s study schedule</div>'
    + (sch.week_found
    ?   '<div class="sched-head">'
    +     '<span class="mono sched-day">' + esc(sch.day_name || '') + ' ' + esc(sch.date || '') + '</span>'
    +     '<button class="day-done-box' + (sch.day_done ? ' on' : '') + '" data-action="toggle-today-row" type="button"'
    +       ' aria-label="Mark day done" title="' + (sch.day_done ? 'done' : 'mark done') + '">' + (sch.day_done ? '&#10003;' : '') + '</button>'
    +   '</div>'
    +   '<div class="sched-line"><span class="sched-track a">A</span>'
    +     '<span>' + (sch.track_a ? esc(sch.track_a) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</span></div>'
    +   '<div class="sched-line"><span class="sched-track b">B</span>'
    +     '<span>' + (sch.track_b ? esc(sch.track_b) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</span></div>'
    + (dayKindNote(sch.kind)
    ?   '<div class="sched-kind">' + esc(dayKindNote(sch.kind)) + '</div>' : '')
    + chunkBarHtml(sch.chunks)
    + chunkListHtml(sch.chunks, false)
    + eveningHtml(sch.evening, false)
    + ((sch.chunks && sch.chunks.length)
    ?   '<div style="margin:10px 0 2px"><button class="btn ghost small"'
    +     ' data-action="open-today-plan" type="button">OPEN THE FULL DAY PLAN</button></div>' : '')
    +   '<div class="sched-target"><span>Allocated time:</span>'
    +     '<input type="number" min="1" max="1440" class="field target-input" id="sched-target" value="'
    +       (sch.target_minutes !== null && sch.target_minutes !== undefined ? esc(String(sch.target_minutes)) : '')
    +       '" placeholder="min">'
    +     '<button class="btn ghost small" data-action="schedule-target-save" type="button">SAVE</button>'
    +   '</div>'
    :   '<div class="empty-note" style="border:none;padding:2px 0">'
    +     (sch.next_week_start
          ? 'Nothing planned today. The plan starts on ' + esc(sch.next_week_start)
            + ' with Week ' + esc(String(sch.next_week_num)) + ' - see Plan &rarr; This Week.'
          : 'No week covers today - plan one under Plan &rarr; This Week.')
    +   '</div>')
    + '</div>'

    // 3 · notes explorer (replaces the due-now counter)
    + '<div class="card cell-due" data-action="open-notes-explorer" role="button" tabindex="0"'
    +   ' aria-label="Open the notes explorer" title="Browse every note">'
    +   '<div class="card-label">Notes explorer</div>'
    +   '<div class="due-count ok">' + (S.notesCount !== undefined ? S.notesCount : '&#8230;') + '</div>'
    +   '<div class="due-hint">markdown notes, by topic. Browse &rarr;</div>'
    + '</div>'

    // 4 · running session pulse card
    + '<div class="card cell-session">'
    +   '<div class="card-label">Study session</div>'
    + (rs
    ?   '<div class="session-line"><span class="pulse-dot"></span>'
    +     '<span>Studying <strong>' + esc(rs.topic) + '</strong></span>'
    +     '<span class="session-elapsed" data-elapsed>--:--</span>'
    +     '<button class="btn danger small" data-action="stop-session" type="button" style="margin-left:auto">STOP</button></div>'
    :   '<div class="empty-note" style="border:none;padding:2px 0">No session running. Open START LEARNING on a topic in Plan.</div>')
    + '</div>'

    // 5 · daily checklist with animated tick morph
    + '<div class="card cell-checklist">'
    +   '<div class="card-label">Today&rsquo;s checklist</div>'
    +   checkRowHtml('core', 'Core session', cl.core)
    +   checkRowHtml('trackb', 'Track B hour', cl.trackb)
    +   checkRowHtml('capture', 'Work capture', cl.capture)
    + '</div>'

    // 6 · consistency heatmap - relocated from the old Study tab
    // (ADR-100) since Study merged into Plan and this real history
    // still deserves a home.
    + '<div class="card cell-heatmap">'
    +   '<div class="card-label">Consistency &middot; last 26 weeks</div>'
    +   '<div class="heatmap-scroll"><div class="heatmap" id="today-heatmap"></div></div>'
    + '</div>';

    $('#today-bento').innerHTML = html;

    // entrance animations
    setRing($('#today-ring'), Math.min(1, (st.days || 0) / 7));
    countUp($('#ring-count'), st.days || 0);
    renderHeatmap((S.study || {}).heatmap || {});
  }

  // ════════════════════════════════════════════════════════════════
  //  TAB 2 - PLAN (Topics | This Week) + loose items strip
  // ════════════════════════════════════════════════════════════════
  async function loadPlan() {
    var el = $('#plan-body');
    skeleton(el, 4);
    var jobs = [
      getJson(API + '/topics').then(function (d) { S.topics = d; }),
      getJson(API + '/weeks').then(function (d) { S.weeks = d; }),
      getJson(API + '/plan').then(function (d) { S.planLoose = d; }),
      // which topics have a linked study module (ADR-100: this is what
      // used to be the Study tab's own board) - reused here to decide
      // whether a topic row grows a START LEARNING / NOTES pair.
      getJson(API + '/modules').then(function (d) { S.modulesBoard = d; })
    ];
    try { await Promise.all(jobs); }
    catch (err) {
      el.innerHTML = '<div class="empty-note bad">Could not reach the plan API — ' + esc(err.message) + '</div>';
      return;
    }
    renderPlan();
    renderLooseItems();
  }

  // One topic's module link, or null when it has none yet. A flat scan
  // over ~32 rows is Tier 0 money - not worth a lookup table.
  function moduleInfoFor(topicId) {
    var groups = ((S.modulesBoard || {}).groups) || [];
    for (var g = 0; g < groups.length; g++) {
      var rows = groups[g].topics || [];
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].id === topicId) return rows[i];
      }
    }
    return null;
  }

  function miniRingHtml(pct, colorVar) {
    return ''
    + '<span class="mini-ring">'
    +   '<svg viewBox="0 0 44 44" aria-hidden="true">'
    +     '<circle class="ring-track" cx="22" cy="22" r="18"></circle>'
    +     '<circle class="ring-fill" cx="22" cy="22" r="18" style="stroke:' + colorVar + ';'
    +       'stroke-dasharray:' + Math.round(2 * Math.PI * 18) + ';stroke-dashoffset:'
    +       Math.round(2 * Math.PI * 18 * (1 - pct / 100)) + '"></circle>'
    +   '</svg>'
    +   '<span>' + pct + '%</span>'
    + '</span>';
  }

  function trackSectionHtml(trackKey, title) {
    var t = (S.topics || {})[trackKey];
    if (!t) return '';
    var groups = t.groups || [];
    var prog = t.progress || { done: 0, total: 0, pct: 0 };
    var cls = trackKey === 'trackA' ? 'track-a' : 'track-b';
    var color = trackKey === 'trackA' ? 'var(--signal)' : 'var(--violet)';
    var html = '<section class="track-section ' + cls + ' rise">'
    + '<div class="track-header">'
    +   miniRingHtml(prog.pct || 0, color)
    +   '<div><div class="track-title">' + title + '</div>'
    +     '<div class="card-sub mono">' + (prog.done || 0) + ' of ' + (prog.total || 0) + ' topics done</div></div>'
    + '</div>';

    if (!groups.length) {
      html += '<div class="empty-note">No topics recorded for this track yet.</div></section>';
      return html;
    }

    groups.forEach(function (g) {
      var topics = g.topics || [];
      var done = topics.filter(function (x) { return x.status === 'done'; }).length;
      var pct = topics.length ? Math.round(100 * done / topics.length) : 0;
      html += '<div class="group-block">'
      + '<div class="group-head"><span class="group-name">' + esc(g.group) + '</span>'
      +   '<span class="group-count">' + done + '/' + topics.length + '</span></div>'
      + '<div class="group-bar"><i data-width="' + pct + '"></i></div>';
      if (!topics.length) {
        html += '<div class="empty-note" style="border:none;padding:2px 0">No topics in this group yet.</div>';
      }
      topics.forEach(function (tp) {
        html += topicRowHtml(tp);
      });
      html += '</div>';
    });
    return html + '</section>';
  }

  // A topic that has a real module grows two buttons (ADR-100): START
  // LEARNING opens it and auto-tracks the session; NOTES opens the same
  // note to read, no session side-effect. A topic with no module yet
  // grows neither - a button that opens nothing is exactly the dead
  // control Rule 12 forbids.
  function topicActionsHtml(tp) {
    var mod = moduleInfoFor(tp.id);
    if (!mod || mod.module_state !== 'ready') return '';
    var progress = mod.tasks_total
      ? '<span class="topic-progress mono">' + esc(String(mod.tasks_done)) + '/' + esc(String(mod.tasks_total)) + '</span>'
      : '';
    return '<div class="topic-actions">'
      + progress
      + '<button class="btn ghost small" data-action="open-notes-for-topic"'
      +   ' data-file="' + esc(mod.note_file) + '" type="button">NOTES</button>'
      + '<button class="btn primary small" data-action="start-learning"'
      +   ' data-topic="' + esc(tp.topic) + '" data-file="' + esc(mod.note_file) + '" type="button">START LEARNING</button>'
      + '</div>';
  }

  function topicRowHtml(tp) {
    var status = tp.status === 'doing' || tp.status === 'done' ? tp.status : 'todo';
    var label = status === 'todo' ? '' : status;
    return ''
    + '<div class="topic-row">'
    +   '<button class="status-dot ' + (status === 'todo' ? '' : status) + '" type="button"'
    +     ' data-action="topic-status" data-id="' + esc(tp.id) + '" data-current="' + status + '"'
    +     ' aria-label="Status: ' + status + '. Click to change." title="click to cycle"></button>'
    +   '<span class="topic-name">' + esc(tp.topic) + '</span>'
    // Phase-1 CS-4: seeded rows say so - starter data is yours to delete,
    // and it must never look like history that accumulated on its own.
    +   (tp.starter ? '<span class="starter-badge" title="Starter data traced to your own contract file - yours to delete">starter</span>' : '')
    +   '<span class="tier ' + esc(tp.tier || 'defer') + '">' + esc(tp.tier || '?') + '</span>'
    +   '<span class="status-label">' + label + '</span>'
    +   topicActionsHtml(tp)
    + '</div>';
  }

  function renderPlan() {
    var el = $('#plan-body');
    if (S.planSub === 'topics') {
      if (!S.topics) { skeleton(el, 4); return; }
      el.innerHTML = trackSectionHtml('trackA', 'Track A — Splunk')
                   + trackSectionHtml('trackB', 'Track B — Detection &amp; Cloud Security');
      requestAnimationFrame(function () {
        $all('.group-bar i', el).forEach(function (bar) {
          bar.style.width = bar.dataset.width + '%';
        });
      });
    } else {
      if (!S.weeks) { skeleton(el, 4); return; }
      el.innerHTML = weeksHtml();
      requestAnimationFrame(function () {
        moveThumb('plan');
      });
    }
  }

  function weeksHtml() {
    var w = S.weeks || {};
    var weeks = w.weeks || [];
    // The accordion IS the week view now: each track lists its topic
    // groups as expandable rows with Done / Pending inside. The day grid
    // stays available under a collapsed edit section - nothing removed,
    // only re-levelled.
    var html = '<div style="display:flex;justify-content:flex-end;margin-bottom:12px">'
    + '<button class="btn primary small" data-action="week-add" type="button">+ ADD WEEK</button></div>';

    html += trackAccordionHtml('trackA', 'Track A — Splunk');
    html += trackAccordionHtml('trackB', 'Track B — Detection &amp; Cloud Security');

    if (!weeks.length) {
      return html + '<div class="empty-note" style="margin-top:16px">No weeks planned yet — start one with “Add week”.</div>';
    }

    html += '<details class="week-details"><summary>Week grid &amp; editing ('
      + weeks.length + ' week(s))</summary>';
    weeks.forEach(function (wk) {
      var isCurrent = wk.id === w.current_id;
      html += '<div class="week-card rise' + (isCurrent ? ' current' : '') + '" style="margin-top:12px">'
      + '<div class="week-head">'
      +   '<span class="week-title mono">' + esc('Week ' + wk.num) + ' · starts ' + esc(wk.start || DASH)
      +     (isCurrent ? '</span><span class="current-chip">this week</span>' : '</span>')
      +   '<span style="display:flex;gap:8px">'
      +     '<button class="btn ghost small" data-action="week-delete" data-id="' + esc(wk.id) + '" type="button">DELETE</button>'
      +   '</span>'
      + '</div>'
      + '<div class="week-focus">'
      +   '<div><label class="focus-label fa">Focus A</label>'
      +     '<input class="focus-input" id="fa-' + esc(wk.id) + '" value="' + esc(wk.focusA || '') + '" maxlength="120"></div>'
      +   '<div><label class="focus-label fb">Focus B</label>'
      +     '<input class="focus-input" id="fb-' + esc(wk.id) + '" value="' + esc(wk.focusB || '') + '" maxlength="120"></div>'
      + '</div>'
      + '<div style="margin-bottom:10px"><button class="btn ok small" data-action="week-save" data-id="' + esc(wk.id) + '" type="button">SAVE FOCUSES</button></div>';
      (wk.days || []).forEach(function (day, i) {
        html += '<div class="day-row" data-action="day-detail" data-wid="' + esc(wk.id) + '" data-di="' + i + '"'
        +       ' title="' + esc(day.note || 'open day detail') + '">'
        +   '<span class="day-name">' + esc(day.d || '') + '</span>'
        +   dayCellHtml('a', day.a)
        +   dayCellHtml('b', day.b)
        +   '<button class="day-done-box' + (day.done ? ' on' : '') + '" type="button"'
        +     ' data-action="week-toggle" data-wid="' + esc(wk.id) + '" data-date="' + esc(day.date) + '"'
        +     ' aria-checked="' + (day.done ? 'true' : 'false') + '" role="checkbox" aria-label="Day done">'
        +     (day.done ? '&#10003;' : '')
        +   '</button>'
        + '</div>';
      });
      html += '</div>';
    });
    html += '</details>';
    return html;
  }

  function dayCellHtml(kind, value) {
    return '<span class="day-cell ' + kind + (value ? '' : ' none') + '">'
         + (value ? esc(value) : 'nothing planned') + '</span>';
  }

  function openDayModal(weekId, dayIndex) {
    var wk = (S.weeks.weeks || []).find(function (x) { return x.id === weekId; });
    if (!wk) return;
    var day = (wk.days || [])[dayIndex];
    if (!day) return;
    openModal(
      '<div class="modal-title">' + esc(day.d) + ' ' + esc(day.date) + ' — Week ' + esc(wk.num) + '</div>'
      + '<div class="form-row"><label>Track A</label><div class="field" style="border-left:3px solid var(--signal)">' + (day.a ? esc(day.a) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</div></div>'
      + '<div class="form-row"><label>Track B</label><div class="field" style="border-left:3px solid var(--violet)">' + (day.b ? esc(day.b) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</div></div>'
      + (dayKindNote(day.kind) ? '<div class="sched-kind">' + esc(dayKindNote(day.kind)) + '</div>' : '')
      + chunkBarHtml(day.chunks)
      + chunkListHtml(day.chunks, true)
      + eveningHtml(day.evening, true)
      + '<div class="form-row"><label>Note</label><div>' + (day.note ? esc(day.note) : '<em style="color:var(--muted-dim)">no note</em>') + '</div></div>'
      + '<div class="form-actions">'
      +   '<button class="btn ghost" data-modal-action="close" type="button">CLOSE</button>'
      +   '<button class="btn ok" data-modal-action="day-toggle" data-wid="' + esc(weekId) + '" data-date="' + esc(day.date) + '" type="button">'
      +     (day.done ? 'MARK NOT DONE' : 'MARK DONE') + '</button>'
      + '</div>');
  }

  function openWeekAddModal() {
    openModal(
      '<div class="modal-title">Add a week</div>'
      + '<div class="form-row"><label for="mw-start">Start date</label><input type="date" class="field" id="mw-start"></div>'
      + '<div class="form-row"><label for="mw-fa">Focus A</label><input class="field" id="mw-fa" maxlength="120" placeholder="e.g. Splunk — scheduled searches"></div>'
      + '<div class="form-row"><label for="mw-fb">Focus B</label><input class="field" id="mw-fb" maxlength="120" placeholder="e.g. Cloud security — IAM basics"></div>'
      + '<div class="form-actions">'
      +   '<button class="btn ghost" data-modal-action="close" type="button">CANCEL</button>'
      +   '<button class="btn primary" data-modal-action="week-create" type="button">ADD WEEK</button>'
      + '</div>');
  }

  // ── loose items strip (legacy /plan endpoints, kept working) ────────
  function renderLooseItems() {
    var el = $('#plan-loose');
    var d = S.planLoose || {};
    var items = d.items || [];
    var formHtml = '<div class="card" style="margin-bottom:12px">'
    + '<div style="display:flex;gap:10px;flex-wrap:wrap">'
    +   '<input type="text" class="field" id="loose-title" placeholder="What (e.g. a certification)" maxlength="120" style="flex:2 1 200px">'
    +   '<input type="date" class="field" id="loose-date" style="flex:1 1 130px">'
    +   '<input type="text" class="field" id="loose-notes" placeholder="Notes (optional)" maxlength="200" style="flex:2 1 180px">'
    +   '<button class="btn primary small" data-action="loose-add" type="button">ADD</button>'
    + '</div></div>';
    if (!items.length) {
      el.innerHTML = formHtml
        + '<div class="empty-note">No loose items — anything that is not a topic or a week lives here.</div>';
      return;
    }
    var rows = '';
    items.forEach(function (it) {
      var id = it.item_id !== undefined ? it.item_id : it.id;
      rows += '<div class="note-row"' + (it.done ? ' style="opacity:0.55"' : '') + '>'
      + '<div><div class="note-title"' + (it.done ? ' style="text-decoration:line-through"' : '') + '>' + esc(it.title) + '</div>'
      + '<div class="note-meta">' + (it.target_date ? 'target ' + esc(it.target_date) : 'no target date')
      + (it.notes ? ' · ' + esc(it.notes) : '') + '</div></div>'
      + '<div class="row-actions">'
      +   '<button class="btn ok small" data-action="loose-done" data-id="' + esc(id) + '" type="button">' + (it.done ? 'UNDO' : 'DONE') + '</button>'
      +   '<button class="btn danger small" data-action="loose-remove" data-id="' + esc(id) + '" type="button">REMOVE</button>'
      + '</div></div>';
    });
    el.innerHTML = formHtml + '<div class="card">' + rows + '</div>';
  }

  // ════════════════════════════════════════════════════════════════
  //  CONSISTENCY HEATMAP (Today tab) - real history, no fabrication.
  //  Study merged into Plan on 2026-08-24 (ADR-100); this is the one
  //  piece of the old Study tab that still needed a home.
  // ════════════════════════════════════════════════════════════════
  function renderHeatmap(hm) {
    var grid = $('#today-heatmap');
    if (!grid) return;
    grid.innerHTML = '';
    var days = hm.days || [];
    if (!days.length) {
      grid.innerHTML = '<div class="empty-note" style="grid-column:1/-1;border:none;padding:0">No study history yet — finished blocks will fill this in.</div>';
      return;
    }
    var frag = document.createDocumentFragment();
    days.forEach(function (cell, i) {
      var div = document.createElement('div');
      var lvl = Math.max(0, Math.min(4, cell.level || 0));
      div.className = 'hm-cell' + (lvl ? ' l' + lvl : '');
      div.title = cell.date + ' · ' + (cell.minutes ? cell.minutes + ' min' : 'no session');
      div.style.animationDelay = REDUCE ? '0ms' : Math.min(1400, i * 5) + 'ms';
      frag.appendChild(div);
    });
    grid.appendChild(frag);
  }

  // ════════════════════════════════════════════════════════════════
  //  TAB 4 - RECALL (My cards - ADR-100 dropped the Leitner notes
  //  queue: every Knowledge_Base note sat in it as permanently "due",
  //  none ever reviewed even once. A real count that told you nothing
  //  is not better than no number - Rule 12's spirit, not just its
  //  letter.)
  // ════════════════════════════════════════════════════════════════
  async function loadRecall() {
    var el = $('#recall-body');
    skeleton(el, 4);
    var d;
    try { d = await getJson(API + '/recall-cards'); }
    catch (err) {
      el.innerHTML = '<div class="empty-note bad">Could not reach the recall API — ' + esc(err.message) + '</div>';
      return;
    }
    S.cards = d;
    renderRecall();
  }

  function renderRecall() {
    var el = $('#recall-body');
    if (!S.cards) { skeleton(el, 4); return; }
    el.innerHTML = myCardsHtml();
    if (S._enterNext) {
      S._enterNext = false;
      var first = el.firstElementChild;
      if (first && !REDUCE) { first.classList.remove('rise'); first.classList.add('flash-enter'); }
    }
  }

  // ── My cards ───────────────────────────────────────────────────────
  function myCardsHtml() {
    var c = S.cards;
    var due = c.due || [];
    if (!due.length) {
      return '<div class="empty-note good">Nothing due — ' + ((c.cards || []).length)
        + ' card(s) scheduled.</div>'
        + manageRowHtml();
    }
    S.reviewIndex = Math.min(S.reviewIndex, due.length - 1);
    return reviewFlowHtml(due) + manageRowHtml();
  }

  function reviewFlowHtml(due) {
    var i = S.reviewIndex;
    var card = due[i];
    if (!card) {
      return '<div class="empty-note good">Nothing due — ' + ((S.cards.cards || []).length) + ' card(s) scheduled.</div>';
    }
    var dots = '';
    for (var k = 0; k < due.length; k++) {
      dots += '<i class="' + (k < i ? 'past' : (k === i ? 'now' : '')) + '"></i>';
    }
    var parts = [
      ['The idea', card.elevator, false],
      ['Likely question', card.likely_q, false],
      ['Trap question', card.trap_q, false],
      ['From my work', card.example, false],
      ['Resume link', card.resume_link, true]
    ];
    var backParts = parts.map(function (p) {
      if (!p[1]) return '';
      var val = p[2]
        ? '<a href="' + esc(p[1]) + '" target="_blank" rel="noopener">' + esc(p[1]) + '</a>'
        : esc(p[1]);
      return '<div class="flash-part"><div class="flash-part-label">' + p[0] + '</div>'
        + '<div class="flash-part-value' + (p[2] ? ' link' : '') + '">' + val + '</div></div>';
    }).join('');

    return ''
    + '<section class="rise">'
    +   '<div class="review-dots">' + dots + '</div>'
    +   '<div class="flash-stage" id="flash-stage">'
    +     '<div class="flashcard' + (card._flipped ? ' flipped' : '') + '" id="flashcard" data-action="flip-card" tabindex="0" role="button"'
    +       ' aria-label="Flashcard for ' + esc(card.topic) + '. Click or press Space to flip.">'
    +       '<div class="flash-face front">'
    +         '<span class="track-chip ' + (card.track === 'B' ? 'b' : 'a') + '">' + (card.track === 'B' ? 'Track B' : 'Track A') + '</span>'
    +         (card.starter ? '<span class="starter-badge" style="margin-left:6px" title="Starter data traced to your own contract file - yours to delete">starter</span>' : '')
    +         '<div class="flash-topic" style="margin-top:10px">' + esc(card.topic) + '</div>'
    +         '<div class="flash-hint">Recall it out loud first — click or press Space to check.</div>'
    +       '</div>'
    +       '<div class="flash-face back">'
    +         backParts
    +         '<div class="flash-hint">Rate how it went below.</div>'
    +       '</div>'
    +     '</div>'
    +   '</div>'
    +   '<div class="rate-row">'
    +     rateBtn('again', 'Again', 0, !card._flipped)
    +     rateBtn('hard', 'Hard', 3, !card._flipped)
    +     rateBtn('good', 'Good', 4, !card._flipped)
    +     rateBtn('easy', 'Easy', 5, !card._flipped)
    +   '</div>'
    + '</section>';
  }

  function rateBtn(cls, label, q, disabled) {
    return '<button class="rate-btn ' + cls + '" type="button" data-action="rate" data-q="' + q + '"'
      + (disabled ? ' disabled' : '') + '>' + label + '<small>' + q + '</small></button>';
  }

  // A quiet manage row instead of an always-open library list (ADR-100
  // - the owner asked for the permanent card-library block gone). The
  // list itself still exists, just one click away in a modal.
  function manageRowHtml() {
    var c = S.cards;
    var cards = c.cards || [];
    return '<div class="recall-manage-row">'
    +   '<span class="card-sub">' + cards.length + ' card(s)'
    +     ((c.resume_ready_count || 0) ? ', ' + c.resume_ready_count + ' resume-ready' : '') + '</span>'
    +   '<div style="display:flex;gap:8px">'
    +     '<button class="btn ghost small" data-action="cards-manage" type="button">MANAGE CARDS</button>'
    +     '<button class="btn primary small" data-action="card-add" type="button">+ ADD CARD</button>'
    +   '</div>'
    + '</div>';
  }

  function manageListHtml() {
    var cards = (S.cards || {}).cards || [];
    if (!cards.length) {
      return '<div class="empty-note">No cards yet — add one. A card is a topic you want to be able to recall out loud.</div>';
    }
    var rows = cards.map(function (cd) {
      return '<div class="lib-row">'
      + '<span class="lib-topic">' + esc(cd.topic) + '</span>'
      + '<span class="track-chip ' + (cd.track === 'B' ? 'b' : 'a') + '">' + (cd.track === 'B' ? 'Track B' : 'Track A') + '</span>'
      + (cd.starter ? '<span class="starter-badge" title="Starter data traced to your own contract file - yours to delete">starter</span>' : '')
      + '<span class="lib-stats">ease ' + esc(cd.ease !== undefined && cd.ease !== null ? cd.ease : DASH)
      +   ' · reps ' + esc(cd.reps !== undefined && cd.reps !== null ? cd.reps : DASH)
      +   ' · next ' + esc(cd.next_due || DASH) + '</span>'
      + (cd.resume_ready ? '<span class="resume-badge" title="Rated Good or Easy twice in separate reviews">resume-ready</span>' : '')
      + '<span class="row-actions">'
      +   '<button class="btn ghost small" data-action="card-edit" data-id="' + esc(cd.id) + '" type="button">EDIT</button>'
      +   '<button class="btn danger small" data-action="card-delete" data-id="' + esc(cd.id) + '" type="button">DELETE</button>'
      + '</span>'
      + '</div>';
    }).join('');
    return '<div class="card">' + rows + '</div>';
  }

  function cardFormHtml(card) {
    card = card || {};
    function f(id, label, val, ph) {
      return '<div class="form-row"><label for="' + id + '">' + label + '</label>'
        + '<textarea class="field" id="' + id + '" rows="2" maxlength="500" placeholder="' + (ph || '') + '">' + esc(val || '') + '</textarea></div>';
    }
    return '<div class="modal-title">' + (card.id ? 'Edit card' : 'Add a card') + '</div>'
    + '<div class="form-row"><label for="cf-topic">Topic</label>'
    +   '<input class="field" id="cf-topic" maxlength="120" value="' + esc(card.topic || '') + '"></div>'
    + '<div class="form-row"><label for="cf-track">Track</label>'
    +   '<select class="field" id="cf-track"><option value="A"' + (card.track === 'B' ? '' : ' selected') + '>Track A — Splunk</option>'
    +   '<option value="B"' + (card.track === 'B' ? ' selected' : '') + '>Track B — Detection &amp; Cloud Security</option></select></div>'
    + f('cf-elevator', 'The idea', card.elevator, 'one plain sentence')
    + f('cf-likely', 'Likely question', card.likely_q)
    + f('cf-trap', 'Trap question', card.trap_q, 'the question that catches people out')
    + f('cf-example', 'From my work', card.example, 'where this showed up in the day job')
    + f('cf-resume', 'Resume link', card.resume_link, 'https://…')
    + '<div class="form-actions">'
    +   '<button class="btn ghost" data-modal-action="close" type="button">CANCEL</button>'
    +   '<button class="btn primary" data-modal-action="' + (card.id ? 'card-save-edit' : 'card-save-new') + '"'
    +     ' data-id="' + esc(card.id || '') + '" type="button">' + (card.id ? 'SAVE' : 'ADD CARD') + '</button>'
    + '</div>';
  }

  // ════════════════════════════════════════════════════════════════
  //  THE READER - interactive markdown study window
  // ════════════════════════════════════════════════════════════════
  var R = { noteFile: '', title: '', markdown: '', annotations: [],
            module: null,
            // true only when THIS reader is the one that started the
            // currently running session (via startLearningOnTopic) - so
            // closing it is what stops the clock. Opening a note purely
            // to read it (NOTES button) never sets this.
            autoSession: false };

  // Start a session for a Plan topic and open its module straight away
  // (ADR-100) - this is now the one way a study block begins. If a
  // session is already running (for any topic), a second START LEARNING
  // click just opens the note; it never silently ends someone else's
  // running block.
  function startLearningOnTopic(topic, noteFile) {
    if (!noteFile) return;
    if (liveRunningSession()) { openReader(noteFile); return; }
    post('/study/start', { topic: topic }).then(function (d) {
      S.runningSession = d.running_session || null;
      R.autoSession = true;
      loadTodayIfNeeded();
      openReader(noteFile);
    }).catch(function (err) { toast('could not start: ' + err.message, 'bad'); });
  }

  // A small, honest markdown renderer: no CDN, no libraries (INKY is
  // local-only). Everything is escaped FIRST, so a note can never inject
  // markup into the page; only the constructs below ever become tags.
  function mdToHtml(src) {
    var lines = (src || '').replace(/\r\n/g, '\n').split('\n');
    var out = [], para = [], list = null, code = null, quote = [];

    function flushPara() {
      if (para.length) { out.push('<p>' + para.map(inline).join('<br>') + '</p>'); para = []; }
    }
    function flushList() {
      if (list) { out.push('</' + list + '>'); list = null; }
    }
    function flushQuote() {
      if (quote.length) { out.push('<blockquote>' + quote.map(inline).join('<br>') + '</blockquote>'); quote = []; }
    }
    function flushAll() { flushPara(); flushList(); flushQuote(); }

    function inline(s) {
      return s
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
        .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,
                 '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (code !== null) {
        if (/^```/.test(line)) { out.push('</code></pre>'); code = null; }
        else out.push(esc(line));
        continue;
      }
      if (/^```/.test(line)) { flushAll(); out.push('<pre><code>'); code = ''; continue; }
      var t = esc(line);
      var h = t.match(/^(#{1,6})\s+(.*)$/);
      if (h) { flushAll(); out.push('<h' + h[1].length + '>' + inline(h[2]) + '</h' + h[1].length + '>'); continue; }
      if (/^\s*(-{3,}|\*{3,})\s*$/.test(t)) { flushAll(); out.push('<hr>'); continue; }
      if (/^&gt;\s?/.test(t)) { flushPara(); flushList(); quote.push(t.replace(/^&gt;\s?/, '')); continue; }
      var ul = t.match(/^\s*[-*]\s+(.*)$/);
      var ol = t.match(/^\s*\d+[.)]\s+(.*)$/);
      if (ul) { flushPara(); flushQuote(); if (list !== 'ul') { flushList(); out.push('<ul>'); list = 'ul'; } out.push('<li>' + inline(ul[1]) + '</li>'); continue; }
      if (ol) { flushPara(); flushQuote(); if (list !== 'ol') { flushList(); out.push('<ol>'); list = 'ol'; } out.push('<li>' + inline(ol[1]) + '</li>'); continue; }
      if (!t.trim()) { flushAll(); continue; }
      flushList(); flushQuote(); para.push(t);
    }
    if (code !== null) out.push('</code></pre>');
    flushAll();
    return out.join('\n');
  }

  function openReader(noteFile) {
    if (!noteFile) return;
    // The module probe rides along with the note fetch - but only when
    // the note's own front matter says it is one. An ordinary note never
    // asks, so reading one stays exactly the quiet call it always was.
    var noteJob = getJson(API + '/notes/file?name=' + encodeURIComponent(noteFile));
    var moduleJob = noteJob.then(function (d) {
      if ((d.type || '') !== 'study-module') return null;
      return getJson(API + '/modules/one?name=' + encodeURIComponent(noteFile))
        .then(function (m) { return m && m.ok ? m : null; })
        .catch(function () { return null; });
    });
    Promise.all([noteJob, moduleJob])
      .then(function (results) {
        var d = results[0];
        R.noteFile = d.note_file;
        R.title = d.title || d.note_file;
        R.markdown = d.markdown || '';
        R.annotations = d.annotations || [];
        R.module = results[1];
        $('#reader-title').textContent = R.title;
        var bits = [];
        if (d.added_at) bits.push('added ' + d.added_at.slice(0, 10));
        if (d.sources && d.sources.length) bits.push(d.sources.length + ' source(s)');
        bits.push(R.annotations.length + ' note(s) here');
        $('#reader-meta').textContent = bits.join(' · ');
        repaintReader();
        var scrim = $('#reader-scrim');
        scrim.hidden = false;
        requestAnimationFrame(function () { scrim.classList.add('open'); });
        syncReaderSession();
      })
      .catch(function (err) { toast('could not open the note: ' + err.message, 'bad'); });
  }

  function closeReader() {
    var scrim = $('#reader-scrim');
    scrim.classList.remove('open');
    setTimeout(function () { scrim.hidden = true; }, REDUCE ? 0 : 200);
    hideReaderMenus();
    // this reader started the session that's running - closing it is
    // the automatic "I'm done" signal (ADR-100), no separate stop click
    // required. An explicit STOP SESSION click already cleared the flag,
    // so this never double-stops.
    if (R.autoSession) {
      R.autoSession = false;
      stopRunningSession('', '');
    }
  }

  function repaintReader() {
    $('#reader-body').innerHTML = mdToHtml(R.markdown);
    paintModuleRoom(true);
    paintAnnotations();
  }

  // ── THE ROOM - what the reader becomes when the note is a module ──
  // Everything the reader already does (highlighting, right-click
  // notes, the session clock, the notes field) is untouched; a module
  // only wears extra clothes: a task panel up top with a live ring,
  // a mark-done control at the end of each task, and an answer box
  // under every question. A non-module note gets none of it.

  function paintModuleRoom(initial) {
    var panel = $('#reader-module');
    var m = R.module;
    if (!panel) return;
    if (!m) { panel.hidden = true; return; }
    if (m.malformed) {
      panel.hidden = false;
      panel.innerHTML = '<div class="room-malformed">This note says '
        + '<code>type: study-module</code> but has no <code>## Task 1</code> '
        + 'heading, so it parses as malformed - nothing to work through yet.</div>';
      return;
    }
    panel.hidden = false;
    buildModulePanel();
    if (initial) decorateModuleBody(m);   // fresh body needs the accordion built
    syncDoneRows(m);
  }

  function buildModulePanel() {
    var m = R.module;
    var done = m.tasks.filter(function (t) { return t.done; }).length;
    var total = m.tasks.length;
    var pct = total ? Math.round(100 * done / total) : 0;
    $('#reader-module').innerHTML = ''
      + '<div class="room-head">'
      +   miniRingHtml(pct, 'var(--signal)')
      +   '<span class="room-count mono">' + esc(String(done)) + ' of '
      +     esc(String(total)) + ' tasks</span>'
      + '</div>';
  }

  // The tick/label states move without re-rendering the body - a full
  // repaint would wipe whatever the reader just typed into an answer
  // box, which is exactly the kind of lie a page must not tell.
  function syncDoneRows(m) {
    var byId = {};
    m.tasks.forEach(function (t) { byId[t.id] = t; });
    $all('#reader-body .task-acc').forEach(function (det) {
      var t = byId[det.dataset.task];
      if (!t) return;
      det.classList.toggle('done', !!t.done);
      var tick = $('.task-acc-tick', det);
      if (tick) tick.innerHTML = t.done ? '&#10003;' : esc(String(t.number));
      var btn = $('.room-done-row button', det);
      if (btn) {
        btn.className = 'btn ' + (t.done ? 'ghost' : 'primary') + ' small';
        btn.textContent = t.done ? 'MARK NOT DONE' : 'MARK DONE';
      }
    });
  }

  // Closing a just-finished task and opening the next one is a small,
  // welcome automation (ADR-100: "auto update it... inside a dropdown")
  // - but only when nothing else is already open, so it never yanks a
  // section shut out from under someone reading it.
  function autoAdvanceAccordion(m, justToggledId) {
    var det = document.querySelector('#reader-body .task-acc[data-task="' + cssId(justToggledId) + '"]');
    var t = m.tasks.filter(function (x) { return x.id === justToggledId; })[0];
    if (!det || !t || !t.done) return;
    det.open = false;
    if (document.querySelector('#reader-body .task-acc[open]')) return;
    var next = m.tasks.filter(function (x) { return !x.done; })[0];
    if (!next) return;
    var nextDet = document.querySelector('#reader-body .task-acc[data-task="' + cssId(next.id) + '"]');
    if (nextDet) nextDet.open = true;
  }

  // Walk the rendered markdown once: wrap each "## Task N" heading and
  // everything under it (up to the next task heading) into one
  // <details class="task-acc"> - a collapsed row per task instead of
  // every task's full content and questions stacked on screen together
  // (the owner's own complaint: "taking a lot of space"). Answer boxes
  // go in first since they live inside a question <li>, unaffected by
  // which task wrapper it later ends up inside.
  function decorateModuleBody(m) {
    var body = $('#reader-body');
    var byNumber = {};
    m.tasks.forEach(function (t) { byNumber[t.number] = t; });
    var kids = Array.prototype.slice.call(body.children);
    kids.forEach(function (el) { if (el.tagName === 'LI') maybeAddAnswerBox(el); });

    var segments = [];   // {number, start, end} indices into `kids`
    var current = null;
    kids.forEach(function (el, i) {
      var hit = el.tagName === 'H2'
        && (el.textContent || '').match(/^Task\s+(\d+)\b/);
      if (hit && byNumber[Number(hit[1])]) {
        current = Number(hit[1]);
        segments.push({ number: current, start: i, end: i });
      } else if (current !== null && byNumber[current]) {
        segments[segments.length - 1].end = i;
      }
    });

    // the first not-done task opens by default; if every task is done,
    // the first task opens - never nothing at all.
    var defaultOpen = null;
    for (var n = 1; n <= m.tasks.length && defaultOpen === null; n++) {
      if (byNumber[n] && !byNumber[n].done) defaultOpen = n;
    }
    if (defaultOpen === null && m.tasks.length) defaultOpen = m.tasks[0].number;

    // build in reverse so earlier indexes into `kids` stay valid as
    // later segments' elements are moved out of the body.
    segments.slice().reverse().forEach(function (seg) {
      var t = byNumber[seg.number];
      var headEl = kids[seg.start];

      var details = document.createElement('details');
      details.className = 'task-acc' + (t.done ? ' done' : '');
      details.dataset.task = t.id;
      details.open = seg.number === defaultOpen;

      var summary = document.createElement('summary');
      summary.className = 'task-acc-head';
      summary.innerHTML = '<span class="task-acc-tick">'
        + (t.done ? '&#10003;' : esc(String(t.number))) + '</span>'
        + '<span class="task-acc-title">' + esc(headEl.textContent) + '</span>';
      details.appendChild(summary);

      var content = document.createElement('div');
      content.className = 'task-acc-body';
      for (var i = seg.start + 1; i <= seg.end; i++) content.appendChild(kids[i]);
      content.insertAdjacentHTML('beforeend', doneRowHtml(t));
      details.appendChild(content);

      headEl.replaceWith(details);
    });
  }

  function doneRowHtml(t) {
    return '<div class="room-done-row">'
      + '<button class="btn ' + (t.done ? 'ghost' : 'primary') + ' small"'
      +     ' data-action="room-task-toggle" data-task="' + esc(t.id) + '" type="button">'
      +     (t.done ? 'MARK NOT DONE' : 'MARK DONE')
      + '</button></div>';
  }

  function maybeAddAnswerBox(li) {
    var hit = (li.textContent || '').match(/^\s*(Q\d+\.\d+)\b/);
    if (!hit) return;
    var qid = hit[1];
    var box = document.createElement('div');
    box.className = 'answer-box';
    box.dataset.q = qid;
    box.innerHTML = ''
      + '<input type="text" class="field answer-input" maxlength="200"'
      +     ' placeholder="your answer to ' + esc(qid) + '"'
      +     ' aria-label="Your answer to ' + esc(qid) + '">'
      + '<button class="btn primary small" data-action="room-answer-check" type="button">CHECK</button>'
      + '<span class="answer-result" aria-live="polite"></span>';
    li.appendChild(box);
  }

  // Wrap every annotated passage in <mark class="note-mark">. Runs on a
  // freshly rendered body, walking text nodes; a quote that spans two
  // nodes (rare - it means the renderer split it) simply does not
  // highlight rather than highlighting the wrong words.
  function paintAnnotations() {
    var body = $('#reader-body');
    if (!R.annotations.length) return;
    R.annotations.forEach(function (a) {
      var walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null, false);
      var seen = 0;
      var node;
      while ((node = walker.nextNode())) {
        var text = node.nodeValue;
        var pos = 0, idx;
        while ((idx = text.indexOf(a.quote, pos)) !== -1) {
          if (seen === (a.occurrence || 0)) {
            var range = document.createRange();
            range.setStart(node, idx);
            range.setEnd(node, idx + a.quote.length);
            var mark = document.createElement('mark');
            mark.className = 'note-mark';
            mark.dataset.annoId = a.id;
            mark.title = 'click to read your note';
            try { range.surroundContents(mark); } catch (e) { /* cross-node */ }
            return;
          }
          seen += 1;
          pos = idx + a.quote.length;
        }
      }
    });
  }

  function syncReaderSession() {
    var rs = liveRunningSession();
    var box = $('#reader-session');
    if (rs) {
      elapsedBase.seconds = (rs.elapsed_minutes || 0) * 60;
      elapsedBase.at = Date.now();
      startElapsedTicker();
      box.hidden = false;
    } else {
      box.hidden = true;
    }
  }

  function hideReaderMenus() {
    $('#reader-menu').hidden = true;
    $('#anno-editor').hidden = true;
    $('#anno-viewer').hidden = true;
  }

  // ── selection -> right-click -> add note ────────────────────────────
  var pendingSelection = '';

  $('#reader-body').addEventListener('mouseup', function () {
    var sel = window.getSelection();
    pendingSelection = sel ? String(sel).trim() : '';
  });

  $('#reader-body').addEventListener('contextmenu', function (e) {
    var mark = e.target.closest('mark.note-mark');
    e.preventDefault();
    $('#anno-editor').hidden = true;
    $('#anno-viewer').hidden = true;
    var menu = $('#reader-menu');
    if (mark) {
      var anno = R.annotations.find(function (x) { return x.id === mark.dataset.annoId; });
      if (anno) {
        menu.innerHTML = '';
        var viewBtn = document.createElement('button');
        viewBtn.className = 'reader-menu-item';
        viewBtn.type = 'button';
        viewBtn.textContent = 'Read your note';
        viewBtn.onclick = function () { menu.hidden = true; showAnnoViewer(anno, e.clientX, e.clientY); };
        var delBtn = document.createElement('button');
        delBtn.className = 'reader-menu-item danger';
        delBtn.type = 'button';
        delBtn.textContent = 'Delete note';
        delBtn.onclick = function () { menu.hidden = true; deleteAnnotation(anno.id); };
        menu.appendChild(viewBtn);
        menu.appendChild(delBtn);
        placeAt(menu, e.clientX, e.clientY, 190, 90);
        menu.hidden = false;
        return;
      }
    }
    if (!pendingSelection || pendingSelection.length < 2) { menu.hidden = true; return; }
    menu.innerHTML = '';
    var btn = document.createElement('button');
    btn.className = 'reader-menu-item';
    btn.type = 'button';
    btn.textContent = 'Add note on "' +
      (pendingSelection.length > 28 ? pendingSelection.slice(0, 28) + '…' : pendingSelection) + '"';
    btn.onclick = function () { menu.hidden = true; openAnnoEditor(e.clientX, e.clientY); };
    menu.appendChild(btn);
    placeAt(menu, e.clientX, e.clientY, 250, 70);
    menu.hidden = false;
  });

  function placeAt(el, x, y, w, h) {
    el.style.left = Math.max(8, Math.min(x, window.innerWidth - w - 10)) + 'px';
    el.style.top = Math.max(8, Math.min(y, window.innerHeight - h - 10)) + 'px';
  }

  function openAnnoEditor(x, y) {
    var ed = $('#anno-editor');
    $('#anno-quote').textContent = '"' + pendingSelection + '"';
    $('#anno-text').value = '';
    placeAt(ed, x - 40, y + 18, 320, 190);
    ed.hidden = false;
    $('#anno-text').focus();
  }

  function saveAnnotation() {
    var noteText = $('#anno-text').value.trim();
    if (!noteText) { toast('the note needs some words', 'bad'); return; }
    // which copy of this phrase was selected? count identical matches
    // earlier in the same text node as the selection start.
    var occurrence = 0;
    try {
      var sel = window.getSelection();
      if (sel && sel.rangeCount) {
        var node = sel.getRangeAt(0).startContainer;
        if (node.nodeType === Node.TEXT_NODE) {
          occurrence = node.nodeValue.slice(0, sel.getRangeAt(0).startOffset)
            .split(pendingSelection).length - 1;
        }
      }
    } catch (e) { /* default 0 */ }
    post('/annotations', {
      note_file: R.noteFile, quote: pendingSelection,
      note: noteText, occurrence: occurrence
    }).then(function (d) {
      R.annotations.push(d.annotation);
      pendingSelection = '';
      window.getSelection().removeAllRanges();
      repaintReader();
      hideReaderMenus();
      toast('note attached', 'ok');
    }).catch(function (err) { toast('could not save: ' + err.message, 'bad'); });
  }

  function deleteAnnotation(id) {
    post('/annotations/delete', { id: id }).then(function () {
      R.annotations = R.annotations.filter(function (x) { return x.id !== id; });
      repaintReader();
      toast('annotation deleted', 'ok');
    }).catch(function (err) { toast('could not delete: ' + err.message, 'bad'); });
  }

  function showAnnoViewer(anno, x, y) {
    $('#anno-view-quote').textContent = '"' + anno.quote + '"';
    $('#anno-view-text').textContent = anno.note;
    $('#anno-viewer').dataset.annoId = anno.id;
    placeAt($('#anno-viewer'), x - 60, y + 14, 340, 200);
    $('#anno-viewer').hidden = false;
  }

  // clicking an existing highlight opens its note
  $('#reader-body').addEventListener('click', function (e) {
    var mark = e.target.closest('mark.note-mark');
    if (!mark) return;
    var anno = R.annotations.find(function (x) { return x.id === mark.dataset.annoId; });
    if (anno) showAnnoViewer(anno, e.pageX, e.pageY);
  });

  // click anywhere outside the popovers dismisses them
  document.addEventListener('mousedown', function (e) {
    if (e.target.closest('#reader-menu,#anno-editor,#anno-viewer')) return;
    $('#reader-menu').hidden = true;
    if (!$('#anno-editor').hidden) $('#anno-editor').hidden = true;
    if (!$('#anno-viewer').hidden) $('#anno-viewer').hidden = true;
  });

  $('#reader-scrim').addEventListener('mousedown', function (e) {
    if (e.target === e.currentTarget) closeReader();
  });
  $('#explorer-scrim').addEventListener('mousedown', function (e) {
    if (e.target === e.currentTarget) explorerClose();
  });

  // Today's assigned topics, read straight off the day's own plan.
  // Kept for the notes explorer's "today" flag below - the old Study
  // tab's per-block START buttons it used to feed are gone (ADR-100),
  // learning now starts from a Plan topic's START LEARNING button.
  function todaysAssignedItems() {
    var sch = ((S.today || {}).schedule) || {};
    var out = [];
    var chunks = sch.chunks || [];
    if (chunks.length) {
      chunks.forEach(function (c) {
        if (c.title) out.push({ track: 'A', topic: c.title, clock: c.clock, kind: c.kind });
      });
      if (sch.evening && sch.evening.title) {
        out.push({ track: 'B', topic: sch.evening.title });
      }
      return out;
    }
    ['track_a', 'track_b'].forEach(function (key, idx) {
      var raw = (sch[key] || '').trim();
      if (!raw) return;
      raw.split(',').forEach(function (part) {
        var topic = part.trim();
        if (topic) out.push({ track: idx === 0 ? 'A' : 'B', topic: topic });
      });
    });
    return out;
  }

  // ── notes explorer drawer ───────────────────────────────────────────
  function explorerOpen() {
    getJson(API + '/notes').then(function (d) {
      S.notesList = d.notes || [];
      S.notesCount = d.total || 0;
      $('#explorer-count').textContent = S.notesCount + ' notes in the knowledge base';
      var todayTopics = todaysAssignedItems().map(function (x) { return x.topic; });
      S.notesTodayMatches = todayTopics
        .map(function (t) { return noteMatchClient(t, S.notesList); })
        .filter(Boolean);
      renderExplorerList('');
      var scrim = $('#explorer-scrim');
      scrim.hidden = false;
      requestAnimationFrame(function () { scrim.classList.add('open'); });
    }).catch(function (err) { toast('could not load notes: ' + err.message, 'bad'); });
  }

  function explorerClose() {
    var s = $('#explorer-scrim');
    s.classList.remove('open');
    setTimeout(function () { s.hidden = true; }, REDUCE ? 0 : 220);
  }

  // The browser-side half of the matcher: same token idea as the
  // server's scorer, used only to flag which listed notes look relevant
  // to today's plan. One shared word is enough to earn a "today" flag -
  // it is a hint, never a claim.
  function noteMatchClient(topic, notes) {
    var STOP = ['a','an','and','are','as','at','by','for','from','in','into',
      'is','it','of','on','or','that','the','to','with','what','how'];
    var tok = function (s) {
      return (s || '').toLowerCase().match(/[a-z0-9]+/g) || [];
    };
    var want = tok(topic).filter(function (w) { return STOP.indexOf(w) === -1; });
    if (!want.length) return null;
    var best = null, bestHits = 0;
    notes.forEach(function (n) {
      var hay = tok(n.title + ' ' + n.note_file.replace(/_/g, ' ').replace('.md', ''));
      var hits = want.filter(function (w) { return hay.indexOf(w) !== -1; }).length;
      if (hits > bestHits) { bestHits = hits; best = n; }
    });
    return bestHits >= 1 ? best : null;
  }

  function renderExplorerList(filterText) {
    var el = $('#explorer-list');
    var notes = (S.notesList || []).slice()
      .sort(function (a, b) { return a.title.localeCompare(b.title); });
    var q = (filterText || '').trim().toLowerCase();
    if (q) {
      notes = notes.filter(function (n) {
        return (n.title + ' ' + n.note_file).toLowerCase().indexOf(q) !== -1;
      });
    }
    if (!notes.length) {
      el.innerHTML = '<div class="empty-note">No notes match.</div>';
      return;
    }
    var matchedFiles = {};
    (S.notesTodayMatches || []).forEach(function (n) { matchedFiles[n.note_file] = true; });
    var groups = {};
    notes.forEach(function (n) {
      var letter = (n.title[0] || '#').toUpperCase();
      if (!/[A-Z]/.test(letter)) letter = '#';
      (groups[letter] = groups[letter] || []).push(n);
    });
    var html = '';
    Object.keys(groups).sort().forEach(function (letter) {
      html += '<div class="explorer-letter">' + letter + '</div>';
      groups[letter].forEach(function (n) {
        html += '<button class="explorer-item' + (matchedFiles[n.note_file] ? ' today' : '')
        + '" data-action="open-note" data-file="' + esc(n.note_file) + '" type="button">'
        + '<span class="explorer-item-title">' + esc(n.title) + '</span>'
        + (matchedFiles[n.note_file] ? '<span class="explorer-flag">today</span>' : '')
        + '</button>';
      });
    });
    el.innerHTML = html;
  }

  $('#explorer-search').addEventListener('input', function () {
    renderExplorerList(this.value);
  });

  // ── PLAN > This Week: track accordions with Done / Pending ─────────
  function accordionGroupHtml(g) {
    var topics = g.topics || [];
    var done = topics.filter(function (x) { return x.status === 'done'; });
    var pending = topics.filter(function (x) { return x.status !== 'done'; });
    var gid = 'acc-' + g.group.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    return ''
    + '<div class="acc-group rise">'
    +   '<button class="acc-head" data-action="accordion-toggle" data-target="' + esc(gid) + '"'
    +     ' aria-expanded="false" type="button">'
    +     '<svg class="acc-arrow" viewBox="0 0 16 16" aria-hidden="true">'
    +       '<path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2"'
    +         ' stroke-linecap="round" stroke-linejoin="round"/></svg>'
    +     '<span class="acc-name">' + esc(g.group) + '</span>'
    +     '<span class="acc-count mono">' + done.length + '/' + topics.length + '</span>'
    +   '</button>'
    +   '<div class="acc-panel" id="' + esc(gid) + '">'
    +     '<div class="acc-sub done-block">'
    +       '<div class="acc-sub-title ok">&#10003; Done</div>'
    +       (done.length ? done.map(topicRowHtml).join('')
         : '<div class="acc-empty">nothing finished here yet</div>')
    +     '</div>'
    +     '<div class="acc-sub">'
    +       '<div class="acc-sub-title">&#9633; Pending</div>'
    +       (pending.length ? pending.map(topicRowHtml).join('')
         : '<div class="acc-empty">everything here is finished</div>')
    +     '</div>'
    +   '</div>'
    + '</div>';
  }

  function trackAccordionHtml(trackKey, title) {
    var t = (S.topics || {})[trackKey];
    if (!t) return '';
    var prog = t.progress || { done: 0, total: 0, pct: 0 };
    var cls = trackKey === 'trackA' ? 'track-a' : 'track-b';
    var color = trackKey === 'trackA' ? 'var(--signal)' : 'var(--violet)';
    var focus = trackKey === 'trackA'
      ? (S.weeks || {}).current_focus_a : (S.weeks || {}).current_focus_b;
    var html = '<section class="track-section ' + cls + '">'
    + '<div class="track-header">'
    +   miniRingHtml(prog.pct || 0, color)
    +   '<div><div class="track-title">' + title + '</div>'
    +     '<div class="card-sub mono">' + (prog.done || 0) + ' of ' + (prog.total || 0) + ' done'
    +       (focus ? ' · this week: ' + esc(focus) : '') + '</div></div>'
    + '</div>';
    var groups = t.groups || [];
    if (!groups.length) {
      html += '<div class="empty-note">No topics recorded for this track yet.</div></section>';
      return html;
    }
    groups.forEach(function (g) { html += accordionGroupHtml(g); });
    return html + '</section>';
  }

  // ════════════════════════════════════════════════════════════════
  //  EVENT DELEGATION - one listener routes every [data-action]
  // ════════════════════════════════════════════════════════════════
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-action]');
    if (!el || el.disabled) return;
    var act = el.dataset.action;
    var handler = ACTIONS[act];
    if (handler) handler(el, e);
  });

  document.addEventListener('keydown', function (e) {
    var el = e.target.closest('[data-action]');
    if (el && (e.key === 'Enter' || e.key === ' ') && el.dataset.action === 'checklist') {
      e.preventDefault(); ACTIONS.checklist(el); return;
    }
    if (el && e.key === 'Enter' && el.dataset.action === 'go-recall') { ACTIONS['go-recall'](el); return; }
    keyboardShortcuts(e);
  });

  function keyboardShortcuts(e) {
    if (S.tab !== 'recall') return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    var due = ((S.cards || {}).due || []);
    var card = due[S.reviewIndex];
    if (!card) return;
    if (e.key === ' ') {
      e.preventDefault();
      ACTIONS['flip-card']();
      return;
    }
    var qByKey = { '1': 0, '2': 3, '3': 4, '4': 5 };
    if (card._flipped && e.key in qByKey) {
      ACTIONS.rate({ dataset: { q: String(qByKey[e.key]) } });
    }
  }

  var ACTIONS = {

    'go-recall': function () { goToTab('recall'); },

    // ── TODAY: schedule target + notes explorer ──
    // Today's card shows the shape of the day; this opens the whole
    // thing, bullets and all, without needing the Plan tab loaded.
    'open-today-plan': function () {
      var sch = ((S.today || {}).schedule) || {};
      openModal(
        '<div class="modal-title">' + esc(sch.day_name || '') + ' ' + esc(sch.date || '') + ' \u2014 the full day</div>'
        + '<div class="form-row"><label>Track A</label><div class="field" style="border-left:3px solid var(--signal)">'
        +   (sch.track_a ? esc(sch.track_a) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</div></div>'
        + '<div class="form-row"><label>Track B</label><div class="field" style="border-left:3px solid var(--violet)">'
        +   (sch.track_b ? esc(sch.track_b) : '<em style="color:var(--muted-dim)">nothing planned</em>') + '</div></div>'
        + (dayKindNote(sch.kind) ? '<div class="sched-kind">' + esc(dayKindNote(sch.kind)) + '</div>' : '')
        + chunkBarHtml(sch.chunks)
        + chunkListHtml(sch.chunks, true)
        + eveningHtml(sch.evening, true)
        + (sch.note ? '<div class="form-row"><label>Note</label><div>' + esc(sch.note) + '</div></div>' : '')
        + '<div class="form-actions">'
        +   '<button class="btn ghost" data-modal-action="close" type="button">CLOSE</button>'
        + '</div>');
    },
    'schedule-target-save': async function () {
      var input = $('#sched-target');
      var raw = input ? input.value.trim() : '';
      var minutes = raw === '' ? null : Number(raw);
      try {
        await post('/schedule/target', { date: ((S.today || {}).schedule || {}).date, minutes: minutes });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      toast(raw === '' ? 'target cleared' : minutes + ' min allocated today', 'ok');
      loadToday();
    },
    'open-notes-explorer': function () { explorerOpen(); },
    'explorer-close': function () { explorerClose(); },
    'open-note': function (el) {
      explorerClose();
      openReader(el.dataset.file);
    },

    // ── PLAN: a topic's START LEARNING / NOTES buttons (ADR-100) ──
    'start-learning': function (el) {
      startLearningOnTopic(el.dataset.topic, el.dataset.file);
    },
    'open-notes-for-topic': function (el) {
      openReader(el.dataset.file);
    },
    'reader-close': function () { closeReader(); },
    'reader-stop': function () {
      var notes = $('#reader-stop-notes') ? $('#reader-stop-notes').value.trim() : '';
      R.autoSession = false;
      stopRunningSession(notes, '').then(function () {
        closeReader();
        syncReaderSession();
      });
    },
    'anno-save': saveAnnotation,
    'anno-cancel': function () { $('#anno-editor').hidden = true; },
    'anno-hide': function () { $('#anno-viewer').hidden = true; },
    'anno-delete': function (el) {
      var id = el.closest('#anno-viewer').dataset.annoId;
      if (id) deleteAnnotation(id);
      $('#anno-viewer').hidden = true;
    },

    // ── THE ROOM: tasks and answers inside the module reader ──
    'room-task-toggle': async function (el) {
      var taskId = el.dataset.task;
      try {
        await post('/modules/task', { name: R.noteFile, task_id: taskId });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      // re-read, never assume: the ring and rows follow what storage says
      try {
        R.module = await getJson(API + '/modules/one?name=' + encodeURIComponent(R.noteFile));
      } catch (err) { /* keep showing what we had */ }
      paintModuleRoom(false);
      autoAdvanceAccordion(R.module, taskId);
    },
    'room-answer-check': async function (el) {
      var box = el.closest('.answer-box');
      if (!box) return;
      var input = $('.answer-input', box);
      var out = $('.answer-result', box);
      var typed = input ? input.value.trim() : '';
      if (!typed) { toast('type an answer first', 'bad'); return; }
      var d;
      try {
        d = await post('/modules/answer', {
          name: R.noteFile, question_id: box.dataset.q, typed: typed
        });
      } catch (err) { toast('could not check: ' + err.message, 'bad'); return; }
      out.className = 'answer-result';
      out.innerHTML = '';
      if (!d.has_key) {
        out.textContent = 'no answer key for this question';
        return;
      }
      if (d.correct) {
        out.innerHTML = '<span class="answer-verdict good">&#10003; correct</span>'
          + (d.why ? '<span class="answer-why">' + esc(d.why) + '</span>' : '');
        return;
      }
      // wrong: the cross and nothing else - no hints, no partial reveals
      out.innerHTML = '<span class="answer-verdict bad">&#10007;</span>';
    },

    // ── PLAN: track accordions ──
    'accordion-toggle': function (el) {
      var panel = document.getElementById(el.dataset.target);
      if (!panel) return;
      var open = panel.classList.toggle('open');
      el.setAttribute('aria-expanded', open ? 'true' : 'false');
      // smooth height: set to content height when open, zero when shut
      panel.style.maxHeight = open ? (panel.scrollHeight + 'px') : '0px';
    },

    // ── TODAY ──
    checklist: async function (el) {
      var key = el.dataset.key;
      var row = el.classList.contains('done');
      try { await post('/checklist', { key: key, value: !row }); }
      catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      loadToday();
    },

    'toggle-today-row': async function () {
      var tr = (S.today || {}).today_row;
      var wk = (S.today || {}).week;
      if (!tr || !wk) return;
      try { await post('/weeks/toggle', { id: wk.id, date: tr.date }); }
      catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      loadToday();
    },

    'stop-session': function () { stopRunningSession('', ''); },
    'confirm-stop': function () {
      var notes = $('#stop-notes') ? $('#stop-notes').value.trim() : '';
      var capture = $('#stop-capture') ? $('#stop-capture').value.trim() : '';
      closeModal();
      stopRunningSession(notes, capture);
    },

    // ── PLAN ──
    'topic-status': async function (el) {
      var order = { todo: 'doing', doing: 'done', done: 'todo' };
      var next = order[el.dataset.current] || 'todo';
      try { await post('/topics/status', { id: el.dataset.id, status: next }); }
      catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      getJson(API + '/topics').then(function (d) { S.topics = d; renderPlan(); });
    },

    'day-detail': function (el) { openDayModal(el.dataset.wid, Number(el.dataset.di)); },

    'week-add': openWeekAddModal,

    'week-create': async function () {
      var v = formValues(['mw-start', 'mw-fa', 'mw-fb']);
      if (!v['mw-start']) { toast('a start date is needed', 'bad'); return; }
      try {
        await post('/weeks', { start: v['mw-start'], focusA: v['mw-fa'], focusB: v['mw-fb'] });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      closeModal();
      toast('week added', 'ok');
      loadPlan();
    },

    'week-save': async function (el) {
      var id = el.dataset.id;
      var fa = $('#fa-' + cssId(id)), fb = $('#fb-' + cssId(id));
      if (!fa || !fb) return;
      var wk = (S.weeks.weeks || []).find(function (x) { return x.id === id; });
      try {
        await post('/weeks/save', { id: id, focusA: fa.value.trim(), focusB: fb.value.trim(), days: (wk && wk.days) || [] });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      toast('focuses saved', 'ok');
      getJson(API + '/weeks').then(function (d) { S.weeks = d; renderPlan(); });
    },

    'week-delete': function (el) {
      openModal(
        '<div class="modal-title">Delete this week?</div>'
        + '<div class="card-sub">The week and its seven day rows go away. This cannot be undone.</div>'
        + '<div class="form-actions">'
        + '<button class="btn ghost" data-modal-action="close" type="button">CANCEL</button>'
        + '<button class="btn danger" data-modal-action="week-delete-go" data-id="' + esc(el.dataset.id) + '" type="button">DELETE</button>'
        + '</div>');
    },
    'week-delete-go': async function (el) {
      try { await post('/weeks/delete', { id: el.dataset.id }); }
      catch (err) { toast('could not delete: ' + err.message, 'bad'); return; }
      closeModal();
      toast('week deleted', 'ok');
      loadPlan();
    },

    'week-toggle': async function (el) {
      try { await post('/weeks/toggle', { id: el.dataset.wid, date: el.dataset.date }); }
      catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      getJson(API + '/weeks').then(function (d) { S.weeks = d; renderPlan(); loadTodayIfNeeded(); });
    },

    // ── loose items ──
    'loose-add': async function () {
      var title = $('#loose-title') ? $('#loose-title').value.trim() : '';
      if (!title) { toast('a title is needed', 'bad'); return; }
      try {
        await post('/plan/add', {
          title: title,
          target_date: $('#loose-date').value,
          notes: $('#loose-notes').value.trim()
        });
      } catch (err) { toast('could not add: ' + err.message, 'bad'); return; }
      toast('added', 'ok');
      loadPlan();
    },
    'loose-done': async function (el) {
      try { await post('/plan/done', { item_id: el.dataset.id }); }
      catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      getJson(API + '/plan').then(function (d) { S.planLoose = d; renderLooseItems(); });
    },
    'loose-remove': async function (el) {
      try { await post('/plan/remove', { item_id: el.dataset.id }); }
      catch (err) { toast('could not remove: ' + err.message, 'bad'); return; }
      getJson(API + '/plan').then(function (d) { S.planLoose = d; renderLooseItems(); });
    },

    // ── RECALL: review flow ──
    'flip-card': function () {
      var due = ((S.cards || {}).due || []);
      var card = due[S.reviewIndex];
      var fc = $('#flashcard');
      if (!card || !fc) return;
      card._flipped = !card._flipped;
      fc.classList.toggle('flipped', !!card._flipped);
      // rate buttons unlock the moment the answer is visible
      $all('.rate-btn').forEach(function (b) { b.disabled = !card._flipped; });
    },

    rate: async function (el) {
      var due = ((S.cards || {}).due || []);
      var card = due[S.reviewIndex];
      if (!card) return;
      var q = Number(el.dataset.q);
      try { await post('/recall-cards/review', { card_id: card.id, quality: q }); }
      catch (err) { toast('could not save rating: ' + err.message, 'bad'); return; }
      S._enterNext = true;
      var stage = $('#flash-stage') || $('#recall-body');
      if (!REDUCE && stage.firstElementChild) {
        stage.classList.add('flash-leave');
        setTimeout(loadRecall, 260);
      } else {
        loadRecall();
      }
    },

    'card-add': function () { openModal(cardFormHtml(null)); },

    'card-edit': function (el) {
      var cd = ((S.cards || {}).cards || []).find(function (x) { return String(x.id) === String(el.dataset.id); });
      if (cd) openModal(cardFormHtml(cd));
    },

    'card-delete': function (el) {
      openModal(
        '<div class="modal-title">Delete this card?</div>'
        + '<div class="card-sub">Its review history goes with it. This cannot be undone.</div>'
        + '<div class="form-actions">'
        + '<button class="btn ghost" data-modal-action="close" type="button">CANCEL</button>'
        + '<button class="btn danger" data-modal-action="card-delete-go" data-id="' + esc(el.dataset.id) + '" type="button">DELETE</button>'
        + '</div>');
    },
    'card-delete-go': async function (el) {
      try { await post('/recall-cards/delete', { id: el.dataset.id }); }
      catch (err) { toast('could not delete: ' + err.message, 'bad'); return; }
      closeModal();
      toast('card deleted', 'ok');
      S.reviewIndex = 0;
      loadRecall();
    },
    'card-save-new': async function () {
      var v = formValues(['cf-topic', 'cf-track', 'cf-elevator', 'cf-likely', 'cf-trap', 'cf-example', 'cf-resume']);
      if (!v['cf-topic']) { toast('a topic is needed', 'bad'); return; }
      try {
        await post('/recall-cards/add', {
          topic: v['cf-topic'], track: v['cf-track'] || 'A',
          elevator: v['cf-elevator'], likely_q: v['cf-likely'],
          trap_q: v['cf-trap'], example: v['cf-example'], resume_link: v['cf-resume']
        });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      closeModal();
      toast('card added', 'ok');
      loadRecall();
    },
    'card-save-edit': async function (el) {
      var v = formValues(['cf-topic', 'cf-track', 'cf-elevator', 'cf-likely', 'cf-trap', 'cf-example', 'cf-resume']);
      if (!v['cf-topic']) { toast('a topic is needed', 'bad'); return; }
      try {
        await post('/recall-cards/update', {
          id: el.dataset.id, topic: v['cf-topic'], track: v['cf-track'] || 'A',
          elevator: v['cf-elevator'], likely_q: v['cf-likely'],
          trap_q: v['cf-trap'], example: v['cf-example'], resume_link: v['cf-resume']
        });
      } catch (err) { toast('could not save: ' + err.message, 'bad'); return; }
      closeModal();
      toast('card saved', 'ok');
      loadRecall();
    },

    'cards-manage': function () {
      openModal(
        '<div class="modal-title">Manage cards</div>'
        + manageListHtml()
        + '<div class="form-actions">'
        +   '<button class="btn ghost" data-modal-action="close" type="button">CLOSE</button>'
        + '</div>');
    },

    // ── modal-scoped actions ──
    'close': closeModal,
    'day-toggle': function (el) {
      closeModal();
      ACTIONS['week-toggle']({ dataset: { wid: el.dataset.wid, date: el.dataset.date } });
    }
  };

  // route clicks inside the modal
  modalBox.addEventListener('click', function (e) {
    var el = e.target.closest('[data-modal-action]');
    if (!el) return;
    var h = ACTIONS[el.dataset.modalAction];
    if (h) h(el, e);
  });

  // ════════════════════════════════════════════════════════════════
  //  SMALL SHARED HELPERS
  // ════════════════════════════════════════════════════════════════
  // ids can contain characters that are awkward in a CSS selector
  function cssId(id) {
    return String(id).replace(/[^A-Za-z0-9_-]/g, function (c) {
      return '\\' + c;
    });
  }

  function loadTodayIfNeeded() {
    if (S.tab === 'today' || LOADED.today === false) loadToday();
  }

  async function stopRunningSession(notes, capture) {
    try { await post('/study/stop', { notes: notes, capture: capture }); }
    catch (err) { toast('could not stop: ' + err.message, 'bad'); return; }
    toast('session stopped', 'ok');
    stopElapsedTimer();
    S.runningSession = null;
    if (S.tab === 'today') loadToday();
    LOADED.today = false;
  }

  // ════════════════════════════════════════════════════════════════
  //  START - Today loads first; the rest load on first visit
  // ════════════════════════════════════════════════════════════════
  LOADED.today = true;
  loadToday();
  requestAnimationFrame(function () {
    moveRailPill();
    moveThumb('plan');
  });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(moveRailPill).catch(function () {});
  }
})();