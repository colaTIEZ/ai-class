"""Phase 1 object storage abstraction tests."""

from pathlib import Path

from app.services.object_storage import LocalObjectStorage


def test_local_object_storage_put_bytes(tmp_path: Path):
    storage = LocalObjectStorage(root=tmp_path, bucket="ai-class-dev")
    key = storage.put_bytes("raw/local-dev/123/source.pdf", b"%PDF-demo")

    stored_path = tmp_path / "ai-class-dev" / "raw" / "local-dev" / "123" / "source.pdf"
    assert key == "raw/local-dev/123/source.pdf"
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"%PDF-demo"


def test_local_object_storage_uri_for(tmp_path: Path):
    storage = LocalObjectStorage(root=tmp_path, bucket="ai-class-dev")
    uri = storage.uri_for("raw/local-dev/123/source.pdf")
    assert uri == "local://ai-class-dev/raw/local-dev/123/source.pdf"


def test_local_object_storage_creates_parent_dirs(tmp_path: Path):
    storage = LocalObjectStorage(root=tmp_path, bucket="b")
    key = storage.put_bytes("a/b/c/d.txt", b"deep")
    stored_path = tmp_path / "b" / "a" / "b" / "c" / "d.txt"
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"deep"
