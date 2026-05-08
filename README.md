# CastorOps

CastorOps is a Gemini-driven DevOps AI agent prototype for making GCP application design, deployment, and operations easier to understand.

The current repository contains the local demo-mode backend implementation used for the hackathon flow. It runs entirely in memory and exercises the core workflow without requiring live GCP credentials.

## Current Scope

Implemented:

- Project creation and phase transitions.
- Requirement follow-up question generation.
- Requirement, design, architecture, and security agent workflow orchestration.
- Approval gates for requirements, design, and architecture.
- Architecture proposal validation and editable node updates.
- Target FastAPI app package generation.
- Deterministic Cloud Build apply plan rendering.
- Local Cloud Build deployment simulation.
- Ops dashboard summary sections.
- Timeline events and SSE event encoding helpers.

Not implemented in this repository yet:

- Production FastAPI HTTP server wiring.
- Persistent Firestore / Cloud Storage adapters.
- Live Vertex AI / Gemini provider adapter.
- Live Cloud Build / Cloud Run deployment execution.
- Frontend UI.
- Authentication for production usage.

## Design Document

The main design document is:

- [castor_ops_design_docs_v21.md](castor_ops_design_docs_v21.md)

The design document is the source of truth for the intended hackathon product scope, architecture, and later production direction.

## Requirements

- Python 3.11 or newer.
- No third-party Python package is required for the current local demo and test suite.

## Local Validation

Run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

Compile all Python modules:

```powershell
python -m compileall app tests scripts
```

Run the local end-to-end demo:

```powershell
python scripts\run_full_demo.py --idea "support desk app" --target-project-id demo-gcp-project
```

Run only the requirement workflow demo:

```powershell
python scripts\run_requirement_demo.py --idea "support desk app"
```

Serve the local browser demo:

```powershell
python scripts\serve_demo.py --host 127.0.0.1 --port 8080 --target-project-id demo-gcp-project
```

Then open:

```text
http://127.0.0.1:8080
```

## Repository Layout

```text
app/
  agents/          Agent runtime, schemas, role-specific agents, and tool guard.
  api/             Application facade and API response envelope.
  approvals/       Approval gate models, repository, and service.
  architectures/   Architecture spec models, validation, and versioning.
  auth/            Demo identity boundary.
  codegen/         Target app package generation.
  core/            Shared error types.
  deployments/     Local deployment adapter and deployment records.
  documents/       Versioned document storage.
  ops/             Ops dashboard aggregation.
  projects/        Project model, repository, and phase service.
  security/        Security finding model and service.
  streaming/       SSE encoding helpers.
  timeline/        User-facing timeline events.
  tools/           Guarded tool execution runtime.
  web/             Dependency-free local demo HTTP server and static UI.
  workflows/       Requirement, design, planning, security, apply, and demo workflows.
scripts/
  run_full_demo.py
  run_requirement_demo.py
  serve_demo.py
tests/
  unittest-based behavior tests.
```

## Git Remote

The canonical GitHub repository is:

```text
https://github.com/sh0g0-ikeda/CastorOps
```
