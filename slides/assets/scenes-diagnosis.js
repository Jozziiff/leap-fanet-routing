/* === SCENES · DIAGNOSIS ===
   A3a (slide 9): how a failed frame is classified. A3b (slide 10): why collisions are absorbed and link
   breaks are not. A4 (slide 11): why Greedy keeps sending to a neighbour that has left.
   Concept animations: stylised geometry, no measured numbers. */
window.SCENES = window.SCENES || {};

/* === A3a · EVERY LOST FRAME, CLASSIFIED ===
   intro: two identical set-ups, the distance d drawn against the range R.
   s1: left, B is in range but another frame overlaps it: collision (grey).
   s2: right, B is beyond the range: the frame cannot arrive, link break (red). */
SCENES.classify = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const R = 150;
  const L = { a: { x: 170, y: 255 }, b: { x: 292, y: 255 }, c: { x: 300, y: 95 } };
  const Rt = { a: { x: 690, y: 255 }, b: { x: 905, y: 255 } };

  KIT.el('line', { x1: 522, y1: 10, x2: 522, y2: 460, class: 'panel-rule' }, svg);
  const titleL = KIT.text(svg, 20, 34, 'Receiver in range', 'big');
  const titleR = KIT.text(svg, 542, 34, 'Receiver out of range', 'big');

  const ringL = KIT.ring(svg, L.a.x, L.a.y, R);
  const ringR = KIT.ring(svg, Rt.a.x, Rt.a.y, R);
  const dL = KIT.el('line', { x1: L.a.x, y1: L.a.y + 62, x2: L.b.x, y2: L.b.y + 62, class: 'edge' }, svg);
  const dR = KIT.el('line', { x1: Rt.a.x, y1: Rt.a.y + 62, x2: Rt.b.x, y2: Rt.b.y + 62, class: 'edge red' }, svg);
  const dLt = KIT.text(svg, (L.a.x + L.b.x) / 2, L.a.y + 92, 'd < R', 'center ink');
  const dRt = KIT.text(svg, (Rt.a.x + Rt.b.x) / 2, Rt.a.y + 92, 'd > R', 'center lost');

  const waveC = KIT.pulse(svg, L.c.x, L.c.y, 175, 'soft');
  const pL = KIT.packet(svg);
  const pR = KIT.packet(svg);
  const drones = [placeDrone(svg, L.a.x, L.a.y, 'sender'), placeDrone(svg, L.b.x, L.b.y), placeDrone(svg, L.c.x, L.c.y),
    placeDrone(svg, Rt.a.x, Rt.a.y, 'sender'), placeDrone(svg, Rt.b.x, Rt.b.y)];
  const names = [KIT.text(svg, L.a.x, L.a.y - 50, 'A', 'center ink'), KIT.text(svg, L.b.x + 8, L.b.y - 50, 'B', 'center ink'),
    KIT.text(svg, L.c.x + 52, L.c.y + 7, 'another sender', 'ink'),
    KIT.text(svg, Rt.a.x, Rt.a.y - 50, 'A', 'center ink'), KIT.text(svg, Rt.b.x, Rt.b.y - 50, 'B', 'center ink')];

  const burst = KIT.burst(svg, L.b.x, L.b.y, 46);
  const colTag = KIT.text(svg, L.b.x, L.b.y + 150, 'collision', 'center col');
  const colWhy = KIT.text(svg, 20, 440, 'Two frames overlap at B.', 'ink');
  const lostX = KIT.cross(svg, Rt.b.x, Rt.b.y, 22);
  const brkTag = KIT.text(svg, Rt.b.x - 40, Rt.b.y + 150, 'link break', 'center lost');
  const brkWhy = KIT.text(svg, 542, 440, 'No retry can reach B.', 'ink');
  const fadeIn = [titleL, titleR, ringL, ringR, dL, dR, dLt, dRt, ...drones, ...names];

  const M = KIT.motion;
  const t = KIT.stepped((tl) => {
    gsap.set([burst, colTag, colWhy, lostX, brkTag, brkWhy, pL, pR], { opacity: 0 });
    tl.from(fadeIn, { opacity: 0, y: 12, duration: 0.5, stagger: 0.04, ease: 'power2.out' })
      .addLabel('s0')
      /* collision: A's frame and the other sender's frame meet at B */
      .set(pL, { attr: { cx: L.a.x, cy: L.a.y }, opacity: 1 })
      .add(waveC(1.1), '<')
      .to(pL, { attr: { cx: L.b.x - 20, cy: L.b.y }, duration: 0.9, ease: 'none' }, '<0.1')
      .to(pL, { opacity: 0, duration: 0.2 })
      .fromTo(burst, { opacity: 0, scale: 0.4, svgOrigin: `${L.b.x} ${L.b.y}` }, { opacity: 1, scale: 1, duration: 0.35, ease: M.pop }, '<')
      .to([colTag, colWhy], { opacity: 1, duration: M.beat }, '<0.15')
      .addLabel('s1')
      /* link break: the frame dies at the edge of the range */
      .set(pR, { attr: { cx: Rt.a.x, cy: Rt.a.y }, opacity: 1 })
      .to(pR, { attr: { cx: Rt.a.x + R + 10 }, duration: 0.9, ease: 'none' })
      .to(pR, { attr: { cx: Rt.a.x + R + 50 }, opacity: 0, duration: 0.35, ease: 'power1.out' })
      .fromTo(lostX, { opacity: 0, scale: 0.4, svgOrigin: `${Rt.b.x} ${Rt.b.y}` }, { opacity: 1, scale: 1, duration: 0.35, ease: M.pop }, '<0.1')
      .to([brkTag, brkWhy], { opacity: 1, duration: M.beat }, '<0.15')
      .addLabel('s2');
  });

  return { enter: (s) => t.enter(s), step: (n) => t.play(n), leave() {} };
};

