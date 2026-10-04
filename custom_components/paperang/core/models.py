"""Resolve the printer model recorded in a config entry.

The model name is stored when the entry is created (``CONF_MODEL``) and is what
the library uses to pick print-head geometry.  Entries created before
multi-model support have no value and fall back to the library default, which
is the P2 — the model those entries were created against.
"""

from __future__ import annotations

from ..const import CONF_MODEL
from .paperang_lib import DEFAULT_MODEL, get_model

#: Print-head width used when the library is too old to resolve a model.
FALLBACK_PRINT_WIDTH = 576


def entry_model_name(entry) -> str:
    """Model name stored in a config entry, defaulting to the library default."""
    data = getattr(entry, "data", None) or {}
    return data.get(CONF_MODEL) or DEFAULT_MODEL


def entry_model(entry):
    """Resolved ``PrinterModel`` for an entry, or None if unavailable.

    Returns None when the installed library predates multi-model support or the
    stored name is unknown, so callers can fall back to P2 geometry.
    """
    if get_model is None:
        return None
    try:
        return get_model(entry_model_name(entry))
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def entry_print_width(entry) -> int:
    """Print-head width in dots for an entry."""
    model = entry_model(entry)
    return model.print_width if model is not None else FALLBACK_PRINT_WIDTH


def registered_model_names() -> list[str]:
    """Names of every model the installed library knows about."""
    if get_model is None:
        return [DEFAULT_MODEL]
    try:
        from .paperang_lib import list_models  # pylint: disable=import-outside-toplevel

        return sorted(list_models()) if list_models else [DEFAULT_MODEL]
    except Exception:  # pylint: disable=broad-exception-caught
        return [DEFAULT_MODEL]
