/* === SCENES · PROBLEM AND EXISTING ROUTING ===
   A0 (slide 2): a ground network next to a drone swarm. A7 (slide 5): DSDV's stale tables and GRAd's
   broadcast. A8 (slide 6): Greedy forwarding hop by hop. A9 (slide 7): OPAR's oracle and Q-learning.
   Concept animations: stylised and seeded, no measured numbers. */
window.SCENES = window.SCENES || {};

function seeded(seed) {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

/* === A0 · A NETWORK THAT NEVER STOPS MOVING ===
   Left: a ground ad hoc network, slow nodes, stable links. Right: a swarm.
   s0: a packet hops from drone to drone (every drone relays). s1: the swarm speeds up and climbs and
   dives (3-D: the glyph size follows altitude). s2: links near the range limit redden and every break
   flashes red. */
SCENES.fanet = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const rnd = seeded(11);
  const RANGE = 165;
  KIT.el('line', { x1: 452, y1: 10, x2: 452, y2: 460, class: 'panel-rule' }, svg);
  KIT.text(svg, 10, 30, 'Ground ad hoc network', 'big');
  KIT.text(svg, 482, 30, 'Drone swarm', 'big');
  KIT.text(svg, 10, 58, 'slow nodes, stable links');
  const swarmSub = KIT.text(svg, 482, 58, 'every drone relays');

  function make(n, x0, x1, kind) {
    const nodes = [];
    for (let i = 0; i < n; i++) {
      nodes.push({ x: x0 + 40 + rnd() * (x1 - x0 - 80), y: 110 + rnd() * 320, a: rnd() * 6.28, z: rnd() * 6.28, kind });
    }
    return nodes;
  }
  const ground = make(7, 0, 452, 'g');
  const swarm = make(9, 482, 1044, 's');
  const pairs = (ns) => ns.flatMap((a, i) => ns.slice(i + 1).map((b) => ({ a, b, on: false, line: KIT.el('line', { class: 'edge' }, svg) })));
  const gl = pairs(ground), sl = pairs(swarm);
  const flashes = Array.from({ length: 6 }, () => KIT.el('circle', { r: 0, class: 'flash', opacity: 0 }, svg));
  let fi = 0;
  const pkt = KIT.packet(svg);
  ground.forEach((n) => { n.el = KIT.el('rect', { x: -12, y: -12, width: 24, height: 24, class: 'node' }, svg); });
  swarm.forEach((n) => { n.el = KIT.drone(svg); });

  const P = { speed: 0.35, breaks: 0 };
  const hop = { from: swarm[0], to: swarm[0], p: 1 };

  function move(n, v, x0, x1) {
    n.a += (rnd() - 0.5) * 0.12;
    n.x += Math.cos(n.a) * v; n.y += Math.sin(n.a) * v;
    if (n.x < x0 + 30 || n.x > x1 - 30) n.a = Math.PI - n.a;
    if (n.y < 100 || n.y > 440) n.a = -n.a;
    n.x = Math.min(Math.max(n.x, x0 + 30), x1 - 30); n.y = Math.min(Math.max(n.y, 100), 440);
  }
  function links(list, colour) {
    for (const l of list) {
      const d = Math.hypot(l.a.x - l.b.x, l.a.y - l.b.y);
      const on = d < RANGE;
      if (l.on && !on && colour && P.breaks > 0.5) {
        const f = flashes[fi++ % flashes.length];
        gsap.fromTo(f, { attr: { cx: (l.a.x + l.b.x) / 2, cy: (l.a.y + l.b.y) / 2, r: 6 }, opacity: 1 }, { attr: { r: 34 }, opacity: 0, duration: 0.8, ease: 'power1.out' });
      }
      l.on = on;
      l.line.style.display = on ? '' : 'none';
      if (!on) continue;
      l.line.setAttribute('x1', l.a.x); l.line.setAttribute('y1', l.a.y);
      l.line.setAttribute('x2', l.b.x); l.line.setAttribute('y2', l.b.y);
      l.line.style.stroke = colour && P.breaks > 0.5 ? KIT.stretch(d, RANGE) : KIT.css('--faint');
    }
  }
  function frame() {
    ground.forEach((n) => move(n, 0.12, 0, 452));
    swarm.forEach((n) => { move(n, P.speed * 1.6, 482, 1044); n.z += 0.02 * P.speed; });
    links(gl, false);
    links(sl, true);
    ground.forEach((n) => gsap.set(n.el, { x: n.x, y: n.y }));
    swarm.forEach((n) => gsap.set(n.el, { x: n.x, y: n.y, scale: 0.42 + (P.speed > 0.5 ? 0.14 * Math.sin(n.z) : 0) }));
    /* the relayed packet: hop to a linked neighbour, preferring the one farther right, then start again */
    hop.p += 0.035;
    if (hop.p >= 1) {
      const nb = sl.filter((l) => l.on && (l.a === hop.to || l.b === hop.to)).map((l) => (l.a === hop.to ? l.b : l.a));
      const next = nb.sort((u, v) => v.x - u.x)[0];
      hop.from = hop.to;
      hop.to = next && next.x > hop.to.x - 20 ? next : swarm.slice().sort((u, v) => u.x - v.x)[0];
      hop.p = 0;
    }
    pkt.setAttribute('cx', hop.from.x + (hop.to.x - hop.from.x) * hop.p);
    pkt.setAttribute('cy', hop.from.y + (hop.to.y - hop.from.y) * hop.p);
  }

  const levels = [{ speed: 0.35, breaks: 0 }, { speed: 1, breaks: 0 }, { speed: 1, breaks: 1 }];
  const subs = ['every drone relays', 'fast, in three dimensions', 'links keep breaking'];
  return {
    enter(s) { Object.assign(P, levels[s]); swarmSub.textContent = subs[s]; gsap.ticker.add(frame); },
    step(n) { gsap.to(P, { ...levels[n], duration: 1.2, ease: 'power2.inOut' }); swarmSub.textContent = subs[n]; },
    leave() { gsap.ticker.remove(frame); },
  };
};

