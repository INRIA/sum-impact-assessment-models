# SPEC — Admin-triggered Full Impact Analysis Refresh

**Status:** Draft v1
**Owner:** Rebeca Murillo (INRIA)
**Target path in impact API repo:** `specs/admin-refresh-analysis/SPEC.md`
**Project:** `sum-impact-assessment-models` (Python / FastAPI)
**Date:** 2026-05-12

---

## 1. Goal

Expose a single endpoint on the impact API that the ODP backoffice can call to refresh **all** impact analyses in one operation. The endpoint internally orchestrates the existing job functions (KPI measures + MCDA quantitative × 3 perspectives + MCDA qualitative × 3 perspectives = **7 job dispatches**), staggered to avoid overwhelming the host.

## 2. Non-goals

- No changes to existing per-job routes (`/jobs/runs/kpi_measures_analysis`, `/jobs/runs/mcda_analysis_quantitative`, `/jobs/runs/mcda_analysis_qualitative`). They keep their current contract.
- No user-level authentication on the impact API (admin user auth stays in the ODP backoffice). The impact API is still secured by API key only.
- No new job worker infrastructure. The orchestrator calls the same underlying job functions the existing routes call.

## 3. New endpoint

### 3.1 Route name (recommended)

```
POST /jobs/runs/full_impact_refresh
```

**Rationale.** It follows the existing `POST /jobs/runs/<job_type>` convention, so the new route is recognizable as just another job type (a meta-job that orchestrates the others). REST-wise, the resource is "a run", and POSTing to `/jobs/runs/<type>` creates a new run of that type. Snake_case matches the existing route names.

Alternative names considered: `/jobs/runs/full_analysis_refresh`, `/jobs/runs/all_analyses`, `/admin/impact-refreshes`. The first two are equivalent stylistically; the third breaks the existing convention without security benefit (the impact API has no `/admin/` namespace today).

### 3.2 Request

**Headers:**
- `X-API-Key: <admin_refresh_key>` — required. **Separate key** from the one ODP uses for its read calls (see §6).
- `Idempotency-Key: <uuid>` — optional but recommended. Prevents accidental double-triggers on backoffice button mashing.
- `X-Triggered-By: <admin_user_id_or_email>` — optional. Logged for audit (see §8).
- `X-Request-Id: <uuid>` — optional. Logged for correlation.

**Body:** empty (or `{}`). The set of analyses and perspectives is fixed by the spec; no parameters needed from the caller.

### 3.3 Response — success

`202 Accepted`

```json
{
  "run_id": "8f3a2c7e-9b14-4d8c-a6f1-...",
  "status": "dispatching",
  "started_at": "2026-05-12T14:32:11Z",
  "dispatched_jobs": [
    {"job": "kpi_measures_analysis","kpi_group_type": "KPI_SIEF", "scheduled_at": "2026-05-12T14:32:11Z"},
    {"job": "mcda_analysis_quantitative", "perspective": "regulatory", "kpi_group_type": "MCDA_GOALS", "scheduled_at": "2026-05-12T14:32:12.5Z"},
    {"job": "mcda_analysis_quantitative", "perspective": "pto", "kpi_group_type": "MCDA_GOALS", "scheduled_at": "2026-05-12T14:32:14Z"},
    {"job": "mcda_analysis_quantitative", "perspective": "nsm_providers", "kpi_group_type": "MCDA_GOALS", "scheduled_at": "2026-05-12T14:32:15.5Z"},
    {"job": "mcda_analysis_qualitative", "perspective": "regulatory", "scheduled_at": "2026-05-12T14:32:17Z"},
    {"job": "mcda_analysis_qualitative", "perspective": "pto", "scheduled_at": "2026-05-12T14:32:18.5Z"},
    {"job": "mcda_analysis_qualitative", "perspective": "nsm_providers", "scheduled_at": "2026-05-12T14:32:20Z"}
  ]
}
```

The endpoint returns *after the dispatch plan is registered* (typically <100 ms). The actual job dispatches happen in a background task — the caller does not wait for jobs to finish.

