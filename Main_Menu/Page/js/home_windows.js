// ----------------------------------------------------------------------
//  home_windows.js - the floating calendar and notes windows.
//
//  Owns every open/close decision for both windows plus everything that
//  renders inside them. The HTML ships only the shells; this file makes
//  them behave.
//
//  Honesty notes (C12): a failed event add prints an inline error line
//  rather than a browser alert, notes storage failures say "storage
//  unavailable" instead of silently pretending to save, and clearing
//  notes asks via a two-click arm because confirm() dialogs are a ruder
//  way of asking the same question.
// ----------------------------------------------------------------------
(function () {
  'use strict';

  // Prefix defined once in home_data.js; literal fallback so this file
  // still works if it is ever loaded standalone.
  const API = window.INKY_API || '/api/main_menu';

  const WINDOWS = ['calendar-window', 'notes-window'];
  let openId = null;

  function byId(id) { return document.getElementById(id); }

  function toISO(date) {
    const p = function (n) { return String(n).padStart(2, '0'); };
    return date.getFullYear() + '-' + p(date.getMonth() + 1) + '-' + p(date.getDate());
  }

  function todayISO() { return toISO(new Date()); }

  // ------------------------------------------------------------------
  //  WINDOW MANAGER - one open window at a time, overlay behind it,
  //  Escape / overlay click / [data-close] all close. Opening one window
  //  closes the other, so the manager never has to track stacking.
  // ------------------------------------------------------------------
  function closeAllWindows() {
    WINDOWS.forEach(function (id) {
      const win = byId(id);
      if (win) win.hidden = true;
    });
    const overlay = byId('window-overlay');
    if (overlay) overlay.hidden = true;
    openId = null;
  }

  function openWindow(id) {
    const win = byId(id);
    if (!win) return;
    closeAllWindows();
    openId = id;
    win.hidden = false;
    const overlay = byId('window-overlay');
    if (overlay) overlay.hidden = false;

    // A dialog div is not focusable by default; tabindex="-1" lets it
    // take focus without joining the tab order, which is what keyboard
    // users need the moment a modal opens.
    win.setAttribute('tabindex', '-1');
    try { win.focus({ preventScroll: true }); } catch (err) { win.focus(); }

    if (id === 'calendar-window') onCalendarOpen();
    if (id === 'notes-window') onNotesOpen();
  }

  // Delegated on document, not bound per button: the utility rail is
  // rendered by the inline script AFTER this file loads, so binding at
  // load time would miss its buttons. The bell has no data-window, so
  // clicks on it fall straight through this matcher and do nothing -
  // which is exactly right while notifications have no source.
  document.addEventListener('click', function (e) {
    const opener = e.target.closest('[data-window]');
    if (opener) {
      openWindow(opener.dataset.window);
      return;
    }
    if (e.target.closest('[data-close]')) {
      closeAllWindows();
      return;
    }
    // Clicks land ON the overlay only when it is the top thing hit -
    // the windows sit above it, so this cannot close them from inside.
    if (e.target.id === 'window-overlay') {
      closeAllWindows();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && openId) closeAllWindows();
  });

  // ------------------------------------------------------------------
  //  CALENDAR - a month grid, a selected day, and real events only.
  //  Module-level state: the view stays where the visitor left it, and
  //  events are refetched on EVERY open (never cached across opens) so
  //  the dots can't go stale.
  // ------------------------------------------------------------------
  const DOW = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  let calYear = null;
  let calMonth = null;          // 0-based, like Date.getMonth()
  let selectedDate = null;      // 'YYYY-MM-DD' local, or null
  let monthEvents = {};         // date -> [titles], rebuilt per open

  function onCalendarOpen() {
    if (calYear === null) {
      const now = new Date();
      calYear = now.getFullYear();
      calMonth = now.getMonth();
      // First open lands on today, so the day's own events are showing
      // before a single click - the calendar answers "what is today"
      // before it answers "what is possible".
      selectedDate = todayISO();
    }
    renderCalendar();
    fetchEvents().then(renderCalendar);
  }

  async function fetchEvents() {
    monthEvents = {};
    try {
      const res = await fetch(API + '/calendar/events');
      if (!res.ok) throw new Error('answered ' + res.status);
      const data = await res.json();
      (Array.isArray(data && data.events) ? data.events : []).forEach(function (ev) {
        if (!ev || !ev.date) return;
        if (!monthEvents[ev.date]) monthEvents[ev.date] = [];
        if (ev.title) monthEvents[ev.date].push(ev.title);
      });
    } catch (err) {
      // Dots simply do not appear. Showing no dots is honest when the
      // source is down; showing fake ones would not be.
    }
  }

  function renderCalendar() {
    const body = byId('calendar-body');
    if (!body) return;

    const head = document.createElement('div');
    head.className = 'cal-head';

    const prev = document.createElement('button');
    prev.type = 'button';
    prev.className = 'cal-nav';
    prev.dataset.calDir = '-1';
    prev.setAttribute('aria-label', 'Previous month');
    prev.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';

    const next = document.createElement('button');
    next.type = 'button';
    next.className = 'cal-nav';
    next.dataset.calDir = '1';
    next.setAttribute('aria-label', 'Next month');
    next.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';

    const label = document.createElement('span');
    label.className = 'cal-label';
    label.textContent = new Date(calYear, calMonth, 1)
      .toLocaleDateString([], { month: 'long', year: 'numeric' });

    const todayBtn = document.createElement('button');
    todayBtn.type = 'button';
    todayBtn.className = 'cal-today-btn';
    todayBtn.dataset.calToday = '1';
    todayBtn.setAttribute('aria-label', 'Jump to today');
    todayBtn.textContent = 'TODAY';

    head.appendChild(prev);
    head.appendChild(label);
    head.appendChild(todayBtn);
    head.appendChild(next);

    const grid = document.createElement('div');
    grid.className = 'cal-grid';

    DOW.forEach(function (d) {
      const cell = document.createElement('span');
      cell.className = 'cal-dow';
      cell.textContent = d;
      grid.appendChild(cell);
    });

    // Start on the first cell of the first week: the Sunday on or before
    // the 1st, so other-month days pad the edges exactly as far as needed.
    const firstDow = new Date(calYear, calMonth, 1).getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const totalCells = Math.ceil((firstDow + daysInMonth) / 7) * 7;
    const todayIso = todayISO();

    for (let i = 0; i < totalCells; i++) {
      const d = new Date(calYear, calMonth, 1 - firstDow + i);
      const iso = toISO(d);
      const cell = document.createElement('button');
      cell.type = 'button';
      cell.className = 'cal-day';
      cell.dataset.date = iso;
      if (d.getMonth() !== calMonth) cell.classList.add('other-month');
      if (iso === todayIso) cell.classList.add('today');
      if (iso === selectedDate) cell.classList.add('selected');

      // The date number sits in the corner, today's filled - then the
      // day's own events stack underneath as chips, truncated to what
      // fits. Two chips and a count, like a real month wall: the full
      // list lives in the agenda under the grid.
      const num = document.createElement('span');
      num.className = 'cal-num';
      num.textContent = String(d.getDate());
      cell.appendChild(num);

      const MAX_CHIPS = 2;
      const titles = monthEvents[iso] || [];
      titles.slice(0, MAX_CHIPS).forEach(function (title) {
        const chip = document.createElement('span');
        chip.className = 'cal-chip';
        chip.textContent = title;
        chip.title = title;              // the whole word on hover
        if (iso < todayIso) chip.classList.add('past');
        cell.appendChild(chip);
      });
      if (titles.length > MAX_CHIPS) {
        const more = document.createElement('span');
        more.className = 'cal-more';
        more.textContent = '+' + (titles.length - MAX_CHIPS) + ' more';
        cell.appendChild(more);
      }
      grid.appendChild(cell);
    }

    body.innerHTML = '';
    body.appendChild(head);
    body.appendChild(grid);

    // The selected day's events, listed in full below the wall - chips
    // truncate, this does not. No selection falls back to today, which
    // is the day you most likely opened the calendar to ask about.
    const agendaDate = selectedDate || todayIso;
    const agendaTitles = monthEvents[agendaDate] || [];
    const agenda = document.createElement('div');
    agenda.className = 'cal-agenda';

    const agendaHead = document.createElement('div');
    agendaHead.className = 'cal-agenda-title';
    agendaHead.textContent = 'AGENDA — ' +
      new Date(agendaDate + 'T00:00:00').toLocaleDateString([], {
        weekday: 'long', day: 'numeric', month: 'long',
      });
    agenda.appendChild(agendaHead);

    if (!agendaTitles.length) {
      const empty = document.createElement('div');
      empty.className = 'cal-agenda-empty';
      empty.textContent = 'no events on this day';
      agenda.appendChild(empty);
    } else {
      agendaTitles.forEach(function (title) {
        const item = document.createElement('div');
        item.className = 'cal-agenda-item';
        item.textContent = title;
        agenda.appendChild(item);
      });
    }
    body.appendChild(agenda);
  }

  // Grid clicks are delegated on the window body, so month navigation and
  // day selection survive every re-render without rebinding.
  document.addEventListener('click', function (e) {
    const nav = e.target.closest('.cal-nav');
    if (nav) {
      calMonth += Number(nav.dataset.calDir);
      if (calMonth < 0) { calMonth = 11; calYear -= 1; }
      if (calMonth > 11) { calMonth = 0; calYear += 1; }
      renderCalendar();
      return;
    }
    const jump = e.target.closest('[data-cal-today]');
    if (jump) {
      const now = new Date();
      calYear = now.getFullYear();
      calMonth = now.getMonth();
      selectedDate = todayISO();
      renderCalendar();
      return;
    }
    const day = e.target.closest('.cal-day');
    if (day && day.dataset.date) {
      selectedDate = day.dataset.date; // YYYY-MM-DD, local - no UTC drift
      renderCalendar();
    }
  });

  // The inline error line: created once, shown/hidden. It lives inside
  // the add-event row's parent so a calendar re-render cannot wipe it.
  function showCalError(message) {
    const win = byId('calendar-window');
    if (!win) return;
    let line = win.querySelector('.cal-error');
    if (!line) {
      line = document.createElement('div');
      line.className = 'cal-error';
      const row = win.querySelector('.cal-event-add');
      if (row && row.parentNode) row.parentNode.insertBefore(line, row.nextSibling);
      else win.appendChild(line);
    }
    line.textContent = message;
  }

  function hideCalError() {
    const win = byId('calendar-window');
    if (!win) return;
    const line = win.querySelector('.cal-error');
    if (line) line.textContent = '';
  }

  async function addCalendarEvent() {
    const input = byId('cal-event-title');
    const btn = byId('cal-event-add');
    if (!input || !btn) return;

    const title = (input.value || '').trim();
    if (!title) {
      showCalError('give the event a title first');
      return;
    }

    btn.disabled = true;
    try {
      // No selected date falls back to today - stated in code here so
      // the fallback is visible rather than surprising.
      const res = await fetch(API + '/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: selectedDate || todayISO(), title: title }),
      });
      if (!res.ok) throw new Error('answered ' + res.status);

      input.value = '';
      hideCalError();
      // Re-read from the source instead of assuming what was stored -
      // the dot must reflect what the server actually kept.
      await fetchEvents();
      renderCalendar();
    } catch (err) {
      showCalError('the calendar did not take it — Data unavailable');
    } finally {
      btn.disabled = false;
    }
  }

  function wireCalendar() {
    const btn = byId('cal-event-add');
    if (btn) btn.addEventListener('click', addCalendarEvent);
    const input = byId('cal-event-title');
    if (input) {
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') addCalendarEvent();
      });
    }
  }

  // ------------------------------------------------------------------
  //  NOTES - one textarea, one localStorage key, debounced writes.
  //  All storage access is wrapped: private mode throws, and the honest
  //  answer to a thrown write is "storage unavailable", not silence.
  // ------------------------------------------------------------------
  const NOTES_KEY = 'inky_home_notes';
  let notesStorageOk = true;
  let saveTimer = null;

  function setNotesStatus(text) {
    const el = byId('notes-status');
    if (el) el.textContent = text;
  }

  function loadNotes() {
    try {
      const el = byId('notes-textarea');
      if (el) el.value = localStorage.getItem(NOTES_KEY) || '';
      notesStorageOk = true;
    } catch (err) {
      notesStorageOk = false;
      setNotesStatus('storage unavailable');
    }
  }

  function saveNotes() {
    const el = byId('notes-textarea');
    if (!el) return;
    try {
      localStorage.setItem(NOTES_KEY, el.value);
      notesStorageOk = true;
      setNotesStatus('saved ' +
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    } catch (err) {
      notesStorageOk = false;
      setNotesStatus('storage unavailable');
    }
  }

  function wireNotes() {
    const el = byId('notes-textarea');
    if (el) {
      el.addEventListener('input', function () {
        if (!notesStorageOk) return; // already known broken; don't spin uselessly
        setNotesStatus('saving\u2026');
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveNotes, 400);
      });
    }

    const clearBtn = byId('notes-clear');
    if (clearBtn) wireNotesClear(clearBtn);
  }

  // Two-click arm instead of confirm(): the button says CLEAR, then
  // SURE? for 2.5 seconds. A second click inside that window wipes;
  // otherwise it disarms itself. Same protection, no modal dialog.
  function wireNotesClear(btn) {
    let armed = false;
    let disarmTimer = null;

    btn.addEventListener('click', function () {
      if (!armed) {
        armed = true;
        btn.textContent = 'SURE?';
        disarmTimer = setTimeout(function () {
          armed = false;
          btn.textContent = 'CLEAR';
        }, 2500);
        return;
      }

      clearTimeout(disarmTimer);
      armed = false;
      btn.textContent = 'CLEAR';

      try {
        localStorage.removeItem(NOTES_KEY);
      } catch (err) {
        // The wipe of the key failing must not stop the visible clear -
        // but the status still tells the truth about storage.
        notesStorageOk = false;
      }
      const el = byId('notes-textarea');
      if (el) el.value = '';
      setNotesStatus(notesStorageOk ? 'cleared' : 'cleared here — storage unavailable');
    });
  }

  function onNotesOpen() {
    // Reload on open too: another tab may have changed the note while
    // this window was shut. The source of truth wins over the stale copy.
    loadNotes();
  }

  // ------------------------------------------------------------------
  //  BOOT
  // ------------------------------------------------------------------
  wireCalendar();
  wireNotes();
  loadNotes(); // notes exist before their window is ever opened

  // Exposed on purpose: the inline script (and any future screen) can
  // open a window programmatically without reaching into this closure.
  window.INKY_WINDOWS = { open: openWindow, closeAll: closeAllWindows };
})();