# Telaryn — Proprietary Source-Available Software

Telaryn is an AI-assisted work management platform built around one principle:

**AI proposes. Humans approve. Telaryn records. Privacy protects every step.**

Telaryn is **proprietary software, not open-source software**. When the source
repository is publicly visible, GitHub visitors can view the code and use
GitHub-provided forking permissions. This does **not** grant a general right
to modify, redistribute, self-host, commercialize, or sublicense Telaryn.
Read the [proprietary source-available notice](LICENSE) and
[third-party notices](THIRD_PARTY_NOTICES.md) for the exact rights and
exceptions. Hosted Telaryn accounts have separate service Terms.

This repository contains selected application code, database migrations,
frontend assets, local-development configuration, and tests. It deliberately
does **not** contain production infrastructure or secrets, private operator
runbooks, or the historical commits of the original Atlas operations
repository. Public Git history of *this* source repository is distinct from
the private Atlas repository.

Making this code visible does not deploy the Telaryn hosted application or
authorize running the included developer configuration on the public internet.
Before a new public-source release, maintainers must complete the
[publication checklist](docs/source-release-checklist.md), run the exact-head
security and functional checks, and obtain explicit owner approval.

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

This repository uses restricted CI that exercises source tests, build and local
database migrations without private Atlas infrastructure jobs. The
[publication checklist](docs/source-release-checklist.md) tracks release gates,
including Alembic migration review and independent history-wide secret scanning.

## Security and licensing

- Never commit credentials, production connection strings, customer data, or
  exported Project/Ticket records.
- See [Security reporting](SECURITY.md).
- If publicly visible, Telaryn remains governed by the [proprietary
  source-available notice](LICENSE), **not** an open-source license. An approved
  user may use the hosted application under separate service Terms of Use.
  Hosted-service use does not permit self-hosting or redistributing the code.
- GitHub's platform terms allow viewing and forking a public repository;
  broader copying, modifying, or commercialization requires permission or
  another right under applicable law.
- Ownership claims cover protectable original work, not general concepts
  or unprotectable ideas.
- Publishing this repository reveals its own retained Git history and PR
  discussions, including historical files since removed from the latest tree.
  The separate, private Atlas operations repository is not part of this history.
