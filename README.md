# Telaryn — Private Source Release Candidate

Telaryn is an AI-assisted work management platform built around one principle:

**AI proposes. Humans approve. Telaryn records. Privacy protects every step.**

This **private review branch** contains a copied snapshot of application code,
migrations, frontend assets, and selected tests for publication screening.
It is **not yet cleared for public visibility or self-hosted production use**.
Private operator runbooks, cloud infrastructure automation, deployment secrets,
and prior Atlas Git history are deliberately excluded.

**Do not make this repository public yet.** The owner must review this exact
snapshot, resolve the release blockers, run CI and independent security scans,
and approve the exact history and current source. Telaryn is **proprietary and source-available, not open source**.
The included [LICENSE](LICENSE) permits viewing and platform-authorized GitHub
forking, but does not grant broad source-code reuse rights.

## Application architecture

- Python / FastAPI / SQLAlchemy / Alembic backend
- React / Vite frontend
- Local SQLite development or an isolated PostgreSQL integration environment
- Optional AI provider boundary and human approval before authoritative changes
- Workspace authorization, private AI-context controls, and auditable work history

For an environment-neutral deployment diagram and security boundary, see
[Deployment architecture](docs/deployment-architecture.md). For deployment
verification guidance, see [Operations overview](docs/operations-overview.md).

## Local development

Prerequisites: Python 3.12+, Node.js, npm. Create a virtual environment before
running the backend.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m fastapi dev app/main.py --app app
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

For a local PostgreSQL container integration, Docker Compose is available.
This is a **development-only** configuration and must not be deployed to the
internet without an independent hardening review.

```powershell
docker compose up --build -d postgres
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.cli set-password atlas.local@example.com
docker compose up -d
```

The local Compose account is not a production identity. Do not reuse its
development credentials in another environment.

## Checks

```powershell
python -m pytest
cd frontend
npm ci
npm run lint
npm test
npm run build
```

This branch uses a separate, restricted CI workflow that excludes private
Atlas infrastructure jobs. See `docs/source-release-checklist.md` for the
remaining publication gates, including Alembic migration review and independent
credential scanning.

## Security and licensing

- Never commit credentials, production connection strings, customer data, or
  exported Project/Ticket records.
- See [Security reporting](SECURITY.md).
- Telaryn is publicly viewable under the [proprietary source-available
  notice](LICENSE), **not** an open-source license. An approved user may use
  the hosted Telaryn application under its separate service Terms of Use.
  Hosted-service use does not permit self-hosting or redistributing the code.
- GitHub's platform terms allow viewing and forking a public repository;
  broader copying, modifying, or commercialization requires permission or
  another right under applicable law.
- Ownership claims cover protectable original work, not general concepts
  or unprotectable ideas.
- Exclusion from this preview does not erase material from the original private
  repository's historical branches, commits, PRs, or Actions logs.
