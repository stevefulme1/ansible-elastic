"""Shared fixtures for stevefulme1.elastic unit tests."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import sys
import importlib
import types
from unittest.mock import MagicMock

import pytest

# Build the ansible_collections namespace path so that
# ansible_collections.stevefulme1.elastic resolves to the repo root.
COLLECTION_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_fake_root = os.path.join(COLLECTION_ROOT, '.test_namespace')
_ns_path = os.path.join(_fake_root, 'ansible_collections', 'stevefulme1', 'elastic')

if not os.path.islink(_ns_path):
    os.makedirs(os.path.join(_fake_root, 'ansible_collections', 'stevefulme1'), exist_ok=True)
    try:
        os.symlink(COLLECTION_ROOT, _ns_path)
    except OSError:
        pass

if _fake_root not in sys.path:
    sys.path.insert(0, _fake_root)

# Ensure the namespace packages are importable
for pkg in ('ansible_collections', 'ansible_collections.stevefulme1'):
    if pkg not in sys.modules:
        try:
            importlib.import_module(pkg)
        except ImportError:
            mod = types.ModuleType(pkg)
            mod.__path__ = [os.path.join(_fake_root, pkg.replace('.', os.sep))]
            mod.__package__ = pkg
            sys.modules[pkg] = mod


@pytest.fixture
def module_args():
    """Return base module args shared by all modules."""
    return {
        "state": "present",
        "api_key": "test-api-key",
        "api_url": "https://api.example.com",
        "validate_certs": True,
        "request_timeout": 30,
    }


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.get.return_value = {"results": []}
    client.POST.return_value = {"id": "test-123"}
    client.put.return_value = {"id": "test-123"}
    client.delete.return_value = None
    return client