> ⚠ Perspective and kpi group types arguments are necessary information for each job to run, as specified in the existing route documentation POST /jobs/runs/<job>. Perspectives are referenced in (`settings.MCDA_PERSPECTIVES`) 

### 3.4 Response — errors

| Status | When | Body |
|---|---|---|
| `401 Unauthorized` | Missing or invalid `X-API-Key` | `{"error": "invalid_api_key"}` |
| `403 Forbidden` | Valid key but wrong scope (e.g., ODP read key trying to call this) | `{"error": "insufficient_scope"}` |
| `409 Conflict` | A refresh run is already in progress | `{"error": "refresh_in_progress", "current_run_id": "..."}` |
| `429 Too Many Requests` | Rate limit hit (see §6.5) | `{"error": "rate_limited", "retry_after_seconds": 60}` |
| `422 Unprocessable Entity` | Duplicate `Idempotency-Key` within window | `{"error": "duplicate_request", "original_run_id": "..."}` |

## 4. Orchestration behavior

### 4.1 Dispatch list

The 7 jobs to dispatch, in order:

1. `kpi_measures_analysis` - body `{"kpi_group_type": "KPI_SIEF"}`
2. `mcda_analysis_quantitative` — body `{"perspective": "<P1>", "kpi_group_type": "MCDA_GOALS"}`
3. `mcda_analysis_quantitative` — body `{"perspective": "<P2>", "kpi_group_type": "MCDA_GOALS"}`
4. `mcda_analysis_quantitative` — body `{"perspective": "<P3>", "kpi_group_type": "MCDA_GOALS"}`
5. `mcda_analysis_qualitative` — body `{"perspective": "<P1>"}`
6. `mcda_analysis_qualitative` — body `{"perspective": "<P2>"}`
7. `mcda_analysis_qualitative` — body `{"perspective": "<P3>"}`

Perspective values are loaded from configuration (`settings.MCDA_PERSPECTIVES`), not from the request — keeps the admin trigger parameter-free.
Setup job configuration in a settings variable or enum, to keep things easily configurable and maintenable. 

### 4.2 Staggered dispatch

Jobs are dispatched **one every ~1.5 seconds** for a total dispatch window of ~10 seconds, to avoid overwhelming the host. This is done with a FastAPI `BackgroundTasks` (or `asyncio.create_task`) coroutine that:

```python
async def dispatch_full_refresh(run_id: str, perspectives: list[str]):
    DISPATCH_INTERVAL_SECONDS = 1.5

    dispatches = [
        ("kpi_measures_analysis", None),
        ("mcda_analysis_quantitative", perspectives[0]),
        ("mcda_analysis_quantitative", perspectives[1]),
        ("mcda_analysis_quantitative", perspectives[2]),
        ("mcda_analysis_qualitative", perspectives[0]),
        ("mcda_analysis_qualitative", perspectives[1]),
        ("mcda_analysis_qualitative", perspectives[2]),
    ]

    for i, (job_name, perspective) in enumerate(dispatches):
        if i > 0:
            await asyncio.sleep(DISPATCH_INTERVAL_SECONDS)
        try:
            await run_job(job_name, perspective=perspective, parent_run_id=run_id)
        except Exception as e:
            log.exception("dispatch_failed", job=job_name, perspective=perspective, run_id=run_id)
            # continue — best-effort dispatch; one failure does not abort remaining jobs
```

### 4.3 Direct function call (not HTTP loopback)

The orchestrator calls the **same underlying job function** that the existing route handlers call — it does not make HTTP requests to its own routes. This means:

