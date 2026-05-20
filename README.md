# Ansible Collection - stevefulme1.elastic

Ansible collection for the Elasticsearch Serverless API, auto-generated from the official OpenAPI specification.

## Modules

| Module | Description |
|--------|-------------|
| `component_template` | Manage component templates |
| `connector` | Manage connectors |
| `data_stream` | Manage data streams |
| `enrich_policy` | Manage enrich policies |
| `index_template` | Manage index templates |
| `ingest_pipeline` | Manage ingest pipelines |
| `logstash_pipeline` | Manage Logstash pipelines |
| `query_rule` | Manage query rules |
| `synonym` | Manage synonyms |
| `transform` | Manage transforms |

Each module has a corresponding `_info` module for read-only queries.

## Installation

```bash
ansible-galaxy collection install stevefulme1.elastic
```

## Authentication

All modules require `api_url` and `api_token` parameters, or the equivalent environment variables.

## License

GPL-3.0-or-later
