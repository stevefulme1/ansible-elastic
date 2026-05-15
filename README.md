# Elastic Stack Ansible Collection

![CI](https://github.com/stevefulme1/ansible-elastic/workflows/CI/badge.svg)

Ansible collection for managing Elastic Stack (Elasticsearch, Kibana, Fleet) infrastructure with Event-Driven Ansible plugins.

## Description

This collection provides modules for managing Elastic Stack resources that are not covered by community.elastic, including:

- Index Lifecycle Management (ILM) policies
- API key management
- Data streams
- Kibana dashboards and spaces
- Fleet agent policies
- Event-Driven Ansible plugins for Elasticsearch alerting

## Installation

```bash
ansible-galaxy collection install stevefulme1.elastic
```

## Requirements

- Python >= 3.11
- `elasticsearch` Python library >= 8.0.0
- `requests` Python library

Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Modules

### Elasticsearch

- `elastic_ilm_policy` - Manage ILM policies
- `elastic_ilm_policy_info` - Retrieve ILM policy information
- `elastic_api_key` - Manage API keys
- `elastic_api_key_info` - Retrieve API key information
- `elastic_data_stream` - Manage data streams
- `elastic_data_stream_info` - Retrieve data stream information

### Kibana

- `kibana_dashboard` - Import/export Kibana dashboards
- `kibana_dashboard_info` - Retrieve dashboard information
- `kibana_space` - Manage Kibana spaces
- `kibana_space_info` - Retrieve space information

### Fleet

- `fleet_agent_policy` - Manage Elastic Agent policies
- `fleet_agent_policy_info` - Retrieve agent policy information

## Event-Driven Ansible Plugins

### Event Sources

- `watcher_webhook` - Receive Elasticsearch Watcher webhook actions
- `query` - Poll Elasticsearch for alerts/anomalies
- `kafka` - Consume events from Kafka topics

### Example Rulebooks

See `extensions/eda/rulebooks/` for examples:
- `alert_remediation.yml` - Automated alert response
- `security_response.yml` - Security event handling
- `capacity_management.yml` - Infrastructure scaling triggers

## Usage Examples

### Create an ILM Policy

```yaml
- name: Create hot-warm-cold ILM policy
  stevefulme1.elastic.elastic_ilm_policy:
    es_host: localhost
    es_port: 9200
    username: elastic
    password: "{{ elastic_password }}"
    name: logs-policy
    policy:
      phases:
        hot:
          actions:
            rollover:
              max_size: 50GB
              max_age: 30d
        warm:
          min_age: 30d
          actions:
            shrink:
              number_of_shards: 1
        cold:
          min_age: 90d
          actions:
            freeze: {}
        delete:
          min_age: 180d
          actions:
            delete: {}
    state: present
```

### Create a Kibana Dashboard

```yaml
- name: Import dashboard from file
  stevefulme1.elastic.kibana_dashboard:
    kibana_host: localhost
    kibana_port: 5601
    username: elastic
    password: "{{ elastic_password }}"
    dashboard_file: /path/to/dashboard.ndjson
    space: default
    state: present
```

### EDA Watcher Webhook

```yaml
---
- name: Handle Elasticsearch Watcher alerts
  hosts: localhost
  sources:
    - stevefulme1.elastic.watcher_webhook:
        host: 0.0.0.0
        port: 8080
        secret: "{{ webhook_secret }}"
  rules:
    - name: Disk space alert
      condition: event.alert_name == "disk_space_low"
      action:
        run_playbook:
          name: expand_disk.yml
```

## Testing

Run unit tests:
```bash
ansible-test units --docker -v
```

Run sanity tests:
```bash
ansible-test sanity --docker -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Apache-2.0

## Author

Steve Fulmer (sfulmer@redhat.com)
