/* === SCENES · LEAP-GR ===
   A10 (slide 12): the link lifetime τ̂ from one hello. A5 (slide 13): the switching rule.
   A11 (slide 14): repair through the platform's penalize hook, MAC unchanged.
   Concept animations: stylised geometry, no measured numbers. Blue always means LEAP-GR. */
window.SCENES = window.SCENES || {};

/* point where the ray p + v·t leaves the circle (c, r); t >= 0 */
function exitPoint(p, v, c, r) {
  const dx = p.x - c.x, dy = p.y - c.y;
  const a = v.x * v.x + v.y * v.y, b = dx * v.x + dy * v.y, k = dx * dx + dy * dy - r * r;
  const t = (-b + Math.sqrt(b * b - a * k)) / a;
  return { x: p.x + v.x * t, y: p.y + v.y * t, t };
}

/* === A10 · HOW LONG WILL THIS LINK LAST? ===
   intro: B sends a hello that carries its position and velocity to A.
   s1: time passes: B has moved; A only knows the hello (ghost) and extrapolates B to now.
   s2: following the relative motion, the predicted B reaches the edge of A's range; the gauge τ̂
   empties as it goes: that remaining time is the link lifetime. */
SCENES.lifetime = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const A = { x: 300, y: 240 }, R = 190;
  const H = { x: 310, y: 150 }; // where B's last hello says it was
  const V = { x: 91, y: 91 }; // B's velocity relative to A, drawn per second of animation
  const P = { x: H.x + V.x * 0.55, y: H.y + V.y * 0.55 }; // where B is now
  const X = exitPoint(P, V, A, R); // where the relative motion leaves A's range
  const U = { x: V.x / Math.hypot(V.x, V.y), y: V.y / Math.hypot(V.x, V.y) };

  KIT.ring(svg, A.x, A.y, R);
  KIT.text(svg, A.x - R + 4, A.y + R + 34, 'A’s range', '');
  const path = KIT.el('line', { x1: P.x, y1: P.y, x2: X.x, y2: X.y, class: 'edge leap dash' }, svg);
  const dr = KIT.el('line', { x1: H.x, y1: H.y, x2: P.x, y2: P.y, class: 'edge dash' }, svg);
  const ghost = placeDrone(svg, H.x, H.y, 'ghost');
  const ghostTag = KIT.text(svg, H.x, H.y - 48, 'last hello', 'center');
  const nowTag = KIT.text(svg, P.x + 46, P.y - 20, 'extrapolated now', 'ink');
  const wave = KIT.pulse(svg, H.x, H.y, 140, 'leap');
  const hello = KIT.chip(svg, 0, 0, 'hello: position + velocity', 'leap');
  const vel = KIT.arrow(svg, 'thin');
  const a = placeDrone(svg, A.x, A.y, 'sender');
  KIT.text(svg, A.x, A.y + 62, 'A', 'center ink');
  const b = placeDrone(svg, H.x, H.y);
  const bTag = KIT.text(svg, H.x, H.y - 46, 'B', 'center ink');
  const pred = KIT.el('circle', { r: 16, fill: 'none', stroke: KIT.css('--leap'), 'stroke-width': 4 }, svg);
  const endX = KIT.cross(svg, X.x, X.y, 16);
  const endTag = KIT.text(svg, X.x + 26, X.y + 8, 'link ends', 'lost');
  const gauge = KIT.gauge(svg, 640, 420, 340, 0.25, 'τ̂');
  const gTag = KIT.text(svg, 640, 366, 'time left on the link', 'ink');
  const eq = KIT.text(svg, 640, 60, '‖Δp + Δv · τ̂‖ = R', 'big');
  const eqTag = KIT.text(svg, 640, 92, 'distance, relative speed, range', '');

  const live = { x: H.x, y: H.y };
  const pr = { x: P.x, y: P.y };
  const g = { v: 1 };
  function draw() {
    gsap.set(b, { x: live.x, y: live.y });
    bTag.setAttribute('x', live.x); bTag.setAttribute('y', live.y - 46);
    vel.set(live.x + U.x * 36, live.y + U.y * 36, live.x + U.x * 110, live.y + U.y * 110);
    pred.setAttribute('cx', pr.x); pred.setAttribute('cy', pr.y);
    gauge.value(g.v);
  }

  const t = KIT.stepped((tl) => {
    gsap.set([path, dr, ghost, ghostTag, nowTag, hello, pred, endX, endTag, gauge, gTag, eq, eqTag], { opacity: 0 });
    tl.from([a, b], { opacity: 0, scale: 0.4, duration: 0.45, stagger: 0.1, ease: KIT.motion.pop })
      .add(wave(1.0))
      .fromTo(hello, { opacity: 0, x: H.x + 40, y: H.y - 70 }, { opacity: 1, duration: 0.3 }, '<0.1')
      .to(hello, { x: 10, y: A.y + 130, duration: 1.1, ease: 'power2.inOut' })
      .from(vel, { opacity: 0, duration: 0.4 }, '<0.3')
      .addLabel('s0')
      .to(hello, { opacity: 0, duration: 0.3 })
      .set(ghost, { opacity: 0.45 })
      .to(live, { x: P.x, y: P.y, duration: 1.4, ease: 'none', onUpdate: draw })
      .to([dr, ghostTag], { opacity: 1, duration: 0.4 }, '-=0.5')
      .to(nowTag, { opacity: 1, duration: 0.4 }, '<0.2')
      .addLabel('s1')
      .to([nowTag, ghostTag, vel], { opacity: 0.25, duration: 0.3 })
      .to([eq, eqTag, gauge, gTag], { opacity: 1, duration: 0.4 }, '<')
      .to(path, { opacity: 1, duration: 0.3 })
      .set(pred, { opacity: 1 })
      .to(pr, { x: X.x, y: X.y, duration: 2.4, ease: 'none', onUpdate: draw })
      .to(g, { v: 0, duration: 2.4, ease: 'none', onUpdate: draw }, '<')
      .fromTo(endX, { opacity: 0, scale: 0.4, svgOrigin: `${X.x} ${X.y}` }, { opacity: 1, scale: 1, duration: 0.3, ease: KIT.motion.pop })
      .to(endTag, { opacity: 1, duration: 0.3 }, '<')
      .addLabel('s2');
  });

  return {
    enter(s) { t.enter(s); draw(); },
    step: (n) => t.play(n),
    leave() {},
  };
};

