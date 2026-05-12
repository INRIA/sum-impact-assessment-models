# Admin Refresh All — Architecture Docs

Visual overview of the jobs API after the admin refresh feature was added **and refactored**. Shows the existing per-job route, the new admin refresh route, the shared services they reuse, how a single admin trigger fans out into seven child job runs, and the clean-code improvements applied in the post-feature refactor.

---

## Refactor summary (post-feature)

Six clean-code improvements applied after the initial feature ship — all non-breaking:

| Area | What changed |
|---|---|
| `services/jobs/base.py` | New `BaseJob` ABC: all 4 job classes extend it; lifecycle (STARTED + FAILURE) is no longer duplicated |
| `services/jobs/__init__.py` | New `jobs` subpackage exposes `BaseJob` at a single canonical import path |
| `services/full_impact_refresh_service.py` | `FullImpactRefreshOrchestrator` class groups orchestration helpers; module-level shims keep all imports backward-compatible |
| `schemas/job_run.py` + `schemas/full_impact_refresh.py` | `schemas/job.py` split into two focused modules; original file is now a compatibility shim |
| `utils/time.py` | `utc_now()` helper replaces deprecated `datetime.utcnow()` calls across all job and service files |
| `utils/exceptions.py` | `@translate_errors` decorator converts unhandled exceptions to HTTP 500 on the three `router.*` handlers |

## 1. Component overview

Highlights what is reused vs. newly introduced. Components added by the feature are tagged `NEW`; refactored components are tagged `REFACTOR`.

```mermaid
flowchart LR
    subgraph Clients
        Backoffice[ODP Backoffice<br/>admin trigger]
        Internal[Internal client<br/>per-job trigger]
    end

    subgraph API[FastAPI app]
        AdminRouter["admin_router /jobs<br/>NEW"]
        JobsRouter[router /jobs]
    end

    subgraph Auth[Dependencies]
        VerifyInternal[verify_api_key]
        VerifyAdmin["verify_admin_refresh_api_key<br/>NEW"]
        Allowlist["enforce_ip_allowlist<br/>NEW"]
        RateLimit["check_rate_limit<br/>NEW"]
        Idempotency["validate_idempotency_key<br/>NEW"]
        TranslateErrors["@translate_errors decorator<br/>REFACTOR"]
    end

    subgraph Routes[Route handlers]
        TriggerJob["trigger_job<br/>POST /jobs/runs/{job_name}"]
        GetJob["get_job_run<br/>GET /jobs/{job_id}"]
        ListJobs["list_job_runs<br/>GET /jobs/"]
        TriggerRefresh["trigger_full_impact_refresh<br/>POST /jobs/runs/full_impact_refresh<br/>NEW"]
        GetRefresh["get_full_impact_refresh_status<br/>GET /jobs/runs/full_impact_refresh/{run_id}<br/>NEW"]
    end

    subgraph Services[Services]
        DispatchHelpers["job_dispatch_service<br/>resolve_actual_job_name<br/>execute_job_in_background<br/>NEW module"]
        RefreshService["full_impact_refresh_service<br/>FullImpactRefreshOrchestrator CLASS<br/>+ module-level shims<br/>REFACTOR"]
        Registry[jobs.JOB_REGISTRY<br/>get_job_class]
        BaseJob["BaseJob ABC<br/>run → _execute<br/>REFACTOR"]
        KpiJob["KpiMeasuresAnalysisJob<br/>extends BaseJob"]
        QuantJob["McdaQuantitativeJob<br/>extends BaseJob"]
        QualJob["McdaQualitativeJob<br/>extends BaseJob"]
        CustomJob["McdaCustomJob<br/>extends BaseJob"]
    end

    subgraph Persistence
        JobRepo["JobRepository<br/>+ get_in_progress_full_refresh NEW<br/>+ update_dispatched_job NEW"]
        JobRunsTable[(job_runs table)]
    end

    subgraph Utils[Utilities]
        UtcNow["utils/time.py<br/>utc_now()<br/>REFACTOR"]
        Exceptions["utils/exceptions.py<br/>@translate_errors<br/>REFACTOR"]
    end

    subgraph Schemas[Schemas]
        JobRunSchema["schemas/job_run.py<br/>JobNameEnum · JobStatusEnum<br/>TriggerJobRequest · JobRunResponse<br/>REFACTOR"]
        RefreshSchema["schemas/full_impact_refresh.py<br/>FullRefreshDispatchedJob<br/>FullImpactRefresh*Response<br/>REFACTOR"]
        JobShim["schemas/job.py<br/>← compatibility shim<br/>REFACTOR"]
    end

    Config["settings.JOB_RUN_CONFIGURATION<br/>NEW"]

    Backoffice -->|X-Admin-Refresh-Key| AdminRouter
    Internal -->|X-Internal-API-Key| JobsRouter

    AdminRouter --> VerifyAdmin
    AdminRouter --> Allowlist
    AdminRouter --> TriggerRefresh
    AdminRouter --> GetRefresh

    JobsRouter --> VerifyInternal
    JobsRouter --> TriggerJob
    JobsRouter --> GetJob
    JobsRouter --> ListJobs

    TriggerJob --> TranslateErrors
    GetJob --> TranslateErrors
    ListJobs --> TranslateErrors

    TriggerRefresh --> RateLimit
    TriggerRefresh --> Idempotency

    TriggerJob --> DispatchHelpers
    TriggerJob --> JobRepo
    GetJob --> JobRepo
    ListJobs --> JobRepo

    TriggerRefresh --> RefreshService
    GetRefresh --> RefreshService
    TriggerRefresh --> JobRepo
    GetRefresh --> JobRepo

    RefreshService --> Config
    RefreshService --> DispatchHelpers
    RefreshService --> JobRepo

    DispatchHelpers --> Registry
    Registry --> KpiJob
    Registry --> QuantJob
    Registry --> QualJob
    Registry --> CustomJob

    KpiJob --> BaseJob
    QuantJob --> BaseJob
    QualJob --> BaseJob
    CustomJob --> BaseJob

    BaseJob --> UtcNow
    RefreshService --> UtcNow
    TriggerRefresh --> UtcNow

    TranslateErrors --> Exceptions

    JobShim --> JobRunSchema
    JobShim --> RefreshSchema

    JobRepo --> JobRunsTable
```