- The existing route handlers should already delegate to a service-layer function (e.g., `services.jobs.run_kpi_measures_analysis()`); if they don't, refactor them so the logic is extracted.
- The orchestrator imports and calls that service function directly.
- No internal auth checks needed (we're inside the same process).
- No HTTP serialization overhead, no risk of self-referential auth loops.

### 4.4 Failure handling

If dispatching one of the 7 jobs raises, the orchestrator **logs and continues** with the remaining jobs. The rationale: an admin-triggered refresh failing partially is recoverable (admin can re-trigger), but aborting halfway leaves analyses in an inconsistent half-old-half-new state — worse outcome.

The run record (see §5) tracks per-job dispatch outcome so the admin can see what actually started.

## 5. Run record (state)

To support concurrency checks and (optionally) status polling, persist a small record per refresh run in the `job_runs` table 

**Storage:** simplest viable — an in-memory dict keyed by `run_id`, plus a single `current_run_id` slot for concurrency checks. If the impact API already has a DB, use a `refresh_runs` table instead so state survives restarts.

**Fields:**
- `run_id` (UUID, primary key)
- `status` (`dispatching` | `dispatched` | `failed`)
- `started_at` (timestamp)
- `dispatch_completed_at` (timestamp, set when the background coroutine finishes the loop)
- `triggered_by` (string, from `X-Triggered-By` header, nullable)
- `idempotency_key` (string, nullable, indexed)
- `dispatched_jobs` (list of `{job, perspective, scheduled_at, status, error}`)

> ⚠ The run record tracks **dispatch**, not job completion. The underlying job system is already async and has its own tracking (whatever existing mechanism shows job completion). See open question Q4.

## 6. Security

### 6.1 Separate API key

Create a **second** API key with scope `admin:refresh` (or similar). The existing ODP→impact-API key keeps its existing scope (read-only or whatever it has). Only the backoffice holds the admin key.

If the impact API today uses a single hardcoded key, the minimal change is: introduce a key→scope map (env-configured), and require the `admin:refresh` scope on the new endpoint.

```python
# Pseudocode
@router.post("/jobs/runs/full_impact_refresh")
async def trigger_full_refresh(
    api_key: ApiKey = Depends(require_scope("admin:refresh")),
    ...
):
    ...
```

### 6.2 Key storage on the backoffice side

Backoffice (PHP) stores the admin key in server-side environment / secrets — **never** exposed to the admin's browser. The admin's PHP-framework session auth is what controls *who can click the button*; the API key is what the PHP server uses to call the impact API.

### 6.3 Idempotency

If `Idempotency-Key` header is present and matches a run started within the last 60 seconds, return `422` with the original `run_id`. Prevents double-clicks and duplicate triggers.

### 6.4 Concurrency

If `current_run_id` is set and that run's status is `dispatching`, return `409 Conflict`. The admin must wait for the dispatch loop to complete (~10 s) before retriggering. Job *execution* may still be ongoing after dispatch finishes — that's fine, concurrent runs of underlying jobs are allowed (or rejected by the existing job system, whichever the current behavior is — see Q5).

### 6.5 Rate limiting

Soft rate limit: 1 successful trigger per 60 seconds per API key. Implemented either via a simple in-memory counter or, if the project already uses a rate-limit middleware, via that. Belt-and-braces against runaway loops on the backoffice side.

### 6.6 Optional: IP allowlist
All client servers for this API are in the same server for production environment deployed with Docker containers. So the calls all should only come from localhost, whitelist the same server IP address, so other containers in the same network are whitelisted by default. 

### 6.7 Transport

TLS only. Reject plain HTTP (presumably already the case for the impact API in production).

## 7. Audit & observability

Every call to `POST /jobs/runs/full_impact_refresh` must produce a log entry containing:

- timestamp
- caller source IP
- `X-Triggered-By` (admin user, if provided)
- `X-Request-Id` (if provided)
- `Idempotency-Key` (if provided)
- resulting `run_id`
- final HTTP status

Each dispatched job inside the orchestration also logs `run_id` so log search can correlate the 7 child dispatches back to the parent trigger.

## 8. Optional: status endpoint

If the backoffice needs to show progress to the admin, add:

```
GET /jobs/runs/full_impact_refresh/{run_id}
```

Returns the run record from §5. Same API key requirement. Returns `404` for unknown `run_id`.

Skipping this for v1 is fine — the backoffice can just show "refresh triggered" and rely on the existing per-job status mechanism if it has one. Decision in Q4.
