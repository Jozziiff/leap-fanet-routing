# Modifications to upstream UavNetSim-v1

Upstream: <https://github.com/Zihao-Felix-Zhou/UavNetSim-v1>, tag `v1.0.1`, commit
`a5622c5d0a9f7b62b4e1d5a7dcc8978f34f0c85f`, MIT license. The first commit of this repository is that tree,
unmodified (its tree hash equals the upstream tag's tree hash). Every later change to an upstream file is listed
here: file, lines, why, and whether simulation behaviour can change.

Check the full diff at any time with `git diff <first-commit> -- <upstream paths>`.

## Non-code changes

| # | Change | Why | Behaviour change |
|---|---|---|---|
| N1 | Removed `.idea/` (6 files) and `routing/qmr/__pycache__/*.pyc` (12 files) shipped by the tag | IDE settings and stale bytecode do not belong in the repository (UPSTREAM_FACTS M33) | none (Python recompiles from source) |
| N2 | Appended a project section to `.gitignore` | ignore the virtual environment, tool caches, local notes and raw results | none |

## Code patches (SPEC §4.3)

None yet. Patches P1–P7 (config injection, routing registry, speed and rate from config, headless plotting,
instrumentation hooks, energy depletion disabled) are added in Phase 1, each with a regression test.
