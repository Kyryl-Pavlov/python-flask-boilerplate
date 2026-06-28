# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Security Measures

The following security controls are intentionally in place. Do not remove or weaken them without a documented reason.

### Application

| Measure | Location | Rule |
|---|---|---|
| `SECRET_KEY` fail-fast | `services/app/app/config.py` — `_require()` | Raises `RuntimeError` at startup if unset. Never add a default fallback value. |
| `MAX_CONTENT_LENGTH` | `services/app/app/config.py` | 50 MB hard limit on all uploads — Flask enforces this before any handler runs. |
| File upload allowlist | `services/app/app/api/v1/media.py` — `_ALLOWED_EXTENSIONS` | Allowlist of safe extensions only. Extend deliberately; never switch to a blocklist. |
| SQL masking in logs | `services/app/app/logging/data_filter.py` — `sanitize_traceback()` | Strips `[SQL: ...]`, `[parameters: ...]`, and connection strings from every traceback before it reaches any log backend. Lambda has an inline equivalent `_safe_exc()` in `lambda/handler.py`. |
| GraphQL introspection | `services/app/app/graphql_api/__init__.py` + `services/app/app/config.py` | `GRAPHQL_INTROSPECTION = True` in `DevelopmentConfig` only; `False` in `ProductionConfig`. Do not hardcode `True`. |
| Explicit JWT algorithm | `services/app/app/config.py` — `JWT_ALGORITHM = "HS256"` | Pinned to prevent silent algorithm changes on library upgrades. |

### Infrastructure (Terraform)

| Measure | Location | Rule |
|---|---|---|
| Redis TLS | `terraform/modules/elasticache/main.tf` | `transit_encryption_enabled = true`. Output URL is `rediss://` (double-s). Both must stay in sync. |
| Non-root containers | `services/app/Dockerfile`, `lambda/Dockerfile`, `lambda/Dockerfile.lambda` | App uses a `app` system user; Lambda uses `nobody`. The `USER` instruction must remain after all `COPY`/`RUN` steps. |
| ECS task role SQS scope | `terraform/modules/iam/main.tf` | Flask app: `sqs:SendMessage` + `sqs:GetQueueAttributes` only. Lambda worker: `ReceiveMessage` + `DeleteMessage`. Never cross-assign. |
| Secrets Manager recovery | `terraform/main.tf`, `terraform/modules/rds/main.tf` | `recovery_window_in_days = 7`. Never set to `0` in committed code (risk of unrecoverable accidental deletion). |
| WAF logging | `terraform/modules/waf/main.tf` | CloudWatch log group `aws-waf-logs-{prefix}`, 90-day retention. Do not remove `aws_wafv2_web_acl_logging_configuration`. |

### Nginx

| Measure | Location | Rule |
|---|---|---|
| Security headers | `nginx/nginx.conf` | `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `server_tokens off`. All use `always` flag so they apply to error responses too. |
| HSTS | `nginx/nginx.conf` (commented) | Enable `Strict-Transport-Security` **only after** TLS is live on the ALB. Enabling it over HTTP permanently breaks access for returning visitors. |

### Intentional gaps (not implemented by design)

- **Content-Security-Policy** — commented in `nginx/nginx.conf`. A CSP covering the GraphQL playground requires per-deployment origin config; a wrong CSP silently breaks the playground. Add once you know your frontend origins.
- **HSTS** — see above.
- **Redis AUTH token** — cluster is in a private subnet accessible only via security group. Add `auth_token` when moving to multi-tenant or shared infrastructure.
- **MIME type sniffing** — files go to S3 and are never executed server-side; extension allowlisting is sufficient. Add `python-magic` if serving files from a public CDN without `Content-Disposition: attachment`.
- **JWT refresh token blacklisting** — stateless by design. Add a Redis-backed blacklist if logout must immediately invalidate tokens.

## Common Commands

```bash
# Start full stack (rebuilds image)
docker compose up --build

# Rebuild and start only the app container
docker compose up --build app

# Run DB migrations inside container
docker compose run --rm migrate flask db upgrade

# Migrations run automatically on every docker compose up --build.
# The migrate service detects model changes, generates a file if needed, then applies it.
# To run manually (e.g. outside Docker):
docker compose exec app flask db migrate -m "description"
docker compose exec app flask db upgrade

