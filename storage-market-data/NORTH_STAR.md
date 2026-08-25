# North Star

Supersedes the original opening vision in `planning.md`. Everything under
"Principles" and the later provider/collection rules in `planning.md`
still applies — this document replaces *why* the project exists and
*what "done" looks like*, not the engineering discipline underneath it.

---

## What this actually is

Not a pricing-intelligence tool for operators (the StorTrack/Radius+
model). This is a **decision-support tool for acquisition teams** —
think of a BlackRock-style research team comparing properties before
deciding what to buy.

The client should never need to read a database, a spreadsheet, or a raw
comparison table. The end deliverable is a packaged, readable comparison
— "here's why Property A is a stronger buy than B, C, and D" — not a
data export.

**Output format, in order:**
1. A generated static report/one-pager per comparison (start here).
2. An interactive dashboard, later, once the report format is proven.

**Primary unit of comparison:** whole properties first (Facility A vs. B
vs. C). Comparing specific unit/space types across properties (all
10×20 storage units, all >5,000 sqft warehouse spaces) is a secondary
lens to add once property-level comparison works.

## The flagship metric: rental velocity

The single most valuable, hardest-to-fake number this project can
produce is **average days-to-lease** — how quickly units/spaces at a
property actually rent, derived from watching observation history over
time (a unit present in one snapshot and gone in the next, without ever
recording a false "sold out" on a failed scrape).

Example: *"Units at this facility rent within an average of 9 days vs.
40 days at the comparable facility down the street."*

This is the metric competitors' static listing sites cannot produce —
it requires exactly the append-only observation history this project
has been building since Milestone 2. **Treat this as the flagship
metric** — prioritize getting enough real observation history to
compute it credibly before investing heavily in anything else
comparison-related.

## Honest scope boundary

This project produces **asking-side intelligence**: current pricing,
availability, and — uniquely — rental velocity derived from historical
observation. It does not produce **underwriting-side data**: cap rates,
NOI, historical rent rolls, comparable sales, tenant credit quality.
Those live behind proprietary/paid data relationships (CoStar, broker
networks) this project doesn't have access to.

The comparison reports should be scoped and worded honestly: "here's how
these properties compare on price, availability, and lease-up speed,
based on what's publicly observable" — not implying a full investment
underwrite. The LLM narrative layer (see below) should reflect this
framing, not oversell it.

## Multi-vertical scope

Self-storage is the first vertical, not the only one. Office, warehouse/
industrial, and retail are the next likely additions — see the vertical
brainstorm from planning discussions for the fuller list. Warehouse/
industrial is the current pick for the second vertical, since it forces
real schema generalization (square footage + $/sqft/year pricing, new
attributes like clear height and dock doors) without going as far afield
as land or data centers.

This means the data model needs to generalize beyond
`width_ft`/`length_ft`/monthly-unit-pricing before the second vertical
is onboarded. That's Milestone 6 work, not urgent today — noted here so
it isn't designed around accidentally in Milestones 4–5.

## Where LLM work fits (ties to "LLM-powered extraction and narrative
generation" on the resume)

Two distinct LLM roles, not one:
1. **Extraction** — an LLM-based fallback/alternative to hand-written
   per-provider parsers, useful once onboarding a second vertical makes
   bespoke parsers expensive to maintain (Milestone 6+).
2. **Narrative generation** — turning a structured comparison (metrics
   table) into the plain-English report a client actually reads. This
   is core to the product, not a nice-to-have — it's the mechanism that
   "eliminates the need for a client to read complicated database info."

## What does NOT change because of this pivot

- Data-integrity rules from `planning.md` (never record a failed scrape
  as sold out, append-only observations, raw/parsed separation) — these
  matter *more* now, since rental velocity depends entirely on them
  being correct.
- Milestones 1–4 as already built (parser, models, Postgres, Docker, CI,
  Cloud Run + Scheduler deployment) — all of this is vertical-agnostic
  infrastructure and stays exactly as-is.
- Provider onboarding policy (robots.txt/ToS checks before collecting
  from any new site) — applies to every future vertical/provider too.