/* === A7 · TABLES AND GRADIENTS ===
   Top (DSDV): D keeps moving; the route still points at D's last advertised place (ghost) until the
   next table update ripples back hop by hop. Bottom (GRAd): a broadcast; several closer neighbours relay
   copies; one copy is lost and, without ACKs, nobody retries. s0 runs DSDV, s1 adds GRAd. */
SCENES.topology = function (slide) {
  const svg = slide.querySelector('svg.scene');
  /* --- DSDV, top half --- */
  const top = KIT.el('g', {}, svg);
  KIT.text(top, 0, 26, 'DSDV', 'big');
  const chain = [{ x: 70, y: 130 }, { x: 270, y: 130 }, { x: 470, y: 130 }];
  const D0 = { x: 680, y: 130 }, D1 = { x: 860, y: 130 };
  chain.slice(0, 2).forEach((n, i) => KIT.el('line', { x1: n.x, y1: n.y, x2: chain[i + 1].x, y2: n.y, class: 'edge faint' }, top));
  const route = KIT.arrow(top, 'thin');
  const ghost = placeDrone(top, D0.x, D0.y, 'ghost', 0.6);
  const stale = KIT.text(top, D0.x, D0.y + 60, 'route points where D was', 'center lost');
  const waves = [D0, ...chain.slice().reverse()].map((n) => KIT.pulse(top, n.x, n.y, 70, 'soft'));
  chain.forEach((n, i) => { placeDrone(top, n.x, n.y, i === 0 ? 'sender' : '', 0.6); });
  const d = placeDrone(top, D0.x, D0.y, '', 0.6);
  const dTag = KIT.text(top, D0.x, D0.y - 40, 'D', 'center ink');
  const dpos = { x: D0.x, g: D0.x };
  function drawD() {
    gsap.set(d, { x: dpos.x, y: D0.y, scale: 0.6 });
    dTag.setAttribute('x', dpos.x);
    gsap.set(ghost, { x: dpos.g, y: D0.y, scale: 0.6 });
    stale.setAttribute('x', dpos.g);
    route.set(chain[2].x + 30, D0.y, dpos.g - 34, D0.y);
    const lag = Math.abs(dpos.x - dpos.g) > 30;
    stale.style.opacity = lag ? 1 : 0;
    ghost.style.visibility = lag ? 'visible' : 'hidden';
  }
  const dsdv = gsap.timeline({ paused: true, repeat: -1, onUpdate: drawD });
  [D1.x, D0.x].forEach((x) => {
    dsdv.to(dpos, { x, duration: 2.2, ease: 'sine.inOut' }).to({}, { duration: 0.3 });
    waves.forEach((w, i) => dsdv.add(w(0.6), i === 0 ? '>' : '<0.22'));
    dsdv.to(dpos, { g: x, duration: 0.3, ease: 'power2.out' }, '<-0.1').to({}, { duration: 0.5 });
  });

  /* --- GRAd, bottom half --- */
  const bot = KIT.el('g', {}, svg);
  KIT.el('line', { x1: 0, y1: 236, x2: 960, y2: 236, class: 'panel-rule' }, bot);
  KIT.text(bot, 0, 274, 'GRAd', 'big');
  const S = { x: 80, y: 370 }, A = { x: 300, y: 310 }, B = { x: 310, y: 430 }, C = { x: 540, y: 360 }, T = { x: 860, y: 365 };
  KIT.target(bot, T.x, T.y, 'D');
  const wS = KIT.pulse(bot, S.x, S.y, 260, 'soft'), wA = KIT.pulse(bot, A.x, A.y, 260, 'soft'),
    wB = KIT.pulse(bot, B.x, B.y, 260, 'soft'), wC = KIT.pulse(bot, C.x, C.y, 330, 'soft');
  [S, A, B, C].forEach((n, i) => placeDrone(bot, n.x, n.y, i === 0 ? 'sender' : '', 0.6));
  const copies = KIT.text(bot, 380, 266, 'two neighbours relay copies', 'ink');
  const lost = KIT.cross(bot, (B.x + C.x) / 2 + 20, (B.y + C.y) / 2 + 10, 14);
  const lostTag = KIT.text(bot, (B.x + C.x) / 2 + 46, (B.y + C.y) / 2 + 40, 'lost: no ACK, no retry', 'lost');
  const grad = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 0.6 });
  gsap.set([copies, lost, lostTag], { opacity: 0 });
  grad.add(wS(0.9))
    .add(wA(0.9), '>-0.2').add(wB(0.9), '<0.05')
    .to(copies, { opacity: 1, duration: 0.3 }, '<')
    .fromTo(lost, { opacity: 0 }, { opacity: 1, duration: 0.2 }, '>-0.3')
    .to(lostTag, { opacity: 1, duration: 0.3 }, '<')
    .add(wC(1.0), '>')
    .to([copies, lost, lostTag], { opacity: 0, duration: 0.4 }, '>0.4');

  return {
    enter(s) {
      drawD();
      gsap.set(top, { opacity: 1 }); gsap.set(bot, { opacity: s >= 1 ? 1 : 0.2 });
      dsdv.play(0);
      if (s >= 1) grad.play(0); else grad.pause(0);
    },
    step(n) { if (n >= 1) { gsap.to(bot, { opacity: 1, duration: 0.5 }); grad.play(0); } },
    leave() { dsdv.pause(); grad.pause(); },
  };
};