# Tail app logs
docker compose logs -f app
```

### Helper Scripts

**`migrate.sh`** — interactive migration helper for local development (runs outside Docker, requires Flask in the active virtual environment). Accepts an optional service name argument (default: `app`). Prompts for a migration message, runs `flask db migrate --directory services/<service>/migrations`, then asks whether to immediately apply with `flask db upgrade`. Also calls `flask db init` if the service's `migrations/` directory does not exist yet.

```bash
bash migrate.sh          # defaults to services/app/migrations
bash migrate.sh payments # uses services/payments/migrations
```

**`launch_app_docker_image.sh`** — builds and launches a single service container standalone. Accepts an optional service name argument (default: `app`).

```bash
bash launch_app_docker_image.sh          # builds services/app/Dockerfile
bash launch_app_docker_image.sh payments # builds services/payments/Dockerfile for future services
# To stop: docker stop flask-boilerplate-<service>
```

> Note: this script starts only the app container with no database or LocalStack, so any endpoint that touches Postgres or S3 will fail. Use it only to verify the image builds and the process starts cleanly.

## Debugging

Two VSCode debug configurations are defined in `.vscode/launch.json`:

### Option 1 — Attach to running Docker container

The `app` service in `docker-compose.yml` uses `Dockerfile.dev`, which starts Flask under `debugpy` on port 5678. The debugger is always available while the stack is running.

```bash
docker compose up --build
```

Then launch **"Docker: Attach to Flask"** in VSCode. Source changes are picked up immediately via the volume mount (no rebuild needed).

### Option 2 — Run Flask on the host

Start only infrastructure, then launch **"Local: Flask Debug"** in VSCode (F5). The `preLaunchTask` runs `docker compose up -d postgres localstack migrate` automatically; `postDebugTask` stops them when the session ends.

The launch config overrides `DATABASE_URL` and S3 endpoint vars to use `localhost` instead of Docker service hostnames. If your `.env.local` uses different Postgres credentials, update `DATABASE_URL` in `.vscode/launch.json` accordingly.

## Local Infrastructure

The full stack runs via Docker Compose. All services share the default Docker network.

| Service | Port | Purpose |
|---|---|---|
| `nginx` | 80 | Reverse proxy / load balancer — single entry point for all services |
| `app` | 5000, 5678 | Flask app (dev server + debugpy on 5678) — also reachable directly on 5000 |
| `postgres` | 5432 | Primary database |
| `migrate` | — | One-shot container: runs `flask db upgrade` on startup |
| `localstack` | 4566 | AWS S3 + CloudWatch Logs emulator |
| `pgadmin` | 5050 | Postgres GUI |
| `s3-console` | 8080 | S3 bucket GUI (cloudlena/s3manager) |
| `loki` | 3100 | Log aggregation — receives structured JSON from `LokiLogger` |
| `prometheus` | 9090 | Metrics database — scrapes `/metrics` from `app` every 15 s |
| `grafana` | 3000 | Dashboards — queries Prometheus (metrics) and Loki (logs) |
| `cadvisor` | 8081 | Container resource metrics (CPU, mem, disk) — **non-functional on Docker Desktop for Windows**, included for production parity only |
| `node-exporter` | 9100 | Host OS metrics (CPU, memory, disk I/O, network, load average) via `/proc` and `/sys` |

**Startup order:** `postgres` healthy → `localstack` healthy → `migrate` completes → `app` starts → `nginx` starts.

**Adding a new microservice behind Nginx:**
1. Add the service to `docker-compose.yml` (no ports needed — it stays internal).
2. Add an upstream block and a `location` block to `nginx/nginx.conf`.
3. Restart: `docker compose up --build nginx`.

Other services reach the Flask API internally via `http://app:5000` (direct) or `http://nginx/api/v1/` (through the proxy). External clients always hit port 80.

**S3 bucket init:** `localstack-init/create-bucket.sh` runs via LocalStack's `/etc/localstack/init/ready.d` hook, creating the `media-bucket`. The service also auto-creates the bucket on first upload via `_ensure_bucket()`.

**Environment:** All config lives in `.env.local`, loaded via `env_file` in compose. Never committed — use `.env.local` as the single source of truth for local development.

## Multi-service Python path (`pyproject.toml`)

`pyproject.toml` lives at the repo root and serves as the single pytest + ruff config. The `pythonpath` array controls which service directories pytest adds to `sys.path`:

```toml
[tool.pytest.ini_options]
pythonpath = ["services/app"]  # one entry per Python microservice
```

When you add a new Python service, append its directory: `pythonpath = ["services/app", "services/payments"]`.

## Services Layout

Microservices live under `services/`. Each service is self-contained with its own Dockerfiles.

```
services/
└── app/                     # Flask REST + GraphQL API
    ├── app/                 # Python package (app factory, models, routes, etc.)
    ├── Dockerfile           # Production image (gunicorn)
    └── Dockerfile.dev       # Dev image (Flask dev server + debugpy, hot-reload via volume)
```

### Docker build pattern

Build context stays at `.` (repo root) so Dockerfiles can access `requirements.txt`, `services/app/migrations/`, and `wsgi.py`. Only the `dockerfile:` path points into `services/`:

```yaml
build:
  context: .
  dockerfile: services/app/Dockerfile
```

### Dev volume mounts

`app` and `migrate` services mount `./services/app:/app`. The `migrate` service also mounts `./services/app/migrations:/app/migrations` for migration file persistence. The `migrate` service sets `FLASK_APP: app` explicitly — `.env.local` sets `FLASK_APP=wsgi` but `wsgi.py` is at root and not in the volume.

### Adding a new microservice

