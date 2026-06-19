# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**`migrate.sh`** — interactive migration helper for local development (runs outside Docker, requires Flask in the active virtual environment). Prompts for a migration message, runs `flask db migrate`, then asks whether to immediately apply with `flask db upgrade`. Also calls `flask db init` if the `migrations/` directory does not exist yet.

```bash
bash migrate.sh
```

**`start_infra.sh`** — starts only the infrastructure services (Postgres, LocalStack, migrations) in detached mode. Used when running the Flask app on the host for local debugging.

```bash
bash start_infra.sh
# To stop: docker compose stop postgres localstack
```

**`launch_app_docker_image.sh`** — builds the production Docker image standalone (no compose, no infrastructure) and starts a single detached container on port 5000. Useful for smoke-testing the image in isolation. After startup it hits `/api/v1/health` to verify the server is up and prints the GraphQL playground URL.

```bash
bash launch_app_docker_image.sh
# To stop: docker stop flask-boilerplate
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

## Architecture

### App Factory

`app/__init__.py` uses a factory pattern (`create_app(config_name)`). The REST API version is selected dynamically via the `REST_API_V` env var (default `v1`) using `importlib`, enabling multi-version support without code changes.

### Dual API Layer

Every feature is exposed over both REST and GraphQL. Both share the same models and services — only the transport layer differs.

- **REST:** `app/api/v1/` — blueprints registered at `/api/v1/`
- **GraphQL:** `app/graphql_api/` — Strawberry schema at `/graphql`, with `multipart_uploads_enabled=True` for file uploads

GraphQL resolvers do not use `@jwt_required()` (a Flask decorator) — they call `verify_jwt_in_request()` manually inside each resolver since Strawberry handles the request context differently.

### Configuration

`app/config.py` has three config classes (`DevelopmentConfig`, `ProductionConfig`, `TestingConfig`) all inheriting from `Config`. The production image (`wsgi.py`) runs `create_app('production')`. All AWS/S3 settings must be on the base `Config` class, not only on `DevelopmentConfig`, or they will be absent in production mode.

### S3 / LocalStack Split Endpoint

The S3 service (`app/services/aws_s3_service.py`) maintains two boto3 client modes:

- `_client()` — uses `AWS_S3_ENDPOINT_URL` (`http://localstack:4566`) for internal operations (upload). Resolvable only inside Docker.
- `_client(public=True)` — uses `AWS_S3_PUBLIC_ENDPOINT_URL` (`http://localhost:4566`) for generating presigned URLs. Needed because presigned URLs are opened by the browser on the host machine, which cannot resolve the `localstack` hostname.

In production both env vars are unset (`None`), so boto3 routes to real AWS automatically.

### Models

All models must be imported in `app/models/__init__.py` for Flask-Migrate to detect them. Current models:

- `User` — `id` (UUID PK), `email` (unique), `password_hash`, `created_at`
- `Media` — `id` (UUID PK), `user_id` (FK → users), `content_key` (S3 object key, **not** a URL), `created_at`

`content_key` stores the S3 key (`media/<user_uuid>/<filename>`). Presigned URLs are generated on demand and never persisted.

### Logging

The app uses an Object Adapter pattern. All loggers implement `LoggerProtocol` (`app/utils/logger.py`) and are injected into `AppLogger`, which fans out calls to all of them.

| Class | Location | Behaviour |
|---|---|---|
| `AppLogger` | `app/logging/logger.py` | Fanout adapter; single public method `log(message, level, data, exc)`. `Level` enum exposed as `AppLogger.Level.{INFO,WARN,ERROR}` |
| `ConsoleLogger` | `app/logging/logger.py` | stdout via Python `logging`; DEBUG in dev, WARNING in prod |
| `SentryLogger` | `app/logging/sentry_logger.py` | `info`/`warn` → Sentry breadcrumbs; `error` → `capture_message` with extras |
| `CloudWatchLogger` | `app/logging/cloudwatch_logger.py` | Structured JSON events via `watchtower`; supports `endpoint_url` for LocalStack |
| `LokiLogger` | `app/logging/loki_logger.py` | POSTs structured JSON to Loki's `/loki/api/v1/push`; uses stdlib `urllib` only (no extra dependency); failures are silently swallowed |

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

**Data filtering:** `mask_sensitive()` in `app/logging/data_filter.py` recursively replaces values of sensitive keys (`password`, `token`, `secret`, `authorization`, etc.) with `***`. Applied automatically in `AppLogger.log()` before any logger sees the data. To add keys, extend `_SENSITIVE_KEYS` in `data_filter.py`.

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
1. Create a class in `app/logging/` implementing `LoggerProtocol` (`info`, `warning`, `error` methods).
2. Instantiate it conditionally in `create_app()` and append to `loggers`.
3. Add the required env var to `app/config.py` base `Config` class.

### Error Handling

Each REST endpoint and GraphQL resolver wraps risky operations (DB commits, S3 calls, UUID parsing) in individual `try/except` blocks with specific messages and appropriate status codes. DB errors always call `db.session.rollback()` before returning.

**S3 `_ensure_bucket`:** `head_bucket` raises `ClientError(404)`, not `client.exceptions.NoSuchBucket`. Always catch `botocore.exceptions.ClientError` and check `e.response["Error"]["Code"]` — catching the named exception variant silently falls through and skips bucket creation.

## Separation of Concerns

Each layer has a strict responsibility. Do not cross these boundaries:

| Layer | Location | Responsibility |
|---|---|---|
| **Models** | `app/models/` | SQLAlchemy schema only — no business logic, no imports from API or service layers |
| **Services** | `app/services/` | External integrations (S3, SQS, future: email, payments). No Flask request context assumptions except `current_app.config` |
| **REST handlers** | `app/api/v1/` | Parse request, validate input, call services/models, return `rest_api_response()`. No raw `jsonify()` calls outside utils |
| **REST utils** | `app/api/utils/utils.py` | Shared REST helpers (`rest_api_response`). All reusable REST helper functions live here — never inline them in handlers |
| **GraphQL resolvers** | `app/graphql_api/resolvers/` | Mirror REST handlers but return `Response[T]` typed objects. No direct HTTP response logic |
| **GraphQL utils** | `app/graphql_api/utils.py` | Shared GraphQL helpers (e.g. model-to-type converters). All reusable GraphQL helper functions live here — never inline them in resolvers |
| **GraphQL types** | `app/graphql_api/types/` | Strawberry type definitions only — no resolver logic |
| **Extensions** | `app/extensions.py` | Instantiate `db`, `migrate`, `jwt` as module-level singletons; initialize them in `create_app()` via `init_app()` to avoid circular imports |
| **Config** | `app/config.py` | All configuration via `os.getenv()` at class definition time. Env vars are never read directly in handlers or services |
| **Logging** | `app/logging/` | `AppLogger` + logger adapters (`ConsoleLogger`, `SentryLogger`, `CloudWatchLogger`, `LokiLogger`), `mask_sensitive` data filter. No Flask request context assumptions except `current_app.logger_adapter` |

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
1. Add/update the SQLAlchemy model and register it in `app/models/__init__.py`.
2. Generate and apply a migration.
3. Add any external service logic to `app/services/`.
4. Add a REST blueprint in `app/api/v1/` and register it in `app/api/v1/__init__.py`.
5. Add a GraphQL resolver class in `app/graphql_api/resolvers/` and merge it into the schema via `merge_types` in `app/graphql_api/schema.py`.
6. Add the corresponding type to `app/graphql_api/types/types.py` if needed.
