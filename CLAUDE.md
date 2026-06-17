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

# Generate a new migration after changing models
docker compose run --rm migrate flask db migrate -m "description"

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
| `app` | 5000, 5678 | Flask app (dev server + debugpy on 5678) |
| `postgres` | 5432 | Primary database |
| `migrate` | — | One-shot container: runs `flask db upgrade` on startup |
| `localstack` | 4566 | AWS S3 emulator |
| `pgadmin` | 5050 | Postgres GUI |
| `s3-console` | 8080 | S3 bucket GUI (cloudlena/s3manager) |

**Startup order:** `postgres` healthy → `localstack` healthy → `migrate` completes → `app` starts.

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

### Error Handling

Each REST endpoint and GraphQL resolver wraps risky operations (DB commits, S3 calls, UUID parsing) in individual `try/except` blocks with specific messages and appropriate status codes. DB errors always call `db.session.rollback()` before returning.

## Separation of Concerns

Each layer has a strict responsibility. Do not cross these boundaries:

| Layer | Location | Responsibility |
|---|---|---|
| **Models** | `app/models/` | SQLAlchemy schema only — no business logic, no imports from API or service layers |
| **Services** | `app/services/` | External integrations (S3, future: email, payments). No Flask request context assumptions except `current_app.config` |
| **REST handlers** | `app/api/v1/` | Parse request, validate input, call services/models, return `rest_api_response()`. No raw `jsonify()` calls outside utils |
| **GraphQL resolvers** | `app/graphql_api/resolvers/` | Mirror REST handlers but return `Response[T]` typed objects. No direct HTTP response logic |
| **GraphQL types** | `app/graphql_api/types/` | Strawberry type definitions only — no resolver logic |
| **Extensions** | `app/extensions.py` | Instantiate `db`, `migrate`, `jwt` as module-level singletons; initialize them in `create_app()` via `init_app()` to avoid circular imports |
| **Config** | `app/config.py` | All configuration via `os.getenv()` at class definition time. Env vars are never read directly in handlers or services |

## Style Guide

**Naming:**
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
