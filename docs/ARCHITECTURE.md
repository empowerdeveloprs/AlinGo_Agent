# Architecture

## Components
- Flask app factory: `server/app.py`
- Independent server blueprints/services: `server/modules/`
- SQLite database: `server/instance/` (runtime; never commit production data)
- Android client: native app, with separate modules per responsibility
- Deployment examples: HTTPS reverse proxy + service manager (configure separately)

## Module contract
Each module should own its routes, service logic, validation, tests and README. Cross-module imports should use service interfaces, not duplicate business logic. Feature flags are enforced on the server as well as in the UI.

## Current implementation boundary
This package includes a modular server prototype for devices, survey CRUD/submission, audit request queue, result receipt, feature flags, and audit events. It does not yet implement push delivery, a finished browser dashboard UI, production-grade CSRF protection, rate limits, tenant isolation, or a complete Android client.
