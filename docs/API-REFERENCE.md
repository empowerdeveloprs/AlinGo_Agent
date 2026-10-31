# API reference (prototype)

Admin browser session:
- `GET /auth/login`
- `POST /auth/login`
- `GET /auth/logout`
- `GET /` dashboard JSON summary
- `GET /devices`
- `POST /devices` JSON `{ "device_uid":"device-001", "label":"Field phone" }`; token returned once
- `GET /admin/features`
- `POST /admin/features/<name>` JSON `{ "enabled": false }`
- `POST /api/v1/admin/surveys` JSON `{ "title":"Survey A", "description":"", "schema":[] }`
- `GET /api/v1/admin/surveys`
- `GET /api/v1/admin/surveys/<id>/responses`
- `POST /api/v1/admin/audit-requests` JSON `{ "device_uid":"device-001", "audit_type":"metadata", "scope":{} }`

Device Bearer token:
- `GET /api/v1/surveys`
- `POST /api/v1/surveys/<id>/responses` JSON object
- `GET /api/v1/audit-requests/pending`
- `POST /api/v1/audit-requests/<id>/result` JSON `{ "result":{} }`

This is a prototype API. Do not expose publicly before production hardening and testing.
