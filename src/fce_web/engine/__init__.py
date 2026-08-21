"""The physics engine, vendored from the reference repo's ``engine/`` package
(kskovpen/fce).

Only the modules that are already free of the desktop front end, or that we
have decoupled from the reference's global state, live here. Nothing under
this package may import the desktop GUI toolkit or the reference's front-end
package -- see ``.claude/shared/CLAUDE.md`` §2. Keep this module
import-light: it must be importable with zero front-end dependencies pulled
in as a side effect.
"""