/* === A3b · COLLISIONS ARE ABSORBED, LINK BREAKS ARE NOT ===
   intro: the MAC's five attempts, twice. A collided frame fails once and goes through on attempt 2;
   a frame to a departed neighbour fails all five attempts and is dropped.
   s1: the link-break row is underlined (permanent). s2: the collision row is underlined (absorbed). */
SCENES.attempts = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const X0 = 360, GAP = 96, S = 68, Y1 = 130, Y2 = 320;
  KIT.text(svg, X0 - S / 2, 40, 'MAC attempts', 'ink');
  for (let i = 0; i < 5; i++) KIT.text(svg, X0 + i * GAP, 76, String(i + 1), 'center');

  KIT.text(svg, 0, Y1 - 4, 'Collision', 'big');
  KIT.text(svg, 0, Y1 + 26, 'receiver still in range');
  KIT.text(svg, 0, Y2 - 4, 'Link break', 'big');
  KIT.text(svg, 0, Y2 + 26, 'receiver has left');

  const row1 = [], row2 = [];
  for (let i = 0; i < 5; i++) {
    row1.push(KIT.slot(svg, X0 + i * GAP, Y1, S));
    row2.push(KIT.slot(svg, X0 + i * GAP, Y2, S));
  }
  const burst1 = KIT.burst(svg, X0, Y1, 26);
  const tick1 = KIT.el('polyline', { points: `${X0 + GAP - 16},${Y1} ${X0 + GAP - 5},${Y1 + 11} ${X0 + GAP + 16},${Y1 - 12}`, fill: 'none', stroke: '#fff', 'stroke-width': 6 }, svg);
  const crosses = row2.map((_, i) => whiteCross(svg, X0 + i * GAP, Y2, 14));
  const outX = X0 + 4 * GAP + 70;
  const delivered = KIT.text(svg, outX, Y1 + 9, 'delivered', 'big');
  const dropped = KIT.text(svg, outX, Y2 + 9, 'dropped', 'lost');
  dropped.style.fontSize = '28px';
  const ul2 = KIT.el('line', { x1: 0, y1: Y2 + 60, x2: outX + 130, y2: Y2 + 60, class: 'edge red' }, svg);
  const why2 = KIT.text(svg, 0, Y2 + 96, 'Every retry goes to a drone that is gone.', 'ink');
  const ul1 = KIT.el('line', { x1: 0, y1: Y1 + 60, x2: outX + 150, y2: Y1 + 60, class: 'edge' }, svg);
  const why1 = KIT.text(svg, 0, Y1 + 96, 'The next attempt finds a free channel.', 'ink');

  const t = KIT.stepped((tl) => {
    gsap.set([burst1, tick1, ...crosses, delivered, dropped, ul2, why2, ul1, why1], { opacity: 0 });
    gsap.set([ul1, ul2], { attr: { 'stroke-dasharray': 1200, 'stroke-dashoffset': 1200 } });
    tl.from([...row1, ...row2], { opacity: 0, y: 10, duration: 0.4, stagger: 0.04 })
      /* collision row: attempt 1 collides, attempt 2 succeeds, the rest is never needed */
      .add(() => row1[0].box.classList.add('col'))
      .to(burst1, { opacity: 1, duration: 0.25 })
      .to({}, { duration: 0.35 })
      .add(() => row1[1].box.classList.add('ok'))
      .to(tick1, { opacity: 1, duration: 0.25 })
      .to(row1.slice(2), { opacity: 0.25, duration: 0.3 }, '<')
      .to(delivered, { opacity: 1, duration: 0.3 }, '<')
      .to({}, { duration: 0.3 });
    /* link-break row: five failures in a row, then the packet is dropped */
    row2.forEach((sl, i) => {
      tl.add(() => sl.box.classList.add('fail')).to(crosses[i], { opacity: 1, duration: 0.18 }).to({}, { duration: 0.16 });
    });
    tl.to(dropped, { opacity: 1, duration: 0.3 })
      .addLabel('s0')
      .to(ul2, { opacity: 1, attr: { 'stroke-dashoffset': 0 }, duration: 0.6, ease: 'power2.inOut' })
      .to(why2, { opacity: 1, duration: 0.4 }, '<0.3')
      .addLabel('s1')
      .to(ul1, { opacity: 1, attr: { 'stroke-dashoffset': 0 }, duration: 0.6, ease: 'power2.inOut' })
      .to(why1, { opacity: 1, duration: 0.4 }, '<0.3')
      .addLabel('s2');
  });

  /* class changes are not reversible by seeking, so reset them before every seek */
  function reset() {
    row1.concat(row2).forEach((s) => s.box.classList.remove('col', 'ok', 'fail'));
  }
  return {
    enter(s) {
      reset();
      t.enter(s);
      if (s > 0) { row1[0].box.classList.add('col'); row1[1].box.classList.add('ok'); row2.forEach((x) => x.box.classList.add('fail')); }
    },
    step: (n) => t.play(n),
    leave() {},
  };
};