1. Create `services/<name>/` with `Dockerfile` and `Dockerfile.dev`.
2. Add to `docker-compose.yml` with `context: .` and `dockerfile: services/<name>/Dockerfile.dev`.
3. Add Nginx upstream + location in `nginx/nginx.conf`.
4. Add build step in `deploy-dev.yml` and `deploy-prod.yml` with `context: .` and `file: services/<name>/Dockerfile`.
5. Add ECR repo in `terraform/modules/ecr/main.tf` and ECS service in `terraform/`.
6. Append `"services/<name>"` to `pythonpath` in `pyproject.toml`.

## Architecture

### App Factory

`services/app/app/__init__.py` uses a factory pattern (`create_app(config_name)`). The REST API version is selected dynamically via the `REST_API_V` env var (default `v1`) using `importlib`, enabling multi-version support without code changes.

### Dual API Layer

Every feature is exposed over both REST and GraphQL. Both share the same models and services — only the transport layer differs.

- **REST:** `services/app/app/api/v1/` — blueprints registered at `/api/v1/`
- **GraphQL:** `services/app/app/graphql_api/` — Strawberry schema at `/graphql`, with `multipart_uploads_enabled=True` for file uploads

GraphQL resolvers do not use `@jwt_required()` (a Flask decorator) — they call `verify_jwt_in_request()` manually inside each resolver since Strawberry handles the request context differently.

### Configuration

`services/app/app/config.py` has three config classes (`DevelopmentConfig`, `ProductionConfig`, `TestingConfig`) all inheriting from `Config`. The production image (`wsgi.py`) runs `create_app('production')`. All AWS/S3 settings must be on the base `Config` class, not only on `DevelopmentConfig`, or they will be absent in production mode.

### S3 / LocalStack Split Endpoint

The S3 service (`services/app/app/services/aws_s3_service.py`) maintains two boto3 client modes:

- `_client()` — uses `AWS_S3_ENDPOINT_URL` (`http://localstack:4566`) for internal operations (upload). Resolvable only inside Docker.
- `_client(public=True)` — uses `AWS_S3_PUBLIC_ENDPOINT_URL` (`http://localhost:4566`) for generating presigned URLs. Needed because presigned URLs are opened by the browser on the host machine, which cannot resolve the `localstack` hostname.

In production both env vars are unset (`None`), so boto3 routes to real AWS automatically.

### Models

All models must be imported in `services/app/app/models/__init__.py` for Flask-Migrate to detect them. Current models:

- `User` — `id` (UUID PK), `email` (unique), `password_hash`, `created_at`
- `Media` — `id` (UUID PK), `user_id` (FK → users), `content_key` (S3 object key, **not** a URL), `created_at`

`content_key` stores the S3 key (`media/<user_uuid>/<filename>`). Presigned URLs are generated on demand and never persisted.

### Logging

The app uses an Object Adapter pattern. All loggers implement `LoggerProtocol` (`services/app/app/utils/logger.py`) and are injected into `AppLogger`, which fans out calls to all of them.

| Class | Location | Behaviour |
|---|---|---|
| `AppLogger` | `services/app/app/logging/logger.py` | Fanout adapter; single public method `log(message, level, data, exc)`. `Level` enum exposed as `AppLogger.Level.{INFO,WARN,ERROR}` |
| `ConsoleLogger` | `services/app/app/logging/logger.py` | stdout via Python `logging`; DEBUG in dev, WARNING in prod |
| `SentryLogger` | `services/app/app/logging/sentry_logger.py` | `info`/`warn` → Sentry breadcrumbs; `error` → `capture_message` with extras |
| `CloudWatchLogger` | `services/app/app/logging/cloudwatch_logger.py` | Structured JSON events via `watchtower`; supports `endpoint_url` for LocalStack |
| `LokiLogger` | `services/app/app/logging/loki_logger.py` | POSTs structured JSON to Loki's `/loki/api/v1/push`; uses stdlib `urllib` only (no extra dependency); failures are silently swallowed |

`AppLogger` is created in `create_app()` and attached as `app.logger_adapter`. Sentry, CloudWatch, and Loki are **opt-in** — only wired when their env vars are set. CloudWatch init failure is non-fatal (logs a warning, app continues with remaining loggers). Loki push failures are silently swallowed.

**Loki labels:** every event is tagged with `{app: "flask-boilerplate", env: <config_name>, level: <info|warning|error>}`. Query in Grafana Explore with `{app="flask-boilerplate"}` or `{level="error"}`.

**Automatic logging:** `rest_api_response()` and `Response.__post_init__` (GraphQL) call the logger automatically on every response — no manual calls needed in handlers. Log level is derived from `success` and `status_code`:
- `success=True` → INFO
- `success=False`, no `exc` → WARN
- `success=False`, `exc` provided → ERROR with full stack trace

**Manual logging:**
```python
from flask import current_app
logger = current_app.logger_adapter
logger.log("upload failed", level=logger.Level.ERROR, data={"key": s3_key}, exc=e)
```

**Data filtering:** `mask_sensitive()` in `services/app/app/logging/data_filter.py` recursively replaces values of sensitive keys (`password`, `token`, `secret`, `authorization`, etc.) with `***`. Applied automatically in `AppLogger.log()` before any logger sees the data. To add keys, extend `_SENSITIVE_KEYS` in `data_filter.py`.

