# 4.65 — Worker audit write failure handling

- Prevent a successful collection from being reported as an overall successful cycle if PostgreSQL audit finalization fails.
- Identify the failure phase (`audit_start`, `collection`, `audit_finish`) without logging exception messages or secrets.
- Do not blindly retry an audit finalization after an ambiguous database commit.
- Reject malformed collection results; explicitly label `audit_persisted` in emitted cycle metadata.
- Add six regression tests for audit start/finish errors, collection failure, invalid result and successful/no-audit paths.

This is a local unit-tested review build, **not** a verified Render/Bitget/PostgreSQL integration or continuous CVD implementation.
