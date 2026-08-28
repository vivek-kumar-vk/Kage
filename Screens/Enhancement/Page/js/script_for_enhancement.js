// =====================================================================
// SCRIPT FOR: Enhancement
// =====================================================================
// Talks only to this screen's own API (/api/enhancement/...) - never
// another screen's port, never an import. Moved out of Learning's
// script_for_learning.js 2026-08-22 (ADR-067). The board is now a
// JIRA-style kanban: four plain-English columns, native HTML5 drag and
// drop (INKY is local-only, so no SortableJS, no CDN, no libraries),
// and a modal for editing an idea and its comments.

    const API = '/api/enhancement';

    async function getJson(path) {
      const res = await fetch(path);
      if (!res.ok) throw new Error(path + ' answered ' + res.status);
      return res.json();
    }
    async function postJson(path, body, method) {
      const res = await fetch(path, { method: method || 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
      let data = {};
      try { data = await res.json(); } catch (e) {}
      return data;
    }
    async function del(path) {
      const res = await fetch(path, { method: 'DELETE' });
      let data = {};
      try { data = await res.json(); } catch (e) {}
      return data;
    }
    function escapeHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    // ══════════════════════════════════════════════════════════════
    //  THE BOARD
    //  A stat row, a search/area/source/done filter that hides and
    //  shows CARDS across every column client-side, then four kanban
    //  columns. One fetch, all filtering and ordering local.
    // ══════════════════════════════════════════════════════════════
    let enhancementIdeas = [];
    let openIdeaId = null;              // idea currently shown in the modal
    let dragIdeaId = null;              // idea being dragged, if any
    let suppressNextCardClick = false;  // letting go of a drag must not open the modal
    const ideaFilters = { search: '', area: '', source: 'all', showDone: false };

    const STATUSES = [
      { value: 'ideas',       label: 'Ideas' },
      { value: 'todo',        label: 'To Do' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'done',        label: 'Done' }
    ];
    const PRIORITIES = ['low', 'medium', 'high', 'critical'];

    function areaBucket(area) {
      const cleaned = (area || '').split('/')[0].replace(/\(.*?\)/g, '').trim();
      return cleaned || 'General';
    }

    // area badges are coloured per top-level bucket, hashed off the
    // bucket's own name - no fixed list anywhere, so a bucket that has
    // never been seen before still gets a stable colour
    const BADGE_COLOURS = ['var(--p5-cyan)', 'var(--p5-yellow)', 'var(--violet)', 'var(--p5-lime)', 'var(--amber)', '#ff7ab6', '#8ecbff'];
    function areaBadgeStyle(area) {
      const b = areaBucket(area);
      let h = 0;
      for (let i = 0; i < b.length; i++) h = (h * 31 + b.charCodeAt(i)) | 0;
      return '--badge:' + BADGE_COLOURS[Math.abs(h) % BADGE_COLOURS.length];
    }

    const orderIndexOf = (i) => (typeof i.order_index === 'number' && isFinite(i.order_index)) ? i.order_index : 0;
    function sortForColumn(list) {
      return [...list].sort((a, b) => orderIndexOf(a) - orderIndexOf(b)
        || String(a.added_at || '').localeCompare(String(b.added_at || '')));
    }

    function passesFilters(idea) {
      if (!ideaFilters.showDone && (idea.status || 'ideas') === 'done') return false;
      if (ideaFilters.source !== 'all' && idea.source !== ideaFilters.source) return false;
      if (ideaFilters.area && areaBucket(idea.area) !== ideaFilters.area) return false;
      const q = ideaFilters.search.trim().toLowerCase();
      if (q) {
        const hay = ((idea.title || '') + ' ' + (idea.note || '') + ' ' + (idea.area || '')).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    }

    async function loadEnhancement() {
      let data;
      try { data = await getJson(API + '/ideas'); }
      catch (err) {
        document.getElementById('enhancement-board-empty').innerHTML =
          `<div class="empty-note">could not load: ${escapeHtml(err.message)}</div>`;
        document.getElementById('enhancement-board').innerHTML = '';
        return;
      }
      enhancementIdeas = data.ideas || [];
      renderEnhancement();
      // Rule 6: a board's age has to be visible. Stamped after every
      // successful read, in IST, via the shared page guard.
      if (window.INKY_GUARD) {
        let el = document.getElementById('board-updated');
        const anchor = document.getElementById('enhancement-board');
        if (!el && anchor) {
          el = document.createElement('div');
          el.id = 'board-updated';
          el.style.cssText = 'font-size:0.62rem;letter-spacing:0.5px;' +
            'color:var(--bone-dim);text-align:right;margin:2px 0 6px;';
          anchor.parentNode.insertBefore(el, anchor);
        }
        window.INKY_GUARD.freshStamp(el);
      }
    }

    function renderEnhancement() {
      const total = enhancementIdeas.length;
      const doneCount = enhancementIdeas.filter(i => (i.status || 'ideas') === 'done').length;
      const openCount = total - doneCount;
      const fromYou = enhancementIdeas.filter(i => i.source === 'user').length;
      const fromAi = enhancementIdeas.filter(i => i.source === 'ai').length;

      document.getElementById('enhancement-stats').innerHTML = `
        <div class="stat-card">
          <div class="stat-label">Ideas captured</div>
          <div class="stat-value">${total}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Open</div>
          <div class="stat-value">${openCount}</div>
          <div class="stat-sub">${doneCount} done</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">From you</div>
          <div class="stat-value">${fromYou}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">From AI</div>
          <div class="stat-value">${fromAi}</div>
          <div class="stat-sub">marked with the violet edge</div>
        </div>`;

      const areaSelect = document.getElementById('idea-area-filter');
      const buckets = [...new Set(enhancementIdeas.map(i => areaBucket(i.area)))].sort();
      const currentArea = areaSelect.value;
      areaSelect.innerHTML = `<option value="">All areas</option>` +
        buckets.map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
      areaSelect.value = buckets.includes(currentArea) ? currentArea : '';
      ideaFilters.area = areaSelect.value;

      const filtered = enhancementIdeas.filter(passesFilters);

      const emptyEl = document.getElementById('enhancement-board-empty');
      if (!total) {
        emptyEl.innerHTML = `<div class="empty-note">Nothing captured yet. Add the first idea above.</div>`;
      } else if (!filtered.length) {
        emptyEl.innerHTML = `<div class="empty-note">No ideas match these filters.</div>`;
      } else {
        emptyEl.innerHTML = '';
      }

      renderBoard(filtered);
    }

    // Four plain-English columns. Filters have already decided which
    // ideas exist; here they just land in their column, ordered.
    function renderBoard(filtered) {
      const boardEl = document.getElementById('enhancement-board');
      boardEl.innerHTML = STATUSES.map(col => {
        const colIdeas = sortForColumn(filtered.filter(i => (i.status || 'ideas') === col.value));
        return `
        <section class="kanban-col" data-status="${col.value}">
          <header class="kanban-col-head">
            <span class="kanban-col-name">${col.label}</span>
            <span class="kanban-count">${colIdeas.length}</span>
          </header>
          <div class="kanban-cards" data-status="${col.value}">
            ${colIdeas.map(ideaCardHtml).join('')}
          </div>
          ${colIdeas.length ? '' : '<div class="kanban-empty-hint">nothing here yet</div>'}
        </section>`;
      }).join('');
      wireBoard();
    }

    function ideaCardHtml(idea) {
      const status = idea.status || 'ideas';
      const done = status === 'done';
      const ai = idea.source === 'ai';
      const prio = PRIORITIES.includes(idea.priority) ? idea.priority : 'medium';
      const commentCount = (idea.comments || []).length;
      const date = String(idea.updated_at || idea.added_at || '').slice(0, 10);
      return `
        <div class="kanban-card${done ? ' is-done' : ''}${ai ? ' ai-generated' : ''}"
             draggable="true" data-id="${escapeHtml(String(idea.id))}">
          <div class="kanban-card-top">
            <span class="idea-key">${escapeHtml(idea.key || 'ENH-' + idea.id)}</span>
            <span class="prio-tag ${prio}">${prio}</span>
          </div>
          <div class="kanban-card-title">${escapeHtml(idea.title)}${ai ? '<span class="source-badge">AI</span>' : ''}</div>
          ${idea.area ? `<div class="area-badge" style="${areaBadgeStyle(idea.area)}">${escapeHtml(areaBucket(idea.area))}</div>` : ''}
          <div class="kanban-card-foot">
            <span>${escapeHtml(date)}</span>
            ${commentCount ? `<span class="card-comments">${commentCount} comment${commentCount === 1 ? '' : 's'}</span>` : ''}
          </div>
        </div>`;
    }

    function clearDropHighlights() {
      document.querySelectorAll('.kanban-col.drop-target').forEach(el => el.classList.remove('drop-target'));
    }

    function wireBoard() {
      const boardEl = document.getElementById('enhancement-board');

      // native HTML5 drag and drop only - no libraries anywhere in INKY
      boardEl.querySelectorAll('.kanban-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
          dragIdeaId = card.dataset.id;
          card.classList.add('dragging');
          e.dataTransfer.effectAllowed = 'move';
          try { e.dataTransfer.setData('text/plain', dragIdeaId); } catch (err) {}
        });
        card.addEventListener('dragend', () => {
          card.classList.remove('dragging');
          dragIdeaId = null;
          clearDropHighlights();
          // a click event lands straight after dragend - swallow that
          // one so releasing a drag never opens the modal
          suppressNextCardClick = true;
          setTimeout(() => { suppressNextCardClick = false; }, 0);
        });
      });

      boardEl.querySelectorAll('.kanban-cards').forEach(zone => {
        zone.addEventListener('dragover', (e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'move';
          zone.closest('.kanban-col').classList.add('drop-target');
        });
        zone.addEventListener('dragleave', (e) => {
          if (!zone.contains(e.relatedTarget)) zone.closest('.kanban-col').classList.remove('drop-target');
        });
        zone.addEventListener('drop', (e) => handleDropInColumn(e, zone));
      });

      // click (not drag) opens the modal
      boardEl.addEventListener('click', (e) => {
        const card = e.target.closest('.kanban-card');
        if (!card || suppressNextCardClick || dragIdeaId) return;
        const idea = enhancementIdeas.find(i => String(i.id) === card.dataset.id);
        if (idea) openIdeaModal(idea);
      });
    }

    // Where in the column did it land? Compare the pointer against the
    // midpoints of the cards actually on screen, turn that slot into an
    // order_index (the midpoint of the two neighbours it sits between),
    // PATCH the status endpoint with it, then re-fetch.
    async function handleDropInColumn(e, zone) {
      e.preventDefault();
      clearDropHighlights();
      if (!dragIdeaId) return;
      const idea = enhancementIdeas.find(i => String(i.id) === dragIdeaId);
      if (!idea) return;

      const newStatus = zone.dataset.status;
      const cardEls = [...zone.querySelectorAll('.kanban-card')].filter(c => c.dataset.id !== dragIdeaId);

      let insertAt = cardEls.length;
      for (let i = 0; i < cardEls.length; i++) {
        const r = cardEls[i].getBoundingClientRect();
        if (e.clientY < r.top + r.height / 2) { insertAt = i; break; }
      }

      const prev = insertAt > 0
        ? enhancementIdeas.find(i => String(i.id) === cardEls[insertAt - 1].dataset.id) : null;
      const next = insertAt < cardEls.length
        ? enhancementIdeas.find(i => String(i.id) === cardEls[insertAt].dataset.id) : null;

      let orderIndex;
      if (prev && next) orderIndex = (orderIndexOf(prev) + orderIndexOf(next)) / 2;
      else if (prev) orderIndex = orderIndexOf(prev) + 10;
      else if (next) orderIndex = orderIndexOf(next) - 10;
      else orderIndex = 10;

      dragIdeaId = null;
      await postJson(API + '/ideas/' + encodeURIComponent(idea.id) + '/status',
        { status: newStatus, order_index: orderIndex }, 'PATCH');
      loadEnhancement();
    }

    // ══════════════════════════════════════════════════════════════
    //  THE MODAL
    //  The full idea: editable priority/status/area, the note with its
    //  line breaks kept, the comments (author-tagged, AI ones with the
    //  violet edge), and save/delete. Everything goes through the API,
    //  then a refresh.
    // ══════════════════════════════════════════════════════════════
    const modalOverlay = document.getElementById('idea-modal-overlay');

    function currentOpenIdea() {
      return enhancementIdeas.find(i => String(i.id) === String(openIdeaId)) || null;
    }

    function openIdeaModal(idea) {
      openIdeaId = idea.id;
      document.getElementById('modal-key').textContent = idea.key || ('ENH-' + idea.id);

      const titleEl = document.getElementById('modal-title');
      titleEl.innerHTML = escapeHtml(idea.title) +
        (idea.source === 'ai' ? '<span class="source-badge">AI</span>' : '');
      titleEl.className = 'modal-title' + (idea.source === 'ai' ? ' ai-generated' : '');

      const prioSel = document.getElementById('modal-priority');
      prioSel.innerHTML = PRIORITIES.map(p => `<option value="${p}">${p}</option>`).join('');
      prioSel.value = PRIORITIES.includes(idea.priority) ? idea.priority : 'medium';

      const statusSel = document.getElementById('modal-status');
      statusSel.innerHTML = STATUSES.map(s => `<option value="${s.value}">${s.label}</option>`).join('');
      statusSel.value = idea.status || 'ideas';

      document.getElementById('modal-area').value = idea.area || '';
      document.getElementById('modal-note').innerHTML =
        (idea.note || '') ? escapeHtml(idea.note) : '<span class="none-note">no note</span>';
      renderModalComments(idea);
      document.getElementById('modal-comment-input').value = '';
      document.getElementById('modal-error').innerHTML = '';
      resetDeleteButton();
      modalOverlay.hidden = false;
    }

    function closeIdeaModal() {
      modalOverlay.hidden = true;
      openIdeaId = null;
    }

    function renderModalComments(idea) {
      const list = idea.comments || [];
      const el = document.getElementById('modal-comments');
      el.innerHTML = list.length ? list.map(c => `
        <div class="comment-row${c.author === 'ai' ? ' ai-generated' : ''}">
          <div class="comment-meta"><span class="author">${escapeHtml(c.author || 'unknown')}</span>${c.created_at ? ' — ' + escapeHtml(String(c.created_at).slice(0, 10)) : ''}</div>
          <div class="comment-text">${escapeHtml(c.text)}</div>
        </div>`).join('')
        : '<div class="empty-note">no comments yet</div>';
    }

    document.getElementById('idea-add-btn').addEventListener('click', async () => {
      const title = document.getElementById('idea-title').value.trim();
      const area = document.getElementById('idea-area').value.trim();
      const note = document.getElementById('idea-note').value.trim();
      const errEl = document.getElementById('idea-error');
      errEl.innerHTML = '';
      if (!title) { errEl.innerHTML = `<div class="empty-note">an idea needs a title</div>`; return; }
      const result = await postJson(API + '/ideas', { title, area, note, priority: 'medium', source: 'user' });
      if (!result.ok) { errEl.innerHTML = `<div class="empty-note">${escapeHtml(result.problem || 'could not add it')}</div>`; return; }
      document.getElementById('idea-title').value = '';
      document.getElementById('idea-area').value = '';
      document.getElementById('idea-note').value = '';
      if (result.duplicate_warning) {
        // never blocks - the idea was saved; this is only a second look
        const w = result.duplicate_warning;
        errEl.innerHTML = `<div class="empty-note">added — but it looks close to ` +
          `${escapeHtml(w.of_key || 'an existing idea')} "${escapeHtml(w.of_title)}" (${escapeHtml(w.reason || 'similar title')})</div>`;
      }
      loadEnhancement();
    });

    document.getElementById('idea-search').addEventListener('input', (e) => {
      ideaFilters.search = e.target.value;
      renderEnhancement();
    });
    document.getElementById('idea-area-filter').addEventListener('change', (e) => {
      ideaFilters.area = e.target.value;
      renderEnhancement();
    });
    document.getElementById('idea-show-done').addEventListener('change', (e) => {
      ideaFilters.showDone = e.target.checked;
      renderEnhancement();
    });
    document.querySelectorAll('#idea-source-filter .seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#idea-source-filter .seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        ideaFilters.source = btn.dataset.value;
        renderEnhancement();
      });
    });

    // ── save: PUT what changed, PATCH a status move, then refresh ──
    document.getElementById('modal-save-btn').addEventListener('click', async () => {
      const idea = currentOpenIdea();
      if (!idea) { closeIdeaModal(); return; }
      const errEl = document.getElementById('modal-error');
      errEl.innerHTML = '';

      const priority = document.getElementById('modal-priority').value;
      const status = document.getElementById('modal-status').value;
      const area = document.getElementById('modal-area').value.trim();

      const calls = [];
      if (priority !== (idea.priority || 'medium')) {
        calls.push(postJson(API + '/ideas/' + encodeURIComponent(idea.id), { priority }, 'PUT'));
      }
      if (area !== (idea.area || '')) {
        calls.push(postJson(API + '/ideas/' + encodeURIComponent(idea.id), { area }, 'PUT'));
      }
      if ((idea.status || 'ideas') !== status) {
        // a status change from the modal lands the idea at the end of
        // its new column - drag it afterwards if the exact spot matters
        const destOthers = sortForColumn(enhancementIdeas.filter(i =>
          String(i.id) !== String(idea.id) && (i.status || 'ideas') === status));
        const orderIndex = destOthers.length ? orderIndexOf(destOthers[destOthers.length - 1]) + 10 : 10;
        calls.push(postJson(API + '/ideas/' + encodeURIComponent(idea.id) + '/status',
          { status, order_index: orderIndex }, 'PATCH'));
      }

      if (!calls.length) { closeIdeaModal(); return; }
      const results = await Promise.all(calls);
      const failed = results.find(r => r && r.ok === false);
      if (failed) {
        errEl.innerHTML = `<div class="empty-note">${escapeHtml(failed.problem || 'could not save the change')}</div>`;
        return;
      }
      closeIdeaModal();
      loadEnhancement();
    });

    // ── comments: input + button (Enter works too) ──
    async function addCommentFromModal() {
      const idea = currentOpenIdea();
      if (!idea) return;
      const input = document.getElementById('modal-comment-input');
      const text = input.value.trim();
      const errEl = document.getElementById('modal-error');
      errEl.innerHTML = '';
      if (!text) { errEl.innerHTML = `<div class="empty-note">write something first</div>`; return; }
      const result = await postJson(API + '/ideas/' + encodeURIComponent(idea.id) + '/comments', { text, author: 'user' });
      if (result && result.ok === false) {
        errEl.innerHTML = `<div class="empty-note">${escapeHtml(result.problem || 'could not add the comment')}</div>`;
        return;
      }
      input.value = '';
      await loadEnhancement();
      const fresh = currentOpenIdea();
      if (fresh) renderModalComments(fresh); else closeIdeaModal();
    }
    document.getElementById('modal-comment-add').addEventListener('click', addCommentFromModal);
    document.getElementById('modal-comment-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') addCommentFromModal();
    });

    // ── delete: two-step on the button itself, no native dialogs ──
    let deleteArmedTimer = null;
    function resetDeleteButton() {
      clearTimeout(deleteArmedTimer);
      const btn = document.getElementById('modal-delete-btn');
      btn.textContent = 'DELETE';
      btn.dataset.armed = '';
    }
    document.getElementById('modal-delete-btn').addEventListener('click', async () => {
      const btn = document.getElementById('modal-delete-btn');
      const idea = currentOpenIdea();
      if (!idea) return;
      if (btn.dataset.armed !== 'yes') {
        btn.dataset.armed = 'yes';
        btn.textContent = 'SURE?';
        deleteArmedTimer = setTimeout(resetDeleteButton, 4000);
        return;
      }
      resetDeleteButton();
      await del(API + '/ideas?id=' + encodeURIComponent(idea.id));
      closeIdeaModal();
      loadEnhancement();
    });

    // ── closing: the X, a click on the dark around the box, or Escape ──
    document.getElementById('modal-close-btn').addEventListener('click', closeIdeaModal);
    modalOverlay.addEventListener('mousedown', (e) => { if (e.target === modalOverlay) closeIdeaModal(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modalOverlay.hidden) closeIdeaModal();
    });

    // ══════════════════════════════════════════════════════════════
    //  START - wrapped so one startup throw names itself instead of
    //  silently killing everything after it (W3.1 error boundary).
    // ══════════════════════════════════════════════════════════════
    (window.INKY_GUARD ? window.INKY_GUARD.boundary('enhancement-start', loadEnhancement)
                       : loadEnhancement)();
