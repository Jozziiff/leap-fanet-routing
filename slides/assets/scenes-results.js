/* === SCENES · RESULTS ===
   A6 (slide 16): packet delivery at 20 m/s for Greedy, the reactive control and LEAP-GR.
   Data: figures/table_paired.csv, N = 30, 20 m/s, λ = 1, mean of 3 paired seeds
   (greedy 0.8401, greedy_reactive 0.9573, leap 0.9875). Bars start at zero; the red end of each bar is
   the share not delivered, so the gap reads directly.
   Reprise of A4 (slide 17): concept animation, no data. */
window.SCENES = window.SCENES || {};

/* === A6 · SAME MAC, SAME SEEDS, ONE CHANGE ===
   intro: the three bars grow from zero. s1: Greedy vs LEAP-GR, the gain shaded on LEAP-GR's bar.
   s2: reactive control vs LEAP-GR, the smaller gain shaded. */
SCENES.bars = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const rows = [
    { name: 'Greedy', sub: 'base protocol', v: 84.0, cls: '--ink' },
    { name: 'Reactive control', sub: 'Greedy + switch after a failure', v: 95.7, cls: '--reactive' },
    { name: 'LEAP-GR', sub: 'switch before the break', v: 98.7, cls: '--leap' },
  ];
  const X0 = 330, W = 560, H = 54, Y = [120, 240, 360];
  KIT.text(svg, 0, 30, 'Packets delivered at 20 m/s', 'big');
  /* legend */
  KIT.el('rect', { x: X0, y: 52, width: 18, height: 18, fill: KIT.css('--break') }, svg);
  KIT.text(svg, X0 + 26, 67, 'red end: packets not delivered', 'ink');

  const parts = rows.map((r, i) => {
    const y = Y[i] - H / 2;
    KIT.text(svg, 0, Y[i] - 2, r.name, 'big');
    KIT.text(svg, 0, Y[i] + 26, r.sub, '');
    const lost = KIT.el('rect', { x: X0, y, width: W, height: H, fill: KIT.css('--break') }, svg);
    const ok = KIT.el('rect', { x: X0, y, width: 0, height: H, fill: KIT.css(r.cls) }, svg);
    const gap = KIT.el('rect', { x: X0, y, width: 2, height: H, fill: '#fff' }, svg);
    const val = KIT.text(svg, X0 + 18, Y[i] + 9, r.v.toFixed(1) + ' %', 'white');
    val.style.fontWeight = 800; val.style.fontSize = '24px';
    const miss = KIT.text(svg, X0 + W + 16, Y[i] + 9, (100 - r.v).toFixed(1) + ' %', 'lost');
    return { lost, ok, gap, val, miss, w: (W * r.v) / 100, y };
  });
  /* gain shading: from the baseline's delivery to LEAP-GR's, drawn on LEAP-GR's row */
  function gainBand(fromV) {
    const x = X0 + (W * fromV) / 100;
    const g = KIT.el('g', {}, svg);
    KIT.el('line', { x1: x, y1: Y[0] - H / 2 - 6, x2: x, y2: Y[2] + H / 2 + 6, class: 'edge dash' }, g);
    KIT.el('rect', { x, y: Y[2] - H / 2 - 8, width: X0 + (W * 98.7) / 100 - x, height: H + 16, fill: 'none', stroke: KIT.css('--leap'), 'stroke-width': 4 }, g);
    return g;
  }
  const g1 = gainBand(84.0), g2 = gainBand(95.7);
  KIT.text(svg, 0, 440, 'N = 30 drones · λ = 1 packet/s per drone · mean of 3 paired seeds', '');

  const t = KIT.stepped((tl) => {
    gsap.set([g1, g2], { opacity: 0 });
    parts.forEach((p, i) => {
      gsap.set([p.lost, p.val, p.miss], { opacity: 0 });
      tl.set(p.lost, { opacity: 1 }, i * 0.25)
        .fromTo(p.ok, { attr: { width: 0 } }, { attr: { width: p.w }, duration: 1.1, ease: 'power3.out' }, i * 0.25)
        .fromTo(p.gap, { attr: { x: X0 } }, { attr: { x: X0 + p.w }, duration: 1.1, ease: 'power3.out' }, i * 0.25)
        .to([p.val, p.miss], { opacity: 1, duration: 0.3 }, i * 0.25 + 0.8);
    });
    tl.addLabel('s0')
      .to(g1, { opacity: 1, duration: 0.4 })
      .to([parts[1].ok, parts[1].lost], { opacity: 0.25, duration: 0.4 }, '<')
      .addLabel('s1')
      .to(g1, { opacity: 0, duration: 0.3 })
      .to([parts[1].ok, parts[1].lost], { opacity: 1, duration: 0.3 }, '<')
      .to([parts[0].ok, parts[0].lost], { opacity: 0.25, duration: 0.3 }, '<')
      .to(g2, { opacity: 1, duration: 0.4 })
      .addLabel('s2');
  });
  return { enter: (s) => t.enter(s), step: (n) => t.play(n), leave() {} };
};

