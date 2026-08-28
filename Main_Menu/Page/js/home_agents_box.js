// ----------------------------------------------------------------------
//  home_agents_box.js - the AGENTS accordion in the right-hand panel.
//
//  Reads the fleet from the menu's own agent registry and renders one
//  accordion section per payload section, in payload order - this file
//  invents no grouping of its own, because a grouping the server did not
//  declare would be a guess about how the fleet is organised (C12).
//
//  Honesty rules: an agent that is only a folder says "(folder only)",
//  a broken one says "(broken)", both dimmed - never dressed up as ready.
// ----------------------------------------------------------------------
(function () {
  'use strict';

  // home_data.js defines the prefix once; fall back to the literal so
  // this file still works if it is ever loaded standalone.
  const API = window.INKY_API || '/api/main_menu';
  const FLEET_ENDPOINT = API + '/agents/fleet';

  // States that must NEVER read as available. Anything else counts as
  // ready for the header count.
  const NOT_READY = { not_built: '(folder only)', broken: '(broken)' };

  // One line, first sentence, ~90 chars - the box is a roster, not a
  // documentation page; the full description lives with the agent.
  const DESC_MAX = 90;

  function byId(id) { return document.getElementById(id); }

  function firstSentence(text) {
    const s = String(text || '').trim();
    if (!s) return '';
    const m = s.match(/^[^.!?]*[.!?]/);
    const sentence = m ? m[0] : s;
    if (sentence.length <= DESC_MAX) return sentence;
    return sentence.slice(0, DESC_MAX - 1).trimEnd() + '\u2026';
  }

  // Built entirely from createElement/textContent - agent names and
  // descriptions are data, and data goes in via textContent, never
  // innerHTML (the same reason the chat bubbles escape their text).
  // Only the static chevron svg, written by this file itself, uses
  // innerHTML.
  function buildSection(section) {
    const item = document.createElement('div');
    item.className = 'accordion';

    const head = document.createElement('button');
    head.type = 'button';
    head.className = 'accordion-head';

    const label = document.createElement('span');
    label.textContent = section.label || section.key || 'unnamed';
    head.appendChild(label);

    // Rotation on open is pure CSS (.accordion.open .accordion-chevron),
    // so the JS only toggles the class - no inline style churn.
    const chevron = document.createElement('span');
    chevron.className = 'accordion-chevron';
    chevron.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<polyline points="6 9 12 15 18 9"/></svg>';
    head.appendChild(chevron);
    const body = document.createElement('div');
    body.className = 'accordion-body';

    const agents = Array.isArray(section.agents) ? section.agents : [];
    if (!agents.length) {
      // An empty section is stated, not collapsed silently (C12).
      const empty = document.createElement('div');
      empty.className = 'agents-empty';
      empty.textContent = 'no agents here yet';
      body.appendChild(empty);
    } else {
      agents.forEach(function (agent) {
        const row = document.createElement('div');
        row.className = 'agent-row';

        const notReadySuffix = NOT_READY[agent.state];
        if (notReadySuffix) {
          // Dimmed AND labelled: neither alone says it clearly enough.
          row.classList.add('dimmed');
          row.style.opacity = '0.45'; // inline fallback if the CSS class ships later
        }

        const name = document.createElement('span');
        name.className = 'agent-name';
        name.textContent = (agent.name || 'unnamed') + (notReadySuffix ? ' ' + notReadySuffix : '');
        row.appendChild(name);

        const desc = document.createElement('span');
        desc.className = 'agent-desc';
        desc.textContent = firstSentence(agent.what_i_am_for);
        desc.title = agent.what_i_am_for || ''; // full text on hover, free of charge
        row.appendChild(desc);

        body.appendChild(row);
      });
    }

    head.addEventListener('click', function () {
      item.classList.toggle('open');
    });

    item.appendChild(head);
    item.appendChild(body);
    return item;
  }

  async function loadFleet() {
    const list = byId('agents-list');
    const countEl = byId('agents-count');
    if (!list) return;

    let data;
    try {
      const res = await fetch(FLEET_ENDPOINT);
      if (!res.ok) throw new Error('answered ' + res.status);
      data = await res.json();
    } catch (err) {
      list.innerHTML = '';
      const empty = document.createElement('div');
      empty.className = 'agents-empty';
      empty.textContent = 'the fleet could not be reached — Data unavailable';
      list.appendChild(empty);
      if (countEl) countEl.textContent = '—';
      return;
    }

    list.innerHTML = '';
    let readyCount = 0;

    const sections = Array.isArray(data && data.sections) ? data.sections : [];
    sections.forEach(function (section) {
      (section.agents || []).forEach(function (agent) {
        if (!NOT_READY[agent.state]) readyCount += 1;
      });
      list.appendChild(buildSection(section));
    });

    if (countEl) countEl.textContent = readyCount + ' ready';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadFleet);
  } else {
    loadFleet();
  }
})();