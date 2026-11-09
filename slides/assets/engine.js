/* === DECK ENGINE ===
   Fixed 1920x1080 stage scaled to the window, keyboard and click navigation, per-slide steps,
   presenter sync over a BroadcastChannel.

   A slide with data-steps="N" takes N presses of -> before the deck moves on. Elements with
   data-reveal="k" get the class .in from step k. A slide with data-scene="name" drives the scene
   registered as SCENES[name]: a factory (slide) => { enter(step), step(n), leave() }.

   URL options: #<slide>.<step> opens that slide and step; ?snap skips entrance animations;
   ?mirror makes the deck follow the presenter channel without broadcasting (presenter previews);
   ?mirror&ahead=1 shows the state one press ahead. */
(function () {
  const stage = document.querySelector('.deck-stage');
  const slides = [...document.querySelectorAll('.slide')];
  const params = new URLSearchParams(location.search);
  const mirror = params.has('mirror');
  const ahead = Number(params.get('ahead') || 0);
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('leap-deck') : null;
  const scenes = new Map();
  let current = 0;
  let step = 0;

  const stepsOf = (i) => Number(slides[i].dataset.steps || 0);

  /* section navigation: every section stays visible; the current one grows and a block slides behind it */
  const navItems = [...document.querySelectorAll('.sections [data-section]')];
  const slider = document.querySelector('.sections .slider');
  let follow = 0;

  function updateNav() {
    const sec = slides[current].dataset.section;
    navItems.forEach((b) => {
      b.classList.toggle('on', b.dataset.section === sec);
      if (b.dataset.section === sec) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
    });
    const on = navItems.find((b) => b.dataset.section === sec);
    if (!slider) return;
    slider.style.opacity = on ? 1 : 0;
    if (!on) return;
    /* the label's size animates for ~0.55 s; keep re-aiming the block at its live box until it settles */
    const until = performance.now() + 700;
    cancelAnimationFrame(follow);
    const aim = () => {
      gsap.to(slider, { x: on.offsetLeft, width: on.offsetWidth, duration: 0.6, ease: 'power3.out', overwrite: true });
      if (performance.now() < until) follow = requestAnimationFrame(aim);
    };
    aim();
  }

  navItems.forEach((b) => b.addEventListener('click', (e) => {
    e.stopPropagation();
    const first = slides.findIndex((s) => s.dataset.section === b.dataset.section);
    if (first >= 0 && !mirror) show(first, 0);
  }));

  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(${(innerWidth - 1920 * s) / 2}px, ${(innerHeight - 1080 * s) / 2}px) scale(${s})`;
  }

  /* a scene that throws must never block navigation: its errors are logged and the slide stays usable */
  function guard(scene, name) {
    const wrap = {};
    for (const k of ['enter', 'step', 'leave']) {
      wrap[k] = (...args) => {
        try { scene[k]?.(...args); } catch (err) { console.error(`scene ${name}.${k}`, err); }
      };
    }
    return wrap;
  }

  function sceneOf(i) {
    const name = slides[i].dataset.scene;
    if (!name || !window.SCENES || !window.SCENES[name]) return null;
    if (!scenes.has(i)) {
      let scene = null;
      try { scene = guard(window.SCENES[name](slides[i]), name); } catch (err) { console.error(`scene ${name}`, err); }
      scenes.set(i, scene);
    }
    return scenes.get(i);
  }

  function reveal() {
    slides[current].querySelectorAll('[data-reveal]').forEach((el) => {
      el.classList.toggle('in', Number(el.dataset.reveal) <= step);
    });
  }

  function broadcast() {
    if (channel && !mirror) channel.postMessage({ slide: current, step, total: slides.length });
    if (!mirror) history.replaceState(null, '', `${location.search}#${current + 1}.${step}`);
  }

  function show(index, atStep) {
    if (index !== current) sceneOf(current)?.leave?.();
    slides.forEach((el, i) => el.classList.toggle('active', i === index));
    current = index;
    step = Math.min(atStep, stepsOf(index));
    sceneOf(current)?.enter(step);
    document.querySelectorAll('[data-page]').forEach((el) => {
      el.textContent = `${String(current + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
    });
    reveal();
    updateNav();
    broadcast();
  }

  function next() {
    if (step < stepsOf(current)) {
      step += 1;
      sceneOf(current)?.step(step);
      reveal();
      broadcast();
    } else if (current < slides.length - 1) show(current + 1, 0);
  }

  function back() {
    if (step > 0) show(current, step - 1);
    else if (current > 0) show(current - 1, stepsOf(current - 1));
  }

  /* the state one press ahead of (slide, step), for the presenter's "next" preview */
  function advance(i, s, n) {
    for (let k = 0; k < n; k++) {
      if (s < stepsOf(i)) s += 1;
      else if (i < slides.length - 1) { i += 1; s = 0; }
    }
    return [i, s];
  }

  function command(cmd) {
    if (cmd === 'next') next();
    else if (cmd === 'back') back();
    else if (cmd === 'first') show(0, 0);
    else if (cmd === 'last') show(slides.length - 1, 0);
    else if (cmd === 'black') document.documentElement.classList.toggle('black');
  }

  if (channel) {
    channel.onmessage = (e) => {
      const m = e.data || {};
      if (mirror && 'slide' in m) {
        const [i, s] = advance(m.slide, m.step, ahead);
        show(i, s);
      }
      if (!mirror && m.cmd) command(m.cmd);
      if (!mirror && m.hello) broadcast();
    };
  }

  addEventListener('resize', fit);
  if (!mirror) {
    addEventListener('keydown', (e) => {
      if (e.target.closest && e.target.closest('input, textarea')) return; /* sliders keep their arrow keys */
      if (['ArrowRight', ' ', 'PageDown', 'Enter'].includes(e.key)) { e.preventDefault(); next(); }
      else if (['ArrowLeft', 'PageUp', 'Backspace'].includes(e.key)) { e.preventDefault(); back(); }
      else if (e.key === 'Home') show(0, 0);
      else if (e.key === 'End') show(slides.length - 1, 0);
      else if (e.key === 'f') document.documentElement.requestFullscreen?.();
      else if (e.key === 'b') command('black');
      else if (e.key === 'p') open('presenter.html', 'leap-presenter', 'width=1400,height=860');
    });
    addEventListener('click', (e) => {
      if (e.target.closest('.sections, .ui')) return;
      if (e.clientX > innerWidth / 3) next(); else back();
    });
  }

  addEventListener('load', () => {
    fit();
    if (params.has('snap') || mirror) document.documentElement.classList.add('snap');
    const m = location.hash.match(/^#(\d+)(?:\.(\d+))?/);
    show(m ? Math.min(Number(m[1]) - 1, slides.length - 1) : 0, m && m[2] ? Number(m[2]) : 0);
    if (mirror && channel) channel.postMessage({ hello: true });
  });
})();
