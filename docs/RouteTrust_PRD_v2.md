# Product Requirements Document (PRD)

**Project:** RouteTrust — Probabilistic Transit Reliability & Leave-By Advisor
**Project Type:** Applied ML / Decision Support
**Target Runtime:** FastAPI + Streamlit
**Deployment Target:** Hugging Face Spaces (single Docker container)
**Build Window:** 3 days · 3rd-Semester B.Tech submission / internship portfolio piece

---

## 1. Problem Statement

Transit riders regularly face schedule variance driven by weather, traffic, and operational bottlenecks. Standard journey planners answer only "when is the bus expected to arrive?" — a single deterministic number that silently hides how wrong that number can be. On a calm day the average and the worst case are close together; on a rainy rush-hour day they diverge sharply, and a rider who trusted the average misses their appointment.

The question riders actually need answered isn't "what's the expected arrival time" — it's **"what time must I leave to arrive on schedule, with a stated level of confidence?"** RouteTrust answers that directly: it models the full conditional delay distribution per route (not just its average) and converts that distribution into a single, risk-adjusted leave-by recommendation.

---

## 2. Product Vision

*A transit rider should never be surprised by "how late" — only by how confidently RouteTrust told them in advance.*

RouteTrust's long-term shape is a lightweight reliability layer that sits on top of any transit system's schedule data and turns "when will it arrive" into "when should I leave," with an honestly reported confidence level attached to every answer.

---

## 3. Target Users

**Primary — Daily Commuter (persona: Priya)**
Rides the same 2–3 routes on a predictable schedule. Needs a leave-by time she can trust for repeat trips, and wants to set her own risk tolerance rather than accept a one-size-fits-all buffer.
*Given* a required arrival time and her usual route, *when* she opens the dashboard, *then* she sees a leave-by time and a plain-language reliability grade for that route at that time of day.

**Secondary — Occasional Rider (persona: Arjun)**
Uses an unfamiliar route for a one-off, higher-stakes trip (an interview, a flight). Cares more about knowing *whether the route is predictable at all* than about fine-tuning a risk slider.
*Given* a route he rarely uses, *when* he checks it before an important trip, *then* he sees the reliability grade and interquantile spread clearly enough to decide whether to add extra buffer of his own.

**Tertiary — Evaluator / Technical Auditor**
Assesses the project for a certificate or portfolio review. Cares about model rigor, honest calibration reporting, and whether limitations are disclosed rather than hidden.
*Given* the deployed dashboard and README, *when* they inspect the diagnostics screen, *then* they can see pinball-loss comparisons against two baselines, per-quantile calibration, and a stated data-provenance limitation.

---

## 4. Core Features

| Feature | Description | Priority |
|---|---|---|
| Probabilistic quantile regressors | Three LightGBM models at τ = 0.10/0.50/0.90, trained on real archived GTFS-RT delay data + Open-Meteo weather, with post-hoc rearrangement to fix quantile crossing | **Must-have** |
| Chance-constrained leave-by optimizer | `leave_by = t_arrive − scheduled_travel_time − Q̂₍₁₋α₎(delay∣x)`, user-selectable α ∈ {0.20, 0.10, 0.05} | **Must-have** |
| Dynamic route reliability grade (A–F) | Normalized interquantile spread `(Q̂0.9 − Q̂0.1)/Q̂0.5`, bucketed into a letter grade | **Must-have** |
| Resilient weather ingestion | Live Open-Meteo call; on failure/rate-limit, falls back to historical median weather for that route/month/hour and tags the response `historical_fallback` — never defaults to clear weather | **Must-have** |
| Early departure guard | Clamps the *recommended* leave-by time (not the raw model output) so it never falls after the scheduled departure, flagged when triggered | **Must-have** |
| Low-sample route flagging | Route/stop pairs with <30 training rows still get a prediction, tagged `confidence: low` rather than suppressed | **Must-have** |
| Diagnostics & explainability console | Pinball-loss comparison vs. two baselines, per-quantile calibration plot, feature importance ranking | **Must-have** |
| Chronological (non-shuffled) train/test split | Avoids temporal leakage in reported metrics | **Must-have** |
| Cost-weighted asymmetric risk (custom early/late penalty) | Lets a user weight the cost of arriving early vs. late instead of a fixed α | Nice-to-have (v2) |
| Model drift alerting | Flags when live coverage drifts >10pp from training-time calibration | Nice-to-have (v2) |
| Multi-leg journey routing | Transfers across multiple routes rather than a single direct segment | Nice-to-have (v2) |
| SHAP-based explainability | Richer per-prediction attribution beyond built-in feature importance | Nice-to-have (v2) |