/* === A5 · GREEDY, UNLESS THE LINK IS ABOUT TO BREAK ===
   intro: S, its range, D, two neighbours: E (Greedy's choice, near the edge) and F (safe), with their
   lifetime gauges. Packets flow on the chosen link all along.
   s0: Greedy's choice is E.  s1: E's link will last: keep it.
   s2: E drifts to the edge, its τ̂ falls under τth: switch to F (blue).
   s3: if F were not safe either (gauge low), keep Greedy's choice: never worse than Greedy. */
SCENES.rule = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const S = { x: 190, y: 250 }, R = 190, D = { x: 975, y: 230 };
  const E0 = { x: 345, y: 185 }, E1 = { x: 372, y: 170 }, F = { x: 320, y: 335 };

  KIT.ring(svg, S.x, S.y, R);
  KIT.target(svg, D.x, D.y, 'D');
  const choice = KIT.arrow(svg);
  const pkt = KIT.packet(svg);
  const s = placeDrone(svg, S.x, S.y, 'sender');
  KIT.text(svg, S.x, S.y + 62, 'S', 'center ink');
  const e = placeDrone(svg, E0.x, E0.y);
  const eTag = KIT.text(svg, 0, 0, 'E', 'center ink');
  const f = placeDrone(svg, F.x, F.y);
  KIT.text(svg, F.x, F.y + 62, 'F', 'center ink');
  const gE = KIT.gauge(svg, 640, 330, 300, 0.25, 'τ̂ to E');
  const gF = KIT.gauge(svg, 640, 410, 300, 0.25, 'τ̂ to F');
  const tag = KIT.chip(svg, 600, 90, 'Greedy’s choice: E');
  const keep = KIT.chip(svg, 600, 160, 'link will last: keep E');
  const sw = KIT.chip(svg, 600, 160, 'about to break: switch to F', 'leap');
  const none = KIT.chip(svg, 600, 230, 'no safe neighbour: keep E', '');

  const st = { e: { x: E0.x, y: E0.y }, to: 'E', ge: 0.8, gf: 0.9, p: 0 };
  function aim() { return st.to === 'E' ? st.e : F; }
  function draw() {
    gsap.set(e, { x: st.e.x, y: st.e.y });
    eTag.setAttribute('x', st.e.x); eTag.setAttribute('y', st.e.y - 46);
    const tg = aim();
    const ang = Math.atan2(tg.y - S.y, tg.x - S.x);
    choice.set(S.x + Math.cos(ang) * 40, S.y + Math.sin(ang) * 40, tg.x - Math.cos(ang) * 40, tg.y - Math.sin(ang) * 40);
    choice.setAttribute('class', 'arrow ' + (st.to === 'F' ? 'leap' : ''));
    gE.value(st.ge); gF.value(st.gf);
  }
  function flow() {
    st.p = (st.p + 0.015) % 1;
    const tg = aim();
    pkt.setAttribute('cx', S.x + (tg.x - S.x) * st.p);
    pkt.setAttribute('cy', S.y + (tg.y - S.y) * st.p);
    pkt.style.fill = st.to === 'F' ? KIT.css('--leap') : KIT.css('--ink');
  }

  const t = KIT.stepped((tl) => {
    gsap.set([tag, keep, sw, none, choice, pkt], { opacity: 0 });
    tl.from([s, e, f], { opacity: 0, scale: 0.4, duration: 0.45, stagger: 0.1, ease: KIT.motion.pop })
      .from([gE, gF], { opacity: 0, duration: 0.4 })
      .to([choice, pkt], { opacity: 1, duration: 0.4 })
      .to(tag, { opacity: 1, duration: 0.4 }, '<')
      .addLabel('s0')
      .to(keep, { opacity: 1, duration: 0.4 })
      .addLabel('s1')
      .to(keep, { opacity: 0, duration: 0.25 })
      .to(st.e, { x: E1.x, y: E1.y, duration: 1.6, ease: 'sine.inOut', onUpdate: draw })
      .to(st, { ge: 0.12, duration: 1.6, ease: 'power1.in', onUpdate: draw }, '<')
      .add(() => { st.to = 'F'; draw(); })
      .to(sw, { opacity: 1, duration: 0.4 })
      .addLabel('s2')
      .to(st, { gf: 0.1, duration: 1.0, ease: 'power1.in', onUpdate: draw })
      .to(f, { opacity: 0.35, duration: 0.5 }, '<')
      .add(() => { st.to = 'E'; draw(); })
      .to(sw, { opacity: 0.25, duration: 0.3 }, '<')
      .to(none, { opacity: 1, duration: 0.4 })
      .addLabel('s3');
  });

  /* which neighbour gets the packets at each step (callbacks do not run on seeks) */
  const target = ['E', 'E', 'F', 'E'];
  return {
    enter(n) { st.to = target[n]; t.enter(n); draw(); gsap.ticker.add(flow); },
    step(n) { t.play(n); },
    leave() { gsap.ticker.remove(flow); },
  };
};