**Sentry notes:**
- JWT auth failures (422) are handled by Flask-JWT-Extended before reaching our code — Sentry won't capture them unless you add a custom `@app.errorhandler(JWTExtendedException)`.
- `info`/`warn` calls appear as breadcrumbs inside Sentry error events, not as standalone events. This is intentional — sending every log as an event burns Sentry quota.

**CloudWatch / LocalStack notes:**
- LocalStack must have `logs` in `SERVICES` (already set in `docker-compose.yml`).
- On Windows with Git Bash, prefix every `aws logs` CLI command with `MSYS_NO_PATHCONV=1` to prevent Git Bash from converting `/myapp/dev` → `C:/Program Files/Git/myapp/dev`.
- Query logs locally: `MSYS_NO_PATHCONV=1 aws --endpoint-url=http://localhost:4566 logs get-log-events --log-group-name /myapp/dev --log-stream-name app`

### Observability Stack

The app ships a **collect → store → visualise** pipeline:

```
Flask /metrics    ──scrape──►  Prometheus  ──PromQL──►  Grafana
AppLogger         ──push───►   Loki        ──LogQL───►  Grafana
node-exporter     ──scrape──►  Prometheus
cAdvisor          ──scrape──►  Prometheus  (non-functional on Docker Desktop)
```

**Grafana provisioning (auto-wired on startup):**
- `grafana/provisioning/datasources/datasources.yml` — registers Prometheus (uid: `prometheus`) and Loki (uid: `loki`) automatically. No manual UI setup needed.
- `grafana/provisioning/dashboards/dashboards.yml` — loads all JSON files from `grafana/dashboards/` on startup.
- `grafana/dashboards/flask-app.json` — Flask App dashboard: request rate, error rate, p95/p99 latency stats, request rate by status/endpoint, latency by endpoint, error logs, all logs.
- `grafana/dashboards/host-metrics.json` — Host Metrics dashboard: CPU usage (total/user/system/iowait), memory (used/buffers/cached/free), network I/O, disk I/O, load average (1m/5m/15m), open file descriptors.
- Default credentials: `admin` / `admin` (set via `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`).

**Prometheus metrics (`prometheus-flask-exporter`):**
- Registers automatically via `PrometheusMetrics(app, ...)` in `create_app()`.
- Exposes `/metrics` in Prometheus text format.
- `DEBUG_METRICS=1` must be set in the app's environment when running with Flask's reloader (`FLASK_DEBUG=1`). Without it the exporter disables itself to avoid double-counting across the reloader's parent/child processes. Already set in `docker-compose.yml`.
- `prometheus.yml` scrapes `app:5000/metrics`, `cadvisor:8080/metrics`, and `node-exporter:9100/metrics` every 15 s.

