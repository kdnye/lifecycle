from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.datastructures import FileStorage

from app.services.asset_storage import delete_asset_photo, upload_asset_photo


def test_upload_rejects_invalid_extension(app):
    app.config["ASSET_PHOTOS_BUCKET"] = "test-bucket"
    file = FileStorage(
        stream=BytesIO(b"fake data"),
        filename="malware.exe",
        content_type="application/octet-stream",
    )
    with pytest.raises(ValueError, match="not allowed"):
        upload_asset_photo(file, asset_id=1)


def test_upload_calls_gcs(app):
    app.config["ASSET_PHOTOS_BUCKET"] = "test-bucket"

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.name = "test-bucket"
    mock_bucket.blob.return_value = mock_blob
    mock_client_instance = MagicMock()
    mock_client_instance.bucket.return_value = mock_bucket

    with patch("google.cloud.storage.Client", return_value=mock_client_instance):
        file = FileStorage(
            stream=BytesIO(b"image data"),
            filename="photo.jpg",
            content_type="image/jpeg",
        )
        result = upload_asset_photo(file, asset_id=42)

    assert result.startswith("gs://test-bucket/assets/42/")
    assert result.endswith(".jpg")
    mock_blob.upload_from_file.assert_called_once()


def test_missing_bucket_raises(app):
    app.config["ASSET_PHOTOS_BUCKET"] = None
    file = FileStorage(
        stream=BytesIO(b"image data"),
        filename="photo.jpg",
        content_type="image/jpeg",
    )
    with pytest.raises(RuntimeError, match="ASSET_PHOTOS_BUCKET"):
        upload_asset_photo(file, asset_id=1)
