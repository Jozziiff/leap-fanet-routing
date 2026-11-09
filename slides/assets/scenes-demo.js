/* === SCENE · DEMO (slide 15) ===
   Plays the asciinema recording of experiments/demo.sh (assets/demo.cast) as live terminal text,
   themed like the deck. It restarts each time the slide opens and pauses when the deck moves on. */
window.SCENES = window.SCENES || {};

SCENES.demo = function (slide) {
  const box = slide.querySelector('.term');
  let player = null;
  const mirror = location.search.includes('mirror');
  function make() {
    if (player || typeof AsciinemaPlayer === 'undefined') return;
    player = AsciinemaPlayer.create('assets/demo.cast', box, {
      fit: 'both', controls: false, preload: true, idleTimeLimit: 1.5, theme: 'swiss',
      terminalFontFamily: "'JetBrains Mono', monospace", terminalLineHeight: 1.3,
    });
  }
  return {
    enter() {
      if (mirror) return;
      make();
      if (player) { player.seek(0).then(() => player.play()); }
    },
    step() {},
    leave() { if (player) player.pause(); },
  };
};