**Node Exporter (host OS metrics):**
- Mounts `/proc`, `/sys`, and `/` read-only from the host and exposes kernel-level metrics: `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `node_filesystem_avail_bytes`, `node_disk_read_bytes_total`, `node_network_receive_bytes_total`, `node_load1/5/15`.
- Works correctly on Docker Desktop for Windows because it reads from `/proc` and `/sys`, which Docker Desktop maps properly into the WSL2 VM (unlike cAdvisor which needs the overlayfs layer database).
- **Scope:** entire host (or WSL2 VM on Windows) — not per-container. Use cAdvisor for per-container breakdowns.

**cAdvisor (container resource metrics):**
- `gcr.io/cadvisor/cadvisor:v0.47.2` — pinned because v0.55+ requires the containerd socket at `/run/containerd/containerd.sock`, which Docker Desktop for Windows does not expose at that path. v0.47.2 uses the Docker HTTP API but still cannot read `/var/lib/docker/image/overlayfs/layerdb/mounts/` on Docker Desktop (path mismatch in the WSL2 VM). Effectively non-functional on Windows Docker Desktop — included for production parity. On a real Linux host it works without changes.
- **Scope:** per-container CPU, memory, network, disk — complements Node Exporter which only shows host totals.

**Node Exporter vs cAdvisor:**
- Node Exporter answers "how loaded is the host?" — total CPU %, memory pressure, disk space, network throughput.
- cAdvisor answers "which container is responsible?" — per-container breakdown of the same resources.
- Both are needed for full visibility; Node Exporter works locally, cAdvisor does not on Docker Desktop.

**Production on AWS Fargate — neither tool runs:**
Fargate is serverless — there is no accessible host OS, Docker socket, or cgroup filesystem. Replace the entire local observability stack with AWS-managed equivalents:

| Local | AWS Fargate |
|---|---|
| Node Exporter + cAdvisor | **CloudWatch Container Insights** — enabled with one ECS cluster setting; collects per-task CPU, memory, network natively from the Fargate hypervisor |
| Prometheus scraping `/metrics` | **ADOT sidecar** (AWS Distro for OpenTelemetry) — runs as a second container in the same Fargate task, scrapes `localhost:5000/metrics`, ships to Amazon Managed Prometheus (AMP) |
| Prometheus (storage) | **Amazon Managed Prometheus (AMP)** |
| Loki | **CloudWatch Logs** — already wired via `CloudWatchLogger`; no changes needed |
| Grafana | **Amazon Managed Grafana (AMG)** — connects to AMP and CloudWatch as data sources |

The only app-side requirement for the production setup is the `/metrics` endpoint — ADOT picks it up without any code changes.

**Adding a new logger backend:**
1. Create a class in `services/app/app/logging/` implementing `LoggerProtocol` (`info`, `warning`, `error` methods).
2. Instantiate it conditionally in `create_app()` and append to `loggers`.
3. Add the required env var to `services/app/app/config.py` base `Config` class.

### Error Handling

Each REST endpoint and GraphQL resolver wraps risky operations (DB commits, S3 calls, UUID parsing) in individual `try/except` blocks with specific messages and appropriate status codes. DB errors always call `db.session.rollback()` before returning.

**S3 `_ensure_bucket`:** `head_bucket` raises `ClientError(404)`, not `client.exceptions.NoSuchBucket`. Always catch `botocore.exceptions.ClientError` and check `e.response["Error"]["Code"]` — catching the named exception variant silently falls through and skips bucket creation.

## Separation of Concerns

Each layer has a strict responsibility. Do not cross these boundaries:

| Layer | Location | Responsibility |
|---|---|---|
| **Models** | `services/app/app/models/` | SQLAlchemy schema only — no business logic, no imports from API or service layers |
| **Services** | `services/app/app/services/` | External integrations (S3, SQS, future: email, payments). No Flask request context assumptions except `current_app.config` |
| **REST handlers** | `services/app/app/api/v1/` | Parse request, validate input, call services/models, return `rest_api_response()`. No raw `jsonify()` calls outside utils |
| **REST utils** | `services/app/app/api/utils/utils.py` | Shared REST helpers (`rest_api_response`). All reusable REST helper functions live here — never inline them in handlers |
| **GraphQL resolvers** | `services/app/app/graphql_api/resolvers/` | Mirror REST handlers but return `Response[T]` typed objects. No direct HTTP response logic |
| **GraphQL utils** | `services/app/app/graphql_api/utils.py` | Shared GraphQL helpers (e.g. model-to-type converters). All reusable GraphQL helper functions live here — never inline them in resolvers |
| **GraphQL types** | `services/app/app/graphql_api/types/` | Strawberry type definitions only — no resolver logic |
| **Extensions** | `services/app/app/extensions.py` | Instantiate `db`, `migrate`, `jwt` as module-level singletons; initialize them in `create_app()` via `init_app()` to avoid circular imports |
| **Config** | `services/app/app/config.py` | All configuration via `os.getenv()` at class definition time. Env vars are never read directly in handlers or services |
| **Logging** | `services/app/app/logging/` | `AppLogger` + logger adapters (`ConsoleLogger`, `SentryLogger`, `CloudWatchLogger`, `LokiLogger`), `mask_sensitive` data filter. No Flask request context assumptions except `current_app.logger_adapter` |

## Code Quality

Pre-commit hooks enforce formatting and linting on every `git commit`. Install once after setting up the dev virtualenv:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

| Hook | Files | Behaviour |
|---|---|---|
| `trailing-whitespace` | non-`.py` | Removes trailing spaces |
| `end-of-file-fixer` | non-`.py` | Ensures files end with a newline |
| `check-yaml` | `.yml`/`.yaml` | Validates YAML syntax |
| `check-toml` | `.toml` | Validates TOML syntax |
| `check-merge-conflict` | all | Fails on unresolved `<<<<<<<` markers |
| `debug-statements` | `.py` | Fails on `breakpoint()` / `pdb.set_trace()` |
| `ruff` (autofix + format) | `.py` | Runs `ruff format` + `ruff check --fix`, re-stages fixed files, then checks for unfixable issues |

**Commit behaviour:**
- Autofixable issues → fixes are applied and staged into the commit automatically (single commit, no second pass needed)
- Unfixable issues → commit aborts with the specific error printed

Run all hooks on the entire codebase without committing:

```bash
pre-commit run --all-files
```

Tool config lives in `pyproject.toml` (`[tool.ruff]`). The hook script is `scripts/ruff_hook.py`.

## Testing

### Structure

Tests live under `tests/app/` mirroring the source tree:

```
tests/
└── app/
    ├── unit/          — pure functions, zero external deps (run in < 2 s)
    │   ├── api/         rest_api_response(), log level selection
    │   ├── graphql_api/ event_to_payload(), field mapping
    │   ├── logging/     mask_sensitive(), AppLogger fanout, CloudWatch serialization
    │   └── services/    CacheService JSON wrap/unwrap, TTL, ping
    ├── integration/   — Flask test client + SQLite in-memory (no Docker needed)
    └── e2e/           — real HTTP against the full CI stack (Docker required)
