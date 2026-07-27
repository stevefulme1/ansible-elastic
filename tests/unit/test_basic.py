"""Basic unit tests for stevefulme1.elastic collection."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type


def test_import_api_client():
    """Verify the API client module can be imported."""
    from ansible_collections.stevefulme1.elastic.plugins.module_utils.api_client import (
        Client,
        ClientError,
        argument_spec,
        auth_mutually_exclusive,
        auth_required_one_of,
        auth_required_together,
    )
    assert callable(argument_spec)
    assert callable(auth_mutually_exclusive)
    assert callable(auth_required_one_of)
    assert callable(auth_required_together)

    spec = argument_spec()
    assert "api_url" in spec
    assert "api_key" in spec
    assert "api_username" in spec
    assert "api_password" in spec
    assert spec["api_url"]["required"] is True
    assert spec["api_key"]["no_log"] is True
    assert spec["api_password"]["no_log"] is True


def test_import_doc_fragment():
    """Verify the auth doc fragment can be imported."""
    from ansible_collections.stevefulme1.elastic.plugins.doc_fragments.auth import (
        ModuleDocFragment,
    )
    assert hasattr(ModuleDocFragment, "DOCUMENTATION")
    assert "api_url" in ModuleDocFragment.DOCUMENTATION
    assert "api_key" in ModuleDocFragment.DOCUMENTATION
    assert "api_username" in ModuleDocFragment.DOCUMENTATION
