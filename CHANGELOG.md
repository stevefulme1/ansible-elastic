# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

### Added

- 50 modules covering full Elastic Stack platform API
- CRUD + info module for every resource type
- EDA source plugins for event-driven automation
- Unit tests and CI pipeline

## [1.0.0-initial] - 2026-05-15

### Added

- Initial release of stevefulme1.elastic collection
- Elasticsearch modules:
  - `elastic_ilm_policy` - Manage ILM policies
  - `elastic_ilm_policy_info` - Retrieve ILM policy information
  - `elastic_api_key` - Manage API keys
  - `elastic_api_key_info` - Retrieve API key information
  - `elastic_data_stream` - Manage data streams
  - `elastic_data_stream_info` - Retrieve data stream information
- Kibana modules:
  - `kibana_dashboard` - Import/export Kibana dashboards
  - `kibana_dashboard_info` - Retrieve dashboard information
  - `kibana_space` - Manage Kibana spaces
  - `kibana_space_info` - Retrieve space information
- Fleet modules:
  - `fleet_agent_policy` - Manage Elastic Agent policies
  - `fleet_agent_policy_info` - Retrieve agent policy information
- Event-Driven Ansible plugins:
  - `watcher_webhook` event source - Receive Elasticsearch Watcher webhooks
  - `query` event source - Poll Elasticsearch for alerts
  - `kafka` event source - Consume from Kafka topics
- Example rulebooks for alert remediation, security response, and capacity management
- Module utilities for Elasticsearch and Kibana API clients
- Documentation fragments for common authentication parameters
- Unit tests and CI workflows

[1.0.0]: https://github.com/stevefulme1/ansible-elastic/releases/tag/v1.0.0