```

### Running tests

```bash
# Install test dependencies (includes pytest, pytest-flask, pytest-cov, requests)
pip install -r requirements-test.txt

# Unit + integration — no Docker needed, < 2 s
pytest tests/app/unit tests/app/integration

# With coverage report
pytest tests/app/unit tests/app/integration --cov=app --cov-report=term-missing

# E2E — requires the CI stack to be running
docker compose -f docker-compose.ci.yml up -d --wait
pytest tests/app/e2e
docker compose -f docker-compose.ci.yml down
```

### Coverage

Current baseline: **87%** (138 tests, ~2 s). Intentional gaps:
- `aws_s3_service`, `aws_sqs_service` — SDK wiring only, no project logic to verify
- `loki_logger`, `sentry_logger` — thin SDK call wrappers

### Key fixtures (`tests/app/integration/conftest.py`)

| Fixture | Scope | What it does |
|---|---|---|
| `app` | session | `create_app("testing")` with SQLite in-memory + `StaticPool` |
| `fast_bcrypt` | session, autouse | Patches `bcrypt.gensalt` to 4 rounds instead of 13, keeps tests fast |
| `clean_tables` | function, autouse | Truncates all tables after each test for isolation |
| `client` | function | Flask test client |
| `auth_headers` | function | Registers + logs in a user, returns REST `Authorization` header |
| `gql` | function | Posts a GraphQL query to `/graphql`, returns the response |
| `gql_auth_headers` | function | Same as `auth_headers` but via the GraphQL login mutation |
| `mock_cache` | function | Attaches a `MagicMock` as `app.cache`, restores `None` after the test |

### Gotchas

**`fast_bcrypt` infinite recursion** — the side_effect lambda must capture the real function *before* the `with patch(...)` block starts, not call `bcrypt.gensalt` by name (which would be the mock after patching):

```python
_real_gensalt = _bcrypt.gensalt          # capture BEFORE patch starts
with patch("app.models.user.bcrypt.gensalt",
           side_effect=lambda rounds=12: _real_gensalt(rounds=4)):
    yield
```

**GraphQL vs REST auth** — resolvers call `verify_jwt_in_request()` manually, not via `@jwt_required()`. GraphQL always returns HTTP 200 — success/failure lives in `response.data.<resolver>.success`. Integration tests POST to `/graphql` with the `Authorization` header directly.

**SQLite + UUID columns** — both `db.Uuid` (User) and `db.UUID(as_uuid=True)` (Media, Event) work with SQLite in tests. SQLAlchemy handles type coercion transparently.

**E2E `BASE_URL`** — defaults to `http://localhost/api/v1`. Override via `E2E_BASE_URL` env var to point at staging or any other environment.

### Adding tests for a new feature

1. Unit tests in `tests/app/unit/<layer>/` for any new pure/utility functions.
2. REST integration tests in `tests/app/integration/test_<resource>.py`.
3. GraphQL integration tests in `tests/app/integration/test_graphql_<resource>.py`.
4. Add the happy-path to `tests/app/e2e/test_e2e.py` if it involves a new infrastructure dependency (new AWS service, new DB table, etc.).
5. Mock at the service-function boundary, not at the SDK level: `patch("app.api.v1.<module>.<fn>")` or `patch("app.graphql_api.resolvers.<module>.<fn>")`.

## Style Guide

**Naming:**
- Do not use leading underscores for function or variable names (`process_record`, not `_process_record`). Python's underscore-private convention is not used in this codebase.
- S3 object paths are called `content_key` (never `content_url`) — they are keys, not URLs. Presigned URLs are transient and never stored.
- GraphQL type fields use snake_case in Python; Strawberry auto-converts to camelCase in the schema (`media_id` → `mediaId`). The Postman collection uses camelCase field names for GraphQL responses.
- REST response fields use snake_case throughout (`access_token`, `refresh_token`, `media_id`).

**Responses:**
- REST: always use `rest_api_response(success, message, data, status_code)` from `app/api/utils/utils.py`. Never return raw `jsonify()` from handlers.
- GraphQL: always return `Response[T]` with `success`, `message`, and optionally `data`. Never raise exceptions from resolvers.

**Authentication:**
- REST handlers: use `@jwt_required()` decorator.
- GraphQL resolvers: call `verify_jwt_in_request()` manually inside a `try/except` at the top of the resolver — the Flask decorator does not integrate with Strawberry's request handling.

**Postman collection:** `postman_collection.json` at the repo root must be kept in sync with API changes. Update it whenever you add, remove, or rename an endpoint or change a request/response shape. The collection uses collection-level variables (`base_url`, `access_token`, `refresh_token`, `media_id`) and test scripts on Login/Upload requests to auto-capture tokens and IDs for chained requests.

**Adding a new feature:**
1. Add/update the SQLAlchemy model and register it in `services/app/app/models/__init__.py`.
2. Generate and apply a migration.
3. Add any external service logic to `services/app/app/services/`.
4. Add a REST blueprint in `services/app/app/api/v1/` and register it in `services/app/app/api/v1/__init__.py`.
5. Add a GraphQL resolver class in `services/app/app/graphql_api/resolvers/` and merge it into the schema via `merge_types` in `services/app/app/graphql_api/schema.py`.
6. Add the corresponding type to `services/app/app/graphql_api/types/types.py` if needed.

