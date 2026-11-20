import unittest

from app import auth
from app.errors import AuthError, Invalid

from tests.helpers import NOW, TEST_LOGIN_PW, World

KEY = auth.TEST_SIGNING_KEY


class TokenTests(unittest.TestCase):
    def test_valid_token_round_trips(self):
        token = auth.issue_token(KEY, 7, 3, "admin", NOW)
        p = auth.verify_token(KEY, token, NOW + 10)
        self.assertEqual((p.user_id, p.tenant_id, p.role), (7, 3, "admin"))

    def test_expired_token_rejected_at_and_after_expiry(self):  # INV-5
        token = auth.issue_token(KEY, 7, 3, "admin", NOW, ttl=60)
        auth.verify_token(KEY, token, NOW + 59)
        for later in (NOW + 60, NOW + 61, NOW + 10_000):
            with self.assertRaises(AuthError):
                auth.verify_token(KEY, token, later)

    def test_bad_signature_rejected(self):  # INV-5
        token = auth.issue_token(KEY, 7, 3, "admin", NOW)
        with self.assertRaises(AuthError):
            auth.verify_token(b"another-key", token, NOW)

    def test_tampered_payload_rejected(self):  # INV-1: tenant claim cannot be edited
        forged = auth.issue_token(KEY, 7, 99, "owner", NOW)
        body, _ = forged.split(".")
        original = auth.issue_token(KEY, 7, 3, "viewer", NOW)
        _, sig = original.split(".")
        with self.assertRaises(AuthError):
            auth.verify_token(KEY, body + "." + sig, NOW)

    def test_malformed_tokens_rejected(self):
        for bad in ("", "abc", "a.b.c", None, 12, "....", "x.y"):
            with self.assertRaises(AuthError):
                auth.verify_token(KEY, bad, NOW)

    def test_non_numeric_expiry_rejected(self):
        body = auth._b64(b'{"uid":1,"tid":1,"role":"owner","exp":true}')
        token = body + "." + auth._sign(KEY, body)
        with self.assertRaises(AuthError):
            auth.verify_token(KEY, token, NOW)


class PasswordTests(unittest.TestCase):
    def test_hash_and_verify(self):
        stored = auth.hash_password("correct-horse")
        self.assertTrue(auth.verify_password("correct-horse", stored))
        self.assertFalse(auth.verify_password("wrong-horse!", stored))

    def test_hashes_are_salted(self):
        self.assertNotEqual(auth.hash_password("correct-horse"), auth.hash_password("correct-horse"))

    def test_short_password_rejected(self):
        with self.assertRaises(Invalid):
            auth.hash_password("short")

    def test_garbage_stored_hash_never_verifies(self):
        for bad in ("", "nodollar", "zz$zz", "$"):
            self.assertFalse(auth.verify_password("correct-horse", bad))


class LoginTests(World):
    def test_login_binds_token_to_requested_tenant_and_actual_role(self):
        token = auth.login(self.db, KEY, "a_admin@example.test", "correct-horse", self.ta, NOW)
        p = auth.verify_token(KEY, token, NOW)
        self.assertEqual((p.tenant_id, p.role), (self.ta, "admin"))

    def test_login_to_foreign_tenant_rejected(self):  # INV-1
        with self.assertRaises(AuthError):
            auth.login(self.db, KEY, "a_admin@example.test", "correct-horse", self.tb, NOW)

    def test_wrong_password_and_unknown_user_look_identical(self):
        errs = []
        for email, pw in (("a_admin@example.test", "wrong-pass!"), ("nobody@example.test", "correct-horse")):
            with self.assertRaises(AuthError) as ctx:
                auth.login(self.db, KEY, email, pw, self.ta, NOW)
            errs.append(str(ctx.exception))
        self.assertEqual(errs[0], errs[1])

    def test_removed_member_cannot_log_in(self):
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_member"],))
        with self.assertRaises(AuthError):
            auth.login(self.db, KEY, "a_member@example.test", "correct-horse", self.ta, NOW)


class SignatureStrictnessTests(unittest.TestCase):
    """REV-003: the signature must match exactly, not by prefix, length or case."""

    def setUp(self):
        self.token = auth.issue_token(KEY, 7, 3, "owner", NOW)
        self.body, self.sig = self.token.split(".")

    def test_empty_truncated_extended_and_recased_signatures_rejected(self):  # INV-5
        for bad in ("", self.sig[:1], self.sig[:32], self.sig[:-1], self.sig + "0",
                    self.sig.upper(), " " + self.sig):
            with self.assertRaises(AuthError, msg=repr(bad)):
                auth.verify_token(KEY, self.body + "." + bad, NOW)

    def test_exact_signature_still_accepted(self):
        self.assertEqual(auth.verify_token(KEY, self.token, NOW).user_id, 7)


