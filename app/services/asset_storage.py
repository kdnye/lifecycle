import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage


_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def _get_bucket():
    bucket_name = current_app.config.get("ASSET_PHOTOS_BUCKET")
    if not bucket_name:
        raise RuntimeError(
            "ASSET_PHOTOS_BUCKET is not configured. "
            "Set this environment variable to enable photo uploads."
        )
    from google.cloud import storage  # noqa: PLC0415 — imported lazily to avoid hard dep in tests
    return storage.Client().bucket(bucket_name)


def upload_asset_photo(file: FileStorage, asset_id: int) -> str:
    """Stream file directly to GCS. Returns gs://bucket/path URL."""
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' is not allowed. "
            f"Accepted: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )
    blob_name = f"assets/{asset_id}/{uuid.uuid4().hex}.{ext}"
    bucket = _get_bucket()
    blob = bucket.blob(blob_name)
    content_type = file.content_type or f"image/{ext}"
    blob.upload_from_file(file.stream, content_type=content_type)
    return f"gs://{bucket.name}/{blob_name}"


def delete_asset_photo(photo_url: str) -> None:
    """Delete a GCS asset photo. Silent no-op if missing or not a GCS URL."""
    if not photo_url or not photo_url.startswith("gs://"):
        return
    try:
        without_scheme = photo_url[len("gs://"):]
        bucket_name, _, blob_name = without_scheme.partition("/")
        bucket = _get_bucket()
        if bucket.name != bucket_name:
            return
        bucket.blob(blob_name).delete()
    except Exception:
        pass
