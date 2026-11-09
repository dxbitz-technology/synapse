/*! synapse-ui 0.1.0 | zero-dependency dashboard kit for Frappe custom frontends | Dxbitz (from bitz-ui 0.1.0) */
(function (G) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const BZ = { version: '0.1.0', locale: 'en-US', currency: 'AED' };

  /* ---------------------------------------------------------------- dom helpers */
  function set(e, a) {
    if (!a) return;
    for (const k in a) {
      const v = a[k];
      if (v == null || v === false) continue;
      if (k === 'style' && typeof v === 'object') {
        for (const s in v) s.startsWith('--') ? e.style.setProperty(s, v[s]) : (e.style[s] = v[s]);
      } else if (k === 'html') e.innerHTML = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    }
  }
  function add(e, kids) {
    kids.flat(9).forEach(k => { if (k != null && k !== false && k !== '') e.append(k.nodeType ? k : String(k)); });
  }
  function h(tag, a, ...kids) { const e = document.createElement(tag); set(e, a); add(e, kids); return e; }
  function sv(tag, a, ...kids) { const e = document.createElementNS(NS, tag); set(e, a); add(e, kids); return e; }
  const q = el => (typeof el === 'string' ? document.querySelector(el) : el);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const textW = s => String(s).length * 6.3; // ~11px Inter
  const trunc = (s, px) => { s = String(s); const n = Math.max(3, Math.floor(px / 6.3)); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };

  const ICON = {
    more: '<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><circle cx="3.5" cy="8" r="1.3"/><circle cx="8" cy="8" r="1.3"/><circle cx="12.5" cy="8" r="1.3"/></svg>',
    chev: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>',
    refresh: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2.5v3h-3"/></svg>',
    filter: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2.5 4h11M4.5 8h7M6.5 12h3"/></svg>',
    up: '<svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 10V2M2.5 5.5L6 2l3.5 3.5"/></svg>',
    down: '<svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2v8M2.5 6.5L6 10l3.5-3.5"/></svg>',
    sun: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="8" r="3"/><path d="M8 1.5V3M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/></svg>',
    moon: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z"/></svg>',
    auto: '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="5.5"/><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor" stroke="none"/></svg>',
    panel: '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2" y="2.5" width="12" height="11" rx="2"/><path d="M6 2.5v11"/></svg>',
    chart: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M3 13V8M8 13V3M13 13V6"/></svg>',
    table: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="M2 6.5h12M2 10h12M6 6.5v7"/></svg>',
    download: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.5v8M4.5 7L8 10.5 11.5 7M3 13.5h10"/></svg>'
  };
  const icon = name => h('span', { class: 'bz-ico', html: ICON[name] });

  /* ---------------------------------------------------------------- formatting */
  const NFC = {};
  const NF = o => { const k = BZ.locale + JSON.stringify(o); return NFC[k] || (NFC[k] = new Intl.NumberFormat(BZ.locale, o)); };
  function fmt(v, f) {
    if (typeof f === 'function') return f(v);
    if (v == null || v === '') return '';
    const [t, arg] = String(f || 'number').split(':');
    if (t === 'date' || t === 'datetime') { const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?/); return m ? `${m[3]}-${m[2]}-${m[1]}` + (t === 'datetime' && m[4] ? ' ' + m[4] : '') : String(v); }
    if (t === 'check') return +v ? '\u2713' : '';
    if (t === 'text' || (typeof v !== 'number' && isNaN(v))) return String(v);
    v = +v;
    switch (t) {
      case 'currency': return NF({ style: 'currency', currency: arg || BZ.currency, maximumFractionDigits: Math.abs(v) >= 1000 ? 0 : 2 }).format(v);
      case 'ccompact': return (arg || BZ.currency) + ' ' + NF({ notation: 'compact', maximumFractionDigits: 1 }).format(v);
      case 'compact': return NF({ notation: 'compact', maximumFractionDigits: 1 }).format(v);
      case 'percent': return NF({ maximumFractionDigits: arg ? +arg : 1 }).format(v) + '%';
      case 'int': return NF({ maximumFractionDigits: 0 }).format(Math.round(v));
      default: return NF({ maximumFractionDigits: arg ? +arg : 2 }).format(v);
    }
  }
  const axisFmt = f => (typeof f === 'function' ? f : /^percent/.test(f || '') ? 'percent:0' : 'compact');

  function nice(lo, hi, count) {
    if (lo === hi) { hi = lo + 1; lo = Math.min(lo, 0); }
    let step = Math.pow(10, Math.floor(Math.log10((hi - lo) / count)));
    const err = (hi - lo) / count / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    const out = [];
    for (let v = Math.floor(lo / step) * step; v <= Math.ceil(hi / step) * step + step / 2; v += step) out.push(+v.toFixed(10));
    return out;
  }

  /* ---------------------------------------------------------------- data normalising
     Accepted shapes (all become {labels, sets:[{name, values, ci}]}):
       [10, 20, 30]                                   + opts.labels
       {Paid: 10, Unpaid: 4}                          single series keyed by label
       {labels: [...], values: [...]}
       {labels: [...], series: {Sales: [...], Cost: [...]}}
       {labels: [...], datasets: [{name, values}]}    frappe-charts shape
       [{month: 'Jan', sales: 10, cost: 4}, ...]      rows, e.g. frappe.db.sql(as_dict=1)
       [['Jan', 10, 4], ['Feb', 12, 5]]               rows as arrays, names from opts.series */
  function norm(d, o) {
    o = o || {};
    const mk = (labels, sets) => ({ labels: labels.map(String), sets: sets.map((s, i) => ({ name: s.name == null ? '' : String(s.name), values: s.values.map(v => (v == null || v === '' ? null : +v)), ci: i })) });
    if (d == null) return mk([], []);
    if (Array.isArray(d)) {
      if (!d.length) return mk([], []);
      if (Array.isArray(d[0])) {
        const names = o.series || d[0].slice(1).map((_, i) => 'Series ' + (i + 1));
        return mk(d.map(r => r[0]), names.map((n, i) => ({ name: n, values: d.map(r => r[i + 1]) })));
      }
      if (typeof d[0] === 'object') {
        const keys = Object.keys(d[0]);
        const lk = o.labelKey || keys.find(k => typeof d[0][k] === 'string') || keys[0];
        const vk = o.valueKeys || keys.filter(k => k !== lk && !isNaN(parseFloat(d[0][k])));
        return mk(d.map(r => r[lk]), vk.map(k => ({ name: (o.seriesNames || {})[k] || title(k), values: d.map(r => r[k]) })));
      }
      return mk(o.labels || d.map((_, i) => i + 1), [{ name: o.name || '', values: d }]);
    }
    if (d.datasets) return mk(d.labels, d.datasets);
    if (d.series) return mk(d.labels, Object.keys(d.series).map(k => ({ name: k, values: d.series[k] })));
    if (d.labels && d.values) return mk(d.labels, [{ name: o.name || '', values: d.values }]);
    const keys = Object.keys(d);
    if (keys.length && Array.isArray(d[keys[0]])) return mk(o.labels || d[keys[0]].map((_, i) => i + 1), keys.map(k => ({ name: k, values: d[k] })));
    return mk(keys, [{ name: o.name || '', values: keys.map(k => d[k]) }]);
  }
  const title = k => String(k).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // fold anything past `max` slices into "Other" (palette never cycles)
  function fold(labels, values, max) {
    const idx = values.map((v, i) => i).sort((a, b) => values[b] - values[a]);
    if (labels.length <= max) return { labels, values };
    const keep = idx.slice(0, max - 1).sort((a, b) => a - b);
    const other = idx.slice(max - 1).reduce((s, i) => s + (values[i] || 0), 0);
    return { labels: keep.map(i => labels[i]).concat('Other'), values: keep.map(i => values[i]).concat(other) };
  }
  const col = (i, o) => (o.colors && o.colors[i]) || `var(--bz-c${(i % 8) + 1})`;

  /* ---------------------------------------------------------------- tooltip + menu */
  let tipEl;
  function tip(html, ev) {
    if (!tipEl) document.body.append((tipEl = h('div', { class: 'bz-tip', role: 'tooltip' })));
    if (html == null) { tipEl.style.opacity = 0; return; }
    tipEl.innerHTML = html;
    tipEl.style.opacity = 1;
    const r = tipEl.getBoundingClientRect(), p = 14;
    let x = ev.clientX + p, y = ev.clientY + p;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - p;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - p;
    tipEl.style.transform = `translate(${Math.max(4, x)}px,${Math.max(4, y)}px)`;
  }
  const trow = (c, name, val) => `<div class="bz-tip-row">${c ? `<i style="background:${c}"></i>` : '<i></i>'}<span>${esc(name)}</span><b>${esc(val)}</b></div>`;

  let menuEl;
  function closeMenu() { if (menuEl) { menuEl.remove(); menuEl = null; document.removeEventListener('pointerdown', outside, true); } }
  function outside(e) { if (menuEl && !menuEl.contains(e.target)) closeMenu(); }
  function menu(anchor, items) {
    closeMenu();
    menuEl = h('div', { class: 'bz-menu', role: 'menu' }, items.map(it =>
      h('button', { class: 'bz-menu-item' + (it.danger ? ' bz-danger' : ''), type: 'button', onclick: e => { closeMenu(); it.onClick(e); } }, it.label)));
    document.body.append(menuEl);
    const r = anchor.getBoundingClientRect(), m = menuEl.getBoundingClientRect();
    menuEl.style.left = clamp(r.right - m.width, 8, innerWidth - m.width - 8) + 'px';
    menuEl.style.top = (r.bottom + m.height + 8 > innerHeight ? r.top - m.height - 4 : r.bottom + 4) + 'px';
    setTimeout(() => document.addEventListener('pointerdown', outside, true));
  }
  addEventListener('scroll', closeMenu, true);

  /* ---------------------------------------------------------------- theme */
  function theme(mode) { // 'light' | 'dark' | 'auto'; no argument = read
    const r = document.documentElement;
    if (mode === undefined) return store.get('bz:theme') || r.getAttribute('data-theme') || 'auto';
    mode === 'auto' ? r.removeAttribute('data-theme') : r.setAttribute('data-theme', mode);
    store.set('bz:theme', mode);
    if (BZ.frappeTheme !== false && G.frappe && G.frappe.boot) call('frappe.core.doctype.user.user.switch_theme', { theme: mode === 'auto' ? 'Automatic' : mode[0].toUpperCase() + mode.slice(1) }).catch(() => {});
    dispatchEvent(new CustomEvent('bz:theme', { detail: mode }));
    return mode;
  }
  // segmented switch: light / dark / auto, icon only
  function themeButton() {
    const opts = [['light', 'sun', 'Light'], ['dark', 'moon', 'Dark'], ['auto', 'auto', 'System']];
    const wrap = h('div', { class: 'bz-theme', role: 'radiogroup', 'aria-label': 'Theme' });
    const paint = () => { const cur = theme(); [...wrap.children].forEach((b, i) => { const on = opts[i][0] === cur; b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); }); };
    opts.forEach(([v, ic, l]) => wrap.append(h('button', { type: 'button', role: 'radio', title: l, 'aria-label': l, html: ICON[ic], onclick: () => theme(v) })));
    paint();
    addEventListener('bz:theme', paint);
    return wrap;
  }
  { const s = store.get('bz:theme'); if (s && s !== 'auto' && !document.documentElement.hasAttribute('data-theme')) document.documentElement.setAttribute('data-theme', s); }

  // group rows by a key or function, keeping first-seen order
  // groupBy may be a key, a function, or a list of either for groups inside groups
  const levels = by => (by == null || by === '' ? [] : Array.isArray(by) ? by.filter(b => b != null && b !== '') : [by]);
  // collapsed: true (all), false (none), or a number = levels from that depth start closed (1 keeps the top level open)
  const startClosed = (collapsed, level) => (typeof collapsed === 'number' ? level >= collapsed : !!collapsed);
  function groups(rows, by) {
    const f = typeof by === 'function' ? by : r => r[by], m = new Map();
    rows.forEach(r => { const k = f(r), key = k == null || k === '' ? '(Not set)' : String(k); m.has(key) || m.set(key, []); m.get(key).push(r); });
    return [...m].map(([key, rows]) => ({ key, rows }));
  }

  /* ---------------------------------------------------------------- chart shell */
  const CHARTS = {};
  function chart(el, opts) {
    el = q(el);
    const o = Object.assign({ type: 'bar', height: 240 }, opts);
    const root = h('div', { class: 'bz-chart' });
    el.replaceChildren(root);
    let data, lastW = 0;
    const hidden = new Set();
    function draw() {
      if (!data) return;
      const W = (lastW = root.clientWidth || 320);
      root.replaceChildren();
      const fn = CHARTS[o.type];
      if (!fn) return root.append(h('div', { class: 'bz-empty', text: 'Unknown chart type: ' + o.type }));
      if (!data.labels.length || !data.sets.length) return root.append(h('div', { class: 'bz-empty', text: o.empty || 'No data' }));
      const d = { labels: data.labels, sets: data.sets.filter(s => !hidden.has(s.ci)), all: data.sets };
      fn(root, d, o, W, ci => { hidden.has(ci) ? hidden.delete(ci) : hidden.add(ci); if (hidden.size >= data.sets.length) hidden.delete(ci); draw(); }, hidden);
    }
    const ro = new ResizeObserver(() => { if (Math.abs((root.clientWidth || 0) - lastW) > 2) draw(); });
    ro.observe(root);
    const api = {
      el: root,
      update(d, more) { if (more) Object.assign(o, more); data = norm(d, o); draw(); return api; },
      destroy() { ro.disconnect(); el.replaceChildren(); }
    };
    if (o.data != null) api.update(o.data);
    return api;
  }

  function legend(d, o, toggle, hidden) {
    if (d.all.length < 2 || o.legend === false) return null;
    return h('div', { class: 'bz-legend' }, d.all.map(s => h('button', {
      type: 'button', class: 'bz-leg' + (hidden.has(s.ci) ? ' off' : ''), onclick: () => toggle(s.ci)
    }, h('i', { style: { background: col(s.ci, o) } }), s.name)));
  }

  // bar with 4px rounded data-end, square at the baseline. a = cross start, w = thickness, p0 base px, p1 end px
  function rbar(hz, a, w, p0, p1, r) {
    const d = p1 >= p0 ? 1 : -1;
    r = Math.min(r, Math.abs(p1 - p0), w / 2);
    const P = (u, v) => (hz ? `${u.toFixed(1)},${v.toFixed(1)}` : `${v.toFixed(1)},${u.toFixed(1)}`);
    return `M${P(p0, a)}L${P(p1 - d * r, a)}Q${P(p1, a)} ${P(p1, a + r)}L${P(p1, a + w - r)}Q${P(p1, a + w)} ${P(p1 - d * r, a + w)}L${P(p0, a + w)}Z`;
  }

  function linePath(pts, smooth) {
    let d = '', prev = null;
    pts.forEach(p => {
      if (!p) { prev = null; return; }
      if (!prev) d += `M${p[0].toFixed(1)},${p[1].toFixed(1)}`;
      else if (smooth) { const xm = (prev[0] + p[0]) / 2; d += `C${xm.toFixed(1)},${prev[1].toFixed(1)} ${xm.toFixed(1)},${p[1].toFixed(1)} ${p[0].toFixed(1)},${p[1].toFixed(1)}`; }
      else d += `L${p[0].toFixed(1)},${p[1].toFixed(1)}`;
      prev = p;
    });
    return d;
  }

  /* ---------------------------------------------------------------- bar / line / dot */
  function cartesian(root, d, o, W, toggle, hidden) {
    const type = o.type === 'area' ? 'line' : o.type, area = o.type === 'area' || o.area;
    const hz = !!o.horizontal && type !== 'line', st = !!o.stacked;
    const L = d.labels, S = d.sets, n = L.length, m = S.length, H = o.height;
    let lo = 0, hi = 0;
    if (st && type !== 'dot') {
      for (let i = 0; i < n; i++) {
        let p = 0, ng = 0;
        S.forEach(s => { const v = s.values[i] || 0; v >= 0 ? (p += v) : (ng += v); });
        hi = Math.max(hi, p); lo = Math.min(lo, ng);
      }
    } else {
      const all = S.flatMap(s => s.values.filter(v => v != null && isFinite(v)));
      lo = Math.min(...all); hi = Math.max(...all);
      if (type === 'bar' || o.zero !== false) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    }
    const ticks = nice(lo, hi, hz ? clamp(Math.floor(W / 100), 2, 6) : clamp(Math.floor(H / 50), 2, 6));
    const v0 = ticks[0], v1 = ticks[ticks.length - 1], af = o.axisFormat || axisFmt(o.format);
    const catW = Math.min(o.labelWidth || 120, W * 0.32, Math.max(...L.map(textW)));
    const lab = o.values && (m === 1 || st);
    const M = { t: 8, r: hz ? (lab ? 56 : 16) : 8, b: 24, l: hz ? catW + 12 : Math.max(...ticks.map(t => textW(fmt(t, af)))) + 10 };
    if (lab && !hz) M.t = 22;
    const pw = Math.max(20, W - M.l - M.r), ph = Math.max(20, H - M.t - M.b);
    const band = (hz ? ph : pw) / n;
    const vs = v => (hz ? M.l + ((v - v0) / (v1 - v0)) * pw : M.t + ph - ((v - v0) / (v1 - v0)) * ph);
    const cs = i => (hz ? M.t : M.l) + band * i;
    const svg = sv('svg', { class: 'bz-svg', width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.title || type + ' chart' });

    // axis + grid
    const ax = sv('g', { class: 'bz-axis' });
    ticks.forEach(t => {
      const p = vs(t), cls = t === 0 ? 'bz-zero' : '';
      if (hz) ax.append(sv('line', { x1: p, x2: p, y1: M.t, y2: M.t + ph, class: cls }), sv('text', { x: p, y: H - 6, 'text-anchor': 'middle' }, fmt(t, af)));
      else ax.append(sv('line', { x1: M.l, x2: M.l + pw, y1: p, y2: p, class: cls }), sv('text', { x: M.l - 8, y: p + 4, 'text-anchor': 'end' }, fmt(t, af)));
    });
    const lw = Math.min(90, Math.max(...L.map(textW)));
    const k = hz ? Math.max(1, Math.ceil((n * 16) / ph)) : Math.max(1, Math.ceil((n * (lw + 12)) / pw));
    L.forEach((l, i) => {
      if (i % k) return;
      const c = cs(i) + band / 2;
      ax.append(hz ? sv('text', { x: M.l - 8, y: c + 4, 'text-anchor': 'end' }, trunc(l, catW))
        : sv('text', { x: c, y: H - 6, 'text-anchor': 'middle' }, trunc(l, band * k - 6)));
    });
    svg.append(ax);

    const hov = sv('rect', { class: type === 'line' ? 'bz-cross' : 'bz-band', opacity: 0 });
    svg.append(hov);
    const mk = sv('g');
    const zero = vs(clamp(0, v0, v1));

    if (type === 'bar') {
      const th = st ? Math.min(o.barWidth || 24, band * 0.62) : Math.min(o.barWidth || 24, (band * 0.72) / m);
      const gap = st ? 0 : Math.min(2, th * 0.15);
      for (let i = 0; i < n; i++) {
        let ap = 0, an = 0, tot = 0;
        const c0 = cs(i) + band / 2 - (st ? th / 2 : (th * m + gap * (m - 1)) / 2);
        S.forEach((s, j) => {
          const v = s.values[i] || 0;
          tot += v;
          if (!v) return;
          let a = 0, b = v;
          if (st) { a = v >= 0 ? ap : an; b = a + v; v >= 0 ? (ap = b) : (an = b); }
          let p0 = vs(a), p1 = vs(b);
          const top = !st || !S.slice(j + 1).some(t => (t.values[i] || 0) * v > 0);
          if (!top) p1 -= Math.sign(p1 - p0) * Math.min(2, Math.abs(p1 - p0) / 2);
          mk.append(sv('path', { d: rbar(hz, st ? c0 : c0 + j * (th + gap), th, p0, p1, top ? 4 : 0), style: { fill: col(s.ci, o) } }));
          if (lab && !st) mk.append(vlabel(hz, c0 + j * (th + gap) + th / 2, p1, v, o));
        });
        if (lab && st) mk.append(vlabel(hz, cs(i) + band / 2, vs(tot >= 0 ? ap : an), tot, o));
      }
    }

    if (type === 'line') {
      const acc = new Array(n).fill(0);
      const pts = S.map(s => s.values.map((v, i) => {
        if (st) { acc[i] += v || 0; v = acc[i]; } else if (v == null || !isFinite(v)) return null;
        return [cs(i) + band / 2, vs(v)];
      }));
      pts.forEach((P, j) => {
        const c = col(S[j].ci, o);
        if (st || (area && (j === 0 || o.areaAll))) {
          const below = st && j ? pts[j - 1] : P.map(p => p && [p[0], zero]);
          const segs = [];
          let cur = [];
          P.forEach((p, i) => { if (p) cur.push(i); else if (cur.length) { segs.push(cur); cur = []; } });
          if (cur.length) segs.push(cur);
          segs.forEach(sg => {
            const top = sg.map(i => P[i]), bot = sg.map(i => below[i]).reverse();
            mk.append(sv('path', { class: 'bz-area', d: linePath(top, o.smooth) + 'L' + bot.map(p => p.join(',')).join('L') + 'Z', style: { fill: c } }));
          });
        }
        mk.append(sv('path', { class: 'bz-line', d: linePath(P, o.smooth), style: { stroke: c } }));
        const dots = n <= 24 ? P : [P.filter(Boolean).pop()];
        dots.forEach(p => p && mk.append(sv('circle', { class: 'bz-pt', cx: p[0], cy: p[1], r: n <= 24 ? 3.5 : 4, style: { fill: c } })));
      });
    }

    if (type === 'dot') {
      const off = Math.min(12, (band * 0.7) / m);
      for (let i = 0; i < n; i++) {
        const c = cs(i) + band / 2;
        const vals = S.map(s => s.values[i]).filter(v => v != null && isFinite(v));
        const P = (u, v) => (hz ? { x: u, y: v } : { x: v, y: u });
        if (st && vals.length > 1) {
          const a = P(vs(Math.min(...vals)), c), b = P(vs(Math.max(...vals)), c);
          mk.append(sv('line', { class: 'bz-conn', x1: a.x, y1: a.y, x2: b.x, y2: b.y }));
        } else {
          const a = P(hz ? M.l : M.t + ph, c), b = P(hz ? M.l + pw : M.t, c);
          mk.append(sv('line', { class: 'bz-track', x1: a.x, y1: a.y, x2: b.x, y2: b.y }));
        }
        S.forEach((s, j) => {
          const v = s.values[i];
          if (v == null || !isFinite(v)) return;
          const p = P(vs(v), c + (st ? 0 : (j - (m - 1) / 2) * off));
          mk.append(sv('circle', { class: 'bz-pt', cx: p.x, cy: p.y, r: 5, style: { fill: col(s.ci, o) } }));
        });
      }
    }
    svg.append(mk);

    // hover layer: one band per category, tooltip lists every series
    const hit = sv('rect', { x: M.l, y: M.t, width: pw, height: ph, fill: 'transparent', class: 'bz-hit' });
    const at = ev => { const r = svg.getBoundingClientRect(); return clamp(Math.floor(((hz ? ev.clientY - r.top - M.t : ev.clientX - r.left - M.l)) / band), 0, n - 1); };
    hit.addEventListener('pointermove', ev => {
      const i = at(ev), c = cs(i);
      if (type === 'line') set(hov, { x: c + band / 2 - 0.5, y: M.t, width: 1, height: ph, opacity: 1 });
      else set(hov, hz ? { x: M.l, y: c, width: pw, height: band, opacity: 1 } : { x: c, y: M.t, width: band, height: ph, opacity: 1 });
      let tot = 0;
      const rows = S.map(s => { tot += s.values[i] || 0; return trow(col(s.ci, o), s.name || o.name || o.title || 'Value', fmt(s.values[i], o.format)); }).join('');
      tip(`<div class="bz-tip-h">${esc(L[i])}</div>${rows}${st && m > 1 ? trow(null, 'Total', fmt(tot, o.format)) : ''}`, ev);
    });
    hit.addEventListener('pointerleave', () => { hov.setAttribute('opacity', 0); tip(null); });
    if (o.onClick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', ev => { const i = at(ev); o.onClick({ label: L[i], index: i, values: S.map(s => s.values[i]) }); }); }
    svg.append(hit);
    root.append(legend(d, o, toggle, hidden) || '', svg);
  }
  function vlabel(hz, c, p, v, o) {
    return hz ? sv('text', { class: 'bz-vlab', x: p + (v >= 0 ? 6 : -6), y: c + 4, 'text-anchor': v >= 0 ? 'start' : 'end' }, fmt(v, o.labelFormat || axisFmt(o.format)))
      : sv('text', { class: 'bz-vlab', x: c, y: p + (v >= 0 ? -6 : 14), 'text-anchor': 'middle' }, fmt(v, o.labelFormat || axisFmt(o.format)));
  }
  CHARTS.bar = CHARTS.line = CHARTS.area = CHARTS.dot = cartesian;

  /* ---------------------------------------------------------------- pie / donut */
  function pie(root, d, o, W) {
    const f = fold(d.labels, d.sets[0].values.map(v => Math.max(0, v || 0)), o.max || 8);
    const tot = f.values.reduce((a, b) => a + b, 0);
    const wide = W >= 380;
    const size = Math.min(o.height, wide ? W * 0.48 : W, 260);
    const c = size / 2, R = c - 2, r = o.type === 'donut' ? R * (o.inner || 0.64) : 0;
    const svg = sv('svg', { class: 'bz-svg', width: size, height: size, viewBox: `0 0 ${size} ${size}`, role: 'img', 'aria-label': o.title || o.type });
    const g = sv('g', { class: 'bz-slices' });
    const rows = h('div', { class: 'bz-pie-legend' });
    let a = -Math.PI / 2;
    const focus = i => { g.classList.toggle('bz-dim', i != null); [...g.children].forEach((p, j) => p.classList.toggle('on', j === i)); [...rows.children].forEach((x, j) => x.classList.toggle('on', j === i)); };
    f.values.forEach((v, i) => {
      const a2 = a + (tot ? (v / tot) * 2 * Math.PI : 0);
      const pct = tot ? (v / tot) * 100 : 0;
      const p = sv('path', { d: v ? arc(c, R, r, a, a2) : '', style: { fill: col(i, o) } });
      const show = ev => { focus(i); tip(`<div class="bz-tip-h">${esc(f.labels[i])}</div>${trow(col(i, o), fmt(pct, 'percent'), fmt(v, o.format))}`, ev); };
      p.addEventListener('pointermove', show);
      p.addEventListener('pointerleave', () => { focus(null); tip(null); });
      if (o.onClick) p.addEventListener('click', () => o.onClick({ label: f.labels[i], index: i, value: v }));
      g.append(p);
      rows.append(h('div', { class: 'bz-li', onpointerenter: () => focus(i), onpointerleave: () => focus(null) },
        h('i', { style: { background: col(i, o) } }), h('span', { class: 'bz-li-l' }, f.labels[i]),
        h('span', { class: 'bz-li-v' }, fmt(v, o.format)), h('span', { class: 'bz-li-p' }, fmt(pct, 'percent:0'))));
      a = a2;
    });
    svg.append(g);
    if (r) svg.append(sv('text', { class: 'bz-pie-total', x: c, y: c + 2, 'text-anchor': 'middle' }, fmt(tot, o.centerFormat || (/currency/.test(o.format || '') ? 'ccompact' : 'compact'))),
      sv('text', { class: 'bz-pie-sub', x: c, y: c + 20, 'text-anchor': 'middle' }, o.centerLabel || 'Total'));
    root.append(h('div', { class: 'bz-pie' + (wide ? ' wide' : '') }, h('div', { class: 'bz-pie-fig' }, svg), rows));
  }
  function arc(c, R, r, a0, a1) {
    if (a1 - a0 >= 2 * Math.PI - 1e-6) a1 = a0 + 2 * Math.PI - 1e-4;
    const L = a1 - a0 > Math.PI ? 1 : 0;
    const p = (rad, a) => (c + rad * Math.cos(a)).toFixed(2) + ',' + (c + rad * Math.sin(a)).toFixed(2);
    return r ? `M${p(R, a0)}A${R},${R} 0 ${L} 1 ${p(R, a1)}L${p(r, a1)}A${r},${r} 0 ${L} 0 ${p(r, a0)}Z`
      : `M${c},${c}L${p(R, a0)}A${R},${R} 0 ${L} 1 ${p(R, a1)}Z`;
  }
  CHARTS.pie = CHARTS.donut = pie;

  /* ---------------------------------------------------------------- horizontal split bars */
  function split(root, d, o, W, toggle, hidden) {
    let rows, names;
    if (d.all.length === 1) {
      const f = fold(d.labels, d.sets[0].values.map(v => Math.max(0, v || 0)), o.max || 8);
      rows = [{ label: o.rowLabel || '', values: f.values }]; names = f.labels;
    } else {
      names = d.all.map(s => s.name);
      rows = d.labels.map((l, i) => ({ label: l, values: d.all.map(s => (hidden.has(s.ci) ? 0 : Math.max(0, s.values[i] || 0))) }));
    }
    const single = rows.length === 1;
    const wrap = h('div', { class: 'bz-split' + (single ? ' single' : '') });
    rows.forEach(row => {
      const tot = row.values.reduce((a, b) => a + b, 0);
      const bar = h('div', { class: 'bz-split-bar', style: { height: (o.barHeight || (single ? 20 : 10)) + 'px' } });
      row.values.forEach((v, j) => {
        if (!v) return;
        const pct = tot ? (v / tot) * 100 : 0;
        bar.append(h('span', {
          style: { flexGrow: v, background: col(j, o) },
          onpointermove: ev => tip(`<div class="bz-tip-h">${esc(row.label || names[j])}</div>${trow(col(j, o), names[j], fmt(v, o.format) + ' · ' + fmt(pct, 'percent:0'))}`, ev),
          onpointerleave: () => tip(null)
        }));
      });
      wrap.append(h('div', { class: 'bz-split-row' },
        !single || row.label ? h('div', { class: 'bz-split-head' }, h('span', null, row.label), h('b', null, fmt(tot, o.format))) : null, bar));
    });
    if (single) {
      const tot = rows[0].values.reduce((a, b) => a + b, 0);
      wrap.append(h('div', { class: 'bz-pie-legend bz-split-leg' }, names.map((nm, j) => h('div', { class: 'bz-li' },
        h('i', { style: { background: col(j, o) } }), h('span', { class: 'bz-li-l' }, nm),
        h('span', { class: 'bz-li-v' }, fmt(rows[0].values[j], o.format)), h('span', { class: 'bz-li-p' }, fmt(tot ? (rows[0].values[j] / tot) * 100 : 0, 'percent:0'))))));
      root.append(wrap);
    } else root.append(legend(d, o, toggle, hidden) || '', wrap);
  }
  CHARTS.split = split;

  /* ---------------------------------------------------------------- stat card */
  function spark(vals, w, hgt) {
    const v = vals.map(Number), lo = Math.min(...v), hi = Math.max(...v), n = v.length;
    const pts = v.map((x, i) => [(i / Math.max(1, n - 1)) * (w - 4) + 2, hgt - 2 - ((x - lo) / (hi - lo || 1)) * (hgt - 4)]);
    return sv('svg', { class: 'bz-spark', width: w, height: hgt, viewBox: `0 0 ${w} ${hgt}` },
      sv('path', { d: linePath(pts, true), class: 'bz-line' }), sv('circle', { cx: pts[n - 1][0], cy: pts[n - 1][1], r: 2.5, class: 'bz-pt' }));
  }
  function stat(el, o) {
    el = q(el);
    const d = o.delta;
    const good = d == null ? null : o.inverse ? d < 0 : d > 0;
    el.replaceChildren(h('div', { class: 'bz-stat' + (o.onClick ? ' bz-click' : ''), onclick: o.onClick },
      h('div', { class: 'bz-stat-label' }, o.label || o.title),
      h('div', { class: 'bz-stat-row' },
        h('div', { class: 'bz-stat-value' }, fmt(o.value, o.format)),
        o.spark && o.spark.length > 1 ? spark(o.spark, 72, 28) : null),
      d != null || o.hint ? h('div', { class: 'bz-stat-foot' },
        d != null ? h('span', { class: 'bz-delta ' + (d === 0 ? '' : good ? 'good' : 'bad') }, d > 0 ? icon('up') : d < 0 ? icon('down') : '', fmt(Math.abs(d), o.deltaFormat || 'percent')) : null,
        h('span', { class: 'bz-muted' }, o.hint || o.deltaLabel || 'vs previous period')) : null));
  }

  /* ---------------------------------------------------------------- quick list */
  const STATUS = {
    green: /^(paid|completed|complete|active|submitted|approved|delivered|closed|to deliver|enabled|received|success|ok)$/i,
    red: /^(overdue|cancelled|rejected|failed|expired|disabled|lost|error)$/i,
    orange: /^(unpaid|pending|open|to bill|to receive|to deliver and bill|on hold|partly paid|partially paid|due)$/i,
    blue: /^(ordered|in progress|working|quotation|replied|new)$/i
  };
  function pill(s) {
    if (!s) return null;
    const lbl = typeof s === 'string' ? s : s.label;
    const c = (typeof s === 'object' && s.color) || Object.keys(STATUS).find(k => STATUS[k].test(lbl)) || 'gray';
    return h('span', { class: 'bz-pill bz-pill-' + c }, lbl);
  }
  const initials = t => String(t || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase();

  function list(el, o) {
    el = q(el);
    o = Object.assign({ size: 'sm', items: [] }, o);
    const items = o.limit ? o.items.slice(0, o.limit) : o.items;
    const box = h('div', { class: `bz-list bz-list-${o.size}` });
    if (!items.length) box.append(h('div', { class: 'bz-empty', text: o.empty || 'Nothing to show' }));
    const row = it => {
      const acts = (o.actions || []).filter(a => !a.show || a.show(it));
      const prim = o.size === 'lg' ? acts.filter(a => a.primary) : [];
      const rest = acts.filter(a => !prim.includes(a));
      const stop = e => { e.stopPropagation(); e.preventDefault(); };
      const clickable = it.href || o.onClick;
      return h(it.href ? 'a' : 'div', { class: 'bz-row' + (clickable ? ' bz-click' : ''), href: it.href, onclick: o.onClick ? e => o.onClick(it, e) : null },
        o.size === 'lg' ? h('span', { class: 'bz-avatar', style: it.color ? { background: it.color } : null }, it.avatar || initials(it.title)) : null,
        o.size !== 'lg' && it.indicator ? h('i', { class: 'bz-ind bz-pill-' + it.indicator }) : null,
        h('div', { class: 'bz-row-main' }, h('div', { class: 'bz-row-title' }, it.title), it.subtitle ? h('div', { class: 'bz-row-sub' }, it.subtitle) : null),
        pill(it.status),
        it.value != null ? h('div', { class: 'bz-row-val' }, fmt(it.value, it.format || o.format), it.meta ? h('div', { class: 'bz-row-sub' }, it.meta) : null) : null,
        prim.map(a => h('button', { type: 'button', class: 'bz-btn bz-btn-sm', onclick: e => { stop(e); a.onClick(it, e); } }, a.label)),
        rest.length ? h('button', { type: 'button', class: 'bz-icon-btn', 'aria-label': 'Actions', html: ICON.more, onclick: e => { stop(e); menu(e.currentTarget, rest.map(a => ({ label: a.label, danger: a.danger, onClick: ev => a.onClick(it, ev) }))); } }) : null);
    };
    const keys = levels(o.groupBy);
    const nest = (rows, level) => groups(rows, keys[level]).map(g => {
      const closed = startClosed(o.collapsed, level);
      const wrap = h('div', { class: 'bz-grp bz-grp-l' + level + (closed ? ' collapsed' : ''), style: { '--lvl': level } });
      const sum = g.rows.reduce((s, r) => s + (+r.value || 0), 0);
      wrap.append(h('button', { type: 'button', class: 'bz-grp-h', 'aria-expanded': String(!closed), onclick: e => e.currentTarget.setAttribute('aria-expanded', String(!wrap.classList.toggle('collapsed'))) },
        h('span', { class: 'bz-chev', html: ICON.chev }), h('span', null, g.key), h('span', { class: 'bz-grp-n' }, g.rows.length),
        g.rows.some(r => r.value != null) ? h('span', { class: 'bz-grp-v' }, fmt(sum, o.format)) : null),
        h('div', { class: 'bz-grp-b' }, level + 1 < keys.length ? nest(g.rows, level + 1) : g.rows.map(it => row(it))));
      return wrap;
    });
    if (keys.length) box.append(...nest(items, 0));
    else items.forEach(it => box.append(row(it)));
    if (o.more) box.append(h('a', { class: 'bz-list-more', href: o.more.href || '#', onclick: o.more.onClick }, o.more.label || 'View all'));
    el.replaceChildren(box);
  }

  /* ---------------------------------------------------------------- table (report view)
     columns: Frappe report columns ({fieldname, label, fieldtype, options, width}), or 'Label:Currency:120' strings,
     or {key, label, format, align, type: 'status', link(v, row), total}. rows: dicts or arrays. */
  const FT = { Currency: 'currency', Float: 'number', Int: 'int', Percent: 'percent', Date: 'date', Datetime: 'datetime', Check: 'check' };
  const NUM = /^(currency|ccompact|compact|number|int|percent)/;
  const scrub = s => String(s).trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
  function columns(c, rows) {
    const r0 = rows[0] || {};
    if (!c || !c.length) c = Array.isArray(r0) ? r0.map((_, i) => 'Column ' + (i + 1)) : Object.keys(r0);
    return c.map(x => {
      if (typeof x === 'string') {
        if (!x.includes(':')) x = Array.isArray(r0) ? { label: x } : { key: x };
        else { const [label, ft, width] = x.split(':'), [fieldtype, options] = (ft || '').split('/'); x = { label, fieldtype, options, width }; }
      }
      const key = x.fieldname || x.key || scrub(x.label);
      return { key, label: x.label || title(key), format: x.format || FT[x.fieldtype], width: x.width, align: x.align, total: x.total,
        status: x.type === 'status' || key === 'status',
        link: x.link || (x.fieldtype === 'Link' && x.options ? v => '/app/' + scrub(x.options).replace(/_/g, '-') + '/' + encodeURIComponent(v) : null) };
    });
  }
  function table(el, o) {
    el = q(el);
    o = Object.assign({ search: true, totals: true, pageSize: 200, export: true }, o);
    const raw = o.rows || [], C = columns(o.columns, raw);
    const R = raw.map(r => (Array.isArray(r) ? Object.fromEntries(C.map((c, i) => [c.key, r[i]])) : r));
    C.forEach(c => {
      if (!c.format) { const s = R.find(r => r[c.key] != null); if (s && typeof s[c.key] === 'number') c.format = 'number'; }
      c.num = NUM.test(c.format || '');
      c.r = (c.align || (c.num ? 'right' : 'left')) === 'right' ? 'r' : null;
      c.sum = Array.isArray(o.totals) ? o.totals.includes(c.key) : c.total != null ? c.total : c.num && !/^percent/.test(c.format);
    });
    const open = {};
    let V = C; // visible columns (group column is hidden while grouped)
    let sortK = o.sortBy, dir = o.sortDir === 'desc' ? -1 : 1, term = '', limit = o.pageSize, t;
    const visible = () => {
      const rows = term ? R.filter(r => C.some(c => String(r[c.key] ?? '').toLowerCase().includes(term))) : R.slice();
      const c = C.find(x => x.key === sortK);
      if (c) rows.sort((a, b) => dir * (c.num ? (+a[c.key] || 0) - (+b[c.key] || 0) : String(a[c.key] ?? '').localeCompare(String(b[c.key] ?? ''), undefined, { numeric: true })));
      return rows;
    };
    const sums = rows => V.map(c => (o.totals && c.sum ? rows.reduce((s, r) => s + (+r[c.key] || 0), 0) : null));
    const rowEl = r => h('tr', { class: o.onClick ? 'bz-click' : null, onclick: o.onClick ? e => o.onClick(r, e) : null }, V.map(c => {
      const v = r[c.key];
      return h('td', { class: c.r, title: typeof v === 'string' && v.length > 30 ? v : null },
        c.status ? pill(v) : c.link && v ? h('a', { class: 'bz-tlink', href: c.link(v, r), onclick: e => e.stopPropagation() }, fmt(v, c.format || 'text')) : fmt(v, c.format || 'text'));
    }));
    const scroll = h('div', { class: 'bz-tscroll', style: o.maxHeight ? { maxHeight: o.maxHeight } : null });
    const count = h('span', { class: 'bz-count' });
    const more = h('button', { type: 'button', class: 'bz-btn bz-btn-sm bz-tmore', onclick: () => { limit += o.pageSize; draw(); } });
    const GK = levels(o.groupBy);
    const paths = (rows, level, base, out) => { groups(rows, GK[level]).forEach(g => { const p = base + '\u0001' + g.key; out.push(p); if (level + 1 < GK.length) paths(g.rows, level + 1, p, out); }); return out; };
    const setAll = v => { paths(R, 0, '', []).forEach(p => (open[p] = v)); draw(); };
    const csv = () => {
      const e = v => { v = v == null ? '' : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
      const text = [C.map(c => e(c.label)).join(',')].concat(visible().map(r => C.map(c => e(r[c.key])).join(','))).join('\n');
      const a = h('a', { href: URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv' })), download: String(o.filename || o.title || 'report').replace(/[^\w-]+/g, '_') + '.csv' });
      document.body.append(a); a.click(); a.remove();
    };
    function draw() {
      const hide = GK.filter(k => typeof k === 'string');
      V = hide.length && C.length > hide.length ? C.filter(c => !hide.includes(c.key)) : C;
      const rows = visible(), body = [];
      const head = h('tr', null, V.map(c => h('th', { class: c.r, style: c.width ? { minWidth: c.width + 'px' } : null, 'aria-sort': sortK === c.key ? (dir > 0 ? 'ascending' : 'descending') : null },
        h('button', { type: 'button', class: 'bz-th', onclick: () => { if (sortK === c.key) dir = -dir; else { sortK = c.key; dir = c.num ? -1 : 1; } draw(); } },
          c.label, h('span', { class: 'bz-sort' }, sortK === c.key ? (dir > 0 ? '↑' : '↓') : '')))));
      if (!rows.length) body.push(h('tbody', null, h('tr', null, h('td', { colspan: V.length, class: 'bz-empty' }, term ? 'No matching rows' : o.empty || 'No data'))));
      else if (GK.length) {
        // One tbody per top group. Deeper groups and rows are indented by level inside it.
        const lines = (list, level, base) => groups(list, GK[level]).flatMap(g => {
          const p = base + '\u0001' + g.key, on = open[p] ?? !startClosed(o.collapsed, level), s = sums(g.rows);
          const head = h('tr', { class: 'bz-grow bz-grow-l' + level + (on ? '' : ' collapsed'), style: { '--lvl': level }, 'aria-expanded': String(on), onclick: () => { open[p] = !on; draw(); } }, V.map((c, i) => (i
            ? h('td', { class: c.r }, s[i] != null ? fmt(s[i], c.format) : '')
            : h('td', { class: 'bz-gcell' }, h('span', { class: 'bz-chev', html: ICON.chev }), g.key, h('span', { class: 'bz-grp-n' }, g.rows.length)))));
          if (!on) return [head];
          return [head, ...(level + 1 < GK.length ? lines(g.rows, level + 1, p) : g.rows.map(r => { const tr = rowEl(r); tr.classList.add('bz-trow-l' + (level + 1)); tr.style.setProperty('--lvl', level + 1); return tr; }))];
        });
        groups(rows, GK[0]).forEach(g => {
          const p = '\u0001' + g.key, on = open[p] ?? !startClosed(o.collapsed, 0);
          // lines() regroups this group's rows by the same key, so it yields this group's header and everything under it
          body.push(h('tbody', { class: 'bz-tgrp' + (on ? '' : ' collapsed') }, lines(g.rows, 0, '')));
        });
      }
      else body.push(h('tbody', null, rows.slice(0, limit).map(rowEl)));
      const tot = rows.length ? sums(rows) : [];
      const foot = tot.some(v => v != null) ? h('tfoot', null, h('tr', null, V.map((c, i) => h('td', { class: c.r }, tot[i] != null ? fmt(tot[i], c.format) : i ? '' : 'Total')))) : null;
      scroll.replaceChildren(h('table', { class: 'bz-table' }, h('thead', null, head), body, foot));
      count.textContent = (rows.length === R.length ? '' : rows.length + ' of ') + R.length + ' rows';
      more.hidden = !!o.groupBy || rows.length <= limit;
      more.textContent = `Show ${Math.min(o.pageSize, rows.length - limit)} more`;
    }
    const bar = h('div', { class: 'bz-tt' },
      o.search ? h('input', { class: 'bz-input', type: 'search', placeholder: 'Search rows', oninput: e => { clearTimeout(t); t = setTimeout(() => { term = e.target.value.trim().toLowerCase(); limit = o.pageSize; draw(); }, 150); } }) : null,
      count,
      o.groupBy ? [h('button', { type: 'button', class: 'bz-btn bz-btn-sm', onclick: () => setAll(true) }, 'Expand all'), h('button', { type: 'button', class: 'bz-btn bz-btn-sm', onclick: () => setAll(false) }, 'Collapse all')] : null,
      o.export ? h('button', { type: 'button', class: 'bz-btn bz-btn-sm', onclick: csv }, icon('download'), 'CSV') : null);
    el.replaceChildren(h('div', { class: 'bz-table-wrap' }, o.toolbar === false ? null : bar, scroll, more));
    draw();
  }

  /* ---------------------------------------------------------------- custom blocks + css */
  const injected = {};
  function css(text, id) {
    id = id || 'bz-css-' + Object.keys(injected).length;
    if (injected[id]) injected[id].textContent = text;
    else document.head.append((injected[id] = h('style', { 'data-bz': id }, text)));
    return id;
  }
  // prefix every selector with `scope`; `:scope` means the block itself; @media/@supports keep working
  function scopeCss(text, scope) {
    return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[{}])\s*([^{}@]+?)\s*\{/g, (m, pre, sel) =>
      /^(from|to|\d+%)/.test(sel) ? m : pre + sel.split(',').map(s => (s.trim().startsWith(':scope') ? scope + s.trim().slice(6) : scope + ' ' + s.trim())).join(',') + '{');
  }
  const tpl = (str, d) => String(str).replace(/\{\{\s*([\w.]+)(?:\s*\|\s*([\w:]+))?\s*\}\}/g, (m, path, f) => {
    const v = path.split('.').reduce((x, k) => (x == null ? x : x[k]), d);
    return esc(f ? fmt(v, f) : v);
  });
  /* opts: {template, render(el, data, opts), css, isolate: 'scoped' (default) | 'shadow' | 'global' | 'none'} */
  let blockSeq = 0;
  function block(el, o, data) {
    el = q(el);
    let host = el;
    const id = o.key || 'b' + ++blockSeq;
    if (o.isolate === 'shadow') {
      const sr = el.shadowRoot || el.attachShadow({ mode: 'open' });
      sr.replaceChildren(h('style', null, ':host{display:block}' + (o.css || '')), (host = h('div', { class: 'bz-block' })));
    } else {
      el.setAttribute('data-bz-block', id);
      el.classList.add('bz-block');
      if (o.css && o.isolate === 'global') css(o.css, 'block-' + id);
      else if (o.css && o.isolate !== 'none') css(scopeCss(o.css, `[data-bz-block="${id}"]`), 'block-' + id);
      else if (o.css) css(o.css, 'block-' + id);
    }
    if (o.render) o.render(host, data, o);
    else host.innerHTML = tpl(o.template || '', data == null ? {} : data);
  }
  const BLOCKS = {};
  function register(type, render) { BLOCKS[type] = render; }

  /* ---------------------------------------------------------------- server call */
  async function call(method, args) {
    if (G.frappe && G.frappe.call) return (await G.frappe.call({ method, args })).message;
    const tok = G.csrf_token || (G.frappe && G.frappe.csrf_token) || '';
    const r = await fetch('/api/method/' + method, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Frappe-CSRF-Token': tok }, body: JSON.stringify(args || {}) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      let msg = j.exception || r.statusText;
      try { msg = JSON.parse(JSON.parse(j._server_messages)[0]).message; } catch (e) { /* keep */ }
      throw new Error(msg);
    }
    return j.message;
  }

  /* ---------------------------------------------------------------- date presets */
  const ymd = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const D = (y, m, d) => new Date(y, m, d);
  const PRESETS = {
    today: ['Today', (t) => [t, t]],
    last_7: ['Last 7 days', (t) => [D(t.getFullYear(), t.getMonth(), t.getDate() - 6), t]],
    last_30: ['Last 30 days', (t) => [D(t.getFullYear(), t.getMonth(), t.getDate() - 29), t]],
    this_month: ['This month', (t) => [D(t.getFullYear(), t.getMonth(), 1), D(t.getFullYear(), t.getMonth() + 1, 0)]],
    last_month: ['Last month', (t) => [D(t.getFullYear(), t.getMonth() - 1, 1), D(t.getFullYear(), t.getMonth(), 0)]],
    this_quarter: ['This quarter', (t) => { const m = t.getMonth() - (t.getMonth() % 3); return [D(t.getFullYear(), m, 1), D(t.getFullYear(), m + 3, 0)]; }],
    last_quarter: ['Last quarter', (t) => { const m = t.getMonth() - (t.getMonth() % 3) - 3; return [D(t.getFullYear(), m, 1), D(t.getFullYear(), m + 3, 0)]; }],
    this_year: ['This year', (t) => [D(t.getFullYear(), 0, 1), D(t.getFullYear(), 11, 31)]],
    last_year: ['Last year', (t) => [D(t.getFullYear() - 1, 0, 1), D(t.getFullYear() - 1, 11, 31)]],
    custom: ['Custom', null]
  };
  const range = name => (PRESETS[name] && PRESETS[name][1] ? PRESETS[name][1](new Date()).map(ymd) : null);

  /* ---------------------------------------------------------------- filters */
  function control(f, val, onChange) {
    const lbl = f.label || title(f.key);
    const opts = (f.options || []).map(x => (typeof x === 'object' ? x : { value: x, label: x }));
    let input;
    switch (f.type) {
      case 'select':
        input = h('select', { class: 'bz-input', onchange: e => onChange(e.target.value) },
          f.required ? null : h('option', { value: '' }, f.placeholder || 'All'),
          opts.map(x => h('option', { value: x.value, selected: String(x.value) === String(val) }, x.label)));
        break;
      case 'segment':
        input = h('div', { class: 'bz-seg', role: 'group' }, opts.map(x => h('button', {
          type: 'button', class: String(x.value) === String(val) ? 'on' : '',
          onclick: e => { [...e.target.parentNode.children].forEach(b => b.classList.toggle('on', b === e.target)); onChange(x.value); }
        }, x.label)));
        break;
      case 'check':
        input = h('label', { class: 'bz-check' }, h('input', { type: 'checkbox', checked: !!+val || val === true, onchange: e => onChange(e.target.checked ? 1 : 0) }), f.checkLabel || lbl);
        break;
      case 'daterange': {
        const preset = Array.isArray(val) ? 'custom' : val || 'this_month';
        const dates = Array.isArray(val) ? val : range(preset);
        const a = h('input', { type: 'date', class: 'bz-input', value: dates[0] }), b = h('input', { type: 'date', class: 'bz-input', value: dates[1] });
        const custom = h('div', { class: 'bz-range', hidden: preset !== 'custom' }, a, b);
        const emit = () => a.value && b.value && onChange([a.value, b.value]);
        a.onchange = b.onchange = emit;
        const keys = f.presets || Object.keys(PRESETS);
        input = h('div', { class: 'bz-daterange' }, h('select', {
          class: 'bz-input', onchange: e => { custom.hidden = e.target.value !== 'custom'; if (e.target.value !== 'custom') onChange(e.target.value); else emit(); }
        }, keys.map(k => h('option', { value: k, selected: k === preset }, PRESETS[k][0]))), custom);
        break;
      }
      case 'link': {
        const id = 'bz-dl-' + f.key;
        const dl = h('datalist', { id });
        let t;
        // suggestions load on focus (empty search) and while typing
        const suggest = (txt, wait) => {
          clearTimeout(t);
          t = setTimeout(async () => {
            const res = f.search ? await f.search(txt) : f.doctype ? await call('frappe.desk.search.search_link', { doctype: f.doctype, txt, page_length: 20 }).catch(() => []) : [];
            dl.replaceChildren(...(res || []).map(r => h('option', { value: r.value || r }, r.description && r.description !== r.value ? r.description : null)));
          }, wait);
        };
        input = h('span', null, h('input', {
          class: 'bz-input', list: id, value: val || '', placeholder: f.placeholder || 'Search ' + lbl, autocomplete: 'off',
          onfocus: e => suggest(e.target.value, 0),
          oninput: e => suggest(e.target.value, 250),
          onchange: e => onChange(e.target.value)
        }), dl);
        break;
      }
      default:
        input = h('input', { class: 'bz-input', type: f.type === 'date' ? 'date' : f.type === 'number' ? 'number' : 'text', value: val == null ? '' : val, placeholder: f.placeholder || '', onchange: e => onChange(e.target.value) });
    }
    return h('div', { class: 'bz-f bz-f-' + (f.type || 'text') }, f.type === 'check' ? null : h('label', { class: 'bz-f-label' }, lbl), input);
  }

  /* ---------------------------------------------------------------- dashboard layout */
  const CHART_TYPES = ['bar', 'line', 'area', 'dot', 'pie', 'donut', 'split'];
  function dashboard(el, o) {
    el = q(el);
    o = Object.assign({ syncUrl: true, autoApply: true, header: true }, o);
    const id = o.id || o.title || 'dash';
    const fdefs = o.filters || [];
    const defaults = {};
    const filters = {};
    const url = new URLSearchParams(location.search);
    fdefs.forEach(f => {
      const dv = typeof f.default === 'function' ? f.default() : f.default;
      defaults[f.key] = dv == null ? (f.type === 'check' ? 0 : f.type === 'daterange' ? 'this_month' : '') : dv;
      let v = defaults[f.key];
      if (o.syncUrl && url.has(f.key)) { v = url.get(f.key); if (f.type === 'daterange' && v.includes(',')) v = v.split(','); }
      filters[f.key] = v;
    });
    // value sent to the server: date ranges always become [from, to]
    const resolved = () => {
      const out = {};
      fdefs.forEach(f => { const v = filters[f.key]; out[f.key] = f.type === 'daterange' && !Array.isArray(v) ? range(v) : v; });
      return out;
    };
    const inst = {}, cards = {};
    let seq = 0, timer;

    const root = h('div', { class: 'bz bz-dash' });
    const fbar = h('div', { class: 'bz-filters' });
    const ftoggle = h('button', { type: 'button', class: 'bz-btn bz-ftoggle', onclick: () => fbar.classList.toggle('open') }, icon('filter'), h('span', null, 'Filters'));
    const head = h('div', { class: 'bz-head' },
      h('div', { class: 'bz-head-t' }, o.title ? h('h1', null, o.title) : null, o.subtitle ? h('p', null, o.subtitle) : null),
      h('div', { class: 'bz-head-a' },
        (o.actions || []).map(a => h('button', { type: 'button', class: 'bz-btn' + (a.primary ? ' bz-btn-primary' : ''), onclick: e => a.onClick(api, e) }, a.label)),
        fdefs.length ? ftoggle : null,
        h('button', { type: 'button', class: 'bz-btn bz-icon-only', title: 'Refresh', 'aria-label': 'Refresh', onclick: () => load() }, icon('refresh')),
        o.themeToggle ? themeButton() : null));

    function drawFilters() {
      fbar.replaceChildren(...fdefs.map(f => control(f, filters[f.key], v => {
        filters[f.key] = v;
        changed();
        if (o.autoApply) { clearTimeout(timer); timer = setTimeout(load, 200); }
      })), h('div', { class: 'bz-f-actions' },
        o.autoApply ? null : h('button', { type: 'button', class: 'bz-btn bz-btn-primary', onclick: () => load() }, 'Apply'),
        h('button', { type: 'button', class: 'bz-link', onclick: () => api.setFilters(defaults) }, 'Reset')));
    }
    function changed() {
      const n = fdefs.filter(f => JSON.stringify(filters[f.key]) !== JSON.stringify(defaults[f.key])).length;
      ftoggle.lastChild.textContent = n ? `Filters (${n})` : 'Filters';
      if (o.syncUrl) {
        const u = new URL(location.href);
        fdefs.forEach(f => { const v = filters[f.key]; JSON.stringify(v) === JSON.stringify(defaults[f.key]) || v === '' ? u.searchParams.delete(f.key) : u.searchParams.set(f.key, Array.isArray(v) ? v.join(',') : v); });
        history.replaceState(history.state, '', u);
      }
    }

    const secs = h('div', { class: 'bz-sections' });
    const redraw = () => Object.values(inst).forEach(i => i.update && i._d !== undefined && i.update(i._d));
    // A section holds widgets and/or child sections. Child sections are indented with a guide line,
    // collapse on their own, and remember their state under the parent's path.
    function section(s, si, level, base) {
      const path = base + (s.key || si);
      const skey = `bz:${id}:${path}`;
      const saved = store.get(skey);
      const collapsed = s.collapsible !== false && (saved != null ? saved === '1' : !!s.collapsed);
      const grid = h('div', { class: 'bz-grid', style: s.gap ? { gap: s.gap + 'px' } : null });
      const sec = h('section', { class: 'bz-sec bz-sec-l' + level + (level ? ' bz-sec-sub' : '') + (collapsed ? ' collapsed' : ''), style: { '--lvl': level } });
      if (s.title) {
        const ht = h('div', { class: 'bz-sec-t' }, h('h2', null, s.title), s.description ? h('p', null, s.description) : null);
        sec.append(s.collapsible === false ? h('div', { class: 'bz-sec-h' }, ht)
          : h('button', { type: 'button', class: 'bz-sec-h', 'aria-expanded': String(!collapsed), onclick: e => {
            const c = sec.classList.toggle('collapsed'); e.currentTarget.setAttribute('aria-expanded', String(!c)); store.set(skey, c ? '1' : '0');
            if (!c) redraw();
          } }, h('span', { class: 'bz-chev', html: ICON.chev }), ht));
      }
      (s.widgets || []).forEach((w, wi) => {
        w.key = w.key || `w${path.replace(/[^\w]/g, '_')}_${wi}`;
        const span = clamp(w.col || 12, 1, 12);
        const md = w.colMd || (span <= 4 ? 6 : 12);
        const body = h('div', { class: 'bz-card-b', style: w.minHeight ? { minHeight: w.minHeight + 'px' } : null });
        const cardActs = (w.actions || []).length ? h('button', { type: 'button', class: 'bz-icon-btn', 'aria-label': 'Widget actions', html: ICON.more, onclick: e => menu(e.currentTarget, w.actions.map(a => ({ label: a.label, onClick: ev => a.onClick(inst[w.key] && inst[w.key]._d, api, ev) }))) }) : null;
        const bare = w.type === 'stat' || w.card === false;
        const card = h('div', { class: 'bz-w bz-card' + (bare ? ' bz-card-stat' : '') + (w.class ? ' ' + w.class : ''), style: { '--col': span, '--md': md }, 'data-key': w.key },
          !bare && (w.title || cardActs) ? h('div', { class: 'bz-card-h' }, h('div', null, h('h3', null, w.title || ''), w.subtitle ? h('p', null, w.subtitle) : null), cardActs) : null, body);
        cards[w.key] = { w, body, card };
        grid.append(card);
      });
      const kids = (s.sections || []).map((c, ci) => section(c, ci, level + 1, path + '/'));
      sec.append(h('div', { class: 'bz-sec-b' }, (s.widgets || []).length ? grid : null, kids.length ? h('div', { class: 'bz-subs' }, kids) : null));
      return sec;
    }
    (o.sections || []).forEach((s, si) => secs.append(section(s, si, 0, '')));

    function renderWidget(key, payload) {
      const { w, body, card } = cards[key];
      card.classList.remove('bz-err');
      let opts = Object.assign({}, w), data = payload;
      if (payload && typeof payload === 'object' && !Array.isArray(payload) && 'data' in payload) { const { data: dd, ...rest } = payload; opts = Object.assign(opts, rest); data = dd; }
      try {
        if (CHART_TYPES.includes(w.type)) {
          if (!inst[key]) inst[key] = chart(body, opts);
          inst[key].update(data, opts);
        } else if (w.type === 'stat') {
          stat(body, Object.assign(opts, data && typeof data === 'object' && !Array.isArray(data) ? data : { value: data }));
          inst[key] = {};
        } else if (w.type === 'table') {
          const rows = Array.isArray(data) ? data : (data && (data.result || data.rows || data.data)) || [];
          table(body, Object.assign(opts, data && data.columns ? { columns: data.columns } : {}, { rows }));
          inst[key] = {};
        } else if (w.type === 'list') {
          list(body, Object.assign(opts, { items: data || [] }));
          inst[key] = {};
        } else {
          const r = w.render || BLOCKS[w.type];
          block(body, Object.assign(opts, r ? { render: r } : {}), data);
          inst[key] = {};
        }
        inst[key]._d = data;
      } catch (e) { fail(key, e); }
    }
    function fail(key, e) {
      const c = cards[key];
      c.card.classList.add('bz-err');
      c.body.replaceChildren(h('div', { class: 'bz-empty' }, 'Could not load: ' + (e && e.message ? e.message : e)));
      if (G.console) console.error('[synapse-ui]', key, e);
    }

    async function load() {
      const my = ++seq;
      root.classList.add('bz-busy');
      const args = resolved();
      if (o.onChange) o.onChange(args, api);
      try {
        const res = o.fetch ? await o.fetch(args, api) : o.method ? await call(o.method, { filters: args }) : o.data || {};
        if (my !== seq) return; // a newer request won
        Object.keys(cards).forEach(k => {
          const w = cards[k].w;
          renderWidget(k, res && k in res ? res[k] : w.data !== undefined ? w.data : null);
        });
      } catch (e) {
        if (my === seq) Object.keys(cards).forEach(k => fail(k, e));
      } finally {
        if (my === seq) root.classList.remove('bz-busy', 'bz-first');
      }
    }

    const api = {
      el: root,
      load, refresh: load,
      getFilters: resolved,
      setFilters(v) { Object.assign(filters, v); drawFilters(); changed(); return load(); },
      widget: key => inst[key],
      setData(key, data) { renderWidget(key, data); },
      destroy() { seq++; Object.values(inst).forEach(i => i && i.destroy && i.destroy()); }
    };

    root.classList.add('bz-first', 'bz-busy');
    root.append(o.header === false ? (fdefs.length ? h('div', { class: 'bz-head bz-head-min' }, h('div'), h('div', { class: 'bz-head-a' }, ftoggle)) : '') : head, fdefs.length ? fbar : '', secs);
    drawFilters();
    changed();
    el.replaceChildren(root);
    load();
    return api;
  }

  /* ---------------------------------------------------------------- report: filters + one full table */
  const TABLE_OPTS = ['columns', 'groupBy', 'collapsed', 'totals', 'sortBy', 'sortDir', 'pageSize', 'search', 'export', 'onClick', 'empty'];
  function report(el, o) {
    const via = o.fetch || (o.report ? f => call('frappe.desk.query_report.run', { report_name: o.report, filters: f }) : o.method ? f => call(o.method, { filters: f }) : null);
    const map = o.mapFilters || (f => f);
    const w = { key: 'table', type: 'table', col: 12, maxHeight: o.maxHeight || 'max(360px, calc(100vh - 230px))', filename: o.title };
    TABLE_OPTS.forEach(k => { if (o[k] !== undefined) w[k] = o[k]; });
    return dashboard(el, Object.assign({}, o, {
      method: null,
      fetch: via ? async (f, api) => ({ table: await via(map(f), api) }) : null,
      data: o.rows ? { table: { columns: o.columns, rows: o.rows } } : undefined,
      sections: [{ key: 'report', collapsible: false, widgets: [Object.assign(w, o.table)] }]
    }));
  }

  /* ---------------------------------------------------------------- app shell: explorer sidebar + views
     items: [{id, title, group, description, keywords, type: 'dashboard' | 'report', ...config}] or async () => items.
     An item may also have load: async item => config, or render: (el, item) => view. */
  function app(el, o) {
    el = q(el);
    o = Object.assign({ title: 'Dashboards', themeToggle: true }, o);
    let items = [], cur = null, view = null, first = true;
    const root = h('div', { class: 'bz bz-app' + (store.get('bz:side') === '0' ? ' side-off' : '') });
    const mobile = () => matchMedia('(max-width: 899px)').matches;
    const toggleSide = () => (mobile() ? root.classList.toggle('side-open') : store.set('bz:side', root.classList.toggle('side-off') ? '0' : '1'));
    const sideBtn = () => h('button', { type: 'button', class: 'bz-btn bz-icon-only', title: 'Toggle sidebar', 'aria-label': 'Toggle sidebar', html: ICON.panel, onclick: toggleSide });
    const nav = h('nav', { class: 'bz-nav' });
    const search = h('input', {
      class: 'bz-input bz-side-search', type: 'search', placeholder: o.searchPlaceholder || 'Search  ( / )', 'aria-label': 'Search dashboards',
      oninput: () => drawNav(),
      onkeydown: e => { if (e.key === 'Enter') { const a = nav.querySelector('.bz-nav-i'); if (a) a.click(); } if (e.key === 'Escape') { search.value = ''; drawNav(); } }
    });
    const main = h('main', { class: 'bz-main' });
    const mainbar = h('div', { class: 'bz-mainbar' }, sideBtn(), h('b', null, o.title));
    // The bar carries the sidebar toggle while the sidebar is hidden, so it is there before any view opens.
    main.append(mainbar);
    function drawNav() {
      const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      const hit = items.filter(it => { const s = [it.title, it.group, it.description, it.keywords].join(' ').toLowerCase(); return words.every(w => s.includes(w)); });
      nav.replaceChildren(...(hit.length ? groups(hit, it => it.group).flatMap(g => [
        g.key === '(Not set)' ? null : h('div', { class: 'bz-nav-g' }, g.key),
        ...g.rows.map(it => h('a', { class: 'bz-nav-i' + (cur && cur.id === it.id ? ' on' : ''), href: '#/' + it.id, title: it.description || it.title },
          icon(it.type === 'report' ? 'table' : 'chart'), h('span', null, it.title)))]).filter(Boolean) : [h('div', { class: 'bz-empty', text: items.length ? 'No matches' : o.emptyNav || 'Nothing here yet' })]));
    }
    async function open(id) {
      const it = items.find(x => x.id === id) || items.find(x => x.id === o.home) || items[0];
      if (!it || (cur === it && view)) return;
      if (!first) history.replaceState(history.state, '', location.pathname + '#/' + it.id); // drop the previous view's filters
      first = false;
      cur = it;
      root.classList.remove('side-open');
      drawNav();
      if (view && view.destroy) view.destroy();
      const host = h('div', { class: 'bz-view' });
      main.replaceChildren(mainbar, host);
      try {
        const cfg = Object.assign({}, it, it.load ? await it.load(it) : null);
        if (cur !== it) return;
        view = cfg.render ? cfg.render(host, cfg) : (cfg.type === 'report' ? report : dashboard)(host, cfg);
      } catch (e) { host.replaceChildren(h('div', { class: 'bz-empty' }, 'Could not open: ' + (e.message || e))); }
      document.title = it.title + (o.title ? ' · ' + o.title : '');
      if (o.onOpen) o.onOpen(it, view);
    }
    const route = () => decodeURIComponent(location.hash.replace(/^#\/?/, ''));
    addEventListener('hashchange', () => open(route()));
    addEventListener('keydown', e => {
      const typing = /INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName);
      if ((e.key === '/' && !typing) || ((e.metaKey || e.ctrlKey) && e.key === 'k')) { e.preventDefault(); if (mobile()) root.classList.add('side-open'); search.focus(); }
    });
    root.append(h('aside', { class: 'bz-side' },
      h('div', { class: 'bz-side-h' }, h('b', null, o.title), o.themeToggle ? themeButton() : null, sideBtn()),
      search, nav, o.footer || null), main, h('div', { class: 'bz-backdrop', onclick: () => root.classList.remove('side-open') }));
    el.replaceChildren(root);
    const api = {
      el: root, open: id => { location.hash = '#/' + id; }, view: () => view, refresh: () => view && view.refresh && view.refresh(),
      // Show a message in place of a view, keeping the sidebar toggle bar.
      message(node) { main.replaceChildren(mainbar, h('div', { class: 'bz-view' }, node)); },
      setItems(list) { items = list.map(x => Object.assign({}, x, { id: x.id || scrub(x.title).replace(/_/g, '-') })); drawNav(); open(route()); }
    };
    Promise.resolve(typeof o.items === 'function' ? o.items() : o.items || []).then(api.setItems);
    return api;
  }

  Object.assign(BZ, { chart, stat, list, table, report, app, block, register, css, scopeCss, dashboard, call, fmt, norm, groups, theme, themeButton, menu, tip, h, range, presets: PRESETS, charts: CHARTS });
  G.SynapseUI = BZ;
  if (typeof module === 'object' && module.exports) module.exports = BZ;
})(typeof window !== 'undefined' ? window : this);