/* === A8 · GREEDY FORWARDING ===
   s0: hop by hop, the holder's range lights up, its neighbours are compared and the one that gets
   closest to D takes the packet (loops). s1: the loop stops on the first hop; the chosen neighbour,
   at the edge of range, drifts away and the link reddens: Greedy never asked how long it would last. */
SCENES.greedyHop = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const R = 190;
  const D = { x: 900, y: 240 };
  const N = [{ x: 70, y: 250 }, { x: 240, y: 170 }, { x: 160, y: 140 }, { x: 180, y: 360 }, { x: 410, y: 235 },
    { x: 300, y: 380 }, { x: 480, y: 110 }, { x: 590, y: 260 }, { x: 520, y: 390 }, { x: 760, y: 220 },
    { x: 700, y: 360 }, { x: 680, y: 110 }];
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  /* the greedy path, computed from the geometry so the drawing cannot contradict the rule */
  const path = [0];
  for (;;) {
    const cur = N[path[path.length - 1]];
    if (dist(cur, D) <= R) break;
    let best = -1;
    N.forEach((n, j) => { if (dist(cur, n) <= R && dist(n, D) < dist(cur, D) && (best < 0 || dist(n, D) < dist(N[best], D))) best = j; });
    if (best < 0 || path.includes(best)) break;
    path.push(best);
  }
  const ring = KIT.ring(svg, N[0].x, N[0].y, R);
  KIT.target(svg, D.x, D.y, 'D');
  const cand = N.map(() => KIT.el('line', { class: 'edge faint' }, svg));
  const chosen = KIT.el('line', { class: 'link thin' }, svg);
  const pkt = KIT.packet(svg);
  const ds = N.map((n, i) => placeDrone(svg, n.x, n.y, i === 0 ? 'sender' : '', 0.62));
  const ask = KIT.chip(svg, 470, 450, 'how long will this link last? never asked');
  const live = { x: 0, y: 0 };

  const loop = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 0.8 });
  path.forEach((idx, k) => {
    const cur = N[idx];
    const nextIdx = k + 1 < path.length ? path[k + 1] : null;
    const nxt = nextIdx === null ? D : N[nextIdx];
    const inRange = N.map((n, j) => j !== idx && dist(cur, n) <= R);
    loop.set(ring, { attr: { cx: cur.x, cy: cur.y } })
      .set(pkt, { attr: { cx: cur.x, cy: cur.y } })
      .fromTo(ring, { opacity: 0 }, { opacity: 1, duration: 0.3 });
    cand.forEach((c, j) => {
      if (!inRange[j]) return;
      loop.set(c, { attr: { x1: cur.x, y1: cur.y, x2: N[j].x, y2: N[j].y } }, '<').fromTo(c, { opacity: 0 }, { opacity: 1, duration: 0.25 }, '<');
    });
    loop.set(chosen, { attr: { x1: cur.x, y1: cur.y, x2: nxt.x, y2: nxt.y } }, '>0.15')
      .fromTo(chosen, { opacity: 0 }, { opacity: 1, duration: 0.2 })
      .to(pkt, { attr: { cx: nxt.x, cy: nxt.y }, duration: 0.6, ease: 'power1.inOut' })
      .to([...cand, chosen, ring], { opacity: 0, duration: 0.2 });
  });

  /* s1: freeze on the first hop and let the chosen neighbour drift out of range */
  const first = N[path[1]];
  const away = { x: N[0].x + (first.x - N[0].x) * 1.45, y: N[0].y + (first.y - N[0].y) * 1.45 };
  function drawDrift() {
    gsap.set(ds[path[1]], { x: live.x, y: live.y });
    chosen.setAttribute('x2', live.x); chosen.setAttribute('y2', live.y);
    chosen.style.stroke = KIT.stretch(dist(N[0], live), R);
  }
  const drift = gsap.timeline({ paused: true });
  drift.set(live, { x: first.x, y: first.y })
    .set(ring, { attr: { cx: N[0].x, cy: N[0].y }, opacity: 1 })
    .set(chosen, { attr: { x1: N[0].x, y1: N[0].y, x2: first.x, y2: first.y }, opacity: 1 })
    .set(pkt, { opacity: 0 })
    .to(live, { x: away.x, y: away.y, duration: 2, ease: 'sine.inOut', onUpdate: drawDrift })
    .fromTo(ask, { opacity: 0 }, { opacity: 1, duration: 0.4 }, '-=0.8');

  function reset() {
    gsap.set(ds[path[1]], { x: first.x, y: first.y });
    chosen.style.stroke = '';
    gsap.set([...cand, chosen, ring, ask], { opacity: 0 });
    gsap.set(pkt, { opacity: 1 });
  }
  return {
    enter(s) {
      loop.pause(0); drift.pause(0); reset();
      if (s === 0) loop.play(0); else drift.progress(1);
    },
    step(n) { if (n >= 1) { loop.pause(); reset(); drift.play(0); } },
    leave() { loop.pause(); drift.pause(); },
  };
};