## 2. Existing per-job trigger flow

`POST /jobs/runs/{job_name}` — unchanged behavior, now using the extracted `resolve_actual_job_name` and `execute_job_in_background` helpers from `job_dispatch_service`. Route handlers are now wrapped by `@translate_errors` (refactored).

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Router as jobs.router
    participant Verify as verify_api_key
    participant TE as @translate_errors
    participant Handler as trigger_job
    participant Dispatch as job_dispatch_service
    participant Repo as JobRepository
    participant DB as job_runs table
    participant BG as FastAPI BackgroundTasks
    participant Base as BaseJob.run
    participant Job as JobClass._execute

    Client->>Router: POST /jobs/runs/{job_name}<br/>X-Internal-API-Key
    Router->>Verify: verify_api_key(headers)
    Verify-->>Router: ok
    Router->>TE: @translate_errors wraps handler
    TE->>Handler: trigger_job(job_name, params)
    Handler->>Dispatch: resolve_actual_job_name(job_name, params)
    Dispatch-->>Handler: actual_job_name
    Handler->>Repo: create_job_run(actual_job_name)
    Repo->>DB: INSERT job_run (PENDING)
    DB-->>Repo: job_run row
    Repo-->>Handler: job_run
    Handler->>BG: add_task(execute_job_in_background, job_name, job_id, params)
    Handler-->>Client: 201 JobRunResponse
    BG->>Dispatch: execute_job_in_background(job_name, job_id, params)
    Dispatch->>Base: JobClass.run(job_id, db, params)
    Base->>Repo: update_job_status(STARTED)
    Base->>Job: cls._execute(job_id, db, params, job_repo)
    Job-->>Base: success / exception
    Base->>Repo: update_job_status(SUCCESS or FAILURE)
    Repo->>DB: UPDATE job_run
