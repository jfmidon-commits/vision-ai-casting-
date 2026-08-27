import json
from typing import Any


def _json_default(value: Any) -> Any:
    """Convert NumPy-style scalars/arrays to native JSON-compatible values.

    NumPy scalar types (for example ``np.bool_``, ``np.int64`` and
    ``np.float32``) expose ``item()``. Arrays expose ``tolist()``. Keeping this
    adapter dependency-free avoids importing NumPy during database startup while
    still normalizing values emitted by computer-vision analyzers.
    """
    item = getattr(value, "item", None)
    if callable(item):
        try:
            native = item()
            if native is not value:
                return native
        except (TypeError, ValueError):
            pass

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return tolist()
        except (TypeError, ValueError):
            pass

    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def json_dumps(value: Any) -> str:
    """Serialize JSON/JSONB payloads while normalizing NumPy values."""
    return json.dumps(value, default=_json_default)
