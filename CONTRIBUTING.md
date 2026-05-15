# Contributing to stevefulme1.elastic

Thank you for your interest in contributing to this Ansible collection!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ansible-elastic.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt -r test-requirements.txt`

## Development Guidelines

### Code Style

- Follow [Ansible development guidelines](https://docs.ansible.com/ansible/latest/dev_guide/index.html)
- Use `ansible-lint` to check your changes
- All modules must include comprehensive documentation and examples
- Use type hints in Python code where applicable

### Testing

Run the full test suite before submitting:

```bash
# Sanity tests
ansible-test sanity --docker -v

# Unit tests
ansible-test units --docker -v

# Linting
ansible-lint
```

### Module Development

When adding new modules:

1. Place module in `plugins/modules/`
2. Add corresponding `_info` module if applicable
3. Add unit tests in `tests/unit/plugins/modules/`
4. Update `README.md` and `CHANGELOG.md`
5. Include documentation with DOCUMENTATION, EXAMPLES, and RETURN blocks
6. Use module_utils for shared code (elastic_api.py, kibana_api.py)

### Documentation

- All modules must have complete DOCUMENTATION, EXAMPLES, and RETURN sections
- Update README.md with new features
- Add entries to CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format
- Include docstrings in Python functions

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (Add, Fix, Update, Remove)
- Reference issue numbers when applicable

Example:
```
Add elastic_ilm_policy module for lifecycle management

Implements create, update, and delete operations for Elasticsearch
ILM policies via the /_ilm/policy API.

Fixes #123
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add changelog entry
4. Submit PR with clear description of changes
5. Link related issues
6. Respond to review feedback

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Contact the maintainer at sfulmer@redhat.com or open a discussion in the repository.