## Lambda Worker Dockerfiles

`lambda/handler.py` supports two runtimes from the same file:
- `handler(event, context)` — Lambda entry point, called by AWS when SQS delivers a batch
- `poll()` — long-running SQS polling loop, called via `if __name__ == "__main__"` for local dev

Two Dockerfiles exist for these two runtimes:

| File | Used by | CMD |
|---|---|---|
| `lambda/Dockerfile` | `docker-compose.yml` worker service | `python handler.py` → runs `poll()` |
| `lambda/Dockerfile.lambda` | `deploy-dev.yml` / `deploy-prod.yml` CI/CD worker image build | `handler.handler` → Lambda RIC calls `handler()` |

Never use `Dockerfile` for the CI/CD image build — it produces a long-running process that is not a valid Lambda container. The deploy workflows already reference `Dockerfile.lambda`.

## CI/CD Pipeline

### Workflows

**`.github/workflows/ci.yml`** — triggers on every push and pull request.

Three parallel jobs:
- `lint` — `ruff format --check` + `ruff check`
- `test` — `pytest tests/app/unit tests/app/integration` with SQLite in-memory (no Docker)
- `e2e` — spins up `docker-compose.ci.yml`, runs `pytest tests/app/e2e`, tears down with `-v`

**`.github/workflows/deploy-dev.yml`** — targets the `dev` environment; triggers manually by default (change to `push: branches: [develop]` to enable automatic deploys on merge).

**`.github/workflows/deploy-prod.yml`** — targets the `production` environment; manual trigger only. Approval gate is on the `migrate` job — approving it unlocks `deploy` and `deploy-workers` for the same run.

The two files are intentionally separate — no branch conditionals, each file has one purpose. They are structurally identical; the only differences are the branch image tag (`develop` vs `main`) and the `environment:` value.

### Job structure

```
build  (all images in parallel)
  ├── migrate-dev          (develop branch — runs ALL migrations before any deploy)
  │     ├── deploy-dev         (needs: [build, migrate-dev] — services in tier order)
  │     └── deploy-workers-dev (needs: [build, migrate-dev] — Lambda workers, parallel with services)
  └── migrate-prod         (main branch — approval gate; approving unlocks entire prod pipeline)
        ├── deploy-prod
        └── deploy-workers-prod
```

### Deploy order within each environment

Migrations are a separate job that must complete before any service or worker is touched:

1. **`migrate-*`** — runs ALL service migrations as one-off ECS Fargate tasks. If any migration fails the entire pipeline stops. Schema is always ahead of code.
2. **`deploy-*`** (services) and **`deploy-workers-*`** (Lambda) — start in parallel once migrate completes. Services deploy in tier order within the job (tier-1 first, then dependents); workers are independent.

### Backward-compatible migrations rule

During a rolling ECS update, old and new task instances run simultaneously against the same database. Every migration must be backward-compatible with the currently-deployed code:
- **Safe**: add a nullable column, add an index, add a table
- **Unsafe**: drop a column the old code still reads, rename a column, change a type non-compatibly

Use a two-phase approach for breaking changes: first deploy adds the new column (old code ignores it), second deploy removes the old column once all instances run the new code.

### Adding a new microservice

1. Create `services/<name>/` with its Dockerfile.
2. Add its ECR repo to `terraform/modules/ecr/main.tf`.
3. Add its ECS service + task definition to `terraform/`.
4. Add a build step in `deploy-dev.yml` and `deploy-prod.yml` with `context: .` and `file: services/<name>/Dockerfile`.
5. Add a `run_migration` call in `migrate` jobs if it has its own DB.
6. Add a deploy step at the correct tier.
7. Add its GitHub environment vars via `terraform output`.

### Required GitHub secrets and variables

**Repository secret** (Settings → Secrets → Actions):
- `AWS_ROLE_ARN` — IAM role for OIDC authentication, output by `terraform output github_actions_role_arn`

**Per-environment variables** (Settings → Environments → `dev` / `production`):
- `ECS_CLUSTER`, `ECS_SERVICE`, `APP_TASK_FAMILY` — from `terraform output`
- `VPC_SUBNETS`, `VPC_SECURITY_GROUPS` — from `terraform output` (used for migration task networking)
- `LAMBDA_FUNCTION_NAME` — from `terraform output`

### CI stack (`.env.ci`)

The CI stack uses `.env.ci` (committed, contains only fake test credentials). It sets `FLASK_ENV=production` to test the production code path. LocalStack provides S3 and SQS. No real AWS credentials are needed for CI.

## Terraform Infrastructure

All AWS infrastructure is declared in `terraform/`. Terraform is an infra-owner operation — run manually when provisioning or changing infrastructure. The CI/CD pipeline handles all ongoing app deployments.

### Module structure

