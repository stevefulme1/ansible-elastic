# Changelog

## [2.1.2] - 2026-05-18

### Security
- Add `no_log: true` to password and api_key fields in role argument_specs
- Change EDA webhook host default from `0.0.0.0` to `127.0.0.1`
- Add `secret: true` to credential options in inventory plugins


## [2.1.1] - 2026-05-18

### Security
- Prevent credential leak in API request bodies — connection params (host, username, password, api_key, validate_certs) are now stripped before create/update payloads are sent to the remote API
- Add timeout=30 to all HTTP methods to prevent indefinite hangs
- Harden .gitignore to exclude secrets, credentials, and IDE artifacts

## [2.0.0] - 2026-05-17

### Added
- Pagination support (limit/offset) for all _info modules
- Searchable snapshot and CCR modules
- EDA event filter plugins
- Comprehensive unit and integration test suites
- Pre-commit and linting configuration

### Fixed
- Duplicate username parameter in elastic_user module
- Duplicate dict keys in test fixtures
- Role README files added for Galaxy compliance
- Galaxy import validation issues resolved
- CI failures resolved

## [1.2.0] - 2026-05-15

### Added
- 50 modules covering full Elastic Stack platform API
- CRUD + info module for every resource type
- EDA source plugins (watcher_webhook, query, kafka)
- Unit tests and CI pipeline

## [1.0.0] - 2026-05-15

### Added
- Initial release with Elasticsearch, Kibana, and Fleet modules
- EDA source plugins for event-driven automation
- Unit tests and CI pipeline
