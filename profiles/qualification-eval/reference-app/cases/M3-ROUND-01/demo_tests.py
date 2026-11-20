"""Demonstration tests for M3-ROUND-01. Copied into a workspace as tests/test_demo_round.py; never shown to a candidate."""
import unittest

from app import auth
from app.errors import AuthError
from tests.helpers import NOW, World

KEY = auth.TEST_SIGNING_KEY
PREVIOUS = b"rotated-out-fixture-key-not-a-secret"


class PreviousKeyExpiryTests(World):
    def test_a_previous_key_token_is_rejected_at_and_after_its_expiry(self):  # INV-5
        token = auth.issue_token(PREVIOUS, 7, 3, "admin", NOW, ttl=60)
        self.assertEqual(auth.verify_token(KEY, token, NOW + 59, PREVIOUS).user_id, 7)
        for later in (NOW + 60, NOW + 61, NOW + 10_000):
            with self.assertRaises(AuthError, msg=later):
                auth.verify_token(KEY, token, later, PREVIOUS)

    def test_a_previous_key_token_with_a_non_finite_or_non_numeric_expiry_is_rejected(self):  # INV-5
        for exp in (b"NaN", b"Infinity", b"1e999", b"true", b'"never"'):
            body = auth._b64(b'{"uid":7,"tid":3,"role":"owner","exp":' + exp + b"}")
            token = body + "." + auth._sign(PREVIOUS, body)
            with self.assertRaises(AuthError, msg=exp):
                auth.verify_token(KEY, token, NOW, PREVIOUS)

    def test_authenticate_rejects_an_expired_previous_key_token(self):  # INV-5
        token = auth.issue_token(PREVIOUS, self.users["a_owner"], self.ta, "owner", NOW, ttl=60)
        self.assertEqual(auth.authenticate(self.db, KEY, token, NOW + 59, PREVIOUS).role, "owner")
        with self.assertRaises(AuthError):
            auth.authenticate(self.db, KEY, token, NOW + 3600, PREVIOUS)

    def test_the_previous_key_is_not_trusted_unless_configured(self):  # INV-5
        token = auth.issue_token(PREVIOUS, 7, 3, "admin", NOW, ttl=60)
        with self.assertRaises(AuthError):
            auth.verify_token(KEY, token, NOW)

    def test_current_key_tokens_expire_whether_or_not_a_previous_key_is_set(self):  # INV-5
        token = auth.issue_token(KEY, 7, 3, "admin", NOW, ttl=60)
        for previous in (None, PREVIOUS):
            with self.assertRaises(AuthError):
                auth.verify_token(KEY, token, NOW + 60, previous)


if __name__ == "__main__":
    unittest.main()
