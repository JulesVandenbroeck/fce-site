"""HTTP endpoints for FCE-site, grouped by what they serve.

Each module here exposes a ``build_router()`` factory rather than a
module-level ``APIRouter``. That is deliberate: ``.claude/shared/CLAUDE.md`` §6
forbids module-level mutable state, and a router is mutable -- routes are
registered into it. Building one per ``create_app()`` call keeps every
application instance independent, which matters once a classroom of students
shares one process.
"""
