/* === SCENE KIT ===
   The shared vocabulary of every concept animation, so all scenes look like one film:
   drone (sender / plain / ghost), range ring, link, packet, tags, attempt dots.
   Styles live in deck.css (.drone, .ring, .link, .packet, .tag, .retry); timing lives in KIT.motion. */
window.KIT = (function () {
  const NS = 'http://www.w3.org/2000/svg';

  /* colour tokens never change during the talk: read each one from CSS once */
  const cache = new Map();
  const css = (name) => {
    if (!cache.has(name)) cache.set(name, getComputedStyle(document.documentElement).getPropertyValue(name).trim());
    return cache.get(name);
  };

  /* motion tokens for GSAP timelines (the CSS twin is --ease / --rise in deck.css) */
  const motion = {
    move: 'sine.inOut', // drones drifting
    snap: 'power3.inOut', // Swiss cut: decisive in, decisive out
    pop: 'back.out(1.7)', // marks appearing (crosses, ticks)
    fall: 'power2.in', // a lost packet dropping
    beat: 0.4, // one small event
    drift: 2.2, // one drone movement
    stagger: 0.28, // between repeated marks (MAC attempts)
  };

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  }

  function text(parent, x, y, str, cls) {
    const t = el('text', { x, y, class: 'tag ' + (cls || '') }, parent);
    t.textContent = str;
    return t;
  }

  /* top-view quadcopter centred on (0, 0); position it with gsap.set(g, {x, y}) */
  function drone(parent, cls) {
    const g = el('g', { class: 'drone ' + (cls || '') }, parent);
    for (const a of [45, 135, 225, 315]) {
      const r = (a * Math.PI) / 180;
      const x = Math.cos(r) * 26;
      const y = Math.sin(r) * 26;
      el('line', { x1: 0, y1: 0, x2: x, y2: y, class: 'arm' }, g);
      const rotor = el('g', { transform: `translate(${x} ${y})` }, g);
      el('circle', { r: 15, class: 'rotor' }, rotor);
      el('line', { x1: -12, y1: 0, x2: 12, y2: 0 }, el('g', { class: 'blade' }, rotor));
    }
    el('rect', { x: -11, y: -11, width: 22, height: 22, rx: 6, class: 'body' }, g);
    return g;
  }

  function ring(parent, cx, cy, r, cls) {
    return el('circle', { cx, cy, r, class: 'ring ' + (cls || '') }, parent);
  }

  /* a link that follows two moving points {x, y}; call .update() every tick */
  function link(parent, a, b, cls) {
    const line = el('line', { class: 'link ' + (cls || '') }, parent);
    line.update = () => {
      line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
      line.setAttribute('x2', b.x); line.setAttribute('y2', b.y);
    };
    line.update();
    return line;
  }

  function packet(parent) {
    return el('circle', { cx: 0, cy: 0, r: 9, class: 'packet' }, parent);
  }

  /* red cross or blue tick, centred on (x, y) */
  function cross(parent, x, y, size) {
    const s = size || 14;
    const g = el('g', { transform: `translate(${x} ${y})` }, parent);
    el('line', { x1: -s, y1: -s, x2: s, y2: s, stroke: css('--break'), 'stroke-width': 5 }, g);
    el('line', { x1: -s, y1: s, x2: s, y2: -s, stroke: css('--break'), 'stroke-width': 5 }, g);
    return g;
  }
  function tick(parent, x, y, size, color) {
    const s = size || 14;
    const g = el('g', { transform: `translate(${x} ${y})` }, parent);
    el('polyline', { points: `${-s},0 ${-s / 3},${s * 0.7} ${s},${-s * 0.7}`, fill: 'none', stroke: css(color || '--leap'), 'stroke-width': 5 }, g);
    return g;
  }

  /* a row of n MAC attempt dots starting at (x, y), spaced by gap */
  function attempts(parent, x, y, n, gap) {
    const g = el('g', { transform: `translate(${x} ${y})` }, parent);
    for (let i = 0; i < n; i++) el('circle', { cx: i * (gap || 45), cy: 0, r: 12, class: 'retry' }, g);
    return g;
  }

  /* link colour from ink to red as the distance d approaches the range r */
  function stretch(d, r) {
    const t = Math.min(Math.max((d / r - 0.6) / 0.4, 0), 1);
    return gsap.utils.interpolate(css('--ink'), css('--break'), t);
  }

  /* a timeline with labels s0..sN. Everything before s0 is the scene's intro: it plays when the slide
     opens at step 0, and is skipped when the deck lands on a later step (going back, deep links). */
  function stepped(build) {
    const tl = gsap.timeline({ paused: true });
    build(tl);
    return {
      tl,
      seek(step) { tl.seek('s' + step).pause(); },
      play(step) { tl.tweenTo('s' + step); },
      enter(step) {
        if (step === 0) { tl.seek(0).pause(); tl.tweenTo('s0'); } else tl.seek('s' + step).pause();
      },
    };
  }

  /* straight arrow with a drawn head; .set(x1, y1, x2, y2) moves it */
  function arrow(parent, cls) {
    const g = el('g', { class: 'arrow ' + (cls || '') }, parent);
    const line = el('line', {}, g);
    const head = el('polygon', { points: '0,0 -18,-9 -18,9' }, g);
    g.set = (x1, y1, x2, y2) => {
      const a = Math.atan2(y2 - y1, x2 - x1);
      const back = 16;
      line.setAttribute('x1', x1); line.setAttribute('y1', y1);
      line.setAttribute('x2', x2 - Math.cos(a) * back); line.setAttribute('y2', y2 - Math.sin(a) * back);
      head.setAttribute('transform', `translate(${x2} ${y2}) rotate(${(a * 180) / Math.PI})`);
    };
    return g;
  }

  /* destination marker: a square target with its letter */
  function target(parent, x, y, letter) {
    const g = el('g', { class: 'target', transform: `translate(${x} ${y})` }, parent);
    el('rect', { x: -30, y: -30, width: 60, height: 60, class: 'outer' }, g);
    el('rect', { x: -16, y: -16, width: 32, height: 32, class: 'inner' }, g);
    text(g, 0, 62, letter || 'D', 'center big');
    return g;
  }

  /* expanding hello ring from (x, y): returns a tween factory for a timeline */
  function pulse(parent, x, y, r, cls) {
    const c = el('circle', { cx: x, cy: y, r: 10, class: 'wave ' + (cls || '') }, parent);
    gsap.set(c, { opacity: 0 });
    /* a nested timeline, so the ring is invisible before and after its own pulse, also when seeking */
    return (dur) => gsap.timeline()
      .set(c, { attr: { r: 10 }, opacity: 0.9, immediateRender: false }, 0)
      .to(c, { attr: { r }, opacity: 0, duration: dur || 0.9, ease: 'power1.out' }, 0);
  }

  /* horizontal lifetime gauge: bar length = value in [0, 1], a tick marks the threshold */
  function gauge(parent, x, y, w, thr, label) {
    const g = el('g', { class: 'gauge', transform: `translate(${x} ${y})` }, parent);
    el('rect', { x: 0, y: 0, width: w, height: 18, class: 'track' }, g);
    const bar = el('rect', { x: 0, y: 0, width: w, height: 18, class: 'fill' }, g);
    el('line', { x1: w * thr, y1: -10, x2: w * thr, y2: 28, class: 'thr' }, g);
    text(g, w * thr, -18, 'τth', 'center');
    text(g, -14, 15, label || 'τ̂', 'ink end');
    g.value = (v) => {
      bar.setAttribute('width', Math.max(0, Math.min(1, v)) * w);
      bar.classList.toggle('low', v < thr);
    };
    return g;
  }

  /* a square MAC attempt slot; mark(kind) shows 'fail' (red cross), 'col' (grey burst) or 'ok' (tick) */
  function slot(parent, x, y, s) {
    const g = el('g', { class: 'slot', transform: `translate(${x} ${y})` }, parent);
    const box = el('rect', { x: -s / 2, y: -s / 2, width: s, height: s, class: 'box' }, g);
    g.box = box;
    return g;
  }

  return { NS, css, motion, el, text, drone, ring, link, packet, cross, tick, attempts, stretch, stepped, arrow, target, pulse, gauge, slot };
})();

