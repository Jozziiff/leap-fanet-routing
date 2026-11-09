# Defense slides

The slides for the 10-minute oral: an HTML deck on a fixed 1920×1080 stage, with step-by-step animations.

## Run

```bash
slides/serve.sh            # then open http://127.0.0.1:8766/
```

A local server is needed: the demo recording does not load from a `file://` page.

| Key | Action |
|---|---|
| → / Space, ← | next / previous step |
| P | presenter view (notes, next step, timer) in a second window |
| F, B | full screen, blank screen |
| Home / End | first / last slide |

The section names at the top are clickable. `#<slide>.<step>` in the URL opens a given slide and step.

## Files

| Path | Content |
|---|---|
| `index.html` | the slides and their speaker notes (`<aside class="notes">`) |
| `presenter.html` | presenter view, synchronised with the deck over a `BroadcastChannel` |
| `assets/deck.css`, `assets/slides.css` | design tokens and components; per-slide layout |
| `assets/engine.js` | stage scaling, navigation, steps, presenter sync |
| `assets/kit.js` | shared drawing vocabulary of the animations (drone, range, link, packet, …) |
| `assets/scenes-*.js` | one animation per concept slide; `scenes-replay.js` replays the recorded demo |
| `assets/demo.cast` | asciinema recording of [`experiments/demo.sh`](../experiments/demo.sh) |
| `assets/replay-data.js` | the two demo runs as replay data, from [`experiments/replay_export.py`](../experiments/replay_export.py) |

## Regenerate the demo and its replay

```bash
asciinema rec -i 1.5 --cols 96 --rows 26 --overwrite -c experiments/demo.sh slides/assets/demo.cast
uv run python experiments/replay_export.py bundle --rerun --check-cast slides/assets/demo.cast
```

The second command records the same two runs (N = 20, 20 m/s, λ = 2, seed 1, τ_th = 0.25 s) and stops
unless their totals equal the ones printed in the recorded demo. The demo is one seed, shown as such; the
results in the article come from three paired seeds.

## Credits

Fixed-stage base CSS from [frontend-slides](https://github.com/zarazhangrui/frontend-slides) (MIT).
Bundled in `assets/vendor/`: [GSAP](https://gsap.com) 3.13.0 (GSAP standard license) and
[asciinema-player](https://github.com/asciinema/asciinema-player) 3.10.0 (Apache-2.0). Fonts: Archivo,
Nunito and JetBrains Mono from Google Fonts. INSAT logo: Institut National des Sciences Appliquées et de
Technologie.