---

## 5. App Flow

1. **Landing (Screen 1 — Control & Input Dashboard):** user selects a route and stop, sets their required arrival time, and picks a risk tolerance via a plain-language slider ("leave late no more than 1 in 10 times"). Invalid inputs (past arrival time, unknown route/stop pair) are rejected here with a clear message.
2. **Submit → `/api/v1/optimize-decision`:** the backend runs the quantile models, applies the chance-constrained calculator, checks the early-departure guard, and checks the weather source and sample-size confidence for that route/stop.
3. **Result (Screen 2 — Decision Console):** the leave-by time is the headline. The reliability grade sits beside it. Any active flags — weather estimated from history, guard applied, low-confidence route — are shown inline, not tucked behind a tooltip, so the user always knows if they're seeing a slightly hedged answer.
4. **Optional deep-dive (Screen 3 — Diagnostics):** a user or evaluator can navigate here to see *why* the system said what it said — the calibration plot, the baseline comparison table, and feature importances. This screen is where the model earns (or loses) trust on inspection, separate from the quick-answer flow most riders will actually use.

---

## 6. Success Metrics

| Metric | Target | Validation |
|---|---|---|
| Pinball loss vs. groupby-median baseline | ≥10% reduction | Chronological holdout test slice |
| Empirical coverage, τ=0.10 | 5%–15% (±5pp) | Holdout, checked independently per quantile |
| Empirical coverage, τ=0.50 | 45%–55% (±5pp) | Holdout, checked independently per quantile |
| Empirical coverage, τ=0.90 | 85%–95% (±5pp) | Holdout, checked independently per quantile |
| Inference latency | <350ms | End-to-end `/api/v1/optimize-decision` response time |

Reporting both baselines' numbers alongside the model's, even where results are imperfect, is itself part of the success criteria — silently omitting an unflattering slice defeats the point of calibration reporting.

---

## 7. Out of Scope for v1

- **User authentication** — no OAuth, JWT, sessions, or API keys. Every interaction is stateless, single-session inference; there's no private user data to gate.
- **Persistent user profiles** — no saved bookmarks, trip history, or per-user setting overrides.
- **Multi-leg journey routing** — scoped strictly to direct route-stop segments.
- **Native mobile apps** — web-only, responsive.
- **Live GPS scraping** — uses curated historical GTFS-RT archives (traines.eu, fallback TfNSW), not an active real-time collector.
- **Cost-weighted risk, drift alerts, SHAP** — legitimate v2 extensions, deliberately deferred to keep the 3-day build achievable.

---

## 8. Technical Assumptions

- **Modeling:** LightGBM (quantile objective), Scikit-Learn, Pandas, NumPy, Joblib.
- **API layer:** FastAPI + Pydantic v2, auto-generated OpenAPI docs.
- **Persistence:** SQLite — training input cache, inference logs, decision audit trail.
- **Frontend:** Streamlit, calling the FastAPI backend over HTTP.
- **Containerization & hosting:** single Docker container running FastAPI (port 8000) and Streamlit (port 7860) via `start.sh`, deployed to Hugging Face Spaces.
- **Data pipeline:** traines.eu GTFS-RT archive (fallback: TfNSW) joined with Open-Meteo historical weather.

Full schema, API contracts, and the copy-paste `AI-AGENT-CONTEXT` build prompt live in the companion **RouteTrust Architecture Blueprint** document — this PRD defines *what* and *why*; that document defines *how*.

---

## 9. Resolved Design Decisions Log

*(Carried over from open questions raised during scoping — included here so the reasoning isn't lost.)*

- **Temporal holdout:** chronological split, not stratified route-hour sampling — avoids leaking same-day conditions across train/test.
- **Early departure guard:** clamp the decision output, not the raw quantile — keeps calibration reporting honest while preventing a nonsensical recommendation.
- **Low-sample routes:** flag with `confidence: low` at a 30-row threshold rather than suppressing predictions.