/* === A4 REPRISE · WHY IT WORKS ===
   The same stale neighbour as in "Greedy picks the edge": its last hello, extrapolated to now, is
   already out of range (τ̂ = 0). Greedy's arrow to it is struck out; LEAP-GR forwards to F instead and
   the packets keep flowing (blue). */
SCENES.reprise = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const S = { x: 140, y: 330 }, R = 190, D = { x: 560, y: 330 };
  const G = { x: 312, y: 255 }, far = { x: 470, y: 180 }, F = { x: 300, y: 420 };
  KIT.ring(svg, S.x, S.y, R);
  KIT.target(svg, D.x, D.y, 'D');
  placeDrone(svg, far.x, far.y, '', 0.7).style.opacity = 0.25;
  const ghost = placeDrone(svg, G.x, G.y, 'ghost');
  const greedy = KIT.arrow(svg, 'soft');
  greedy.set(S.x + 34, S.y - 18, G.x - 34, G.y + 16);
  const strike = KIT.cross(svg, (S.x + G.x) / 2 + 4, (S.y + G.y) / 2 - 2, 16);
  const leap = KIT.arrow(svg, 'leap');
  leap.set(S.x + 36, S.y + 18, F.x - 36, F.y - 14);
  const pkt = KIT.packet(svg);
  placeDrone(svg, S.x, S.y, 'sender');
  KIT.text(svg, S.x, S.y + 62, 'S', 'center ink');
  placeDrone(svg, F.x, F.y);
  KIT.text(svg, F.x, F.y + 62, 'F', 'center ink');
  const c1 = KIT.chip(svg, 20, 90, 'last hello, extrapolated: already gone');
  const c2 = KIT.chip(svg, 20, 140, 'τ̂ = 0: skip it', '');
  const c3 = KIT.chip(svg, 20, 590, 'LEAP-GR forwards to F', 'leap');
  const st = { p: 0, on: false };
  function flow() {
    if (!st.on) return;
    st.p = (st.p + 0.016) % 1;
    pkt.setAttribute('cx', S.x + (F.x - S.x) * st.p);
    pkt.setAttribute('cy', S.y + (F.y - S.y) * st.p);
  }
  const t = KIT.stepped((tl) => {
    gsap.set([ghost, greedy, strike, leap, pkt, c1, c2, c3], { opacity: 0 });
    tl.to(greedy, { opacity: 1, duration: 0.4 }, 0.3)
      .to(ghost, { opacity: 0.45, duration: 0.4 }, '<')
      .to(c1, { opacity: 1, duration: 0.4 })
      .to(c2, { opacity: 1, duration: 0.4 }, '+=0.3')
      .fromTo(strike, { opacity: 0, scale: 0.4, svgOrigin: `${(S.x + G.x) / 2 + 4} ${(S.y + G.y) / 2 - 2}` }, { opacity: 1, scale: 1, duration: 0.3, ease: KIT.motion.pop }, '<')
      .to(leap, { opacity: 1, duration: 0.4 }, '+=0.2')
      .add(() => { st.on = true; })
      .to([pkt, c3], { opacity: 1, duration: 0.3 })
      .addLabel('s0');
  });
  return {
    enter(s) { st.on = false; t.enter(s); gsap.ticker.add(flow); },
    step() {},
    leave() { gsap.ticker.remove(flow); },
  };
};
