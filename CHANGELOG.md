# Changelog

All notable changes to QuantumPACS follow [Keep a Changelog](https://keepachangelog.com/).

## [v3.0.0] - 2026-07-30

### Added
- E2E test suite (10 ADR-021 specs, 30 tests)
- Frontend test infrastructure (Vitest + RTL with 200+ tests)
- Comprehensive backend security review (126 findings)
- Sprint 1 security hotfixes (SQL injection, missing permissions, encryption, config)

### Changed
- Production hardening foundation merged (config, Dockerfile, CI, data integrity)
- PWA service worker auto-destruction fix

### Security
- Parameterized all SQL queries in oauth.py and fhir.py
- Added @requires_permission decorators to file endpoints
- encrypt_secret() raises on failure instead of returning plaintext
- Configuration errors raise ConfigurationError instead of sys.exit(1)
