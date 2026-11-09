"""Normalize feedback context and safely decode user-supplied screenshots."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePath
import re
from urllib.parse import urlsplit
import warnings

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError


MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024
MAX_SCREENSHOT_PIXELS = 40_000_000
MAX_SCREENSHOT_DIMENSION = 8_000
Image.MAX_IMAGE_PIXELS = MAX_SCREENSHOT_PIXELS

_FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def normalize_route(value: str) -> str:
    """Keep only a bounded application path, never query strings or fragments."""
    candidate = value.strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return (urlsplit(candidate).path or "/")[:500]


def safe_filename(value: str | None, content_type: str) -> str:
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
    name = PurePath(value or f"feedback-screenshot{suffix}").name[:255]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", PurePath(name).stem)[:220].strip(".-") or "feedback-screenshot"
    return f"{stem}{suffix}"


async def sanitize_screenshot(upload: UploadFile | None) -> tuple[bytes | None, str | None, str | None]:
    """Validate actual pixels and re-encode without metadata or active content."""
    if upload is None or not upload.filename:
        return None, None, None
    raw = await upload.read(MAX_SCREENSHOT_BYTES + 1)
    if len(raw) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Screenshot must be 5 MB or smaller.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as opened:
                image_format = (opened.format or "").upper()
                if image_format not in _FORMAT_CONTENT_TYPES or getattr(opened, "n_frames", 1) != 1:
                    raise ValueError("unsupported image")
                opened.load()
                if opened.width > MAX_SCREENSHOT_DIMENSION or opened.height > MAX_SCREENSHOT_DIMENSION:
                    raise ValueError("image dimensions are too large")
                content_type = _FORMAT_CONTENT_TYPES[image_format]
                has_alpha = "A" in opened.getbands()
                normalized = opened.convert("RGBA" if has_alpha and image_format != "JPEG" else "RGB")
                output = BytesIO()
                if image_format == "JPEG":
                    normalized.save(output, format="JPEG", quality=88, optimize=True)
                elif image_format == "PNG":
                    normalized.save(output, format="PNG", optimize=True)
                else:
                    normalized.save(output, format="WEBP", quality=88, method=6)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=422, detail="Screenshot must be a valid PNG, JPEG, or WebP image.") from None
    sanitized = output.getvalue()
    if len(sanitized) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Sanitized screenshot must be 5 MB or smaller.")
    return sanitized, content_type, safe_filename(upload.filename, content_type)
