"""Application-wide runtime configuration."""

import sys
from typing import TextIO


def _configure_utf8(stream: TextIO | None) -> None:
    """Use UTF-8 for application logs without assuming a specific terminal."""
    if stream is None:
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if not callable(reconfigure):
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        # Some test runners and embedded environments expose immutable streams.
        pass


_configure_utf8(sys.stdout)
_configure_utf8(sys.stderr)