```

## 3. Admin full impact refresh flow

`POST /jobs/runs/full_impact_refresh` — NEW. One admin call creates one parent `job_run` and seven child `job_run` rows, dispatched 1.5 s apart.

```mermaid
sequenceDiagram
    autonumber
    participant Admin as ODP Backoffice
    participant Router as jobs.admin_router
    participant Auth as Admin auth deps
    participant Handler as trigger_full_impact_refresh
    participant Refresh as full_impact_refresh_service
    participant Dispatch as job_dispatch_service
    participant Repo as JobRepository
    participant DB as job_runs table
    participant BG as FastAPI BackgroundTasks
    participant Job as Child JobClass.run

    Admin->>Router: POST /jobs/runs/full_impact_refresh<br/>X-Admin-Refresh-Key<br/>X-Triggered-By, X-Request-Id<br/>Idempotency-Key
    Router->>Auth: verify_admin_refresh_api_key + enforce_ip_allowlist
    Auth-->>Router: ok
    Router->>Handler: trigger_full_impact_refresh
    Handler->>Auth: validate_idempotency_key + check_rate_limit
    Auth-->>Handler: ok
    Handler->>Repo: get_in_progress_full_refresh()
    Repo->>DB: SELECT job_runs WHERE job_name='full_impact_refresh' AND status IN (PENDING, STARTED)
    DB-->>Repo: none
    Repo-->>Handler: None
    Handler->>Refresh: build_dispatch_plan(started_at)
    Refresh-->>Handler: plan (7 entries from JOB_RUN_CONFIGURATION)
    Handler->>Repo: create_job_run('full_impact_refresh') + update_job_data(plan, audit, dispatch_state)
    Repo->>DB: INSERT parent job_run + UPDATE input/output_data
    DB-->>Repo: parent_run
    Repo-->>Handler: parent_run
    Handler->>BG: add_task(dispatch_full_refresh, parent_run.id, plan)
    Handler-->>Admin: 202 FullImpactRefreshTriggerResponse

    BG->>Refresh: dispatch_full_refresh(parent_run_id, plan)
    Refresh->>Repo: update_job_status(parent, STARTED)
    Repo->>DB: UPDATE parent job_run
    loop For each plan item (7 total)
        Refresh->>Repo: create_job_run(actual_job_name)
        Repo->>DB: INSERT child job_run
        Refresh->>Repo: update_job_data(child, parent_run_id + params)
        Refresh->>Repo: update_dispatched_job(parent, sequence, scheduled)
        Repo->>DB: UPDATE parent.output_data.dispatched_jobs
        Refresh->>Dispatch: asyncio.create_task(asyncio.to_thread(execute_job_in_background, ...))
        Dispatch->>Job: JobClass.run(child_job_id, db, params)
        Job->>Repo: update child status + data
        Refresh->>Refresh: await asyncio.sleep(1.5)
    end
    Refresh->>Repo: update_job_status(parent, SUCCESS or FAILURE, completed_at)
    Repo->>DB: UPDATE parent job_run
```

## 4. Status polling flow

`GET /jobs/runs/full_impact_refresh/{run_id}` — NEW. Reads the parent `job_run` and joins the linked child rows on the fly to surface the latest status of each dispatched job.

```mermaid
sequenceDiagram
    autonumber
    participant Admin as ODP Backoffice
    participant Router as jobs.admin_router
    participant Handler as get_full_impact_refresh_status
    participant Repo as JobRepository
    participant Refresh as full_impact_refresh_service
    participant DB as job_runs table

    Admin->>Router: GET /jobs/runs/full_impact_refresh/{run_id}<br/>X-Admin-Refresh-Key
    Router->>Handler: get_full_impact_refresh_status(run_id)
    Handler->>Repo: get_job_run(run_id)
    Repo->>DB: SELECT parent job_run
    DB-->>Repo: parent_run (job_name='full_impact_refresh')
    Handler->>Refresh: build_status_response(parent_run, repo)
    loop Each entry in parent.output_data.dispatched_jobs
        Refresh->>Repo: get_job_run(child_run_id)
        Repo->>DB: SELECT child job_run
        DB-->>Repo: child_run
    end
    Refresh-->>Handler: FullImpactRefreshStatusResponse
    Handler-->>Admin: 200 status payload
