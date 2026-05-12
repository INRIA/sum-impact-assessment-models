# Admin Refresh All Plan

## Goal

Add an admin-only endpoint that triggers all supported analysis jobs in one action, persists a parent refresh run in the existing `job_runs` table, creates child job runs for each dispatched job, and exposes a status endpoint for the refresh orchestration.

## Scope

- Add `POST /jobs/runs/full_impact_refresh`
- Add `GET /jobs/runs/full_impact_refresh/{run_id}`
- Use a dedicated `ADMIN_REFRESH_API_KEY`
- Reuse the existing `job_runs` table for the parent refresh run and the child runs
- Dispatch the 7 configured jobs with a staggered interval of 1.5 seconds
- Track trigger metadata (`X-Triggered-By`, `X-Request-Id`, `Idempotency-Key`, source IP)
- Enforce concurrency, idempotency, rate limiting, and IP allowlisting for the admin endpoint

## Implementation Steps

1. Add configuration values for the admin key, rate-limit windows, IP allowlist, dispatch interval, and the ordered `JOB_RUN_CONFIGURATION` list.
2. Extend job schemas with a `full_impact_refresh` job name and dedicated refresh response models.
3. Add a second API-key dependency for admin refresh calls and request guard helpers for allowlist, rate limit, and idempotency.
4. Extract reusable job dispatch helpers so the existing per-job route and the new orchestrator share the same execution and naming logic.
5. Add repository helpers to find in-progress refresh runs and update per-child dispatch state on the parent run.
6. Implement a refresh orchestration service that creates child job runs, records results on the parent run, and launches execution asynchronously.
7. Split the jobs routes into the existing internal-key routes and the new admin-only refresh routes.
8. Add API and service tests covering the happy path and the new guardrail behavior.

## Persistence Model

- Parent refresh run:
  - `job_name = "full_impact_refresh"`
  - `input_data.plan` stores the configured dispatch plan
  - `input_data.audit` stores trigger metadata
  - `output_data.dispatched_jobs` stores per-child orchestration state
- Child job runs:
  - Normal existing `job_runs` rows
  - `input_data.parent_run_id` links the child back to the parent refresh run

## Dispatch Plan

The ordered `JOB_RUN_CONFIGURATION` contains:

1. `kpi_measures_analysis` with `kpi_group_type=KPI_SIEF`
2. `mcda_analysis_quantitative` with `perspective=regulatory`, `kpi_group_type=MCDA_GOALS`
3. `mcda_analysis_quantitative` with `perspective=pto`, `kpi_group_type=MCDA_GOALS`
4. `mcda_analysis_quantitative` with `perspective=nsm_providers`, `kpi_group_type=MCDA_GOALS`
5. `mcda_analysis_qualitative` with `perspective=regulatory`
6. `mcda_analysis_qualitative` with `perspective=pto`
7. `mcda_analysis_qualitative` with `perspective=nsm_providers`

`mcda_analysis_custom` is intentionally excluded because it requires user-supplied payload data.

## Verification

- API tests for `POST /jobs/runs/full_impact_refresh` and `GET /jobs/runs/full_impact_refresh/{run_id}`
- Unit tests for the orchestration service and the guard helpers
- Regression run for the updated jobs API tests