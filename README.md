<div align="center">
  <img src="docs/favicon.svg" width="80" height="80" alt="Python Flask Boilerplate"/>
</div>

# python-flask-boilerplate

A production-ready **Python 3.12 / Flask** boilerplate for building scalable **REST** and **GraphQL** APIs — engineered for teams who want a clean architecture without spending weeks on infrastructure.

Ships fully wired: **JWT authentication** (Flask-JWT-Extended), **PostgreSQL** with SQLAlchemy 2 ORM and Alembic migrations, **AWS S3** file uploads with presigned URLs, async event processing via **AWS SQS + Lambda**, **Redis** caching, **Nginx** reverse proxy with DDoS protection, structured logging to **Sentry / CloudWatch / Loki**, **Prometheus** metrics with **Grafana** dashboards, **Docker Compose** full-stack setup, and a **pytest** test suite (unit · integration · E2E) — all production-wired from the first commit.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running the Full Stack](#running-the-full-stack)
- [API Reference](#api-reference)
- [Example Flow](#example-flow)
- [GraphQL API](#graphql-api)
- [Database Migrations](#database-migrations)
- [Reverse Proxy & Load Balancer](#reverse-proxy--load-balancer)
- [Async Event Processing](#async-event-processing)
- [Redis Cache](#redis-cache)
- [Logging](#logging)
- [Observability](#observability)
  - [Grafana dashboards](#grafana-dashboards-pre-built-auto-provisioned)
  - [App metrics](#app-metrics-metrics)
  - [Host metrics](#host-metrics-node-exporter)
  - [Logs](#logs-loki)
  - [Production on AWS Fargate](#production-on-aws-fargate)
- [Security](#security)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deploying to AWS](#deploying-to-aws)
- [Debugging](#debugging)
- [Production Image](#production-image)

---

## Features

- REST API (Flask blueprints, versioned at `/api/v1/`)
- GraphQL API (Strawberry, at `/graphql`)
- JWT authentication (access + refresh tokens)
- PostgreSQL with Flask-Migrate (Alembic) — migrations auto-generated and applied on every `docker compose up --build`
- S3 media uploads (LocalStack for local dev, real AWS in production)
- Async event processing via **SQS + Lambda** — Flask publishes events to SQS; a Lambda function (locally: a worker container) consumes them and writes to Postgres
- **Nginx reverse proxy** as the single entry point on port 80, with DDoS protection: rate limiting, connection capping, Slowloris mitigation, and oversized-request blocking
- **Redis caching** — opt-in per endpoint via `CacheService`; disabled gracefully when `REDIS_URL` is not set
- Structured logging with Sentry (error tracking), CloudWatch (log aggregation), and Loki (local log UI)
- Automatic sensitive data masking before any log is emitted
- Prometheus metrics endpoint (`/metrics`) with per-endpoint request duration histograms
- Host OS metrics via Node Exporter (CPU, memory, disk I/O, network, load average)
- Pre-built Grafana dashboards for app metrics and host metrics, auto-provisioned on startup
- Docker Compose full-stack setup with all infrastructure included
- VSCode debugger integration (Docker attach + host launch)
- Pre-commit hooks for automatic code formatting and linting (Ruff)

---

## How It Works

Every feature is exposed over **both REST and GraphQL**. Both share the same database models and business logic — only the transport layer differs. You can use whichever style fits your client best.

**Authentication** uses JWT (JSON Web Tokens). After logging in you receive two tokens:
- `access_token` — short-lived (15 minutes), sent with every protected request in the `Authorization: Bearer <token>` header
- `refresh_token` — long-lived (30 days), used only to obtain a new `access_token` when the current one expires

**Media uploads** are stored in S3 (or LocalStack locally). The database only stores the S3 object key — never a URL. When you need to display a file, the API generates a **presigned URL** on demand: a time-limited, signed link that grants direct browser access to the file without exposing your S3 credentials. Presigned URLs expire after 24 hours by default.

---

## Project Structure

```
.
├── app/
│   ├── __init__.py          # App factory (create_app)
│   ├── config.py            # Dev / Prod / Test config classes
│   ├── extensions.py        # db, migrate, jwt singletons
│   ├── models/              # SQLAlchemy models (User, Media, Event)
│   ├── services/            # External integrations (S3, SQS)
│   ├── logging/             # AppLogger, SentryLogger, CloudWatchLogger, data_filter
│   ├── api/
│   │   └── v1/              # REST blueprints (auth, media, events, cache, health)
│   └── graphql_api/
│       ├── resolvers/       # GraphQL mutations and queries
│       ├── types/           # Strawberry type definitions
│       ├── utils.py         # Shared GraphQL helpers (model → type converters)
│       └── schema.py        # Merged GraphQL schema
├── lambda/
│   ├── handler.py           # Shared: handler(event, context) for Lambda + poll() for local dev
│   ├── Dockerfile           # Local dev — long-polling worker (used by docker-compose)
│   ├── Dockerfile.lambda    # AWS Lambda — uses Lambda Python base image
│   └── requirements.txt     # Lambda dependencies (boto3, sqlalchemy, psycopg2)
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint + test on every push and pull request
│       └── deploy.yml       # Build images → push to ECR → deploy to ECS + Lambda (manual trigger)
├── terraform/
│   ├── bootstrap/           # Run once: creates S3 state bucket + DynamoDB lock table
│   ├── environments/
│   │   ├── dev.tfvars       # Dev-specific sizes and flags
│   │   └── prod.tfvars      # Prod: Multi-AZ, deletion protection, HTTPS
│   ├── modules/
│   │   ├── networking/      # VPC, NAT gateway, subnets, security groups, VPC flow logs
│   │   ├── ecr/             # ECR repositories for app and worker images
│   │   ├── iam/             # ECS roles, Lambda role, GitHub OIDC deploy role
│   │   ├── rds/             # PostgreSQL on RDS + DATABASE_URL stored in Secrets Manager
│   │   ├── elasticache/     # Redis (ElastiCache replication group)
│   │   ├── s3/              # Media bucket with encryption + HTTPS-only policy
│   │   ├── sqs/             # Events queue + dead-letter queue
│   │   ├── alb/             # Application Load Balancer with HTTP→HTTPS redirect
│   │   ├── waf/             # WAF: OWASP Top 10, SQLi rules, per-IP rate limit
│   │   ├── ecs/             # Fargate cluster, task definition, service
│   │   └── lambda/          # Container image Lambda function + SQS event source
│   ├── main.tf              # Root module — wires all child modules
│   ├── variables.tf         # All input variables with descriptions
│   ├── outputs.tf           # Outputs map directly to GitHub environment vars
│   ├── versions.tf          # Provider pins + S3 backend stub
│   └── backend.hcl          # Fill-in template — gitignored, never committed
├── nginx/
│   └── nginx.conf           # Reverse proxy config with DDoS protection
├── migrations/              # Alembic migration files (auto-generated on up --build)
├── Dockerfile               # Production image (gunicorn)
├── Dockerfile.dev           # Dev image (Flask dev server + debugpy)
├── docker-compose.yml       # Full local stack
├── wsgi.py                  # Production entrypoint
├── migrate.sh               # Interactive migration helper
├── start_infra.sh           # Start only DB + S3 (for host debugging)
└── .vscode/
    ├── launch.json          # VSCode debug configurations
    └── tasks.json           # Pre/post debug tasks
```

---

## Prerequisites

### Required for everyone

| Tool | Version | Purpose | Download |
|---|---|---|---|
| **Git** | any | Clone the repository | [git-scm.com](https://git-scm.com/downloads) |
| **Docker Desktop** | 4.x+ | Runs the entire infrastructure (Postgres, S3, app) in containers — no manual installs needed | [docker.com](https://www.docker.com/products/docker-desktop/) |

Docker Desktop includes **Docker Compose** and the Docker CLI. No separate installation is needed for Postgres, LocalStack, or any other service — Docker handles all of it.

Verify your installation:

```bash
docker --version        # Docker version 26.x.x
docker compose version  # Docker Compose version v2.x.x
```

### Required for host-based debugging only

If you want to run Flask directly on your machine (debug Option 2), you also need:

| Tool | Version | Purpose | Download |
|---|---|---|---|
| **Python** | 3.12+ | Runs the Flask app and installs dependencies | [python.org](https://www.python.org/downloads/) |
| **VSCode** | any | IDE with integrated debugger | [code.visualstudio.com](https://code.visualstudio.com/) |
| **Python extension** (VSCode) | any | Enables Python debugging in VSCode | [marketplace link](https://marketplace.visualstudio.com/items?itemName=ms-python.python) |

Verify Python:

```bash
python --version   # Python 3.12.x
```

> On macOS/Linux you may need to use `python3` instead of `python`.

### Optional but recommended

| Tool | Purpose | Download |
|---|---|---|
| **Postman** | Test and explore the API endpoints — a ready-made collection is included (`postman_collection.json`) | [postman.com](https://www.postman.com/downloads/) |

---

## Environment Setup

Create a `.env.local` file in the project root. This file is never committed — it is the single source of truth for all local configuration.

All values below work out of the box with Docker Compose. Before deploying to production, replace `SECRET_KEY` and `JWT_SECRET_KEY` with strong random strings.

**Core**

```env
SECRET_KEY=dev-secret-key
JWT_SECRET_KEY=19c7a47a7b4330769667c83436293f125474076d58399761e61a4a16da3ee206
DATABASE_URL=postgresql://user:password@postgres:5432/appdb
```

> Generate a production `JWT_SECRET_KEY` with `openssl rand -hex 32`.

**Flask**

```env
FLASK_ENV=development
FLASK_APP=wsgi.py
REST_API_V=v1
REST_API_VN=1.0.0
GRAPHQL_API_VN=1.0.0
```

**AWS / S3 — LocalStack defaults (no real AWS needed locally)**

```env
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=media-bucket
AWS_S3_ENDPOINT_URL=http://localstack:4566
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:4566
PRESIGNED_URL_EXPIRY=86400
```

**SQS — LocalStack defaults**

```env
AWS_SQS_ENDPOINT_URL=http://localstack:4566
SQS_QUEUE_URL=http://localstack:4566/000000000000/events-queue
```

> `AWS_SQS_ENDPOINT_URL` and `SQS_QUEUE_URL` are injected by Docker Compose automatically for the `app` and `worker` containers. Add them to `.env.local` only when running Flask directly on the host (debug Option 2), replacing `localstack` with `localhost`.

**Redis**

```env
REDIS_URL=redis://redis:6379/0
```

> Injected by Docker Compose for the `app` container. For host debugging use `redis://localhost:6379/0`.

**Observability — wired to local Docker services**

```env
CLOUDWATCH_LOG_GROUP=/myapp/dev
CLOUDWATCH_STREAM_NAME=app
CLOUDWATCH_ENDPOINT_URL=http://localstack:4566
LOKI_URL=http://loki:3100
```

**Admin tools**

```env
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

**Error tracking — optional**

```env
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
```

---

## Running the Full Stack

```bash
docker compose up --build
```

This builds the dev image and starts all services. On first run, database migrations are applied automatically before the app starts.

| Service | URL | Purpose |
|---|---|---|
| **Nginx** (entry point) | http://localhost | Reverse proxy — all API traffic goes here |
| Flask API (direct) | http://localhost:5000 | Bypass Nginx for debugging |
| GraphQL playground | http://localhost/graphql | Interactive query UI |
| pgAdmin | http://localhost:5050 | Postgres GUI |
| S3 console | http://localhost:8080 | S3 bucket browser |
| LocalStack | http://localhost:4566 | AWS S3 + SQS emulator |
| Loki | http://localhost:3100 | Log aggregation |
| Prometheus | http://localhost:9090 | Metrics database + query UI |
| Grafana | http://localhost:3000 | Dashboards (metrics + logs) |
| Node Exporter | http://localhost:9100/metrics | Host OS raw metrics |

To tail app logs:

```bash
docker compose logs -f app
```

To rebuild only the app container after changing dependencies:

```bash
docker compose up --build app
```

> Code changes are reflected immediately without rebuilding — the source directory is mounted as a volume and Flask's dev server reloads on file changes.

---

## API Reference

All REST responses follow the same envelope shape:

```json
{
  "success": true,
  "message": "",
  "data": {}
}
```

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | None | Returns status and API version |

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | None | Create a new user account |
| POST | `/api/v1/auth/login` | None | Log in, receive access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Refresh token | Exchange refresh token for a new access token |

### Media

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/media/upload` | Access token | Upload a file to S3, returns presigned URL |
| GET | `/api/v1/media/<media_id>/url` | Access token | Get a fresh presigned URL for an existing file |

### Events

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/events` | Access token | Publish an event to SQS; returns `message_id` (202) |
| GET | `/api/v1/events` | Access token | List the last 100 processed events from the database |

### Cache (dev / diagnostics)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/cache/ping` | None | Check Redis connectivity |
| GET | `/api/v1/cache/test` | None | Read a cached value (cache miss computes and stores it) |
| DELETE | `/api/v1/cache/test` | None | Invalidate the cached value |

---

## Example Flow

This walks through the complete user journey from registration to file retrieval using `curl`.

### 1. Register

```bash
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "secret123"}'
```

```json
{"success": true, "message": "", "data": {}}
```

### 2. Login

```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "secret123"}'
```

```json
{
  "success": true,
  "message": "",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

Save the `access_token` — you need it for all subsequent requests. It expires after 15 minutes.

### 3. Upload a file

```bash
curl -X POST http://localhost/api/v1/media/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/photo.jpg"
```

```json
{
  "success": true,
  "message": "",
  "data": {
    "media_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "url": "http://localhost:4566/media-bucket/media/...?X-Amz-Signature=...",
    "expires_in": 3600
  }
}
```

The `url` in the response is a presigned link you can open directly in a browser or `<img>` tag. Save `media_id` to request a fresh URL later.

### 4. Get a fresh presigned URL

Access tokens and presigned URLs both expire. Use the stored `media_id` to generate a new URL at any time:

```bash
curl http://localhost/api/v1/media/<media_id>/url \
  -H "Authorization: Bearer <access_token>"
```

```json
{
  "success": true,
  "message": "",
  "data": {
    "url": "http://localhost:4566/media-bucket/media/...?X-Amz-Signature=..."
  }
}
```

### 5. Refresh an expired access token

When your access token expires (after 15 minutes), use the refresh token to get a new one without logging in again:

```bash
curl -X POST http://localhost/api/v1/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

```json
{
  "success": true,
  "message": "",
  "data": {
    "access_token": "eyJ..."
  }
}
```

---

## GraphQL API

The GraphQL playground is available at http://localhost/graphql. The same flow works over GraphQL using mutations and queries.

> For authenticated requests in the playground, add an HTTP header: `{"Authorization": "Bearer <access_token>"}`

### Register

```graphql
mutation {
  register(email: "alice@example.com", password: "secret123") {
    success
    message
  }
}
```

### Login

```graphql
mutation {
  login(email: "alice@example.com", password: "secret123") {
    success
    message
    data {
      accessToken
      refreshToken
    }
  }
}
```

### Upload a file

File uploads over GraphQL use the [multipart request spec](https://github.com/jaydenseric/graphql-multipart-request-spec). Use a client that supports it (e.g. the playground, Postman, or Apollo Client with the upload link):

```graphql
mutation UploadFile($file: Upload!) {
  uploadFile(file: $file) {
    success
    message
    data {
      mediaId
      url
      expiresIn
    }
  }
}
```

### Get a presigned URL

```graphql
query {
  signedUrl(mediaId: "3fa85f64-5717-4562-b3fc-2c963f66afa6") {
    success
    data
  }
}
```

> GraphQL field names use **camelCase** (`accessToken`, `mediaId`, `expiresIn`) even though Python uses snake_case — Strawberry converts them automatically.

---

## Database Migrations

Migrations are **automatic** — every `docker compose up --build` runs `flask db migrate` (detects model changes, generates a file if needed) followed by `flask db upgrade`. You never need to run migration commands manually for new models.

To run manually (e.g. to apply a handwritten migration outside of the full stack):

```bash
docker compose exec app flask db migrate -m "description"
docker compose exec app flask db upgrade
```

> Use `exec app` (not `run --rm migrate`) so the generated file is written to the host via the volume mount.

> New models must be imported in `app/models/__init__.py` or Flask-Migrate won't detect them.

---

## Reverse Proxy & Load Balancer

All external traffic enters through **Nginx on port 80** (`nginx/nginx.conf`). The Flask app is not exposed publicly — Nginx proxies to it internally at `app:5000`.

**DDoS protections applied:**

| Protection | Mechanism | Config |
|---|---|---|
| Rate limiting (general) | `limit_req` | 300 req/min per IP, burst 50 |
| Rate limiting (auth) | `limit_req` | 20 req/min per IP, burst 5 — slows brute-force |
| Connection cap | `limit_conn` | 20 concurrent connections per IP |
| Slowloris mitigation | Timeouts | Body/header/send: 10 s, keepalive: 30 s |
| Oversized requests | Buffer limits | Header: 1 k, body buffer: 16 k |
| Blocked methods | `if` guard | Only GET, POST, PUT, PATCH, DELETE, OPTIONS allowed |
| Metrics lockdown | `allow`/`deny` | `/metrics` reachable only from Docker internal network |

**Adding a new microservice:**

1. Add the service to `docker-compose.yml` — no port exposure needed (stays internal).
2. Add an upstream and a location block to `nginx/nginx.conf`:

```nginx
upstream payments {
    server payments:3000;
}

location /payments/ {
    limit_req        zone=api burst=50 nodelay;
    limit_req_status 429;
    proxy_pass       http://payments/;
}
```

3. Reload Nginx without downtime:

```bash
docker compose up -d payments
docker compose exec nginx nginx -s reload
```

Service-to-service calls within the Docker network use service names directly (`http://payments:3000`) — routing through Nginx for internal traffic adds unnecessary latency.

---

## Async Event Processing

The stack includes an end-to-end SQS → Lambda pipeline:

```
Flask app  →  SQS queue  →  Lambda (locally: worker container)  →  PostgreSQL
```

**Publishing an event** (REST):

```bash
curl -X POST http://localhost/api/v1/events \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"type": "user.action", "payload": {"detail": "example"}}'
```

```json
{"success": true, "message": "", "data": {"message_id": "<sqs-id>"}}
```

**Reading processed events:**

```bash
curl http://localhost/api/v1/events \
  -H "Authorization: Bearer <access_token>"
```

**How it works locally:**

The `worker` container (`lambda/handler.py`) polls SQS using long-polling (`WaitTimeSeconds=5`). When a message arrives it inserts a row into the `events` table using `ON CONFLICT DO NOTHING` on `sqs_message_id` — safe for at-least-once delivery. Messages are deleted from the queue only after a successful DB write.

**Deploying to AWS:**

`lambda/handler.py` already exposes `handler(event, context)` — the Lambda entry point. Two Dockerfiles handle the two runtimes:

| File | Used by | Runtime |
|---|---|---|
| `lambda/Dockerfile` | `docker-compose.yml` | Long-polling loop (`poll()`) — blocks and polls SQS continuously |
| `lambda/Dockerfile.lambda` | `deploy.yml` CI/CD | AWS Lambda base image — Lambda runtime invokes `handler()` per SQS batch |

The CI/CD pipeline builds `Dockerfile.lambda` and pushes it to ECR. On AWS, `DATABASE_URL` points to RDS, `SQS_QUEUE_URL` to the real queue, and `AWS_SQS_ENDPOINT_URL` is unset (boto3 routes to real AWS automatically).

> For high-concurrency Lambda deployments, add **RDS Proxy** in front of your database to multiplex connections. `NullPool` is already configured in `handler.py` so each invocation closes its connection immediately.

---

## Redis Cache

Redis is included in the stack and exposed to the app via `REDIS_URL`. The `CacheService` wraps it with a simple `get` / `set` / `delete` / `ttl` / `ping` interface.

**`/api/v1/cache/ping`** — returns `{"redis": "ok"}` or `{"redis": "unavailable"}`.

**`/api/v1/cache/test`** — demonstrates a read-through cache: first call computes a value and stores it for 60 seconds, subsequent calls return it from Redis with the remaining TTL.

**Using the cache in a handler:**

```python
from flask import current_app

cache = current_app.cache
if cache:
    cached = cache.get("my:key")
    if cached is None:
        result = expensive_computation()
        cache.set("my:key", result, ttl=300)
```

If `REDIS_URL` is not set, `current_app.cache` is `None` and all cache calls are skipped — the app degrades gracefully without errors.

---

## Security

The boilerplate ships with a hardened baseline. The measures below are active out of the box — understand them before changing anything.

### Application

**`SECRET_KEY` is required** — the app refuses to start if `SECRET_KEY` is not set. There is no default fallback. Set it in `.env.local` for local dev; Secrets Manager injects it in production via the ECS task definition.

**File uploads are restricted** — only `jpg`, `jpeg`, `png`, `gif`, `webp`, `pdf`, `mp4`, `mov` are accepted. Anything else returns `415`. Maximum upload size is 50 MB (Flask's `MAX_CONTENT_LENGTH`). To extend the allowlist, edit `_ALLOWED_EXTENSIONS` in [app/api/v1/media.py](app/api/v1/media.py).

**SQL queries are stripped from logs** — SQLAlchemy exceptions include the full query and bound parameters in their string representation. `sanitize_traceback()` in [app/logging/data_filter.py](app/logging/data_filter.py) redacts `[SQL: ...]` and `[parameters: ...]` blocks from every traceback before it reaches any log backend (Console, Sentry, CloudWatch, Loki). The Lambda worker has an equivalent `_safe_exc()` helper.

**GraphQL introspection is disabled in production** — controlled by `GRAPHQL_INTROSPECTION` in `config.py`. `True` in `DevelopmentConfig` (playground needs it), `False` in `ProductionConfig`. Introspection lets unauthenticated callers enumerate your entire schema.

**JWT algorithm is pinned** — `JWT_ALGORITHM = "HS256"` is explicit in config, preventing silent changes on library upgrades.

### Nginx (local dev)

All responses include:

| Header | Protects against |
|---|---|
| `X-Frame-Options: SAMEORIGIN` | Clickjacking |
| `X-Content-Type-Options: nosniff` | MIME-type sniffing attacks |
| `Referrer-Policy: strict-origin-when-cross-origin` | URL leakage to third parties |
| `Permissions-Policy: geolocation=(), camera=(), microphone=()` | Unwanted browser API access |
| `server_tokens off` | Nginx version disclosure |

**HSTS is commented out** — `Strict-Transport-Security` is in the config but disabled. Enable it only after TLS is live on the ALB; enabling it over HTTP permanently breaks access for returning visitors.

**Content-Security-Policy is not set** — a CSP covering the GraphQL playground requires tuning per deployment. Add it once you know your frontend's allowed origins.

### Infrastructure (production, via Terraform)

| Measure | What it does |
|---|---|
| Redis TLS | `transit_encryption_enabled = true` — all data between ECS tasks and ElastiCache is encrypted in transit (`rediss://` scheme) |
| Non-root containers | Flask app runs as `app` system user; Lambda runs as `nobody` — no root access if a container is compromised |
| ECS task role scoped to send-only SQS | Flask app can only `SendMessage`. Only the Lambda worker can `ReceiveMessage` and `DeleteMessage` |
| Secrets Manager 7-day recovery | All secrets have a 7-day deletion grace period — accidental `terraform destroy` is recoverable |
| WAF logging | All blocked requests logged to CloudWatch (`aws-waf-logs-{prefix}`, 90-day retention) — full forensic trail of who was blocked and why |
| ALB + private subnets | ECS tasks have no public IP — only the ALB is internet-facing. Traffic flows: Internet → WAF → ALB → ECS (private) |

### What is not included (by design)

| Gap | Reason | How to add |
|---|---|---|
| Content-Security-Policy | Requires per-deployment origin config | Add to `nginx/nginx.conf` once frontend origins are known |
| JWT refresh token blacklisting | Stateless by design | Add Redis-backed blacklist if logout must immediately invalidate tokens |
| Redis AUTH token | Private subnet + SG is sufficient isolation | Add `auth_token` in `terraform/modules/elasticache/main.tf` for multi-tenant setups |
| MIME type sniffing | Files go to S3, never executed server-side | Add `python-magic` if serving files from a public CDN |

---

## Code Quality

Pre-commit hooks run automatically on every `git commit` and keep the codebase consistently formatted. Set them up once after creating your dev virtualenv:

```bash
python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
pre-commit install
```

From that point on, every commit automatically:

1. Removes trailing whitespace and fixes missing end-of-file newlines (non-Python files)
2. Validates YAML and TOML syntax
3. Fails if unresolved merge conflict markers are found
4. Fails if `breakpoint()` or `pdb.set_trace()` calls are left in Python files
5. Reformats Python code with **Ruff** (`ruff format`)
6. Applies all autofixable lint violations with **Ruff** (`ruff check --fix`)
7. Re-stages any fixed files so they are included in the same commit — no second commit needed
8. Aborts the commit only if unfixable violations remain, printing exactly what needs to be fixed manually

To run the hooks across the entire codebase without committing:

```bash
pre-commit run --all-files
```

Ruff configuration (line length, selected rules, import ordering) lives in `pyproject.toml`.

---

## Testing

### Install test dependencies

```bash
python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-test.txt
```

### Unit and integration tests (no Docker required)

Tests use SQLite in-memory for the database and mock all AWS services — no infrastructure needed.

```bash
pytest tests/app/unit tests/app/integration
```

With coverage:

```bash
pytest tests/app/unit tests/app/integration --cov=app --cov-report=term-missing
```

Current coverage: **87%** across 138 tests in under 2 seconds.

### E2E tests (CI/CD only)

E2E tests make real HTTP requests through Nginx to a fully running stack — real Postgres, LocalStack S3/SQS, and Redis. They are designed to run in CI/CD pipelines, not during local development.

```bash
# Start the CI stack (stripped-down: no Grafana, Prometheus, pgAdmin, etc.)
docker compose -f docker-compose.ci.yml up -d --wait

# Run smoke tests
pytest tests/app/e2e/

# Tear down
docker compose -f docker-compose.ci.yml down
```

Override the target URL to run against a deployed environment:

```bash
E2E_BASE_URL=https://staging.example.com/api/v1 pytest tests/app/e2e/
```

### Test structure

```
tests/
└── app/
    ├── unit/          — pure functions, no external deps (< 2 s total)
    │   ├── api/         rest_api_response(), log level selection
    │   ├── graphql_api/ event_to_payload(), field mapping
    │   ├── logging/     mask_sensitive(), AppLogger fanout, CloudWatch serialization
    │   └── services/    CacheService JSON wrap/unwrap, TTL default, ping failure
    ├── integration/   — Flask test client + SQLite in-memory (< 2 s total)
    │   ├── REST:        test_auth, test_media, test_events, test_cache, test_health
    │   └── GraphQL:     test_graphql_auth, test_graphql_media, test_graphql_events,
    │                    test_graphql_cache, test_graphql_health
    └── e2e/           — real HTTP through Nginx (CI/CD only)
        └── test_e2e.py  health check, full auth flow, S3 upload, SQS event publish
```

---

## CI/CD Pipeline

Two GitHub Actions workflows are included in `.github/workflows/`. They are designed for a **GitOps** model: merging to `develop` deploys to dev, merging to `main` deploys to production.

### `ci.yml` — runs on every push and pull request

Three parallel jobs, no Docker infrastructure needed for lint and unit tests:

| Job | What it does | Docker needed |
|---|---|---|
| **Lint** | `ruff format --check` + `ruff check` | No |
| **Unit & Integration Tests** | pytest with SQLite in-memory (~2 s) | No |
| **E2E Tests** | Spins up `docker-compose.ci.yml`, runs full e2e suite | Yes |

### `deploy-dev.yml` and `deploy-prod.yml` — triggered manually by default

Two separate files — one per environment, no branch conditionals. To enable automatic deploys, change each file's trigger from `workflow_dispatch` to a push trigger:

```yaml
# deploy-dev.yml
on:
  push:
    branches: [develop]

# deploy-prod.yml
on:
  push:
    branches: [main]
```

**Pipeline stages:**

```
build  ── all images pushed to ECR before anything deploys
  │
  ├── migrate-dev  ── ALL migrations run before any service update
  │     │              ⚠ schema must stay backward-compatible (rolling update)
  │     ├── deploy-dev          ── services in dependency tier order
  │     └── deploy-workers-dev  ── Lambda workers (parallel with services)
  │
  └── migrate-prod  ── same, but pauses for manual approval first
        ├── deploy-prod
        └── deploy-workers-prod
```

**Why migrations are a separate job:** during a rolling ECS update, old and new task instances run simultaneously against the same database. Migrations must complete and be backward-compatible before any instance picks up the new code.

**Adding a new microservice:** add a build step to `build`, a `run_migration` call in both `migrate-*` jobs, and a deploy step at the correct tier in both `deploy-*` jobs. Workers go in `deploy-workers-*`.

The production approval gate is a native GitHub feature: create a `production` environment in **Settings → Environments**, add required reviewers, and the workflow pauses automatically.

### Required GitHub configuration

**Repository secret** (Settings → Secrets → Actions):

| Secret | Value |
|---|---|
| `AWS_ROLE_ARN` | IAM role ARN created by Terraform (`terraform output github_actions_role_arn`) |

**Environment variables** (Settings → Environments → `dev` and `production`):

| Variable | Source |
|---|---|
| `ECS_CLUSTER` | `terraform output ecs_cluster` |
| `ECS_SERVICE` | `terraform output ecs_service` |
| `APP_TASK_FAMILY` | `terraform output app_task_family` |
| `VPC_SUBNETS` | `terraform output vpc_subnets` |
| `VPC_SECURITY_GROUPS` | `terraform output vpc_security_groups` |
| `LAMBDA_FUNCTION_NAME` | `terraform output lambda_function_name` |

All of these are printed by `terraform output` after the first `terraform apply`.

---

## Deploying to AWS

The `terraform/` directory contains a complete, production-ready AWS infrastructure definition. It provisions everything the app needs — networking, compute, database, cache, queues, and security — as code.

### Architecture

```
Internet → WAF → ALB (public subnets) → ECS Fargate (private subnets)
                                              ↓              ↓
                                            RDS          ElastiCache
                                              ↓
                                  SQS queue → Lambda worker
```

- The app is never directly reachable from the internet — only the ALB is public
- NAT Gateway allows ECS tasks to reach AWS APIs (ECR, Secrets Manager, CloudWatch) outbound
- All secrets (DB password, JWT key, Flask secret key) are stored in AWS Secrets Manager and injected into containers at startup — never in environment files or task definitions
- WAF sits in front of the ALB with OWASP Top 10 rules, SQLi protection, and per-IP rate limiting

### Prerequisites

| Tool | Purpose |
|---|---|
| [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.6 | Infrastructure provisioning |
| [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | Authenticate and bootstrap |
| AWS account with admin access | Target for provisioning |

### Bootstrap (once per AWS account)

The S3 state bucket and DynamoDB lock table must exist before Terraform can store its own state. A minimal bootstrap module creates them with local state:

```bash
cd terraform/bootstrap
terraform init
terraform apply -var="bucket_name=myorg-flask-boilerplate-tfstate"
# outputs: bucket_name and lock_table_name → copy these into the next step
```

### First deploy

```bash
cd terraform

# 1. Fill in terraform/backend.hcl with the bucket and table names from bootstrap
# 2. Fill in environments/dev.tfvars with your GitHub org, repo, and image placeholders

terraform init -backend-config=backend.hcl

# 3. Create ECR repositories first (images don't exist yet)
terraform apply -target=module.ecr -var-file=environments/dev.tfvars

# 4. Push initial images to ECR
#    Either trigger the deploy workflow manually, or push directly:
#    aws ecr get-login-password | docker login --username AWS --password-stdin <registry>
#    docker build -t <registry>/flask-boilerplate-dev/app:latest .
#    docker push <registry>/flask-boilerplate-dev/app:latest
#    (repeat for lambda/Dockerfile.lambda → /worker:latest)

# 5. Set app_image and worker_image in dev.tfvars to the ECR URLs from step 3
# 6. Apply everything
terraform apply -var-file=environments/dev.tfvars

# 7. Copy outputs into GitHub environment vars
terraform output
```

### Subsequent infrastructure changes

```bash
terraform plan -var-file=environments/dev.tfvars   # preview
terraform apply -var-file=environments/dev.tfvars  # apply
```

App image updates (ECS task definition, Lambda image) are managed by the CI/CD pipeline — Terraform uses `lifecycle { ignore_changes = [...] }` on those fields so it never rolls back what CI/CD deployed.

### Estimated monthly cost

| Environment | ~Cost |
|---|---|
| Dev (single task, db.t3.micro, no HTTPS) | ~$83/month |
| Production (2 tasks, db.t3.small, Multi-AZ, HTTPS) | ~$134/month |

The NAT Gateway (~$32/month) is the largest fixed cost in both environments. RDS and ElastiCache are the next largest. All compute (ECS Fargate, Lambda) scales to zero when idle.

---

## Debugging

Two debug modes are supported, both configured in `.vscode/launch.json`.

### Option 1 — Attach debugger to Docker container

The `app` service runs Flask under `debugpy` (port 5678) and mounts the source directory as a volume, so code changes are reflected immediately without rebuilding.

**Steps:**

1. Start the full stack:
   ```bash
   docker compose up --build
   ```
2. Open the **Run & Debug** panel in VSCode (`Ctrl+Shift+D`).
3. Select **"Docker: Attach to Flask"** and press **F5**.

VSCode connects to `debugpy` on `localhost:5678`. Set breakpoints anywhere in the source — they will be hit on the next matching request.

> To debug startup code, add `--wait-for-client` to the `CMD` in `Dockerfile.dev`. The app will pause on start until the debugger attaches.

---

### Option 2 — Run Flask on the host

Run only the infrastructure in Docker and the Flask app directly on your machine. This can give a faster feedback loop.

**One-time setup** — create and activate a virtual environment with dev dependencies:

```bash
python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

**Steps:**

1. Open the **Run & Debug** panel in VSCode (`Ctrl+Shift+D`).
2. Select **"Local: Flask Debug"** and press **F5**.

VSCode automatically:
- Starts Postgres, LocalStack, and runs migrations before launch (`preLaunchTask`)
- Launches Flask under `debugpy` on port 5000 with hot reload enabled
- Stops the infrastructure containers when you stop the debugger (`postDebugTask`)

**Note on hostnames:** when Flask runs on the host it cannot resolve Docker service names like `postgres` or `localstack`. The launch config overrides those env vars automatically:

| Variable | Docker value | Host override |
|---|---|---|
| `DATABASE_URL` | `postgresql://...@postgres:5432/appdb` | `postgresql://...@localhost:5432/appdb` |
| `AWS_S3_ENDPOINT_URL` | `http://localstack:4566` | `http://localhost:4566` |
| `AWS_S3_PUBLIC_ENDPOINT_URL` | `http://localhost:4566` | `http://localhost:4566` |

If your `.env.local` uses different Postgres credentials, update `DATABASE_URL` in `.vscode/launch.json` to match.

---

## Logging

The app uses a fanout logger (`AppLogger`) that dispatches every log call to one or more backends simultaneously. Backends are opt-in — only those with env vars set are activated.

| Backend | Env var required | Purpose |
|---|---|---|
| Console | — | Always active; DEBUG in dev, WARNING in prod |
| Sentry | `SENTRY_DSN` | Error tracking — `info`/`warn` become breadcrumbs, `error` becomes a captured event |
| CloudWatch | `CLOUDWATCH_LOG_GROUP` | Structured JSON log aggregation (production) |
| Loki | `LOKI_URL` | Structured log aggregation, queryable in Grafana (local dev) |

All log `data` payloads are automatically filtered by `mask_sensitive()` before reaching any backend — sensitive keys (`password`, `token`, `secret`, `authorization`, etc.) are replaced with `***`.

### Sentry setup

1. Create a project at [sentry.io](https://sentry.io) and copy the DSN.
2. Add to `.env.local`:
   ```env
   SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
   ```
3. Restart the app — errors will appear in your Sentry Issues dashboard with breadcrumb trails.

### CloudWatch setup (production)

```env
CLOUDWATCH_LOG_GROUP=/myapp/production
CLOUDWATCH_STREAM_NAME=app
AWS_ACCESS_KEY_ID=<real-key>
AWS_SECRET_ACCESS_KEY=<real-secret>
AWS_DEFAULT_REGION=us-east-1
```

### CloudWatch setup (local via LocalStack)

```env
CLOUDWATCH_LOG_GROUP=/myapp/dev
CLOUDWATCH_STREAM_NAME=app
CLOUDWATCH_ENDPOINT_URL=http://localstack:4566
```

Query logs locally with the AWS CLI:

```bash
# macOS / Linux
aws --endpoint-url=http://localhost:4566 logs get-log-events \
  --log-group-name /myapp/dev \
  --log-stream-name app

# Windows (Git Bash) — MSYS_NO_PATHCONV=1 prevents path conversion
MSYS_NO_PATHCONV=1 aws --endpoint-url=http://localhost:4566 logs get-log-events \
  --log-group-name /myapp/dev \
  --log-stream-name app
```

### Loki setup (local dev)

Loki runs as a Docker Compose service and requires no extra configuration — `LOKI_URL=http://loki:3100` is already set in `.env.local`. Logs are pushed automatically on every request. To query them, use Grafana (see [Observability](#observability)).

---

## Observability

The stack ships with a full observability pipeline: **Prometheus** for metrics, **Loki** for logs, **Node Exporter** for host metrics, and **Grafana** to visualise everything.

### Grafana dashboards (pre-built, auto-provisioned)

Both Prometheus and Loki data sources and both dashboards are wired automatically on startup — no manual configuration needed. Open Grafana at `http://localhost:3000` (login: `admin` / `admin`) and go to **Dashboards**.

**Flask App** dashboard:

| Panel | What it shows |
|---|---|
| Request Rate | Requests/sec across all endpoints |
| Error Rate | % of non-2xx responses (green → yellow → red) |
| p95 / p99 Latency | Response time percentiles in ms |
| Request Rate by Status | Time series, 4xx coloured yellow, 5xx red |
| Response Time Percentiles | p50 / p95 / p99 over time |
| Request Rate by Endpoint | Per-endpoint throughput with mean/max table |
| Latency by Endpoint (p95) | Per-endpoint p95 with mean/max table |
| Error Logs | Live Loki feed, errors only |
| All Logs | Live Loki feed, all levels |

**Host Metrics** dashboard:

| Panel | What it shows |
|---|---|
| CPU Usage (stat) | Total CPU % (green → yellow → red) |
| Memory Usage (stat) | % of RAM in use |
| Disk Usage (stat) | `/` filesystem % used |
| System Load 1m (stat) | `node_load1` |
| CPU (timeseries) | total / user / system / iowait breakdown |
| Memory (timeseries) | used / buffers / cached / free in bytes |
| Network I/O | bytes/sec received vs transmitted |
| Disk I/O | bytes/sec read vs written |
| Load Average | 1m / 5m / 15m over time |
| Open File Descriptors | allocated vs system maximum |

### App metrics (`/metrics`)

The Flask app exposes a Prometheus-format metrics endpoint at `http://localhost:5000/metrics`. Prometheus scrapes it every 15 seconds. Query directly at `http://localhost:9090`.

Useful PromQL queries:

```promql
# Request rate per endpoint (last 5 min)
rate(flask_http_request_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))

# Error rate (non-2xx responses)
rate(flask_http_request_total{status!~"2.."}[5m])
```

> `prometheus-flask-exporter` disables itself when Flask's reloader is active. `DEBUG_METRICS=1` (already set in `docker-compose.yml`) re-enables it for local dev.

### Host metrics (Node Exporter)

Node Exporter exposes OS-level metrics from `/proc` and `/sys` at `http://localhost:9100/metrics`. Prometheus scrapes it every 15 seconds. Useful PromQL queries:

```promql
# CPU usage %
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage %
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk space used %
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100

# Network throughput
rate(node_network_receive_bytes_total{device!="lo"}[5m])
```

> On Windows with Docker Desktop, Node Exporter reports WSL2 VM metrics (not Windows host metrics). This is expected — Docker containers run inside WSL2.

### Logs (Loki)

Every log emitted through `AppLogger` is pushed to Loki with labels `app`, `env`, and `level`. Query in Grafana Explore with LogQL:

```logql
{app="flask-boilerplate"}                    # all logs
{app="flask-boilerplate", level="error"}     # errors only
{app="flask-boilerplate"} |= "upload"        # text search
```

### cAdvisor (container metrics)

cAdvisor (`http://localhost:8081`) provides per-container CPU, memory, and network metrics. It works correctly on Linux hosts. **On Docker Desktop for Windows it does not report container metrics** due to a path mismatch in the WSL2 layer database — this is a known limitation. Use Node Exporter for host-level metrics locally and rely on CloudWatch Container Insights in production.

### Production on AWS Fargate

Neither Node Exporter nor cAdvisor can run on Fargate (no access to host OS). AWS-managed equivalents replace them with zero configuration changes to the app:

| Local | AWS production |
|---|---|
| Node Exporter + cAdvisor | **CloudWatch Container Insights** — enable on the ECS cluster, collects per-task CPU/mem/network from the Fargate hypervisor |
| Prometheus + `/metrics` | **ADOT sidecar** (AWS Distro for OpenTelemetry) in the Fargate task → **Amazon Managed Prometheus** |
| Loki | **CloudWatch Logs** — already wired via `CloudWatchLogger`, no code changes needed |
| Grafana | **Amazon Managed Grafana** — connects to AMP + CloudWatch as data sources |

The only app-side requirement is the `/metrics` endpoint — ADOT picks it up automatically.

---

## Production Image

The production Docker image uses `Dockerfile` (gunicorn, 4 workers, no debugpy). To smoke-test it in isolation:

```bash
bash launch_app_docker_image.sh
# To stop: docker stop flask-boilerplate
```

This starts only the app container with no database or LocalStack, so any endpoint that touches Postgres or S3 will fail. Use it only to verify the image builds and the process starts cleanly.

For real deployments, set the following environment variables on your server (remove all LocalStack/local-only vars):

```env
DATABASE_URL=postgresql://user:password@your-db-host:5432/appdb
SECRET_KEY=<random-string>
JWT_SECRET_KEY=<random-string>
AWS_ACCESS_KEY_ID=<real-key>
AWS_SECRET_ACCESS_KEY=<real-secret>
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
# AWS_S3_ENDPOINT_URL and AWS_S3_PUBLIC_ENDPOINT_URL must NOT be set
# so boto3 routes to real AWS automatically
```
