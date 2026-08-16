"""Browser-level end-to-end tests.

The rest of the suite drives the application in-process through Starlette's
``TestClient``, which proves what the *server* returns. These tests boot the
real server on a socket and drive a real Chromium against it, which proves
what a *browser* does with what it got -- script errors, and every URL the
page actually fetches, whatever file asked for it.

That difference is not academic. A stylesheet containing
``@import url(https://fonts.googleapis.com/...)`` is invisible to a sweep over
served HTML, and breaches the offline-classroom rule in
``.claude/shared/CLAUDE.md`` §3 all the same.

A package (rather than a bare directory) because ``tests/`` is one: pytest's
default import mode needs the ``__init__.py`` chain to import
``tests.e2e.test_smoke`` unambiguously.
"""