class AuthenticateTests(World):
    """REV-001: authority comes from live membership, never from a token claim."""

    def token_for(self, name, tenant, role="owner"):
        return auth.issue_token(KEY, self.users[name], tenant, role, NOW)

    def test_role_is_read_live_not_from_the_token(self):  # INV-2
        token = self.token_for("a_viewer", self.ta, role="owner")  # inflated claim
        self.assertEqual(auth.authenticate(self.db, KEY, token, NOW).role, "viewer")

    def test_demoted_member_loses_authority_immediately(self):  # INV-2
        token = auth.login(self.db, KEY, "a_admin@example.test", TEST_LOGIN_PW, self.ta, NOW)
        self.db.execute("UPDATE memberships SET role = 'viewer' WHERE user_id = ?", (self.users["a_admin"],))
        self.assertEqual(auth.authenticate(self.db, KEY, token, NOW).role, "viewer")

    def test_removed_member_token_rejected(self):  # INV-2
        token = auth.login(self.db, KEY, "a_member@example.test", TEST_LOGIN_PW, self.ta, NOW)
        self.db.execute("UPDATE memberships SET active = 0 WHERE user_id = ?", (self.users["a_member"],))
        with self.assertRaises(AuthError):
            auth.authenticate(self.db, KEY, token, NOW)

    def test_token_for_tenant_user_never_joined_rejected(self):  # INV-1
        with self.assertRaises(AuthError):
            auth.authenticate(self.db, KEY, self.token_for("outsider", self.ta), NOW)

    def test_expired_and_forged_tokens_still_rejected(self):  # INV-5
        token = auth.issue_token(KEY, self.users["a_owner"], self.ta, "owner", NOW, ttl=10)
        with self.assertRaises(AuthError):
            auth.authenticate(self.db, KEY, token, NOW + 10)
        with self.assertRaises(AuthError):
            auth.authenticate(self.db, b"other-key", token, NOW)


class LoginInputTypeTests(World):
    """REV-006: malformed login inputs fail exactly like any other login failure."""

    def test_non_string_or_non_int_inputs_are_uniform_auth_errors(self):
        email, pw, tid = "a_admin@example.test", TEST_LOGIN_PW, self.ta
        bad_sets = [
            ({"a": 1}, pw, tid), (email, ["x"], tid), (None, pw, tid), (email, None, tid),
            (email, pw, {"a": 1}), (email, pw, "1"), (email, pw, 1.0), (email, pw, True),
            (email, pw, None), (email, pw, 2**63), (email, pw, -(2**63) - 1), (email, pw, 10**400),
        ]
        messages = set()
        for e, p, t in bad_sets:
            with self.assertRaises(AuthError) as ctx:
                auth.login(self.db, KEY, e, p, t, NOW)
            messages.add(str(ctx.exception))
        self.assertEqual(messages, {"invalid credentials"})


class FiniteTimeTests(World):
    """SR-002: a token never carries, and the verifier never accepts, a non-finite time."""

    def test_minting_rejects_non_finite_or_nonpositive_ttl_and_non_finite_now(self):
        for ttl in (float("nan"), float("inf"), float("-inf"), 0, -5, True, "60", None):
            with self.assertRaises(Invalid, msg=repr(ttl)):
                auth.issue_token(KEY, 1, 1, "owner", NOW, ttl=ttl)
        for now in (float("nan"), float("inf"), None, "0"):
            with self.assertRaises(Invalid, msg=repr(now)):
                auth.issue_token(KEY, 1, 1, "owner", now)

    def signed(self, raw_payload):
        body = auth._b64(raw_payload)
        return body + "." + auth._sign(KEY, body)

    def test_a_correctly_signed_token_with_a_non_finite_expiry_is_rejected(self):
        for exp in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            token = self.signed(b'{"uid":1,"tid":1,"role":"owner","exp":' + exp + b"}")
            with self.assertRaises(AuthError, msg=exp):
                auth.verify_token(KEY, token, 10**100)
            with self.assertRaises(AuthError, msg=exp):
                auth.verify_token(KEY, token, NOW)

    def test_a_non_finite_clock_never_validates_anything(self):
        token = auth.issue_token(KEY, 1, 1, "owner", NOW)
        for now in (float("nan"), float("inf"), None):
            with self.assertRaises(AuthError, msg=repr(now)):
                auth.verify_token(KEY, token, now)

    def test_a_non_ascii_signature_is_a_clean_auth_error(self):  # SR-004
        body = auth.issue_token(KEY, 1, 1, "owner", NOW).split(".")[0]
        for sig in ("\u00e9", "x\u00e9y", "\u202e" + "0" * 64):
            with self.assertRaises(AuthError, msg=repr(sig)):
                auth.verify_token(KEY, body + "." + sig, NOW)


if __name__ == "__main__":
    unittest.main()
