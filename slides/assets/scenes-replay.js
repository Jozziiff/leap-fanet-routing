/* === SCENE · REPLAY OF THE DEMO RUN (slide 16) ===
   Data: window.REPLAY, written by experiments/replay_export.py from the two recorded demo runs (same seed,
   same traffic and trajectories). Nothing is invented: positions, transmissions and their outcomes, drops,
   deliveries and LEAP-GR's switches are the recorded events.

   Visual language (one meaning per mark):
   - grey lines: the network, every pair of drones within radio range;
   - faint black / blue strokes: frames delivered to the next hop (Greedy / LEAP-GR);
   - red broken link (gap + cross): Greedy keeps sending to a neighbour that has already left;
   - red "lost" badge: the packet is dropped after its 5 attempts (link break);
   - blue arrow + grey dashed line: LEAP-GR switches to a safe neighbour, away from the one about to leave.
   Below the panels, a timeline: red ticks = packets Greedy lost to link breaks, blue ticks = LEAP-GR switches.

   Deck steps: s0 the run plays; s1 everything but breaks and switches fades; s2 a guided moment.
   Controls (mouse): play/pause, speed, click or drag the timeline, moment chips, back to the full run. */
window.SCENES = window.SCENES || {};

SCENES.replay = function (slide) {
  const D = window.REPLAY;
  if (!D) return { enter() {}, step() {}, leave() {} };
  const RMAX = D.r_max_m, TAU = D.tau_th_s;
  const T0 = 2.0, T1 = D.config.sim_time_s; // the replay starts with the traffic (2 s, run_one default)
  const runs = [D.runs.greedy, D.runs.leap];
  const frames = runs[0].frames; // trajectories are identical in both runs (same seed)
  const N = frames[0][1].length;
  const FDT = frames[1][0] - frames[0][0];
  const svgs = [...slide.querySelectorAll('svg.replay')];
  const $ = (q) => slide.querySelector(q);
  const ui = {
    play: $('[data-ui="play"]'), time: $('[data-ui="time"]'), line: $('[data-ui="timeline"]'),
    speeds: [...slide.querySelectorAll('[data-speed]')], moments: $('[data-ui="moments"]'), full: $('[data-ui="full"]'),
    story: $('[data-ui="story"]'), counts: [...slide.querySelectorAll('[data-ui="count"]')],
  };
  const red = KIT.css('--break'), blue = KIT.css('--leap'), ink = KIT.css('--ink'), faint = KIT.css('--faint');

  /* ---------- time helpers ---------- */
  function posAt(t) {
    const f = Math.min(Math.max((t - frames[0][0]) / FDT, 0), frames.length - 1.001);
    const i = Math.floor(f), u = f - i;
    const a = frames[i][1], b = frames[i + 1][1];
    return a.map((p, k) => [p[0] + (b[k][0] - p[0]) * u, 600 - (p[1] + (b[k][1] - p[1]) * u), p[2] + (b[k][2] - p[2]) * u]);
  }
  function upper(arr, t) { // number of items with time <= t (arrays sorted by time)
    let lo = 0, hi = arr.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (arr[m][0] <= t) lo = m + 1; else hi = m; }
    return lo;
  }
  const line = (el, a, b) => { el.setAttribute('x1', a[0]); el.setAttribute('y1', a[1]); el.setAttribute('x2', b[0]); el.setAttribute('y2', b[1]); };

  /* ---------- derived events ---------- */
  function episodes(tx) { // consecutive out-of-range attempts of one packet from one drone to one neighbour
    const map = new Map();
    for (const a of tx) {
      if (a[5] !== 'FAIL_RANGE') continue;
      const key = `${a[1]}:${a[2]}:${a[3]}`;
      const e = map.get(key);
      if (e) { e[1] = a[0]; e[4] += 1; } else map.set(key, [a[0], a[0], a[2], a[3], 1]);
    }
    return [...map.values()].sort((x, y) => x[0] - y[0]); // [t_first, t_last, from, to, attempts]
  }

  /* ---------- build both panels ---------- */
  const P = svgs.map((svg, r) => {
    const g = { svg, run: runs[r], leap: r === 1 };
    g.root = KIT.el('g', {}, svg);
    KIT.el('rect', { x: 0, y: 0, width: 600, height: 600, fill: 'none', stroke: KIT.css('--hair'), 'stroke-width': 2 }, g.root);
    g.links = [];
    for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) g.links.push({ i, j, el: KIT.el('line', { class: 'rl' }, g.root) });
    g.txPool = Array.from({ length: 70 }, () => KIT.el('line', { class: 'rtx ' + (g.leap ? 'leap' : '') }, g.root));
    /* broken links: two red segments with a gap and a cross in the gap */
    g.brk = Array.from({ length: 10 }, () => {
      const b = KIT.el('g', { class: 'rbrk' }, g.root);
      b.a = KIT.el('line', {}, b); b.b = KIT.el('line', {}, b);
      b.x = KIT.el('g', {}, b);
      KIT.el('line', { x1: -8, y1: -8, x2: 8, y2: 8 }, b.x); KIT.el('line', { x1: -8, y1: 8, x2: 8, y2: -8 }, b.x);
      b.style.display = 'none';
      return b;
    });
    /* LEAP switches: dashed grey line to the avoided neighbour, blue arrow to the chosen one */
    g.swp = Array.from({ length: 14 }, () => {
      const s = KIT.el('g', { class: 'rsw' }, g.root);
      s.av = KIT.el('line', { class: 'avoid' }, s);
      s.ar = KIT.arrow(s, 'leap');
      s.style.display = 'none';
      return s;
    });
    g.drones = Array.from({ length: N }, () => KIT.drone(g.root));
    /* lost badges above the drones */
    g.lost = Array.from({ length: 8 }, () => {
      const l = KIT.el('g', { class: 'rlost' }, g.root);
      KIT.el('rect', { x: -34, y: -50, width: 68, height: 26 }, l);
      const t = KIT.text(l, 0, -31, 'lost', 'center white'); t.style.fontWeight = 800; t.style.fontSize = '17px';
      l.style.display = 'none';
      return l;
    });
    g.over = KIT.el('g', {}, svg); // moment annotations
    g.tx = g.run.tx.filter((a) => a[5] === 'OK');
    g.eps = episodes(g.run.tx);
    g.lb = g.run.drops.filter((d) => d[3] === 'LINK_BREAK');
    g.sw = g.run.switches;
    g.dl = g.run.delivered;
    return g;
  });

  /* ---------- timeline: red ticks = Greedy's link-break losses, blue ticks = LEAP-GR switches ---------- */
  const TW = 760, TH = 52;
  const tsvg = KIT.el('svg', { viewBox: `0 -26 ${TW} ${TH + 30}`, width: TW, height: TH + 30 }, ui.line);
  const tx = (t) => ((t - T0) / (T1 - T0)) * TW;
  KIT.el('rect', { x: 0, y: 0, width: TW, height: TH, fill: '#fff', stroke: ink, 'stroke-width': 2 }, tsvg);
  KIT.el('line', { x1: 0, y1: TH / 2, x2: TW, y2: TH / 2, stroke: KIT.css('--hair'), 'stroke-width': 1 }, tsvg);
  P[0].lb.forEach((d) => KIT.el('line', { x1: tx(d[0]), y1: 4, x2: tx(d[0]), y2: TH / 2 - 3, stroke: red, 'stroke-width': 3 }, tsvg));
  P[1].sw.forEach((s) => KIT.el('line', { x1: tx(s[0]), y1: TH / 2 + 3, x2: tx(s[0]), y2: TH - 4, stroke: blue, 'stroke-width': 1.5, opacity: 0.7 }, tsvg));
  D.moments.forEach((m, i) => {
    const g = KIT.el('g', { transform: `translate(${tx(m.greedy_tries[0][0])} 0)` }, tsvg);
    KIT.el('rect', { x: -9, y: -22, width: 18, height: 18, fill: ink }, g);
    const t = KIT.text(g, 0, -8, String(i + 1), 'center white'); t.style.fontSize = '13px'; t.style.fontWeight = 800;
  });
  const head = KIT.el('line', { x1: 0, y1: -4, x2: 0, y2: TH + 4, stroke: ink, 'stroke-width': 3 }, tsvg);
  function seekFromPointer(e) {
    const r = tsvg.getBoundingClientRect();
    const u = Math.min(Math.max((e.clientX - r.left) / (r.width || 1), 0), 1);
    clearMoment();
    S.t = T0 + u * (T1 - T0);
    draw(S.t);
  }
  let dragging = false;
  tsvg.addEventListener('pointerdown', (e) => { dragging = true; seekFromPointer(e); });
  addEventListener('pointermove', (e) => { if (dragging) seekFromPointer(e); });
  addEventListener('pointerup', () => { dragging = false; });

  /* ---------- state and drawing ---------- */
  const S = { t: T0, speed: 0.25, playing: true, moment: null };
  let tl = null;

  function draw(t) {
    const pos = posAt(t);
    for (const g of P) {
      pos.forEach((p, k) => g.drones[k].setAttribute('transform', `translate(${p[0].toFixed(1)} ${p[1].toFixed(1)}) scale(${(0.3 + p[2] / 600).toFixed(3)})`));
      for (const l of g.links) {
        const a = pos[l.i], b = pos[l.j];
        const d = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
        if (d > RMAX) { l.el.style.display = 'none'; continue; }
        l.el.style.display = '';
        line(l.el, a, b);
      }
      /* delivered frames of the last 0.3 s, faint */
      let k = 0;
      for (let n = upper(g.tx, t) - 1; n >= 0 && k < g.txPool.length; n--) {
        const x = g.tx[n], age = t - x[0];
        if (age > 0.3) break;
        const el = g.txPool[k++];
        el.style.display = '';
        line(el, pos[x[2]], pos[x[3]]);
        el.style.opacity = (1 - age / 0.3) * 0.55;
      }
      for (; k < g.txPool.length; k++) g.txPool[k].style.display = 'none';
      /* broken links, held from the first failed attempt until 0.8 s after the last */
      k = 0;
      for (let n = upper(g.eps, t) - 1; n >= 0 && k < g.brk.length; n--) {
        const e = g.eps[n];
        if (t - e[1] > 0.8) { if (t - e[0] > 3) break; continue; }
        const b = g.brk[k++], a = pos[e[2]], c = pos[e[3]];
        const mx = (a[0] + c[0]) / 2, my = (a[1] + c[1]) / 2;
        const dx = c[0] - a[0], dy = c[1] - a[1], L = Math.hypot(dx, dy) || 1, gap = 14;
        b.style.display = '';
        line(b.a, a, [mx - (dx / L) * gap, my - (dy / L) * gap]);
        line(b.b, [mx + (dx / L) * gap, my + (dy / L) * gap], c);
        b.x.setAttribute('transform', `translate(${mx} ${my})`);
        b.style.opacity = t <= e[1] ? 1 : 1 - (t - e[1]) / 0.8;
      }
      for (; k < g.brk.length; k++) g.brk[k].style.display = 'none';
      /* lost badges for 1.5 s after a link-break drop */
      k = 0;
      for (let n = upper(g.lb, t) - 1; n >= 0 && k < g.lost.length; n--) {
        const x = g.lb[n], age = t - x[0];
        if (age > 1.5) break;
        const l = g.lost[k++];
        l.style.display = '';
        l.setAttribute('transform', `translate(${pos[x[2]][0]} ${pos[x[2]][1]})`);
        l.style.opacity = age < 1.1 ? 1 : 1 - (age - 1.1) / 0.4;
      }
      for (; k < g.lost.length; k++) g.lost[k].style.display = 'none';
      /* LEAP-GR switches for 0.9 s */
      k = 0;
      for (let n = upper(g.sw, t) - 1; n >= 0 && k < g.swp.length; n--) {
        const x = g.sw[n], age = t - x[0];
        if (age > 0.9) break;
        const s = g.swp[k++], a = pos[x[2]], to = pos[x[4]];
        s.style.display = '';
        if (x[3] !== null && x[3] !== undefined) { s.av.style.display = ''; line(s.av, a, pos[x[3]]); } else s.av.style.display = 'none';
        const ang = Math.atan2(to[1] - a[1], to[0] - a[0]);
        s.ar.set(a[0] + Math.cos(ang) * 16, a[1] + Math.sin(ang) * 16, to[0] - Math.cos(ang) * 18, to[1] - Math.sin(ang) * 18);
        s.style.opacity = age < 0.6 ? 1 : 1 - (age - 0.6) / 0.3;
      }
      for (; k < g.swp.length; k++) g.swp[k].style.display = 'none';
    }
    P.forEach((g, r) => {
      const c = ui.counts[r];
      c.querySelector('[data-c="dl"]').textContent = upper(g.dl, t);
      c.querySelector('[data-c="lb"]').textContent = upper(g.lb, t);
      const sw = c.querySelector('[data-c="sw"]');
      if (sw) sw.textContent = upper(g.sw, t);
    });
    ui.time.textContent = `t = ${t.toFixed(2)} s`;
    head.setAttribute('transform', `translate(${tx(t)} 0)`);
  }

  function frame() {
    if (S.playing && !S.moment) {
      S.t += gsap.ticker.deltaRatio() * (1 / 60) * S.speed;
      if (S.t > T1) S.t = T0;
    }
    if (!S.moment) draw(S.t);
  }

  /* ---------- guided moments ---------- */
  const layers = (g) => [...g.links.map((l) => l.el), ...g.txPool, ...g.brk, ...g.lost, ...g.swp];
  /* during a moment: the drones of the story stay fully visible, everything else steps back */
  function focusOn(g, ids, tlx) {
    tlx.to(layers(g), { opacity: 0.06, duration: 0.5 }, 0)
      .to(g.drones.filter((_, k) => !ids.has(k)), { opacity: 0.18, duration: 0.5 }, 0)
      .to(g.drones.filter((_, k) => ids.has(k)), { opacity: 1, duration: 0.3 }, 0);
  }
  const fmt = (x, d = 3) => Number(x).toFixed(d);
  function clearMoment() {
    if (tl) tl.kill();
    tl = null;
    S.moment = null;
    P.forEach((g) => {
      g.over.innerHTML = '';
      gsap.set(g.svg, { attr: { viewBox: '0 0 600 600' } });
      gsap.set([...g.drones, ...layers(g)], { opacity: 1 });
    });
    slide.classList.remove('in-moment');
    ui.moments.querySelectorAll('button').forEach((b) => b.classList.remove('on'));
  }

  function playMoment(idx) {
    clearMoment();
    const m = D.moments[idx];
    if (!m) return;
    S.moment = m;
    slide.classList.add('in-moment');
    ui.moments.querySelectorAll('button')[idx]?.classList.add('on');
    const t0 = m.greedy_tries[0][0];
    S.t = t0;
    draw(t0);
    const pos = posAt(t0);
    const at = (k, p = pos) => ({ x: p[k][0], y: p[k][1], id: k });
    const H = at(m.node), G = at(m.pick), DST = at(m.dst);
    const legs = m.leap_path.map((a) => { const p = posAt(a[0]); return [at(a[2], p), at(a[3], p)]; });
    const pts = [H, G, DST, ...legs.flat()];
    const minx = Math.min(...pts.map((p) => p.x)), maxx = Math.max(...pts.map((p) => p.x));
    const miny = Math.min(...pts.map((p) => p.y)), maxy = Math.max(...pts.map((p) => p.y));
    const side = Math.max(maxx - minx, maxy - miny) + 220; // generous margins around everything involved
    const cx = (minx + maxx) / 2, cy = (miny + maxy) / 2;
    const vb = `${cx - side / 2} ${cy - side / 2} ${side} ${side}`;
    const k = side / 600; // on-screen size of annotations stays constant while zoomed
    const centroid = { x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length };

    /* annotation helpers (sizes in screen pixels, scaled by k) */
    const away = (p, dist) => { // a point beyond p, on the side away from the other drones
      let dx = p.x - centroid.x, dy = p.y - centroid.y;
      const L = Math.hypot(dx, dy);
      if (L < 1) { dx = 0; dy = -1; } else { dx /= L; dy /= L; }
      return { x: p.x + dx * dist * k, y: p.y + dy * dist * k };
    };
    const label = (o, p, txt) => {
      const q = away(p, 40);
      const t = KIT.text(o, q.x, q.y + 6 * k, txt, 'center ink');
      t.style.fontSize = 20 * k + 'px'; t.style.fontWeight = 800;
      return t;
    };
    const badge = (o, p, n, colour, shift) => { // numbered step marker, tied to the numbered lines in the story column
      const q = away(p, 76);
      const g = KIT.el('g', { transform: `translate(${q.x + (shift || 0) * k} ${q.y}) scale(${k})` }, o);
      KIT.el('circle', { r: 15, fill: colour }, g);
      const t = KIT.text(g, 0, 6, String(n), 'center white'); t.style.fontWeight = 800; t.style.fontSize = '17px';
      return g;
    };
    const arrow = (o, a, b, cls) => {
      const ar = KIT.arrow(o, cls);
      const ang = Math.atan2(b.y - a.y, b.x - a.x), off = 30 * k;
      ar.set(a.x + Math.cos(ang) * off, a.y + Math.sin(ang) * off, b.x - Math.cos(ang) * off, b.y - Math.sin(ang) * off);
      ar.querySelector('line').style.strokeWidth = 5 * k;
      const poly = ar.querySelector('polygon');
      poly.setAttribute('transform', poly.getAttribute('transform') + ` scale(${k})`);
      return ar;
    };
    const dot = (o, colour) => KIT.el('circle', { r: 10 * k, fill: colour }, o);
    const cross = (o, p, colour) => {
      const g = KIT.el('g', { transform: `translate(${p.x} ${p.y}) scale(${k})` }, o);
      KIT.el('line', { x1: -14, y1: -14, x2: 14, y2: 14, stroke: colour, 'stroke-width': 6 }, g);
      KIT.el('line', { x1: -14, y1: 14, x2: 14, y2: -14, stroke: colour, 'stroke-width': 6 }, g);
      return g;
    };
    const setup = (g) => {
      const o = g.over;
      const ring = KIT.ring(o, H.x, H.y, RMAX); ring.style.strokeWidth = 2.5 * k;
      const rt = KIT.text(o, H.x, H.y - RMAX - 10 * k, `range of drone ${m.node}`, 'center'); rt.style.fontSize = 17 * k + 'px';
      const tgt = KIT.target(o, DST.x, DST.y, ' '); tgt.setAttribute('transform', `translate(${DST.x} ${DST.y}) scale(${0.55 * k})`);
      const ids = new Set([m.node, m.pick, m.dst, ...(g.leap ? legs.flat().map((p) => p.id) : [])]);
      for (const id of ids) label(o, at(id), id === m.dst ? `D · ${id}` : String(id));
    };
    const [gG, gL] = P;
    setup(gG); setup(gL);

    /* Greedy: arrow to its pick, five attempts that die out of range, the packet is lost */
    const gArrow = arrow(gG.over, H, G, '');
    const gPkt = dot(gG.over, ink);
    const gX = cross(gG.over, G, red);
    const gLost = KIT.el('g', { transform: `translate(${H.x} ${H.y}) scale(${k})` }, gG.over);
    KIT.el('rect', { x: -34, y: 24, width: 68, height: 26, fill: red }, gLost);
    const lt = KIT.text(gLost, 0, 43, 'lost', 'center white'); lt.style.fontWeight = 800; lt.style.fontSize = '17px';
    const gb = [badge(gG.over, H, 1, ink), badge(gG.over, G, 2, ink, -20), badge(gG.over, G, 3, red, 20)];
    /* LEAP-GR: the same pick flagged and avoided (dashed), the switch, the path to the destination */
    const s = m.switch;
    const lWarn = arrow(gL.over, H, G, 'soft');
    const lX = cross(gL.over, G, faint);
    const lLegs = legs.map(([a, b]) => arrow(gL.over, a, b, 'leap'));
    const lPkt = dot(gL.over, blue);
    const okTick = KIT.tick(gL.over, 0, 0, 14);
    okTick.setAttribute('transform', `translate(${DST.x} ${DST.y - 44 * k}) scale(${k})`);
    const lb = [badge(gL.over, G, 1, blue), badge(gL.over, legs[0][1], 2, blue), badge(gL.over, DST, 3, blue)];

    const tries = m.greedy_tries;
    const allRange = tries.every((x) => x[5] === 'FAIL_RANGE');
    const tauTxt = s[5] <= 0 ? 'τ̂ = 0 s: by its last hello it has already left' : `τ̂ = ${fmt(s[5], 2)} s, under τth = ${TAU} s`;
    ui.story.innerHTML = `<p class="sub">Moment ${idx + 1} · packet ${m.pid} · drone ${m.node} → drone ${m.dst}</p>
      <div class="col"><b>Greedy</b>
        <p><i>1</i>Drone ${m.node} holds the packet at t = ${fmt(t0, 2)} s.</p>
        <p><i>2</i>${m.pick === m.dst ? `It sends it straight to drone ${m.dst}, the destination, still listed in its table.` : `It sends it to drone ${m.pick}, the neighbour closest to drone ${m.dst}.`}</p>
        <p class="bad"><i>3</i>${tries.length} attempts in ${fmt((tries[tries.length - 1][0] - tries[0][0]) * 1000, 0)} ms, ${allRange ? `drone ${m.pick} already out of range` : 'no ACK'}: lost.</p></div>
      <div class="col leap"><b>LEAP-GR</b>
        <p><i>1</i>Same drone, same packet. Drone ${m.pick}: ${tauTxt}.</p>
        <p><i>2</i>It switches to drone ${s[4]}.</p>
        <p class="good"><i>3</i>Delivered to drone ${m.dst} at t = ${fmt(m.leap_delivered_t, 2)} s.</p></div>
      <p class="note">Real recorded events, slowed down.</p>`;
    const gl = [...ui.story.querySelectorAll('.col:not(.leap) p')], ll = [...ui.story.querySelectorAll('.col.leap p')];

    tl = gsap.timeline();
    gsap.set([gArrow, gPkt, gX, gLost, ...gb, lWarn, lX, ...lLegs, lPkt, okTick, ...lb, ...gl, ...ll], { opacity: 0 });
    focusOn(gG, new Set([m.node, m.pick, m.dst]), tl);
    focusOn(gL, new Set([m.node, m.pick, m.dst, ...legs.flat().map((p) => p.id)]), tl);
    tl.to(P.map((g) => g.svg), { attr: { viewBox: vb }, duration: 1.2, ease: 'power3.inOut' }, 0)
      .to([gb[0], gl[0]], { opacity: 1, duration: 0.3 }, 1.0)
      .to([gArrow, gb[1], gl[1]], { opacity: 1, duration: 0.4 }, 1.6)
      .to([gb[2], gl[2]], { opacity: 1, duration: 0.3 }, 2.2);
    tries.forEach((x, i) => {
      const a0 = 2.3 + i * 0.45;
      tl.set(gPkt, { attr: { cx: H.x, cy: H.y }, opacity: 1 }, a0)
        .to(gPkt, { attr: { cx: G.x, cy: G.y }, duration: 0.32, ease: 'none' }, a0)
        .set(gPkt, { opacity: 0 }, a0 + 0.32)
        .to(gX, { opacity: i === tries.length - 1 ? 1 : 0.55, duration: 0.1 }, a0 + 0.32);
    });
    const g1 = 2.3 + tries.length * 0.45;
    tl.to(gLost, { opacity: 1, duration: 0.3 }, g1)
      .to([lWarn, lX, lb[0], ll[0]], { opacity: 1, duration: 0.4 }, g1 + 0.6)
      .to([lWarn, lX], { opacity: 0.35, duration: 0.4 }, g1 + 1.6)
      .to([lb[1], ll[1]], { opacity: 1, duration: 0.3 }, g1 + 1.6);
    lLegs.forEach((leg, i) => {
      const a0 = g1 + 1.8 + i * 0.6;
      const [a, b] = legs[i];
      tl.to(leg, { opacity: 1, duration: 0.25 }, a0)
        .set(lPkt, { attr: { cx: a.x, cy: a.y }, opacity: 1 }, a0)
        .to(lPkt, { attr: { cx: b.x, cy: b.y }, duration: 0.45, ease: 'power1.inOut' }, a0);
    });
    const end = g1 + 1.8 + lLegs.length * 0.6;
    tl.set(lPkt, { opacity: 0 }, end).to([okTick, lb[2], ll[2]], { opacity: 1, duration: 0.4 }, end);
  }

  /* ---------- controls ---------- */
  ui.play.addEventListener('click', () => {
    if (S.moment) clearMoment();
    S.playing = !S.playing;
    ui.play.textContent = S.playing ? 'Pause' : 'Play';
  });
  ui.speeds.forEach((b) => b.addEventListener('click', () => {
    S.speed = Number(b.dataset.speed);
    ui.speeds.forEach((x) => x.classList.toggle('on', x === b));
  }));
  D.moments.forEach((m, i) => {
    const b = document.createElement('button');
    b.innerHTML = `<i>${i + 1}</i>Moment · t = ${m.greedy_tries[0][0].toFixed(1)} s`;
    b.addEventListener('click', () => playMoment(i));
    ui.moments.appendChild(b);
  });
  ui.full.addEventListener('click', () => { clearMoment(); S.playing = true; ui.play.textContent = 'Pause'; ui.story.innerHTML = intro[1]; });

  const g0 = runs[0].totals, g1 = runs[1].totals;
  const GUIDE = Math.max(0, D.moments.findIndex((m) => m.pick !== m.dst)); // first moment where Greedy's pick is a relay
  const sample = (svg) => `<svg class="key" viewBox="0 0 64 24" width="64" height="24">${svg}</svg>`;
  const keyRows = `<div class="keys">
    <div class="keyrow">${sample(`<line x1="2" y1="12" x2="62" y2="12" stroke="#cfcfcb" stroke-width="2"/>`)}<span>two drones in radio range</span></div>
    <div class="keyrow">${sample(`<line x1="2" y1="12" x2="24" y2="12" stroke="${red}" stroke-width="4"/><line x1="40" y1="12" x2="62" y2="12" stroke="${red}" stroke-width="4"/><line x1="26" y1="6" x2="38" y2="18" stroke="${red}" stroke-width="4"/><line x1="26" y1="18" x2="38" y2="6" stroke="${red}" stroke-width="4"/>`)}<span>Greedy sending to a neighbour <b class="red">that has left</b></span></div>
    <div class="keyrow">${sample(`<rect x="10" y="3" width="44" height="18" fill="${red}"/><text x="32" y="16" fill="#fff" font-size="12" font-weight="800" text-anchor="middle" font-family="Archivo">lost</text>`)}<span>packet dropped after 5 attempts</span></div>
    <div class="keyrow">${sample(`<line x1="2" y1="6" x2="44" y2="6" stroke="${faint}" stroke-width="3" stroke-dasharray="5 5"/><line x1="2" y1="18" x2="48" y2="18" stroke="${blue}" stroke-width="4"/><polygon points="62,18 48,12 48,24" fill="${blue}"/>`)}<span>LEAP-GR <b class="blue">switches</b> away from it (dashed)</span></div></div>`;
  const intro = [
    `<p class="sub">The demo run, replayed</p><p>Same 20 drones, same trajectories, same traffic. Only the routing decision differs.</p>${keyRows}`,
    `<p class="sub">Where packets are lost</p><p>Each red tick on the timeline is a packet Greedy loses to a link break: ${g0.link_break} in this run. LEAP-GR loses ${g1.link_break}; each blue tick is one of its ${g1.switches} switches before a break.</p>${keyRows}`,
  ];

  return {
    enter(step) {
      clearMoment();
      S.playing = true; ui.play.textContent = 'Pause';
      slide.classList.toggle('focus', step >= 1);
      if (step < 2) { ui.story.innerHTML = intro[step]; S.t = T0; } else playMoment(GUIDE);
      gsap.ticker.add(frame);
    },
    step(n) {
      slide.classList.toggle('focus', n >= 1);
      if (n < 2) ui.story.innerHTML = intro[n]; else playMoment(GUIDE);
    },
    leave() { gsap.ticker.remove(frame); clearMoment(); },
  };
};
