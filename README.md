# PCWIS — Predictive Cash-Withdrawal Intelligence System

*A graph-and-geospatial decision-support layer for cybercrime fund-flow forecasting.*

> **A note before anything else:** every number, case record, and account reference in
> this repository is synthetic. Nothing here is trained on, tested against, or connected
> to real financial or personal data. This is a research prototype, and it's built and
> presented as one.

---

## Why this exists

Most fraud-detection software answers one question well: *is this account suspicious?*
Rule engines flag it, a compliance officer reviews it, and the case moves into an
investigation queue. That part of the problem is mature — banks and regulators have
spent years building it, and it works.

What almost nothing answers is the next question: *given that this account is already
flagged, where is the money actually going to surface?* By the time a suspicious
transfer is confirmed, the funds have usually already moved through two or three more
accounts and are on their way to a cash withdrawal somewhere — a specific ATM, in a
specific city, within a specific window of time. That withdrawal is the last moment
anyone can intervene before the money is effectively gone. Almost no system tries to
predict it in advance.

PCWIS is an attempt at that narrower, harder problem. It doesn't try to replace fraud
detection — it assumes a ring has already been flagged, and asks what happens next.

## What it actually does

Given a cluster of linked, already-suspicious accounts, PCWIS traces how funds move
between them, layers in geography and timing, and produces a short, ranked list of
plausible cash-out locations — each with a calibrated confidence score and a plain-
language reason, not a black-box number. An officer reviewing the output can see exactly
why a location was flagged, how confident the system actually is, and what to do next.
Nothing is automated past that point. The system recommends; a person decides.

That distinction matters more than it might seem. A wrong prediction that quietly
influences a human's judgment is a minor cost. A wrong prediction that autonomously
freezes an account or dispatches a patrol is a real one — so this system is built to
never take the second kind of action, under any confidence threshold.

## How it's put together

The pipeline is organized into ten layers, each one replaceable and independently
testable rather than a single monolithic script:

**Governance and intake.** Every identifier — phone numbers, account numbers, device
IDs — is tokenized with HMAC before it ever enters the system. Raw personal data never
touches the pipeline. Transactions and complaints stream in through Redis Streams,
mimicking the kind of event pipeline a real deployment would need.

**Entity and graph analysis.** A Neo4j graph stitches together accounts, devices, and
known high-risk exit points, tracing how money moves between them and catching cases
where a brand-new account shares a device with one that's already been flagged.

**Geography and ranking.** Candidate cash-out locations are shortlisted using real
OpenStreetMap ATM data and PostGIS spatial queries, then ranked with a LightGBM
learning-to-rank model — trained to optimize for the right question (does the correct
location appear near the top of a short list) rather than a generic accuracy score that
would look good and mean little.

**Decision and interface.** Predictions pass through a tiered policy layer before
reaching a React dashboard built for the person actually using it — an investigator
deciding what to do in the next hour, not a data scientist inspecting a model.

**Evaluation.** Every claim the system makes about its own performance is checked
against a proper held-out, time-respecting split and compared to a naive baseline —
because a number with no baseline and no honest test set isn't really a number.

## Stack

Python and FastAPI on the backend, LightGBM and scikit-learn for the model, Neo4j
(AuraDB) for the graph, PostGIS for spatial queries, Redis Streams for ingestion. The
frontend is React and Leaflet, rendered on plain OpenStreetMap tiles rather than a
paid mapping service — partly a cost decision, partly a bet that the map shouldn't be
the part of the system anyone has to think about.

## Running it locally

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env   # add your Neo4j Aura, PostGIS, and Redis credentials
python -m layer6_spatial.setup_db
python -m scripts.fetch_osm_atms
uvicorn api:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## What this is, and isn't

This is a working prototype, built to explore whether a specific, narrow prediction
problem is tractable at all — not a finished product and not a claim of real-world
accuracy. Every dataset it runs on is synthetic, generated to resemble realistic fraud
patterns without ever touching real financial records. It has no connection to any
government system, bank, or live data source, and it isn't built to be dropped into
production as-is. Treat it as a technical exploration of the problem, not a finished
answer to it.

## Credits
Kirti Chauhan