```

## 5. Class-level interactions

How the new modules collaborate with the existing job classes and repository. Reuse is intentional: the admin orchestration calls the same dispatch helpers as the per-job route. Job lifecycle management is now centralised in `BaseJob` (refactored).

```mermaid
classDiagram
    class JobsRouter {
        +trigger_job(job_name, params)
        +get_job_run(job_id)
        +list_job_runs(filters)
    }
    class AdminRouter {
        <<NEW>>
        +trigger_full_impact_refresh(headers, body)
        +get_full_impact_refresh_status(run_id)
    }
    class TranslateErrors {
        <<REFACTOR decorator>>
        +__call__(func) wraps route handlers
        re-raises HTTPException
        converts other exceptions → HTTP 500
    }
    class JobDispatchService {
        <<NEW module>>
        +resolve_actual_job_name(job_name, params)
        +execute_job_in_background(job_name, job_id, params)
    }
    class FullImpactRefreshOrchestrator {
        <<REFACTOR class>>
        build_dispatch_plan : staticmethod
        build_initial_dispatch_state : staticmethod
        dispatch : staticmethod
        build_trigger_response : staticmethod
        build_status_response : staticmethod
    }
    class AdminRefreshGuards {
        <<NEW>>
        +enforce_ip_allowlist(request)
        +check_rate_limit(api_key)
        +validate_idempotency_key(header)
        +mark_rate_limit(api_key)
        +remember_idempotency_key(key, run_id)
    }
    class AuthDependencies {
        +verify_api_key(header)
        +verify_admin_refresh_api_key(header) <<NEW>>
    }
    class TimeUtils {
        <<REFACTOR utils/time.py>>
        +utc_now() datetime
    }
    class JobRepository {
        +create_job_run(job_name)
        +get_job_run(job_id)
        +get_job_runs(filters)
        +update_job_status(...)
        +update_job_data(...)
        +get_in_progress_full_refresh() <<NEW>>
        +update_dispatched_job(parent_id, sequence, updates) <<NEW>>
    }
    class BaseJob {
        <<REFACTOR ABC services/jobs/base.py>>
        +run(job_id, db, params)$ classmethod
        +_execute(job_id, db, params, job_repo)$ abstract classmethod
        lifecycle: STARTED → SUCCESS/FAILURE
    }
    class KpiMeasuresAnalysisJob {
        <<extends BaseJob>>
        +_execute(job_id, db, params, job_repo)$
    }
    class McdaQuantitativeJob {
        <<extends BaseJob>>
        +_execute(job_id, db, params, job_repo)$
    }
    class McdaQualitativeJob {
        <<extends BaseJob>>
        +_execute(job_id, db, params, job_repo)$
    }
    class McdaCustomJob {
        <<extends BaseJob>>
        +_execute(job_id, db, params, job_repo)$
    }
    class JobRegistry {
        +JOB_REGISTRY: Dict
        +get_job_class(job_name)
    }
    class Settings {
        +ADMIN_REFRESH_API_KEY <<NEW>>
        +ADMIN_REFRESH_ALLOWED_IPS <<NEW>>
        +REFRESH_DISPATCH_INTERVAL_SECONDS <<NEW>>
        +REFRESH_RATE_LIMIT_SECONDS <<NEW>>
        +REFRESH_IDEMPOTENCY_WINDOW_SECONDS <<NEW>>
        +JOB_RUN_CONFIGURATION <<NEW>>
    }

    JobsRouter --> TranslateErrors : decorates handlers
    JobsRouter --> AuthDependencies : verify_api_key
    JobsRouter --> JobDispatchService : resolve + execute
    JobsRouter --> JobRepository
    JobsRouter --> TimeUtils : utc_now()

    AdminRouter --> AuthDependencies : verify_admin_refresh_api_key
    AdminRouter --> AdminRefreshGuards
    AdminRouter --> FullImpactRefreshOrchestrator
    AdminRouter --> JobRepository
    AdminRouter --> TimeUtils : utc_now()

    FullImpactRefreshOrchestrator --> Settings : JOB_RUN_CONFIGURATION
    FullImpactRefreshOrchestrator --> JobDispatchService
    FullImpactRefreshOrchestrator --> JobRepository
    FullImpactRefreshOrchestrator --> TimeUtils : utc_now()

    JobDispatchService --> JobRegistry
    JobRegistry --> KpiMeasuresAnalysisJob
    JobRegistry --> McdaQuantitativeJob
    JobRegistry --> McdaQualitativeJob
    JobRegistry --> McdaCustomJob

    KpiMeasuresAnalysisJob --|> BaseJob
    McdaQuantitativeJob --|> BaseJob
    McdaQualitativeJob --|> BaseJob
    McdaCustomJob --|> BaseJob

    BaseJob --> JobRepository : instantiates
    BaseJob --> TimeUtils : utc_now()
```

## 6. Persistence model

Both flows use the same `job_runs` table. The parent refresh row tracks the orchestration; child rows are normal job runs linked back via `input_data.parent_run_id`.

```mermaid
erDiagram
    JOB_RUNS ||--o{ JOB_RUNS : "parent_run_id in input_data"
    JOB_RUNS {
        string id PK
        string job_name "e.g. full_impact_refresh, mcda_analysis_quantitative_regulatory"
        string status "PENDING, STARTED, SUCCESS, FAILURE"
        text message
        datetime created_at
        datetime started_at
        datetime completed_at
        json input_data "parent: plan + audit. child: params + parent_run_id"
        json output_data "parent: dispatched_jobs[]"
    }
```
