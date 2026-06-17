# python-flask-boilerplate

A clean, production-ready Flask Web API boilerplate to start your Python backend projects fast.

Provides a solid foundation for scalable RESTful and GraphQL APIs with clean folder architecture, JWT authentication, database migrations, and AWS S3 media uploads out of the box.

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
- [Debugging](#debugging)
- [Production Image](#production-image)

---

## Features

- REST API (Flask blueprints, versioned at `/api/v1/`)
- GraphQL API (Strawberry, at `/graphql`)
- JWT authentication (access + refresh tokens)
- PostgreSQL with Flask-Migrate (Alembic)
- S3 media uploads (LocalStack for local dev, real AWS in production)
- Docker Compose full-stack setup with all infrastructure included
- VSCode debugger integration (Docker attach + host launch)

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
│   ├── models/              # SQLAlchemy models (User, Media)
│   ├── services/            # External integrations (S3)
│   ├── api/
│   │   └── v1/              # REST blueprints (auth, media, health)
│   └── graphql_api/
│       ├── resolvers/       # GraphQL mutations and queries
│       ├── types/           # Strawberry type definitions
│       └── schema.py        # Merged GraphQL schema
├── migrations/              # Alembic migration files
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

Copy the example env file and fill in the values:

```bash
cp .env.local.example .env.local
```

> `.env.local` is never committed. It is the single source of truth for all local configuration.

Default values that work out of the box with Docker Compose:

```env
DATABASE_URL=postgresql://user:password@postgres:5432/appdb
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me

AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=media-bucket
AWS_S3_ENDPOINT_URL=http://localstack:4566
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:4566

PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

> Change `SECRET_KEY` and `JWT_SECRET_KEY` to random strings before deploying anywhere. Everything else can stay as-is for local development.

---

## Running the Full Stack

```bash
docker compose up --build
```

This builds the dev image and starts all services. On first run, database migrations are applied automatically before the app starts.

| Service | URL | Purpose |
|---|---|---|
| Flask API | http://localhost:5000 | REST + GraphQL |
| GraphQL playground | http://localhost:5000/graphql | Interactive query UI |
| pgAdmin | http://localhost:5050 | Postgres GUI |
| S3 console | http://localhost:8080 | S3 bucket browser |
| LocalStack | http://localhost:4566 | AWS S3 emulator |

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

---

## Example Flow

This walks through the complete user journey from registration to file retrieval using `curl`.

### 1. Register

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "secret123"}'
```

```json
{"success": true, "message": "", "data": {}}
```

### 2. Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
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
curl -X POST http://localhost:5000/api/v1/media/upload \
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
curl http://localhost:5000/api/v1/media/<media_id>/url \
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
curl -X POST http://localhost:5000/api/v1/auth/refresh \
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

The GraphQL playground is available at http://localhost:5000/graphql. The same flow works over GraphQL using mutations and queries.

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

Whenever you add or change a SQLAlchemy model, generate a migration:

```bash
# Generate the migration file
docker compose run --rm migrate flask db migrate -m "adds session table"

# Apply it
docker compose run --rm migrate flask db upgrade
```

Or use the interactive helper script (requires Flask in your local venv):

```bash
bash migrate.sh
```

> New models must be imported in `app/models/__init__.py` or Flask-Migrate won't detect them.

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
