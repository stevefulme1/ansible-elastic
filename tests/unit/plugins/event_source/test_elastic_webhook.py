# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Steve Fulmer (@stevefulme1)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib
import hmac
import json

import pytest

from ansible_collections.stevefulme1.elastic.plugins.event_source.elastic_webhook import (
    _verify_signature,
)


class TestVerifySignature:
    """Test HMAC-SHA256 signature verification."""

    def test_valid_signature(self):
        body = b'{"alert": "test"}'
        token = "my-secret"
        sig = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(body, sig, token) is True

    def test_invalid_signature(self):
        body = b'{"alert": "test"}'
        token = "my-secret"
        assert _verify_signature(body, "badhex", token) is False

    def test_wrong_token(self):
        body = b'{"alert": "test"}'
        token = "my-secret"
        wrong_token = "wrong-secret"
        sig = hmac.new(wrong_token.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(body, sig, token) is False

    def test_empty_body(self):
        body = b""
        token = "my-secret"
        sig = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(body, sig, token) is True
