"""Tests for storage backends."""

import tempfile
from pathlib import Path
import pytest
from storage.local import LocalStorageBackend


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def local_backend(temp_storage_dir):
    """Create a local storage backend for testing."""
    return LocalStorageBackend(temp_storage_dir)


def test_local_backend_save(local_backend, temp_storage_dir):
    """Test saving a file to local storage."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_file = Path(f.name)

    try:
        result = local_backend.save(temp_file, "test_dir/test_file.txt")
        assert result == "test_dir/test_file.txt"
        assert (Path(temp_storage_dir) / "test_dir" / "test_file.txt").exists()
    finally:
        temp_file.unlink()


def test_local_backend_load(local_backend, temp_storage_dir):
    """Test loading a file from local storage."""
    # Create a file in storage
    storage_dir = Path(temp_storage_dir)
    storage_dir.joinpath("test_dir").mkdir(exist_ok=True)
    storage_file = storage_dir / "test_dir" / "test_file.txt"
    storage_file.write_text("test content")

    # Load it back
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = Path(f.name)

    try:
        local_backend.load("test_dir/test_file.txt", temp_path)
        assert temp_path.exists()
        assert temp_path.read_text() == "test content"
    finally:
        temp_path.unlink()


def test_local_backend_exists(local_backend, temp_storage_dir):
    """Test checking file existence."""
    storage_dir = Path(temp_storage_dir)
    storage_dir.joinpath("test_dir").mkdir(exist_ok=True)
    storage_file = storage_dir / "test_dir" / "test_file.txt"
    storage_file.write_text("test")

    assert local_backend.exists("test_dir/test_file.txt") is True
    assert local_backend.exists("test_dir/nonexistent.txt") is False


def test_local_backend_delete(local_backend, temp_storage_dir):
    """Test deleting a file."""
    storage_dir = Path(temp_storage_dir)
    storage_dir.joinpath("test_dir").mkdir(exist_ok=True)
    storage_file = storage_dir / "test_dir" / "test_file.txt"
    storage_file.write_text("test")

    assert storage_file.exists()
    local_backend.delete("test_dir/test_file.txt")
    assert not storage_file.exists()


def test_local_backend_list_dir(local_backend, temp_storage_dir):
    """Test listing files in a directory."""
    storage_dir = Path(temp_storage_dir)
    storage_dir.joinpath("test_dir").mkdir(exist_ok=True)
    Path(storage_dir / "test_dir" / "file1.txt").write_text("1")
    Path(storage_dir / "test_dir" / "file2.txt").write_text("2")

    files = local_backend.list_dir("test_dir")
    assert len(files) == 2
    assert "test_dir/file1.txt" in files
    assert "test_dir/file2.txt" in files


def test_local_backend_get_url(local_backend, temp_storage_dir):
    """Test getting a file URL."""
    storage_dir = Path(temp_storage_dir)
    storage_dir.joinpath("test_dir").mkdir(exist_ok=True)
    storage_file = storage_dir / "test_dir" / "test_file.txt"
    storage_file.write_text("test")

    url = local_backend.get_url("test_dir/test_file.txt")
    assert url.startswith("file://")
    assert "test_dir/test_file.txt" in url
