"""FCE-site: a browser-based learning game for particle-physics data analysis.

This package holds the whole server side of the project: the FastAPI
application, the data layer, and the physics engine vendored from
``kskovpen/fce``. Nothing here imports a UI toolkit -- the desktop
predecessor's Dear PyGui front end is deliberately not carried over.

Keep this module import-light. It is imported by packaging metadata checks and
by every sub-module, so pulling heavy scientific dependencies in here would tax
startup and make ``import fce_web`` fail in environments that only need the
version.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
