# Contributing to stevefulme1.elastic

Thank you for your interest in contributing to this Ansible collection for the Elastic Stack!

## Getting Started

1. Fork the repository on [GitHub](https://github.com/stevefulme1/ansible-elastic).
2. Clone your fork and create a feature branch.
3. Make your changes and add tests.
4. Submit a pull request.

## Development Setup

```bash
# Clone into the Ansible collection path
mkdir -p ansible_collections/stevefulme1
cd ansible_collections/stevefulme1
git clone https://github.com/stevefulme1/ansible-elastic.git elastic
cd elastic

# Install dependencies
pip install ansible-core pytest pytest-mock pytest-asyncio aiohttp

# Run unit tests
python -m pytest tests/unit/ -v

# Run sanity tests
ansible-test sanity --docker

# Build the collection
ansible-galaxy collection build
```

## Reporting Bugs

Please report bugs via [GitHub Issues](https://github.com/stevefulme1/ansible-elastic/issues/new).

Include:
- Ansible version (`ansible --version`)
- Collection version
- Elasticsearch/Kibana version
- Steps to reproduce
- Expected vs actual behavior

## Code Standards

- All modules must include GPL-3.0 header, DOCUMENTATION, EXAMPLES, and RETURN blocks.
- Run `ansible-test sanity` and `flake8` before submitting.
- Add unit tests for new modules.

## Developer Certificate of Origin

By contributing to this project you agree to the Developer Certificate of Origin (DCO).
