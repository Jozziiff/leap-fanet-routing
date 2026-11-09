/* === SCENES ===
   Concept animations: stylised, no numbers from the results. Each entry is a factory
   (slide) => { enter(step), step(n), leave() } used by engine.js. */
window.SCENES = window.SCENES || {};

/* === SCENE: TITLE SWARM (seeded, illustration only) ===
   Drones wander; links between close pairs redden near the range limit; a red ring marks each break. */
SCENES.swarm = function (slide) {
  const c = slide.querySelector('canvas.scene');
  const ctx = c.getContext('2d');
  const w = c.width;
  const h = c.height;
  const RANGE = 300;
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const drones = Array.from({ length: 11 }, () => ({ x: 80 + rnd() * (w - 160), y: 80 + rnd() * (h - 160), a: rnd() * 6.28, v: 0.7 + rnd() * 0.9 }));
  const links = new Map();
  let flashes = [];
  let running = false;

  function glyph(x, y, col) {
    ctx.strokeStyle = col;
    ctx.lineWidth = 2;
    for (const a of [0.785, 2.356, 3.927, 5.498]) {
      const ax = x + Math.cos(a) * 15, ay = y + Math.sin(a) * 15;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(ax, ay); ctx.stroke();
      ctx.beginPath(); ctx.arc(ax, ay, 8, 0, 6.283); ctx.stroke();
    }
    ctx.fillStyle = col;
    ctx.fillRect(x - 6, y - 6, 12, 12);
  }

  function frame() {
    if (!running) return;
    const ink = KIT.css('--ink'), red = KIT.css('--break');
    ctx.clearRect(0, 0, w, h);
    for (const d of drones) {
      d.a += (rnd() - 0.5) * 0.08;
      d.x += Math.cos(d.a) * d.v; d.y += Math.sin(d.a) * d.v;
      if (d.x < 40 || d.x > w - 40) d.a = Math.PI - d.a;
      if (d.y < 40 || d.y > h - 40) d.a = -d.a;
    }
    for (let i = 0; i < drones.length; i++) for (let j = i + 1; j < drones.length; j++) {
      const a = drones[i], b = drones[j];
      const dist = Math.hypot(a.x - b.x, a.y - b.y), key = i + '-' + j;
      if (dist < RANGE) {
        const t = Math.min(Math.max((dist / RANGE - 0.65) / 0.35, 0), 1);
        ctx.strokeStyle = gsap.utils.interpolate(ink, red, t);
        ctx.globalAlpha = 0.85 - 0.35 * t;
        ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        links.set(key, true);
      } else if (links.get(key)) {
        links.set(key, false);
        flashes.push({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, life: 1 });
      }
    }
    ctx.globalAlpha = 1;
    flashes = flashes.filter((f) => (f.life -= 0.02) > 0);
    for (const f of flashes) {
      ctx.strokeStyle = red; ctx.globalAlpha = f.life; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(f.x, f.y, 10 + (1 - f.life) * 28, 0, 6.283); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    drones.forEach((d) => glyph(d.x, d.y, ink));
    requestAnimationFrame(frame);
  }

  return {
    enter() { if (!running) { running = true; requestAnimationFrame(frame); } },
    step() {},
    leave() { running = false; },
  };
};

/* === SCENE A2: LINK BREAK ===
   s0: A sends to B, packets flow. s1: B drifts to the edge of A's range, the link reddens.
   s2: B leaves the range, the link snaps, the frame in flight is lost, the MAC tries 5 times. */
SCENES.linkbreak = function (slide) {
  const svg = slide.querySelector('svg.scene');
  const A = { x: 430, y: 300 };
  const B = { x: 650, y: 330 };
  const R = 430;
  KIT.ring(svg, A.x, A.y, R);
  KIT.text(svg, A.x + R * 0.71, A.y - R * 0.71 - 18, 'radio range');
  const link = KIT.link(svg, A, B);
  const pkt = KIT.packet(svg);
  const a = KIT.drone(svg, 'sender');
  const b = KIT.drone(svg);
  KIT.text(svg, A.x, A.y + 70, 'A', 'center ink');
  const bName = KIT.text(svg, 0, 0, 'B', 'center ink');
  const lost = KIT.el('g', {}, svg);
  KIT.cross(lost, 862, 552, 11);
  KIT.text(lost, 885, 560, 'frame lost', 'lost');
  const tries = KIT.attempts(svg, A.x - 90, A.y + 120, 5);
  const triesLabel = KIT.text(tries, 0, 48, '5 attempts to a neighbour that has left');
  const dots = [...tries.querySelectorAll('circle')];
  gsap.set(a, { x: A.x, y: A.y });

  let flowing = true;
  let p = 0;
  function draw() {
    gsap.set(b, { x: B.x, y: B.y });
    bName.setAttribute('x', B.x); bName.setAttribute('y', B.y + 70);
    link.update();
    link.style.stroke = KIT.stretch(Math.hypot(B.x - A.x, B.y - A.y), R);
    if (flowing) {
      p = (p + 0.012) % 1;
      pkt.setAttribute('cx', A.x + (B.x - A.x) * p);
      pkt.setAttribute('cy', A.y + (B.y - A.y) * p);
    }
  }

  const M = KIT.motion;
  const t = KIT.stepped((tl) => {
    tl.addLabel('s0')
      .to(B, { x: 830, y: 360, duration: M.drift, ease: M.move })
      .addLabel('s1')
      .to(B, { x: 1010, y: 380, duration: 1.6, ease: 'sine.in' })
      .add(() => { flowing = false; }, '-=0.6')
      .to(link, { opacity: 0, duration: 0.5 }, '-=0.3')
      .to(pkt, { attr: { cy: '+=160' }, opacity: 0, duration: 0.9, ease: M.fall }, '<')
      .fromTo(lost, { opacity: 0 }, { opacity: 1, duration: M.beat }, '<')
      .fromTo(dots, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, stagger: M.stagger, duration: 0.25, transformOrigin: 'center' })
      .to(dots, { fill: KIT.css('--break'), stagger: M.stagger, duration: 0.2 }, '<0.12')
      .fromTo(triesLabel, { opacity: 0 }, { opacity: 1, duration: M.beat }, '<')
      .addLabel('s2');
  });

  return {
    enter(step) {
      gsap.set(link, { opacity: 1 });
      gsap.set(pkt, { opacity: 1 });
      t.seek(step);
      flowing = step < 2;
      gsap.ticker.add(draw);
    },
    step(n) { t.play(n); },
    leave() { gsap.ticker.remove(draw); },
  };
};