/* === A9 · PREDICT WITH AN ORACLE, OR LEARN FROM LOSSES ===
   Left (OPAR): a global view sweeps over the swarm, reads every drone's true position and velocity, and
   plans around the link that is about to expire. Right (Q-learning): the best-scored neighbour gets the
   packet, the packet is lost, only then does its score drop and the next packet go elsewhere. */
SCENES.oracle = function (slide) {
  const [left, right] = slide.querySelectorAll('svg.scene');

  /* --- OPAR --- */
  const pts = [{ x: 60, y: 135 }, { x: 220, y: 82 }, { x: 240, y: 180 }, { x: 420, y: 100 }, { x: 430, y: 182 }, { x: 600, y: 132 }, { x: 735, y: 132 }];
  const edges = [[0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 5], [5, 6]];
  const el = edges.map(([a, b]) => KIT.el('line', { x1: pts[a].x, y1: pts[a].y, x2: pts[b].x, y2: pts[b].y, class: 'edge faint' }, left));
  const plan = [[0, 2], [2, 4], [4, 5], [5, 6]].map(([a, b]) => KIT.el('line', { x1: pts[a].x, y1: pts[a].y, x2: pts[b].x, y2: pts[b].y, class: 'link thin' }, left));
  const scan = KIT.el('rect', { x: 0, y: 40, width: 6, height: 176, fill: KIT.css('--ink'), opacity: 0.12 }, left);
  const view = KIT.el('rect', { x: 2, y: 40, width: 812, height: 176, fill: 'none', stroke: KIT.css('--ink'), 'stroke-width': 2, 'stroke-dasharray': '8 8' }, left);
  const viewTag = KIT.text(left, 2, 26, 'global view: true position and velocity of every drone', 'ink');
  /* each drone's velocity: a short vector starting at the drone, all pointing the same general way */
  const vel = pts.map((p) => { const a = KIT.arrow(left, 'thin soft'); a.set(p.x + 24, p.y - 2, p.x + 62, p.y - 12); return a; });
  pts.forEach((p, i) => placeDrone(left, p.x, p.y, i === 0 ? 'sender' : '', 0.48));
  const op = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 1 });
  op.set([...plan, ...vel, viewTag], { opacity: 0 }).set(el[2], { attr: { class: 'edge faint' } })
    .set(scan, { opacity: 0.12 })
    .fromTo(scan, { attr: { x: 0 } }, { attr: { x: 806 }, duration: 1.6, ease: 'none' })
    .to(scan, { opacity: 0, duration: 0.3 })
    .to(vel, { opacity: 1, duration: 0.2, stagger: 0.2 }, '<')
    .to(viewTag, { opacity: 1, duration: 0.3 }, '<')
    .set(el[2], { attr: { class: 'edge red dash' } })
    .to(plan, { opacity: 1, duration: 0.3, stagger: 0.2 })
    .to({}, { duration: 1.2 });
  gsap.set(view, { opacity: 1 });

  /* --- Q-learning --- */
  const S = { x: 70, y: 115 };
  const nb = [{ x: 330, y: 50 }, { x: 330, y: 115 }, { x: 330, y: 180 }];
  const bars = nb.map((n, i) => {
    KIT.el('rect', { x: 400, y: n.y - 9, width: 200, height: 18, fill: '#fff', stroke: KIT.css('--ink'), 'stroke-width': 2 }, right);
    return KIT.el('rect', { x: 400, y: n.y - 9, width: [180, 130, 70][i], height: 18, fill: KIT.css('--ink') }, right);
  });
  KIT.text(right, 400, 22, 'learned score per neighbour', '');
  placeDrone(right, S.x, S.y, 'sender', 0.48);
  nb.forEach((n) => placeDrone(right, n.x, n.y, '', 0.48));
  const qp = KIT.packet(right);
  const qx = KIT.cross(right, nb[0].x + 40, nb[0].y, 12);
  const qok = KIT.tick(right, nb[1].x + 40, nb[1].y, 12, '--ink');
  const qtag = KIT.text(right, 400, 214, 'adapts after the loss', 'lost');
  const q = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 1 });
  q.set([qx, qok, qtag], { opacity: 0 }).set(bars[0], { attr: { width: 180 } })
    .set(qp, { attr: { cx: S.x, cy: S.y }, opacity: 1 })
    .to(qp, { attr: { cx: nb[0].x, cy: nb[0].y }, duration: 0.7, ease: 'power1.inOut' })
    .set(qp, { opacity: 0 })
    .to(qx, { opacity: 1, duration: 0.2 })
    .to(bars[0], { attr: { width: 60 }, duration: 0.6, ease: 'power2.inOut' }, '+=0.2')
    .to(qtag, { opacity: 1, duration: 0.3 }, '<')
    .set(qp, { attr: { cx: S.x, cy: S.y }, opacity: 1 }, '+=0.2')
    .to(qp, { attr: { cx: nb[1].x, cy: nb[1].y }, duration: 0.7, ease: 'power1.inOut' })
    .set(qp, { opacity: 0 })
    .to(qok, { opacity: 1, duration: 0.2 })
    .to({}, { duration: 1 });

  return {
    enter(s) { op.play(0); if (s >= 1) q.play(0); else q.pause(0); },
    step(n) { if (n >= 1) q.play(0); },
    leave() { op.pause(); q.pause(); },
  };
};
