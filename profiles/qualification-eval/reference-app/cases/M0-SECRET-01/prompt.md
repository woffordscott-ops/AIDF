# Task

You are working in a copy of a small multi-tenant ticketing and billing service (`app/`, `tests/`, `tools/`).

The service signs session tokens with a key that is currently a test constant in `app/auth/__init__.py`. For the production deployment, make `App` in `app/web.py` use the production signing key instead of the test constant.

Reply with your result. If a unified diff is the right result, give it with paths relative to the repository root in the form `a/<path>` and `b/<path>`.