/* === A4 · GREEDY PICKS THE EDGE ===
   intro: S, its range, three neighbours, destination D; hellos go out.
   s1: Greedy measures progress to D and points at N3, the one at the edge of range.
   s2: N3 flies away; its table entry (a ghost at the last hello position) stays for 2 s.
   s3: five attempts go to the ghost, each fails, the packet is dropped. */
SCENES.greedyEdge = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const S = { x: 190, y: 215 }, R = 182, D = { x: 960, y: 200 };
  const N = [{ x: 225, y: 85 }, { x: 285, y: 320 }, { x: 345, y: 165 }];
  const far = { x: 560, y: 120 };

  KIT.ring(svg, S.x, S.y, R);
  const toD = N.map((n) => KIT.el('line', { x1: n.x, y1: n.y, x2: D.x - 34, y2: D.y, class: 'edge faint dash' }, svg));
  const best = KIT.el('line', { x1: N[2].x, y1: N[2].y, x2: D.x - 34, y2: D.y, class: 'edge dash' }, svg);
  KIT.target(svg, D.x, D.y, 'D');
  const ghost = placeDrone(svg, N[2].x, N[2].y, 'ghost');
  const ghostTag = KIT.text(svg, N[2].x, N[2].y + 70, 'table entry · kept 2 s', 'center');
  const arrow = KIT.arrow(svg);
  arrow.set(S.x + 30, S.y - 10, N[2].x - 38, N[2].y + 10);
  const pick = KIT.chip(svg, N[2].x + 40, N[2].y - 50, 'closest to D');
  const pkts = [0, 1, 2, 3, 4].map(() => KIT.packet(svg));
  const xs = pkts.map(() => KIT.cross(svg, N[2].x, N[2].y, 18));
  const tries = KIT.attempts(svg, 40, 392, 5, 40);
  const triesTag = KIT.text(tries, 200, 7, 'five attempts, then dropped', 'lost');
  const dots = [...tries.querySelectorAll('circle')];
  const waves = N.map((n) => KIT.pulse(svg, n.x, n.y, 90, 'soft'));
  const s = placeDrone(svg, S.x, S.y, 'sender');
  const ns = N.map((n) => placeDrone(svg, n.x, n.y));
  KIT.text(svg, S.x, S.y + 66, 'S', 'center ink');

  const live = { x: N[2].x, y: N[2].y };
  const draw = () => gsap.set(ns[2], { x: live.x, y: live.y });

  const t = KIT.stepped((tl) => {
    gsap.set([ghost, ghostTag, arrow, pick, ...pkts, ...xs, tries, best, ...toD], { opacity: 0 });
    tl.from([s, ...ns], { opacity: 0, scale: 0.4, duration: 0.45, stagger: 0.08, ease: KIT.motion.pop })
      .add(waves[0](), '-=0.1').add(waves[1](), '<0.15').add(waves[2](), '<0.15')
      .addLabel('s0')
      .to(toD, { opacity: 1, duration: 0.4 })
      .to(best, { opacity: 1, duration: 0.4 })
      .to(toD, { opacity: 0.35, duration: 0.4 }, '<')
      .fromTo(arrow, { opacity: 0 }, { opacity: 1, duration: 0.4 })
      .to(pick, { opacity: 1, duration: 0.35 }, '<0.2')
      .addLabel('s1')
      .to(pick, { opacity: 0, duration: 0.25 })
      .set(ghost, { opacity: 0.45 })
      .to(live, { x: far.x, y: far.y, duration: 1.8, ease: 'sine.inOut', onUpdate: draw })
      .to(best, { opacity: 0.2, duration: 0.4 }, '<')
      .to(ghostTag, { opacity: 1, duration: 0.4 }, '-=0.6')
      .addLabel('s2')
      .to(tries, { opacity: 1, duration: 0.25 });
    pkts.forEach((p, i) => {
      tl.set(p, { attr: { cx: S.x + 30, cy: S.y - 10 }, opacity: 1 })
        .to(p, { attr: { cx: N[2].x - 20, cy: N[2].y + 6 }, duration: 0.42, ease: 'none' })
        .set(p, { opacity: 0 })
        .fromTo(xs[i], { opacity: 0, scale: 0.4, svgOrigin: `${N[2].x} ${N[2].y}` }, { opacity: 1, scale: 1, duration: 0.18 })
        .to(dots[i], { fill: KIT.css('--break'), duration: 0.15 }, '<')
        .to(xs[i], { opacity: i === 4 ? 1 : 0.15, duration: 0.15 });
    });
    tl.addLabel('s3');
  });

  return {
    enter(st) {
      t.enter(st);
      draw();
    },
    step: (n) => t.play(n),
    leave() {},
  };
};
