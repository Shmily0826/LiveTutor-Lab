# LiveTutor-Lab

An evaluation rig for one question:

> **Should LiveTutor keep its current base architecture, or switch to Project
> N.E.K.O?**

**Answer, as of 2026-10-08: keep the current base (option A).** Reasoning and
evidence in [`docs/base-evaluation.md`](docs/base-evaluation.md).

This repo exists to hold evidence, not features. It contains no product code, and
it is not the place LiveTutor gets built.

---

## Why this repo exists

The previous LiveTutor was frozen on 2026-10-07 with an explicit note that the
*base architecture* was still an open question:

> "before any further feature work, the base architecture must be re-evaluated
> against N.E.K.O as a possible substrate."

Building more on an undecided base is the specific waste the freeze existed to
prevent. This lab is that re-evaluation. It ends in a decision, and the decision
is written down with numbers attached.

---

## Layout

```
README.md
docs/
  base-evaluation.md      <- the decision. Read this one.
  architecture-notes.md   <- mechanics: how N.E.K.O is built, what was measured
benchmarks/
  raw/                    <- gitignored working data
    evidence/             <- committed: the evidence behind every claim
    asar-src/             <- 138 Electron files extracted from shipped app.asar
    neko-app/             <- the shipped bundle
scripts/                  <- the diagnosis and measurement chain
candidates/               <- gitignored: third-party clones, own git history
```

`candidates/` is gitignored on purpose. N.E.K.O is cloned there at depth 50 with
its own git history intact and is never committed into this repo. No submodules.

---

## What was actually done

1. **Verified N.E.K.O independently.** Commit
   `1d814cf32fba8c02b5727d2890710e4e7b8ece24`, 2026-10-06, Apache-2.0, 3026★.
   No prior summary was trusted.
2. **Ran the backend standalone.** Cleared the storage gate through the product's
   own `/restart` contract, got 340 live routes, measured startup, latency, CPU
   and RAM.
3. **Read the closed half as far as it can be read.** The desktop shell is not in
   the open repo (`N.E.K.O.-PC` → 404), so the shipped `app.asar` was parsed and
   138 Electron source files extracted.
4. **Tested the decisive question directly.** An external HTTP brain registered
   custom tools into the running backend, appeared in the agent role's tool list,
   was loopback-enforced, and unregistered cleanly — with no N.E.K.O source
   changes.
5. **Searched the teaching surface honestly.** Read the keyword matches rather
   than counting them: 146 hits for `exercise` are all the English verb.
6. **Compared against the frozen baseline** without touching it.
7. **Reviewed five alternatives** with the same rigour.

---

## The decision in one paragraph

N.E.K.O is a good project and a genuinely extensible one — external services
attach to it over public API, and its plugin isolation, memory service and
proactive pipeline are real work that would be expensive to rebuild. But its
teaching layer is **0 % implemented** (not experimental, not abandoned:
absent), its desktop shell cannot be built or audited from source, screen
capture is bound to the Electron renderer (`no_renderer`, so no headless
operation and no GUI-free testing), and barge-in has no acoustic echo
cancellation. Adopting it does not reduce the teaching work, which must be built
either way — it relocates that work onto a worse substrate.

**OLV is retained and frozen to: Live2D/VRM rendering, audio I/O, and
expression/lip-sync mapping.** No new perception, proactive, or brain logic goes
into OLV.

---

## Honest limits of this evaluation

Stated plainly, because a decision document that hides its gaps is worse than
no decision document:

- **The Electron desktop shell never ran here.** The only distributable is an
  NSIS installer; the documented channel is Steam; silent install fails with
  rc=1. A control experiment proved the GUI subsystem itself works, so this is a
  packaging limit, not an environment limit.
- Therefore **avatar, voice path, barge-in, and proactive speech are BLOCKED in
  actual use** — implemented in code, unverified in practice.
- **Dialogue quality (5–8 turns) was not measured.** It needs a configured LLM
  provider and the shell.
- **This machine's loopback is silent**, so audio claims are unverifiable here for
  LiveTutor too, not just for N.E.K.O.
- **Attachability is proven; invocation inside a real LLM turn is not.** N.E.K.O
  calls registered tools only from its own agent turn, which needs a provider.
- An earlier CPU reading of `13435848058.8s` was a FILETIME field error. It is
  discarded and corrected in `benchmarks/raw/evidence/cpu-ram.txt`.

`BLOCKED` in these documents means "this evaluation could not verify it", which is
not the same as "N.E.K.O lacks it". The distinction is kept explicit throughout.

---

## What would change the recommendation

Recorded in advance so the decision can be revisited on evidence rather than
sentiment:

- N.E.K.O opens the shell source **and** moves capture out of the renderer into a
  service.
- N.E.K.O ships any teaching-layer work at all — re-run §5 of the evaluation first;
  that single fact flips the comparison.
- A third party ships a Windows tutor substrate with `WDA_EXCLUDEFROMCAPTURE`
  done properly.

---

## Reproducing

`scripts/` is ordered as the diagnosis actually happened, so the reasoning is
followable:

| Script | Purpose |
|---|---|
| `diag_neko_packer.py` | Proves the exe is an NSIS installer |
| `control_gui_probe.py` | Proves the GUI subsystem works (control experiment) |
| `neko_restart_proper.py` | Clears the storage gate via the product's `/restart` |
| `measure_neko.py` | Startup, latency, route inventory, capture probes |
| `brain_integration_probe.py` | The decisive external-Brain attachment test |
| `cpu_probe.py` | Corrected CPU/RAM measurement |

Everything under `benchmarks/raw/evidence/` was produced by these and committed,
so the claims can be checked without re-running anything.

---

## Scope

This lab stopped at the recommendation. No migration was started and no
`LiveTutor-Next` was created, by design.