```
terraform/
├── bootstrap/        # Run once: S3 state bucket + DynamoDB lock table (local state)
├── environments/
│   ├── dev.tfvars    # Small sizes, no HTTPS, relaxed WAF, no deletion protection
│   └── prod.tfvars   # Multi-AZ RDS, deletion protection, HTTPS required, 2 ECS tasks
├── modules/
│   ├── networking    # VPC, public/private subnets, NAT gateway, 5 security groups, VPC flow logs
│   ├── ecr           # ECR repos for app + worker; scan on push; keep last 10 images
│   ├── iam           # ECS task execution role, ECS task role, Lambda role, GitHub OIDC role
│   ├── rds           # PostgreSQL 16 encrypted; DATABASE_URL secret in Secrets Manager
│   ├── elasticache   # Redis 7 replication group; encrypted at rest
│   ├── s3            # Media bucket; public access blocked; HTTPS-only bucket policy
│   ├── sqs           # events queue + DLQ; SSE; redrive after 3 failures
│   ├── alb           # ALB; HTTP→HTTPS redirect; TLS 1.3; drop invalid headers
│   ├── waf           # OWASP Top 10, bad inputs, SQLi, per-IP rate limit
│   ├── ecs           # Fargate cluster; task def with secrets from Secrets Manager; service
│   └── lambda        # Container image function in VPC; SQS event source mapping
├── main.tf           # Wires all modules; creates JWT + Flask app secrets in Secrets Manager
├── variables.tf      # All inputs (sizes, flags, image URIs, GitHub org/repo, state bucket)
├── outputs.tf        # All values needed for GitHub environment vars, labelled
└── versions.tf       # AWS ~> 5.0, random ~> 3.0; partial S3 backend
```

### State management

State is stored in S3 with DynamoDB locking. The S3 bucket and DynamoDB table are created by `terraform/bootstrap/` with local state (the bootstrap is the only exception to "never use local state").

`backend.hcl` — fill-in file referencing the state bucket and lock table. **Gitignored** — never committed.

### Bootstrap and first deploy

```bash
# 1. Create state infrastructure (once per AWS account)
cd terraform/bootstrap
terraform init
terraform apply -var="bucket_name=myorg-flask-boilerplate-tfstate"
# Copy outputs → fill in backend.hcl and environments/*.tfvars

# 2. Init main module
cd ../
terraform init -backend-config=backend.hcl

# 3. Create ECR repos first (images must exist before ECS/Lambda can be created)
terraform apply -target=module.ecr -var-file=environments/dev.tfvars

# 4. Push initial images to ECR, then set app_image and worker_image in dev.tfvars

# 5. Full apply
terraform apply -var-file=environments/dev.tfvars

# 6. Populate GitHub environment vars
terraform output
```

### Secrets management

All sensitive values are generated by Terraform and stored in AWS Secrets Manager:
- `DATABASE_URL` — constructed from RDS endpoint + random password; injected into ECS containers via the `secrets` field in the task definition (not environment variables)
- `JWT_SECRET_KEY` — 64-char random string
- `SECRET_KEY` (Flask) — 64-char random string

Secrets are injected at container startup by the ECS agent using the task execution role. The app code reads them as plain environment variables (`os.environ["DATABASE_URL"]`) — no Secrets Manager SDK calls needed in app code.

### IAM roles

| Role | Principal | Permissions |
|---|---|---|
| `ecs-task-execution` | ECS agent | ECR pull, CloudWatch logs, read specific Secrets Manager ARNs |
| `ecs-task` | Flask app | S3 read/write (media bucket), SQS send/receive, CloudWatch logs |
| `lambda` | Lambda service | SQS consume, S3 read/write, Secrets Manager read, VPC networking |
| `github-actions` | GitHub OIDC | ECR push, ECS update, Lambda update, register task def, read/write state bucket, DynamoDB lock |

The GitHub Actions role uses OIDC — no long-lived AWS credentials are stored in GitHub. The trust policy is scoped to the specific repo and the `main`/`develop` branches only.

### Security group rules

| From | To | Port | Protocol |
|---|---|---|---|
| Internet | ALB | 80, 443 | TCP |
| ALB | ECS tasks | 5000 | TCP |
| ECS tasks | RDS | 5432 | TCP |
| ECS tasks | Redis | 6379 | TCP |
| ECS tasks | Internet | 443 | TCP (outbound: ECR, Secrets Manager, CloudWatch) |
| Lambda | RDS | 5432 | TCP |
| Lambda | Redis | 6379 | TCP |
| Lambda | Internet | 443 | TCP (outbound: AWS APIs) |

ECS tasks and Lambda have no inbound rules from the internet. RDS and Redis have no outbound rules.

### Lifecycle rules

- `aws_ecs_service`: `ignore_changes = [task_definition, desired_count]` — CI/CD manages these after initial deploy
- `aws_lambda_function`: `ignore_changes = [image_uri]` — CI/CD manages this
- `aws_s3_bucket` (state bucket in bootstrap): `prevent_destroy = true`
- `aws_dynamodb_table` (lock table in bootstrap): `prevent_destroy = true`