/* === A11 · THE MAC STAYS THE SAME ===
   intro: the protocol stack on the left, S, E (about to break) and F on the right.
   s0: the frame to E gets no ACK; the MAC calls penalize() on the routing layer.
   s1: LEAP-GR sees E's lifetime under τth and redirects the retry to F; the ACK comes back.
   s2: the reactive control is shown beside it: same hook, but it redirects after every timeout. */
SCENES.repair = function (slide) {
  const svg = slide.querySelector('svg.scene');
  function layer(y, title, sub, cls) {
    const g = KIT.el('g', { class: 'chip ' + (cls || ''), transform: `translate(30 ${y})` }, svg);
    KIT.el('rect', { x: 0, y: 0, width: 380, height: 92 }, g);
    KIT.text(g, 20, 40, title, 'big' + (cls === 'leap' ? ' white' : ''));
    KIT.text(g, 20, 70, sub, cls === 'leap' ? 'white' : '');
    return g;
  }
  const route = layer(40, 'Routing · LEAP-GR', 'routing/leap/, our module', 'leap');
  const mac = layer(200, 'MAC · CSMA/CA', 'the platform’s code, unchanged');
  layer(360, 'PHY + channel', 'unchanged');
  const macBox = mac.querySelector('rect');
  const up = KIT.arrow(svg, 'red thin');
  up.set(330, 196, 330, 140);
  const upTag = KIT.text(svg, 344, 176, 'penalize()', 'lost');

  const S = { x: 600, y: 270 }, E = { x: 800, y: 160 }, F = { x: 770, y: 390 };
  KIT.ring(svg, S.x, S.y, 225, 'soft');
  const toE = KIT.arrow(svg);
  toE.set(S.x + 36, S.y - 20, E.x - 36, E.y + 20);
  const toF = KIT.arrow(svg, 'leap');
  toF.set(S.x + 36, S.y + 22, F.x - 36, F.y - 22);
  placeDrone(svg, S.x, S.y, 'sender');
  KIT.text(svg, S.x - 50, S.y + 8, 'S', 'center ink');
  placeDrone(svg, E.x, E.y);
  KIT.text(svg, E.x, E.y - 46, 'E', 'center ink');
  placeDrone(svg, F.x, F.y);
  KIT.text(svg, F.x, F.y + 62, 'F', 'center ink');
  const p1 = KIT.packet(svg), p2 = KIT.packet(svg);
  const xE = KIT.cross(svg, E.x, E.y, 18);
  const noAck = KIT.text(svg, E.x + 50, E.y + 8, 'no ACK', 'lost');
  const okF = KIT.tick(svg, F.x + 56, F.y, 16);
  const ack = KIT.text(svg, F.x + 82, F.y + 8, 'ACK', 'leap');
  const why = KIT.chip(svg, 440, 30, 'τ̂ to E < τth: retry via F', 'leap');
  const ctl = KIT.chip(svg, 440, 84, 'reactive control: switch after every timeout', 'soft');

  const t = KIT.stepped((tl) => {
    gsap.set([up, upTag, toF, p1, p2, xE, noAck, okF, ack, why, ctl], { opacity: 0 });
    tl.from(svg.querySelectorAll('.chip:not(.soft), .drone'), { opacity: 0, y: 10, duration: 0.45, stagger: 0.06 })
      .from(toE, { opacity: 0, duration: 0.4 })
      .addLabel('s0-start')
      .set(p1, { attr: { cx: S.x + 36, cy: S.y - 20 }, opacity: 1 })
      .to(p1, { attr: { cx: E.x - 26, cy: E.y + 14 }, duration: 0.7, ease: 'none' })
      .set(p1, { opacity: 0 })
      .fromTo(xE, { opacity: 0, scale: 0.4, svgOrigin: `${E.x} ${E.y}` }, { opacity: 1, scale: 1, duration: 0.25, ease: KIT.motion.pop })
      .to(noAck, { opacity: 1, duration: 0.25 }, '<')
      .to(macBox, { stroke: KIT.css('--break'), duration: 0.25 })
      .to([up, upTag], { opacity: 1, duration: 0.35 })
      .addLabel('s0')
      .to(why, { opacity: 1, duration: 0.4 })
      .to(toE, { opacity: 0.2, duration: 0.3 })
      .to(toF, { opacity: 1, duration: 0.3 }, '<')
      .set(p2, { attr: { cx: S.x + 36, cy: S.y + 22 }, opacity: 1 })
      .to(p2, { attr: { cx: F.x - 26, cy: F.y - 16 }, duration: 0.7, ease: 'none' })
      .set(p2, { opacity: 0 })
      .to([okF, ack], { opacity: 1, duration: 0.3 })
      .to(macBox, { stroke: KIT.css('--ink'), duration: 0.3 }, '<')
      .addLabel('s1')
      .to(ctl, { opacity: 1, duration: 0.4 })
      .addLabel('s2');
  });

  return { enter: (s) => t.enter(s), step: (n) => t.play(n), leave() {} };
};