/* label chip: white box with ink text (or blue with white text for LEAP); width follows the text */
KIT.chip = function (parent, x, y, str, cls) {
  const g = KIT.el('g', { class: 'chip ' + (cls || ''), transform: `translate(${x} ${y})` }, parent);
  const r = KIT.el('rect', { x: 0, y: -25, height: 38 }, g);
  const t = KIT.text(g, 14, 1, str, 'ink');
  let w = str.length * 10.5;
  try { w = t.getComputedTextLength() || w; } catch (e) { /* not laid out yet */ }
  r.setAttribute('width', w + 28);
  return g;
};

/* collision burst: eight short grey rays around (x, y) */
KIT.burst = function (parent, x, y, r) {
  const g = KIT.el('g', { transform: `translate(${x} ${y})` }, parent);
  for (let k = 0; k < 8; k++) {
    const a = (k * Math.PI) / 4;
    KIT.el('line', { x1: Math.cos(a) * r * 0.45, y1: Math.sin(a) * r * 0.45, x2: Math.cos(a) * r, y2: Math.sin(a) * r,
      stroke: KIT.css('--muted'), 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
  }
  return g;
};

/* drone placed at (x, y), drawn at 80 % so several fit in one scene */
function placeDrone(svg, x, y, cls, scale) {
  const d = KIT.drone(svg, cls);
  gsap.set(d, { x, y, scale: scale || 0.8 });
  return d;
}
function whiteCross(parent, x, y, s) {
  const g = KIT.el('g', { transform: `translate(${x} ${y})` }, parent);
  KIT.el('line', { x1: -s, y1: -s, x2: s, y2: s, stroke: '#fff', 'stroke-width': 5 }, g);
  KIT.el('line', { x1: -s, y1: s, x2: s, y2: -s, stroke: '#fff', 'stroke-width': 5 }, g);
  return g;
}
