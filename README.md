# Ansible Collection - stevefulme1.elastic

Ansible collection for managing the Elastic Stack -- Elasticsearch, Kibana, Fleet, Security SIEM, and Event-Driven Ansible integration.

## Modules

### Elasticsearch Core

| Module | Description |
|--------|-------------|
| `component_template` / `component_template_info` | Manage component templates |
| `connector` / `connector_info` | Manage connectors |
| `data_stream` / `data_stream_info` | Manage data streams |
| `enrich_policy` / `enrich_policy_info` | Manage enrich policies |
| `index_template` / `index_template_info` | Manage index templates |
| `ingest_pipeline` / `ingest_pipeline_info` | Manage ingest pipelines |
| `logstash_pipeline` / `logstash_pipeline_info` | Manage Logstash pipelines |
| `query_rule` / `query_rule_info` | Manage query rules |
| `synonym` / `synonym_info` | Manage synonyms |
| `transform` / `transform_info` | Manage transforms |

### Elasticsearch Lifecycle & Backup

| Module | Description |
|--------|-------------|
| `ilm_policy` / `ilm_policy_info` | Index Lifecycle Management policies |
| `slm_policy` / `slm_policy_info` | Snapshot Lifecycle Management policies |
| `snapshot_repository` / `snapshot_repository_info` | Snapshot repositories (S3, GCS, Azure, FS) |

### Elasticsearch Watcher

| Module | Description |
|--------|-------------|
| `watcher` / `watcher_info` | Watch definitions for alerting |

### Elasticsearch Security

| Module | Description |
|--------|-------------|
| `security_role` / `security_role_info` | RBAC role management |
| `security_user` / `security_user_info` | User provisioning |
| `security_role_mapping` / `security_role_mapping_info` | LDAP/SAML group to role mappings |
| `security_api_key` / `security_api_key_info` | API key lifecycle |

### Kibana Spaces & Data

| Module | Description |
|--------|-------------|
| `kibana_space` / `kibana_space_info` | Multi-tenant space management |
| `kibana_data_view` / `kibana_data_view_info` | Index pattern/data view management |
| `kibana_connector` / `kibana_connector_info` | Alerting connectors (Slack, PagerDuty, Jira, etc.) |

### Kibana Operations

| Module | Description |
|--------|-------------|
| `kibana_alerting_rule` / `kibana_alerting_rule_info` | Alerting rules as code |
| `kibana_saved_object` / `kibana_saved_object_info` | Dashboard/visualization import/export |
| `kibana_slo` / `kibana_slo_info` | Service Level Objectives |
| `kibana_maintenance_window` / `kibana_maintenance_window_info` | Alert suppression windows |
| `kibana_case` / `kibana_case_info` | Incident case management |

### Fleet

| Module | Description |
|--------|-------------|
| `fleet_agent_policy` / `fleet_agent_policy_info` | Elastic Agent enrollment policies |
| `fleet_package_policy` / `fleet_package_policy_info` | Integration configurations |
| `fleet_output` / `fleet_output_info` | Output destinations (ES, Logstash, Kafka) |
| `fleet_enrollment_key` / `fleet_enrollment_key_info` | Agent enrollment tokens |
| `fleet_server_host` / `fleet_server_host_info` | Fleet Server endpoint management |

### Security SIEM

| Module | Description |
|--------|-------------|
| `security_detection_rule` / `security_detection_rule_info` | SIEM detection rules |
| `security_exception` / `security_exception_info` | Detection exception lists |
| `security_timeline` / `security_timeline_info` | Investigation timelines |

## EDA Event Source Plugins

| Plugin | Description |
|--------|-------------|
| `elastic_alert` | Event source for Kibana alerting rule triggers |
| `elastic_siem` | Event source for Security detection signals |
| `elastic_watcher` | Event source for Watcher execution history |

## Installation

```bash
ansible-galaxy collection install stevefulme1.elastic
```

## Authentication

All modules require `api_url` and `api_token` parameters, or the equivalent environment variables.

## License

GPL-3.0-or-later
