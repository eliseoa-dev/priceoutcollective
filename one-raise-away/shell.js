// One Raise Away — app shell (router, back-by-one, tabs, header, toast, sheet, delegated taps).
// Every fleet app re-derived this by hand and every harness found the same holes
// (unwired back button / tabs, toast eating taps, replaceState never re-rendering).
// It is now the scaffold's job. Build the app in app.js against these globals:
//
//   FN.<name> = (arg) => …        any element with data-fn="name:arg" calls it on tap
//   go('#/path?x=1')              navigate (pushes ONE level onto the back stack)
//   replace('#/path?x=2')         same view, new query — swaps the top of the stack, no level
//   back()                        pops exactly one level; at a root it stays put
//   setTop({title, back, act, actOn, actLabel, tab, wordmark})   header + active tab
//   toast('Saved')                2.2s status, pointer-events:none so it never eats a tap
//   sheet(html) / closeSheet()    bottom sheet; tapping the scrim closes it
//   render(r)                     YOU define this in app.js: r = {path, q, raw}
//   route(true)                   re-render without touching the stack (call after data changes)
//   TODAY()                       local yyyy-mm-dd (never toISOString — that is UTC)
//
// Roots = the tab bar's data-tab values. Anything else is a level under the current root.
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const FN = {};
  const NAV = { stack: [], popping: false };
  const TABS = () => [...document.querySelectorAll('#tabs [data-tab]')].map((b) => b.dataset.tab);
  const HOME = () => TABS()[0] || '#/home';

  const parseHash = () => {
    const h = location.hash || HOME();
    const [path, qs] = h.split('?');
    const q = {};
    (qs || '').split('&').forEach((kv) => { if (!kv) return; const [k, v] = kv.split('='); q[decodeURIComponent(k)] = decodeURIComponent((v || '').replace(/\+/g, ' ')); });
    return { path, q, raw: h };
  };
  const qs = (o) => { const p = Object.keys(o || {}).filter((k) => o[k] !== '' && o[k] != null).map((k) => encodeURIComponent(k) + '=' + encodeURIComponent(o[k])); return p.length ? '?' + p.join('&') : ''; };
  const rootOf = () => NAV.stack[0] || HOME();
  const go = (h) => { if (h === location.hash) route(true); else location.hash = h; };
  // history.replaceState fires NO hashchange — route yourself or the screen never repaints.
  const replace = (h) => { history.replaceState(null, '', h); route(true); };
  const back = () => {
    if (NAV.stack.length > 1) { NAV.stack.pop(); NAV.popping = true; location.hash = NAV.stack[NAV.stack.length - 1]; }
    else route(true); // already at a root: nothing to pop, stay put
  };
  const route = (isReplace) => {
    if (!location.hash) history.replaceState(null, '', HOME());
    const r = parseHash();
    if (isReplace) { if (NAV.stack.length) NAV.stack[NAV.stack.length - 1] = r.raw; else NAV.stack = [r.raw]; }
    else if (NAV.popping) NAV.popping = false;
    else if (TABS().includes(r.path) || r.path === '#/') NAV.stack = [r.raw];
    else {
      const top = NAV.stack[NAV.stack.length - 1] || '';
      if (top.split('?')[0] === r.path) NAV.stack[NAV.stack.length - 1] = r.raw; // same view, new query ≠ a level
      else NAV.stack.push(r.raw);
    }
    if (typeof window.render === 'function') window.render(r);
    else $('app').innerHTML = '<p style="padding:24px 0;color:var(--dim)">Define <code>render(r)</code> in app.js.</p>';
    closeSheet();
    window.scrollTo(0, 0);
  };

  const setTop = (o) => {
    o = o || {};
    const t = $('topTitle');
    if (o.wordmark || (!o.title && !o.back)) t.innerHTML = '<span class="wordmark">' + (typeof o.wordmark === 'string' ? o.wordmark : t.dataset.name) + '</span>';
    else t.textContent = o.title || '';
    $('backBtn').hidden = !o.back;
    const a = $('topAct');
    a.hidden = !o.act;
    if (o.act) { a.dataset.fn = o.act; a.textContent = o.actLabel || ''; a.setAttribute('aria-label', o.actLabel || 'Action'); a.classList.toggle('on', !!o.actOn); }
    $('top').classList.toggle('line', !!(o.back || (o.title && !o.wordmark)));
    const tab = o.tab || rootOf().split('?')[0];
    document.querySelectorAll('#tabs [data-tab]').forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
  };
  const toast = (m) => { const t = $('toast'); t.textContent = m; t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 2200); };
  const sheet = (html) => { $('sheetIn').innerHTML = '<div class="grab"></div>' + html; $('sheet').classList.add('open'); };
  const closeSheet = () => { const s = $('sheet'); if (!s.classList.contains('open')) return; s.classList.remove('open'); $('sheetIn').innerHTML = ''; };
  const TODAY = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };

  // ONE delegated handler for the whole app. Never add a second listener on the same
  // control (a dedicated #topAct listener + this one fired every header action twice).
  document.addEventListener('click', (e) => {
    const tb = e.target.closest('#tabs [data-tab]');
    if (tb) { e.preventDefault(); go(tb.dataset.tab); return; }
    const t = e.target.closest('[data-fn]');
    if (!t) return;
    const [fn, ...rest] = t.dataset.fn.split(':');
    if (!FN[fn]) return;
    e.preventDefault();
    FN[fn](rest.join(':'), t, e);
  });
  FN.back = back;
  FN.closeSheet = closeSheet;
  document.addEventListener('DOMContentLoaded', () => {
    $('sheet').addEventListener('click', (e) => { if (e.target === $('sheet')) closeSheet(); });
    $('topTitle').dataset.name = $('topTitle').textContent.trim();
    window.addEventListener('hashchange', () => route(false));
    route(true);
  });

  Object.assign(window, { $, FN, NAV, parseHash, qs, rootOf, go, replace, back, route, setTop, toast, sheet, closeSheet, TODAY });
})();
