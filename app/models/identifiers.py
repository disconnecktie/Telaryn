"""Generate compact, human-readable public references for Telaryn work."""

from __future__ import annotations

from secrets import choice


# Avoid visually ambiguous characters in references people read aloud or type.
PUBLIC_ID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_public_id(prefix: str) -> str:
    """Return an opaque, grouped public identifier such as TKT-7H4K-9M2P-6R8W."""
    groups = [
        "".join(choice(PUBLIC_ID_ALPHABET) for _ in range(4))
        for _ in range(3)
    ]
    return f"{prefix}-{'-'.join(groups)}"

