"""``python -m fce_web`` -- the one launch a teacher needs.

Runs ``create_app`` under uvicorn with ``access_log=False``. Uvicorn's default access log
prints every client's address on every request; on a classroom network of minors that is an
IP address logged for no reason (design-brief §6, GDPR -- ``.claude/backend/CLAUDE.md`` §5).
The documented ``uvicorn --factory fce_web.app:create_app`` launch does not turn this off, so
it is not the safe default any more -- this module is.

Default host is ``0.0.0.0``: a classroom is students on laptops reaching the teacher's
machine over the LAN, and ``127.0.0.1`` would only ever answer the teacher's own browser.
A single laptop with no network still works the same way. Pass ``--host 127.0.0.1`` to
refuse LAN connections entirely.
"""
import argparse
from typing import Optional, Sequence

import uvicorn


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m fce_web", description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on (default: 8000)")
    args = parser.parse_args(argv)
    uvicorn.run("fce_web.app:create_app", factory=True, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
