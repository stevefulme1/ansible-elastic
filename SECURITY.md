# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this collection, please send an email to:

**sfulmer@redhat.com**

Please include:
- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Any suggested fixes

We will acknowledge receipt of your vulnerability report within 48 hours and send a more detailed response within 5 business days indicating the next steps in handling your report.

After the initial reply to your report, we will keep you informed of the progress towards a fix and announcement.

## Security Best Practices

When using this collection:

1. **Credentials**: Never hardcode credentials in playbooks. Use Ansible Vault or external secret management systems.
2. **TLS/SSL**: Always use `validate_certs: true` in production environments.
3. **API Keys**: Prefer API key authentication over username/password when possible.
4. **Least Privilege**: Create Elasticsearch users and API keys with minimal required permissions.
5. **Network Security**: Restrict network access to Elasticsearch and Kibana endpoints.
6. **Webhook Secrets**: Always configure webhook secrets for EDA event sources.

## Known Security Considerations

- This collection transmits credentials to Elasticsearch/Kibana APIs. Ensure transport security (HTTPS).
- EDA webhook event sources expose HTTP endpoints. Use authentication and restrict access.
- Kafka event source credentials should be protected using Ansible Vault.
